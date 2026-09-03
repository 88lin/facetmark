"""Local HTTP service. The browser extension's only counterparty.

Three things about this file are load-bearing.

**Bind address.** 127.0.0.1 by default, and refusing to serve on 0.0.0.0 without
an explicit opt-in. The index contains the user's entire browsing interest
graph; it is not a thing to expose on a LAN by accident.

**Token, not origin.** Every route except ``/`` and ``/health`` requires a
bearer token minted on first run into a file in the data directory. Loopback is
not an authorisation boundary -- any local process, and via Chrome's Local
Network Access story any web page the user visits, can send requests to
127.0.0.1. Origin checks do not help because a non-browser client sets whatever
origin it likes.

**Channel B.** ``/queue/next`` and ``/queue/complete`` are the extension's half
of the two-channel fetcher. Channel A (httpx, this process) handles the ~98% of
pages that answer a plain GET. Everything it cannot honestly get past -- bot
walls, login-gated pages, client-rendered shells -- is queued here and read out
of a real tab with the user's own session. The server never opens tabs and the
extension never fetches anything the server did not ask for.
"""

from __future__ import annotations

import asyncio
import contextlib
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, admin, service
from . import health as healthmod
from .bridges import karakeep as kkbridge
from .config import Settings, get_settings
from .db import open_db
from .fetch import store as fetchstore
from .providers import get_provider
from .search.pipeline import ALL_CONFIGS, default_config
from .web import INDEX_HTML, STATIC_DIR

#: Chrome extension pages and service workers send this scheme.
_EXT_ORIGIN_PREFIXES = ("chrome-extension://", "moz-extension://", "safari-web-extension://")

PUBLIC_PATHS = frozenset({
    "/", "/health", "/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc",
    # The web UI. `/app` is a static document and `/app/boot` hands the page
    # its token, gated on loopback rather than on the token it does not have
    # yet. See `_pairing_gate`.
    "/app", "/app/boot",
})

#: Host header values that mean "this browser is talking to its own machine".
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

#: Peer addresses that mean the same thing at the TCP layer.
_LOOPBACK_PEERS = frozenset({"127.0.0.1", "::1"})


# ---------------------------------------------------------------------------
# app state
# ---------------------------------------------------------------------------


