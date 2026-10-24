"""Capture the actual React folder glyph, at review size, in cloud only."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Component rendering runs in GitHub Actions only")
    output = Path("folder-evidence")
    output.mkdir(exist_ok=True)
    handler = partial(SimpleHTTPRequestHandler, directory=str(Path("folder-preview").resolve()))
    errors = []
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(viewport={"width": 900, "height": 560},
                                              record_video_dir=str(output / "raw"),
                                              record_video_size={"width": 900, "height": 560})
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.route("**/*", lambda route: route.continue_()
                           if route.request.url.startswith("http://127.0.0.1:") else route.abort())
                page.goto(f"http://127.0.0.1:{server.server_port}/design/folders.html")
                page.evaluate("() => document.fonts.ready")
                page.locator(".folder-glyph").first.wait_for()
                page.wait_for_timeout(450)
                page.screenshot(path=str(output / "folders-rest.png"))
                for tone in ["amber", "sky", "lilac", "sage"]:
                    button = page.locator(f'button:has([data-tone="{tone}"])')
                    button.hover()
                    page.wait_for_timeout(350)
                    button.click()
                    page.wait_for_timeout(500)
                page.mouse.move(830, 470)
                page.wait_for_timeout(500)
                page.screenshot(path=str(output / "folders-selected.png"))
                page.keyboard.press("Tab")
                page.wait_for_timeout(400)
                page.keyboard.press("Enter")
                page.wait_for_timeout(650)
                video = page.video
                context.close()
                video.save_as(str(output / "folders.webm"))
                browser.close()
        finally:
            server.shutdown()
    subprocess.run(["ffmpeg", "-y", "-i", str(output / "folders.webm"), "-c:v", "libx264",
                    "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(output / "folders.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(output / "folders.webm"), "-filter_complex",
                    "fps=24,scale=900:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse",
                    str(output / "folders.gif")], check=True)
    captures = [{"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in sorted(output.iterdir()) if path.suffix in {".png", ".mp4", ".gif"}]
    (output / "provenance.json").write_text(json.dumps({
        "commit": os.environ["GITHUB_SHA"], "run": os.environ["GITHUB_RUN_ID"],
        "kind": "component review using production FolderGlyph, synthetic names; not the full UI",
        "errors": errors, "captures": captures,
    }, indent=2), encoding="utf-8")
    if errors:
        raise SystemExit(errors)


if __name__ == "__main__":
    main()
