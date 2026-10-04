"""Inspect the installed Tauri WebView, exclusively on a disposable CI VM."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import Error, sync_playwright

if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
    raise SystemExit('Installed WebView inspection is restricted to GitHub-hosted runners')

output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=True)
with sync_playwright() as playwright:
    # The splash WebView is destroyed just before the main one is created.
    # Runtime readiness alone does not mean the main WebView's CDP port exists.
    deadline = time.monotonic() + 60
    while True:
        try:
            browser = playwright.chromium.connect_over_cdp('http://127.0.0.1:9223', timeout=5000)
            break
        except Error:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.5)
    deadline = time.monotonic() + 45
    page = None
    while time.monotonic() < deadline:
        page = next((p for context in browser.contexts for p in context.pages
                     if p.url.startswith('http://127.0.0.1:') and '/app' in p.url), None)
        if page:
            break
        time.sleep(.25)
    assert page is not None, 'Installed app did not navigate to the local workbench'
    page.locator('#root .app-shell').wait_for(timeout=30000)
    page.locator('.setup-flow').wait_for(timeout=30000)
    page.screenshot(path=str(output / 'installed-workbench.png'))
    (output / 'installed-webview.json').write_text(json.dumps({
        'url': page.url, 'react_root_rendered': True,
        'setup_rendered': True, 'title': page.title(),
        'body_text': page.locator('h1').first.inner_text(),
        'browser': browser.version, 'synthetic_empty_library': True,
    }, indent=2), encoding='utf-8')
    # Stop the CDP connection with Playwright; do not close the user's app.
