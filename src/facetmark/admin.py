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
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, get_args, get_origin

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from . import service
from .config import Settings, split_list
from .configfile import config_path, external_setting_keys, read_config, update_config
from .db import open_db
from .importers import decode_bookmark_bytes
from .providers import get_provider

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
    "chat_model",
    "chat_model_fallbacks",
    "embed_model",
    "embed_dim",
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
NEEDS_RESTART = frozenset({"embed_dim", "embed_backend", "local_embed_path"})

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

    def __init__(self) -> None:
        self.job: IndexJob | None = None
        self._task: asyncio.Task | None = None

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
        self._task = asyncio.create_task(self._run(job, settings))
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
        return True

    async def _run(self, job: IndexJob, settings: Settings) -> None:
        # Its own connection. The service connection is guarded by a single
        # asyncio lock that every search takes, and an index run holding that
        # for minutes would make the UI look hung. WAL means a second writer
        # blocks only on the write itself, which is short.
        conn = open_db(settings.db_path, same_thread=False)
        last = time.monotonic()

        def progress(name: str, value: Any) -> None:
            nonlocal last
            now = time.monotonic()
            job.stages.append(Stage(name=name, value=value, seconds=now - last))
            job.log.append(_summarise(name, value))
            last = now
            if job.cancel_requested:
                raise _Cancelled

        try:
            await service.index_all(
                conn,
                provider=get_provider(settings),
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
            job.state = "cancelled"
            job.log.append("cancelled by shutdown")
            raise
        except Exception as exc:  # noqa: BLE001 - surfaced to the operator
            job.state = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            job.log.append(job.error)
        finally:
            job.finished_at = time.monotonic()
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
    embed_model: str | None = None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def mask(value: str) -> str:
    """Enough of a secret to recognise, never enough to use."""
    if not value:
        return ""
    return value if len(value) <= 8 else f"{value[:3]}...{value[-4:]}"


def env_locked() -> frozenset[str]:
    """Writable fields the environment has already decided.

    An exported variable outranks the file (see
    :meth:`Settings.settings_customise_sources`), so a write to one of these
    persists a value the next boot ignores. The UI renders them read-only, but
    the UI is not the only caller of a localhost HTTP API, so the rule lives
    here and both the view and the write path read it.
    """
    return external_setting_keys(WRITABLE)


def settings_view(settings: Settings) -> dict:
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
    file_keys = set(read_config())
    rows = []
    for name in WRITABLE:
        env = name in locked
        source = "env" if env else ("file" if name in file_keys else "default")
        value = getattr(settings, name)
        if isinstance(value, tuple):
            value = list(value)
        rows.append({
            "key": name,
            "value": mask(value) if name == "api_key" else value,
            "secret": name == "api_key",
            "set": bool(value),
            "source": source,
            # An environment variable cannot be overridden from a file, so the
            # input is rendered read-only rather than silently ineffective.
            "locked": env,
            "needs_restart": name in NEEDS_RESTART,
        })
    return {"path": str(config_path()), "settings": rows}


async def probe(settings: Settings) -> dict:
    """One chat call and one embed call. Report each independently.

    Independently because they fail independently and constantly: aggregated
    free endpoints will list six models from ``GET /v1/models`` and serve none
    of them to ``/embeddings``, and a combined pass/fail hides which half is
    broken.
    """
    provider = get_provider(settings)
    out: dict[str, Any] = {}
    try:
        t = time.monotonic()
        await provider.chat_json(
            "Reply with compact JSON.",
            'Return exactly {"ok": true} and nothing else.',
        )
        out["chat"] = {"ok": True, "ms": round((time.monotonic() - t) * 1000),
                       "model": settings.chat_model, "error": None}
    except Exception as exc:  # noqa: BLE001 - the message is the product here
        out["chat"] = {"ok": False, "ms": None, "model": settings.chat_model,
                       "error": f"{type(exc).__name__}: {exc}"[:400]}
    try:
        t = time.monotonic()
        vectors = await provider.embed(["facetmark connection test"])
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
        out["embed"] = {"ok": False, "ms": None, "model": settings.embed_model, "dim": 0,
                        "dim_matches": False, "expected_dim": settings.embed_dim,
                        "error": f"{type(exc).__name__}: {exc}"[:400]}
    with contextlib.suppress(Exception):
        await provider.aclose()
    out["ok"] = out["chat"]["ok"] and out["embed"]["ok"] and out["embed"]["dim_matches"]
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
        job = _state(request).jobs.job
        return job.as_dict() if job else {"state": "idle", "planned": list(INDEX_STAGES)}

    @app.post("/admin/job/cancel", dependencies=deps)
    async def admin_job_cancel(request: Request) -> dict:
        runner = _state(request).jobs
        cancelled = runner.cancel()
        job = runner.job
        return {"cancel_requested": cancelled, "job": job.as_dict() if job else None}

    @app.get("/admin/settings", dependencies=deps)
    async def admin_settings(request: Request) -> dict:
        return settings_view(_state(request).settings)

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
            current = {k: getattr(state.settings, k) for k in WRITABLE}
            effective = dict(changes)
            for key, value in changes.items():
                if value is None:
                    effective[key] = Settings.model_fields[key].get_default(
                        call_default_factory=True
                    )
            validated = Settings(**{**current, **effective})
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"invalid settings: {exc}"[:400]) from None

        # Persist and apply the validated representation, not raw JSON strings.
        persisted = {
            key: None if value is None else getattr(validated, key)
            for key, value in changes.items()
        }
        update_config(persisted)
        # Refresh the live objects so anything that can take effect now, does.
        applied = [k for k in changes if k not in NEEDS_RESTART]
        for key in applied:
            with contextlib.suppress(Exception):
                setattr(state.settings, key, getattr(validated, key))
        state._provider = None
        return {
            **settings_view(state.settings),
            "applied": applied,
            "restart_required": sorted(set(changes) & NEEDS_RESTART),
        }

    @app.post("/admin/settings/test", dependencies=deps)
    async def admin_settings_test(body: ProbeRequest, request: Request) -> dict:
        state = _state(request)
        base = state.settings.model_dump()
        for key, value in body.model_dump(exclude_none=True).items():
            if value != "":
                base[key] = value
        return await probe(Settings(**base))