class AppState:
    """One SQLite connection, one lock, one provider.

    SQLite connections are not safe to share across threads without care, and
    the write paths here (queue leases, interaction logging) are short. A single
    connection guarded by an asyncio lock is simpler and, at one user and a few
    thousand rows, indistinguishable in speed from a pool.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.ensure_dirs()
        self.conn: sqlite3.Connection = open_db(self.settings.db_path, same_thread=False)
        self.lock = asyncio.Lock()
        #: At most one index run, on its own connection. See `facetmark.admin`.
        self.jobs = admin.JobRunner()
        self.token = service.pairing_token(self.settings)
        self.started_at = int(time.time())
        self._provider = None

    @property
    def provider(self):
        if self._provider is None:
            self._provider = get_provider(self.settings)
        return self._provider

    def close(self) -> None:
        with contextlib.suppress(Exception):  # pragma: no cover
            self.conn.close()


def get_state(request: Request) -> AppState:
    return request.app.state.fm


def require_token(request: Request) -> None:
    state: AppState = request.app.state.fm
    if not state.token:  # pragma: no cover - token is always minted
        return
    header = request.headers.get("authorization", "")
    supplied = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if not supplied:
        supplied = request.headers.get("x-facetmark-token", "").strip()
    if supplied != state.token:
        raise HTTPException(status_code=401, detail="bad or missing pairing token")


def _pairing_gate(request: Request) -> str:
    """``""`` when this caller may be handed the pairing token, else a reason.

    Two conditions, and the second one is the interesting one.

    The TCP peer must be loopback. That is necessary and nowhere near
    sufficient: under DNS rebinding the peer *is* loopback, because the request
    comes from the victim's own browser. An attacker publishes
    ``evil.example`` with a short TTL, gets the user to load a page, re-answers
    the next lookup with ``127.0.0.1``, and now their JavaScript is issuing
    same-origin requests to this server from a real local socket.

    What the attacker cannot forge is the ``Host`` header: the browser sends
    the name the user's page was loaded from, so a rebound request arrives
    carrying ``evil.example``. Requiring that header to be a loopback literal
    is therefore the check that actually holds, and refusing to hand out the
    token leaves the attacker facing the same 401 as any other unauthenticated
    caller.

    Deliberately scoped to ``/app/boot`` rather than applied globally. Every
    other route already requires the token, so a global ``Host`` allowlist
    would buy no security while breaking anyone who binds a LAN address on
    purpose -- which the CLI already warns about and permits.
    """
    peer = (request.client.host if request.client else "") or ""
    if peer not in _LOOPBACK_PEERS:
        return "peer_not_loopback"
    # `url.hostname` is the Host header with the port stripped and IPv6
    # brackets removed, falling back to the ASGI `server` tuple when the header
    # is absent -- so a missing Host fails closed rather than open.
    if (request.url.hostname or "").lower() not in _LOOPBACK_HOSTS:
        return "host_not_loopback"
    return ""


# ---------------------------------------------------------------------------
# request models
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """``limit``/``offset``/``depth`` carry no static upper bound on purpose.

    They are clamped in one place -- ``resolve_page``, against
    ``max_page_size`` and ``max_candidate_depth`` -- and the response reports
    the values actually served. A second ceiling here would be a limit hidden
    in a file the operator does not edit: raising ``max_page_size`` in ``.env``
    would appear to do nothing. Oversized values cost nothing, since clamping
    happens before any query runs.
    """

    q: str
    limit: int = Field(default=20, ge=1)
    offset: int = Field(default=0, ge=0)
    #: Pin the per-facet candidate depth. Echo back ``depth`` from the previous
    #: page to guarantee that this page continues it; omit it and the depth is
    #: derived from the window.
    depth: int | None = Field(default=None, ge=1)
    config: str = "full"
    assist: bool = False
    expand: int = Field(default=8, ge=0, le=50)


class CompleteRequest(BaseModel):
    bookmark_id: int
    body: str = ""
    title: str = ""
    final_url: str = ""
    error: str = ""


class SaveRequest(BaseModel):
    url: str
    title: str = ""
    folder: str = ""
    #: Optional user tags. Stored on the bookmark (JSON array), indexed as
    #: free text, and queryable exactly via ``tag:`` in the search box.
    tags: list[str] = Field(default_factory=list)
    date_added: int | None = None


class OpenRequest(BaseModel):
    bookmark_id: int
    query: str = ""


class SuggestRequest(BaseModel):
    text: str
    limit: int = Field(default=8, ge=1, le=50)


class SuggestQueryRequest(BaseModel):
    """The token being typed, not the whole query box.

    The frontend keeps the surrounding words to itself and sends only the token
    the cursor is in; the reply's ``insert`` replaces that token.
    """

    text: str = ""
    limit: int = Field(default=8, ge=1, le=25)


class SynthesizeRequest(BaseModel):
    q: str
    limit: int = Field(default=8, ge=1, le=20)


class KarakeepAddRequest(BaseModel):
    """``addDocuments``. ``embed`` is escapable so a bulk backfill can defer it."""

    documents: list[dict]
    embed: bool = True


class KarakeepDeleteRequest(BaseModel):
    ids: list[str]


class KarakeepSearchRequest(BaseModel):
    """``SearchOptions`` verbatim, plus the ablation rung for experiments."""

    query: str = ""
    filter: list[dict] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    sort: list[dict] = Field(default_factory=list)
    config: str = "full"


class HealthCheckRequest(BaseModel):
    ids: list[int] | None = None
    limit: int = Field(default=50, ge=1, le=1000)


# ---------------------------------------------------------------------------
# app factory
# ---------------------------------------------------------------------------


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.fm = AppState(settings)
        try:
            yield
        finally:
            app.state.fm.close()

    app = FastAPI(
        title="facetmark",
        version=__version__,
        summary="Local bookmark retrieval service.",
        lifespan=lifespan,
    )

    # The extension's service worker is exempt from most CORS restrictions, but
    # the options page is a normal document and is not. Allowing extension
    # origins only keeps ordinary web pages out even before the token check.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^(chrome|moz|safari-web)-extension://.*$",
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["authorization", "content-type", "x-facetmark-token"],
    )

    _register(app)
    return app


def _register(app: FastAPI) -> None:  # noqa: C901 - a route table, not a branchy function
    auth = [Depends(require_token)]

    @app.get("/")
    async def root(state: AppState = Depends(get_state)) -> dict:
        """Unauthenticated liveness probe. Deliberately reveals nothing."""
        return {"service": "facetmark", "version": __version__, "ok": True}

    @app.get("/health")
    async def service_health(state: AppState = Depends(get_state)) -> dict:
        n = state.conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0]
        return {
            "ok": True,
            "version": __version__,
            "uptime_s": int(time.time()) - state.started_at,
            "bookmarks": int(n),
            "provider": "mock" if state.settings.use_mock_provider else "openai-compatible",
        }

    @app.get("/stats", dependencies=auth)
    async def stats(state: AppState = Depends(get_state)) -> dict:
        return service.library_stats(state.conn)

    # ---------------- write routes for the web UI ----------------
    # Import, index and settings. Token-gated like everything else, plus a hard
    # loopback check and an off switch. See `facetmark.admin`.
    admin.register(app, auth)

    # ---------------- web UI ----------------
    # Three unauthenticated routes. Two serve bytes off disk; the third is the
    # only place in the service that will ever disclose the pairing token.

    @app.get("/app", include_in_schema=False)
    async def web_app() -> FileResponse:
        """The UI shell, served verbatim.

        Nothing is substituted into this document. Templating the token in
        would mean escaping a secret into an HTML context correctly forever --
        one ``</script>`` in the wrong place and the page is an injection
        primitive. Fetching it from ``/app/boot`` instead keeps the secret in a
        JSON body, where the escaping rules are the parser's problem, and it
        keeps this file cacheable.
        """
        if not INDEX_HTML.is_file():  # pragma: no cover - a broken install
            raise HTTPException(503, "web assets missing from this installation")
        return FileResponse(INDEX_HTML, media_type="text/html; charset=utf-8")

    @app.get("/app/boot", include_in_schema=False)
    async def web_boot(request: Request, state: AppState = Depends(get_state)) -> JSONResponse:
        """Hand a same-machine browser its pairing token, or explain why not."""
        reason = _pairing_gate(request)
        body = {
            "version": __version__,
            "paired": not reason,
            "token": "" if reason else state.token,
            "reason": reason,
        }
        # Caches and history restores are not places for a bearer token.
        return JSONResponse(body, headers={"Cache-Control": "no-store"})

    # `check_dir=False`: a broken install should 404 one asset, not refuse to
    # start the service the extension depends on.
    app.mount(
        "/app/static",
        StaticFiles(directory=STATIC_DIR, check_dir=False),
        name="facetmark-web",
    )

    # ---------------- search ----------------

    @app.get("/quick", dependencies=auth)
    async def quick(
        q: str,
        limit: int = Query(default=20, ge=1),
        offset: int = Query(default=0, ge=0),
        depth: int | None = Query(default=None, ge=1),
        state: AppState = Depends(get_state),
    ) -> dict:
        """First paint. Lexical only, no model call, no await on anything."""
        return service.quick_search(
            state.conn, q, limit=limit, offset=offset, depth=depth,
            settings=state.settings,
        ).as_dict()

    @app.post("/search", dependencies=auth)
    async def full_search(req: SearchRequest, state: AppState = Depends(get_state)) -> dict:
        # "full" is the name of *whatever this deployment ships*, and that
        # depends on whether it has real embeddings -- so it resolves through
        # default_config rather than through the table.
        cfg = (
            default_config(state.settings, state.provider)
            if req.config in ("", "full")
            else ALL_CONFIGS.get(req.config)
        )
        if cfg is None:
            raise HTTPException(400, f"unknown config {req.config!r}")
        async with state.lock:
            resp = await service.search(
                state.conn, req.q, limit=req.limit, offset=req.offset,
                depth=req.depth, config=cfg,
                provider=state.provider, settings=state.settings,
                assist=req.assist, expand_limit=req.expand,
            )
        return resp.as_dict()

    @app.post("/suggest", dependencies=auth)
    async def suggest(req: SuggestRequest, state: AppState = Depends(get_state)) -> dict:
        return service.suggest_from_context(state.conn, req.text, limit=req.limit)

    @app.post("/synthesize", dependencies=auth)
    async def synthesize(req: SynthesizeRequest, state: AppState = Depends(get_state)) -> dict:
        async with state.lock:
            out = await service.synthesize(
                state.conn, req.q, limit=req.limit,
                provider=state.provider, settings=state.settings,
            )
        return out.as_dict()

    # ---------------- records ----------------

    @app.get("/bookmark/{bookmark_id}", dependencies=auth)
    async def get_bookmark(
        bookmark_id: int, body: bool = False, state: AppState = Depends(get_state)
    ) -> dict:
        rec = service.bookmark_record(
            state.conn, bookmark_id, settings=state.settings, include_body=body
        )
        if rec is None:
            raise HTTPException(404, "no such bookmark")
        return rec

    @app.get("/bookmark/{bookmark_id}/related", dependencies=auth)
    async def get_related(
        bookmark_id: int,
        kind: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        state: AppState = Depends(get_state),
    ) -> list[dict]:
        try:
            return service.related_records(state.conn, bookmark_id, kind=kind, limit=limit)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/sessions", dependencies=auth)
    async def list_sessions(
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        min_size: int = Query(default=2, ge=1),
        state: AppState = Depends(get_state),
    ) -> list[dict]:
        return service.session_list(state.conn, limit=limit, offset=offset, min_size=min_size)

    @app.get("/timeline", dependencies=auth)
    async def get_timeline(
        months: int = Query(default=12, ge=1, le=60),
        state: AppState = Depends(get_state),
    ) -> dict:
        """Save-activity buckets: the last week by day, older months by month.

        Ported from hister's history timeline. Read-only, one scan of the
        ``date_added`` column -- cheap enough that the UI can ask on every
        visit to the library view.
        """
        return service.timeline(state.conn, months=months)

    @app.post("/suggest/query", dependencies=auth)
    async def suggest_query(
        req: SuggestQueryRequest, state: AppState = Depends(get_state)
    ) -> dict:
        """Complete the query language: field names, values, sort directives.

        Distinct from ``/suggest``, which completes *documents* from text the
        reader is typing. This one completes *syntax*: ``dom`` offers
        ``domain:``, ``domain:git`` offers the domains in this library that
        start with ``git``. The values come from this database -- the point of
        a value suggestion is that it is a value that exists here.
        """
        return service.suggest_query_syntax(state.conn, req.text, limit=req.limit)

    @app.get("/session/{session_id}", dependencies=auth)
    async def get_session(session_id: int, state: AppState = Depends(get_state)) -> dict:
        rec = service.session_record(state.conn, session_id)
        if rec is None:
            raise HTTPException(404, "no such session")
        return rec

    # ---------------- writes ----------------

    @app.post("/bookmark", dependencies=auth)
    async def save(req: SaveRequest, state: AppState = Depends(get_state)) -> dict:
        async with state.lock:
            return service.save_bookmark(
                state.conn, req.url, title=req.title, folder=req.folder,
                tags=req.tags, date_added=req.date_added, settings=state.settings,
            )

    @app.post("/open", dependencies=auth)
    async def opened(req: OpenRequest, state: AppState = Depends(get_state)) -> dict:
        async with state.lock:
            service.record_open(state.conn, req.bookmark_id, query=req.query)
        return {"ok": True}

    # ---------------- channel B ----------------

    @app.get("/queue/next", dependencies=auth)
    async def queue_next(
        n: int = Query(default=3, ge=1, le=10), state: AppState = Depends(get_state)
    ) -> dict:
        """Lease up to ``n`` URLs for the extension to open in a background tab.

        Capped at 10 on purpose. The extension opens real tabs; handing it a
        hundred at once would make the browser unusable, and the user has to be
        able to watch this happen and stop it.
        """
        async with state.lock:
            items = fetchstore.lease_browser_batch(state.conn, n)
            state.conn.commit()
        return {"items": items, "queue": fetchstore.queue_stats(state.conn),
                "waiting": fetchstore.queue_waiting(state.conn)}

    @app.post("/queue/complete", dependencies=auth)
    async def queue_complete(
        req: CompleteRequest, state: AppState = Depends(get_state)
    ) -> dict:
        async with state.lock:
            out = fetchstore.complete_browser_item(
                state.conn, req.bookmark_id, body=req.body, title=req.title,
                final_url=req.final_url, error=req.error,
            )
            state.conn.commit()
        return {"bookmark_id": out.bookmark_id, "stored": out.stored, "changed": out.changed,
                "queue": fetchstore.queue_stats(state.conn)}

    @app.get("/queue/stats", dependencies=auth)
    async def queue_status(state: AppState = Depends(get_state)) -> dict:
        return {**fetchstore.queue_stats(state.conn),
                "waiting": fetchstore.queue_waiting(state.conn)}

    # ---------------- link health ----------------

    @app.get("/link-health/summary", dependencies=auth)
    async def health_summary(state: AppState = Depends(get_state)) -> dict:
        return healthmod.summary(state.conn)

    @app.get("/link-health/{bookmark_id}", dependencies=auth)
    async def health_state(bookmark_id: int, state: AppState = Depends(get_state)) -> dict:
        return healthmod.state_of(
            state.conn, bookmark_id, settings=state.settings
        ).as_dict()

    @app.post("/link-health/check", dependencies=auth)
    async def health_check(
        req: HealthCheckRequest, state: AppState = Depends(get_state)
    ) -> dict:
        async with state.lock:
            rep = await healthmod.check_bookmarks(
                state.conn, ids=req.ids, limit=req.limit, settings=state.settings
            )
            state.conn.commit()
        return rep.as_dict()

    @app.get("/graveyard", dependencies=auth)
    async def graveyard(
        limit: int = Query(default=100, ge=1, le=1000), state: AppState = Depends(get_state)
    ) -> list[dict]:
        """Confirmed-dead links. Still in the library, still searchable.

        This endpoint exists so the UI can *offer* a cleanup view, not so
        anything can be removed automatically. Nothing here is deleted by
        facetmark, ever.
        """
        rows = state.conn.execute(
            "SELECT DISTINCT bookmark_id FROM health WHERE verdict IN ('gone','soft_gone') "
            "ORDER BY bookmark_id LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            st = healthmod.state_of(state.conn, r["bookmark_id"], settings=state.settings)
            if not st.show_in_graveyard:
                continue
            rec = service.bookmark_record(
                state.conn, r["bookmark_id"], settings=state.settings
            )
            if rec:
                out.append(rec)
        return out

    # -- karakeep search provider ------------------------------------------
    # Four routes mirroring packages/shared/search.ts. They live behind the same
    # pairing token as everything else, and they are the only endpoints that
    # write bookmarks from an external system.

    @app.post("/karakeep/documents", dependencies=auth)
    async def karakeep_add(
        req: KarakeepAddRequest, state: AppState = Depends(get_state)
    ) -> dict:
        async with state.lock:
            return await kkbridge.add_documents(
                state.conn, req.documents, provider=state.provider,
                settings=state.settings, embed=req.embed,
            )

    @app.post("/karakeep/documents/delete", dependencies=auth)
    async def karakeep_delete(
        req: KarakeepDeleteRequest, state: AppState = Depends(get_state)
    ) -> dict:
        async with state.lock:
            return kkbridge.delete_documents(state.conn, req.ids)

    @app.post("/karakeep/search", dependencies=auth)
    async def karakeep_search(
        req: KarakeepSearchRequest, state: AppState = Depends(get_state)
    ) -> dict:
        if req.config not in ALL_CONFIGS:
            raise HTTPException(status_code=400, detail=f"unknown config {req.config!r}")
        return await kkbridge.search_documents(
            state.conn, req.model_dump(), provider=state.provider,
            settings=state.settings, config=req.config,
        )

    @app.post("/karakeep/clear", dependencies=auth)
    async def karakeep_clear(state: AppState = Depends(get_state)) -> dict:
        async with state.lock:
            return kkbridge.clear_index(state.conn)

    @app.get("/karakeep/stats", dependencies=auth)
    async def karakeep_stats(state: AppState = Depends(get_state)) -> dict:
        return kkbridge.mapping_stats(state.conn)

    @app.exception_handler(sqlite3.Error)
    async def _sqlite_error(request: Request, exc: sqlite3.Error) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": f"database error: {exc}"})


def serve(settings: Settings | None = None, **kw: Any) -> None:  # pragma: no cover - runtime
    import uvicorn

    st = settings or get_settings()
    st.ensure_dirs()
    token = service.pairing_token(st)
    print(f"facetmark {__version__}  http://{st.host}:{st.port}")
    # The line a first-time user needs. Everything else in this banner is for
    # somebody wiring up the extension, which is not where anyone starts.
    print(f"open the search page:     http://{st.host}:{st.port}/app")
    print(f"pairing token written to: {st.token_path}")
    print(f"token: {token}")
    uvicorn.run(create_app(st), host=st.host, port=st.port, log_level=kw.get("log_level", "info"))


__all__ = ["AppState", "create_app", "require_token", "serve"]
