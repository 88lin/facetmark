"""MCP server: nine tools and two resources over the local index.

Why an agent-facing surface at all. A bookmark library is the one corpus an
assistant cannot get from the web: it is the set of pages *this person* decided
were worth keeping, in the order and grouping they kept them. Exposing it over
MCP means "what did I save about X" becomes answerable inside whatever the user
is already working in, without a round trip through a web UI.

Two rules the tool shapes enforce.

*Bounded payloads.* ``summary`` is 200 characters and ``snippet`` is 300,
clipped in :mod:`facetmark.service`. Twenty results must stay small enough to
paste into a context window without evicting the user's actual work.

*No silent deletion.* ``check_link_health`` reports; it never removes. Even a
twice-confirmed ``gone`` link stays in the library and stays searchable, with an
archive URL attached when one exists.

Every tool is ``async``. FastMCP may dispatch synchronous tools on a worker
thread, and this module holds a single SQLite connection, which is bound to the
thread that created it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Annotated, Any

from pydantic import Field

from . import __version__, service
from . import health as healthmod
from .config import Settings, get_settings
from .db import open_db
from .edges import WEIGHTS as EDGE_WEIGHTS
from .providers import get_provider
from .search.pipeline import default_config

try:  # pragma: no cover - import shape differs across fastmcp majors
    from fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "fastmcp is required for the MCP server: pip install 'facetmark[all]'"
    ) from exc


INSTRUCTIONS = """\
facetmark indexes a personal bookmark library along four retrieval facets:
page content, the queries the page would answer, lexical text, and the saving
episode it belongs to.

Guidance:
* Start with `search_bookmarks`. Vague, memory-shaped queries work: "that thing
  I saved while setting up Docker" is a supported query form, not a fallback.
* `synthesize` answers a question over the library and cites bookmark numbers
  per claim. Prefer it over stitching search results together yourself.
* `find_related` follows typed edges. `session` = saved in the same sitting,
  `supersession` = a newer version of the same thing (directional),
  `same_domain`, `anchor_sibling`, `semantic`.
* Link health is advisory. A `gone` verdict does not mean the bookmark was
  removed; nothing is ever removed.
