"""Drive the actual unpacked extension in Actions, with a disposable Chromium profile."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from contextlib import suppress
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:8793"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".extension-build/evidence"


def server(path: str = "/_test/state", data: dict | None = None) -> dict:
    request = Request(BASE + path, data=json.dumps(data).encode() if data is not None else None,
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def until(page, predicate, message: str, seconds: float = 10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        page.wait_for_timeout(50)
    raise AssertionError(message)


def calls(path: str) -> list[dict]:
    return [entry for entry in server()["requests"] if entry["path"] == path]


def saved_row(bid: int) -> dict:
    return next(row for row in server()["bookmarks"] if row["id"] == bid)


def storage(page, key: str):
    return page.evaluate("async key => (await chrome.storage.local.get({[key]: []}))[key]", key)


def lose_response(worker, path: str, before_server: bool = False):
    worker.evaluate("""({path, before}) => {
      const transport = globalThis.fetch; let used = false;
      globalThis.fetch = async (...args) => {
        if (!used && new URL(String(args[0])).pathname === path) {
          used = true;
          if (!before) { const response = await transport(...args); await response.text(); }
          throw new TypeError('Synthetic dropped original response');
        }
        return transport(...args);
      };
    }""", {"path": path, "before": before_server})


def language(page, value: str):
    if page.evaluate("document.documentElement.lang").startswith(value):
        return
    page.locator("[data-lang-toggle]").click()
    assert page.evaluate("document.documentElement.lang").startswith(value)


def capture(page, name: str):
    page.evaluate("document.fonts.ready")
    widths = page.evaluate("""() => ({viewport: innerWidth, document: document.documentElement.scrollWidth,
      main: document.querySelector('main')?.scrollWidth ?? document.body.scrollWidth})""")
    assert widths["document"] <= widths["viewport"] + 1, widths
    page.screenshot(path=str(EVIDENCE / f"{name}.png"), full_page=True)


def review(context, worker, report: dict):
    extension_id = worker.url.split("/")[2]
    root = f"chrome-extension://{extension_id}"
    options = context.new_page()
    options.goto(root + "/options.html")
    expect(options.locator("#endpoint")).to_be_enabled()
    assert options.locator("#token").get_attribute("type") == "password"
    token = server()["token"]
    options.locator("#endpoint").fill(BASE)
    options.locator("#token").fill(token)
    options.locator("#token").press("Enter")
    expect(options.locator("#state")).to_contain_text("已连接")
    options.locator("#show-token").click()
    assert options.locator("#token").get_attribute("type") == "text"
    options.locator("#show-token").click()
    assert options.locator("#token").get_attribute("type") == "password"
    options.locator("#channelB").check()
    expect(options.locator("#state")).to_contain_text("已允许")
    assert options.evaluate("chrome.permissions.contains({origins:['http://*/*','https://*/*']})")
    report["scenarios"].append("real options startup, Enter save, token visibility and granted optional permission")

    def popup():
        page = context.new_page()
        page.goto(root + "/popup.html")
        expect(page.locator("#q")).to_be_visible()
        return page

    search = popup()
    search.locator("#q").fill("Original")
    expect(search.locator("#results a").first).to_be_visible()
    expect(search.locator("li.more button")).to_be_visible()
    opened = len(calls("/open"))
    pages = len(context.pages)
    search.locator("#q").evaluate("el => el.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter',isComposing:true,bubbles:true}))")
    assert len(context.pages) == pages and len(calls("/open")) == opened
    server("/_test/flags", {"delay_search": True})
    search.locator("li.more button").click(click_count=2)
    search.locator("[data-lang-toggle]").click()
    until(search, lambda: any(entry["body"].get("offset") == 20 for entry in calls("/search")), "next page not sent")
    expect(search.locator("#results a")).to_have_count(40)
    more = [entry["body"] for entry in calls("/search") if entry["body"].get("offset") == 20]
    first = next(entry["body"] for entry in calls("/search") if entry["body"].get("offset", 0) == 0)
    assert len(more) == 1 and more[0]["depth"] > 0 and first["q"] == more[0]["q"]
    language(search, "zh")
    server("/_test/flags", {})
    search.locator("#q").fill("slow")
    until(search, lambda: any(entry["query"].startswith("q=slow") for entry in calls("/quick")), "slow request not sent")
    search.locator("#q").fill("")
    until(search, lambda: server()["finished_quick"] > 0, "slow response did not finish")
    expect(search.locator("#results a")).to_have_count(0)
    assert search.locator("#q").input_value() == ""
    search.locator("#q").fill("Original")
    expect(search.locator("#results a").first).to_be_visible()
    capture(search, "extension-popup-results")
    report["scenarios"].append("real search, two-stage paging, double click, language switch, IME Enter and clear during a late response")
    first_url = search.locator("#results a").first.get_attribute("href")
    opened = len(calls("/open"))
    with context.expect_page() as opened_page:
        search.locator("#q").press("Enter")
    original_page = opened_page.value
    original_page.wait_for_url(first_url)
    until(options, lambda: len(calls("/open")) == opened + 1, "native popup closing lost the opening record")
    assert calls("/open")[-1]["body"]["query"] == "Original"
    report["scenarios"].append("normal keyboard Enter opens the original URL and the worker retains its opening record")
    search = popup()

    website = context.new_page()
    website.goto(BASE + "/fixture/page/90")
    page = popup()
    tab_id = page.evaluate("async url => (await chrome.tabs.query({url}))[0].id", website.url)
    page.evaluate("id => chrome.tabs.update(id,{active:true})", tab_id)
    assert page.evaluate("async () => (await chrome.tabs.query({active:true,currentWindow:true}))[0].url") == website.url
    before = len(calls("/bookmark"))
    lose_response(worker, "/bookmark")
    page.locator("#save").click(click_count=2)
    expect(page.locator("#save-recovery")).to_be_visible()
    expect(page.locator("#save-status")).to_contain_text("无法连接")
    original = storage(options, "save-deliveries")[0]
    assert len(calls("/bookmark")) == before + 1
    assert calls("/bookmark")[-1]["body"] == original["body"]
    bid = next(row["id"] for row in server()["bookmarks"] if row["url"] == website.url)
    server("/_test/edit", {"bookmark_id": bid, "delete": True})
    options.reload()
    expect(options.locator("#pending-panel")).to_be_visible()
    options.locator("#confirm").click()
    expect(options.locator("#pending-panel")).to_be_hidden()
    assert len(calls("/bookmark")) == before + 1
    assert not any(row["id"] == bid for row in server()["bookmarks"])
    report["scenarios"].append("popup double save with a real accepted response dropped, refresh and read-only confirmation after deletion")

    page = popup()
    page.evaluate("id => chrome.tabs.update(id,{active:true})", tab_id)
    lose_response(worker, "/bookmark", before_server=True)
    page.locator("#save").click()
    expect(page.locator("#save-recovery")).to_be_visible()
    original = storage(options, "save-deliveries")[0]
    website.goto(BASE + "/fixture/page/91")
    options.reload()
    expect(options.locator("#pending-panel")).to_be_visible()
    options.locator("#confirm").click()
    expect(options.locator("#state")).to_contain_text("尚未查到")
    options.locator(".pending-result summary").click()
    options.locator("[data-retry-save]").click()
    expect(options.locator("#pending-panel")).to_be_hidden()
    assert calls("/bookmark")[-1]["body"] == original["body"]
    assert len(calls("/bookmark")) == before + 2
    report["scenarios"].append("unaccepted save, read-only absence check and explicit original retry after changing the active website")

    queued = server("/_test/queue", {})
    options.locator("#drain").click()
    expect(options.locator("#state")).to_contain_text("已处理 1")
    row = saved_row(queued["bookmark_id"])
    assert row["queue_state"] == "done" and "Browser extracted paragraph" in row["body_text"]
    until(options, lambda: not any(tab["url"] == queued["url"] for tab in options.evaluate("chrome.tabs.query({})")), "temporary reading tab left behind")
    completion = calls("/queue/complete")[-1]["body"]
    assert completion["source_url"] == queued["url"] and completion["lease_id"] and completion["request_id"]
    report["scenarios"].append("real temporary tab, injected extraction, original lease acknowledgement and tab cleanup")

    queued = server("/_test/queue", {})
    completions = len(calls("/queue/complete"))
    lose_response(worker, "/queue/complete")
    options.locator("#drain").click()
    expect(options.locator("#pending-panel")).to_be_visible()
    assert storage(options, "fetch-deliveries")[0]["body"]["body"] == saved_row(queued["bookmark_id"])["body_text"]
    server("/_test/edit", {"bookmark_id": queued["bookmark_id"], "body": "Later original reading text remains saved"})
    options.locator("#confirm").click()
    expect(options.locator("#pending-panel")).to_be_hidden()
    assert len(calls("/queue/complete")) == completions + 1
    assert saved_row(queued["bookmark_id"])["body_text"] == "Later original reading text remains saved"
    report["scenarios"].append("accepted browser text response lost, durable original body and read-only confirmation preserving later text")

    queued = server("/_test/queue", {"delay": True})
    completions = len(calls("/queue/complete"))
    options.locator("#drain").click()
    until(options, lambda: any(tab["url"] == queued["url"] for tab in options.evaluate("chrome.tabs.query({})")), "reading tab did not open")
    expect(options.locator("#paused")).to_be_enabled()
    options.locator("#paused").check()
    until(options, lambda: saved_row(queued["bookmark_id"])["queue_state"] == "pending", "paused lease not released")
    assert saved_row(queued["bookmark_id"])["attempts"] == 0
    assert len(calls("/queue/complete")) == completions
    until(options, lambda: not any(tab["url"] == queued["url"] for tab in options.evaluate("chrome.tabs.query({})")), "pause left the temporary tab open")
    expect(options.locator("#drain")).to_be_enabled()
    assert options.evaluate("chrome.permissions.remove({origins:['http://*/*','https://*/*']})")
    leases = len(calls("/queue/next"))
    options.locator("#paused").uncheck()
    expect(options.locator("#drain")).to_be_enabled()
    options.locator("#drain").click()
    expect(options.locator("#state")).to_contain_text("访问权限")
    assert len(calls("/queue/next")) == leases
    assert saved_row(queued["bookmark_id"])["queue_state"] == "pending"
    options.locator("#channelB").uncheck()
    expect(options.locator("#drain")).to_be_enabled()
    report["scenarios"].append("pause while the real tab is loading, exact lease release without spending an attempt and revoked permissions before leasing")
    options.locator("#channelB").check()
    expect(options.locator("#state")).to_contain_text("已允许")
    server("/_test/flags", {"queue_failure": True})
    options.locator("#drain").click()
    expect(options.locator("#state")).to_contain_text("Synthetic queue service unavailable")
    assert "没有可抓取" not in options.locator("#state").inner_text()
    server("/_test/flags", {})
    options.locator("#channelB").uncheck()
    expect(options.locator("#drain")).to_be_enabled()
    report["scenarios"].append("manual queue HTTP failure is displayed as failure rather than no ready pages")

    stale = context.new_page()
    stale.goto(root + "/options.html")
    expect(stale.locator("#save")).to_be_enabled()
    options.locator("#token").fill("synthetic-other-token")
    options.locator("#save").click()
    expect(options.locator("#save")).to_be_enabled()
    stale.locator("#endpoint").fill(BASE + "/unsaved-path")
    stale.locator("#save").click()
    expect(stale.locator("#state")).to_contain_text("其他窗口")
    assert stale.evaluate("async () => (await chrome.storage.local.get('endpoint')).endpoint") == BASE
    stale.once("dialog", lambda dialog: dialog.accept())
    stale.locator("#reload-settings").click()
    expect(stale.locator("#token")).to_have_value("synthetic-other-token")
    stale.locator("#token").fill(token)
    stale.locator("#save").click()
    expect(stale.locator("#state")).to_contain_text("已连接")
    options.reload()
    expect(options.locator("#save")).to_be_enabled()
    report["scenarios"].append("two real options windows reject stale writes and reload the changed settings before another explicit save")

    result = options.evaluate("""async () => chrome.runtime.sendMessage({type:'save-page',body:{
      url:'http://127.0.0.1:8793/fixture/page/99',title:'原保存内容与长标题 Original saved content '.repeat(10),
      folder:'需要长期保存与反复核对的原文件夹 / Original folder',tags:['原标签 original tag']}})""")
    assert result["ok"] is True
    lose_response(worker, "/bookmark", before_server=True)
    result = options.evaluate("""async () => chrome.runtime.sendMessage({type:'save-page',body:{
      url:'http://127.0.0.1:8793/fixture/page/98',title:'原保存内容与长标题 Original saved content '.repeat(10),
      folder:'需要长期保存与反复核对的原文件夹 / Original folder',tags:['原标签 original tag']}})""")
    assert result["ok"] is False
    until(options, lambda: options.locator(".pending-result").count() == 1, "pending long title not displayed")
    options.locator(".pending-result summary").click()
    for lang, theme, width, height in [("zh", "light", 1280, 850), ("en", "dark", 1024, 768),
                                       ("zh", "dark", 320, 640), ("en", "light", 683, 384)]:
        options.set_viewport_size({"width": width, "height": height})
        options.emulate_media(color_scheme=theme, reduced_motion="reduce")
        language(options, lang)
        options.locator("#endpoint").focus()
        options.keyboard.press("Tab")
        assert options.evaluate("document.activeElement.id") == "token"
        assert options.locator("#token").get_attribute("type") == "password"
        assert options.locator("#save").evaluate("el => getComputedStyle(el).transitionDuration") == "0s"
        capture(options, f"extension-options-{lang}-{theme}-{width}-{height}")
    search.set_viewport_size({"width": 320, "height": 600})
    search.emulate_media(color_scheme="dark", reduced_motion="reduce")
    language(search, "zh")
    search.locator("#q").fill("Original")
    expect(search.locator("#results a").first).to_be_visible()
    capture(search, "extension-popup-zh-dark-320")
    report["scenarios"].append("source-matched light/dark, Chinese/English, 320px/short window, long original payload, keyboard focus and reduced-motion captures")
    report["requests"] = server()["requests"]
    report["extension_id"] = extension_id


def main() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise SystemExit("Extension browser validation requires a disposable GitHub-hosted runner")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    report: dict = {"status": "running", "revision": os.environ.get("GITHUB_SHA"), "scenarios": [],
                    "profile": "temporary synthetic Chromium only", "permission_prompts": "automatic acceptance in isolated test runner",
                    "sources": {str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sorted((ROOT / "extension/src").rglob("*")) if path.is_file()}}
    runtime_errors: list[str] = []
    with (tempfile.TemporaryDirectory(prefix="facetmark-extension-profile-") as profile,
          (EVIDENCE / "server.log").open("w", encoding="utf-8") as log):
        process = subprocess.Popen([sys.executable, str(ROOT / "scripts/extension_server.py")], cwd=ROOT, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 30
            while True:
                try:
                    server()
                    break
                except (URLError, TimeoutError):
                    if time.monotonic() >= deadline or process.poll() is not None:
                        raise AssertionError("Synthetic extension server did not start") from None
                    time.sleep(0.1)
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(profile, channel="chromium", headless=True,
                    args=[f"--disable-extensions-except={ROOT / 'extension/dist'}", f"--load-extension={ROOT / 'extension/dist'}",
                          "--auto-accept-this-extension-permission-request"], ignore_default_args=["--disable-extensions"])
                context.add_init_script("if(location.protocol==='chrome-extension:' && !localStorage.getItem('fm-lang')) localStorage.setItem('fm-lang','zh')")
                context.on("page", lambda page: page.on("pageerror", lambda error: runtime_errors.append(str(error))))
                context.tracing.start(screenshots=True, snapshots=True, sources=True)
                try:
                    worker = context.service_workers[0] if context.service_workers else context.wait_for_event("serviceworker")
                    review(context, worker, report)
                    assert not runtime_errors, runtime_errors
                    report["status"] = "passed"
                    print(json.dumps({"extension_review": "passed", "scenarios": len(report["scenarios"])}, ensure_ascii=False))
                finally:
                    report["runtime_errors"] = runtime_errors
                    if report["status"] != "passed":
                        for index, page in enumerate(context.pages):
                            with suppress(Exception):
                                page.screenshot(path=str(EVIDENCE / f"failure-page-{index}.png"), full_page=True)
                        context.tracing.stop(path=str(EVIDENCE / "failure-trace.zip"))
                    else:
                        context.tracing.stop()
                    context.close()
        except BaseException:
            report["status"] = "failed"
            report["error"] = traceback.format_exc()
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            (EVIDENCE / "extension-browser.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
