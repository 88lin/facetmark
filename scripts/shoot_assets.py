#!/usr/bin/env python3
"""Regenerate the fourteen PNGs the site embeds.

    python3 scripts/shoot_assets.py                # all of them
    python3 scripts/shoot_assets.py --only popup,og

Until now these were shot by hand, which meant a palette change left the
pictures showing the old one and there was no way to tell which run produced
what.  Four groups, all offline:

``popup`` / ``options``
    The real extension HTML and the real ``popup.css``, linked to the real
    ``palettes.css``, with the DOM that ``popup.ts`` would build injected as a
    fixture instead of running the extension.  No npm, no browser profile: the
    panel is 420 CSS px of static markup, and mocking the rows is the only way
    to photograph a populated result list without a server *and* a paired
    token.  Two overrides are injected, both noted at the point of use: the
    panel's scroll clamps exist so a popup cannot outgrow the browser window,
    and a screenshot has no window to outgrow.

``app``
    The served page against ``facetmark demo``, through the same ``App``
    context manager ``browser_check.py`` uses, so the corpus is the offline
    synthetic one and the counts are reproducible.

``og``
    The social card, drawn here rather than in a design tool, from the same
    palette tokens as everything else.  The three figures on it are measured
    results and are passed through untouched.

Shot at device scale 2 for the two extension panels -- they are photographs of
a small UI that gets displayed twice its size -- and at 1 for the app and the
card, which are already large.
"""

from __future__ import annotations

import argparse
import asyncio
import http.server
import shutil
import socket
import socketserver
import sys
import tempfile
import threading
from contextlib import suppress
from pathlib import Path

from playwright.async_api import Browser, async_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from browser_check import App, say  # noqa: E402

ASSETS = ROOT / "docs" / "landing" / "assets"
EXT = ROOT / "extension" / "src"
STATIC = ROOT / "src" / "facetmark" / "web" / "static"

#: The panels are photographed at their own CSS width; the file is twice that.
POPUP_WIDTH = 420
OPTIONS_WIDTH = 560
APP_WIDTH = 1440
#: Only a starting height.  Every app shot is full-page, so the real height is
#: whatever the view needs -- which is what the old files did too (they ranged
#: 1916 to 1959) and what keeps a long view from being silently cropped.
APP_HEIGHT = 1000
CARD = (1200, 630)

FONTS = "'Liberation Sans', Arimo, 'Noto Sans CJK SC', sans-serif"


# ---------------------------------------------------------------------------
# a loopback server: file:// gives no localStorage partition and trips CORS on
# the module scripts, and the app shots need a real origin anyway
# ---------------------------------------------------------------------------


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def serve(directory: Path) -> tuple[socketserver.TCPServer, str]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(directory), **kw)

        def log_message(self, *a):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", free_port()), Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


# ---------------------------------------------------------------------------
# the extension fixture
# ---------------------------------------------------------------------------

#: What `popup.ts` receives from `/search` and turns into rows.  The wording is
#: the wording the previous pictures shipped with, so a palette change shows up
#: as a palette change and nothing else.
HITS = [
    {
        "title": "签到脚本：自动打卡的几种姿势",
        "lead": "juejin.cn · 工具",
        "facets": ["content", "intent"],
        "snippet": "用 headless 浏览器定时触发签到接口，注意 cookie 过期……",
    },
    {
        "title": "How I automate check-ins with cron",
        "lead": "example.dev",
        "facets": ["lex_seg"],
        "snippet": "A small systemd timer plus a curl one-liner is enough…",
    },
    {
        "title": "老旧的签到页面（已打不开）",
        "lead": "dead.example",
        "facets": ["lex_tri"],
        "cold": True,
        "snippet": "存档前的快照：每日签到领积分……",
    },
]
NEIGHBOURS = [
    {"title": "浏览器自动化书单", "lead": "books.example"},
    {"title": "cron 表达式速查", "lead": "cheatsheet.dev"},
]
FACET_LABEL = {"content": "about", "intent": "asked as", "lex_seg": "words",
               "lex_tri": "substring"}

