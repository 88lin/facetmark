#!/usr/bin/env python
"""Drive the MCP server the way an assistant does: over a real stdio pipe.

``tests/test_api.py::TestMcpServer`` calls ``create_server()`` in process. That
proves the tool table is complete and the handlers work. It does not prove that
a client can *launch* the server as a subprocess, complete the JSON-RPC
handshake, call every tool, and read the resources back -- which is the only
thing a user of the MCP integration actually does.

Two failure modes only show up out here: something in the import path writes to
stdout and corrupts the protocol stream, and a tool whose return annotation
FastMCP cannot turn into a schema. Neither is visible to an in-process test.

Everything this touches is a throwaway mock library in a temp directory. It
makes no network calls and needs no model: ``--mock`` all the way down.

    python scripts/mcp_e2e.py            # exit 0 if every check passes
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

NOW = int(time.time())

#: Two topical clusters saved days apart, so the library has sessions and edges
#: rather than just rows. One page has no body: a dead link is a first-class
#: member of a library and the tools have to survive it.
PAGES: list[tuple[str, str, str, int, str]] = [
    ("https://ex.test/rrf", "Reciprocal rank fusion explained", "search", 5,
     "Reciprocal rank fusion merges several ranked lists without calibrating their "
     "scores against each other. Each list contributes 1/(k+rank). The constant k "
     "damps the head so a single confident list cannot dominate the fused order."),
    ("https://ex.test/bm25", "BM25 and why term saturation matters", "search", 7,
     "BM25 saturates term frequency so a document repeating a word fifty times is "
     "not fifty times more relevant. The b parameter controls length normalisation."),
    ("https://ex.test/fts5", "SQLite FTS5 tokenizers", "search", 9,
     "FTS5 ships unicode61, porter and trigram tokenizers. Trigram indexing makes "
     "substring search possible for Chinese text where whitespace carries no "
     "segmentation information."),
    ("https://ex.test/vec", "sqlite-vec for local vector search", "search", 12,
     "sqlite-vec stores float32 vectors in a virtual table and answers k nearest "
     "neighbour queries with a brute force scan. Distances are L2 on the raw "
     "vectors, so normalise before insert if you want cosine."),
    ("https://ex.test/hnsw", "HNSW graphs in plain words", "search", 15,
     "Hierarchical navigable small world graphs give logarithmic search by keeping "
     "long range links on upper layers and short links at the bottom."),
    ("https://ex.test/sourdough", "Sourdough hydration for beginners", "cooking",
     3 * 24 * 60 + 4,
     "Hydration is water weight divided by flour weight. Eighty percent hydration "
     "gives an open crumb but a slack dough that beginners find hard to shape."),
    ("https://ex.test/knife", "How to sharpen a kitchen knife", "cooking",
     3 * 24 * 60 + 9,
     "A whetstone at a fifteen degree angle removes steel from the bevel until a "
     "burr forms along the full length of the edge. Then you strop the burr off."),
    ("https://ex.test/stock", "Chicken stock without a pressure cooker", "cooking",
     3 * 24 * 60 + 13,
     "Simmer bones below a boil for six hours. A rolling boil emulsifies fat into "
     "the liquid and the stock turns cloudy and greasy."),
    ("https://ex.test/rust-async", "Async Rust without tears", "code",
     9 * 24 * 60 + 2,
     "A future in Rust does nothing until polled. The executor owns the poll loop "
     "and wakers are how a leaf future says it is ready to make progress."),
    ("https://ex.test/pyasync", "Python asyncio task groups", "code",
     9 * 24 * 60 + 6,
     "TaskGroup replaces gather for structured concurrency. When one child raises "
     "the group cancels its siblings and re-raises as an ExceptionGroup."),
    ("https://ex.test/dead", "A page that no longer resolves", "code",
     20 * 24 * 60, ""),
    ("https://ex.test/typescript", "Erasable TypeScript syntax", "code",
     9 * 24 * 60 + 11,
     "Constructor parameter properties and enums cannot be removed by a type "
     "stripper because they emit runtime code. The erasableSyntaxOnly flag makes "
     "the compiler reject them."),
]

TOOLS = [
    "check_link_health", "find_related", "get_bookmark", "get_session",
    "list_sessions", "save_bookmark", "search_bookmarks", "suggest_from_context",
    "synthesize",
]


async def build_library(home: Path) -> dict:
    from facetmark import service
    from facetmark.config import Settings
    from facetmark.db import open_db
    from facetmark.text import sync_fts

    st = Settings(data_dir=home, use_mock_provider=True, embed_dim=64)
    conn = open_db(home / "fm.db")
    ids: dict[str, int] = {}
    for url, title, folder, mins_ago, body in PAGES:
        rec = service.save_bookmark(conn, url, title=title, folder=folder,
                                    date_added=NOW - mins_ago * 60, settings=st)
        bid = rec["bookmark_id"]
        ids[url] = bid
        if body:
            conn.execute(
                "INSERT INTO content(bookmark_id, body_text, body_hash, char_count, "
                "  extractor, fetch_channel, http_status, fetched_at) "
                "VALUES(?,?,?,?,'probe','a',200,?)",
                (bid, body, f"h{bid}", len(body), NOW),
            )
        sync_fts(conn, bid, title=title, body=body)
    conn.commit()
    await service.index_all(conn, settings=st, fetch=False)
    stats = service.library_stats(conn)
    conn.close()
    return {"ids": ids, "stats": stats}


class Probe:
    """Records every check instead of stopping at the first failure."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.rows.append((name, "PASS", detail))

    def bad(self, name: str, detail: str) -> None:
        self.rows.append((name, "FAIL", detail))

    async def run(self, name, call, check):
        try:
            res = await call()
        except Exception as exc:  # noqa: BLE001 - the probe reports, never raises
            self.bad(name, f"{type(exc).__name__}: {exc}")
            return None
        try:
            self.ok(name, check(res) or "")
        except AssertionError as exc:
            self.bad(name, f"shape: {exc}")
        except Exception as exc:  # noqa: BLE001
            last = traceback.format_exc(limit=1).splitlines()[-1]
            self.bad(name, f"{type(exc).__name__}: {exc} | {last}")
        return res

    async def raises(self, name, call, wants: tuple[str, ...]):
        try:
            res = await call()
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            missing = [w for w in wants if w not in msg]
            if missing:
                self.bad(name, f"message lacks {missing}: {msg[:80]}")
            else:
                self.ok(name, msg[:70])
            return
        self.bad(name, f"did not raise, returned {str(payload(res))[:80]}")

    def report(self) -> int:
        width = max(len(r[0]) for r in self.rows)
        fails = sum(1 for r in self.rows if r[1] == "FAIL")
        for name, status, detail in self.rows:
            print(f"  {status}  {name.ljust(width)}  {detail}")
        print(f"\n{len(self.rows) - fails}/{len(self.rows)} checks passed")
        return fails


