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
    # Exercise the installed app's real import/search/reader flow as well as setup.
    # This disposable export never reads a browser profile or contacts its URLs.
    page.locator('input[type=file]').set_input_files({
        'name': 'facetmark-synthetic-ci.html',
        'mimeType': 'text/html',
        'buffer': (
            '<!DOCTYPE NETSCAPE-Bookmark-file-1><DL>'
            '<DT><A HREF="https://notes.example/reading">合成示例：为收藏留下可以找回的线索</A>'
            '<DT><A HREF="https://design.example/context">合成示例：保持阅读与检索的上下文</A>'
            '</DL>'
        ).encode(),
    })
    page.get_by_role('status').filter(has_text='导入完成').wait_for(timeout=15000)
    page.get_by_role('button', name='先用关键词检索', exact=True).click()
    page.get_by_role('textbox', name='搜索书签').fill('合成示例')
    page.locator('.result-row').first.wait_for(timeout=15000)
    page.locator('.result-row').first.click()
    page.get_by_text('正文还未保存', exact=True).wait_for(timeout=15000)
    page.screenshot(path=str(output / 'installed-reader.png'))
    narrow_reader = page.locator('.preview-drawer').is_visible()
    return_label = '返回收藏' if narrow_reader else '关闭预览'
    page.get_by_role('button', name=return_label, exact=True).click()
    assert page.get_by_role('textbox', name='搜索书签').input_value() == '合成示例'
    page.screenshot(path=str(output / 'installed-collection.png'))
    (output / 'installed-reader.json').write_text(json.dumps({
        'commit': os.environ.get('GITHUB_SHA'), 'data': 'synthetic HTML import only',
        'import_rendered': True, 'keyword_search': True,
        'reader_missing_body_state': True, 'close_preserved_query': True,
        'reader_return_label': return_label,
        'viewport': page.evaluate('({ width: innerWidth, height: innerHeight })'),
        'real_provider_used': False,
    }, indent=2), encoding='utf-8')
    # Stop the CDP connection with Playwright; do not close the user's app.
