"""Remote waits must leave local reading, opening and cancellation responsive.

Every wait uses an Event and MockProvider. No fixture contacts a remote host.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import sqlite3
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest

from facetmark import api, health, service
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.configfile import config_path, read_config
from facetmark.fetch import store as fetchstore
from facetmark.health import HealthCheck, LocalProbe, LocalVerdict, Status
from facetmark.mcp_server import Ctx, create_server
from facetmark.providers import MockProvider

WAIT_SECONDS = 5


async def bounded(awaitable):
    return await asyncio.wait_for(awaitable, timeout=WAIT_SECONDS)


async def dispose(task, release=None):
    if release is not None:
        release.set()
    if not task.done():
        task.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await bounded(task)


class GatedProvider(MockProvider):
    def __init__(self, settings):
        super().__init__(settings)
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        self.chat_entered, self.chat_release = asyncio.Event(), asyncio.Event()
        self.failure = None
        self.closed = False

    async def embed(self, texts):
        self.entered.set()
        await self.release.wait()
        if self.failure is not None:
            raise self.failure
        return await super().embed(texts)

    async def chat_json(self, system, user):
        self.chat_entered.set()
        await self.chat_release.wait()
        return await super().chat_json(system, user)

    async def aclose(self):
        self.closed = True
        await super().aclose()


@asynccontextmanager
async def local_client(tmp_path, monkeypatch):
    directory = tmp_path / "responsive-library"
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(directory))
    settings = Settings(data_dir=directory, use_mock_provider=True, embed_dim=8,
        embed_model="mock-embed", chat_model="mock-chat", health_enable_external=False,
        chat_extra_body=json.dumps({"metadata": {"values": ["saved"]}}))
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        state = app.state.fm
        provider = GatedProvider(state.settings)
        state._provider = provider
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 42000)),
            base_url="http://127.0.0.1:8787", headers={"Authorization": "Bearer " + state.token},
        ) as client:
            yield client, state, provider


def seed(state, *, body="Synthetic saved evidence about responsive recovery."):
    bid = service.save_bookmark(state.conn, "https://responsive.test/saved-page",
        title="Synthetic recovery page", settings=state.settings)["bookmark_id"]
    if body is not None:
        fetchstore.store_body(state.conn, bid, body=body, extractor="synthetic-local", channel="extension")
    state.conn.commit()
    return bid


async def assert_local_controls_respond(client, bid):
    listed = await bounded(client.get("/bookmarks"))
    assert listed.status_code == 200 and listed.json()["total"] >= 1, listed.text
    reading = await bounded(client.get(f"/bookmark/{bid}?body=true"))
    assert reading.status_code == 200 and reading.json()["bookmark_id"] == bid, reading.text
    opened = await bounded(client.post("/open", json={"bookmark_id": bid, "query": "synthetic"}))
    assert opened.status_code == 200 and opened.json() == {"ok": True}, opened.text
    settings = await bounded(client.get("/admin/settings"))
    assert settings.status_code == 200, settings.text
    stopped = await bounded(client.post("/admin/jobs/cancel"))
    assert stopped.status_code == 200, stopped.text


async def assert_settings_rejected_while_waiting(client, state, provider):
    previous_settings = state.settings
    previous_config = read_config(config_path(state.settings.data_dir))
    written = await bounded(client.put("/admin/settings", json={"values": {"enrich_concurrency": 5}}))
    assert written.status_code == 409, written.text
    applied = await bounded(client.post("/admin/settings/apply", json={}))
    assert applied.status_code == 409, applied.text
    assert state.settings is previous_settings
    assert read_config(config_path(state.settings.data_dir)) == previous_config
    assert state.provider is provider and not provider.closed


async def assert_settings_work_after_wait(client, state, provider):
    written = await bounded(client.put("/admin/settings", json={"values": {"enrich_concurrency": 5}}))
    assert written.status_code == 200, written.text
    assert state.settings.enrich_concurrency == 5
    assert read_config(config_path(state.settings.data_dir))["enrich_concurrency"] == 5
    assert provider.closed
    applied = await bounded(client.post("/admin/settings/apply", json={}))
    assert applied.status_code == 200 and applied.json()["applied"], applied.text


def patch_network(monkeypatch, operation, state, bid):
    captures = []

    async def wait_for_remote(conn, *args, provider, settings, **kwargs):
        captures.append((conn, provider, settings))
        assert conn is not state.conn and provider is state.provider
        assert settings is not state.settings
        assert settings.chat_extra_body == state.settings.chat_extra_body
        assert not state.lock.locked()
        # Karakeep may save metadata before its embedding request. That write
        # must be committed before a local /open arrives during the wait.
        if operation == "karakeep-add":
            assert conn.isolation_level is None
            conn.execute("UPDATE bookmark SET title=title WHERE id=?", (bid,))
        else:
            conn.execute("SELECT id FROM bookmark WHERE id=?", (bid,)).fetchall()
        await provider.embed(["synthetic remote wait"])
        result = {"hits": [], "expanded": [], "claims": [], "sources": [], "gaps": []}
        return result if operation.startswith("karakeep-") else SimpleNamespace(as_dict=lambda: result)

    if operation == "search":
        monkeypatch.setattr(service, "search", wait_for_remote)
    elif operation == "synthesize":
        monkeypatch.setattr(service, "synthesize", wait_for_remote)
    elif operation == "karakeep-add":
        monkeypatch.setattr(api.kkbridge, "add_documents", wait_for_remote)
    else:
        monkeypatch.setattr(api.kkbridge, "search_documents", wait_for_remote)
    return captures


def start_http(client, operation):
    requests = {
        "search": ("/search", {"q": "synthetic recovery", "config": "A"}),
        "synthesize": ("/synthesize", {"q": "synthetic recovery"}),
        "karakeep-add": ("/karakeep/documents", {"documents": [{"id": "synthetic-document"}], "embed": True}),
        "karakeep-search": ("/karakeep/search", {"query": "synthetic recovery", "config": "A"}),
    }
    path, body = requests[operation]
    return asyncio.create_task(client.post(path, json=body))


def assert_connection_released(state, captures):
    assert state.model_users == 0 and not state.lock.locked()
    assert state.conn.execute("SELECT 1").fetchone()[0] == 1
    assert len(captures) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        captures[0][0].execute("SELECT 1")


@pytest.mark.parametrize("operation", ["search", "synthesize", "karakeep-add", "karakeep-search"])
@pytest.mark.parametrize("outcome", ["success", "failure", "cancel"])
async def test_http_remote_wait_uses_lease_and_releases_it_after_every_outcome(tmp_path, monkeypatch, operation, outcome):
    async with local_client(tmp_path, monkeypatch) as (client, state, provider):
        bid = seed(state)
        captures = patch_network(monkeypatch, operation, state, bid)
        if outcome == "failure":
            provider.failure = RuntimeError("synthetic remote failure")
        pending = start_http(client, operation)
        try:
            await bounded(provider.entered.wait())
            assert state.model_users == 1
            await assert_local_controls_respond(client, bid)
            await assert_settings_rejected_while_waiting(client, state, provider)
            assert not pending.done()
            if outcome == "cancel":
                pending.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await bounded(pending)
            else:
                provider.release.set()
                if outcome == "failure":
                    with pytest.raises(RuntimeError, match="synthetic remote failure"):
                        await bounded(pending)
                else:
                    response = await bounded(pending)
                    assert response.status_code == 200, response.text
            assert_connection_released(state, captures)
            assert not provider.closed
            await assert_settings_work_after_wait(client, state, provider)
        finally:
            await dispose(pending, provider.release)


@pytest.mark.parametrize("tool,operation", [("search_bookmarks", "search"), ("synthesize", "synthesize")])
@pytest.mark.parametrize("outcome", ["success", "failure", "cancel"])
async def test_shared_mcp_remote_tools_use_same_leases_and_leave_local_controls_responsive(tmp_path, monkeypatch, tool, operation, outcome):
    async with local_client(tmp_path, monkeypatch) as (client, state, provider):
        bid = seed(state)
        captures = patch_network(monkeypatch, operation, state, bid)
        server = create_server(context=Ctx(None, None, state_getter=lambda: state))
        if outcome == "failure":
            provider.failure = RuntimeError("synthetic remote failure")
        pending = asyncio.create_task(server.call_tool(tool, {"query": "synthetic recovery"}))
        try:
            await bounded(provider.entered.wait())
            assert state.model_users == 1
            await assert_local_controls_respond(client, bid)
            await assert_settings_rejected_while_waiting(client, state, provider)
            if outcome == "cancel":
                pending.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await bounded(pending)
            else:
                provider.release.set()
                if outcome == "failure":
                    with pytest.raises(Exception, match="synthetic remote failure"):
                        await bounded(pending)
                else:
                    await bounded(pending)
            assert_connection_released(state, captures)
            await server.facetmark_ctx.aclose()
            assert state.conn.execute("SELECT 1").fetchone()[0] == 1 and not provider.closed
            await assert_settings_work_after_wait(client, state, provider)
        finally:
            await dispose(pending, provider.release)
            await server.facetmark_ctx.aclose()


async def test_model_leases_have_independent_connections_and_settings_snapshots(tmp_path, monkeypatch):
    async with local_client(tmp_path, monkeypatch) as (_, state, provider):
        saved_extra = state.settings.chat_extra_body
        saved_concurrency = state.settings.enrich_concurrency
        async with state.model_operation() as (first, first_provider, first_settings):
            assert state.model_users == 1
            first_settings.chat_extra_body = json.dumps({"metadata": {"values": ["lease-only"]}})
            first_settings.enrich_concurrency = 7
            assert state.settings.chat_extra_body == saved_extra
            assert state.settings.enrich_concurrency == saved_concurrency
            async with state.model_operation(writing=True) as (second, second_provider, second_settings):
                assert state.model_users == 2
                assert first is not second and second is not state.conn
                assert first_provider is second_provider is provider
                assert second_settings.chat_extra_body == saved_extra
                assert second_settings.enrich_concurrency == saved_concurrency
                assert first_settings is not second_settings
                assert second.isolation_level is None and not state.lock.locked()
            assert state.model_users == 1
            with pytest.raises(sqlite3.ProgrammingError, match="closed"):
                second.execute("SELECT 1")
            assert first.execute("SELECT 1").fetchone()[0] == 1
        assert state.model_users == 0
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            first.execute("SELECT 1")


async def test_connection_open_failure_releases_model_lease_counter_without_closing_root(tmp_path, monkeypatch):
    async with local_client(tmp_path, monkeypatch) as (_, state, provider):
        def fail_to_open(*args, **kwargs):
            raise sqlite3.OperationalError("synthetic independent connection failure")

        monkeypatch.setattr(api, "open_db", fail_to_open)
        with pytest.raises(sqlite3.OperationalError, match="synthetic independent connection failure"):
            async with state.model_operation():
                pytest.fail("a failed connection cannot yield a lease")
        assert state.model_users == 0 and not state.lock.locked()
        assert state.conn.execute("SELECT 1").fetchone()[0] == 1 and not provider.closed


async def test_chat_stop_responds_during_an_independent_slow_search_and_apply_rejects_active_reply(tmp_path, monkeypatch):
    async with local_client(tmp_path, monkeypatch) as (client, state, provider):
        bid = seed(state)
        created = await bounded(client.post("/chat/conversations", json={"bookmark_ids": [bid]}))
        assert created.status_code == 200, created.text
        path = f"/chat/conversations/{created.json()['id']}"
        reply = asyncio.create_task(client.post(path + "/messages", json={
            "text": "How do I recover the saved evidence?", "language": "en", "request_id": "stop-this-reply"}))
        search = None
        try:
            await bounded(provider.chat_entered.wait())
            assert state.model_users == 0 and any(not task.done() for task in state.chat_runs.values())
            await assert_settings_rejected_while_waiting(client, state, provider)
            captures = patch_network(monkeypatch, "search", state, bid)
            search = start_http(client, "search")
            await bounded(provider.entered.wait())
            await assert_local_controls_respond(client, bid)
            stopped = await bounded(client.post(path + "/cancel", json={"request_id": "stop-this-reply"}))
            assert stopped.status_code == 200 and stopped.json()["cancelled"], stopped.text
            settled = await bounded(reply)
            assert settled.status_code == 200 and settled.json()["messages"][-1]["status"] == "cancelled"
            assert not search.done() and state.model_users == 1
            assert not provider.release.is_set()
            provider.release.set()
            assert (await bounded(search)).status_code == 200
            assert_connection_released(state, captures)
            await assert_settings_work_after_wait(client, state, provider)
        finally:
            await dispose(reply, provider.chat_release)
            if search is not None:
                await dispose(search, provider.release)


def patch_health_probe(monkeypatch, *, failure=False, recovered=False):
    entered, release = asyncio.Event(), asyncio.Event()
    observed = []

    async def probe_many(targets, **kwargs):
        observed.extend(targets)
        entered.set()
        await release.wait()
        if failure:
            raise RuntimeError("synthetic link probe failure")
        return [LocalProbe(target["url"], LocalVerdict.ALIVE, http_status=200, final_url=target["url"])
            for target in targets]

    def recovered_check(probe, external, *, now_ts):
        return HealthCheck(url=probe.url, status=Status.ALIVE, confidence=0.8, checked_at=now_ts,
            http_status=200, local=probe, recovered_body="OLDER_RECOVERED_BODY", recovered_title="Older recovered title")

    monkeypatch.setattr(health, "probe_many", probe_many)
    if recovered:
        monkeypatch.setattr(health, "synthesize", recovered_check)
    return entered, release, observed


@pytest.mark.parametrize("transport", ["http", "mcp"])
@pytest.mark.parametrize("outcome", ["success", "failure", "cancel"])
async def test_health_wait_shares_state_across_transports_and_releases_it_after_every_outcome(tmp_path, monkeypatch, transport, outcome):
    async with local_client(tmp_path, monkeypatch) as (client, state, provider):
        bid = seed(state)
        entered, release, _ = patch_health_probe(monkeypatch, failure=outcome == "failure")
        server = create_server(context=Ctx(None, None, state_getter=lambda: state))
        pending = asyncio.create_task(client.post("/link-health/check", json={"ids": [bid]})) if transport == "http" else (
            asyncio.create_task(server.call_tool("check_link_health", {"bookmark_ids": [bid], "probe": True})))
        try:
            await bounded(entered.wait())
            assert state.health_running and state.model_users == 0 and not state.lock.locked()
            await assert_local_controls_respond(client, bid)
            await assert_settings_rejected_while_waiting(client, state, provider)
            duplicate = await bounded(client.post("/link-health/check", json={"ids": [bid]}))
            assert duplicate.status_code == 409, duplicate.text
            if outcome == "cancel":
                pending.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await bounded(pending)
            else:
                release.set()
                if outcome == "failure":
                    with pytest.raises(Exception, match="synthetic link probe failure"):
                        await bounded(pending)
                else:
                    result = await bounded(pending)
                    if transport == "http":
                        assert result.status_code == 200 and result.json()["probed"] == 1, result.text
            assert not state.health_running and not state.lock.locked()
            assert state.conn.execute("SELECT count(*) FROM health").fetchone()[0] == int(outcome == "success")
            assert state.conn.execute("SELECT 1").fetchone()[0] == 1
            await assert_settings_work_after_wait(client, state, provider)
        finally:
            await dispose(pending, release)
            await server.facetmark_ctx.aclose()


@pytest.mark.parametrize("change", ["none", "delete", "url", "newer-body"])
async def test_health_persistence_rechecks_deleted_changed_and_newly_saved_pages(tmp_path, monkeypatch, change):
    async with local_client(tmp_path, monkeypatch) as (client, state, _):
        bid = seed(state, body=None)
        entered, release, observed = patch_health_probe(monkeypatch, recovered=True)
        pending = asyncio.create_task(client.post("/link-health/check", json={"ids": [bid]}))
        try:
            await bounded(entered.wait())
            assert observed[0]["url"] == "https://responsive.test/saved-page" and observed[0]["known_chars"] == 0
            if change == "delete":
                changed = await bounded(client.delete(f"/admin/library/bookmarks/{bid}"))
                assert changed.status_code == 200, changed.text
            elif change == "url":
                changed = await bounded(client.patch(f"/admin/library/bookmarks/{bid}", json={"url": "https://new.test/replaced"}))
                assert changed.status_code == 200, changed.text
            elif change == "newer-body":
                await bounded(state.lock.acquire())
                try:
                    fetchstore.store_body(state.conn, bid, body="NEWER_LOCAL_BODY", extractor="newer-local", channel="extension")
                    state.conn.commit()
                finally:
                    state.lock.release()
            release.set()
            checked = await bounded(pending)
            assert checked.status_code == 200 and checked.json()["probed"] == 1, checked.text
            assert checked.json()["recovered_bodies"] == int(change == "none")
            assert not state.health_running
            content = state.conn.execute("SELECT body_text,extractor,fetch_channel FROM content WHERE bookmark_id=?", (bid,)).fetchone()
            if change in {"delete", "url"}:
                assert content is None
                assert state.conn.execute("SELECT count(*) FROM health WHERE bookmark_id=?", (bid,)).fetchone()[0] == 0
                bookmark = state.conn.execute("SELECT url FROM bookmark WHERE id=?", (bid,)).fetchone()
                if change == "delete":
                    assert bookmark is None
                else:
                    assert bookmark["url"] == "https://new.test/replaced"
            else:
                assert state.conn.execute("SELECT count(*) FROM health WHERE bookmark_id=?", (bid,)).fetchone()[0] == 1
                expected = ("OLDER_RECOVERED_BODY", "reader-proxy", "reader") if change == "none" else (
                    "NEWER_LOCAL_BODY", "newer-local", "extension")
                assert tuple(content) == expected
        finally:
            await dispose(pending, release)