#: Injected into the popup, mirroring `row()` in popup.ts element for element:
#: `li > a.hit > .title + .meta(lead + chips + badge) + .snippet`.  If that
#: function grows a node, this fixture is what has to grow with it.
POPUP_FIXTURE = """
(data) => {
  const [hits, neighbours, labels] = data;
  document.querySelector("#q").value = "上次存的那个签到脚本";
  document.querySelector("#status").textContent =
    "3 results · 212 ms · episodic + content";
  document.querySelector("#queue").textContent = "3 pages queued";
  const list = document.querySelector("#results");
  const row = (h, neighbour) => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = "#";
    a.className = neighbour ? "hit neighbour" : "hit";
    const title = document.createElement("div");
    title.className = "title";
    title.textContent = h.title;
    a.appendChild(title);
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.appendChild(document.createTextNode(h.lead));
    const chips = neighbour ? ["linked"] : (h.facets || []).map((f) => labels[f]);
    for (const text of chips) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = text;
      meta.appendChild(chip);
    }
    a.appendChild(meta);
    if (h.cold) {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = "cold";
      meta.appendChild(badge);
    }
    if (h.snippet) {
      const sn = document.createElement("div");
      sn.className = "snippet";
      sn.textContent = h.snippet;
      a.appendChild(sn);
    }
    li.appendChild(a);
    return li;
  };
  for (const h of hits) list.appendChild(row(h, false));
  const group = document.createElement("li");
  group.className = "group";
  group.textContent = "saved around these · " + neighbours.length;
  list.appendChild(group);
  for (const h of neighbours) list.appendChild(row(h, true));
}
"""

#: The clamps that keep a real popup inside a real browser window, and the
#: pulsing dot on the status line.  A still frame catches an animation at an
#: arbitrary opacity, so it is stopped rather than left to chance.  Harmless on
#: the options page, which has no clamps and nothing moving.
STILL_FRAME = """
  body { max-height: none !important; }
  ul#results { max-height: none !important; overflow: visible !important; }
  *, *::before, *::after { animation: none !important; transition: none !important; }
"""

OPTIONS_FIXTURE = """
() => {
  document.querySelector("#endpoint").value = "http://127.0.0.1:8787";
  document.querySelector("#token").value =
    "fm_7b41c0e9a2d84f13b6e5c07a9d2f8341";
  document.querySelector("#channelB").checked = true;
  document.querySelector("#paused").checked = false;
  const state = document.querySelector("#state");
  state.className = "ok";
  state.textContent = "saved · server reachable · 2,376 pages indexed";
}
"""


def extension_fixture_dir() -> Path:
    """The two entry points, the sheet, and the palette, with the module
    scripts dropped -- the DOM is injected instead of built."""
    tmp = Path(tempfile.mkdtemp(prefix="fm-shoot-ext-"))
    shutil.copy(EXT / "popup.css", tmp / "popup.css")
    shutil.copy(STATIC / "palettes.css", tmp / "palettes.css")
    for name in ("popup.html", "options.html"):
        text = (EXT / name).read_text(encoding="utf-8")
        text = text.replace(
            f'<script type="module" src="{name[:-5]}.js"></script>', "")
        (tmp / name).write_text(text, encoding="utf-8")
    return tmp


