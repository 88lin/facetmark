"""Drive the shipped pages in a real browser and fail on what unit tests cannot see.

The suites already in CI answer different questions.  ``tests/web/*.test.mjs``
imports the pure modules and checks their arithmetic; it never builds a DOM.
``tests/test_web.py`` reads the stylesheet and the markup as *text* -- it can
say that a rule exists, not that the rule leaves the fifth tab on screen.
``tests/test_landing.py`` compares the committed HTML with a fresh render.  A
whole class of defect sits outside all three:

  * a media query that fits four of five tabs into a 390px phone,
  * a key handler that closes a dialog and then keeps travelling,
  * a colour that has no dark-mode step, so white text lands on cream,
  * a redirect that makes one of two languages unreachable.

Every one of those shipped in this repository, and every one of them is
one line of measurement away from being caught.  This script is that
measurement.  It boots the real server against an offline demo corpus
(``facetmark demo`` -- no key, no network), serves the committed landing pages
over loopback, and then asserts geometry, focus, contrast and console silence
against a real Chromium.

    python scripts/browser_check.py            # everything
    python scripts/browser_check.py --only app # or: site, regressions

Exit status is 0 when every check passes and 1 otherwise; each failure prints
the measurement that produced it, not just the name of the check.
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import http.server
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import closing, suppress
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "docs" / "landing"

# The eight views the shell can route to.  Five are tabs; `setup` and
# `settings` are reached from the gear and from an empty library.
VIEWS = ["search", "ask", "library", "sessions", "system", "setup", "settings"]

# Seven pages, two languages.  `index` is the one with the hero.
PAGES = ["index", "quickstart", "webui", "config", "integrations", "guide", "measured"]

# 390 is an iPhone 14; 768 an iPad in portrait; 1440 a laptop.  The narrow two
# are where the layout bugs live, so both languages get both of them.
APP_WIDTHS = [390, 768, 1440]
SITE_WIDTHS = [390, 1280]

QUERY = {"en": "vector index", "zh": "向量 索引"}


# --------------------------------------------------------------- plumbing


def free_port() -> int:
    with closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Landing:
    """The committed landing pages over loopback.

    They are read from `file://` nowhere in this script on purpose: the pages
    set `localStorage`, and a `file://` origin has no reliable storage
    partition to set it in.
    """

    def __init__(self) -> None:
        handler = functools.partial(_QuietHandler, directory=str(LANDING))
        self.port = free_port()
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self) -> Landing:
        self.thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def url(self, page: str) -> str:
        return f"http://127.0.0.1:{self.port}/{page}"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:  # noqa: A003 - stdlib name
        pass


class App:
    """The real server on an offline demo corpus.

    ``facetmark demo`` builds a synthetic 40-page library with real page
    bodies, deterministically, with no API key and no network.  That is the
    whole reason this can run in CI at all.
    """

    def __init__(self, size: int = 40) -> None:
        self.size = size
        self.port = free_port()
        self.dir = Path(tempfile.mkdtemp(prefix="fm-browser-"))
        self.proc: subprocess.Popen | None = None

    def __enter__(self) -> App:
        db = self.dir / "demo.db"
        say(f"building the demo corpus ({self.size} pages, offline)")
        subprocess.run(
            [sys.executable, "-m", "facetmark.cli", "demo",
             "--size", str(self.size), "--keep", "--db", str(db), "--json"],
            check=True, capture_output=True, cwd=ROOT,
        )
        env = {
            **os.environ,
            "FACETMARK_DATA_DIR": str(self.dir),
            "FACETMARK_DB_NAME": "demo.db",
            "FACETMARK_USE_MOCK_PROVIDER": "true",
            "FACETMARK_PORT": str(self.port),
        }
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "facetmark.cli", "serve"],
            env=env, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        self._wait()
        return self

    def _wait(self, seconds: float = 60.0) -> None:
        import urllib.error
        import urllib.request

        deadline = time.time() + seconds
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                out = self.proc.stdout.read().decode() if self.proc.stdout else ""
                raise RuntimeError(f"server exited early:\n{out}")
            with (
                suppress(urllib.error.URLError, ConnectionError, OSError),
                urllib.request.urlopen(f"{self.base}/health", timeout=2) as r,
            ):
                if r.status == 200:
                    return
            time.sleep(0.3)
        raise RuntimeError("server did not come up")

    def __exit__(self, *_exc: object) -> None:
        if self.proc is not None:
            self.proc.terminate()
            with suppress(subprocess.TimeoutExpired):
                self.proc.wait(timeout=10)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"


def say(msg: str) -> None:
    print(f"  {msg}", flush=True)


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0

    def ok(self, where: str, condition: bool, detail: str) -> None:
        self.checks += 1
        if not condition:
            self.failures.append(f"{where}: {detail}")

    def __bool__(self) -> bool:
        return not self.failures


# ------------------------------------------------------------- measurement

# Console noise is a finding, not decoration: a page that logs an error is a
# page where some branch already went wrong.  Both suites of screenshots in
# docs/landing/tools hold the same bar.
NOISE = ("error", "warning")

# An embedded screenshot is a box in somebody else's layout, and nothing in
# the suites can see how big that box is: the file is committed, the link
# resolves, the page does not scroll sideways.  A full-page capture of the
# search view -- an endless list -- came out 4,798px tall and rendered as a
# 3,550px column that swallowed a third of the landing page.  Height is the
# measurement that catches it.  Two and a half screens is generous for a
# figure and nowhere near 3,550.
TALLEST = 2.5

# `loading="lazy"` means a picture below the fold has not been fetched yet, so
# its box is zero tall and any question about its size answers itself wrongly.
# Force the fetch, wait for the decode, then measure.
SETTLED_IMAGES = """
async () => {
  const imgs = [...document.images];
  imgs.forEach((i) => { i.loading = 'eager'; });
  await Promise.all(imgs.map((i) => i.decode().catch(() => {})));
  return imgs.filter((i) => i.naturalWidth > 0).map((i) => ({
    src: i.currentSrc.split('/').pop(),
    h: Math.round(i.getBoundingClientRect().height),
    nat: `${i.naturalWidth}x${i.naturalHeight}`,
  }));
}
"""


async def open_page(browser, *, width: int, lang: str, theme: str, height: int = 900):
    ctx = await browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=1,
        is_mobile=width < 600,
        has_touch=width < 600,
        locale="zh-CN" if lang == "zh" else "en-US",
        color_scheme=theme,
    )
    await ctx.add_init_script(
        f"localStorage.setItem('fm-lang','{lang}');"
        f"localStorage.setItem('fm-theme','{theme}');"
    )
    page = await ctx.new_page()
    logged: list[str] = []
    page.on("console", lambda m: logged.append(f"{m.type}: {m.text}")
            if m.type in NOISE else None)
    page.on("pageerror", lambda e: logged.append(f"pageerror: {e}"))
    requested: list[str] = []
    page.on("request", lambda r: requested.append(r.url))
    return ctx, page, logged, requested


# Composite a possibly translucent colour over its backdrop and return the
# WCAG contrast ratio against a foreground.  Reading `backgroundColor` alone is
# not enough: the landing header is `rgba(..., .86)` over the page, and the
# whole defect this pins was that the .86 was the *day* cream.
LUMA = """
(sel) => {
  const parse = (s) => {
    const m = String(s).match(/[\\d.]+/g) || [];
    return { r: +m[0] || 0, g: +m[1] || 0, b: +m[2] || 0, a: m.length > 3 ? +m[3] : 1 };
  };
  const over = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  });
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const el = document.querySelector(sel);
  if (!el) return null;
  const page = parse(getComputedStyle(document.documentElement).backgroundColor);
  const root = page.a ? page : parse(getComputedStyle(document.body).backgroundColor);
  let bg = { r: root.r, g: root.g, b: root.b, a: 1 };
  for (const node of [...document.querySelectorAll('*')].filter((n) => n.contains(el) || n === el)) {
    const c = parse(getComputedStyle(node).backgroundColor);
    if (c.a > 0) bg = over(c, bg);
  }
  const fg = over(parse(getComputedStyle(el).color), bg);
  const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
  return { ratio: (a + 0.05) / (b + 0.05), bgLum: lum(bg), bg: getComputedStyle(el).backgroundColor };
}
"""

# `documentElement.scrollWidth` is not enough on its own, and finding that out
# is the reason this probe has two halves.  Given a list forced to 2200px
# inside a 390px phone, Chromium reported `scrollWidth === clientWidth === 390`
# -- no horizontal scrollbar, and the overflow simply unreachable.  A check
# built on the document alone would have called that page clean.  So the
# second half walks the box tree instead and asks the question directly: is
# any painted box sticking out past the right edge with nothing scrollable
# between it and the root?  Boxes inside a deliberately scrollable or clipped
# ancestor -- the wide-table wrapper, the diagram rail -- are theirs to manage.
OVERFLOW = """
() => {
  const vw = document.documentElement.clientWidth;
  const managed = (el) => {
    for (let n = el.parentElement; n; n = n.parentElement) {
      if (/auto|scroll|hidden|clip/.test(getComputedStyle(n).overflowX)) return true;
    }
    return false;
  };
  let worst = null;
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height || r.right <= vw + 1) continue;
    if (managed(el)) continue;
    if (!worst || r.right > worst.right) {
      worst = { right: Math.round(r.right), w: Math.round(r.width),
                tag: el.tagName.toLowerCase(),
                cls: (el.className || '').toString().slice(0, 50) };
    }
  }
  return {
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
    widest: worst,
  };
}
"""

TABS = """
() => {
  const bar = document.getElementById('tabs');
  if (!bar) return null;
  const tabs = [...bar.querySelectorAll('.tab')].map((t) => {
    const b = t.getBoundingClientRect();
    return {
      view: t.dataset.view,
      x: Math.round(b.x), y: Math.round(b.y),
      w: Math.round(b.width), h: Math.round(b.height),
      offscreen: b.right > innerWidth + 1 || b.left < -1,
      clipped: t.scrollWidth > t.clientWidth + 1,
    };
  });
  return { scrollW: bar.scrollWidth, clientW: bar.clientWidth, tabs,
           rows: new Set(tabs.map((t) => t.y)).size };
}
"""


async def settle(page, ms: int = 350) -> None:
    with suppress(Exception):
        await page.wait_for_load_state("networkidle", timeout=8000)
    await page.wait_for_timeout(ms)


async def sweep_app(browser, app: App, rep: Report) -> None:
    """Every view, both languages, both themes, three widths."""
    for width in APP_WIDTHS:
        for lang in ("en", "zh"):
            # Themes only need the wide pass: dark mode is a colour question,
            # and colour does not depend on the viewport.  Narrow widths are a
            # geometry question, and geometry does not depend on the theme.
            themes = ("light", "dark") if width == 1440 else ("light",)
            for theme in themes:
                ctx, page, logged, _ = await open_page(
                    browser, width=width, lang=lang, theme=theme)
                for view in VIEWS:
                    await page.goto(f"{app.base}/app#/{view}", wait_until="load")
                    await settle(page)
                    where = f"app {view} {lang}/{theme} @{width}"
                    m = await page.evaluate(OVERFLOW)
                    rep.ok(where, m["scrollW"] <= m["clientW"] + 1,
                           f"the page scrolls sideways: {m['scrollW']} > {m['clientW']}")
                    rep.ok(where, m["widest"] is None,
                           f"a box hangs off the right edge unreachably: {m['widest']}")
                    t = await page.evaluate(TABS)
                    if t:
                        bad = [x for x in t["tabs"] if x["offscreen"] or x["clipped"]]
                        rep.ok(where, not bad, f"tabs unreachable or cut: {bad}")
                        rep.ok(where, t["rows"] == 1,
                               f"the tab bar wrapped onto {t['rows']} rows: {t['tabs']}")
                        rep.ok(where, len(t["tabs"]) == 5,
                               f"expected five tabs, found {len(t['tabs'])}")
                    if lang == "en":
                        text = await page.inner_text("body")
                        rep.ok(where, "itting" not in text,
                               "the English UI still says 'Sitting'")
                rep.ok(f"app {lang}/{theme} @{width}", not logged,
                       f"console: {list(dict.fromkeys(logged))[:6]}")
                await ctx.close()
        say(f"app swept at {width}px")


async def sweep_site(browser, land: Landing, rep: Report) -> None:
    for width in SITE_WIDTHS:
        for lang in ("en", "zh"):
            themes = ("light", "dark") if width == 1280 else ("light",)
            for theme in themes:
                ctx, page, logged, requested = await open_page(
                    browser, width=width, lang=lang, theme=theme)
                for name in PAGES:
                    fn = f"{name}.html" if lang == "en" else f"{name}.zh.html"
                    await page.goto(land.url(fn), wait_until="load")
                    await settle(page, 250)
                    where = f"site {fn} {theme} @{width}"
                    m = await page.evaluate(OVERFLOW)
                    rep.ok(where, m["scrollW"] <= m["clientW"] + 1,
                           f"the page scrolls sideways: {m['scrollW']} > {m['clientW']}")
                    rep.ok(where, m["widest"] is None,
                           f"a box hangs off the right edge unreachably: {m['widest']}")
                    broken = await page.evaluate(
                        "() => [...document.images].filter((i) => i.complete "
                        "&& i.naturalWidth === 0).map((i) => i.getAttribute('src'))")
                    rep.ok(where, not broken, f"images did not load: {broken}")
                    if width == 1280:
                        ceiling = TALLEST * page.viewport_size["height"]
                        tall = [s for s in await page.evaluate(SETTLED_IMAGES)
                                if s["h"] > ceiling]
                        rep.ok(where, not tall,
                               f"a picture is taller than {TALLEST} screens: {tall}")
                rep.ok(f"site {lang}/{theme} @{width}", not logged,
                       f"console: {list(dict.fromkeys(logged))[:6]}")
                fonts = [u for u in requested if "fonts.googleapis" in u or "gstatic" in u]
                rep.ok(f"site {lang}/{theme} @{width}", not fonts,
                       f"a web font was fetched from a CDN: {fonts[:3]}")
                await ctx.close()
        say(f"site swept at {width}px")


# ------------------------------------------------------------- regressions
#
# One function per defect that shipped.  Each is named for the symptom, and
# each measures the thing the user would have noticed.


async def esc_keeps_the_search(browser, app: App, rep: Report) -> None:
    """Escape closed the dialog and then cleared the query behind it.

    The dialog's key handler ran in the capture phase and only called
    preventDefault.  It closed the overlay, the event carried on to the
    page-level handler, and the `if (detail.isOpen()) return` guard there read
    the overlay it had just closed -- so the query and every result went with
    it.
    """
    ctx, page, logged, _ = await open_page(browser, width=1280, lang="en", theme="light")
    await page.goto(f"{app.base}/app#/search", wait_until="load")
    await settle(page)
    await page.fill("#q", QUERY["en"])
    await page.keyboard.press("Enter")
    await page.wait_for_selector("#results li .peek", timeout=20000)
    await page.wait_for_timeout(600)
    # The suggestion list overlays the first rows; dismiss it before clicking.
    await page.mouse.click(8, 400)
    await page.wait_for_timeout(150)
    before = await page.eval_on_selector("#q", "(e) => e.value")
    n_before = await page.locator("#results li").count()
    await page.locator("#results li .peek").first.click()
    await page.wait_for_selector("#overlay:not([hidden])", timeout=10000)
    await page.wait_for_timeout(250)
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(300)

    state = await page.evaluate("""() => ({
      open: !document.getElementById('overlay').hidden,
      q: document.getElementById('q').value,
      n: document.querySelectorAll('#results li').length,
      focus: (document.activeElement.className || '') + '|' + document.activeElement.tagName,
    })""")
    w = "regression/escape"
    rep.ok(w, not state["open"], "Escape did not close the dialog")
    rep.ok(w, state["q"] == before,
           f"Escape cleared the query behind the dialog: {before!r} -> {state['q']!r}")
    rep.ok(w, state["n"] == n_before,
           f"Escape dropped the results behind the dialog: {n_before} -> {state['n']}")
    rep.ok(w, "peek" in state["focus"],
           f"focus did not return to the button that opened it: {state['focus']}")
    rep.ok(w, not logged, f"console: {logged[:4]}")
    await ctx.close()


async def the_fifth_tab_is_reachable(browser, app: App, rep: Report) -> None:
    """On a 390px phone the fifth view sat off the right edge.

    The row scrolled horizontally with the scrollbar hidden, so in English
    `System` was at x=394 on a 390px viewport with nothing to say it was there,
    and in Chinese the row squeezed itself to 81px with three-line labels.
    """
    for width in (360, 390, 480, 600, 720):
        for lang in ("en", "zh"):
            ctx, page, _, _ = await open_page(browser, width=width, lang=lang, theme="light")
            await page.goto(f"{app.base}/app#/search", wait_until="load")
            await settle(page, 300)
            t = await page.evaluate(TABS)
            w = f"regression/tabs {lang} @{width}"
            rep.ok(w, t is not None, "the tab bar is missing")
            if not t:
                await ctx.close()
                continue
            rep.ok(w, t["scrollW"] <= t["clientW"] + 1,
                   f"the tab row scrolls: {t['scrollW']} > {t['clientW']}")
            rep.ok(w, t["rows"] == 1, f"labels wrapped onto {t['rows']} rows")
            rep.ok(w, all(not x["offscreen"] for x in t["tabs"]),
                   f"a view is off screen: {[x['view'] for x in t['tabs'] if x['offscreen']]}")
            rep.ok(w, max(x["h"] for x in t["tabs"]) < 64,
                   f"the row is {max(x['h'] for x in t['tabs'])}px tall -- labels are wrapping")
            await ctx.close()


async def touch_hides_the_keyboard_hint(browser, app: App, rep: Report) -> None:
    """The `/` shortcut badge stayed on a phone that has no `/` key."""
    ctx, page, _, _ = await open_page(browser, width=390, lang="en", theme="light")
    await page.goto(f"{app.base}/app#/search", wait_until="load")
    await settle(page, 250)
    shown = await page.eval_on_selector(
        ".ask .hint", "(e) => getComputedStyle(e).display")
    rep.ok("regression/hint", shown == "none",
           f"the keyboard hint is visible on a touch viewport: display:{shown}")
    await ctx.close()


async def a_session_link_opens_that_session(browser, app: App, rep: Report) -> None:
    """Clicking a session in the dialog raced the router and lost.

    The view rendered its list first and the requested session was dropped, so
    the click landed on the index instead of the page it named.
    """
    ctx, page, _, _ = await open_page(browser, width=1280, lang="en", theme="light")
    await page.goto(f"{app.base}/app#/sessions", wait_until="load")
    await settle(page, 400)
    opener = page.locator("#view-sessions button").filter(has_not_text="").first
    if await page.locator(".sitting").count() == 0:
        rep.ok("regression/session", True, "no sessions in the demo corpus")
        await ctx.close()
        return
    await opener.click()
    await page.wait_for_timeout(500)
    back = await page.locator("#view-sessions .small").count()
    rep.ok("regression/session", back > 0,
           "opening one session did not reach the single-session page")
    await ctx.close()


async def dark_mode_is_actually_dark(browser, land: Landing, rep: Report) -> None:
    """Two colours on the landing site had no dark step.

    `header.site` was a hard-coded day cream, so the near-white logo sat on it
    invisibly; and `--warning-soft` -- unlike its success and danger siblings
    -- kept its day value, so every warning callout was pale yellow behind
    near-white text.
    """
    ctx, page, _, _ = await open_page(browser, width=1280, lang="zh", theme="dark")
    await page.goto(land.url("measured.zh.html"), wait_until="load")
    await settle(page, 300)
    for sel, name in ((".logo", "the header"), (".callout.warn", "a warning callout")):
        m = await page.evaluate(LUMA, sel)
        w = f"regression/dark {sel}"
        rep.ok(w, m is not None, f"{name} is missing from the page")
        if not m:
            continue
        rep.ok(w, m["bgLum"] < 0.2,
               f"{name} is still painted a light colour in dark mode "
               f"(luminance {m['bgLum']:.3f})")
        rep.ok(w, m["ratio"] >= 4.5,
               f"{name} reads at {m['ratio']:.2f}:1 in dark mode")
    await ctx.close()


async def a_named_page_stays_on_that_page(browser, land: Landing, rep: Report) -> None:
    """A stored language preference hijacked every explicit link.

    `initLang` replaced the location whenever the stored language differed from
    the page's, which meant one of the two languages was unreachable: follow a
    link to the English page with `zh` stored and you were bounced back.
    """
    for saved, fn in (("zh", "index.html"), ("en", "index.zh.html")):
        ctx, page, _, _ = await open_page(browser, width=1280, lang=saved, theme="light")
        await page.goto(land.url(fn), wait_until="load")
        await settle(page, 400)
        got = page.url.rsplit("/", 1)[-1]
        rep.ok("regression/lang", got == fn,
               f"stored {saved!r} hijacked an explicit link to {fn}: landed on {got}")
        await ctx.close()
    # The bare directory URL is the one place the preference should still win.
    ctx, page, _, _ = await open_page(browser, width=1280, lang="zh", theme="light")
    await page.goto(land.url(""), wait_until="load")
    await settle(page, 400)
    rep.ok("regression/lang", page.url.rsplit("/", 1)[-1] == "index.zh.html",
           f"a bare directory URL ignored the stored language: {page.url}")
    await ctx.close()


async def the_highlighted_phrase_stays_on_one_line(browser, land: Landing, rep: Report) -> None:
    """The hero's highlighter broke in half when the phrase wrapped."""
    for fn in ("index.html", "index.zh.html"):
        for width in (390, 1280):
            ctx, page, _, _ = await open_page(browser, width=width, lang="en", theme="light")
            await page.goto(land.url(fn), wait_until="load")
            await settle(page, 250)
            rects = await page.eval_on_selector(
                ".hero h1 em", "(e) => e.getClientRects().length")
            rep.ok(f"regression/hero {fn} @{width}", rects == 1,
                   f"the highlighted phrase is split across {rects} lines")
            await ctx.close()


