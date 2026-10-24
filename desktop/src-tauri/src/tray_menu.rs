//! Styled native tray window; privileged actions are limited to this local page.
use super::{ci_record, cloud_webview_inspection, display_areas, focus_main, preferences, request_exit, update_preferences, work_areas, Backend, CI_BROWSER_ARGS, SHORTCUT};
use crate::window_state::{client_size_for_outer, tray_menu_geometry};
use serde::Serialize;
use std::sync::atomic::Ordering;
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_autostart::ManagerExt;
use tauri_plugin_global_shortcut::GlobalShortcutExt;

fn record_window_event(app: &tauri::AppHandle, details: serde_json::Value) {
    if !cloud_webview_inspection() { return; }
    let Some(directory) = std::env::var_os("FACETMARK_CI_EVIDENCE_DIR") else { return; };
    use std::io::Write;
    if let Ok(mut file) = std::fs::OpenOptions::new().create(true).append(true)
        .open(std::path::PathBuf::from(directory).join("tray-window-events.jsonl")) {
        let time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_millis();
        let menu = app.get_webview_window("tray-menu");
        let mut record = serde_json::json!({ "process": std::process::id(), "time_ms": time, "details": details,
            "menu_url": menu.as_ref().and_then(|window| window.url().ok()).map(|url| url.to_string()) });
        #[cfg(windows)]
        {
            use windows_sys::Win32::UI::WindowsAndMessaging::GetForegroundWindow;
            record["menu_hwnd"] = serde_json::json!(menu.and_then(|window| window.hwnd().ok()).map(|hwnd| hwnd.0 as usize));
            record["foreground_hwnd"] = serde_json::json!(unsafe { GetForegroundWindow() } as usize);
        }
        let _ = writeln!(file, "{}", record);
    }
}
pub fn focus_changed(window: &tauri::Window, focused: bool) {
    record_window_event(window.app_handle(), serde_json::json!({ "event": "focus", "focused": focused,
        "visible_before": window.is_visible().ok() }));
    if !focused { let _ = window.hide(); }
}

fn packaged_tray_url(url: &tauri::Url) -> bool {
    url.path() == "/tray.html" && ((matches!(url.scheme(), "http" | "https") && url.host_str() == Some("tauri.localhost"))
        || (url.scheme() == "tauri" && url.host_str() == Some("localhost")))
}
fn check_window(window: &tauri::WebviewWindow) -> Result<(), String> {
    if window.label() != "tray-menu" || !packaged_tray_url(&window.url().map_err(|error| error.to_string())?) {
        return Err("Only the packaged tray menu may use native tray actions".into());
    }
    Ok(())
}
#[derive(Serialize)]
pub struct TraySnapshot { startup: bool, shortcut: bool, ready: bool }
fn snapshot(app: &tauri::AppHandle) -> Result<TraySnapshot, String> {
    Ok(TraySnapshot { startup: app.autolaunch().is_enabled().map_err(|error| error.to_string())?,
        shortcut: app.global_shortcut().is_registered(SHORTCUT), ready: app.state::<Backend>().ready.load(Ordering::SeqCst) })
}
pub fn hide(app: &tauri::AppHandle) {
    if let Some(menu) = app.get_webview_window("tray-menu") { let _ = menu.hide(); }
}
#[tauri::command]
pub fn tray_snapshot(window: tauri::WebviewWindow, app: tauri::AppHandle) -> Result<TraySnapshot, String> {
    check_window(&window)?;
    snapshot(&app)
}
#[tauri::command]
pub fn tray_action(window: tauri::WebviewWindow, app: tauri::AppHandle, action: String) -> Result<TraySnapshot, String> {
    check_window(&window)?;
    match action.as_str() {
        "show" => { hide(&app); focus_main(&app); },
        "startup" => {
            let enabled = app.autolaunch().is_enabled().map_err(|error| error.to_string())?;
            let result = if enabled { app.autolaunch().disable() } else { app.autolaunch().enable() };
            result.map_err(|error| error.to_string())?;
        },
        "shortcut" => {
            let enabled = app.global_shortcut().is_registered(SHORTCUT);
            let result = if enabled { app.global_shortcut().unregister(SHORTCUT) } else { app.global_shortcut().register(SHORTCUT) };
            result.map_err(|error| error.to_string())?;
            update_preferences(&app, |prefs| prefs.shortcut = !enabled);
        },
        "update" => {
            hide(&app);
            if let Some(main) = app.get_webview_window("main") { main.eval("window.location.hash = 'settings/desktop'").map_err(|error| error.to_string())?; }
            focus_main(&app);
        },
        "exit" => { hide(&app); request_exit(&app); },
        "dismiss" => hide(&app),
        _ => return Err("Unknown tray action".into()),
    }
    snapshot(&app)
}

