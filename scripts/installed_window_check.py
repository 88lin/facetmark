"""Exercise startup retry and physical window persistence on the installed CI app."""
from __future__ import annotations

import ctypes
import json
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

from playwright.sync_api import Error, sync_playwright

if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
    raise SystemExit("Installed window checks require a disposable GitHub-hosted Windows runner")

output = Path(sys.argv[1])
mode = sys.argv[2]
process = int(sys.argv[3])
output.mkdir(parents=True, exist_ok=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetDpiForWindow.argtypes = [wintypes.HWND]
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def report(name, values):
    (output / name).write_text(json.dumps({"commit": os.environ.get("GITHUB_SHA"),
        "scope": "installed app; disposable CI VM; synthetic library", **values},
        ensure_ascii=False, indent=2), encoding="utf-8")


def wait_for(check, message, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            result = check()
        except (FileNotFoundError, json.JSONDecodeError):
            result = None
        if result:
            return result
        time.sleep(.1)
    raise AssertionError(message)


def running(pid):
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        assert kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        return code.value == 259
    finally:
        kernel32.CloseHandle(handle)


def installed_page(playwright, *, splash=False):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            browser = playwright.chromium.connect_over_cdp("http://127.0.0.1:9223", timeout=2500)
            for context in browser.contexts:
                for page in context.pages:
                    if splash and page.locator("#retry").count():
                        return page
                    if not splash and page.url.startswith("http://127.0.0.1:") and "/app" in page.url:
                        page.locator("#root .app-shell").wait_for(timeout=15000)
                        return page
        except Error:
            pass
        time.sleep(.25)
    raise AssertionError("Installed WebView never reached the expected startup/workspace page")


def window_handle():
    handles = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def collect(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, len(title))
        if owner.value == process and title.value == "Facetmark" and user32.IsWindowVisible(hwnd):
            handles.append(hwnd)
        return True

    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows(collect, 0)
    return handles[0] if handles else None


def rectangle(hwnd):
    rect = wintypes.RECT()
    assert user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return {"x": rect.left, "y": rect.top, "width": rect.right - rect.left, "height": rect.bottom - rect.top}


def work_area(hwnd):
    class MonitorInfo(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("monitor", wintypes.RECT),
                    ("work", wintypes.RECT), ("flags", wintypes.DWORD)]
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(info)
    assert user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info))
    rect = info.work
    return {"x": rect.left, "y": rect.top, "width": rect.right - rect.left, "height": rect.bottom - rect.top}


def writes():
    path = output / "geometry-writes.jsonl"
    if not path.exists():
        return []
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [record for record in records if record["process"] == process]


def window_metadata():
    path = output / "native-window.json"
    if not path.exists():
        return None
    metadata = read_json(path)
    return metadata if metadata["process"] == process else None


if mode == "startup":
    failure = wait_for(lambda: read_json(output / "startup-failure-injected.json")
                       if (output / "startup-failure-injected.json").exists() else None,
                       "The CI workspace failure was not injected after sidecar readiness", 60)
    assert failure["process"] == process
    assert failure["sidecar_pid"], "Failure evidence did not identify its ready sidecar"
    wait_for(lambda: not running(failure["sidecar_pid"]), "Failed workspace left its sidecar alive")
    with sync_playwright() as playwright:
        page = installed_page(playwright, splash=True)
        page.locator("#retry").wait_for(state="visible")
        assert "construction failure" in page.locator("#hint").inner_text()
        page.screenshot(path=str(output / "installed-startup-failure.png"))
        try:
            page.locator("#retry").press("Enter")
        except Error as error:
            if "closed" not in str(error).lower():
                raise
        restored = installed_page(playwright)
        assert restored.locator("#root .app-shell").is_visible()
    report("installed-startup-retry.json", {"failure_after_ready": True, "failed_sidecar_stopped": True,
        "real_keyboard_retry": True, "workspace_recovered": True, "failed_sidecar": failure["sidecar_pid"]})
elif mode == "prepare":
    metadata = wait_for(window_metadata, "No current native-window evidence")
    hwnd = wait_for(window_handle, "Installed main window missing")
    area = work_area(hwnd)
    before = len(writes())
    width, height = min(960, area["width"]), min(680, area["height"])
    y = area["y"] + max(0, min(50, area["height"] - height))
    for tick in range(240):
        assert user32.SetWindowPos(hwnd, None, area["x"] + tick % 19, y + tick % 7,
                                   width - tick % 13, height - tick % 9, 0x14)
    wait_for(lambda: len(writes()) > before, "Quiet drag was never persisted")
    drag_writes = len(writes()) - before
    assert drag_writes <= 2, f"240 changing drag/resize calls produced {drag_writes} writes"
    # Save a real outer frame with only one pixel inside the monitor. WM_CLOSE
    # exercises the app's own final flush and tray behavior.
    assert user32.SetWindowPos(hwnd, None, area["x"] + area["width"] - 1, y, width, height, 0x14)
    saved = rectangle(hwnd)
    assert abs(saved["x"] - (area["x"] + area["width"] - 1)) <= 1
    assert user32.PostMessageW(hwnd, 0x10, 0, 0)
    wait_for(lambda: not user32.IsWindowVisible(hwnd), "Closing the main window did not hide it")
    preference_path = Path(metadata["preferences_path"])
    wait_for(lambda: read_json(preference_path).get("window") == saved,
             "Close did not flush the final physical outer frame")
    report("installed-window-before-restart.json", {"process": process, "saved": saved, "work_area": area,
        "dpi": user32.GetDpiForWindow(hwnd), "scale_factor": metadata["scale_factor"],
        "changing_native_calls": 240, "drag_writes": drag_writes, "close_flushed_latest": True})
elif mode == "restored":
    previous = read_json(output / "installed-window-before-restart.json")
    metadata = wait_for(window_metadata, "Relaunch did not record the new native window", 60)
    hwnd = wait_for(window_handle, "Relaunched main window missing", 60)
    actual = rectangle(hwnd)
    saved = previous["saved"]
    area = work_area(hwnd)
    assert abs(actual["width"] - saved["width"]) <= 2 and abs(actual["height"] - saved["height"]) <= 2, (saved, actual)
    assert actual["x"] >= area["x"] - 1 and actual["y"] >= area["y"] - 1
    assert actual["x"] + actual["width"] <= area["x"] + area["width"] + 1
    assert actual["y"] + actual["height"] <= area["y"] + area["height"] + 1
    assert abs(actual["x"] - (area["x"] + area["width"] - actual["width"])) <= 2
    assert abs(actual["y"] - saved["y"]) <= 2
    with sync_playwright() as playwright:
        page = installed_page(playwright)
        page.locator(".result-row").first.wait_for(timeout=15000)
        page.evaluate("() => document.fonts.ready")
        page.screenshot(path=str(output / "installed-window-restored.png"))
    report("installed-window-restored.json", {"actual": actual, "saved": saved, "work_area": area,
        "dpi": user32.GetDpiForWindow(hwnd), "scale_factor": metadata["scale_factor"],
        "physical_outer_size_retained": True, "whole_frame_visible": True,
        "position_clamped_without_recentering": True,
        "other_dpi_and_removed_monitor_scope": "Rust pure regression cases; not a second physical CI monitor"})
else:
    raise SystemExit(f"Unknown installed window check: {mode}")
