"""Render the replacement workbench prototype in Actions with synthetic data only."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

SOURCE = Path("frontend/design/workbench/index.html")
OUTPUT = Path("design-evidence")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name, value):
    (OUTPUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class Evidence:
    def __init__(self, origin):
        self.origin = origin
        self.captures = []
        self.videos = []
        self.actions = []
        self.checks = []
        self.page_errors = []
        self.blocked_requests = []
        self.source_files = {SOURCE.as_posix()}
        self.started = time.monotonic()

    def record(self, name, **details):
        self.actions.append({"action": name, "elapsed_ms": round((time.monotonic() - self.started) * 1000),
                             **details})

    def check(self, name, condition, **details):
        self.checks.append({"check": name, "passed": bool(condition), **details})
        if not condition:
            raise AssertionError(f"{name}: {details}")

    def route(self, route):
        request = route.request
        url = urlsplit(request.url)
        origin = f"{url.scheme}://{url.netloc}"
        if origin != self.origin or request.method not in {"GET", "HEAD"}:
            self.blocked_requests.append({"url": request.url, "method": request.method})
            route.abort("blockedbyclient")
            return
        candidate = (Path.cwd() / unquote(url.path).lstrip("/")).resolve()
        if candidate.is_relative_to(Path.cwd().resolve()) and candidate.is_file():
            self.source_files.add(candidate.relative_to(Path.cwd().resolve()).as_posix())
        route.continue_()

    def context(self, browser, width, height, *, video=False, reduced_motion="no-preference"):
        options = {"viewport": {"width": width, "height": height}, "device_scale_factor": 1,
                   "color_scheme": "light", "reduced_motion": reduced_motion,
                   "locale": "zh-CN", "timezone_id": "Asia/Shanghai", "service_workers": "block"}
        if video:
            options.update(record_video_dir=str(OUTPUT / "raw"),
                           record_video_size={"width": width, "height": height})
        context = browser.new_context(**options)
        context.route("**/*", self.route)
        context.on("page", lambda page: page.on("pageerror", lambda error: self.page_errors.append(str(error))))
        return context

    def open(self, context):
        page = context.new_page()
        page.goto(f"{self.origin}/{SOURCE.as_posix()}", wait_until="networkidle")
        page.evaluate("() => document.fonts.ready")
        page.locator('[data-preview="101"]').wait_for(state="visible")
        page.wait_for_timeout(350)
        self.check("six synthetic bookmarks", page.locator("[data-preview]:visible").count() == 6)
        return page

    def screenshot(self, page, name, state):
        measurements = page.evaluate("""() => ({
          width: innerWidth, height: innerHeight,
          documentWidth: document.documentElement.scrollWidth,
          bodyWidth: document.body.scrollWidth,
          theme: document.documentElement.dataset.theme || document.body.dataset.theme || 'light',
          horizontalOverflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) > innerWidth + 1
        })""")
        self.check(f"{name} has no horizontal overflow", not measurements["horizontalOverflow"], **measurements)
        destination = OUTPUT / f"{name}.png"
        page.screenshot(path=str(destination), animations="disabled")
        self.captures.append({"file": destination.name, "sha256": sha256(destination),
                              "source": SOURCE.as_posix(), "state": state, **measurements})

    def no_motion(self, page, name):
        # Allow the <= 1ms CSS accessibility fallback to settle for two frames.
        page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
        animations = page.evaluate("""() => document.getAnimations().filter(animation => {
          const target = animation.effect?.target;
          const box = target?.getBoundingClientRect();
          return animation.playState === 'running' && box && box.width && box.height;
        }).map(animation => ({
          target: animation.effect.target.id || animation.effect.target.className?.toString(),
          duration: animation.effect.getComputedTiming().duration,
          iterations: animation.effect.getComputedTiming().iterations
        })).filter(animation => animation.duration > 1 || animation.iterations === Infinity)""")
        self.check(name, not animations, active_animations=animations)


def capture_states(browser, evidence, expect):
    for width, height, label in [(1440, 1000, "1440"), (390, 844, "390"), (1024, 650, "1024-short")]:
        context = evidence.context(browser, width, height)
        try:
            page = evidence.open(context)
            evidence.screenshot(page, f"workbench-light-{label}", "collection")
            page.locator("#theme-toggle").click()
            expect(page.locator("html")).to_have_attribute("data-theme", "dark")
            page.wait_for_timeout(400)
            evidence.screenshot(page, f"workbench-dark-{label}", "collection")
            if width == 390:
                page.locator('[data-preview="101"]').click()
                expect(page.locator("#reader-dialog")).to_be_visible()
                evidence.check("mobile reader is modal", page.locator("#reader-dialog").evaluate("element => element.open"))
                evidence.screenshot(page, "workbench-reader-390", "reading")
                page.locator("#reader-close").click()
                expect(page.locator('[data-preview="101"]')).to_be_focused()
                evidence.record("mobile reading returns focus", viewport=label)
        finally:
            context.close()


def interaction_sequence(browser, evidence, expect):
    context = evidence.context(browser, 1440, 1000, video=True)
    page = evidence.open(context)
    video = page.video
    try:
        page.wait_for_timeout(1100)
        page.locator("#directory-toggle").click()
        expect(page.locator("#directory-toggle")).to_have_attribute("aria-expanded", "true")
        expect(page.locator("#directory-popover")).to_be_visible()
        page.wait_for_timeout(650)
        evidence.screenshot(page, "workbench-directory-1440", "directory-open")
        evidence.record("open directory", expanded=True)
        page.locator('[data-folder="设计 / 界面"]').click()
        expect(page.locator('[data-preview="101"]')).to_be_visible()
        expect(page.locator("[data-preview]:visible")).to_have_count(2)
        evidence.record("filter by exact directory", folder="设计 / 界面", count=2)
        page.wait_for_timeout(800)
        page.locator("#clear-filters").click()
        expect(page.locator("[data-preview]:visible")).to_have_count(6)
        page.wait_for_timeout(500)

        preview = page.locator('[data-preview="101"]')
        preview.focus()
        preview.press("Enter")
        dialog = page.locator("#reader-dialog")
        expect(dialog).to_be_visible()
        evidence.check("reader is native open dialog", dialog.evaluate("element => element.tagName === 'DIALOG' && element.open"))
        evidence.check("reader receives focus", dialog.evaluate("element => element.contains(document.activeElement)"))
        page.wait_for_timeout(1100)
        evidence.screenshot(page, "workbench-reader-1440", "reading")
        evidence.record("open reading with Enter", bookmark="101", focus_inside=True)
        page.locator("#reader-close").click()
        expect(dialog).not_to_be_visible()
        expect(preview).to_be_focused()
        evidence.record("close reading", focus_returned=True)
        page.wait_for_timeout(650)

        for bookmark in ["101", "102"]:
            checkbox = page.locator(f'[data-select="{bookmark}"]')
            checkbox.check()
            expect(checkbox).to_be_checked()
        expect(page.locator("#selection-bar")).to_be_visible()
        expect(page.locator("#selection-count")).to_have_text("2")
        page.wait_for_timeout(800)
        evidence.screenshot(page, "workbench-selected-1440", "two-selected")
        evidence.record("select two bookmarks", selected=["101", "102"])
        page.locator("#clear-selection").click()
        expect(page.locator('[data-select="101"]')).not_to_be_checked()
        expect(page.locator('[data-select="102"]')).not_to_be_checked()
        expect(page.locator("#selection-bar")).not_to_be_visible()
        evidence.record("clear selection", selected=[])
        page.wait_for_timeout(550)

        page.locator("#view-list").click()
        expect(page.locator("#view-list")).to_have_attribute("aria-pressed", "true")
        page.wait_for_timeout(700)
        evidence.screenshot(page, "workbench-list-1440", "compact-list")
        evidence.record("switch to compact view")
        page.locator("#view-grid").click()
        expect(page.locator("#view-grid")).to_have_attribute("aria-pressed", "true")
        page.wait_for_timeout(550)

        page.locator("#search-input").fill("__facetmark_no_matching_synthetic_record__")
        expect(page.locator("[data-preview]:visible")).to_have_count(0)
        evidence.screenshot(page, "workbench-empty-1440", "empty-search")
        evidence.record("search empty state", visible_results=0)
        page.wait_for_timeout(650)
        page.locator("#search-clear").click()
        expect(page.locator("#search-input")).to_have_value("")
        expect(page.locator("[data-preview]:visible")).to_have_count(6)
        evidence.record("clear search", visible_results=6)
        page.wait_for_timeout(700)
        page.locator("#theme-toggle").click()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        evidence.record("switch dark theme")
        page.wait_for_timeout(1200)
        page.locator("#theme-toggle").click()
        expect(page.locator("html")).to_have_attribute("data-theme", "light")
        page.wait_for_timeout(1000)
    finally:
        context.close()
        video.save_as(str(OUTPUT / "workbench-interactions.webm"))


def check_filters_and_forms(browser, evidence, expect):
    context = evidence.context(browser, 390, 844)
    try:
        page = evidence.open(context)
        page.locator('#view-list').click()
        checkbox = page.locator('[data-select="101"]')
        expect(checkbox).to_be_visible()
        checkbox.focus()
        checkbox.press("Space")
        expect(checkbox).to_be_checked()
        page.locator('[data-category="开发"]').click()
        expect(page.locator('[data-preview]:visible')).to_have_count(1)
        expect(page.locator('#selection-count')).to_have_text('1')
        page.locator('#selection-summary').click()
        expect(page.locator('#action-dialog')).to_contain_text('让导航退后一步')
        expect(page.locator('#action-dialog')).to_contain_text('不会连接模型服务')
        page.keyboard.press('Escape')
        expect(page.locator('#selection-summary')).to_be_focused()
        page.locator('#clear-filters').click()
        expect(checkbox).to_be_checked()
        page.locator('#clear-selection').click()
        page.locator('#view-grid').click()
        for status, count in [('pending', 2), ('done', 3), ('failed', 1)]:
            page.locator(f'[data-status="{status}"]').click()
            expect(page.locator('[data-preview]:visible')).to_have_count(count)
        page.locator('#clear-filters').click()
        search = page.locator('#search-input')
        # A synthetic composition sequence checks that intermediate IME text does
        # not refilter the collection before compositionend.
        search.evaluate("""input => {
          input.dispatchEvent(new CompositionEvent('compositionstart', {bubbles:true}));
          input.value = '导航';
          input.dispatchEvent(new InputEvent('input', {bubbles:true, isComposing:true}));
        }""")
        expect(page.locator('[data-preview]:visible')).to_have_count(6)
        search.evaluate("input => input.dispatchEvent(new CompositionEvent('compositionend', {bubbles:true}))")
        expect(page.locator('[data-preview]:visible')).to_have_count(1)
        page.locator('#search-clear').click()
        page.keyboard.press('Control+k')
        expect(search).to_be_focused()
        page.locator('#sort-order').select_option('oldest')
        expect(page.locator('[data-preview]').first).to_have_attribute('data-preview', '106')
        evidence.record('filters, hidden selection and synthetic IME', pending=2, done=3, failed=1)
        page.locator('#add-bookmark').click()
        page.locator('#demo-add input[name="url"]').fill('https://example.com/demo')
        page.locator('#demo-add input[name="title"]').fill('合成收藏检查')
        page.locator('#demo-add button[type="submit"]').click()
        expect(page.locator('.action-feedback')).to_contain_text('原型不保存')
        page.keyboard.press('Escape')
        expect(page.locator('#add-bookmark')).to_be_focused()
        expect(page.locator('[data-preview]:visible')).to_have_count(6)
        evidence.record('native demo form and focus return', persisted=False)
        for route in ['tasks', 'settings']:
            page.locator(f'[data-route="{route}"]').click()
            expect(page.locator('#action-dialog')).to_contain_text('交互原型')
            page.keyboard.press('Escape')
            expect(page.locator(f'[data-route="{route}"]')).to_be_focused()
        page.locator('#sort-order').select_option('newest')
        page.locator('#view-list').click()
        evidence.screenshot(page, 'workbench-list-390', 'compact-mobile-with-selection-controls')
        evidence.check('all static original links preserved', page.locator('a.card-external[href^="https://"]').count() == 6)
    finally:
        context.close()


def check_reduced_motion_and_isolation(browser, evidence, expect):
    context = evidence.context(browser, 1440, 1000, reduced_motion="reduce")
    try:
        page = evidence.open(context)
        page.locator("#directory-toggle").click()
        expect(page.locator("#directory-popover")).to_be_visible()
        evidence.no_motion(page, "directory respects reduced motion")
        page.keyboard.press("Escape")
        expect(page.locator("#directory-popover")).not_to_be_visible()
        expect(page.locator("#directory-toggle")).to_be_focused()

        for activation in ["Space", "Enter"]:
            preview = page.locator('[data-preview="101"]')
            preview.focus()
            preview.press(activation)
            expect(page.locator("#reader-dialog")).to_be_visible()
            evidence.no_motion(page, f"reading respects reduced motion after {activation}")
            page.keyboard.press("Escape")
            expect(page.locator("#reader-dialog")).not_to_be_visible()
            expect(preview).to_be_focused()

        page.emulate_media(reduced_motion="no-preference")
        page.locator('[data-preview="101"]').click()
        page.emulate_media(reduced_motion="reduce")
        evidence.no_motion(page, "live reduced-motion change cancels motion")
        page.locator("#reader-close").click()
        for _ in range(3):
            page.locator("#directory-toggle").click()
            page.locator("#directory-toggle").click()
        expect(page.locator("#directory-popover")).not_to_be_visible()
        expect(page.locator("#directory-toggle")).to_have_attribute("aria-expanded", "false")
        evidence.record("reduced motion and fast directory toggles", keyboard=["Enter", "Space", "Escape"],
                        preference_changed_while_open=True, toggle_pairs=3)

        # The route handler aborts this exact request before external network access.
        blocked = page.evaluate("""async () => {
          try { await fetch('https://facetmark-network-probe.invalid/blocked'); return false; }
          catch { return true; }
        }""")
        evidence.check("external network is blocked", blocked and any(
            item["url"] == "https://facetmark-network-probe.invalid/blocked" for item in evidence.blocked_requests))
        unexpected = [item for item in evidence.blocked_requests
                      if item["url"] != "https://facetmark-network-probe.invalid/blocked"]
        evidence.check("prototype has no external requests or writes", not unexpected, unexpected=unexpected)
        evidence.check("no page errors", not evidence.page_errors, errors=evidence.page_errors)
    finally:
        context.close()


def encode_video(evidence):
    destination = OUTPUT / "workbench-interactions.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
                    str(OUTPUT / "workbench-interactions.webm"), "-an", "-c:v", "libx264", "-crf", "22",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destination)], check=True)
    duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                              "-of", "default=noprint_wrappers=1:nokey=1", str(destination)], text=True))
    evidence.videos.append({"file": destination.name, "sha256": sha256(destination),
                            "width": 1440, "height": 1000, "duration_seconds": duration,
                            "source": SOURCE.as_posix(), "kind": "recorded browser clicks and keyboard actions"})


def package_preview():
    """A portable static prototype; the user can open index.html after extraction."""
    destination = OUTPUT / 'preview'
    destination.mkdir(exist_ok=True)
    for name in ['index.html', 'workbench.js']:
        shutil.copy2(SOURCE.parent / name, destination / name)
    css = (SOURCE.parent / 'workbench.css').read_text(encoding='utf-8')
    (destination / 'workbench.css').write_text(
        css.replace('../../src/assets/fonts/', './fonts/'), encoding='utf-8')
    fonts = destination / 'fonts'
    fonts.mkdir(exist_ok=True)
    for name in ['noto-sans-sc.woff2', 'NotoSansSC-LICENSE.txt']:
        shutil.copy2(Path('frontend/src/assets/fonts') / name, fonts / name)
    (destination / 'README.txt').write_text(
        'Facetmark interactive visual proposal. Open index.html in a browser.\n'
        'Synthetic content only. Not the application or an installer.\n'
        'Search, filters, selection, reading, themes and fixture JSON export work.\n'
        'Add/move/summary dialogs are demonstrations; no database or AI connection.\n', encoding='utf-8')


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Design prototype rendering runs in GitHub Actions only")
    if not SOURCE.is_file():
        raise SystemExit(f"Missing prototype: {SOURCE}")
    from playwright.sync_api import expect, sync_playwright

    OUTPUT.mkdir(exist_ok=True)
    handler = partial(SimpleHTTPRequestHandler, directory=str(Path.cwd()))
    failure = None
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        evidence = Evidence(f"http://127.0.0.1:{server.server_port}")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    capture_states(browser, evidence, expect)
                    interaction_sequence(browser, evidence, expect)
                    check_filters_and_forms(browser, evidence, expect)
                    check_reduced_motion_and_isolation(browser, evidence, expect)
                    encode_video(evidence)
                    package_preview()
                finally:
                    browser.close()
        except Exception as error:
            failure = f"{type(error).__name__}: {error}"
        finally:
            server.shutdown()
            sources = [{"file": file, "sha256": sha256(Path(file))} for file in sorted(evidence.source_files)]
            write_json("interactions.json", {"source": SOURCE.as_posix(), "actions": evidence.actions,
                       "checks": evidence.checks, "page_errors": evidence.page_errors,
                       "blocked_requests": evidence.blocked_requests, "failure": failure})
            write_json("provenance.json", {
                "commit": os.environ["GITHUB_SHA"], "run": os.environ["GITHUB_RUN_ID"],
                "kind": "replacement visual prototype with synthetic content; not production or installed application screenshots",
                "entrypoint": SOURCE.as_posix(), "source_files": sources,
                "captures": evidence.captures, "videos": evidence.videos,
                "interaction_evidence": {"file": "interactions.json", "sha256": sha256(OUTPUT / "interactions.json")},
                "status": "failed" if failure else "passed", "failure": failure,
            })
    if failure:
        raise SystemExit(failure)
    print(f"Captured {len(evidence.captures)} prototype states and {len(evidence.videos)} interaction video; "
          f"{len(evidence.checks)} checks passed")


if __name__ == "__main__":
    main()
