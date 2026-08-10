#!/usr/bin/env python3
"""Render the 1200x630 link-preview cards into ../assets/og-{en,zh}.png.

The card reads its colours from the real style.css and its words from the real
content files, so it cannot drift away from the page it is advertising.  Two of
the three numbers on the card are negative results; that is deliberate.

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
<html lang="{lang}" data-theme="light">
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
  .brand .mark {{
    width: 40px; height: 40px; border-radius: 10px; flex: none;
    background:
      linear-gradient(135deg, var(--brand) 0 50%, transparent 50% 100%),
      linear-gradient(135deg, var(--highlight) 0 100%);
  }}
  .url {{
    position: absolute; top: 72px; right: 72px;
    font-family: var(--mono); font-size: 17px; color: var(--ink-light);
  }}
  .kick {{
    font-size: 18px; font-weight: 700; letter-spacing: 0.15em;
    text-transform: uppercase; color: var(--ink-light); margin: 0 0 20px;
  }}
  .kick.cjk {{ letter-spacing: 0.07em; text-transform: none; font-size: 20px; }}
  .kick::after {{
    content: ""; display: block; width: 40px; height: 3px; border-radius: 3px;
    margin: 14px 0 0; background: var(--brand);
  }}
  h1 {{
    margin: 0; max-width: 1000px; font-weight: 800;
    font-size: {h1}px; line-height: 1.15; letter-spacing: -0.024em;
  }}
  h1 em {{
    font-style: normal; color: var(--accent-ink);
    background: linear-gradient(transparent 62%, rgba(var(--highlight-rgb), 0.4) 62%);
    padding: 0 0.06em; border-radius: 3px;
  }}
  .stats {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
  }}
  .s {{
    padding: 20px 22px 22px; border-radius: 16px;
    border: 2px dashed var(--brand); background: var(--blue-wash);
  }}
  .s:nth-child(2) {{ border-color: var(--warning); background: var(--yellow-soft); }}
  .s:nth-child(3) {{ border-color: var(--peach); background: var(--peach-soft); }}
  .s b {{ display: block; font-size: 42px; font-weight: 800; letter-spacing: -0.02em; line-height: 1; }}
  .s.good b {{ color: var(--success); }}
  .s.bad b {{ color: var(--danger-strong); }}
  .s span {{ display: block; margin-top: 10px; font-size: 17px; line-height: 1.35; color: var(--ink-light); }}
</style>
</head>
<body>
<div class="url">{site}</div>
<div class="brand"><span class="mark"></span><span>facetmark</span></div>
<div>
  <p class="kick{cjk}">{kicker}</p>
  <h1>{h1_text}</h1>
</div>
<div class="stats">{stats}</div>
</body>
</html>
"""


def card(t: dict, cjk: bool, h1_px: int) -> str:
    i = t["index"]
    stats = "".join(
        f'<div class="s {kind}"><b>{html.escape(num)}</b>'
        f"<span>{html.escape(label)}</span></div>"
        for num, label, kind in i["meas_stats"]
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
