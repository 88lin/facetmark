#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::sync::{atomic::{AtomicBool, AtomicU64, Ordering}, Mutex};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
use tauri::tray::TrayIconBuilder;
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_shell::{process::{CommandChild, CommandEvent}, ShellExt};

mod native_shell;
mod backend_state;
mod tray_menu;
mod window_state;
use backend_state::{RetryError, SidecarGate};
use window_state::{DisplayArea, Geometry, GeometryQueue, WorkArea, client_size_for_outer, visible_geometry};

const SHORTCUT: &str = "Ctrl+Shift+Space";

fn cloud_webview_inspection() -> bool {
    std::env::var("GITHUB_ACTIONS").as_deref() == Ok("true")
        && std::env::var("RUNNER_ENVIRONMENT").as_deref() == Ok("github-hosted")
        && std::env::var("FACETMARK_CI_WEBVIEW_INSPECT").as_deref() == Ok("1")
}
const CI_BROWSER_ARGS: &str = "--remote-debugging-port=9223 --disable-features=msWebOOUI,msPdfOOUI,msSmartScreenProtection";
static CI_WORKSPACE_FAILURE_INJECTED: AtomicBool = AtomicBool::new(false);

fn ci_record(name: &str, record: serde_json::Value) {
    if !cloud_webview_inspection() { return; }
    if let Some(directory) = std::env::var_os("FACETMARK_CI_EVIDENCE_DIR") {
        let path = std::path::PathBuf::from(directory).join(name);
        let _ = std::fs::write(path, record.to_string());
    }
}

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
    lifetime: SidecarGate,
    exiting: AtomicBool,
    starting: AtomicBool,
    ready: AtomicBool,
    owned: AtomicBool,
    error_shown: AtomicBool,
    generation: AtomicU64,
}

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
static PREFERENCE_IO: Mutex<()> = Mutex::new(());

fn write_preferences(app: &tauri::AppHandle, prefs: &Preferences) -> bool {
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
        return false;
    }
    true
}
fn update_preferences(app: &tauri::AppHandle, change: impl FnOnce(&mut Preferences)) {
    let _io = PREFERENCE_IO.lock().unwrap();
    let mut prefs = preferences(app);
    change(&mut prefs);
    write_preferences(app, &prefs);
}

struct GeometryWriter {
    queue: Mutex<GeometryQueue>,
    clock: std::time::Instant,
    maximized: AtomicBool,
}
impl Default for GeometryWriter {
    fn default() -> Self { Self { queue: Mutex::new(GeometryQueue::default()), clock: std::time::Instant::now(), maximized: AtomicBool::new(false) } }
}

fn flush_geometry(app: &tauri::AppHandle, force: bool) {
    // Choose the latest candidate only after serializing all preference writes.
    // An older worker cannot overwrite the final geometry flushed on close.
    let _io = PREFERENCE_IO.lock().unwrap();
    let writer = app.state::<GeometryWriter>();
    let candidate = writer.queue.lock().unwrap().candidate(writer.clock.elapsed(), force);
    let Some((revision, geometry)) = candidate else { return; };
    let mut prefs = preferences(app);
    prefs.window = Some(geometry);
    let saved = write_preferences(app, &prefs);
    writer.queue.lock().unwrap().acknowledge(revision);
    if saved && cloud_webview_inspection() {
        if let Some(directory) = std::env::var_os("FACETMARK_CI_EVIDENCE_DIR") {
            use std::io::Write;
            if let Ok(mut file) = std::fs::OpenOptions::new().create(true).append(true)
                .open(std::path::PathBuf::from(directory).join("geometry-writes.jsonl")) {
                let _ = writeln!(file, "{}", serde_json::json!({ "revision": revision, "geometry": geometry,
                    "process": std::process::id(), "forced": force }));
            }
        }
    }
}

fn remember_geometry(window: &tauri::Window) {
    if !window.is_visible().unwrap_or(false) || window.is_minimized().unwrap_or(true) { return; }
    let Ok(maximized) = window.is_maximized() else { return; };
    let writer = window.app_handle().state::<GeometryWriter>();
    writer.maximized.store(maximized, Ordering::SeqCst);
    if maximized { return; }
    let (Ok(position), Ok(size)) = (window.outer_position(), window.outer_size()) else { return };
    if size.width == 0 || size.height == 0 { return; }
    let geometry = Geometry {
        x: position.x, y: position.y,
        width: size.width, height: size.height,
    };
    // Window events update memory only. One worker writes after 900ms of quiet;
    // closing or quitting flushes the latest box regardless of the deadline.
    let start = writer.queue.lock().unwrap().record(geometry, writer.clock.elapsed());
    if start {
        let handle = window.app_handle().clone();
        std::thread::spawn(move || loop {
            let writer = handle.state::<GeometryWriter>();
            let wait = writer.queue.lock().unwrap().next_wait(writer.clock.elapsed());
            match wait {
                None => break,
                Some(wait) if wait.is_zero() => flush_geometry(&handle, false),
                Some(wait) => std::thread::sleep(wait),
            }
        });
    }
}

