"""CI-only frozen-service checks; no download and no real browser data."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


def request(port, path, token='', *, payload=None, headers=None):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}',
        data=json.dumps(payload).encode('utf-8') if payload is not None else None,
        headers={'Authorization': f'Bearer {token}',
                 **({'Content-Type': 'application/json'} if payload is not None else {}),
                 **(headers or {})})
    return urllib.request.urlopen(req, timeout=5)


def mcp_check(port, pairing_token):
    """Actual HTTP protocol calls to the frozen child, without a Python client."""
    protocol = '2025-03-26'
    headers = {'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': protocol}

    def rpc(token, method, params=None):
        with request(port, '/mcp/', token, payload={'jsonrpc': '2.0', 'id': 1,
                'method': method, 'params': params or {}}, headers=headers) as response:
            assert response.status == 200
            value = json.load(response)
            assert 'error' not in value, 'Frozen MCP returned a protocol error'
            return value['result']

    try:
        rpc('', 'initialize')
        raise AssertionError('MCP must be disabled until enabled in settings')
    except urllib.error.HTTPError as error:
        assert error.code == 404
    with request(port, '/admin/mcp', pairing_token, payload={'enabled': True}) as response:
        configured = json.load(response)
    assert configured['running'] and configured['transport_ready']
    token = configured['token']
    assert token and token != pairing_token
    assert configured['endpoint'] == f'http://127.0.0.1:{port}/mcp/'
    for unauthorized in ('', pairing_token):
        try:
            rpc(unauthorized, 'tools/list')
            raise AssertionError('MCP accepted browser or missing authority')
        except urllib.error.HTTPError as error:
            assert error.code == 401
    initialized = rpc(token, 'initialize', {'protocolVersion': protocol,
        'capabilities': {}, 'clientInfo': {'name': 'facetmark-frozen-smoke', 'version': '1'}})
    assert initialized['serverInfo']['name'] == 'facetmark'
    with request(port, '/mcp/', token, payload={'jsonrpc': '2.0',
            'method': 'notifications/initialized'}, headers=headers) as notification:
        assert notification.status == 202
    tools = rpc(token, 'tools/list')['tools']
    resources = rpc(token, 'resources/list')['resources']
    templates = rpc(token, 'resources/templates/list')['resourceTemplates']
    assert len(tools) == 9 and len(resources) == 1 and len(templates) == 2
    assert any(tool['name'] == 'save_bookmark' for tool in tools)
    created = rpc(token, 'tools/call', {'name': 'save_bookmark', 'arguments': {
        'url': 'https://synthetic.example/frozen-mcp', 'title': 'Frozen MCP synthetic bookmark'}})
    assert not created.get('isError', False)
    record = created.get('structuredContent') or json.loads(created['content'][0]['text'])
    found = rpc(token, 'tools/call', {'name': 'get_bookmark', 'arguments': {
        'bookmark_id': record['bookmark_id']}})
    assert not found.get('isError', False)
    bookmark = found.get('structuredContent') or json.loads(found['content'][0]['text'])
    assert bookmark['url'] == 'https://synthetic.example/frozen-mcp'
    with request(port, '/admin/mcp', pairing_token, payload={'rotate_token': True}) as response:
        rotated = json.load(response)
    assert rotated['token'] != token
    try:
        rpc(token, 'tools/list')
        raise AssertionError('MCP retained the old token after rotation')
    except urllib.error.HTTPError as error:
        assert error.code == 401
    with request(port, '/admin/mcp', pairing_token, payload={'enabled': False}) as response:
        assert json.load(response)['running'] is False
    try:
        rpc(rotated['token'], 'tools/list')
        raise AssertionError('MCP remained available after disabling')
    except urllib.error.HTTPError as error:
        assert error.code == 404
    return {'transport': 'streamable-http', 'real_http_socket': True,
        'tools': len(tools), 'resources': len(resources), 'templates': len(templates),
        'independent_token': True, 'rotation_revokes_old_token': True,
        'disable_revokes_access': True, 'synthetic_write_read': True}


def ready(process):
    import queue
    events = queue.Queue()

    def drain():
        for line in process.stdout:
            print(f"service[{process.pid}]: {line.rstrip()}", flush=True)
            try:
                event = json.loads(line)
                if event.get('event') in ('ready', 'error'):
                    events.put(event)
            except ValueError:
                pass
    threading.Thread(target=drain, daemon=True).start()
    event = events.get(timeout=45)
    assert event['event'] == 'ready', event
    return event


def main():
    exe = Path(sys.argv[1]).resolve()
    # Neither Python, node nor the source checkout is discoverable to the child.
    env = {k: v for k, v in os.environ.items() if not k.startswith(('PYTHON', 'FACETMARK_'))}
    env['PATH'] = os.path.join(os.environ['SYSTEMROOT'], 'System32')
    env['PYTHONNOUSERSITE'] = '1'
    env['FACETMARK_DIAGNOSTICS'] = '1'
    evidence = {'frozen_service': str(exe), 'no_python_on_child_path': True, 'checks': []}
    with tempfile.TemporaryDirectory(prefix='Facetmark 中文 路径 ') as temporary:
        temp = Path(temporary)
        result = subprocess.run([str(exe), '--self-test'], env=env, cwd=temp,
                                capture_output=True, text=True, encoding='utf-8', timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        evidence['checks'].append({'self_test': json.loads(result.stdout.strip().splitlines()[-1])})
        blocker = socket.socket()
        blocker.bind(('127.0.0.1', 8787))
        blocker.listen(1)
        data = temp / '资料库'
        command = [str(exe), '--data-dir', str(data)]
        started = time.monotonic()
        process = subprocess.Popen(command, env=env, cwd=temp, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8')
        try:
            first = ready(process)
            port = first['port']
            assert port != 8787 and first['owned'] is True
            evidence['startup_seconds'] = round(time.monotonic() - started, 2)
            token = (data / 'pairing-token.txt').read_text().strip()
            with request(port, '/health') as response:
                assert json.load(response)['ok']
            with request(port, '/app') as response:
                assert response.status == 200 and b'<!' in response.read()[:100]
            with request(port, '/admin/runtime', token) as response:
                assert json.load(response)['service'] == 'facetmark'
            with request(port, '/quick?q=search', token) as response:
                assert response.status == 200
            try:
                request(port, '/admin/runtime', 'wrong')
                raise AssertionError('Runtime identity must be authenticated')
            except urllib.error.HTTPError as error:
                assert error.code == 401
            evidence['mcp'] = mcp_check(port, token)
            second = subprocess.Popen(command, env=env, cwd=temp, stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, encoding='utf-8')
            try:
                reused = ready(second)
                assert reused['port'] == port and reused['owned'] is False
                assert second.wait(timeout=15) == 0
            finally:
                if second.poll() is None:
                    second.kill()
                    second.wait()
            evidence['checks'] += ['port_collision', 'unicode_path', 'static_assets',
                                   'keyword_search', 'authenticated_identity', 'single_data_directory']
        finally:
            if process.poll() is None:
                process.stdin.write('stop\n')
                process.stdin.flush()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise AssertionError('Service did not shut down gracefully') from None
            blocker.close()
        assert (data / 'facetmark.db').is_file()
        assert not (data / 'desktop-runtime.json').exists()
        evidence['checks'].append('graceful_shutdown_preserves_data')
    destination = Path('.desktop-build/evidence')
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'frozen-service.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
