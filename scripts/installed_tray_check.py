"""Inspect the packaged tray window and real native actions on a disposable VM."""
from __future__ import annotations

import ctypes
import json
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import Error, expect, sync_playwright

if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
    raise SystemExit("Installed tray checks require a disposable GitHub-hosted Windows runner")

output = Path(sys.argv[1])
process = int(sys.argv[2])
mode = sys.argv[3] if len(sys.argv) > 3 else "operate"
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetDpiForWindow.argtypes = [wintypes.HWND]
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.GetForegroundWindow.restype = wintypes.HWND
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class MonitorInfo(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]


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


def activate_main(hwnd):
    # The native-link smoke leaves a fresh system browser in front. Establish a
    # real foreground main window before the CI-only tray trigger; never show or
    # focus the tray HWND directly, which would mask the application's opening.
    previous = user32.GetForegroundWindow()
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    method = "SetForegroundWindow"
    if user32.GetForegroundWindow() != hwnd:
        message = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        owner = wintypes.DWORD()
        foreground_thread = user32.GetWindowThreadProcessId(previous, ctypes.byref(owner)) if previous else 0
        current_thread = kernel32.GetCurrentThreadId()
        attached = bool(foreground_thread and foreground_thread != current_thread
                        and user32.AttachThreadInput(current_thread, foreground_thread, True))
        try:
            user32.SetForegroundWindow(hwnd)
            method = "temporary foreground input-queue attachment"
        finally:
            if attached:
                user32.AttachThreadInput(current_thread, foreground_thread, False)
    if user32.GetForegroundWindow() != hwnd:
        # Alt releases Windows' foreground lock through actual OS keyboard input.
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        time.sleep(.1)
        user32.SetForegroundWindow(hwnd)
        method = "OS Alt input followed by SetForegroundWindow"
    wait_for(lambda: user32.GetForegroundWindow() == hwnd, "Could not establish the native main foreground", 5)
    activation_history.append({"previous": previous, "foreground": hwnd, "method": method})


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
    activation_history = []
    tray_connection = None

    def cdp_targets():
        try:
            with urlopen("http://127.0.0.1:9223/json/list", timeout=3) as response:
                return json.load(response)
        except (OSError, ValueError) as error:
            return {"error": str(error)}

    def menu_page():
        global tray_connection
        handle = native_window("Facetmark tray")
        if not handle or not user32.IsWindowVisible(handle):
            return None
        connection = tray_connection or browser
        page = next((page for context in connection.contexts for page in context.pages
                     if page.url.endswith("/tray.html")), None)
        if page:
            return page
        # WebView2 exposes a late-created WebView in /json/list without always
        # notifying an existing browser CDP connection. Reconnect only after the
        # actual native HWND and its packaged target both exist. This discovers
        # the installed page; it never creates or navigates a replacement page.
        targets = cdp_targets()
        if tray_connection is None and isinstance(targets, list) and any(
                target.get("url") == "http://tauri.localhost/tray.html"
                and target.get("title") == "Facetmark tray" for target in targets):
            tray_connection = playwright.chromium.connect_over_cdp("http://127.0.0.1:9223", timeout=15000)
            return next((page for context in tray_connection.contexts for page in context.pages
                         if page.url.endswith("/tray.html")), None)
        return None

    def open_menu(*, actual_click=False):
        global sequence
        activate_main(main_handle)
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
                        handle = native_window("Facetmark tray")
                        wait_for(lambda: user32.GetForegroundWindow() == handle, "Native tray did not take the foreground", 5)
                        opening_sources.append("right-click on notification icon")
                        return menu
                    except AssertionError:
                        pass
        # A headless Server desktop may have no usable notification area. The
        # CI-only native trigger still creates and positions the real WebView.
        activate_main(main_handle)
        sequence += 1
        request = output / f"tray-open-request-{process}.json"
        temporary = request.with_suffix(".tmp")
        temporary.write_text(json.dumps({"sequence": sequence}), encoding="utf-8")
        temporary.replace(request)
        wait_for(lambda: (record := read_json(output / "tray-menu-native.json")).get("process") == process
                 and record.get("source") == f"synthetic cloud tray trigger {sequence}",
                 "Native tray trigger did not run")
        try:
            menu = wait_for(menu_page, "Native tray WebView missing")
        except AssertionError:
            handle = native_window("Facetmark tray")
            report("installed-tray-failure.json", {"menu_hwnd": handle,
                "menu_visible": bool(handle and user32.IsWindowVisible(handle)),
                "foreground_hwnd": user32.GetForegroundWindow(), "main_hwnd": main_handle,
                "cdp_pages": [page.url for connection in [browser, tray_connection] if connection
                              for context in connection.contexts for page in context.pages],
                "cdp_targets": cdp_targets(),
                "activation_history": activation_history, "opening_sources": opening_sources})
            raise
        handle = native_window("Facetmark tray")
        wait_for(lambda: user32.GetForegroundWindow() == handle, "Native tray did not take the foreground", 5)
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
            "owned_sidecar_stopped": True, "opening_sources": opening_sources,
            "late_native_target_attached": tray_connection is not None})
    elif mode == "operate":
        handle = native_window("Facetmark tray")
        rect = wintypes.RECT()
        assert user32.GetWindowRect(handle, ctypes.byref(rect))
        assert rect.right > rect.left and rect.bottom > rect.top
        geometry = read_json(output / "tray-menu-native.json")
        assert geometry["process"] == process
        client_rect = wintypes.RECT()
        assert user32.GetClientRect(handle, ctypes.byref(client_rect))
        monitor = MonitorInfo()
        monitor.cbSize = ctypes.sizeof(monitor)
        assert user32.GetMonitorInfoW(user32.MonitorFromWindow(handle, 2), ctypes.byref(monitor))
        measured_geometry = {"x": rect.left, "y": rect.top,
            "width": rect.right - rect.left, "height": rect.bottom - rect.top}
        work_area = {"x": monitor.rcWork.left, "y": monitor.rcWork.top,
            "width": monitor.rcWork.right - monitor.rcWork.left,
            "height": monitor.rcWork.bottom - monitor.rcWork.top}
        report("installed-tray-geometry.json", {"requested_outer": geometry["outer"],
            "measured_outer": measured_geometry,
            "measured_client": {"width": client_rect.right, "height": client_rect.bottom},
            "work_area": work_area, "dpi": user32.GetDpiForWindow(handle)})
        for dimension in ["x", "y", "width", "height"]:
            assert abs(measured_geometry[dimension] - geometry["outer"][dimension]) <= 2, (
                f"Tray outer {dimension} differs: requested {geometry['outer']}, measured {measured_geometry}")
        assert rect.left >= monitor.rcWork.left and rect.top >= monitor.rcWork.top
        assert rect.right <= monitor.rcWork.right and rect.bottom <= monitor.rcWork.bottom, (
            f"Tray frame is outside the monitor work area: {measured_geometry}, {work_area}")
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
        user32.ShowWindow(main_handle, 0)
        assert not user32.IsWindowVisible(main_handle), "Open-workspace regression needs a hidden main window"
        menu.locator('[data-action="show"]').press("Enter")
        wait_for(lambda: user32.IsWindowVisible(main_handle), "Open workspace did not restore the main window")
        wait_for(lambda: not user32.IsWindowVisible(handle), "Open workspace left the menu over the application")
        menu = open_menu()
        activate_main(main_handle)
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
            "measured_outer": measured_geometry, "work_area": work_area, "whole_frame_visible": True,
            "startup_toggled_and_restored": True, "shortcut_toggled_persisted_and_restored": True,
            "real_global_shortcut": True, "open_workspace": True, "escape_hides_menu": True,
            "native_focus_loss_hides_menu": True, "update_opens_desktop_settings": True,
            "remote_tray_actions_denied": remote, "opening_sources": opening_sources,
            "late_native_target_attached": tray_connection is not None,
            "activation_history": activation_history,
            "theme_scope": "WebView media overrides for light/dark and reduced motion", "page_errors": errors})
    else:
        raise SystemExit(f"Unknown tray check mode: {mode}")
