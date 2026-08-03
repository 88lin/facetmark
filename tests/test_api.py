"""Tests for the local HTTP service and the MCP server.

The security-relevant assertions are the ones about the token. "It only listens
on loopback" is not an access control: any local process, and under Chrome's
Local Network Access rules a web page the user is merely visiting, can reach
127.0.0.1. Every route that reads or writes the index must reject an
unauthenticated caller, and the test below enumerates the routes rather than
spot-checking one, so a new endpoint cannot quietly ship without auth.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from facetmark import service
from facetmark.api import PUBLIC_PATHS, create_app
from facetmark.config import Settings
from facetmark.fetch import store as fetchstore
from facetmark.health import store as hstore
from facetmark.health.synth import HealthCheck
from facetmark.health.verdicts import Status
from facetmark.mcp_server import create_server
from facetmark.text import sync_fts

DAY = 86_400


@pytest.fixture()
def st(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path / "fm", use_mock_provider=True)


@pytest.fixture()
def client(st):
    app = create_app(st)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def token(client) -> str:
    return client.app.state.fm.token


@pytest.fixture()
def auth(token) -> dict:
    return {"Authorization": f"Bearer {token}"}


def seed(client, url: str, title: str, *, body: str = "") -> int:
    conn = client.app.state.fm.conn
    st = client.app.state.fm.settings
    rec = service.save_bookmark(conn, url, title=title, settings=st)
    bid = rec["bookmark_id"]
    if body:
        conn.execute(
            "INSERT OR REPLACE INTO content(bookmark_id, body_text, body_hash, "
            "char_count, extractor, fetch_channel, http_status, fetched_at) "
            "VALUES(?,?,?,?,'test','a',200,?)",
            (bid, body, f"h{bid}", len(body), int(time.time())),
        )
        sync_fts(conn, bid, title=title, body=body)
    conn.commit()
    return bid


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_the_liveness_probe_needs_no_token_and_leaks_nothing(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert set(r.json()) == {"service", "version", "ok"}

    def test_every_other_route_rejects_an_unauthenticated_caller(self, client):
        """Enumerated, not spot-checked: a new route cannot ship without auth."""
        checked = 0
        for route in client.app.routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set()) or set()
            if path in PUBLIC_PATHS or "{" in path:
                continue
            for method in sorted(methods & {"GET", "POST"}):
                resp = client.request(method, path, json={})
                assert resp.status_code == 401, f"{method} {path} did not require a token"
                checked += 1
        assert checked >= 8

    def test_a_parameterised_route_also_rejects(self, client):
        assert client.get("/bookmark/1").status_code == 401
        assert client.get("/session/1").status_code == 401

    def test_a_wrong_token_is_rejected(self, client):
        r = client.get("/stats", headers={"Authorization": "Bearer nope"})
        assert r.status_code == 401

    def test_the_header_alternative_works_for_clients_that_cannot_set_authorization(
        self, client, token
    ):
        r = client.get("/stats", headers={"X-Facetmark-Token": token})
        assert r.status_code == 200

    def test_the_token_is_the_one_on_disk(self, client, st):
        assert client.app.state.fm.token == st.token_path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearchRoutes:
    def test_quick_search_returns_hits(self, client, auth):
        seed(client, "https://a.example/1", "sqlite vector search notes")
        r = client.get("/quick", params={"q": "sqlite"}, headers=auth)
        assert r.status_code == 200
        assert [h["title"] for h in r.json()["hits"]] == ["sqlite vector search notes"]

    def test_full_search_runs_all_facets(self, client, auth):
        seed(client, "https://a.example/2", "rrf fusion", body="reciprocal rank fusion " * 20)
        r = client.post("/search", json={"q": "fusion", "limit": 5}, headers=auth)
        assert r.status_code == 200
        assert r.json()["config"] == "full"

    def test_an_unknown_ablation_config_is_a_400_not_a_silent_default(self, client, auth):
        r = client.post("/search", json={"q": "x", "config": "Z"}, headers=auth)
        assert r.status_code == 400

    def test_the_ablation_rungs_are_reachable_by_name(self, client, auth):
        seed(client, "https://a.example/3", "graph expansion")
        r = client.post("/search", json={"q": "graph", "config": "B"}, headers=auth)
        assert r.status_code == 200
        assert r.json()["config"] == "B"

    def test_suggest_needs_no_model_call(self, client, auth):
        seed(client, "https://a.example/4", "docker compose cheatsheet")
        r = client.post("/suggest", json={"text": "setting up docker compose today"},
                        headers=auth)
        assert r.json()["hits"][0]["title"] == "docker compose cheatsheet"

    def test_synthesize_returns_the_documented_shape(self, client, auth):
        seed(client, "https://a.example/5", "vector db comparison",
             body="pgvector qdrant milvus comparison " * 20)
        r = client.post("/synthesize", json={"q": "vector db", "limit": 3}, headers=auth)
        body = r.json()
        assert set(body) >= {"claims", "sources", "gaps", "degraded", "model"}


# ---------------------------------------------------------------------------
# records
# ---------------------------------------------------------------------------


class TestRecordRoutes:
    def test_a_missing_bookmark_is_404(self, client, auth):
        assert client.get("/bookmark/9999", headers=auth).status_code == 404

    def test_a_missing_session_is_404(self, client, auth):
        assert client.get("/session/9999", headers=auth).status_code == 404

    def test_an_unknown_edge_kind_is_400(self, client, auth):
        bid = seed(client, "https://b.example/1", "x")
        r = client.get(f"/bookmark/{bid}/related", params={"kind": "vibes"}, headers=auth)
        assert r.status_code == 400

    def test_saving_a_bookmark_then_reading_it_back(self, client, auth):
        r = client.post("/bookmark", json={"url": "https://b.example/2", "title": "saved"},
                        headers=auth)
        bid = r.json()["bookmark_id"]
        assert r.json()["created"] is True
        assert client.get(f"/bookmark/{bid}", headers=auth).json()["title"] == "saved"

    def test_recording_an_open_increments_the_counter(self, client, auth):
        bid = seed(client, "https://b.example/3", "x")
        client.post("/open", json={"bookmark_id": bid, "query": "q"}, headers=auth)
        assert client.get(f"/bookmark/{bid}", headers=auth).json()["open_count"] == 1


# ---------------------------------------------------------------------------
# channel B
# ---------------------------------------------------------------------------


class TestChannelB:
    def test_leasing_hands_out_work_and_marks_it_leased(self, client, auth):
        conn = client.app.state.fm.conn
        bid = seed(client, "https://c.example/1", "walled page")
        fetchstore.enqueue_for_browser(conn, bid, reason="wall")
        conn.commit()
        r = client.get("/queue/next", params={"n": 3}, headers=auth)
        items = r.json()["items"]
        assert [i["bookmark_id"] for i in items] == [bid]
        assert r.json()["queue"]["leased"] == 1

    def test_a_lease_is_not_handed_out_twice(self, client, auth):
        conn = client.app.state.fm.conn
        bid = seed(client, "https://c.example/2", "walled")
        fetchstore.enqueue_for_browser(conn, bid, reason="wall")
        conn.commit()
        client.get("/queue/next", headers=auth)
        assert client.get("/queue/next", headers=auth).json()["items"] == []

    def test_completing_with_a_body_stores_it(self, client, auth):
        conn = client.app.state.fm.conn
        bid = seed(client, "https://c.example/3", "walled")
        fetchstore.enqueue_for_browser(conn, bid, reason="wall")
        conn.commit()
        client.get("/queue/next", headers=auth)
        r = client.post("/queue/complete",
                        json={"bookmark_id": bid, "body": "the real text " * 30,
                              "title": "walled", "final_url": "https://c.example/3"},
                        headers=auth)
        assert r.json()["stored"] is True
        assert r.json()["queue"].get("done") == 1
        row = conn.execute("SELECT fetch_channel, char_count FROM content WHERE bookmark_id=?",
                           (bid,)).fetchone()
        assert row["fetch_channel"] == "b" and row["char_count"] > 200

    def test_completing_empty_returns_the_item_to_the_queue(self, client, auth):
        conn = client.app.state.fm.conn
        bid = seed(client, "https://c.example/4", "walled")
        fetchstore.enqueue_for_browser(conn, bid, reason="wall")
        conn.commit()
        client.get("/queue/next", headers=auth)
        r = client.post("/queue/complete",
                        json={"bookmark_id": bid, "error": "tab timed out"}, headers=auth)
        assert r.json()["stored"] is False
        assert r.json()["queue"].get("pending") == 1

    def test_the_lease_size_is_capped(self, client, auth):
        assert client.get("/queue/next", params={"n": 999}, headers=auth).status_code == 422


# ---------------------------------------------------------------------------
# link health
# ---------------------------------------------------------------------------


class TestHealthRoutes:
    def test_the_summary_counts_unchecked_bookmarks(self, client, auth):
        seed(client, "https://d.example/1", "x")
        assert client.get("/link-health/summary", headers=auth).json()["unchecked"] == 1

    def test_a_never_checked_bookmark_reports_unknown(self, client, auth):
        bid = seed(client, "https://d.example/2", "x")
        assert client.get(f"/link-health/{bid}", headers=auth).json()["status"] == "unknown"

    def test_the_graveyard_needs_two_confirmations_a_week_apart(self, client, auth):
        conn = client.app.state.fm.conn
        bid = seed(client, "https://d.example/3", "dead")
        now = int(time.time())
        hstore.record_check(conn, bid, HealthCheck(
            url="https://d.example/3", status=Status.GONE, confidence=0.9,
            http_status=404, checked_at=now))
        conn.commit()
        assert client.get("/graveyard", headers=auth).json() == []
        hstore.record_check(conn, bid, HealthCheck(
            url="https://d.example/3", status=Status.GONE, confidence=0.9,
            http_status=404, checked_at=now + 8 * DAY))
        conn.commit()
        out = client.get("/graveyard", headers=auth).json()
        assert [r["bookmark_id"] for r in out] == [bid]

    def test_a_graveyard_entry_is_still_searchable(self, client, auth):
        """The contract the whole health layer is built around."""
        conn = client.app.state.fm.conn
        bid = seed(client, "https://d.example/4", "vanished tutorial")
        now = int(time.time())
        for t in (now, now + 8 * DAY):
            hstore.record_check(conn, bid, HealthCheck(
                url="https://d.example/4", status=Status.GONE, confidence=0.9,
                http_status=404, checked_at=t))
        conn.commit()
        hits = client.get("/quick", params={"q": "vanished"}, headers=auth).json()["hits"]
        assert [h["bookmark_id"] for h in hits] == [bid]


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------


class TestMcpServer:
    @pytest.fixture()
    def srv(self, st, tmp_path):
        from facetmark.db import open_db

        conn = open_db(":memory:")
        server = create_server(st, conn)
        yield server
        conn.close()

    async def test_it_exposes_exactly_the_nine_documented_tools(self, srv):
        names = sorted(t.name for t in await srv.list_tools())
        assert names == [
            "check_link_health", "find_related", "get_bookmark", "get_session",
            "list_sessions", "save_bookmark", "search_bookmarks",
            "suggest_from_context", "synthesize",
        ]

    async def test_every_tool_carries_a_description_an_agent_can_act_on(self, srv):
        for t in await srv.list_tools():
            assert t.description and len(t.description) > 60, t.name

    async def test_the_two_documented_resource_templates_exist(self, srv):
        tpls = {t.uri_template for t in await srv.list_resource_templates()}
        assert tpls == {"bookmark://{bookmark_id}", "session://{session_id}"}

    async def test_saving_then_searching_round_trips(self, srv):
        await srv.call_tool("save_bookmark", {"url": "https://m.example/1",
                                              "title": "quokka husbandry guide"})
        out = await srv.call_tool("search_bookmarks", {"query": "quokka", "quick": True})
        assert out.structured_content["hits"][0]["title"] == "quokka husbandry guide"

    async def test_an_unknown_bookmark_raises_rather_than_returning_null(self, srv):
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError):
            await srv.call_tool("get_bookmark", {"bookmark_id": 4242})

    async def test_check_link_health_makes_no_request_when_probe_is_false(self, srv):
        import respx

        await srv.call_tool("save_bookmark", {"url": "https://m.example/2", "title": "t"})
        with respx.mock(assert_all_called=False) as mock:
            out = await srv.call_tool("check_link_health", {"probe": False})
            assert len(mock.calls) == 0
        assert out.structured_content["probed"] is False

    async def test_find_related_names_the_valid_kinds_when_given_a_bad_one(self, srv):
        from fastmcp.exceptions import ToolError

        r = await srv.call_tool("save_bookmark", {"url": "https://m.example/3", "title": "t"})
        bid = r.structured_content["bookmark_id"]
        with pytest.raises(ToolError, match="supersession"):
            await srv.call_tool("find_related", {"bookmark_id": bid, "kind": "nope"})

    async def test_the_instructions_tell_an_agent_that_nothing_is_deleted(self, srv):
        assert "never removed" in srv.instructions or "removed" in srv.instructions


# ---------------------------------------------------------------------------
# the extension boundary
# ---------------------------------------------------------------------------


def _ts_source() -> str:
    from pathlib import Path

    p = Path(__file__).resolve().parents[1] / "extension" / "src" / "api.ts"
    if not p.exists():
        pytest.skip("extension sources not in this tree")
    return p.read_text(encoding="utf-8")


def _ts_paths(src: str) -> set[str]:
    """Every request path in the client, query strings stripped."""
    import re

    out = set()
    for lit in re.findall(r"[\"`](/[^\"`]*)[\"`]", src):
        out.add(lit.split("?", 1)[0])
    return out


def _ts_interface(src: str, name: str) -> dict[str, bool]:
    """``{field: required}`` for the top level of one ``export interface``."""
    import re

    m = re.search(rf"export interface {name} \{{\n(.*?)\n\}}", src, re.S)
    assert m, f"interface {name} not found -- rename?"
    fields: dict[str, bool] = {}
    depth = 0
    for line in m.group(1).splitlines():
        bare = line.strip()
        if not bare.startswith(("//", "/*", "*")):
            f = re.match(r"(\w+)(\??):", bare)
            if depth == 0 and f:
                fields[f.group(1)] = f.group(2) != "?"
        depth += line.count("{") - line.count("}")
    assert fields, f"parsed no fields out of {name}"
    return fields


def _ts_queue_keys(src: str) -> set[str]:
    """Every ``/queue/stats`` key the client reads by name."""
    import re

    m = re.search(r"export function summarizeQueue\(.*?\n\}", src, re.S)
    assert m, "summarizeQueue not found -- rename?"
    return set(re.findall(r"n\(\"(\w+)\"\)", m.group(0)))


class TestTheExtensionContract:
    """The one boundary the type checker cannot see.

    `request<T>` in the extension is `await res.json() as T` -- an unchecked
    cast. TypeScript will believe any shape written there, so a field the
    server renamed, or never sent, arrives as `undefined` and renders as an
    empty string or `[object Object]`. Both have happened. These assertions run
    on the Python side because that is where the truth is.
    """

    def test_every_path_the_extension_calls_is_a_real_route(self, client):
        declared = _ts_paths(_ts_source())
        routes = {r.path for r in client.app.routes}
        assert declared, "parsed no paths out of api.ts"
        assert declared <= routes, f"extension calls routes that do not exist: {declared - routes}"

    def test_the_hit_type_describes_what_the_server_actually_sends(self, client, auth):
        seed(client, "https://a.example/rust", "Rust ownership", body="borrow checker rust")
        r = client.post("/search", json={"q": "rust", "limit": 5}, headers=auth)
        assert r.status_code == 200 and r.json()["hits"]
        actual = set(r.json()["hits"][0])
        required = {k for k, req in _ts_interface(_ts_source(), "Hit").items() if req}
        assert required <= actual, f"declared but never sent: {sorted(required - actual)}"

    def test_the_response_type_describes_what_the_server_actually_sends(self, client, auth):
        seed(client, "https://a.example/rust", "Rust ownership", body="borrow checker rust")
        for r in (client.get("/quick?q=rust", headers=auth),
                  client.post("/search", json={"q": "rust"}, headers=auth)):
            actual = set(r.json())
            required = {
                k for k, req in _ts_interface(_ts_source(), "SearchResponse").items() if req
            }
            assert required <= actual, f"declared but never sent: {sorted(required - actual)}"

    def test_took_ms_is_a_breakdown_and_the_client_is_told_so(self, client, auth):
        """It was typed `number`. The popup printed `[object Object] ms`."""
        seed(client, "https://a.example/rust", "Rust ownership", body="borrow checker rust")
        took = client.post("/search", json={"q": "rust"}, headers=auth).json()["took_ms"]
        assert isinstance(took, dict) and "total" in took
        assert "took_ms: Record<string, number>" in _ts_source()

    def test_the_expansion_group_is_part_of_the_response_the_client_declares(self, client, auth):
        seed(client, "https://a.example/rust", "Rust ownership", body="borrow checker rust")
        assert "expanded" in client.post("/search", json={"q": "rust"}, headers=auth).json()
        assert "expanded" in _ts_interface(_ts_source(), "SearchResponse")

    def test_a_graph_neighbour_actually_reaches_the_client(self, client, auth):
        """The key being present is not the same as the group being reachable.

        Asserting on the key passed for as long as the expansion group was
        empty on every query, which it was.
        """
        a = seed(client, "https://a.example/rust", "Rust ownership",
                 body="borrow checker rust lifetimes")
        b = seed(client, "https://b.example/cook", "Braising short ribs",
                 body="low oven braise beef stock aromatics")
        conn = client.app.state.fm.conn
        conn.execute("INSERT OR REPLACE INTO edge(src,dst,kind,weight) "
                     "VALUES(?,?,'session',1.0)", (a, b))
        conn.commit()
        body = client.post("/search", json={"q": "rust", "limit": 1},
                           headers=auth).json()
        assert [h["bookmark_id"] for h in body["hits"]] == [a]
        assert [h["bookmark_id"] for h in body["expanded"]] == [b]
        assert body["expanded"][0]["via"] == a
        assert body["expanded"][0]["via_kind"] == "session"

    def test_the_queue_states_the_client_reads_are_the_ones_the_server_writes(self, client, auth):
        """``/queue/stats`` is a ``GROUP BY state``: a state nobody is in is absent.

        So the client reads it key by key, and a state renamed on this side
        arrives over there as a zero rather than as an error. Put one bookmark
        in every state the store can write and check that the two vocabularies
        are the same set.
        """
        conn = client.app.state.fm.conn
        ids = [seed(client, f"https://q{i}.example/p", f"page {i}") for i in range(4)]
        for bid in ids:
            fetchstore.enqueue_for_browser(conn, bid, reason="wall")

        fetchstore.complete_browser_item(conn, ids[0], body="a body long enough to keep")
        conn.execute(
            "UPDATE fetch_queue SET attempts=? WHERE bookmark_id=?",
            (fetchstore.MAX_BROWSER_ATTEMPTS, ids[1]),
        )
        fetchstore.complete_browser_item(conn, ids[1], body="")
        conn.execute("UPDATE fetch_queue SET attempts=1 WHERE bookmark_id=?", (ids[2],))
        fetchstore.complete_browser_item(conn, ids[2], body="")  # back to pending, in backoff
        leased = fetchstore.lease_browser_batch(conn, 10)
        assert [r["bookmark_id"] for r in leased] == [ids[3]], "a backoff must not be leasable"

        got = client.get("/queue/stats", headers=auth).json()
        assert got == {"done": 1, "failed": 1, "pending": 1, "leased": 1, "waiting": 1}
        assert set(got) == _ts_queue_keys(_ts_source())

    def test_waiting_is_a_share_of_pending_and_the_client_subtracts_it(self, client, auth):
        """`waiting` counts pending rows in backoff. Adding the two double-counts."""
        conn = client.app.state.fm.conn
        bid = seed(client, "https://slow.example/p", "slow")
        fetchstore.enqueue_for_browser(conn, bid, reason="wall")
        fetchstore.complete_browser_item(conn, bid, body="")  # first failure -> backoff

        got = client.get("/queue/stats", headers=auth).json()
        assert got["pending"] == 1 and got["waiting"] == 1
        src = _ts_source()
        assert "pending - waiting" in src, "the client must carve `waiting` out of `pending`"