async def the_site_reads_with_scripting_off(browser, land: Landing, rep: Report) -> None:
    """Every word of every page was invisible without JavaScript.

    `.reveal` ships at `opacity: 0` and a scroll observer adds the class that
    brings it back.  There was a fallback for a browser that lacks
    IntersectionObserver and none for a browser that never runs the script, so
    with scripting off the pages rendered a header, a footer, and 13,148
    characters of nothing -- which is also what a reader gets from Ctrl-P
    before scrolling, and what a text-mode crawler got every time.
    """
    for lang in ("en", "zh"):
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=1,
            locale="zh-CN" if lang == "zh" else "en-US",
            java_script_enabled=False,
        )
        page = await ctx.new_page()
        for name in PAGES:
            fn = f"{name}.html" if lang == "en" else f"{name}.zh.html"
            await page.goto(land.url(fn), wait_until="load")
            m = await page.evaluate("""() => {
              const rev = [...document.querySelectorAll('.reveal')];
              const dark = rev.filter((e) => +getComputedStyle(e).opacity < 0.05);
              const chars = (n) => n.reduce((s, e) => s + (e.innerText || '').length, 0);
              return {n: rev.length, hidden: dark.length, lost: chars(dark)};
            }""")
            rep.ok(f"regression/noscript {fn}", m["hidden"] == 0,
                   f"{m['hidden']} of {m['n']} blocks -- {m['lost']} characters -- "
                   "are invisible with scripting off")
        await ctx.close()


