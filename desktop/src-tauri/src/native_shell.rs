//! Keep the official sidecar lifecycle without the shell plugin's legacy web APIs.
//!
//! Shell 2.4 injects a body click handler that cancels `_blank` links before trying
//! an IPC call. Our remote workbench intentionally has no shell IPC permission.
//! Delegate its Rust setup/exit hooks, leaving web APIs and initialization scripts
//! at the Plugin trait defaults. Native navigation handlers own external links.

use tauri::{plugin::Plugin, AppHandle, RunEvent, Runtime};

struct NativeShell<R: Runtime>(Box<dyn Plugin<R>>);

impl<R: Runtime> Plugin<R> for NativeShell<R> {
    fn name(&self) -> &'static str {
        self.0.name()
    }

    fn initialize(
        &mut self,
        app: &AppHandle<R>,
        config: serde_json::Value,
    ) -> Result<(), Box<dyn std::error::Error>> {
        self.0.initialize(app, config)
    }

    fn on_event(&mut self, app: &AppHandle<R>, event: &RunEvent) {
        self.0.on_event(app, event);
    }
}

pub fn init<R: Runtime>() -> impl Plugin<R> {
    NativeShell(Box::new(tauri_plugin_shell::init::<R>()))
}