async def shoot_extension(browser: Browser, out: Path, groups: set[str]) -> list[Path]:
    tmp = extension_fixture_dir()
    srv, base = serve(tmp)
    written: list[Path] = []
    try:
        jobs = []
        if "popup" in groups:
            jobs.append(("popup-mock", "popup.html", POPUP_WIDTH,
                         POPUP_FIXTURE, [HITS, NEIGHBOURS, FACET_LABEL]))
        if "options" in groups:
            jobs.append(("options", "options.html", OPTIONS_WIDTH,
                         OPTIONS_FIXTURE, None))
        for stem, page_file, width, fixture, arg in jobs:
            for theme in ("light", "dark"):
                ctx = await browser.new_context(
                    viewport={"width": width, "height": 600},
                    device_scale_factor=2,
                    color_scheme=theme,
                    reduced_motion="reduce",
                    locale="zh-CN",
                )
                page = await ctx.new_page()
                await page.goto(f"{base}/{page_file}", wait_until="load")
                await page.add_style_tag(content=STILL_FRAME)
                if arg is None:
                    await page.evaluate(fixture)
                else:
                    await page.evaluate(fixture, arg)
                await page.wait_for_timeout(250)
                # A panel is as tall as its content, and `full_page` floors at
                # the viewport, so the viewport is trimmed to the body first --
                # otherwise every shot carries a strip of empty page colour.
                tall = await page.evaluate(
                    "() => Math.ceil(document.body.getBoundingClientRect().height)")
                await page.set_viewport_size({"width": width, "height": tall})
                await page.wait_for_timeout(150)
                name = out / f"{stem}{'-dark' if theme == 'dark' else ''}.png"
                await page.screenshot(path=str(name))
                written.append(name)
                await ctx.close()
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    return written


# ---------------------------------------------------------------------------
# the served page
# ---------------------------------------------------------------------------

#: 60 pages is what the previous pictures showed -- "Library 60", "Sessions 10",
#: "1-20 of 60" -- and the demo corpus is deterministic, so the numbers on the
#: new pictures match the numbers in the prose that describes them.
DEMO_SIZE = 60
QUERY = {"en": "vector index", "zh": "向量 索引"}
#: The search view answers with twenty rows, and a full-page capture of it is
#: 4,718px tall -- a picture nobody scrolls, and the reason `browser_check.py`
#: grew a ceiling of 2.5 screens after the last one shipped at 4,798px. Ten
#: rows is half the answer, which reads as "and it continues" rather than as a
#: page that ends. The cut lands exactly on the tenth row's bottom hairline --
#: the list is a 2px-gap stack, so any gutter at all starts slicing the
#: eleventh title in half -- and the height therefore comes out where the
#: language puts it (1,897 in English, 1,959 in Chinese) rather than being
#: forced to one number for both.
ROWS_IN_SHOT = 10


async def shoot_app(browser: Browser, out: Path) -> list[Path]:
    written: list[Path] = []
    with App(size=DEMO_SIZE) as app:
        for lang in ("en", "zh"):
            for theme in ("light", "dark"):
                ctx = await browser.new_context(
                    viewport={"width": APP_WIDTH, "height": APP_HEIGHT},
                    device_scale_factor=1,
                    color_scheme=theme,
                    reduced_motion="reduce",
                    locale="zh-CN" if lang == "zh" else "en-US",
                )
                page = await ctx.new_page()
                # The theme and language live in localStorage, so they have to
                # be set before the boot script reads them, not after.
                await page.add_init_script(
                    f"localStorage.setItem('fm-theme','{theme}');"
                    f"localStorage.setItem('fm-lang','{lang}');")
                await page.goto(f"{app.base}/app", wait_until="networkidle")
                await page.wait_for_timeout(600)
                for view in ("search", "library"):
                    await page.click(f'[data-view="{view}"]')
                    if view == "search":
                        await page.fill("#q", QUERY[lang])
                        await page.keyboard.press("Enter")
                        await page.wait_for_selector(
                            "#results li:nth-child(4)", timeout=30000)
                    else:
                        await page.wait_for_selector("#stats .block", timeout=30000)
                    await page.wait_for_timeout(800)
                    stem = f"app-{view}{'-zh' if lang == 'zh' else ''}"
                    name = out / f"{stem}{'-dark' if theme == 'dark' else ''}.png"
                    clip = None
                    if view == "search":
                        cut = await page.evaluate(
                            "(n) => { const r = [...document.querySelectorAll("
                            "'#results > li')].slice(0, n).pop();"
                            " return r ? Math.round(r.getBoundingClientRect()"
                            ".bottom + window.scrollY) : null; }", ROWS_IN_SHOT)
                        if cut:
                            clip = {"x": 0, "y": 0, "width": APP_WIDTH,
                                    "height": cut}
                    await page.screenshot(path=str(name), full_page=True, clip=clip)
                    written.append(name)
                await ctx.close()
    return written


