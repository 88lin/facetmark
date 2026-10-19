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
    def capture_still(name):
        page.evaluate('''async () => {
            await document.fonts.ready;
            const deadline = performance.now() + 5000;
            let previous = '', stable = performance.now();
            await new Promise((resolve, reject) => {
                const sample = () => {
                    const elements = [...document.querySelectorAll(
                        '.result-row, .preview-drawer, .preview-pane, .page-scroll, .workspace-toolbar, .setup-flow')];
                    const snapshot = JSON.stringify(elements.map(element => {
                        const box = element.getBoundingClientRect(), style = getComputedStyle(element);
                        return [box.x, box.y, box.width, box.height, style.transform, style.opacity, style.filter];
                    }));
                    if (snapshot !== previous || document.querySelector('[data-content-motion], .interaction-ink') ||
                        elements.some(element => element.getAnimations().some(a => a.playState === 'running')))
                        stable = performance.now();
                    previous = snapshot;
                    if (performance.now() - stable >= 250) return resolve();
                    if (performance.now() > deadline) return reject(new Error('Installed layout did not settle'));
                    requestAnimationFrame(sample);
                };
                requestAnimationFrame(sample);
            });
        }''')
        page.screenshot(path=str(output / name))

    capture_still('installed-workbench.png')
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
    capture_still('installed-reader.png')
    narrow_reader = page.locator('.preview-drawer').is_visible()
    return_label = '返回收藏' if narrow_reader else '关闭预览'
    page.get_by_role('button', name=return_label, exact=True).click()
    assert page.get_by_role('textbox', name='搜索书签').input_value() == '合成示例'
    capture_still('installed-collection.png')
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

    # Inspect actual running frames in the installed WebView, not just final
    # screenshots. These steps use only the synthetic library above and never
    # save a settings draft or contact a model provider.
    interaction_evidence = []
    interaction_writes = []
    initial_layout = page.evaluate("localStorage.getItem('fm-collection-layout') === 'list' ? 'list' : 'grid'")

    def record_interaction_write(request):
        if request.method != 'GET' and ('/admin/library/' in request.url
                                       or request.url.split('?')[0].endswith('/admin/settings')):
            interaction_writes.append({'method': request.method, 'url': request.url})

    page.on('request', record_interaction_write)

    def motion_step(label, selectors, action, *, running=False, content=False, direction=None,
                    moving=False, exiting=False):
        page.evaluate('''selectors => {
            const started = performance.now();
            const probe = window.__installedMotion = { frames: [], request: 0 };
            const identities = new WeakMap();
            let nextNode = 0;
            const sample = () => {
                const targets = {};
                for (const selector of selectors) {
                    targets[selector] = [...document.querySelectorAll(selector)].slice(0, 4).map(element => {
                        const style = getComputedStyle(element);
                        const rect = element.getBoundingClientRect();
                        const matrix = new DOMMatrixReadOnly(style.transform === 'none' ? undefined : style.transform);
                        if (!identities.has(element)) identities.set(element, `node-${++nextNode}`);
                        return {
                            key: identities.get(element),
                            transform: style.transform, opacity: style.opacity, filter: style.filter,
                            translateX: matrix.m41, translateY: matrix.m42,
                            inline: { transform: element.style.transform, opacity: element.style.opacity,
                                      filter: element.style.filter, willChange: element.style.willChange },
                            x: Math.round(rect.x * 100) / 100, y: Math.round(rect.y * 100) / 100,
                            inert: element.inert, hidden: element.getAttribute('aria-hidden'),
                            phase: element.dataset.overlayPhase, pointerEvents: style.pointerEvents,
                            animations: element.getAnimations().filter(animation =>
                                animation.effect?.getComputedTiming().iterations !== Infinity
                            ).map(animation => ({
                                state: animation.playState,
                                progress: animation.effect?.getComputedTiming().progress,
                                properties: Object.keys(animation.effect?.getKeyframes()[0] || {}),
                            })),
                        };
                    });
                }
                probe.frames.push({ time: Math.round(performance.now() - started), targets });
                probe.request = requestAnimationFrame(sample);
            };
            sample();
        }''', selectors)
        try:
            action()
            # Bounded sampling includes active and settled frames without
            # asserting an implementation's exact duration or transform value.
            page.wait_for_timeout(650)
        finally:
            frames = page.evaluate('''() => {
                cancelAnimationFrame(window.__installedMotion.request);
                return window.__installedMotion.frames;
            }''')
            interaction_evidence.append({'action': label, 'frames': frames})
        samples = [node for frame in frames for nodes in frame['targets'].values() for node in nodes]
        if running:
            assert any(animation['state'] == 'running' and animation.get('progress') is not None
                       for node in samples for animation in node['animations']), f'{label}: no running DOM animation'
        if content:
            # GSAP is sampled from its actual painted properties, independently
            # of WAAPI. Never combine different nodes or selectors as evidence.
            for selector in selectors:
                selector_samples = [node for frame in frames for node in frame['targets'][selector]]
                by_node = {}
                for node in selector_samples:
                    by_node.setdefault(node['key'], []).append(node)
                assert any(len({node['transform'] for node in values}) > 2
                           and len({node['opacity'] for node in values if 0 < float(node['opacity']) < 1}) > 2
                           and len({node['filter'] for node in values if node['filter'] not in ('none', 'blur(0px)')}) > 2
                           for values in by_node.values()), f'{label}: {selector} has no same-node travel/opacity/focus sequence'
                if direction:
                    assert any(node['translateX'] * direction > 1 for node in selector_samples), f'{label}: incorrect travel direction'
                assert all(node['inline'] == {'transform': '', 'opacity': '', 'filter': '', 'willChange': ''}
                           for node in frames[-1]['targets'][selector]), f'{label}: content retained animated inline styles'
        if moving:
            positions = {}
            for node in samples:
                positions.setdefault(node['key'], set()).add((node['x'], node['y']))
            assert any(len(values) > 2 for values in positions.values()), f'{label}: no intermediate layout positions'
        if exiting:
            for selector in selectors:
                closing = [node for frame in frames for node in frame['targets'][selector]
                           if node.get('phase') == 'closing']
                assert closing, f'{label}: {selector} has no recorded exit phase'
                assert all(node['inert'] and node['hidden'] == 'true' and node['pointerEvents'] == 'none'
                           for node in closing), f'{label}: {selector} still accepts input during exit'

    page.emulate_media(reduced_motion='no-preference')
    page.evaluate('() => document.fonts.ready')
    try:
        header = page.locator('.app-header')
        motion_step('收藏 → 任务', ['.page-scroll'],
                    lambda: header.get_by_role('button', name='任务', exact=True).click(), content=True, direction=1)

        def reverse_navigation():
            for destination in ('设置', '任务', '设置'):
                header.get_by_role('button', name=destination, exact=True).click()
                page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')

        motion_step('任务 → 设置，快速往返后停在设置', ['.page-scroll'],
                    reverse_navigation, content=True)
        assert page.get_by_role('heading', name='设置', exact=True).is_visible()
        # Local Agent discovery may replace the summary input. Embeddings keep
        # an editable model draft regardless of the detected summary provider.
        model = page.locator('input[name="embed_model"]')
        original_model = model.input_value()
        model.fill('synthetic-unsaved-installed-motion-draft')
        motion_step('设置 → 设备同步', ['.settings-panel:not([hidden])'],
                    lambda: page.get_by_role('tab', name='设备同步', exact=True).click(), content=True, direction=1)
        assert not model.is_visible()
        motion_step('设置 → AI 连接', ['.settings-panel:not([hidden])'],
                    lambda: page.get_by_role('tab', name='AI 连接', exact=True).click(), content=True, direction=-1)
        assert model.input_value() == 'synthetic-unsaved-installed-motion-draft'
        model.fill(original_model)
        motion_step('设置 → 收藏', ['.results-column'],
                    lambda: header.get_by_role('button', name='全部书签', exact=True).click(), content=True, direction=-1)
        page.locator('.result-row').nth(1).wait_for(timeout=15000)
        categories = page.locator('.collection-sidebar')
        for category in ('标签', '文件夹'):
            motion_step(f'分类：{category}', ['.collection-sidebar .facet-options'],
                        lambda category=category: categories.get_by_role('button', name=category, exact=True).click(),
                        content=True, direction=1 if category == '标签' else -1)
        second_id = page.locator('.result-row').nth(1).get_attribute('data-bookmark-id')
        layout_label = '列表视图' if initial_layout == 'grid' else '卡片视图'
        motion_step('切换收藏布局', [f'.result-row[data-bookmark-id="{second_id}"]'],
                    lambda: page.get_by_role('button', name=layout_label, exact=True).first.click(), moving=True)
        restore_label = '卡片视图' if initial_layout == 'grid' else '列表视图'
        page.get_by_role('button', name=restore_label, exact=True).first.click()
        motion_step('胶囊按压波纹', ['.interaction-ink'],
                    lambda: categories.get_by_role('button', name='文件夹', exact=True).click(), running=True)
        motion_step('打开新增收藏并清理原按钮波纹', ['.library-dialog'],
                    lambda: page.get_by_role('button', name='新增收藏', exact=True).click(), moving=True)
        assert page.locator('.interaction-ink').count() == 0
        dialog = page.get_by_role('dialog', name='新增收藏', exact=True)
        dialog.locator('.folder-picker-trigger').click()
        folder_search = dialog.get_by_role('textbox', name='搜索文件夹', exact=True)
        folder_search.wait_for()
        motion_step('Escape 只关闭目录', ['.folder-picker-panel'],
                    lambda: folder_search.press('Escape'), exiting=True)
        assert dialog.is_visible()
        motion_step('关闭新增窗口', ['.library-dialog', '.library-dialog-overlay'],
                    lambda: dialog.locator('.folder-picker-trigger').press('Escape'), exiting=True)
        assert page.locator('.library-dialog, .library-dialog-overlay').count() == 0
        page.emulate_media(reduced_motion='reduce')
        motion_step('实时减少动态效果', ['.page-scroll', '.interaction-ink'],
                    lambda: header.get_by_role('button', name='设置', exact=True).click())
        reduced_samples = [node for frame in interaction_evidence[-1]['frames']
                           for nodes in frame['targets'].values() for node in nodes]
        assert not any(animation['state'] == 'running' for node in reduced_samples for animation in node['animations'])
        assert all(node['transform'] == 'none' and node['filter'] == 'none' and float(node['opacity']) == 1
                   for node in reduced_samples), 'Reduced motion retained travel or focus effects'
        assert page.locator('.interaction-ink').count() == 0
        header.get_by_role('button', name='全部书签', exact=True).click()
        page.get_by_role('textbox', name='搜索书签').fill('合成示例')
        page.locator('.result-row').nth(1).wait_for(timeout=15000)
        page.wait_for_function("document.querySelector('.result-count')?.textContent === '2'")
        capture_still('installed-interactions.png')
        assert not link_errors, f'Installed interaction steps raised WebView errors: {link_errors}'
        assert not interaction_writes, f'Installed interaction steps unexpectedly saved data: {interaction_writes}'
    finally:
        # Python None omits the parameter; the explicit "null" value removes
        # Playwright's temporary media override and returns to the OS setting.
        page.emulate_media(reduced_motion='null')
        page.remove_listener('request', record_interaction_write)
        (output / 'installed-interactions.json').write_text(json.dumps({
            'commit': os.environ.get('GITHUB_SHA'),
            'data': 'synthetic installed-library interactions; no saved settings changes',
            'viewport': page.evaluate('({ width: innerWidth, height: innerHeight })'),
            'page_errors': link_errors, 'writes': interaction_writes, 'evidence': interaction_evidence,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
    # Stop the CDP connection with Playwright; do not close the user's app.
