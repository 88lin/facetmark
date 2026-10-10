"""Standalone reading jobs use synthetic records and stub every external call."""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

from facetmark import admin, service
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.db import ensure_vec_tables, upsert_content_vector, upsert_intent_vector
from facetmark.enrich import Enrichment, store_enrichment, targets
from facetmark.fetch import store as fetchstore
from facetmark.fetch.client import BatchResult, FetchResult, Verdict
from facetmark.providers import Provider, ProviderError


@pytest.fixture()
def client(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path / "reading", embed_dim=8,
                        privacy_excluded_domains=("private.test",),
                        health_enable_external=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("A reading job must not construct a combined provider")

    monkeypatch.setattr(admin, "get_provider", forbidden)
    with TestClient(create_app(settings), client=("127.0.0.1", 40001)) as test:
        test.headers["Authorization"] = f"Bearer {test.app.state.fm.token}"
        yield test


def save(client, name, *, url=None, body=None, enriched=False):
    state = client.app.state.fm
    bid = service.save_bookmark(
        state.conn, url or f"https://reading.test/{name}", title=name, tags=["personaltag"],
        settings=state.settings,
    )["bookmark_id"]
    if body is not None:
        fetchstore.store_body(state.conn, bid, body=body)
    if enriched:
        target = targets(state.conn, ids=[bid], force=True)[0]
        store_enrichment(state.conn, target,
                         Enrichment(summary=f"oldsummary {name}", intent_queries=[f"oldquery {name}"]),
                         model="old-chat")
    service.sync_fts_tag_refresh(state.conn, bid)
    state.conn.commit()
    return bid


def vectors(client, bids):
    conn = client.app.state.fm.conn
    ensure_vec_tables(conn, 8, "old-embedding")
    for bid in bids:
        upsert_content_vector(conn, bid, [0.1] * 8, text_hash="old-fingerprint")
        for row in conn.execute("SELECT id FROM intent_query WHERE bookmark_id=?", (bid,)):
            upsert_intent_vector(conn, row["id"], [0.1] * 8)
    if len(bids) > 1:
        conn.execute("INSERT INTO edge(src,dst,kind,weight) VALUES(?,?,'semantic',0.4)", bids[:2])
    conn.commit()


def fake_fetch(monkeypatch, *, bodies=None, failures=()):
    contacted = []

    async def fetch_many(urls, *, on_result, **kwargs):
        results = []
        for url in urls:
            contacted.append(url)
            result = FetchResult(
                url=url, verdict=Verdict.REFUSED if url in failures else Verdict.OK,
                body=(bodies or {}).get(url, "Fresh synthetic body with searchable text."),
                http_status=403 if url in failures else 200, extractor="test",
            )
            on_result(result)
            results.append(result)
        return BatchResult(results)

    monkeypatch.setattr(fetchstore, "fetch_many", fetch_many)
    return contacted


def wait_job(client):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = client.get("/admin/job").json()
        if job["state"] != "running":
            return job
        time.sleep(0.01)
    raise AssertionError(f"Reading job did not settle: {job}")


def configure_chat(client, monkeypatch, *, fail=False):
    state = client.app.state.fm
    state.settings = state.settings.model_copy(update={
        "chat_base_url": "https://chat.test/v1", "chat_api_key": "synthetic-secret",
        "embed_api_key": "", "embed_backend": "local", "local_embed_path": "",
    })
    state.probe_results["chat"] = {"fingerprint": admin.probe_fingerprint(state.settings, "chat")}
    instances = []

    class ChatOnly(Provider):
        name = "chat-only-test"

        def __init__(self, settings):
            super().__init__(settings)
            self.prompts = []
            self.closed = False
            instances.append(self)

        async def chat_json(self, system, user):
            self.prompts.append(user)
            if fail:
                raise ProviderError("failure synthetic-secret")
            return {"summary": "A fresh reading summary.", "topics": ["reading"],
                    "intent_queries": ["new reading question"]}

        async def embed(self, texts):
            raise AssertionError("Standalone summaries cannot call embeddings")

        async def aclose(self):
            self.closed = True

    monkeypatch.setattr(admin, "OpenAICompatibleProvider", ChatOnly)
    return instances


def test_fetch_needs_no_model_or_embedding_apply_and_respects_selection(client, monkeypatch):
    selected = save(client, "selected")
    cached = save(client, "cached", body="Cached page")
    private = save(client, "private", url="https://private.test/item")
    other = save(client, "other")
    contacted = fake_fetch(monkeypatch)
    state = client.app.state.fm
    state.pending_settings["embed_dim"] = 16
    started = client.post("/admin/jobs/start", json={
        "mode": "fetch", "bookmark_ids": [selected, cached, private],
    })
    assert started.status_code == 200, started.text
    job = wait_job(client)
    assert job["state"] == "done", job
    assert job["planned"] == job["done"] == ["fetch"]
    assert job["items"] == {"done": 1, "total": 1}
    assert job["params"]["mode"] == "fetch"
    assert job["params"]["bookmark_ids"] == [selected, cached, private]
    assert contacted == ["https://reading.test/selected"]
    assert not state.conn.execute("SELECT 1 FROM enrichment").fetchone()
    assert not state.conn.execute("SELECT 1 FROM content WHERE bookmark_id=?", (other,)).fetchone()
    assert client.get("/quick?q=personaltag").json()["total"] == 4


def test_refetch_retires_only_changed_data_and_keeps_failed_cached_content(client, monkeypatch):
    changed = save(client, "changed", body="Old body", enriched=True)
    same = save(client, "same", body="Unchanged body", enriched=True)
    failed = save(client, "failed", body="Keep this cached body", enriched=True)
    other = save(client, "other", body="Other body", enriched=True)
    vectors(client, [changed, same, failed, other])
    fake_fetch(monkeypatch, bodies={"https://reading.test/same": "Unchanged body"},
               failures={"https://reading.test/failed"})
    response = client.post("/admin/jobs/start", json={
        "mode": "fetch", "bookmark_ids": [changed, same, failed], "force": True,
    })
    assert response.status_code == 200
    job = wait_job(client)
    assert job["state"] == "partial", job
    assert job["stages"][0]["value"]["failed"] == 1
    conn = client.app.state.fm.conn
    assert not conn.execute("SELECT 1 FROM enrichment WHERE bookmark_id=?", (changed,)).fetchone()
    assert not conn.execute("SELECT 1 FROM intent_query WHERE bookmark_id=?", (changed,)).fetchone()
    assert {r[0] for r in conn.execute("SELECT bookmark_id FROM vec_content")} == {same, failed, other}
    assert not conn.execute("SELECT 1 FROM edge WHERE src=? OR dst=?", (changed, changed)).fetchone()
    assert conn.execute("SELECT body_text FROM content WHERE bookmark_id=?", (failed,)).fetchone()[0] == "Keep this cached body"
    assert {r[0] for r in conn.execute("SELECT bookmark_id FROM enrichment")} == {same, failed, other}
    assert client.get("/quick?q=oldsummary").json()["total"] == 3
    assert client.get("/quick?q=personaltag").json()["total"] == 4


def test_selected_summary_uses_chat_only_and_retires_stale_vectors(client, monkeypatch):
    selected = save(client, "selected", body="A cached article", enriched=True)
    other = save(client, "other", body="A separate article", enriched=True)
    private = save(client, "private", url="https://private.test/item")
    vectors(client, [selected, other])
    instances = configure_chat(client, monkeypatch)
    state = client.app.state.fm
    state.pending_settings["embed_dim"] = 16
    response = client.post("/admin/jobs/start", json={
        "mode": "summarize", "bookmark_ids": [selected, private], "confirmed": True, "force": True,
    })
    assert response.status_code == 200, response.text
    job = wait_job(client)
    assert job["state"] == "done", job
    assert job["planned"] == job["done"] == ["enrich"]
    assert job["params"]["fetch"] is False
    assert job["items"] == {"done": 1, "total": 1}
    assert len(instances) == 1 and len(instances[0].prompts) == 1
    assert instances[0].settings.base_url == "https://chat.test/v1"
    assert instances[0].settings.api_key == "synthetic-secret"
    assert instances[0].closed
    conn = state.conn
    assert {r[0] for r in conn.execute("SELECT bookmark_id FROM vec_content")} == {other}
    assert conn.execute("SELECT summary,basis FROM enrichment WHERE bookmark_id=?", (selected,)).fetchone()[:] == ("A fresh reading summary.", "body")
    assert conn.execute("SELECT summary FROM enrichment WHERE bookmark_id=?", (other,)).fetchone()[0] == "oldsummary other"
    assert conn.execute("SELECT text,kept FROM intent_query WHERE bookmark_id=?", (selected,)).fetchone()[:] == ("new reading question", 0)
    assert client.get("/quick?q=personaltag").json()["total"] == 3


def test_summary_requires_only_chat_test_and_consent(client, monkeypatch):
    bid = save(client, "title only")
    body = {"mode": "summarize", "bookmark_ids": [bid]}
    assert client.post("/admin/jobs/start", json={**body, "confirmed": True}).status_code == 409
    instances = configure_chat(client, monkeypatch)
    assert client.post("/admin/jobs/start", json=body).status_code == 400
    state = client.app.state.fm
    state.probe_results.clear()
    assert client.post("/admin/jobs/start", json={**body, "confirmed": True}).status_code == 409
    state.probe_results["chat"] = {"fingerprint": admin.probe_fingerprint(state.settings, "chat")}
    assert client.post("/admin/jobs/start", json={**body, "confirmed": True}).status_code == 200
    assert wait_job(client)["state"] == "done"
    assert len(instances[0].prompts) == 1
    assert state.conn.execute("SELECT basis FROM enrichment WHERE bookmark_id=?", (bid,)).fetchone()[0] == "title"


def test_chat_probe_does_not_construct_an_embedding_provider(client, monkeypatch):
    instances = configure_chat(client, monkeypatch)
    result = client.post("/admin/settings/test", json={"channel": "chat"})
    assert result.status_code == 200, result.text
    assert result.json()["ok"] is True, result.json()
    assert len(instances) == 1 and instances[0].closed


def test_summary_failure_is_partial_keeps_existing_summary_and_redacts_status(client, monkeypatch):
    bid = save(client, "failed", body="Saved page", enriched=True)
    vectors(client, [bid])
    instances = configure_chat(client, monkeypatch, fail=True)
    client.post("/admin/jobs/start", json={
        "mode": "summarize", "bookmark_ids": [bid], "force": True, "confirmed": True,
    })
    job = wait_job(client)
    assert job["state"] == "partial", job
    assert job["stages"][0]["value"]["failed"] == 1
    assert "synthetic-secret" not in json.dumps(job)
    assert instances[0].closed
    conn = client.app.state.fm.conn
    assert conn.execute("SELECT summary FROM enrichment WHERE bookmark_id=?", (bid,)).fetchone()[0] == "oldsummary failed"
    assert conn.execute("SELECT count(*) FROM vec_content").fetchone()[0] == 1


@pytest.mark.parametrize("mode", ["fetch", "summarize"])
def test_limit_applies_to_selected_pending_work_only(client, monkeypatch, mode):
    cached = save(client, "cached", body="Saved", enriched=True)
    first = save(client, "first")
    second = save(client, "second")
    contacted = fake_fetch(monkeypatch)
    instances = configure_chat(client, monkeypatch) if mode == "summarize" else []
    response = client.post("/admin/jobs/start", json={
        "mode": mode, "bookmark_ids": [second, cached, first], "limit": 1, "confirmed": True,
    })
    assert response.status_code == 200
    assert wait_job(client)["items"] == {"done": 1, "total": 1}
    if mode == "fetch":
        assert contacted == ["https://reading.test/first"]
    else:
        assert len(instances[0].prompts) == 1
        assert "https://reading.test/first" in instances[0].prompts[0]


@pytest.mark.parametrize("ids", [[], [0], [-1], [True], [2**64], [1, 1], list(range(1, 202))])
def test_invalid_selection_never_starts_a_job(client, ids):
    response = client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": ids})
    assert response.status_code == 422
    assert client.get("/admin/job").json()["state"] == "idle"


def test_missing_ids_and_selected_index_fail_before_work(client):
    bid = save(client, "exists")
    assert client.post("/admin/jobs/start", json={"mode": "fetch", "bookmark_ids": [bid, 9999]}).status_code == 404
    assert client.post("/admin/jobs/start", json={"mode": "index", "bookmark_ids": [bid]}).status_code == 400
    assert client.get("/admin/job").json()["state"] == "idle"


def test_new_route_requires_token(client):
    response = client.post("/admin/jobs/start", json={"mode": "fetch"}, headers={"Authorization": ""})
    assert response.status_code == 401


def test_fetch_cancellation_is_persisted_and_blocks_imports(client, monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(0.2)
        return fetchstore.CrawlReport()

    monkeypatch.setattr(fetchstore, "crawl", slow)
    assert client.post("/admin/jobs/start", json={"mode": "fetch"}).status_code == 200
    assert client.post("/admin/jobs/start", json={"mode": "fetch"}).status_code == 409
    raw = '<DL><DT><A HREF="https://reading.test/import">Synthetic</A></DL>'
    assert client.post("/admin/import", content=raw).status_code == 409
    assert client.post("/admin/job/cancel").json()["cancel_requested"] is True
    job = wait_job(client)
    assert job["state"] == "cancelled"
    saved = admin.JobRunner(client.app.state.fm.settings.data_dir).previous
    assert saved["state"] == "cancelled" and saved["params"]["mode"] == "fetch"


async def test_fetch_shutdown_persists_interrupted(tmp_path, monkeypatch):
    entered = asyncio.Event()

    async def slow(*args, **kwargs):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(fetchstore, "crawl", slow)
    settings = Settings(data_dir=tmp_path)
    runner = admin.JobRunner(tmp_path)
    runner.start(settings, mode="fetch", fetch=True, limit=None, force=False)
    await asyncio.wait_for(entered.wait(), 2)
    await runner.shutdown()
    assert admin.JobRunner(tmp_path).previous["state"] == "interrupted"


async def test_summary_shutdown_drains_model_tasks_before_closing_provider(tmp_path, monkeypatch):
    from facetmark.db import open_db

    settings = Settings(data_dir=tmp_path, use_mock_provider=True, enrich_concurrency=2)
    conn = open_db(settings.db_path)
    for i in range(2):
        service.save_bookmark(conn, f"https://reading.test/{i}", settings=settings)
    conn.close()
    entered = asyncio.Event()
    events = []

    class WaitingChat(Provider):
        async def embed(self, texts):
            raise AssertionError("Summary jobs never embed")

        async def chat_json(self, system, user):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                events.append("call ended")

        async def aclose(self):
            events.append("provider closed")

    monkeypatch.setattr(admin, "get_chat_provider", lambda settings: WaitingChat(settings))
    runner = admin.JobRunner(tmp_path)
    runner.start(settings, mode="summarize", fetch=False, limit=None, force=False)
    await asyncio.wait_for(entered.wait(), 2)
    await runner.shutdown()
    assert events == ["call ended", "call ended", "provider closed"]
    assert admin.JobRunner(tmp_path).previous["state"] == "interrupted"


def test_unfinished_snapshot_reloads_without_claiming_a_current_stage(tmp_path):
    (tmp_path / "last-index-job.json").write_text(json.dumps({
        "state": "running", "current": "fetch", "params": {"mode": "fetch"},
    }), encoding="utf-8")
    previous = admin.JobRunner(tmp_path).previous
    assert previous["state"] == "interrupted"
    assert previous["current"] is None
