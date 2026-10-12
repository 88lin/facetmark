"""Inspect the installed Tauri WebView, exclusively on a disposable CI VM."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
    # Exercise the actual Tauri -> system-browser handoff. The only destination
    # is a disposable loopback server on this GitHub-hosted VM, never a real site.
    opened = threading.Event()
    control_opened = threading.Event()
    link_errors = []
    requests = []
    page.on('pageerror', lambda error: link_errors.append(str(error)))

    class OriginalPage(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append({'path': self.path, 'user_agent': self.headers.get('User-Agent')})
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<h1>Facetmark synthetic original page</h1>')
            if self.path == '/original':
                opened.set()
            elif self.path == '/os-control':
                control_opened.set()

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(('127.0.0.1', 0), OriginalPage) as original_server:
        threading.Thread(target=original_server.serve_forever, daemon=True).start()
        try:
            original_url = f'http://127.0.0.1:{original_server.server_port}/original'
            original_link = page.locator('a.result-title').first
            assert original_link.get_attribute('target') == '_blank'
            # Keep the imported record, substituting only its synthetic link
            # destination so this test can observe the external process request.
            original_link.evaluate('(link, url) => link.href = url', original_url)
            page.evaluate('''() => {
                window.__linkClicks = [];
                window.addEventListener('click', event => {
                    const link = event.target.closest('a');
                    if (link) setTimeout(() => window.__linkClicks.push({
                        href: link.href, prevented: event.defaultPrevented, trusted: event.isTrusted
                    }), 0);
                });
            }''')
            workbench_url = page.url
            original_link.click()
            deadline = time.monotonic() + 30
            while not opened.is_set() and time.monotonic() < deadline:
                page.wait_for_timeout(250)
            if not opened.is_set():
                # A diagnostic control only: it never satisfies the app-click gate.
                control_error = None
                try:
                    os.startfile(original_url.replace('/original', '/os-control'))
                    control_opened.wait(15)
                except OSError as error:
                    control_error = str(error)
                (output / 'external-link-failure.json').write_text(json.dumps({
                    'commit': os.environ.get('GITHUB_SHA'),
                    'clicks': page.evaluate('window.__linkClicks'), 'page_errors': link_errors,
                    'requests': requests, 'os_control_opened': control_opened.is_set(),
                    'os_control_error': control_error, 'path': os.environ.get('PATH'),
                }, indent=2), encoding='utf-8')
                raise AssertionError('The installed app did not open the original URL in the system browser')
            assert not link_errors, f'Original-page click raised WebView errors: {link_errors}'
            assert page.url == workbench_url
            assert page.locator('.bookmark-preview[aria-pressed="true"]').count() == 0
        finally:
            original_server.shutdown()
    page.locator('.bookmark-preview').first.click()
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
        'original_opened_in_system_browser': True,
        'original_requests': requests,
        'original_click_page_errors': link_errors,
        'reader_missing_body_state': True, 'close_preserved_query': True,
        'reader_return_label': return_label,
        'viewport': page.evaluate('({ width: innerWidth, height: innerHeight })'),
        'real_provider_used': False,
    }, indent=2), encoding='utf-8')
    # Stop the CDP connection with Playwright; do not close the user's app.
