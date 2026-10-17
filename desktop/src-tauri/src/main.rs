#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::sync::{atomic::{AtomicBool, AtomicU64, Ordering}, Mutex};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
use tauri::menu::{CheckMenuItem, Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri_plugin_autostart::ManagerExt;
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_shell::{process::{CommandChild, CommandEvent}, ShellExt};

mod native_shell;

const SHORTCUT: &str = "Ctrl+Shift+Space";

fn cloud_webview_inspection() -> bool {
    std::env::var("GITHUB_ACTIONS").as_deref() == Ok("true")
        && std::env::var("RUNNER_ENVIRONMENT").as_deref() == Ok("github-hosted")
        && std::env::var("FACETMARK_CI_WEBVIEW_INSPECT").as_deref() == Ok("1")
}
const CI_BROWSER_ARGS: &str = "--remote-debugging-port=9223 --disable-features=msWebOOUI,msPdfOOUI,msSmartScreenProtection";

fn open_original(app: &tauri::AppHandle, target: &tauri::Url, event: &str) {
    if !matches!(target.scheme(), "http" | "https") { return; }
    let result = app.opener().open_url(target.as_str(), None::<&str>);
    // Diagnostics are restricted to the disposable CI VM and its synthetic URLs.
    if cloud_webview_inspection() {
        if let Some(directory) = std::env::var_os("FACETMARK_CI_EVIDENCE_DIR") {
            use std::io::Write;
            let path = std::path::PathBuf::from(directory).join("native-links.jsonl");
            if let Ok(mut file) = std::fs::OpenOptions::new().create(true).append(true).open(path) {
                let record = serde_json::json!({ "event": event, "url": target.as_str(),
                    "error": result.err().map(|error| error.to_string()) });
                let _ = writeln!(file, "{record}");
            }
        }
    }
}

#[derive(Default)]
struct Backend {
    child: Mutex<Option<CommandChild>>,
    exiting: AtomicBool,
    starting: AtomicBool,
    ready: AtomicBool,
    owned: AtomicBool,
    error_shown: AtomicBool,
    generation: AtomicU64,
}

/// Last known main-window box. Stored so a reopen lands where the user left it.
#[derive(Serialize, Deserialize, Clone, Copy)]
struct Geometry { x: i32, y: i32, width: u32, height: u32 }

#[derive(Serialize, Deserialize)]
#[serde(default)]
struct Preferences {
    tray_notice_seen: bool,
    shortcut: bool,
    window: Option<Geometry>,
    maximized: bool,
}
impl Default for Preferences {
    fn default() -> Self { Self { tray_notice_seen: false, shortcut: true, window: None, maximized: false } }
}
fn preferences(app: &tauri::AppHandle) -> Preferences {
    app.path().app_config_dir().ok()
        .and_then(|p| std::fs::read(p.join("desktop.json")).ok())
        .and_then(|b| serde_json::from_slice(&b).ok()).unwrap_or_default()
}
fn save_preferences(app: &tauri::AppHandle, prefs: &Preferences) {
    let write = || -> Result<(), Box<dyn std::error::Error>> {
        let dir = app.path().app_config_dir()?;
        std::fs::create_dir_all(&dir)?;
        let temp = dir.join("desktop.tmp");
        std::fs::write(&temp, serde_json::to_vec(prefs)?)?;
        std::fs::rename(temp, dir.join("desktop.json"))?;
        Ok(())
    };
    if let Err(error) = write() {
        app.dialog().message(format!("偏好未能保存，重启后可能恢复默认值。 / Preferences could not be saved: {error}")).title("Facetmark").show(|_| {});
    }
}

/// Mutex because it is the only way to keep a throttle in a plain `static`;
/// `Instant::now` is monotonic, so a clock change cannot freeze the writes.
static LAST_GEOMETRY: Mutex<Option<(std::time::Instant, Geometry)>> = Mutex::new(None);

fn remember_geometry(window: &tauri::Window) {
    if window.is_maximized().unwrap_or(false) || window.is_minimized().unwrap_or(false) { return; }
    let (Ok(position), Ok(size)) = (window.outer_position(), window.outer_size()) else { return };
    if size.width == 0 || size.height == 0 { return; }
    let geometry = Geometry {
        x: position.x, y: position.y,
        width: size.width, height: size.height,
    };
    // Drags resize hundreds of times a second; one write per second is enough
    // to survive a crash and keeps the config file off the hot path.
    let mut last = LAST_GEOMETRY.lock().unwrap();
    if let Some((at, previous)) = *last {
        if at.elapsed() < std::time::Duration::from_millis(900) && previous.width == geometry.width
            && previous.height == geometry.height && previous.x == geometry.x && previous.y == geometry.y { return; }
    }
    *last = Some((std::time::Instant::now(), geometry));
    let mut prefs = preferences(window.app_handle());
    prefs.window = Some(geometry);
    prefs.maximized = false;
    save_preferences(window.app_handle(), &prefs);
}

/// A geometry saved on a monitor that is gone would open the window offscreen.
fn saved_geometry(app: &tauri::AppHandle) -> Option<Geometry> {
    let geometry = preferences(app).window?;
    let monitors = app.available_monitors().ok()?;
    let monitor = monitors.iter().find(|m| {
        let (origin, size) = (m.position(), m.size());
        geometry.x < origin.x + size.width as i32 && geometry.x + geometry.width as i32 > origin.x
            && geometry.y < origin.y + size.height as i32 && geometry.y + geometry.height as i32 > origin.y
    })?;
    let bounds = monitor.size();
    if geometry.width < 780 || geometry.height < 560 || geometry.width > bounds.width.saturating_mul(2)
        || geometry.height > bounds.height.saturating_mul(2) { return None; }
    Some(geometry)
}

fn focus_main(app: &tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("main").or_else(|| app.get_webview_window("loading")) {
        let _ = win.show(); let _ = win.unminimize(); let _ = win.set_focus();
    }
}
fn startup_error(app: &tauri::AppHandle, message: &str) {
    let window = app.get_webview_window("loading").or_else(|| {
        WebviewWindowBuilder::new(app, "loading", WebviewUrl::App("index.html".into()))
            .title("Facetmark").inner_size(460., 320.).center().build().ok()
    });
    if let Some(win) = window {
        let _ = win.show();
        let payload = serde_json::to_string(message).unwrap_or_default();
        // `eval` can beat the splash's script on a cold start. Park the message
        // on the window and let the page pick it up when it is ready.
        let _ = win.eval(format!(
            "window.__facetmarkStartupError = {payload};\
             if (window.showStartupError) window.showStartupError({payload});"
        ).as_str());
    }
}
fn open_workspace(app: &tauri::AppHandle, port: u16) -> Result<(), String> {
    let url: tauri::Url = format!("http://127.0.0.1:{port}/app").parse().map_err(|e| format!("{e}"))?;
    let geometry = saved_geometry(app);
    let prefs = preferences(app);
    let origin = url.origin();
    let handle = app.clone();
    let new_handle = app.clone();
    let mut builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
        .title("Facetmark")
        .inner_size(geometry.map_or(1440., |g| g.width as f64), geometry.map_or(920., |g| g.height as f64))
        .min_inner_size(780., 560.)
        .on_navigation(move |target| {
            if target.origin() == origin && (target.path() == "/app" || target.path().starts_with("/app/")) { return true; }
            open_original(&handle, target, "navigation");
            false
        })
        .on_new_window(move |target, _| {
            open_original(&new_handle, &target, "new_window");
            tauri::webview::NewWindowResponse::Deny
        });
    // Only a service restart under a live UI needs the label freed first.
    if let Some(old) = app.get_webview_window("main") { let _ = old.destroy(); }
    builder = match geometry {
        Some(box_) => builder.position(box_.x as f64, box_.y as f64),
        None => builder.center(),
    };
    if cloud_webview_inspection() { builder = builder.additional_browser_args(CI_BROWSER_ARGS); }
    let window = match builder.build() {
        Ok(window) => window,
        Err(error) => {
            // Keep the app reachable: without a window the tray is the only
            // entry point, and a failed build may have taken the splash too.
            startup_error(app, &format!("工作台窗口未能打开。 / The workspace window could not open: {error}"));
            return Err(error.to_string());
        }
    };
    if prefs.maximized { let _ = window.maximize(); }
    let _ = window.set_focus();
    if let Some(splash) = app.get_webview_window("loading") { let _ = splash.destroy(); }
    Ok(())
}
fn spawn_backend(app: &tauri::AppHandle) -> Result<(), String> {
    let state = app.state::<Backend>();
    if state.starting.swap(true, Ordering::SeqCst) { return Ok(()); }
    let generation = state.generation.fetch_add(1, Ordering::SeqCst) + 1;
    state.ready.store(false, Ordering::SeqCst);
    let command = app.shell().sidecar("facetmark-service").map_err(|e| {
            state.starting.store(false, Ordering::SeqCst); e.to_string()
        })?
        .args(["--parent-pid", &std::process::id().to_string()]);
    let (mut events, child) = match command.spawn() {
        Ok(result) => result,
        Err(e) => { state.starting.store(false, Ordering::SeqCst); return Err(e.to_string()); }
    };
    *state.child.lock().unwrap() = Some(child);
    let timeout_handle = app.clone();
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_secs(45));
        let state = timeout_handle.state::<Backend>();
        if state.generation.load(Ordering::SeqCst) != generation { return; }
        if state.starting.swap(false, Ordering::SeqCst) && !state.ready.load(Ordering::SeqCst) && !state.exiting.load(Ordering::SeqCst) {
            if let Some(child) = state.child.lock().unwrap().take() { let _ = child.kill(); }
            startup_error(&timeout_handle, "服务启动超时。请重试或检查数据目录权限。 / Startup timed out. Retry or check data directory permissions.");
        }
    });
    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            if handle.state::<Backend>().generation.load(Ordering::SeqCst) != generation { break; }
            match event {
                CommandEvent::Stdout(line) => {
                    if let Ok(record) = serde_json::from_slice::<serde_json::Value>(&line) {
                        match record["event"].as_str() {
                            Some("ready") => {
                                let state = handle.state::<Backend>();
                                state.starting.store(false, Ordering::SeqCst);
                                state.owned.store(record["owned"].as_bool().unwrap_or(false), Ordering::SeqCst);
                                if let Some(port) = record["port"].as_u64().filter(|p| *p > 0 && *p < 65536) {
                                    match open_workspace(&handle, port as u16) {
                                        Ok(_) => { state.ready.store(true, Ordering::SeqCst); },
                                        Err(e) => startup_error(&handle, &e),
                                    }
                                }
                            },
                            Some("error") => {
                                // The sidecar reports a fatal condition and then
                                // exits; clear the handle now so Restart is not
                                // rejected as "still running" during that gap.
                                let state = handle.state::<Backend>();
                                state.error_shown.store(true, Ordering::SeqCst);
                                state.starting.store(false, Ordering::SeqCst);
                                if let Some(child) = state.child.lock().unwrap().take() { let _ = child.kill(); }
                                startup_error(&handle, record["message"].as_str().unwrap_or("Service startup failed"));
                            },
                            _ => {},
                        }
                    }
                },
                CommandEvent::Terminated(_) => {
                    let state = handle.state::<Backend>();
                    state.starting.store(false, Ordering::SeqCst);
                    *state.child.lock().unwrap() = None;
                    // A specific startup error already explains this exit; the
                    // generic line would replace it with less information.
                    let specific = state.error_shown.swap(false, Ordering::SeqCst);
                    if !specific && !state.exiting.load(Ordering::SeqCst)
                        && (!state.ready.load(Ordering::SeqCst) || state.owned.load(Ordering::SeqCst)) {
                        startup_error(&handle, "本地服务已停止。可重新启动；已保存的书签会保留。 / Local service stopped. Restart to continue.");
                    }
                    break;
                },
                _ => {},
            }
        }
    });
    Ok(())
}
fn request_exit(app: &tauri::AppHandle) {
    let state = app.state::<Backend>();
    if state.exiting.swap(true, Ordering::SeqCst) { return; }
    if let Some(child) = state.child.lock().unwrap().as_mut() { let _ = child.write(b"stop\n"); }
    let handle = app.clone();
    std::thread::spawn(move || {
        // Give lifespan shutdown time to persist interrupted work and close SQLite.
        for _ in 0..100 {
            if handle.state::<Backend>().child.lock().unwrap().is_none() { break; }
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        if let Some(child) = handle.state::<Backend>().child.lock().unwrap().take() { let _ = child.kill(); }
        handle.exit(0);
    });
}
#[tauri::command]
fn restart_backend(window: tauri::WebviewWindow, app: tauri::AppHandle) -> Result<(), String> {
    if window.label() != "loading" { return Err("Only the local startup window may restart the service".into()); }
    if app.state::<Backend>().child.lock().unwrap().is_some() { return Err("Service is still running".into()); }
    spawn_backend(&app)
}
fn main() {
    let mut context = tauri::generate_context!();
    if cloud_webview_inspection() {
        for window in &mut context.config_mut().app.windows {
            window.additional_browser_args = Some(CI_BROWSER_ARGS.into());
        }
    }
    // Explicit libraries have independent desktop single-instance namespaces.
    // Canonicalizing matches Python's resolved data directory, including aliases.
    let directory = std::env::var_os("FACETMARK_DATA_DIR").or_else(|| {
        std::env::var_os("LOCALAPPDATA").or_else(|| std::env::var_os("USERPROFILE"))
            .map(|base| std::path::PathBuf::from(base).join("facetmark").into_os_string())
    });
    if let Some(directory) = directory {
        let path = std::path::PathBuf::from(directory);
        let _ = std::fs::create_dir_all(&path);
        if let Ok(path) = path.canonicalize() {
            std::env::set_var("FACETMARK_DATA_DIR", &path);
            // Windows paths are case-insensitive; elsewhere two distinct
            // directory names must stay distinct single-instance namespaces.
            let normalized = if cfg!(windows) { path.to_string_lossy().to_lowercase() } else { path.to_string_lossy().into_owned() };
            let hash = normalized.bytes().fold(0xcbf29ce484222325u64, |h, b| (h ^ b as u64).wrapping_mul(0x100000001b3));
            context.config_mut().identifier.push_str(&format!(".library-{hash:016x}"));
        }
    }
    tauri::Builder::default()
        .manage(Backend::default())
        .plugin(tauri_plugin_single_instance::init(|app, _, _| focus_main(app)))
        .plugin(native_shell::init())
        // The remote workbench has no opener IPC capability. Leave native link
        // events to on_navigation/on_new_window instead of cancelling them in JS.
        .plugin(tauri_plugin_opener::Builder::new().open_js_links_on_click(false).build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_autostart::Builder::new().build())
        .plugin(tauri_plugin_global_shortcut::Builder::new().with_handler(|app, _, event| {
            if event.state() == ShortcutState::Pressed { focus_main(app); }
        }).build())
        .invoke_handler(tauri::generate_handler![restart_backend])
        .setup(|app| {
            let show = MenuItem::with_id(app, "show", "打开 Facetmark / Open", true, None::<&str>)?;
            let startup = CheckMenuItem::with_id(app, "startup", "开机启动 / Launch at login", true, app.autolaunch().is_enabled().unwrap_or(false), None::<&str>)?;
            let prefs = preferences(app.handle());
            let shortcut = CheckMenuItem::with_id(app, "shortcut", "全局快捷键 Ctrl+Shift+Space", true, prefs.shortcut, None::<&str>)?;
            let update = MenuItem::with_id(app, "update", "检查更新 / Check for updates", true, None::<&str>)?;
            let exit = MenuItem::with_id(app, "exit", "退出 / Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &startup, &shortcut, &update, &exit])?;
            TrayIconBuilder::new().icon(app.default_window_icon().unwrap().clone()).tooltip("Facetmark")
                .on_tray_icon_event(|tray, event| {
                    // Windows convention: a plain left click restores the app;
                    // without this the tray icon feels dead until right-clicked.
                    if let tauri::tray::TrayIconEvent::Click {
                        button: tauri::tray::MouseButton::Left,
                        button_state: tauri::tray::MouseButtonState::Up, ..
                    } = event {
                        focus_main(tray.app_handle());
                    }
                })
                .menu(&menu).on_menu_event(move |app, event| {
                    match event.id.as_ref() {
                        "show" => focus_main(app),
                        "startup" => {
                            let enabled = app.autolaunch().is_enabled().unwrap_or(false);
                            let result = if enabled { app.autolaunch().disable() } else { app.autolaunch().enable() };
                            let _ = startup.set_checked(if result.is_ok() { !enabled } else { enabled });
                        },
                        "shortcut" => {
                            // Trust the actual registration, not the stored
                            // preference: a failed first registration leaves
                            // the two disagreeing, and toggling from the stale
                            // value asks the wrong direction.
                            let registered = app.global_shortcut().is_registered(SHORTCUT).unwrap_or(false);
                            let mut prefs = preferences(app);
                            let result = if registered { app.global_shortcut().unregister(SHORTCUT) } else { app.global_shortcut().register(SHORTCUT) };
                            if result.is_ok() { prefs.shortcut = !registered; save_preferences(app, &prefs); }
                            let _ = shortcut.set_checked(result.is_ok() && !registered);
                        },
                        "update" => {
                            if let Some(win) = app.get_webview_window("main") { let _ = win.eval("window.location.hash = 'settings'"); }
                            focus_main(app);
                        },
                        "exit" => request_exit(app),
                        _ => {},
                    }
                }).build(app)?;
            if prefs.shortcut {
                if let Err(error) = app.global_shortcut().register(SHORTCUT) {
                    let _ = shortcut.set_checked(false);
                    app.dialog().message(format!("无法注册全局快捷键，可能已被占用。 / Global shortcut unavailable: {error}")).title("Facetmark").show(|_| {});
                }
            }
            if let Err(e) = spawn_backend(app.handle()) { startup_error(app.handle(), &e); }
            Ok(())
        })
        .on_window_event(|win, event| {
            match event {
                tauri::WindowEvent::Moved(_) | tauri::WindowEvent::Resized(_) if win.label() == "main" => {
                    remember_geometry(win);
                }
                tauri::WindowEvent::CloseRequested { api, .. } => {
                    if win.label() == "main" {
                        api.prevent_close();
                        remember_geometry(win);
                        if win.is_maximized().unwrap_or(false) {
                            let mut prefs = preferences(win.app_handle());
                            prefs.maximized = true;
                            save_preferences(win.app_handle(), &prefs);
                        }
                        let app = win.app_handle();
                        let mut prefs = preferences(app);
                        if !prefs.tray_notice_seen {
                            app.dialog().message("Facetmark 将在系统托盘继续运行，索引任务不会停止。可在托盘菜单退出。\n\nFacetmark continues in the system tray. Use the tray menu to quit.").title("Facetmark").show(|_| {});
                            prefs.tray_notice_seen = true; save_preferences(app, &prefs);
                        }
                        let _ = win.hide();
                    } else if win.label() == "loading" {
                        api.prevent_close();
                        request_exit(win.app_handle());
                    }
                }
                _ => {}
            }
        })
        .build(context).expect("Cannot initialize Facetmark")
        .run(|app, event| {
            if let tauri::RunEvent::ExitRequested { api, .. } = event {
                if !app.state::<Backend>().exiting.load(Ordering::SeqCst) { api.prevent_exit(); }
            }
        });
}
