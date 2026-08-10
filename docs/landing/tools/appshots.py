"""Re-shoot the eight `/app` frames the landing pages embed.

This replaces the node version that used to live here, for two reasons.

The first is that it was no longer telling the truth.  It fulfilled every
request from a table of invented JSON, which meant the picture came out of
whatever shape that table happened to have -- and the table drifted.  Driving
the real server instead means the frame is produced by the shipped renderer
against the shipped routes, so a response the page mishandles shows up in the
picture rather than in a fixture nobody re-reads.

The second is that it can now be done without giving anything away.
``facetmark demo`` builds a synthetic library offline -- no key, no network,
no real page ever fetched -- so the rule that has always governed this
directory still holds: no one's browsing history goes on a public page.  The
corpus is seeded, so the same command twice gives the same library.

    python docs/landing/tools/appshots.py

Console errors and warnings fail the run.  A screenshot of a page that logged
an exception is a screenshot of a bug, and it should not be quietly committed.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "landing" / "assets"
sys.path.insert(0, str(ROOT / "scripts"))

from browser_check import App  # noqa: E402  (needs the path above)

# 1440 at scale 1, full page: the geometry the committed PNGs already use, and
# wide enough that the three-column census in the library view is the layout a
# reader on a laptop actually sees.
WIDTH = 1440

# An English query in both languages on purpose.  The corpus is synthetic
# English, so a Chinese query would photograph an empty result list; what the
# Chinese frame is for is the translated *interface*, which is exactly what a
# Chinese quickstart illustrated with an English screenshot was getting wrong.
QUERY = "vector index"


async def main() -> int:
    noise: list[str] = []
    with App(size=60) as app:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for lang in ("en", "zh"):
                for theme in ("light", "dark"):
                    ctx = await browser.new_context(
                        viewport={"width": WIDTH, "height": 1000},
                        device_scale_factor=1,
                        locale="zh-CN" if lang == "zh" else "en-US",
                        color_scheme=theme,
                    )
                    page = await ctx.new_page()
                    page.on("console", lambda m: noise.append(f"{m.type}: {m.text}")
                            if m.type in ("error", "warning") else None)
                    page.on("pageerror", lambda e: noise.append(f"pageerror: {e}"))
                    await page.add_init_script(
                        f"localStorage.setItem('fm-lang','{lang}');"
                        f"localStorage.setItem('fm-theme','{theme}');"
                    )
                    await page.goto(f"{app.base}/app", wait_until="networkidle")
                    await page.wait_for_timeout(700)

                    suffix = ("-zh" if lang == "zh" else "") + ("-dark" if theme == "dark" else "")
                    await page.fill("#q", QUERY)
                    await page.keyboard.press("Enter")
                    # Wait for the ranked list to replace the lexical first
                    # paint, not for a timer.
                    await page.wait_for_selector("#results li:nth-child(4)", timeout=20000)
                    await page.wait_for_timeout(900)
                    await shoot(page, f"app-search{suffix}.png")

                    await page.click('[data-view="library"]')
                    await page.wait_for_selector("#stats .block", timeout=20000)
                    await page.wait_for_timeout(900)
                    await shoot(page, f"app-library{suffix}.png")
                    await ctx.close()
            await browser.close()

    if noise:
        print("console was not clean:", *dict.fromkeys(noise), sep="\n  ")
        return 1
    print("console clean")
    return 0


async def shoot(page, name: str) -> None:
    path = OUT / name
    await page.screenshot(path=str(path), full_page=True)
    print(f"  {name:<28} {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
