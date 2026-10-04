"""Write routes for the web UI: import, index, and settings.

Everything else the service exposes is a read. These six routes are the only
ones that change the library or the configuration, and they exist for one
reason: without them a first-time user who opens ``/app`` sees an empty
database and the only way forward is a terminal. ``facetmark import`` and
``facetmark index`` are two commands, but they are two commands *after*
installing Python, and that is where people stop.

Three gates, all three required:

1. the pairing token, same as every other non-public route;
2. a loopback TCP peer -- a LAN-bound service answers 403 here even with a
   valid token, because "administer my bookmark index" is not a thing to offer
   over a network on the strength of a shared secret in a text file;
3. ``FACETMARK_ADMIN_API``, which turns the group off entirely.

There is no remote escape hatch on purpose. Anyone who genuinely needs this
from another machine has SSH port forwarding, which authenticates properly and
leaves the service exactly as exposed as it was.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_args, get_origin

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from . import service
from .config import Settings, split_list
from .configfile import config_path, external_setting_keys, read_config, update_config
from .db import open_db
from .importers import decode_bookmark_bytes
from .privacy import refresh_privacy
from .providers import (
    MockProvider,
    OpenAICompatibleProvider,
    ProviderError,
    SplitProvider,
    get_provider,
)

#: Stage names emitted by :func:`service.index_all`, in the order it runs them.
#: The UI draws a progress bar from this, so it is asserted against the real
#: call in the test suite rather than trusted.
INDEX_STAGES = (
    "fetch",
    "enrich",
    "embed_content",
    "filter_intents",
    "embed_intents",
    "sessions",
    "edges",
)

#: Refuse bodies larger than this. A Netscape export of 50k bookmarks is about
#: 12 MB; 64 MB is generous and still bounded, which matters because the body
#: is decoded into memory rather than streamed to disk.
MAX_UPLOAD_BYTES = 64 * 1024 * 1024

#: Settings the UI is allowed to write. Deliberately not "every field": the
#: retrieval constants are load-bearing for numbers published in the README,
#: and a text box is the wrong place to discover that.
WRITABLE = (
    "api_key",
    "base_url",
    "chat_base_url", "chat_api_key", "chat_allow_no_key",
    "embed_base_url", "embed_api_key", "embed_allow_no_key",
    "chat_model",
    "chat_extra_body",
    "chat_model_fallbacks",
    "embed_model",
    "embed_dim",
    "embed_send_dimensions",
    "embed_batch_size",
    "embed_backend",
    "local_embed_path",
    "request_timeout",
    "fetch_concurrency",
    "enrich_concurrency",
    "privacy_excluded_domains",
)

#: Writable fields that hold a sequence. Read off the model rather than typed
#: out, because a hand-written list is exactly what goes stale when the next
#: tuple-valued setting is added -- and the failure mode is a 400 the UI cannot
#: explain, or a string assigned to a tuple field.
TUPLE_FIELDS = frozenset(
    name
    for name in WRITABLE
    if (
        get_origin(Settings.model_fields[name].annotation) is tuple
        or any(get_origin(arg) is tuple for arg in get_args(Settings.model_fields[name].annotation))
    )
)

#: Changing these mid-flight would leave the running process disagreeing with
#: the file it just wrote, so the UI says "restart to apply" instead of
#: pretending.
NEEDS_RESTART = frozenset({"embed_dim", "embed_backend", "local_embed_path", "embed_model",
                           "embed_base_url", "embed_api_key", "embed_allow_no_key", "embed_send_dimensions"})
SECRETS = frozenset({'api_key', 'chat_api_key', 'embed_api_key'})

_LOOPBACK_PEERS = frozenset({"127.0.0.1", "::1"})


class _Cancelled(Exception):
    """Raised inside the progress callback to unwind a running index."""


# ---------------------------------------------------------------------------
# job state
# ---------------------------------------------------------------------------


@dataclass
class Stage:
    name: str
    value: Any
    seconds: float


@dataclass
class IndexJob:
    """One run of :func:`service.index_all`, observable while it runs."""

    id: str
    fetch: bool
    limit: int | None
    force: bool
    started_at: float
    planned: tuple[str, ...]
    state: str = "running"  # running | done | failed | cancelled
    stages: list[Stage] = field(default_factory=list)
    log: deque[str] = field(default_factory=lambda: deque(maxlen=200))
    error: str | None = None
    finished_at: float | None = None
    cancel_requested: bool = False

    def as_dict(self) -> dict:
        done = [s.name for s in self.stages]
        return {
            "id": self.id,
            "state": self.state,
            "planned": list(self.planned),
            "done": done,
            # The stage that is running now, or `null` once the job is over.
            "current": next(
                (s for s in self.planned if s not in done), None
            ) if self.state == "running" else None,
            "progress": round(len(done) / len(self.planned), 4) if self.planned else 1.0,
            "stages": [{"name": s.name, "value": s.value, "seconds": round(s.seconds, 2)}
                       for s in self.stages],
            "elapsed": round((self.finished_at or time.monotonic()) - self.started_at, 2),
            "error": self.error,
            "cancel_requested": self.cancel_requested,
            "log": list(self.log),
            "params": {"fetch": self.fetch, "limit": self.limit, "force": self.force},
        }


def _summarise(name: str, value: Any) -> str:
    """One log line per stage. Counts, not objects."""
    if isinstance(value, dict):
        parts = [f"{k}={v}" for k, v in value.items()
                 if isinstance(v, (int, float, str)) and not isinstance(v, bool)]
        body = " ".join(parts[:6]) or "ok"
    else:
        body = str(value)
    return f"{name}: {body}"


class JobRunner:
    """At most one index job per process.

    Single-flight rather than a queue. Two concurrent index runs over one
    SQLite file would interleave writes to the same rows and produce a report
    that describes neither run, and nobody has ever wanted two.
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        self.job: IndexJob | None = None
        self._task: asyncio.Task | None = None
        self.path = data_dir / 'last-index-job.json' if data_dir else None
        self.previous = None
        if self.path:
            try:
                self.previous = json.loads(self.path.read_text(encoding='utf-8'))
                if self.previous.get('state') == 'running':
                    self.previous['state'] = 'interrupted'
            except (OSError, ValueError, AttributeError):
                self.previous = None

    def persist(self) -> None:
        if self.path and self.job:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(self.job.as_dict()), encoding='utf-8')
            with contextlib.suppress(OSError):
                tmp.chmod(0o600)
            tmp.replace(self.path)

    async def shutdown(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    @property
    def running(self) -> bool:
        return self.job is not None and self.job.state == "running"

    def start(self, settings: Settings, *, fetch: bool, limit: int | None, force: bool) -> IndexJob:
        if self.running:
            raise RuntimeError("an index job is already running")
        planned = INDEX_STAGES if fetch else INDEX_STAGES[1:]
        job = IndexJob(
            id=uuid.uuid4().hex[:12],
            fetch=fetch,
            limit=limit,
            force=force,
            started_at=time.monotonic(),
            planned=planned,
        )
        job.log.append(f"started: fetch={fetch} limit={limit} force={force}")
        self.job = job
        self.persist()
        self._task = asyncio.create_task(self._run(job, settings.model_copy(deep=True)))
        return job

    def cancel(self) -> bool:
        """Ask the running job to stop at the next stage boundary.

        Not a kill. :func:`service.index_all` reports progress between stages
        and nowhere inside them, so the honest contract is "it will stop after
        the stage it is in", and the UI says exactly that. Tearing the task
        down mid-stage would abandon a half-written embedding table, which is
        worse than waiting.
        """
        if not self.running or self.job is None:
            return False
        self.job.cancel_requested = True
        self.job.log.append("cancel requested; stopping after the current stage")
        self.persist()
        return True

    async def _run(self, job: IndexJob, settings: Settings) -> None:
        # Its own connection. The service connection is guarded by a single
        # asyncio lock that every search takes, and an index run holding that
        # for minutes would make the UI look hung. WAL means a second writer
        # blocks only on the write itself, which is short.
        conn = None
        provider = None
        last = time.monotonic()

        def progress(name: str, value: Any) -> None:
            nonlocal last
            now = time.monotonic()
            job.stages.append(Stage(name=name, value=value, seconds=now - last))
            job.log.append(_summarise(name, value))
            self.persist()
            last = now
            if job.cancel_requested:
                raise _Cancelled

        try:
            conn = open_db(settings.db_path, same_thread=False)
            provider = get_provider(settings)
            await service.index_all(
                conn,
                provider=provider,
                settings=settings,
                fetch=job.fetch,
                limit=job.limit,
                force=job.force,
                progress=progress,
            )
            job.state = "done"
            job.log.append("finished")
        except _Cancelled:
            job.state = "cancelled"
            job.log.append("cancelled")
            with contextlib.suppress(Exception):
                conn.commit()
        except asyncio.CancelledError:  # pragma: no cover - process shutdown
            job.state = "interrupted"
            job.log.append("interrupted by shutdown; completed items can be reused")
            raise
        except Exception as exc:  # noqa: BLE001 - surfaced to the operator
            job.state = "failed"
            job.error = safe_error(exc, settings)
            job.log.append(job.error)
        finally:
            job.finished_at = time.monotonic()
            self.persist()
            if provider is not None:
                with contextlib.suppress(Exception):
                    await provider.aclose()
            with contextlib.suppress(Exception):
                conn.close()


# ---------------------------------------------------------------------------
# request models
# ---------------------------------------------------------------------------


class IndexRequest(BaseModel):
    fetch: bool = True
    """Crawl page bodies first. Off is the fast path for a re-index."""
    limit: int | None = Field(default=None, ge=1)
    force: bool = False
    confirmed: bool = False
    """Consent to send indexable titles, URLs and extracted text to configured models."""


class SettingsPatch(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    """Keys from :data:`WRITABLE`. ``null`` clears one back to its default."""


class ProbeRequest(BaseModel):
    """Credentials to try *without* saving them.

    Separate from the patch on purpose: the common failure is a key that is
    valid for chat and silently absent from ``/embeddings``, and finding that
    out should not require first writing a broken configuration to disk.
    """

    api_key: str | None = None
    base_url: str | None = None
    chat_model: str | None = None
    chat_extra_body: str | None = None
    embed_model: str | None = None
    chat_base_url: str | None = None
    chat_api_key: str | None = None
    chat_allow_no_key: bool | None = None
    embed_base_url: str | None = None
    embed_api_key: str | None = None
    embed_allow_no_key: bool | None = None
    embed_dim: int | None = Field(default=None, ge=1)
    embed_send_dimensions: bool | None = None
    embed_backend: str | None = None
    local_embed_path: str | None = None
    channel: str | None = None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def mask(value: str) -> str:
    """Enough of a secret to recognise, never enough to use."""
    if not value:
        return ""
    return '••••' if len(value) <= 8 else f"{value[:3]}...{value[-4:]}"


def safe_error(exc: Exception, settings: Settings) -> str:
    text = f'{type(exc).__name__}: {exc}'
    for key in SECRETS:
        secret = getattr(settings, key, None)
        if secret:
            text = text.replace(secret, '[redacted]')
    return text[:400]


def draft_settings(settings: Settings, changes: dict) -> Settings:
    """Validate a snapshot without re-inheriting keys from the environment."""
    values = settings.model_dump()
    effective = dict(changes)
    for key, value in list(effective.items()):
        if value is None:
            effective[key] = Settings.model_fields[key].get_default(call_default_factory=True)
    if 'base_url' in effective or 'api_key' in effective:
        if 'base_url' in effective and effective['base_url'] != settings.base_url and 'api_key' not in effective:
            effective['api_key'] = ''
        for channel in ('chat', 'embed'):
            effective.setdefault(f'{channel}_base_url', effective.get('base_url', settings.base_url))
            effective.setdefault(f'{channel}_api_key', effective.get('api_key', settings.api_key))
    for channel in ('chat', 'embed'):
        url, key = f'{channel}_base_url', f'{channel}_api_key'
        if url in effective and effective[url] != getattr(settings, url) and key not in effective:
            effective[key] = ''
        if key in effective and effective[key] is None:
            effective[key] = ''
    # model_validate bypasses settings sources, while retaining field validators.
    # All fields are passed explicitly so no process/file source can fill holes.
    result = Settings(**{**values, **effective})
    result.channel_settings('chat')
    result.channel_settings('embed')
    return result


def probe_fingerprint(settings: Settings, channel: str) -> str:
    names = ([f'{channel}_base_url', f'{channel}_api_key', f'{channel}_allow_no_key',
              f'{channel}_model', 'use_mock_provider'] +
             (['embed_dim', 'embed_backend', 'local_embed_path', 'embed_send_dimensions']
              if channel == 'embed' else ['chat_extra_body', 'chat_model_fallbacks']))
    return hashlib.sha256(json.dumps({k: getattr(settings, k) for k in names},
                                    sort_keys=True, default=str).encode()).hexdigest()


def env_locked() -> frozenset[str]:
    """Writable fields the environment has already decided.

    An exported variable outranks the file (see
    :meth:`Settings.settings_customise_sources`), so a write to one of these
    persists a value the next boot ignores. The UI renders them read-only, but
    the UI is not the only caller of a localhost HTTP API, so the rule lives
    here and both the view and the write path read it.
    """
    locked = set(external_setting_keys(WRITABLE))
    if locked.intersection({'base_url', 'api_key'}):
        locked.update({'chat_base_url', 'chat_api_key', 'embed_base_url', 'embed_api_key'})
    return frozenset(locked)


def settings_view(settings: Settings, pending: dict[str, Any] | None = None) -> dict:
    """Every writable setting, its value, and where the value came from.

    ``source`` is the field people actually need. Editing a box and seeing the
    value not change is baffling until you learn that an exported environment
    variable outranks the file, so the UI is told which keys it cannot win.

    ``path`` is resolved from the environment, not from ``settings.data_dir``,
    and that is deliberate: :class:`~facetmark.config.ConfigFileSource` reads
    the same environment-resolved path, so this is the file the next boot will
    actually read. Pointing it at ``settings.data_dir`` would look tidier under
    ``serve --db /elsewhere/x.db`` and would write settings nothing ever reads.
    """
    locked = env_locked()
    file_values = read_config()
    # Restart-only fields are edited as their saved values. Keep the active
    # value alongside them so a reload never makes a successful save vanish.
    saved = Settings(**{
        **settings.model_dump(),
        **{k: v for k, v in file_values.items() if k in NEEDS_RESTART and k not in locked},
        **(pending or {}),
    })
    rows = []
    for name in WRITABLE:
        env = name in locked
        source = "env" if env else ("file" if name in file_values else "default")
        active = getattr(settings, name)
        value = getattr(saved, name) if name in NEEDS_RESTART and not env else active
        pending_restart = value != active
        if isinstance(value, tuple):
            value = list(value)
        rows.append({
            "key": name,
            "value": mask(value or '') if name in SECRETS else value,
            "secret": name in SECRETS,
            "set": bool(value),
            "source": source,
            # An environment variable cannot be overridden from a file, so the
            # input is rendered read-only rather than silently ineffective.
            "locked": env,
            "needs_restart": name in NEEDS_RESTART,
            "active_value": mask(active or '') if name in SECRETS else active,
            "pending_restart": pending_restart,
        })
    return {"path": str(config_path()), "settings": rows,
            "channels": {name: {"configured": saved.channel_ready(name),
                "base_url": getattr(saved, f'{name}_base_url') or saved.base_url,
                "key_set": bool(getattr(saved, f'{name}_api_key'))} for name in ('chat', 'embed')}}


async def probe(settings: Settings, channel: str | None = None) -> dict:
    """One chat call and one embed call. Report each independently.

    Independently because they fail independently and constantly: aggregated
    free endpoints will list six models from ``GET /v1/models`` and serve none
    of them to ``/embeddings``, and a combined pass/fail hides which half is
    broken.
    """
    try:
        provider = get_provider(settings)
    except Exception as exc:
        error = safe_error(exc, settings)
        return {
            "ok": False,
            "chat": {"ok": False, "ms": None, "model": settings.chat_model, "error": error},
            "embed": {"ok": False, "ms": None, "model": settings.embed_model, "error": error,
                      "dim": 0, "expected_dim": settings.embed_dim, "dim_matches": False},
        }
    chat_provider = provider.chat_provider if isinstance(provider, SplitProvider) else provider
    embed_provider = provider.embed_provider if isinstance(provider, SplitProvider) else provider
    mock_reason = (
        "Offline demo mode; no real model connection was tested."
        if settings.use_mock_provider else
        "API key is not configured; connection was not tested."
    )
    out: dict[str, Any] = {}
    try:
        if channel == 'embed':
            raise ProviderError('Not requested')
        if isinstance(chat_provider, MockProvider):
            raise ProviderError(mock_reason)
        t = time.monotonic()
        await provider.chat_json(
            "Reply with compact JSON.",
            'Return exactly {"ok": true} and nothing else.',
        )
        out["chat"] = {"ok": True, "ms": round((time.monotonic() - t) * 1000),
                       "model": getattr(provider, "chat_model_in_use", settings.chat_model),
                       "error": None}
    except Exception as exc:  # noqa: BLE001 - the message is the product here
        out["chat"] = {"ok": False, "ms": None,
                       "model": "mock" if isinstance(chat_provider, MockProvider) else settings.chat_model,
                       "error": safe_error(exc, settings)}
    try:
        if channel == 'chat':
            raise ProviderError('Not requested')
        if isinstance(embed_provider, MockProvider):
            raise ProviderError(mock_reason)
        t = time.monotonic()
        vectors = (await embed_provider.probe_embedding()
                   if isinstance(embed_provider, OpenAICompatibleProvider)
                   else await provider.embed(["facetmark connection test"]))
        dim = len(vectors[0]) if vectors and vectors[0] else 0
        out["embed"] = {
            "ok": bool(dim),
            "ms": round((time.monotonic() - t) * 1000),
            "model": settings.embed_model,
            "dim": dim,
            # The mismatch that corrupts an index silently if it is not caught
            # here: the meta table pins the dimension on first build.
            "dim_matches": dim == settings.embed_dim,
            "expected_dim": settings.embed_dim,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        out["embed"] = {"ok": False, "ms": None,
                        "model": "mock" if isinstance(embed_provider, MockProvider) else settings.embed_model,
                        "dim": 0,
                        "dim_matches": False, "expected_dim": settings.embed_dim,
                        "error": safe_error(exc, settings)}
    with contextlib.suppress(Exception):
        await provider.aclose()
    out["ok"] = out["chat"]["ok"] and out["embed"]["ok"] and out["embed"]["dim_matches"]
    if channel:
        out['ok'] = out[channel]['ok'] and (channel != 'embed' or out[channel]['dim_matches'])
    return out


def admin_gate(request: Request) -> None:
    """403 unless the caller is on this machine and the group is enabled."""
    state = request.app.state.fm
    if not getattr(state.settings, "admin_api", True):
        raise HTTPException(403, "admin API disabled (FACETMARK_ADMIN_API=false)")
    peer = (request.client.host if request.client else "") or ""
    if peer not in _LOOPBACK_PEERS:
        raise HTTPException(403, "admin API is loopback-only; use an SSH tunnel")


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------


def register(app: FastAPI, auth: list) -> None:
    """Mount ``/admin/*``. ``auth`` is the same token dependency every route uses."""
    deps = [*auth, Depends(admin_gate)]

    def _state(request: Request):
        return request.app.state.fm

    @app.get("/admin/runtime", dependencies=deps)
    async def runtime_identity(request: Request) -> dict:
        from . import __version__
        from .desktop import database_identity

        state = _state(request)
        return {"service": "facetmark", "version": __version__,
                "database_identity": database_identity(state.settings.db_path)}

    @app.post("/admin/import", dependencies=deps)
    async def admin_import(request: Request) -> dict:
        """Import a bookmark export sent as the raw request body.

        Raw bytes rather than ``multipart/form-data`` because FastAPI's file
        handling needs ``python-multipart``, and a new runtime dependency for
        one endpoint is a bad trade when ``fetch(url, {body: file})`` sends the
        bytes just as happily. The format is sniffed from the content, so
        Netscape HTML and Chrome JSON both just work.
        """
        raw = await request.body()
        if not raw:
            raise HTTPException(400, "empty body")
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"file larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
        # The same ladder `facetmark import <file>` uses. Decoding the upload
        # as UTF-8 with `errors="replace"` instead returns 200 and stores
        # `Caf\ufffd` -- an import that reports success and has already damaged
        # the title it indexed, summarised and embedded.
        content = decode_bookmark_bytes(raw)
        state = _state(request)
        async with state.lock:
            stats = service.import_content(state.conn, content, settings=state.settings)
        stats["filename"] = request.headers.get("x-filename", "")
        stats["bytes"] = len(raw)
        return stats

    @app.post("/admin/index", dependencies=deps)
    async def admin_index(body: IndexRequest, request: Request) -> dict:
        state = _state(request)
        if state.pending_settings:
            raise HTTPException(409, 'Apply the saved embedding settings before indexing')
        if not state.settings.use_mock_provider:
            if not all(state.settings.channel_ready(c) for c in ('chat', 'embed')):
                raise HTTPException(409, 'Configure chat and embedding models before indexing')
            if not body.confirmed:
                raise HTTPException(400, 'Confirm sending titles, URLs and extracted text to the configured models')
            if not all(state.probe_results.get(c, {}).get('fingerprint') == probe_fingerprint(state.settings, c)
                       for c in ('chat', 'embed')):
                raise HTTPException(409, 'Test both saved model connections before indexing')
        from .workbench import validate_space
        validate_space(state.conn, state.settings)
        try:
            job = state.jobs.start(
                state.settings, fetch=body.fetch, limit=body.limit, force=body.force
            )
        except RuntimeError:
            # 409 rather than 400: the request is well-formed, the resource is
            # busy, and the body tells the UI what it is busy with.
            raise HTTPException(409, "an index job is already running") from None
        return job.as_dict()

    @app.get("/admin/job", dependencies=deps)
    async def admin_job(request: Request) -> dict:
        runner = _state(request).jobs
        return runner.job.as_dict() if runner.job else (runner.previous or {"state": "idle", "planned": list(INDEX_STAGES)})

    @app.post("/admin/job/cancel", dependencies=deps)
    async def admin_job_cancel(request: Request) -> dict:
        runner = _state(request).jobs
        cancelled = runner.cancel()
        job = runner.job
        return {"cancel_requested": cancelled, "job": job.as_dict() if job else None}

    @app.get("/admin/settings", dependencies=deps)
    async def admin_settings(request: Request) -> dict:
        state = _state(request)
        return settings_view(state.settings, state.pending_settings)

    @app.put("/admin/settings", dependencies=deps)
    async def admin_settings_write(body: SettingsPatch, request: Request) -> dict:
        unknown = sorted(set(body.values) - set(WRITABLE))
        if unknown:
            raise HTTPException(400, f"not writable from the UI: {', '.join(unknown)}")
        # 409 rather than 400: the request is well-formed and the field is
        # writable in general, but this process was started with the variable
        # exported. Accepting it would wipe the live value while the view still
        # -- correctly -- reports the source as `env`.
        locked = sorted(set(body.values) & env_locked())
        if locked:
            raise HTTPException(
                409, f"set by the environment, unset the variable to edit here: {', '.join(locked)}"
            )
        changes = dict(body.values)
        try:
            # An empty string for the key means "clear it", not "set it to empty".
            if changes.get("api_key") == "":
                changes["api_key"] = None
            # One text box holds a list, so a string arrives. Normalize before
            # validating and writing, and reject every other shape explicitly.
            for key in TUPLE_FIELDS & set(changes):
                value = changes[key]
                if value is None:
                    continue
                if isinstance(value, str):
                    changes[key] = list(split_list(value))
                elif isinstance(value, (list, tuple)) and all(
                    isinstance(item, str) for item in value
                ):
                    parts: list[str] = []
                    for item in value:
                        parts.extend(split_list(item))
                    changes[key] = list(dict.fromkeys(parts))
                else:
                    raise ValueError(f"{key} must be a string or a list of strings")

            state = _state(request)
            current = draft_settings(state.settings, state.pending_settings)
            validated = draft_settings(current, changes)
            # Include implicit key clearing and legacy-to-channel changes in
            # both persistence and the active/pending snapshot.
            for key in WRITABLE:
                if getattr(validated, key) != getattr(current, key):
                    changes.setdefault(key, getattr(validated, key))
        except Exception as exc:  # noqa: BLE001
            # Validation exceptions can echo entire input dictionaries, keys included.
            raise HTTPException(400, f"invalid settings ({type(exc).__name__}); check field types and endpoint URLs") from None

        # Persist and apply the validated representation, not raw JSON strings.
        persisted = {
            key: None if value is None else getattr(validated, key)
            for key, value in changes.items()
        }
        applied = [k for k in changes if k not in NEEDS_RESTART]
        async with state.lock:
            # A job already selected its targets. Applying privacy rules while
            # it runs would claim to protect requests already queued by it.
            if state.jobs.running:
                raise HTTPException(409, "stop the index job before changing settings or privacy rules")
            update_config(persisted)
            state.settings = state.settings.model_copy(update={
                key: getattr(validated, key) for key in applied
            })
            for key in set(changes) & NEEDS_RESTART:
                if getattr(validated, key) == getattr(state.settings, key):
                    state.pending_settings.pop(key, None)
                else:
                    state.pending_settings[key] = getattr(validated, key)
            if "privacy_excluded_domains" in changes:
                refresh_privacy(state.conn, state.settings)
            old_provider, state._provider = state._provider, None
            if old_provider is not None:
                with contextlib.suppress(Exception):
                    await old_provider.aclose()
        view = settings_view(state.settings, state.pending_settings)
        return {
            **view,
            "applied": applied,
            "restart_required": sorted(row["key"] for row in view["settings"] if row["pending_restart"]),
        }

    @app.post("/admin/settings/test", dependencies=deps)
    async def admin_settings_test(body: ProbeRequest, request: Request) -> dict:
        state = _state(request)
        if body.channel not in (None, 'chat', 'embed'):
            raise HTTPException(400, 'channel must be chat or embed')
        try:
            base = draft_settings(state.settings, state.pending_settings)
            settings = draft_settings(base, body.model_dump(exclude_none=True, exclude={'channel'}))
        except ValueError:
            raise HTTPException(400, 'Invalid model settings; check endpoint URLs and field types') from None
        result = await probe(settings, body.channel) if body.channel else await probe(settings)
        for channel in ('chat', 'embed') if body.channel is None else (body.channel,):
            if result.get(channel, {}).get('ok') and (channel != 'embed' or result[channel]['dim_matches']):
                state.probe_results[channel] = {'fingerprint': probe_fingerprint(settings, channel),
                                                'result': result[channel]}
            else:
                state.probe_results.pop(channel, None)
        return result
