"""Cloud-only visual studies; no application database or browser profile."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Design study rendering runs in GitHub Actions only")
    output = Path("design-evidence")
    output.mkdir(exist_ok=True)
    records = []
    handler = partial(SimpleHTTPRequestHandler, directory=str(Path.cwd()))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                for source in sorted(Path(".impeccable/mocks/decision").glob("*-study.html")):
                    for width, height in [(1440, 900), (390, 844)]:
                        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
                        page.route("**/*", lambda route: route.continue_()
                                   if route.request.url.startswith("http://127.0.0.1:") else route.abort())
                        page.goto(f"http://127.0.0.1:{server.server_port}/{source.as_posix()}")
                        page.evaluate("() => document.fonts.ready")
                        destination = output / f"{source.stem}-{width}.png"
                        page.screenshot(path=str(destination), animations="disabled")
                        records.append({"file": destination.name, "width": width, "height": height,
                                        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                                        "horizontal_overflow": page.evaluate(
                                            "document.documentElement.scrollWidth > innerWidth")})
                        page.close()
                browser.close()
        finally:
            server.shutdown()
    (output / "provenance.json").write_text(json.dumps({
        "commit": os.environ["GITHUB_SHA"], "run": os.environ["GITHUB_RUN_ID"],
        "kind": "visual studies only, synthetic content, not application screenshots",
        "captures": records,
    }, indent=2), encoding="utf-8")
    if not records:
        raise SystemExit("No visual studies found")


if __name__ == "__main__":
    main()