async def the_page_uses_the_system_face(browser, app: App, land: Landing, rep: Report) -> None:
    """Both surfaces should resolve to the platform UI face, with no CDN."""
    for what, url in (("app", f"{app.base}/app"), ("site", land.url("index.html"))):
        ctx, page, _, requested = await open_page(
            browser, width=1280, lang="en", theme="light")
        await page.goto(url, wait_until="load")
        await settle(page, 250)
        face = await page.evaluate("() => getComputedStyle(document.body).fontFamily")
        rep.ok(f"regression/font {what}", face.startswith("-apple-system"),
               f"body does not lead with the system face: {face}")
        for banned in ("Inter", "Roboto", "Fraunces", "Caveat"):
            rep.ok(f"regression/font {what}", banned not in face,
                   f"{banned} is still in the stack: {face}")
        cdn = [u for u in requested if "fonts.googleapis" in u or "gstatic" in u]
        rep.ok(f"regression/font {what}", not cdn, f"font CDN requested: {cdn[:2]}")
        await ctx.close()


# -------------------------------------------------------------------- main


async def run(only: str) -> int:
    rep = Report()
    started = time.time()
    with Landing() as land, App() as app:
        say(f"app on {app.base}, site on {land.url('')}")
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            if only in ("all", "app"):
                await sweep_app(browser, app, rep)
            if only in ("all", "site"):
                await sweep_site(browser, land, rep)
            if only in ("all", "regressions"):
                await esc_keeps_the_search(browser, app, rep)
                await the_fifth_tab_is_reachable(browser, app, rep)
                await touch_hides_the_keyboard_hint(browser, app, rep)
                await a_session_link_opens_that_session(browser, app, rep)
                await dark_mode_is_actually_dark(browser, land, rep)
                await a_named_page_stays_on_that_page(browser, land, rep)
                await the_highlighted_phrase_stays_on_one_line(browser, land, rep)
                await the_site_reads_with_scripting_off(browser, land, rep)
                await the_page_uses_the_system_face(browser, app, land, rep)
                say("regressions measured")
            await browser.close()

    took = time.time() - started
    if rep:
        print(f"\n{rep.checks} checks passed in {took:.0f}s")
        return 0
    print(f"\n{len(rep.failures)} of {rep.checks} checks failed in {took:.0f}s\n")
    for f in rep.failures:
        print(f"  FAIL  {f}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="all", choices=["all", "app", "site", "regressions"])
    args = ap.parse_args()
    return asyncio.run(run(args.only))


if __name__ == "__main__":
    raise SystemExit(main())