fn save_window_mode(app: &tauri::AppHandle) {
    let Some(window) = app.get_webview_window("main") else { return; };
    let writer = app.state::<GeometryWriter>();
    // A minimized window may report is_maximized=false even when it was
    // maximized before minimizing. Retain its last non-minimized mode.
    if !window.is_minimized().unwrap_or(true) {
        if let Ok(maximized) = window.is_maximized() {
            writer.maximized.store(maximized, Ordering::SeqCst);
        }
    }
    let maximized = writer.maximized.load(Ordering::SeqCst);
    update_preferences(app, |prefs| prefs.maximized = maximized);
}

fn display_areas(app: &tauri::AppHandle) -> Vec<DisplayArea> {
    app.available_monitors().unwrap_or_default().iter().map(|monitor| {
        let (origin, size) = (monitor.position(), monitor.size());
        let fallback = WorkArea { x: origin.x, y: origin.y, width: size.width, height: size.height };
        #[cfg(windows)] {
            use windows_sys::Win32::{Foundation::POINT, Graphics::Gdi::{GetMonitorInfoW, MonitorFromPoint, MONITORINFO, MONITOR_DEFAULTTONEAREST}};
            let point = POINT { x: (i64::from(origin.x) + i64::from(size.width) / 2) as i32,
                y: (i64::from(origin.y) + i64::from(size.height) / 2) as i32 };
            let mut info: MONITORINFO = unsafe { std::mem::zeroed() };
            info.cbSize = std::mem::size_of::<MONITORINFO>() as u32;
            if unsafe { GetMonitorInfoW(MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST), &mut info) } != 0 {
                let work = info.rcWork;
                return DisplayArea { bounds: fallback, scale: monitor.scale_factor(),
                    work: WorkArea { x: work.left, y: work.top, width: (work.right - work.left).max(0) as u32,
                        height: (work.bottom - work.top).max(0) as u32 } };
            }
        }
        DisplayArea { bounds: fallback, work: fallback, scale: monitor.scale_factor() }
    }).collect()
}
fn work_areas(app: &tauri::AppHandle) -> Vec<WorkArea> {
    display_areas(app).into_iter().map(|display| display.work).collect()
}

fn restore_geometry(window: &tauri::WebviewWindow, saved: Option<Geometry>) -> tauri::Result<()> {
    let (position, size) = (window.outer_position()?, window.outer_size()?);
    let current = Geometry { x: position.x, y: position.y, width: size.width, height: size.height };
    let areas = work_areas(window.app_handle());
    let wanted = saved.and_then(|geometry| visible_geometry(geometry, &areas)).or_else(|| visible_geometry(current, &areas));
    let Some(wanted) = wanted else { return Ok(()); };
    // Move first so frame measurements and minimum size use the target DPI.
    window.set_position(tauri::PhysicalPosition::new(wanted.x, wanted.y))?;
    let (outer, inner) = (window.outer_size()?, window.inner_size()?);
    let client = client_size_for_outer(wanted, (outer.width, outer.height), (inner.width, inner.height));
    let scale = window.scale_factor()?;
    window.set_min_size(Some(tauri::PhysicalSize::new(((780. * scale).round() as u32).min(client.0),
        ((560. * scale).round() as u32).min(client.1))))?;
    window.set_size(tauri::PhysicalSize::new(client.0, client.1))?;
    window.set_position(tauri::PhysicalPosition::new(wanted.x, wanted.y))?;
    Ok(())
}

