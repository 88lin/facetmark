"""Inspect the packaged tray window and real native actions on a disposable VM."""
from __future__ import annotations

import ctypes
import json
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

from playwright.sync_api import Error, expect, sync_playwright

if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
    raise SystemExit("Installed tray checks require a disposable GitHub-hosted Windows runner")

output = Path(sys.argv[1])
process = int(sys.argv[2])
mode = sys.argv[3] if len(sys.argv) > 3 else "operate"
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetForegroundWindow.restype = wintypes.HWND
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def wait_for(check, message, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            result = check()
        except (FileNotFoundError, json.JSONDecodeError, Error):
            result = None
        if result:
            return result
        time.sleep(.1)
    raise AssertionError(message)


def native_window(title):
    handles = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def collect(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        text = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, text, len(text))
        if owner.value == process and text.value == title:
            handles.append(hwnd)
        return True

    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows(collect, 0)
    return handles[0] if handles else None


def alive(pid):
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        assert kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        return code.value == 259
    finally:
        kernel32.CloseHandle(handle)


def report(name, values):
    (output / name).write_text(json.dumps({"commit": os.environ.get("GITHUB_SHA"),
        "scope": "installed Tauri tray window; disposable CI VM; synthetic library",
        **values}, ensure_ascii=False, indent=2), encoding="utf-8")


with sync_playwright() as playwright:
    browser = playwright.chromium.connect_over_cdp("http://127.0.0.1:9223", timeout=30000)
    main = wait_for(lambda: next((page for context in browser.contexts for page in context.pages
        if page.url.startswith("http://127.0.0.1:") and "/app" in page.url), None), "Installed main WebView missing")
    main_handle = wait_for(lambda: native_window("Facetmark"), "Installed main window missing")
    sequence = 0
    opening_sources = []

    def menu_page():
        handle = native_window("Facetmark tray")
        if not handle or not user32.IsWindowVisible(handle):
            return None
        return next((page for context in browser.contexts for page in context.pages if page.url.endswith("/tray.html")), None)

    def open_menu(*, actual_click=False):
        global sequence
        # Try a real right click on the registered notification icon first.
        if actual_click:
            icon_path = output / "tray-icon-native.json"
            if icon_path.exists():
                icon = read_json(icon_path)
                if icon.get("process") == process and icon.get("width", 0) > 0 and icon.get("height", 0) > 0:
                    user32.SetCursorPos(round(icon["x"] + icon["width"] / 2), round(icon["y"] + icon["height"] / 2))
                    user32.mouse_event(0x0008, 0, 0, 0, 0)
                    user32.mouse_event(0x0010, 0, 0, 0, 0)
                    try:
                        menu = wait_for(menu_page, "Notification area did not expose the tray menu", 8)
                        opening_sources.append("right-click on notification icon")
                        return menu
                    except AssertionError:
                        pass
        # A headless Server desktop may have no usable notification area. The
        # CI-only native trigger still creates and positions the real WebView.
        sequence += 1
        request = output / f"tray-open-request-{process}.json"
        temporary = request.with_suffix(".tmp")
        temporary.write_text(json.dumps({"sequence": sequence}), encoding="utf-8")
        temporary.replace(request)
        wait_for(lambda: (record := read_json(output / "tray-menu-native.json")).get("process") == process
                 and record.get("source") == f"synthetic cloud tray trigger {sequence}",
                 "Native tray trigger did not run")
        menu = wait_for(menu_page, "Native tray WebView missing")
        opening_sources.append("synthetic cloud trigger; actual native window")
        return menu

    menu = open_menu(actual_click=mode == "operate")
    menu.locator(".tray-menu").wait_for()
    menu.evaluate("() => document.fonts.ready")
    errors = []
    menu.on("pageerror", lambda error: errors.append(str(error)))

    if mode == "exit":
        runtime = read_json(Path(os.environ["FACETMARK_DATA_DIR"]) / "desktop-runtime.json")
        try:
            menu.locator('[data-action="exit"]').press("Enter")
        except Error as error:
            if "closed" not in str(error).lower():
                raise
        wait_for(lambda: not alive(process), "Tray Quit did not exit the desktop", 30)
        wait_for(lambda: not alive(runtime["pid"]), "Tray Quit left the owned sidecar alive", 30)
        report("installed-tray-exit.json", {"real_quit_button": True, "desktop_stopped": True,
            "owned_sidecar_stopped": True, "opening_sources": opening_sources})
    elif mode == "operate":
        handle = native_window("Facetmark tray")
        rect = wintypes.RECT()
        assert user32.GetWindowRect(handle, ctypes.byref(rect))
        assert rect.right > rect.left and rect.bottom > rect.top
        geometry = read_json(output / "tray-menu-native.json")
        assert geometry["process"] == process
        assert abs((rect.right - rect.left) - geometry["outer"]["width"]) <= 2
        assert abs((rect.bottom - rect.top) - geometry["outer"]["height"]) <= 2
        def snapshot():
            return menu.evaluate("() => window.__TAURI_INTERNALS__.invoke('tray_snapshot')")

        initial = snapshot()
        for action in ["startup", "shortcut"]:
            item = menu.locator(f'[data-action="{action}"]')
            expect(item).to_have_attribute("aria-checked", str(initial[action]).lower())
            item.press("Space")
            expect(item).to_have_attribute("aria-checked", str(not initial[action]).lower())
            assert snapshot()[action] is not initial[action]
            item.press("Enter")
            expect(item).to_have_attribute("aria-checked", str(initial[action]).lower())
            assert snapshot()[action] is initial[action]
        metadata = read_json(output / "native-window.json")
        assert read_json(metadata["preferences_path"])["shortcut"] is initial["shortcut"]
        remote = main.evaluate("""async () => {
            if (!window.__TAURI_INTERNALS__) return 'no native bridge';
            try { await window.__TAURI_INTERNALS__.invoke('tray_action', { action: 'exit' }); return 'ALLOWED'; }
            catch (error) { return String(error); }
        }""")
        assert remote != "ALLOWED" and alive(process), "Remote workbench acquired tray Quit privilege"
        for theme in ["light", "dark"]:
            menu.emulate_media(color_scheme=theme)
            menu.locator('[data-action="exit"]').focus()
            expect(menu.locator('[data-action="exit"]')).to_be_in_viewport(ratio=1)
            menu.screenshot(path=str(output / f"installed-tray-{theme}.png"))
        menu.emulate_media(reduced_motion="reduce")
        assert menu.locator(".tray-shell").evaluate("el => getComputedStyle(el).animationName") == "none"
        menu.keyboard.press("Escape")
        wait_for(lambda: not user32.IsWindowVisible(handle), "Escape did not hide the native tray window")
        menu = open_menu()
        menu.locator('[data-action="show"]').press("Enter")
        wait_for(lambda: user32.IsWindowVisible(main_handle), "Open workspace did not restore the main window")
        wait_for(lambda: not user32.IsWindowVisible(handle), "Open workspace left the menu over the application")
        menu = open_menu()
        user32.SetForegroundWindow(main_handle)
        wait_for(lambda: not user32.IsWindowVisible(handle), "Losing native focus did not hide the tray menu")
        menu = open_menu()
        menu.locator('[data-action="update"]').press("Enter")
        expect(main.locator("#settings-tab-desktop")).to_have_attribute("aria-selected", "true")
        expect(main.locator("#settings-panel-desktop")).to_be_visible()
        # The real registered OS hotkey, rather than a DOM keydown event.
        menu = open_menu()
        if not snapshot()["shortcut"]:
            menu.locator('[data-action="shortcut"]').press("Space")
            expect(menu.locator('[data-action="shortcut"]')).to_have_attribute("aria-checked", "true")
        menu.keyboard.press("Escape")
        user32.ShowWindow(main_handle, 0)
        for key in [0x11, 0x10, 0x20]:
            user32.keybd_event(key, 0, 0, 0)
        for key in [0x20, 0x10, 0x11]:
            user32.keybd_event(key, 0, 2, 0)
        wait_for(lambda: user32.IsWindowVisible(main_handle), "Actual global shortcut did not restore the desktop")
        if not initial["shortcut"]:
            menu = open_menu()
            menu.locator('[data-action="shortcut"]').press("Space")
            expect(menu.locator('[data-action="shortcut"]')).to_have_attribute("aria-checked", "false")
            menu.keyboard.press("Escape")
        menu.emulate_media(color_scheme="null", reduced_motion="null")
        assert not errors
        report("installed-tray.json", {"native_geometry": geometry, "initial_state": initial,
            "startup_toggled_and_restored": True, "shortcut_toggled_persisted_and_restored": True,
            "real_global_shortcut": True, "open_workspace": True, "escape_hides_menu": True,
            "native_focus_loss_hides_menu": True, "update_opens_desktop_settings": True,
            "remote_tray_actions_denied": remote, "opening_sources": opening_sources,
            "theme_scope": "WebView media overrides for light/dark and reduced motion", "page_errors": errors})
    else:
        raise SystemExit(f"Unknown tray check mode: {mode}")
