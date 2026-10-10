"""Lifecycle for the bundled local service. No browser profile is opened here.

The desktop shell reads newline-delimited readiness records from stdout and
sends ``stop`` on stdin. Authentication stays in the existing token file, never
in argv, URLs, or the readiness record. An existing compatible service is
reused only after an authenticated identity check against the same data path.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import socket
import sqlite3
import sys
import threading
import time
from pathlib import Path

from . import __version__


def database_identity(path: Path) -> str:
    return hashlib.sha256(os.path.normcase(str(path.resolve())).encode()).hexdigest()


class InstanceLock:
    def __init__(self, path: Path):
        self.path = path
        self.file = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open('a+b')
        self.file.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                self.file.close()
                self.file = None
                return False
        else:
            import fcntl
            try:
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                self.file.close()
                self.file = None
                return False
        return True

    def close(self):
        if self.file:
            self.file.close()
            self.file = None


def emit(event: str, **values) -> None:
    print(json.dumps({'event': event, **values}, ensure_ascii=True), flush=True)


def read_manifest(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError):
        return {}


def compatible_service(settings, port: int) -> bool:
    import httpx

    from .service import pairing_token
    token = pairing_token(settings, create=False)
    if not token or not 0 < port < 65536:
        return False
    try:
        with httpx.Client(trust_env=False, timeout=1.5) as client:
            r = client.get(f'http://127.0.0.1:{port}/admin/runtime',
                           headers={'Authorization': f'Bearer {token}'})
            r.raise_for_status()
            data = r.json()
        return (data.get('service') == 'facetmark' and data.get('version') == __version__
                and data.get('database_identity') == database_identity(settings.db_path))
    except (httpx.HTTPError, ValueError, TypeError):
        return False


def reserve_port(preferred: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Keep the socket bound through server startup: no check-then-bind race.
    if os.name == 'nt':
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        sock.bind(('127.0.0.1', preferred))
    except OSError:
        sock.bind(('127.0.0.1', 0))
    sock.listen(128)
    sock.setblocking(False)
    return sock


def backup_on_upgrade(settings) -> None:
    stamp = settings.data_dir / 'desktop-version.json'
    previous = read_manifest(stamp).get('version')
    if previous != __version__ and settings.db_path.is_file():
        # SQLite's backup API includes committed WAL pages; copying .db alone does not.
        backup_dir = settings.data_dir / 'backups'
        backup_dir.mkdir(exist_ok=True)
        suffix = time.strftime('%Y%m%d-%H%M%S')
        with contextlib.closing(sqlite3.connect(settings.db_path)) as source, contextlib.closing(
            sqlite3.connect(backup_dir / f'before-{__version__}-{suffix}.db')
        ) as dest:
            source.backup(dest)
        config = settings.data_dir / 'config.toml'
        if config.is_file():
            import shutil
            shutil.copy2(config, backup_dir / f'before-{__version__}-{suffix}.toml')
    # Written only after startup succeeds; failed migrations keep the old stamp.


async def run_service(settings, *, parent_pid: int = 0) -> None:
    import uvicorn

    from .api import create_app

    manifest = settings.data_dir / 'desktop-runtime.json'
    lock = InstanceLock(settings.data_dir / '.desktop.lock')
    acquired = lock.acquire()
    candidates = [read_manifest(manifest).get('port'), settings.port]
    # The first shell may still be starting. Wait for its authenticated endpoint.
    for _attempt in range(30 if not acquired else 1):
        for port in dict.fromkeys(candidates):
            if isinstance(port, int) and await asyncio.to_thread(compatible_service, settings, port):
                lock.close()
                emit('ready', port=port, version=__version__, owned=False)
                return
        if not acquired:
            await asyncio.sleep(.3)
            candidates[0] = read_manifest(manifest).get('port')
    if not acquired:
        raise RuntimeError('Another Facetmark instance is starting or is incompatible. Close it and retry.')
    sock = None
    try:
        backup_on_upgrade(settings)
        sock = reserve_port(settings.port)
        port = sock.getsockname()[1]
        settings = settings.model_copy(update={'host': '127.0.0.1', 'port': port})
        app = create_app(settings)
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port,
                                loop='asyncio', http='h11', log_level='warning', access_log=False))

        def control():
            for line in sys.stdin:
                if line.strip() == 'stop':
                    emit('stopping', phase='stdin')
                    if os.environ.get('FACETMARK_DIAGNOSTICS') == '1':
                        import faulthandler
                        faulthandler.dump_traceback_later(12)
                    server.should_exit = True
                    return
            if parent_pid:
                server.should_exit = True

        threading.Thread(target=control, daemon=True).start()

        if parent_pid and os.name == 'nt':
            def watch_parent():
                import ctypes
                from ctypes import wintypes
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                kernel.OpenProcess.restype = wintypes.HANDLE
                kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
                kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                handle = kernel.OpenProcess(0x00100000, False, parent_pid)
                if handle:
                    kernel.WaitForSingleObject(handle, 0xFFFFFFFF)
                    kernel.CloseHandle(handle)
                    server.should_exit = True
            threading.Thread(target=watch_parent, daemon=True).start()

        async def ready():
            while not server.started:
                await asyncio.sleep(.05)
            payload = {'pid': os.getpid(), 'port': port, 'version': __version__}
            temp = manifest.with_suffix('.tmp')
            temp.write_text(json.dumps(payload), encoding='utf-8')
            temp.replace(manifest)
            (settings.data_dir / 'desktop-version.json').write_text(
                json.dumps({'version': __version__}), encoding='utf-8')
            emit('ready', port=port, version=__version__, owned=True)

        ready_task = asyncio.create_task(ready())
        try:
            await server.serve(sockets=[sock])
        finally:
            emit('stopping', phase='server_closed')
            if os.environ.get('FACETMARK_DIAGNOSTICS') == '1':
                import faulthandler
                faulthandler.cancel_dump_traceback_later()
            ready_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await ready_task
    finally:
        if sock:
            sock.close()
        if read_manifest(manifest).get('pid') == os.getpid():
            manifest.unlink(missing_ok=True)
        lock.close()


def self_test() -> dict:
    """Exercise native extensions and package data without network or user data."""
    import tempfile

    from .db import open_db
    from .fetch.extract import extract
    from .text import segment
    from .web import INDEX_HTML, STATIC_DIR
    with tempfile.TemporaryDirectory(prefix='facetmark-打包检验 ') as directory:
        conn = open_db(Path(directory) / 'test.db')
        try:
            version = conn.execute('select vec_version()').fetchone()[0]
            conn.execute('CREATE VIRTUAL TABLE temp.packaging_fts USING fts5(text)')
            conn.execute("INSERT INTO temp.packaging_fts VALUES('书签 search')")
            assert conn.execute("SELECT count(*) FROM temp.packaging_fts WHERE packaging_fts MATCH 'search'").fetchone()[0] == 1
        finally:
            conn.close()
        text = 'A bookmark library helps people rediscover useful information. ' * 40
        result = extract(f'<html><head><title>Bookmarks</title></head><body><article><h1>Bookmarks</h1><p>{text}</p></article></body></html>')
        assert result.ok, 'HTML extraction unavailable'
        assert segment('中文书签检索'), 'Chinese dictionary unavailable'
        assert INDEX_HTML.is_file() and list(STATIC_DIR.iterdir()), 'Web assets missing'
    return {'ok': True, 'version': __version__, 'sqlite_vec': version, 'frozen': bool(getattr(sys, 'frozen', False))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--parent-pid', type=int, default=0)
    parser.add_argument('--data-dir', type=Path)
    args = parser.parse_args()
    try:
        if args.self_test:
            emit('self-test', **self_test())
            return
        from .config import Settings
        if args.data_dir:
            os.environ['FACETMARK_DATA_DIR'] = str(args.data_dir)
        settings = Settings()
        settings.ensure_dirs()
        # A desktop shortcut's working directory must not import an unrelated .env.
        os.chdir(settings.data_dir)
        settings = Settings()
        asyncio.run(run_service(settings, parent_pid=args.parent_pid))
    except Exception as exc:
        emit('error', message=f'{type(exc).__name__}: {exc}')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