pub fn open(app: &tauri::AppHandle, x: f64, y: f64, source: &str) -> tauri::Result<()> {
    let Some((geometry, scale)) = tray_menu_geometry(x, y, &display_areas(app)) else { return Ok(()); };
    let menu = if let Some(menu) = app.get_webview_window("tray-menu") { menu } else {
        let navigation_app = app.clone();
        let mut builder = WebviewWindowBuilder::new(app, "tray-menu", WebviewUrl::App("tray.html".into()))
            // Hidden construction must not focus the WebView. Its queued
            // GotFocus/LostFocus events can otherwise arrive after show().
            // The one explicit focus request belongs to the visible opening.
            .title("Facetmark tray").inner_size(312., 374.).visible(false).focused(false).decorations(false)
            // Alpha is only for the menu's rounded corners. A native shadow
            // adds a second translucent frame around the opaque menu surface.
            .resizable(false).skip_taskbar(true).always_on_top(true).transparent(true).shadow(false)
            .on_navigation(move |url| {
                let allowed = packaged_tray_url(url);
                record_window_event(&navigation_app, serde_json::json!({ "event": "navigation", "url": url.as_str(), "allowed": allowed }));
                allowed
            })
            .on_page_load(|window, payload| {
                record_window_event(window.app_handle(), serde_json::json!({ "event": "page-load", "url": payload.url().as_str(),
                    "phase": format!("{:?}", payload.event()) }));
            })
            .on_new_window(|_, _| tauri::webview::NewWindowResponse::Deny);
        if cloud_webview_inspection() { builder = builder.additional_browser_args(CI_BROWSER_ARGS); }
        builder.build()?
    };
    menu.set_position(tauri::PhysicalPosition::new(geometry.x, geometry.y))?;
    // set_size takes the client area. Undecorated Windows shadows still have
    // native frame offsets, so measure them at the target monitor's DPI before
    // fitting the entire outer frame to the available work area.
    let (outer, inner) = (menu.outer_size()?, menu.inner_size()?);
    let client = client_size_for_outer(geometry, (outer.width, outer.height), (inner.width, inner.height));
    menu.set_size(tauri::PhysicalSize::new(client.0, client.1))?;
    menu.set_position(tauri::PhysicalPosition::new(geometry.x, geometry.y))?;
    // Reset roving focus and reread real plugin state on every open. The script
    // also loads its state on first parse if this eval arrives before it.
    let _ = menu.eval("if (window.openFacetmarkTray) window.openFacetmarkTray()");
    menu.show()?;
    menu.set_focus()?;
    record_window_event(app, serde_json::json!({ "event": "open", "source": source,
        "visible": menu.is_visible().ok() }));
    ci_record("tray-menu-native.json", serde_json::json!({ "process": std::process::id(),
        "source": source, "outer": geometry, "scale_factor": scale, "preference_shortcut": preferences(app).shortcut }));
    Ok(())
}

/// Disposable Windows runners may lack an interactive notification area. This
/// explicit CI-only trigger opens the same native window, never granting IPC to
/// the remote workbench. Evidence records that its opening was synthetic.
pub fn start_ci_inspection(app: &tauri::AppHandle) {
    if !cloud_webview_inspection() || std::env::var("FACETMARK_CI_TRAY_INSPECT").as_deref() != Ok("1") { return; }
    let Some(directory) = std::env::var_os("FACETMARK_CI_EVIDENCE_DIR") else { return; };
    let request = std::path::PathBuf::from(directory).join(format!("tray-open-request-{}.json", std::process::id()));
    let handle = app.clone();
    std::thread::spawn(move || {
        let mut previous = 0;
        for _ in 0..4000 {
            if handle.state::<Backend>().exiting.load(Ordering::SeqCst) { break; }
            if let Some(record) = std::fs::read(&request).ok().and_then(|bytes| serde_json::from_slice::<serde_json::Value>(&bytes).ok()) {
                let sequence = record["sequence"].as_u64().unwrap_or(0);
                if sequence > previous {
                    previous = sequence;
                    let app = handle.clone();
                    let _ = handle.run_on_main_thread(move || {
                        if record["action"].as_str() == Some("hide-main") {
                            if let Some(main) = app.get_webview_window("main") {
                                // Test preparation must use the same window API
                                // as CloseRequested. A raw Win32 SW_HIDE bypasses
                                // Tao's cached VISIBLE flag and invalidates show().
                                let result = main.hide();
                                ci_record("tray-main-hide-native.json", serde_json::json!({
                                    "process": std::process::id(), "sequence": sequence,
                                    "api": "Tauri Window.hide; same API as main CloseRequested",
                                    "visible": main.is_visible().ok(),
                                    "error": result.err().map(|error| error.to_string())
                                }));
                            }
                            return;
                        }
                        let areas = work_areas(&app);
                        if let Some(area) = areas.first() {
                            let x = record["x"].as_f64().unwrap_or(f64::from(area.x) + f64::from(area.width) - 12.);
                            let y = record["y"].as_f64().unwrap_or(f64::from(area.y) + f64::from(area.height) + 8.);
                            let _ = open(&app, x, y, &format!("synthetic cloud tray trigger {sequence}"));
                        }
                    });
                }
            }
            std::thread::sleep(std::time::Duration::from_millis(150));
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn only_the_packaged_tray_origin_is_allowed() {
        for url in ["http://tauri.localhost/tray.html", "https://tauri.localhost/tray.html", "tauri://localhost/tray.html"] {
            assert!(packaged_tray_url(&url.parse().unwrap()));
        }
        for url in ["http://127.0.0.1:8791/app", "https://example.com/tray.html", "http://tauri.localhost/index.html", "file:///tray.html"] {
            assert!(!packaged_tray_url(&url.parse().unwrap()));
        }
    }
}