fn focus_main(app: &tauri::AppHandle) {
    tray_menu::hide(app);
    if let Some(win) = app.get_webview_window("main").or_else(|| app.get_webview_window("loading")) {
        let _ = win.show(); let _ = win.unminimize(); let _ = win.set_focus();
    }
}
fn startup_error(app: &tauri::AppHandle, message: &str) {
    let window = app.get_webview_window("loading").or_else(|| {
        let mut builder = WebviewWindowBuilder::new(app, "loading", WebviewUrl::App("index.html".into()))
            .title("Facetmark").inner_size(500., 360.).resizable(false).center();
        if cloud_webview_inspection() { builder = builder.additional_browser_args(CI_BROWSER_ARGS); }
        builder.build().ok()
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
    let prefs = preferences(app);
    let origin = url.origin();
    let handle = app.clone();
    let new_handle = app.clone();
    let mut builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
        .title("Facetmark")
        .inner_size(1440., 920.).visible(false).center()
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
    if cloud_webview_inspection() { builder = builder.additional_browser_args(CI_BROWSER_ARGS); }
    if cloud_webview_inspection() && std::env::var("FACETMARK_CI_FAIL_WORKSPACE_ONCE").as_deref() == Ok("1")
        && !CI_WORKSPACE_FAILURE_INJECTED.swap(true, Ordering::SeqCst) {
        let runtime = std::env::var_os("FACETMARK_DATA_DIR")
            .and_then(|directory| std::fs::read(std::path::PathBuf::from(directory).join("desktop-runtime.json")).ok())
            .and_then(|bytes| serde_json::from_slice::<serde_json::Value>(&bytes).ok());
        ci_record("startup-failure-injected.json", serde_json::json!({ "stage": "workspace build after sidecar ready", "port": port,
            "process": std::process::id(), "generation": app.state::<Backend>().generation.load(Ordering::SeqCst),
            "sidecar_pid": runtime.and_then(|record| record["pid"].as_u64()) }));
        return Err("Synthetic CI workspace window construction failure after sidecar ready".into());
    }
    let window = match builder.build() {
        Ok(window) => window,
        Err(error) => return Err(format!("工作台窗口未能打开。 / The workspace window could not open: {error}")),
    };
    app.state::<GeometryWriter>().maximized.store(prefs.maximized, Ordering::SeqCst);
    if let Err(error) = restore_geometry(&window, prefs.window).and_then(|_| window.show()) {
        let _ = window.destroy();
        return Err(format!("工作台窗口未能恢复。 / The workspace window could not restore: {error}"));
    }
    if prefs.maximized { let _ = window.maximize(); }
    let _ = window.set_focus();
    if cloud_webview_inspection() {
        if let (Ok(outer), Ok(position), Ok(inner), Ok(scale)) = (window.outer_size(), window.outer_position(), window.inner_size(), window.scale_factor()) {
            ci_record("native-window.json", serde_json::json!({
                "process": std::process::id(),
                "outer": Geometry { x: position.x, y: position.y, width: outer.width, height: outer.height },
                "inner": { "width": inner.width, "height": inner.height }, "scale_factor": scale,
                "preferences_path": app.path().app_config_dir().ok().map(|path| path.join("desktop.json")),
            }));
        }
    }
    if let Some(splash) = app.get_webview_window("loading") { let _ = splash.destroy(); }
    Ok(())
}
fn spawn_backend(app: &tauri::AppHandle) -> Result<(), String> {
    let state = app.state::<Backend>();
    if state.starting.swap(true, Ordering::SeqCst) { return Ok(()); }
    if state.exiting.load(Ordering::SeqCst) { state.starting.store(false, Ordering::SeqCst); return Err("Application is closing".into()); }
    let Some(generation) = state.lifetime.begin() else {
        state.starting.store(false, Ordering::SeqCst);
        return Err("Service is still running or stopping".into());
    };
    state.generation.store(generation, Ordering::SeqCst);
    state.ready.store(false, Ordering::SeqCst);
    state.error_shown.store(false, Ordering::SeqCst);
    let command = app.shell().sidecar("facetmark-service").map_err(|e| {
            state.starting.store(false, Ordering::SeqCst); state.lifetime.terminated(generation); e.to_string()
        })?
        .args(["--parent-pid", &std::process::id().to_string()]);
    let (mut events, child) = match command.spawn() {
        Ok(result) => result,
        Err(e) => { state.starting.store(false, Ordering::SeqCst); state.lifetime.terminated(generation); return Err(e.to_string()); }
    };
    ci_record("backend-spawn.json", serde_json::json!({ "process": std::process::id(), "generation": generation, "sidecar_pid": child.pid() }));
    *state.child.lock().unwrap() = Some(child);
    let timeout_handle = app.clone();
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_secs(45));
        let state = timeout_handle.state::<Backend>();
        // Serialize with the receiver clearing the child before releasing the
        // gate. A paused old timer cannot mutate the next attempt's flags.
        let _child = state.child.lock().unwrap();
        if !state.lifetime.is_current(generation) { return; }
        if state.starting.swap(false, Ordering::SeqCst) && !state.ready.load(Ordering::SeqCst) && !state.exiting.load(Ordering::SeqCst) {
            state.error_shown.store(true, Ordering::SeqCst);
            stop_failed_backend(&timeout_handle, generation, false);
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
                                // The startup timeout and readiness claim the
                                // same attempt. A late ready cannot reopen a
                                // workspace after that attempt began stopping.
                                if state.exiting.load(Ordering::SeqCst) || !state.starting.swap(false, Ordering::SeqCst) { continue; }
                                ci_record("backend-ready.json", serde_json::json!({ "process": std::process::id(),
                                    "generation": generation, "port": record["port"], "owned": record["owned"] }));
                                state.owned.store(record["owned"].as_bool().unwrap_or(false), Ordering::SeqCst);
                                if let Some(port) = record["port"].as_u64().filter(|p| *p > 0 && *p < 65536) {
                                    let opened = open_workspace(&handle, port as u16);
                                    match opened {
                                        Ok(_) => { state.ready.store(true, Ordering::SeqCst); },
                                        Err(e) => {
                                            state.error_shown.store(true, Ordering::SeqCst);
                                            state.ready.store(false, Ordering::SeqCst);
                                            stop_failed_backend(&handle, generation, true);
                                            startup_error(&handle, &e);
                                        },
                                    }
                                } else {
                                    state.error_shown.store(true, Ordering::SeqCst);
                                    stop_failed_backend(&handle, generation, false);
                                    startup_error(&handle, "服务未提供有效端口。请重试。 / The service did not provide a valid port. Retry.");
                                }
                            },
                            Some("error") => {
                                // Keep the retirement gate closed until its
                                // actual Terminated event, even if kill consumes
                                // the child handle. Immediate Retry waits safely.
                                let state = handle.state::<Backend>();
                                state.error_shown.store(true, Ordering::SeqCst);
                                state.starting.store(false, Ordering::SeqCst);
                                stop_failed_backend(&handle, generation, false);
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
                    ci_record("backend-exit-confirmed.json", serde_json::json!({ "process": std::process::id(), "generation": generation }));
                    state.lifetime.terminated(generation);
                    break;
                },
                _ => {},
            }
        }
    });
    Ok(())
}
fn stop_failed_backend(app: &tauri::AppHandle, generation: u64, hold_for_ci: bool) {
    let state = app.state::<Backend>();
    if !state.lifetime.stop(generation) { return; }
    state.starting.store(false, Ordering::SeqCst);
    state.ready.store(false, Ordering::SeqCst);
    let handle = app.clone();
    std::thread::spawn(move || {
        // Only this disposable-runner injection leaves the failed, ready
        // service alive until the test has pressed Retry. Production never waits
        // on a file or deliberately delays a shutdown.
        if hold_for_ci && cloud_webview_inspection()
            && std::env::var("FACETMARK_CI_HOLD_FAILED_SERVICE").as_deref() == Ok("1") {
            if let Some(directory) = std::env::var_os("FACETMARK_CI_EVIDENCE_DIR") {
                let request = std::path::PathBuf::from(directory).join(format!("startup-exit-release-{}.json", std::process::id()));
                for _ in 0..250 {
                    if handle.state::<Backend>().exiting.load(Ordering::SeqCst) { break; }
                    let released = std::fs::read(&request).ok().and_then(|bytes| serde_json::from_slice::<serde_json::Value>(&bytes).ok())
                        .is_some_and(|record| record["generation"].as_u64() == Some(generation));
                    if released { break; }
                    std::thread::sleep(std::time::Duration::from_millis(100));
                }
            }
        }
        {
            let state = handle.state::<Backend>();
            let mut child = state.child.lock().unwrap();
            if !state.lifetime.is_current(generation) { return; }
            if let Some(child) = child.as_mut() { let _ = child.write(b"stop\n"); }
        }
        ci_record("backend-stop-request.json", serde_json::json!({ "process": std::process::id(), "generation": generation }));
        for _ in 0..100 {
            if !handle.state::<Backend>().lifetime.is_current(generation) { return; }
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        // The gate stays closed after kill. Only the receiver observing an
        // exited OS process may release it, never a timer or an empty handle.
        let state = handle.state::<Backend>();
        let mut child = state.child.lock().unwrap();
        if state.lifetime.is_current(generation) {
            if let Some(child) = child.take() { let _ = child.kill(); }
        }
    });
}
fn request_exit(app: &tauri::AppHandle) {
    let state = app.state::<Backend>();
    if state.exiting.swap(true, Ordering::SeqCst) { return; }
    state.lifetime.wake();
    flush_geometry(app, true);
    save_window_mode(app);
    if let Some(child) = state.child.lock().unwrap().as_mut() { let _ = child.write(b"stop\n"); }
    let handle = app.clone();
    std::thread::spawn(move || {
        // Give lifespan shutdown time to persist interrupted work and close SQLite.
        for _ in 0..100 {
            let state = handle.state::<Backend>();
            if !state.lifetime.is_current(state.generation.load(Ordering::SeqCst)) { break; }
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        if let Some(child) = handle.state::<Backend>().child.lock().unwrap().take() { let _ = child.kill(); }
        handle.exit(0);
    });
}
#[tauri::command]
async fn restart_backend(window: tauri::WebviewWindow, app: tauri::AppHandle) -> Result<(), String> {
    if window.label() != "loading" { return Err("Only the local startup window may restart the service".into()); }
    tauri::async_runtime::spawn_blocking(move || {
        let state = app.state::<Backend>();
        state.lifetime.wait_for_retry(std::time::Duration::from_secs(30), &state.exiting).map_err(|error| match error {
            RetryError::Running => "服务仍在运行。 / Service is still running",
            RetryError::ExitUnconfirmed => "旧服务尚未确认退出，请稍后重试。 / The previous service has not exited. Retry shortly.",
            RetryError::Exiting => "程序正在退出。 / The application is closing",
        }.to_string())?;
        spawn_backend(&app)
    }).await.map_err(|error| error.to_string())?
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
        .manage(GeometryWriter::default())
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
        .invoke_handler(tauri::generate_handler![restart_backend, tray_menu::tray_snapshot, tray_menu::tray_action])
        .setup(|app| {
            let prefs = preferences(app.handle());
            let tray = TrayIconBuilder::with_id("facetmark-tray")
                .icon(app.default_window_icon().unwrap().clone()).tooltip("Facetmark")
                .show_menu_on_left_click(false)
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click { button, button_state: tauri::tray::MouseButtonState::Up, position, .. } = event {
                        match button {
                            tauri::tray::MouseButton::Left => focus_main(tray.app_handle()),
                            tauri::tray::MouseButton::Right => {
                                if let Err(error) = tray_menu::open(tray.app_handle(), position.x, position.y, "right-click") {
                                    tray.app_handle().dialog().message(format!("托盘菜单未能打开。 / Could not open the tray menu: {error}"))
                                        .title("Facetmark").show(|_| {});
                                }
                            },
                            _ => {},
                        }
                    }
                }).build(app)?;
            if cloud_webview_inspection() {
                let handle = app.handle().clone();
                std::thread::spawn(move || {
                    std::thread::sleep(std::time::Duration::from_secs(1));
                    if let Ok(Some(rect)) = tray.rect() {
                        let position = rect.position.to_physical::<f64>(1.);
                        let size = rect.size.to_physical::<u32>(1.);
                        ci_record("tray-icon-native.json", serde_json::json!({
                            "process": std::process::id(), "x": position.x, "y": position.y, "width": size.width, "height": size.height
                        }));
                    }
                    tray_menu::start_ci_inspection(&handle);
                });
            }
            if prefs.shortcut {
                if let Err(error) = app.global_shortcut().register(SHORTCUT) {
                    app.dialog().message(format!("无法注册全局快捷键，可能已被占用。 / Global shortcut unavailable: {error}")).title("Facetmark").show(|_| {});
                }
            }
            if let Err(e) = spawn_backend(app.handle()) { startup_error(app.handle(), &e); }
            Ok(())
        })
        .on_window_event(|win, event| {
            match event {
                tauri::WindowEvent::Focused(false) if win.label() == "tray-menu" => {
                    let _ = win.hide();
                }
                tauri::WindowEvent::Moved(_) | tauri::WindowEvent::Resized(_) if win.label() == "main" => {
                    remember_geometry(win);
                }
                tauri::WindowEvent::CloseRequested { api, .. } => {
                    if win.label() == "main" {
                        api.prevent_close();
                        remember_geometry(win);
                        let app = win.app_handle();
                        flush_geometry(app, true);
                        save_window_mode(app);
                        let mut prefs = preferences(app);
                        if !prefs.tray_notice_seen {
                            app.dialog().message("Facetmark 将在系统托盘继续运行，索引任务不会停止。可在托盘菜单退出。\n\nFacetmark continues in the system tray. Use the tray menu to quit.").title("Facetmark").show(|_| {});
                            prefs.tray_notice_seen = true;
                            update_preferences(app, |saved| saved.tray_notice_seen = prefs.tray_notice_seen);
                        }
                        let _ = win.hide();
                    } else if win.label() == "tray-menu" {
                        api.prevent_close();
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
