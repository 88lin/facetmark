#!/usr/bin/env python3
"""Render the 1200x630 link-preview cards into ../assets/og-{en,zh}.png.

The card reads its colours from the real style.css and its words from the real
content files, so it cannot drift away from the page it is advertising.  Two of
the three numbers on the card are negative results; that is deliberate.

usage:  python3 tools/ogcard.py          # from docs/landing/
requires: playwright resolvable by node (npm i playwright && npx playwright install chromium)
"""

from __future__ import annotations

import html
import shutil
import subprocess
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
<link rel="stylesheet" href="style.css">
<style>
  html, body {{ margin: 0; }}
  body {{
    position: relative; box-sizing: border-box;
    width: {w}px; height: {h}px; overflow: hidden;
    padding: 62px 72px 58px;
    background: var(--paper); color: var(--ink); font-family: var(--sans);
    display: flex; flex-direction: column; justify-content: space-between;
  }}
  .brand {{
    display: flex; align-items: center; gap: 15px;
    font-weight: 700; font-size: 31px; letter-spacing: -0.022em;
  }}
  .brand .mark {{
    width: 40px; height: 40px; border-radius: 10px; flex: none;
    background:
      linear-gradient(135deg, var(--accent) 0 50%, transparent 50% 100%),
      linear-gradient(135deg, var(--warn) 0 100%);
  }}
  .url {{
    position: absolute; top: 72px; right: 72px;
    font-family: var(--mono); font-size: 17px; color: var(--ink-2);
  }}
  .kick {{
    font-size: 18px; font-weight: 700; letter-spacing: 0.15em;
    text-transform: uppercase; color: var(--ink-2); margin: 0 0 20px;
  }}
  .kick.cjk {{ letter-spacing: 0.07em; text-transform: none; font-size: 20px; }}
  .kick::after {{
    content: ""; display: block; width: 40px; height: 3px; border-radius: 3px;
    margin: 14px 0 0; background: var(--accent);
  }}
  h1 {{
    margin: 0; max-width: 1000px; font-weight: 800;
    font-size: {h1}px; line-height: 1.15; letter-spacing: -0.024em;
  }}
  h1 em {{ font-style: normal; color: var(--accent-ink); }}
  .stats {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 36px;
    border-top: 1px solid var(--line); padding-top: 24px;
  }}
  .s b {{ display: block; font-size: 42px; font-weight: 800; letter-spacing: -0.02em; line-height: 1; }}
  .s.good b {{ color: var(--pass); }}
  .s.bad b {{ color: var(--fail); }}
  .s span {{ display: block; margin-top: 10px; font-size: 17px; line-height: 1.35; color: var(--ink-2); }}
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


def main() -> int:
    out_dir = LANDING / "assets"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(LANDING / "style.css", work / "style.css")
        jobs = [("en", EN, False, 62), ("zh", ZH, True, 64)]
        for code, t, cjk, h1_px in jobs:
            src = work / f"og-{code}.html"
            src.write_text(card(t, cjk, h1_px), encoding="utf-8")
            png = out_dir / f"og-{code}.png"
            r = subprocess.run(
                ["node", str(TOOLS / "shot.js"), str(src), str(png), str(W), str(H), "1"],
                capture_output=True,
                text=True,
            )
            sys.stdout.write(r.stdout)
            if r.returncode != 0:
                sys.stderr.write(r.stderr)
                return r.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