"""


# ---------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------


@dataclass
class Ctx:
    settings: Settings
    conn: sqlite3.Connection
    _provider: Any = None

    @property
    def provider(self):
        if self._provider is None:
            self._provider = get_provider(self.settings)
        return self._provider


def build_context(settings: Settings | None = None,
                  conn: sqlite3.Connection | None = None) -> Ctx:
    st = settings or get_settings()
    st.ensure_dirs()
    return Ctx(settings=st, conn=conn if conn is not None else open_db(st.db_path))


# ---------------------------------------------------------------------------
# server
# ---------------------------------------------------------------------------


def create_server(  # noqa: C901 - a tool table, not a branchy function
    settings: Settings | None = None, conn: sqlite3.Connection | None = None
) -> FastMCP:
    ctx = build_context(settings, conn)
    mcp = FastMCP(name="facetmark", instructions=INSTRUCTIONS, version=__version__)

    # ---- 1 ----------------------------------------------------------------
    @mcp.tool
    async def search_bookmarks(
        query: Annotated[str, Field(description="Natural language, keywords, or a "
                                    "memory fragment such as 'the CSS thing from "
                                    "around when I was learning Svelte'.")],
        limit: Annotated[int, Field(ge=1, description="Hits per page. Clamped to "
                                    "the server's `max_page_size`; the response "
                                    "reports what was actually served.")] = 10,
        offset: Annotated[int, Field(ge=0, description="Skip this many hits. Use "
                                     "with `depth` from the previous response "
                                     "to page through results.")] = 0,
        depth: Annotated[int | None, Field(ge=1, description="Pin the candidate "
                                           "depth. Pass back the `depth` of the "
                                           "previous page so this one continues "
                                           "it rather than re-ranking.")] = None,
        quick: Annotated[bool, Field(description="Lexical-only. Milliseconds, no "
                                     "model call. Use when latency matters more "
                                     "than recall.")] = False,
        include_related: Annotated[bool, Field(description="Also return one-hop "
                                               "graph neighbours as a separate "
                                               "group.")] = True,
    ) -> dict:
        """Search the bookmark library across all four retrieval facets.

        Returns ranked hits with the facets that found each one, so you can tell
        a lexical match from an episodic one. `expanded` holds graph neighbours
        and is never interleaved with `hits`.

        The default of 10 is a context-window budget, not a recall ceiling: the
        payload carries snippets and per-facet provenance, so a large page is
        expensive to *read*. When `has_more` is true, ask for the next page with
        `offset` and the `depth` this response reported, rather than re-running
        the query at a bigger `limit`.

        An oversized `limit` is clamped rather than rejected, because an agent
        that spends a turn on a validation error has paid more for the mistake
        than the mistake was worth. The served window comes back as `limit` and
        `offset`, so a caller can always tell what it got.
        """
        if quick:
            resp = service.quick_search(
                ctx.conn, query, limit=limit, offset=offset, depth=depth,
                settings=ctx.settings,
            )
        else:
            resp = await service.search(
                ctx.conn, query, limit=limit, offset=offset, depth=depth,
                config=default_config(ctx.settings, ctx.provider),
                provider=ctx.provider, settings=ctx.settings,
                expand_limit=8 if include_related else 0,
            )
        out = resp.as_dict()
        if not include_related:
            out["expanded"] = []
        return out

    # ---- 2 ----------------------------------------------------------------
    @mcp.tool
    async def get_bookmark(
        bookmark_id: int,
        include_body: Annotated[bool, Field(description="Include the full indexed "
                                            "page text. Can be long.")] = False,
    ) -> dict:
        """Full record for one bookmark: enrichment, saving session, link health.

        `health.status` is advisory and `in_graveyard` only means two confirmed
        failures a week apart; the bookmark is still in the library.
        """
        rec = service.bookmark_record(
            ctx.conn, bookmark_id, settings=ctx.settings, include_body=include_body
        )
        if rec is None:
            raise ValueError(f"no bookmark with id {bookmark_id}")
        return rec

    # ---- 3 ----------------------------------------------------------------
    @mcp.tool
    async def list_sessions(
        limit: Annotated[int, Field(ge=1, le=200)] = 30,
        offset: Annotated[int, Field(ge=0)] = 0,
        min_size: Annotated[int, Field(ge=1, description="Skip sessions smaller "
                                       "than this.")] = 2,
    ) -> list[dict]:
        """Saving episodes, newest first.

        A session is a burst of bookmarks saved close together in time, found by
        clustering `date_added` with a gap threshold fitted to this library
        rather than a fixed constant.
        """
        return service.session_list(ctx.conn, limit=limit, offset=offset, min_size=min_size)

    # ---- 4 ----------------------------------------------------------------
    @mcp.tool
    async def get_session(session_id: int) -> dict:
        """Everything saved in one episode, in the order it was saved.

        Useful for "what else was I looking at when I found this" -- the
        neighbours in a session are often the context that makes a bookmark
        make sense again.
        """
        rec = service.session_record(ctx.conn, session_id)
        if rec is None:
            raise ValueError(f"no session with id {session_id}")
        return rec

    # ---- 5 ----------------------------------------------------------------
    @mcp.tool
    async def find_related(
        bookmark_id: int,
        kind: Annotated[str | None, Field(description="One of: session, semantic, "
                                          "supersession, same_domain, "
                                          "anchor_sibling. Omit for all kinds.")] = None,
        limit: Annotated[int, Field(ge=1, le=50)] = 10,
    ) -> list[dict]:
        """Typed neighbours of a bookmark.

        `supersession` is directional: an outgoing edge means this bookmark was
        superseded by the other one, i.e. the other one is the newer version.
        """
        try:
            return service.related_records(ctx.conn, bookmark_id, kind=kind, limit=limit)
        except ValueError as exc:
            raise ValueError(
                f"{exc}. Valid kinds: {', '.join(sorted(EDGE_WEIGHTS))}"
            ) from exc

    # ---- 6 ----------------------------------------------------------------
    @mcp.tool
    async def synthesize(
        query: Annotated[str, Field(description="A question to answer using only "
                                    "what is in the library.")],
        limit: Annotated[int, Field(ge=1, le=20,
                                    description="How many bookmarks to read.")] = 8,
    ) -> dict:
        """Answer a question from the library, with a source per claim.

        Returns `{claims, sources, gaps}`. Each claim cites the numbered sources
        it came from; a claim that cites nothing is dropped rather than shown.
        `gaps` names what the library does not cover, including facets that
        returned nothing and sources with no indexed text. `degraded: true`
        means the model was unavailable and the claims are raw excerpts.
        """
        out = await service.synthesize(
            ctx.conn, query, limit=limit, provider=ctx.provider, settings=ctx.settings
        )
        return out.as_dict()

    # ---- 7 ----------------------------------------------------------------
    @mcp.tool
    async def suggest_from_context(
        text: Annotated[str, Field(description="A paragraph the user is writing, "
                                   "or the current working context.")],
        limit: Annotated[int, Field(ge=1, le=30)] = 8,
    ) -> dict:
        """Surface bookmarks relevant to a block of text, with no model call.

        Lexical only and synchronous, because this is meant to be safe to call
        repeatedly while someone types. The text is never embedded or sent
        anywhere.
        """
        return service.suggest_from_context(ctx.conn, text, limit=limit)

    # ---- 8 ----------------------------------------------------------------
    @mcp.tool
    async def check_link_health(
        bookmark_ids: Annotated[list[int] | None,
                                Field(description="Specific bookmarks. Omit to "
                                      "check whatever is due.")] = None,
        limit: Annotated[int, Field(ge=1, le=500)] = 25,
        probe: Annotated[bool, Field(description="Make network requests. False "
                                     "returns only what is already recorded.")] = False,
    ) -> dict:
        """Report which links still work. Never deletes or hides anything.

        With `probe=false` this is a pure read of stored verdicts. With
        `probe=true` it fetches: a ranged GET locally, then, only for failures,
        DNS-over-HTTPS, the Wayback Machine and a reader proxy to distinguish
        "dead" from "blocked from here". A `gone` verdict needs two
        high-confidence failures at least seven days apart.
        """
        if not probe:
            if bookmark_ids:
                states = [
                    healthmod.state_of(ctx.conn, i, settings=ctx.settings).as_dict()
                    for i in bookmark_ids
                ]
            else:
                due = healthmod.due_for_check(ctx.conn, limit=limit)
                states = [
                    healthmod.state_of(ctx.conn, r["id"], settings=ctx.settings).as_dict()
                    for r in due
                ]
            return {"probed": False, "summary": healthmod.summary(ctx.conn),
                    "states": states}
        rep = await healthmod.check_bookmarks(
            ctx.conn, ids=bookmark_ids, limit=limit, settings=ctx.settings
        )
        ctx.conn.commit()
        return {"probed": True, **rep.as_dict(), "summary": healthmod.summary(ctx.conn)}

    # ---- 9 ----------------------------------------------------------------
    @mcp.tool
    async def save_bookmark(
        url: str,
        title: str = "",
        folder: Annotated[str, Field(description="Display path. Stored verbatim; "
                                     "never split on '/'.")] = "",
    ) -> dict:
        """Add a URL to the facetmark index.

        This does not touch the browser's own bookmarks. facetmark reads the
        browser's export and never writes back to it, so uninstalling it cannot
        damage anything you had before.

        The new row is searchable immediately by title. Content fetching,
        enrichment and vectors happen on the next index run.
        """
        return service.save_bookmark(
            ctx.conn, url, title=title, folder=folder, settings=ctx.settings
        )

    # ---- resources --------------------------------------------------------

    @mcp.resource("bookmark://{bookmark_id}", mime_type="application/json")
    async def bookmark_resource(bookmark_id: str) -> dict:
        """A single bookmark record, addressable as a resource."""
        rec = service.bookmark_record(ctx.conn, int(bookmark_id), settings=ctx.settings)
        if rec is None:
            raise ValueError(f"no bookmark with id {bookmark_id}")
        return rec

    @mcp.resource("session://{session_id}", mime_type="application/json")
    async def session_resource(session_id: str) -> dict:
        """One saving episode with its members."""
        rec = service.session_record(ctx.conn, int(session_id))
        if rec is None:
            raise ValueError(f"no session with id {session_id}")
        return rec

    @mcp.resource("facetmark://stats", mime_type="application/json")
    async def stats_resource() -> dict:
        """Index size, coverage and link-health totals."""
        return service.library_stats(ctx.conn)

    mcp.facetmark_ctx = ctx  # type: ignore[attr-defined]
    return mcp


def main(settings: Settings | None = None) -> None:  # pragma: no cover - runtime
    create_server(settings).run()


if __name__ == "__main__":  # pragma: no cover
    main()