# ---------------------------------------------------------------------------
# the social card
# ---------------------------------------------------------------------------

#: Three measured results, and they are quoted here exactly as they are quoted
#: on /measured.  Do not round them to make a card balance.
CARD_TEXT = {
    "en": {
        "kicker": "LOCAL-FIRST BOOKMARK RETRIEVAL",
        "head": ['Find the bookmark you can only',
                 '<mark>half</mark> remember.'],
        "caps": ["Recall@5 on 479 real queries, one facet",
                 "what turning on all four facets cost",
                 "what the shipped episodic gate cost"],
        "spacing": "0.14em",
    },
    "zh": {
        "kicker": "本地优先的书签检索",
        "head": ['找回那个你<mark>只记得一半</mark>的书签。'],
        "caps": ["479 条真实查询、单一个面的 Recall@5",
                 "四个面全打开的代价",
                 "已经发出去的情景门的代价"],
        "spacing": "0.02em",
    },
}
FIGURES = ["0.643", "\u22125.4pp", "\u221218.83pp"]

#: The card is drawn from palette tokens, not from picked values: --indigo-ink
#: on --indigo-soft for the headline result, --plum-ink on --highlight-soft for
#: the cost of fusion, --danger-strong on --rose-soft for the regression that
#: was reverted.  Three hues that are all in the shipped family.
CARD_HTML = """<!doctype html>
<html lang="{lang}" data-palette="I">
<head><meta charset="utf-8">
<link rel="stylesheet" href="palettes.css">
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; }}
  body {{
    width: {w}px; height: {h}px; padding: 56px 72px 48px;
    background: var(--cream); color: var(--ink);
    font: 16px/1.5 {fonts};
    display: flex; flex-direction: column;
  }}
  .top {{ display: flex; align-items: center; justify-content: space-between; }}
  .wordmark {{ display: flex; align-items: center; gap: 16px;
               font-size: 34px; font-weight: 700; letter-spacing: -0.01em; }}
  .wordmark img {{ width: 40px; height: 40px; display: block; }}
  .url {{ font: 15px/1 ui-monospace, "Liberation Mono", monospace;
          color: var(--ink-faint); letter-spacing: 0.01em; }}
  /* The claim is centred in whatever room the card has left, so a one-line
     Chinese headline and a two-line English one both sit balanced instead of
     leaving a hole above the figures. */
  .mid {{ flex: 1; display: flex; flex-direction: column; justify-content: center; }}
  .kicker {{ font-size: 15px; font-weight: 700;
             letter-spacing: {spacing}; color: var(--ink-faint); }}
  .rule {{ width: 40px; height: 4px; border-radius: 2px;
           background: var(--brand); margin: 14px 0 0; }}
  h1 {{ margin: 26px 0 0; font-size: {size}px; line-height: 1.16;
        font-weight: 700; letter-spacing: -0.022em; }}
  h1 mark {{ background: var(--highlight); color: var(--brand-deep);
             padding: 0 6px; border-radius: 3px; }}
  .figs {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }}
  .fig {{ border: 2px dashed; border-radius: 14px; padding: 18px 22px 20px; }}
  .fig b {{ display: block; font-size: 36px; font-weight: 700;
            letter-spacing: -0.01em; }}
  .fig span {{ display: block; margin-top: 8px; font-size: 14px;
               line-height: 1.4; color: var(--ink-light); }}
  .a {{ background: #dfecfb; border-color: rgba(35, 60, 104, 0.45); }}
  .a b {{ color: #233c68; }}
  .b {{ background: var(--highlight-soft); border-color: rgba(91, 35, 73, 0.4); }}
  .b b {{ color: #5b2349; }}
  .c {{ background: #fee1ed; border-color: rgba(180, 35, 60, 0.4); }}
  .c b {{ color: var(--danger-strong); }}
</style></head>
<body>
  <div class="top">
    <div class="wordmark"><img src="favicon.svg" alt="">facetmark</div>
    <div class="url">88lin.github.io/facetmark</div>
  </div>
  <div class="mid">
    <div class="kicker">{kicker}</div>
    <div class="rule"></div>
    <h1>{head}</h1>
  </div>
  <div class="figs">
    <div class="fig a"><b>{f0}</b><span>{c0}</span></div>
    <div class="fig b"><b>{f1}</b><span>{c1}</span></div>
    <div class="fig c"><b>{f2}</b><span>{c2}</span></div>
  </div>
</body></html>
"""


