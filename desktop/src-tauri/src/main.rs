#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::sync::{atomic::{AtomicBool, Ordering}, Mutex};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
use tauri::menu::{CheckMenuItem, Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri_plugin_autostart::ManagerExt;
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_shell::{process::{CommandChild, CommandEvent}, ShellExt};

const SHORTCUT: &str = "Ctrl+Shift+Space";

#[derive(Default)]
struct Backend {
    child: Mutex<Option<CommandChild>>,
    exiting: AtomicBool,
    starting: AtomicBool,
    ready: AtomicBool,
    owned: AtomicBool,
}

#[derive(Serialize, Deserialize)]
#[serde(default)]
struct Preferences { tray_notice_seen: bool, shortcut: bool }
impl Default for Preferences {
    fn default() -> Self { Self { tray_notice_seen: false, shortcut: true } }
}
fn preferences(app: &tauri::AppHandle) -> Preferences {
    app.path().app_config_dir().ok()
        .and_then(|p| std::fs::read(p.join("desktop.json")).ok())
        .and_then(|b| serde_json::from_slice(&b).ok()).unwrap_or_default()
}
fn save_preferences(app: &tauri::AppHandle, prefs: &Preferences) {
    if let Ok(dir) = app.path().app_config_dir() {
        if std::fs::create_dir_all(&dir).is_ok() {
            let temp = dir.join("desktop.tmp");
            if let Ok(bytes) = serde_json::to_vec(prefs) {
                if std::fs::write(&temp, bytes).is_ok() {
                    let _ = std::fs::rename(temp, dir.join("desktop.json"));
                }
            }
        }
    }
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
        let _ = win.eval(format!("setTimeout(() => window.showStartupError({payload}), 300)").as_str());
    }
}
fn open_workspace(app: &tauri::AppHandle, port: u16) -> Result<(), String> {
    let url: tauri::Url = format!("http://127.0.0.1:{port}/app").parse().map_err(|e| format!("{e}"))?;
    if let Some(old) = app.get_webview_window("main") { let _ = old.destroy(); }
    let origin = url.origin();
    let handle = app.clone();
    let new_handle = app.clone();
    let window = WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
        .title("Facetmark").inner_size(1440., 920.).min_inner_size(780., 560.)
        .center()
        .on_navigation(move |target| {
            if target.origin() == origin && (target.path() == "/app" || target.path().starts_with("/app/")) { return true; }
            if matches!(target.scheme(), "http" | "https") { let _ = handle.opener().open_url(target.as_str(), None::<&str>); }
            false
        })
        .on_new_window(move |target, _| {
            if matches!(target.scheme(), "http" | "https") { let _ = new_handle.opener().open_url(target.as_str(), None::<&str>); }
            tauri::webview::NewWindowResponse::Deny
        })
        .build().map_err(|e| e.to_string())?;
    let _ = window.set_focus();
    if let Some(splash) = app.get_webview_window("loading") { let _ = splash.destroy(); }
    Ok(())
}
fn spawn_backend(app: &tauri::AppHandle) -> Result<(), String> {
    let state = app.state::<Backend>();
    if state.starting.swap(true, Ordering::SeqCst) { return Ok(()); }
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
        if state.starting.swap(false, Ordering::SeqCst) && !state.ready.load(Ordering::SeqCst) && !state.exiting.load(Ordering::SeqCst) {
            if let Some(child) = state.child.lock().unwrap().take() { let _ = child.kill(); }
            startup_error(&timeout_handle, "服务启动超时。请重试或检查数据目录权限。 / Startup timed out. Retry or check data directory permissions.");
        }
    });
    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
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
                            Some("error") => startup_error(&handle, record["message"].as_str().unwrap_or("Service startup failed")),
                            _ => {},
                        }
                    }
                },
                CommandEvent::Terminated(_) => {
                    let state = handle.state::<Backend>();
                    state.starting.store(false, Ordering::SeqCst);
                    *state.child.lock().unwrap() = None;
                    if !state.exiting.load(Ordering::SeqCst) && (!state.ready.load(Ordering::SeqCst) || state.owned.load(Ordering::SeqCst)) {
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
    tauri::Builder::default()
        .manage(Backend::default())
        .plugin(tauri_plugin_single_instance::init(|app, _, _| focus_main(app)))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
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
            let update = MenuItem::with_id(app, "update", "下载更新 / Updates", true, None::<&str>)?;
            let exit = MenuItem::with_id(app, "exit", "退出 / Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &startup, &shortcut, &update, &exit])?;
            TrayIconBuilder::new().icon(app.default_window_icon().unwrap().clone()).tooltip("Facetmark")
                .menu(&menu).on_menu_event(move |app, event| {
                    match event.id.as_ref() {
                        "show" => focus_main(app),
                        "startup" => {
                            let enabled = app.autolaunch().is_enabled().unwrap_or(false);
                            let result = if enabled { app.autolaunch().disable() } else { app.autolaunch().enable() };
                            let _ = startup.set_checked(if result.is_ok() { !enabled } else { enabled });
                        },
                        "shortcut" => {
                            let mut prefs = preferences(app);
                            let result = if prefs.shortcut { app.global_shortcut().unregister(SHORTCUT) } else { app.global_shortcut().register(SHORTCUT) };
                            if result.is_ok() { prefs.shortcut = !prefs.shortcut; save_preferences(app, &prefs); }
                            let _ = shortcut.set_checked(prefs.shortcut);
                        },
                        "update" => { let _ = app.opener().open_url("https://github.com/88lin/facetmark/releases", None::<&str>); },
                        "exit" => request_exit(app),
                        _ => {},
                    }
                }).build(app)?;
            if prefs.shortcut {
                if let Err(error) = app.global_shortcut().register(SHORTCUT) {
                    app.dialog().message(format!("无法注册全局快捷键，可能已被占用。 / Global shortcut unavailable: {error}")).title("Facetmark").show(|_| {});
                }
            }
            if let Err(e) = spawn_backend(app.handle()) { startup_error(app.handle(), &e); }
            Ok(())
        })
        .on_window_event(|win, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if win.label() == "main" {
                    api.prevent_close();
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
        })
        .build(tauri::generate_context!()).expect("Cannot initialize Facetmark")
        .run(|app, event| {
            if let tauri::RunEvent::ExitRequested { api, .. } = event {
                if !app.state::<Backend>().exiting.load(Ordering::SeqCst) { api.prevent_exit(); }
            }
        });
}
