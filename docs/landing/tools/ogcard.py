#!/usr/bin/env python3
"""Render the 1200x630 link-preview cards into ../assets/og-{en,zh}.png.

The card reads its colours from the real style.css and its words from the real
content files, so the shared link matches the website's title and brand.

usage:  python3 tools/ogcard.py          # from docs/landing/
requires: python playwright (pip install playwright && playwright install chromium)
"""

from __future__ import annotations

import html
import shutil
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
LANDING = TOOLS.parent
sys.path.insert(0, str(LANDING))

from content_en import EN  # noqa: E402
from content_zh import ZH  # noqa: E402

SITE = "88lin.github.io/facetmark"
W, H = 1200, 630

CARD = """<!doctype html>
<html lang="{lang}" data-theme="light" data-palette="G">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="palettes.css">
<link rel="stylesheet" href="style.css">
<style>
  html, body {{ margin: 0; }}
  body {{
    position: relative; box-sizing: border-box;
    width: {w}px; height: {h}px; overflow: hidden;
    padding: 62px 72px 58px;
    background: var(--cream); color: var(--ink); font-family: var(--sans);
    display: flex; flex-direction: column; justify-content: space-between;
  }}
  .brand {{
    display: flex; align-items: center; gap: 15px;
    font-weight: 700; font-size: 31px; letter-spacing: -0.022em;
  }}
  .brand .mark {{ width: 40px; height: 40px; flex: none; }}
  .url {{
    position: absolute; top: 72px; right: 72px;
    font-family: var(--mono); font-size: 17px; color: var(--ink-light);
  }}
  .summary {{ font-size: 22px; line-height: 1.65; color: var(--ink-light); margin: 24px 0 0; }}
  h1 {{
    margin: 0; max-width: 1000px; font-weight: 800;
    font-size: {h1}px; line-height: 1.15; letter-spacing: -0.024em;
  }}
  h1 em {{
    font-style: normal; color: var(--accent-ink);
  }}
  .stats {{
    display: flex; gap: 48px; border-top: 1px solid var(--border); padding-top: 24px;
  }}
  .s {{
    display: flex; align-items: baseline; gap: 12px;
  }}
  .s b {{ font-size: 22px; font-weight: 700; }}
  .s span {{ font-size: 17px; color: var(--ink-light); }}
</style>
</head>
<body>
<div class="url">{site}</div>
<div class="brand"><img class="mark" src="favicon.svg" alt=""><span>facetmark</span></div>
<div>
  <h1>{h1_text}</h1>
  <p class="summary">{lede}</p>
</div>
<div class="stats">{stats}</div>
</body>
</html>
"""


def card(t: dict, cjk: bool, h1_px: int) -> str:
    i = t["index"]
    stats = "".join(
        f'<div class="s"><span>{html.escape(label)}</span><b>{html.escape(value)}</b></div>'
        for label, value in i["chips"]
    )
    return CARD.format(
        lang=t["html_lang"],
        w=W,
        h=H,
        h1=h1_px,
        site=SITE,
        cjk=" cjk" if cjk else "",
        kicker=html.escape(i["kicker"]),
        h1_text=i["h1"],
        lede=i["lede"],
        stats=stats,
    )


def shoot(src: Path, png: Path) -> None:
    """One deterministic frame. Python playwright, so the tool needs no npm."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto(src.as_uri(), wait_until="networkidle")
        page.wait_for_timeout(250)
        page.screenshot(path=str(png))
        browser.close()


def main() -> int:
    out_dir = LANDING / "assets"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(LANDING / "style.css", work / "style.css")
        shutil.copy(LANDING / "palettes.css", work / "palettes.css")
        shutil.copy(LANDING / "assets" / "favicon.svg", work / "favicon.svg")
        jobs = [("en", EN, False, 62), ("zh", ZH, True, 64)]
        for code, t, cjk, h1_px in jobs:
            src = work / f"og-{code}.html"
            src.write_text(card(t, cjk, h1_px), encoding="utf-8")
            png = out_dir / f"og-{code}.png"
            shoot(src, png)
            print("  ->", png.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