async def shoot_og(browser: Browser, out: Path) -> list[Path]:
    tmp = Path(tempfile.mkdtemp(prefix="fm-shoot-og-"))
    shutil.copy(STATIC / "palettes.css", tmp / "palettes.css")
    shutil.copy(ASSETS / "favicon.svg", tmp / "favicon.svg")
    srv, base = serve(tmp)
    written: list[Path] = []
    w, h = CARD
    try:
        for lang, t in CARD_TEXT.items():
            (tmp / f"og-{lang}.html").write_text(CARD_HTML.format(
                lang="zh" if lang == "zh" else "en", w=w, h=h, fonts=FONTS,
                spacing=t["spacing"], size=58 if lang == "en" else 62,
                kicker=t["kicker"], head="<br>".join(t["head"]),
                f0=FIGURES[0], f1=FIGURES[1], f2=FIGURES[2],
                c0=t["caps"][0], c1=t["caps"][1], c2=t["caps"][2],
            ), encoding="utf-8")
            ctx = await browser.new_context(
                viewport={"width": w, "height": h}, device_scale_factor=1,
                locale="zh-CN" if lang == "zh" else "en-US")
            page = await ctx.new_page()
            await page.goto(f"{base}/og-{lang}.html", wait_until="load")
            await page.wait_for_timeout(200)
            name = out / f"og-{lang}.png"
            await page.screenshot(path=str(name))
            written.append(name)
            await ctx.close()
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    return written


# ---------------------------------------------------------------------------

GROUPS = ("popup", "options", "app", "og")


async def main(groups: set[str], out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            if groups & {"popup", "options"}:
                say("extension panels")
                written += await shoot_extension(browser, out, groups)
            if "og" in groups:
                say("social card")
                written += await shoot_og(browser, out)
            if "app" in groups:
                say("served page")
                written += await shoot_app(browser, out)
        finally:
            await browser.close()
    for p in sorted(written):
        with suppress(Exception):
            import struct
            head = p.read_bytes()[:24]
            iw, ih = struct.unpack(">II", head[16:24])
            print(f"  {p.name:<26} {iw}x{ih}  {p.stat().st_size / 1024:.0f} KB")
    return 0 if written else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="all",
                    help=f"comma-separated subset of {','.join(GROUPS)}")
    ap.add_argument("--out", default=str(ASSETS),
                    help="where to write (default: the site's asset folder)")
    args = ap.parse_args()
    chosen = set(GROUPS) if args.only == "all" else {
        g.strip() for g in args.only.split(",")}
    unknown = chosen - set(GROUPS)
    if unknown:
        sys.exit(f"unknown group(s): {', '.join(sorted(unknown))}")
    raise SystemExit(asyncio.run(main(chosen, Path(args.out))))