def payload(res):
    """fastmcp hands back a CallToolResult; ``.data`` is the structured body."""
    return res.data if hasattr(res, "data") else res


def text(res) -> str:
    return res[0].text if isinstance(res, list) else res.contents[0].text


async def drive(home: Path, built: dict, python: str) -> int:
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    ids = built["ids"]
    rrf = ids["https://ex.test/rrf"]
    dead = ids["https://ex.test/dead"]

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(Path(__file__).resolve().parents[1] / "src"),
                    env.get("PYTHONPATH", "")) if p
    )
    env["FACETMARK_USE_MOCK_PROVIDER"] = "true"
    env["FACETMARK_EMBED_DIM"] = "64"
    env["FACETMARK_DATA_DIR"] = str(home)
    transport = StdioTransport(
        command=python,
        args=["-m", "facetmark.cli", "mcp", "--db", str(home / "fm.db"), "--mock"],
        env=env,
    )

    p = Probe()
    async with Client(transport) as c:

        def tools(res):
            names = sorted(t.name for t in res)
            assert names == TOOLS, f"got {names}"
            blank = [t.name for t in res if not (t.description or "").strip()]
            assert not blank, f"undescribed: {blank}"
            schemaless = [t.name for t in res
                          if not (t.inputSchema or {}).get("properties")]
            assert not schemaless, f"no input schema: {schemaless}"
            return f"{len(names)} tools, all described and schema'd"

        await p.run("list_tools", c.list_tools, tools)

        def full(res):
            d = payload(res)
            assert d.get("hits"), f"no hits: {sorted(d)}"
            titles = [h["title"] for h in d["hits"]]
            assert any("fusion" in t.lower() for t in titles), titles
            return f"{len(d['hits'])} hits, top={titles[0][:34]!r}"

        await p.run("search_bookmarks(full)",
                    lambda: c.call_tool("search_bookmarks",
                                        {"query": "rank fusion", "limit": 5}), full)

        await p.run("search_bookmarks(quick)",
                    lambda: c.call_tool("search_bookmarks",
                                        {"query": "trigram tokenizer", "limit": 5,
                                         "quick": True}),
                    lambda r: f"{len(payload(r)['hits'])} hits")

        def related_on(res):
            d = payload(res)
            assert d.get("expanded"), "include_related=True produced no neighbours"
            hits = {h["bookmark_id"] for h in d["hits"]}
            exp = {e["bookmark_id"] for e in d["expanded"]}
            assert not hits & exp, f"expansion interleaved with hits: {hits & exp}"
            assert all(e.get("via") for e in d["expanded"]), \
                "an expansion row cannot say which hit it came from"
            return f"{len(exp)} neighbours, disjoint from {len(hits)} hits"

        await p.run("search_bookmarks(include_related=True)",
                    lambda: c.call_tool("search_bookmarks",
                                        {"query": "rank fusion", "limit": 3,
                                         "include_related": True}), related_on)

        await p.run("search_bookmarks(include_related=False)",
                    lambda: c.call_tool("search_bookmarks",
                                        {"query": "rank fusion", "limit": 3,
                                         "include_related": False}),
                    lambda r: (_ for _ in ()).throw(AssertionError("expanded not empty"))
                    if payload(r).get("expanded") else "expanded suppressed")

        def with_body(res):
            d = payload(res)
            assert d.get("bookmark_id") == rrf, d.get("bookmark_id")
            assert d.get("body_text"), f"include_body returned no text: {sorted(d)}"
            return f"id={d['bookmark_id']}, {len(d)} keys, {len(d['body_text'])} chars"

        await p.run("get_bookmark(include_body=True)",
                    lambda: c.call_tool("get_bookmark",
                                        {"bookmark_id": rrf, "include_body": True}),
                    with_body)

        def without_body(res):
            d = payload(res)
            assert not d.get("body_text"), \
                "include_body=False still shipped the page text"
            assert d.get("summary") or d.get("title"), sorted(d)
            return "page text withheld"

        await p.run("get_bookmark(include_body=False)",
                    lambda: c.call_tool("get_bookmark",
                                        {"bookmark_id": rrf, "include_body": False}),
                    without_body)

        await p.raises("get_bookmark(unknown) explains itself",
                       lambda: c.call_tool("get_bookmark", {"bookmark_id": 999_999}),
                       ("999999",))

        def sessions(res):
            d = payload(res)
            assert isinstance(d, list) and d, f"no sessions: {d!r}"
            assert "session_id" in d[0] or "id" in d[0], sorted(d[0])
            return f"{len(d)} sessions"

        listed = await p.run("list_sessions",
                             lambda: c.call_tool("list_sessions", {"limit": 10}),
                             sessions)
        rows = payload(listed) if listed is not None else None
        sid = rows[0].get("session_id", rows[0].get("id")) if rows else None

        if sid is None:
            p.bad("get_session", "no session id to ask for")
        else:
            def session(res):
                d = payload(res)
                members = d.get("bookmarks") or d.get("members")
                assert members, sorted(d)
                return f"session {sid} holds {len(members)} bookmarks"

            await p.run("get_session",
                        lambda: c.call_tool("get_session", {"session_id": sid}), session)

        def neighbours(res):
            d = payload(res)
            assert isinstance(d, list), type(d)
            assert d, "a bookmark in a session has no neighbours"
            return f"{len(d)} neighbours, kinds={sorted({e.get('kind') for e in d})}"

        await p.run("find_related",
                    lambda: c.call_tool("find_related",
                                        {"bookmark_id": rrf, "limit": 10}), neighbours)

        await p.raises("find_related(bad kind) lists the legal ones",
                       lambda: c.call_tool("find_related",
                                           {"bookmark_id": rrf, "kind": "not-a-kind"}),
                       ("session", "semantic"))

        def synth(res):
            d = payload(res)
            assert d.get("sources") or d.get("hits"), sorted(d)
            return f"keys={sorted(d)}"

        await p.run("synthesize",
                    lambda: c.call_tool("synthesize",
                                        {"query": "how do i fuse ranked lists",
                                         "limit": 5}), synth)

        await p.run("suggest_from_context",
                    lambda: c.call_tool("suggest_from_context",
                                        {"text": "I am writing about merging several "
                                                 "ranked candidate lists into one order "
                                                 "without calibrating their scores.",
                                         "limit": 5}),
                    lambda r: f"keys={sorted(payload(r))}")

        await p.run("check_link_health(probe=false)",
                    lambda: c.call_tool("check_link_health",
                                        {"bookmark_ids": [rrf, dead], "probe": False}),
                    lambda r: f"keys={sorted(payload(r))}")

        def saved(res):
            d = payload(res)
            assert d.get("bookmark_id"), sorted(d)
            assert "mcp" in (d.get("url") or ""), d.get("url")
            return f"id={d['bookmark_id']}"

        await p.run("save_bookmark",
                    lambda: c.call_tool("save_bookmark",
                                        {"url": "https://ex.test/mcp-roundtrip",
                                         "title": "Saved over MCP", "folder": "inbox"}),
                    saved)

        def roundtrip(res):
            titles = [h["title"] for h in payload(res).get("hits", [])]
            assert "Saved over MCP" in titles, titles
            return "the page saved one call ago is findable"

        await p.run("save -> search roundtrip",
                    lambda: c.call_tool("search_bookmarks",
                                        {"query": "Saved over MCP", "limit": 10,
                                         "quick": True}), roundtrip)

        def templates(res):
            got = sorted(r.uriTemplate for r in res)
            assert "bookmark://{bookmark_id}" in got, got
            assert "session://{session_id}" in got, got
            return ", ".join(got)

        await p.run("list_resource_templates", c.list_resource_templates, templates)

        def resources(res):
            got = sorted(str(r.uri) for r in res)
            assert any("facetmark://stats" in u for u in got), got
            return ", ".join(got)

        await p.run("list_resources", c.list_resources, resources)

        def stats(res):
            d = json.loads(text(res))
            assert d.get("bookmarks", 0) >= len(PAGES), d.get("bookmarks")
            return f"bookmarks={d['bookmarks']}, {len(d)} keys"

        await p.run("read facetmark://stats",
                    lambda: c.read_resource("facetmark://stats"), stats)

        def bookmark_res(res):
            d = json.loads(text(res))
            assert d.get("bookmark_id") == rrf, d.get("bookmark_id")
            return f"id={d['bookmark_id']}"

        await p.run("read bookmark://<id>",
                    lambda: c.read_resource(f"bookmark://{rrf}"), bookmark_res)

        if sid is not None:
            await p.run("read session://<id>",
                        lambda: c.read_resource(f"session://{sid}"),
                        lambda r: f"keys={sorted(json.loads(text(r)))[:5]}")

    print("\n--- facetmark MCP, end to end over stdio ---")
    return p.report()


async def main_async(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--python", default=sys.executable,
                    help="interpreter used to launch the server subprocess")
    ap.add_argument("--keep", action="store_true",
                    help="leave the throwaway library on disk")
    ap.add_argument("--timeout", type=float, default=240.0)
    args = ap.parse_args(argv)

    tmp = tempfile.mkdtemp(prefix="facetmark-mcp-")
    home = Path(tmp)
    try:
        built = await build_library(home)
        s = built["stats"]
        print(f"library: bookmarks={s['bookmarks']} sessions={s['sessions']} "
              f"edges={s['edges']} enriched={s['enriched']} "
              f"intent_kept={s['intent_kept']}\n")
        return await asyncio.wait_for(drive(home, built, args.python), args.timeout)
    finally:
        if args.keep:
            print(f"\nlibrary left at {home}")
        else:
            import shutil
            shutil.rmtree(home, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    return 1 if asyncio.run(main_async(argv)) else 0


if __name__ == "__main__":
    sys.exit(main())
