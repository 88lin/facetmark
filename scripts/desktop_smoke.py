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


def request(port, path, token=''):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}',
                                headers={'Authorization': f'Bearer {token}'})
    return urllib.request.urlopen(req, timeout=5)


def ready(process):
    import queue
    events = queue.Queue()

    def drain():
        for line in process.stdout:
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
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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
            second = subprocess.Popen(command, env=env, cwd=temp, stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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
