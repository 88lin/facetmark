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
from facetmark.enrich.prompts import resolve_summary_language, summary_prompt_hash
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
                         model="old-chat", language=resolve_summary_language(state.settings.summary_language),
                         prompt_hash=summary_prompt_hash(resolve_summary_language(state.settings.summary_language),
                                                         state.settings.summary_prompt))
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


def configure_chat(client, monkeypatch, *, fail=False, payload=None):
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
            if fail and (fail is True or fail in user):
                raise ProviderError("failure synthetic-secret")
            if payload is not None:
                return payload
            return {"title": "Generated reading title", "summary": "A fresh reading summary.", "topics": ["reading"],
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
    assert job["items"] == {"done": 1, "total": 1, "failed": 0}
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
    assert job["items"] == {"done": 1, "total": 1, "failed": 0}
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


def test_generated_title_is_separate_searchable_and_exported_with_its_language(client, monkeypatch):
    bid = save(client, "Original English title", body="Saved source text.")
    instances = configure_chat(client, monkeypatch)
    preview = client.post("/admin/jobs/preview", json={"mode": "summarize", "summary_language": "zh"}).json()
    started = client.post("/admin/jobs/start", json={
        "mode": "summarize", "summary_language": "zh", "confirmed": True,
        "preview_revision": preview["revision"], "preview_prompt_hash": preview["prompt_hash"],
    })
    assert started.status_code == 200, started.text
    assert wait_job(client)["state"] == "done"
    assert "OUTPUT_LANGUAGE: zh" in instances[0].prompts[0]
    record = client.get(f"/bookmark/{bid}?body=true").json()
    assert record["title"] == "Original English title"
    assert record["ai_title"] == "Generated reading title"
    assert record["summary_language"] == "zh"
    assert record["body_text"] == "Saved source text."
    hits = client.get("/quick?q=Generated").json()["hits"]
    assert hits[0]["bookmark_id"] == bid and hits[0]["ai_title"] == record["ai_title"]
    listed = client.get("/bookmarks?sort=title").json()["items"][0]
    assert listed["ai_title"] == record["ai_title"] and listed["title"] == record["title"]
    exported = service.export_reading_data(client.app.state.fm.conn, [bid])[bid]["derived"]
    assert exported["ai_title"] == record["ai_title"]
    assert exported["summary_language"] == "zh"
    assert exported["prompt_hash"] == preview["prompt_hash"]


def test_saved_language_and_custom_prompt_invalidate_completed_summaries_without_retesting_chat(client, monkeypatch):
    bid = save(client, "cached language", body="English source", enriched=True)
    instances = configure_chat(client, monkeypatch)
    original = client.post("/admin/jobs/preview", json={"mode": "summarize"}).json()
    assert original["total"] == 0
    custom = "Focus on practical steps. Keep {literal braces} and examples concise."
    saved = client.put("/admin/settings", json={"values": {"summary_language": "en", "summary_prompt": custom}})
    assert saved.status_code == 200, saved.text
    assert client.get("/admin/setup-status").json()["channels"]["chat"]["tested"]
    assert client.get("/admin/setup-status").json()["summary_language"] == "en"
    preview = client.post("/admin/jobs/preview", json={"mode": "summarize"}).json()
    assert preview["total"] == 1 and preview["prompt_hash"] != original["prompt_hash"]
    started = client.post("/admin/jobs/start", json={
        "mode": "summarize", "confirmed": True, "preview_revision": preview["revision"],
        "preview_prompt_hash": preview["prompt_hash"],
    })
    assert started.status_code == 200, started.text
    finished = wait_job(client)
    assert finished["state"] == "done" and finished["params"]["summary_language"] == "en"
    assert finished["params"]["summary_prompt"] == custom
    assert custom in instances[0].prompts[0] and "OUTPUT_LANGUAGE: en" in instances[0].prompts[0]
    assert client.post("/admin/jobs/preview", json={"mode": "summarize"}).json()["total"] == 0
    assert client.get(f"/bookmark/{bid}").json()["summary_language"] == "en"
    assert client.put("/admin/settings", json={"values": {"summary_prompt": ""}}).status_code == 200
    reset = client.post("/admin/jobs/preview", json={"mode": "summarize"}).json()
    assert reset["total"] == 1 and reset["prompt_hash"] != preview["prompt_hash"]
    stale = client.post("/admin/jobs/start", json={
        "mode": "summarize", "confirmed": True, "preview_prompt_hash": preview["prompt_hash"],
    })
    assert stale.status_code == 409 and "Summary settings changed" in stale.text
    assert len(instances) == 1


def test_resume_keeps_original_language_and_prompt_after_preferences_change(client, monkeypatch):
    save(client, "retry same prompt")
    save(client, "completed same prompt")
    configure_chat(client, monkeypatch, fail="retry same prompt")
    started = client.post("/admin/jobs/start", json={
        "mode": "summarize", "confirmed": True, "summary_language": "en",
        "summary_prompt": "Original task writing instructions.",
    })
    assert started.status_code == 200
    previous = wait_job(client)
    assert previous["state"] == "partial"
    save(client, "added after original task")
    assert client.put("/admin/settings", json={"values": {
        "summary_language": "zh", "summary_prompt": "New task writing instructions.",
    }}).status_code == 200
    instances = configure_chat(client, monkeypatch)
    response = client.post("/admin/jobs/resume", json={"resume_id": previous["id"], "confirmed": True})
    assert response.status_code == 200, response.text
    assert wait_job(client)["state"] == "done"
    assert len(instances[0].prompts) == 1
    prompt = instances[0].prompts[0]
    assert "retry same prompt" in prompt and "OUTPUT_LANGUAGE: en" in prompt
    assert "Original task writing instructions." in prompt and "New task writing instructions." not in prompt


@pytest.mark.parametrize("payload", [{"summary_language": "zh-CN"}, {"summary_prompt": "x" * 10001}])
def test_summary_preferences_reject_invalid_saved_values(client, payload):
    assert client.put("/admin/settings", json={"values": payload}).status_code == 400


def test_builtin_prompt_remains_available_and_custom_instructions_do_not_replace_output_contract(client):
    from facetmark.enrich.prompts import build_user_prompt

    defaults = client.get("/admin/settings").json()["summary_prompt_defaults"]
    assert "中文标题" in defaults["zh"] and "title" in defaults["en"]
    prompt = build_user_prompt(title="Original title", url="https://reading.test/prompt", folder="",
                               body="Original source", n_queries=8, language="zh",
                               custom_prompt="Prefer numbered practical takeaways.")
    assert "Prefer numbered practical takeaways." in prompt
    assert '"title"' in prompt and '"intent_queries"' in prompt
    assert "Required target language: 简体中文" in prompt
    assert prompt.endswith("<<<PAGE>>>\nOriginal source")


@pytest.mark.parametrize("payload", [
    {"summary": "Incomplete replacement", "intent_queries": ["replacement query"]},
    {"title": "Incomplete replacement", "intent_queries": ["replacement query"]},
])
def test_incomplete_model_reply_keeps_previous_title_summary_queries_and_search_index(client, monkeypatch, payload):
    bid = save(client, "original saved title", body="Saved source text", enriched=True)
    state = client.app.state.fm
    state.conn.execute("UPDATE enrichment SET ai_title='previous generated title' WHERE bookmark_id=?", (bid,))
    service.sync_fts_tag_refresh(state.conn, bid)
    state.conn.commit()
    previous = dict(state.conn.execute("SELECT * FROM enrichment WHERE bookmark_id=?", (bid,)).fetchone())
    queries = [tuple(row) for row in state.conn.execute("SELECT * FROM intent_query WHERE bookmark_id=?", (bid,))]
    instances = configure_chat(client, monkeypatch, payload=payload)
    response = client.post("/admin/jobs/start", json={
        "mode": "summarize", "bookmark_ids": [bid], "force": True, "confirmed": True,
    })
    assert response.status_code == 200, response.text
    job = wait_job(client)
    assert job["state"] == "partial" and job["items"] == {"done": 1, "total": 1, "failed": 1}
    assert dict(state.conn.execute("SELECT * FROM enrichment WHERE bookmark_id=?", (bid,)).fetchone()) == previous
    assert [tuple(row) for row in state.conn.execute("SELECT * FROM intent_query WHERE bookmark_id=?", (bid,))] == queries
    record = client.get(f"/bookmark/{bid}?body=true").json()
    assert record["ai_title"] == previous["ai_title"] and record["summary"] == previous["summary"]
    assert record["title"] == "original saved title" and record["body_text"] == "Saved source text"
    assert "generated title and summary" in record["summary_error"]
    assert client.get("/quick?q=previous").json()["hits"][0]["bookmark_id"] == bid
    assert len(instances[0].prompts) == 2  # one shorter-body retry; neither reply overwrites saved data


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
def test_partial_task_retries_original_snapshot_without_new_library_items(client, monkeypatch, mode):
    failed = save(client, "retry-original")
    save(client, "already-succeeded")
    if mode == "fetch":
        fake_fetch(monkeypatch, failures=("https://reading.test/retry-original",))
    else:
        configure_chat(client, monkeypatch, fail="retry-original")
    response = client.post("/admin/jobs/start", json={"mode": mode, "scope": {}, "confirmed": True})
    assert response.status_code == 200
    previous = wait_job(client)
    assert previous["state"] == "partial" and previous["resumable"]
    added = save(client, "added-after-failure")
    if mode == "fetch":
        contacted = fake_fetch(monkeypatch)
    else:
        instances = configure_chat(client, monkeypatch)
    resumed = client.post("/admin/jobs/resume", json={"resume_id": previous["id"], "confirmed": True})
    assert resumed.status_code == 200, resumed.text
    final = wait_job(client)
    assert final["id"] == previous["id"]
    assert final["state"] == "done" and final["items"] == {"done": 2, "total": 2, "failed": 0}
    if mode == "fetch":
        assert contacted == ["https://reading.test/retry-original"]
    else:
        assert len(instances[0].prompts) == 1
        assert "retry-original" in instances[0].prompts[0]
    table = "content" if mode == "fetch" else "enrichment"
    conn = client.app.state.fm.conn
    assert conn.execute(f"SELECT bookmark_id FROM {table} WHERE bookmark_id IN (?,?)", (failed, added)).fetchall()[0][0] == failed
    assert conn.execute("SELECT count(*) FROM processing_item WHERE job_id=?", (previous["id"],)).fetchone()[0] == 0


def test_discovered_model_is_tested_saved_and_used_by_actual_summary_job(client, monkeypatch):
    from facetmark import local_agents, model_catalog

    calls = []
    monkeypatch.setattr(local_agents, "selected_agent", lambda preference: "opencode")
    monkeypatch.setattr(local_agents, "resolve_command", lambda agent: ["synthetic-agent"])

    async def catalog(preference):
        return {"agent": "opencode", "models": [{"id": "fixture/chosen", "label": "Chosen", "source": "cli"}],
                "default_model": "fixture/default", "warning": ""}

    class Agent(Provider):
        name = "synthetic-agent"

        def __init__(self, settings):
            super().__init__(settings)
            self.chat_model_in_use = settings.chat_agent_model

        async def chat_json(self, system, user):
            calls.append((self.chat_model_in_use, user))
            return {"ok": True, "title": "Selected model title", "summary": "Summary from the selected model", "topics": [], "intent_queries": ["selected model"]}

        async def embed(self, texts):
            raise AssertionError("Summary generation must not require embeddings")

    monkeypatch.setattr(model_catalog, "agent_catalog", catalog)
    monkeypatch.setattr(local_agents, "LocalAgentProvider", Agent)
    draft = {"chat_backend": "agent", "chat_agent": "opencode"}
    choices = client.post("/admin/settings/models", json={"channel": "chat", **draft}).json()
    draft["chat_agent_model"] = choices["models"][0]["id"]
    probe = client.post("/admin/settings/test", json={"channel": "chat", **draft})
    assert probe.json()["chat"]["ok"], probe.text
    assert client.put("/admin/settings", json={"values": draft}).status_code == 200
    bid = save(client, "summary-workflow", body="Saved text to summarize")
    started = client.post("/admin/jobs/start", json={"mode": "summarize", "bookmark_ids": [bid], "confirmed": True})
    assert started.status_code == 200, started.text
    assert wait_job(client)["state"] == "done"
    assert len(calls) == 2 and all(model == "fixture/chosen" for model, _ in calls)
    assert "summary-workflow" in calls[-1][1]
    assert client.app.state.fm.conn.execute("SELECT summary FROM enrichment WHERE bookmark_id=?", (bid,)).fetchone()[0] == "Summary from the selected model"


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
    assert wait_job(client)["items"] == {"done": 1, "total": 1, "failed": 0}
    if mode == "fetch":
        assert contacted == ["https://reading.test/first"]
    else:
        assert len(instances[0].prompts) == 1
        assert "https://reading.test/first" in instances[0].prompts[0]


@pytest.mark.parametrize("ids", [[], [0], [-1], [True], [2**64], [1, 1], list(range(1, 10002))])
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
    save(client, "cancellation target")
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
    from facetmark.db import open_db
    conn = open_db(settings.db_path)
    service.save_bookmark(conn, "https://fetch.test/pending", settings=settings)
    conn.close()
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


def test_scoped_summary_preview_and_execution_skip_exclusions_and_private_rows(client, monkeypatch):
    first = save(client, "chosen first")
    excluded = save(client, "chosen excluded")
    save(client, "outside")
    save(client, "chosen private", url="https://private.test/excluded")
    instances = configure_chat(client, monkeypatch)
    scope = {"q": "chosen", "exclude_ids": [excluded]}
    preview = client.post("/admin/jobs/preview", json={"mode": "summarize", "scope": scope}).json()
    assert preview["total"] == 1
    response = client.post("/admin/jobs/start", json={"mode": "summarize", "scope": scope,
        "confirmed": True, "preview_revision": preview["revision"]})
    assert response.status_code == 200, response.text
    assert wait_job(client)["items"] == {"done": 1, "total": 1, "failed": 0}
    assert len(instances[0].prompts) == 1 and "chosen first" in instances[0].prompts[0]
    data = client.get("/bookmarks", params={"q": "chosen", "status": "done"}).json()
    assert [row["bookmark_id"] for row in data["items"]] == [first]
    assert data["items"][0]["summary"] == "A fresh reading summary."
    assert data["items"][0]["summary_basis"] == "title"


def test_preview_rejects_changed_library_and_title_only_changes_are_eligible(client, monkeypatch):
    bid = save(client, "before", enriched=True)
    configure_chat(client, monkeypatch)
    state = client.app.state.fm
    assert client.post("/admin/jobs/preview", json={"mode": "summarize"}).json()["total"] == 0
    state.conn.execute("UPDATE bookmark SET title='after' WHERE id=?", (bid,))
    preview = client.post("/admin/jobs/preview", json={"mode": "summarize"}).json()
    assert preview["total"] == 1
    save(client, "added after preview")
    response = client.post("/admin/jobs/start", json={"mode": "summarize", "confirmed": True,
        "preview_revision": preview["revision"]})
    assert response.status_code == 409
    assert client.get("/admin/job").json()["state"] == "idle"


def test_failure_filter_retry_does_not_reprocess_success(client, monkeypatch):
    failed = save(client, "will fail", enriched=True)
    save(client, "successful", enriched=True)
    configure_chat(client, monkeypatch, fail=True)
    client.post("/admin/jobs/start", json={"mode": "summarize", "bookmark_ids": [failed], "force": True, "confirmed": True})
    assert wait_job(client)["state"] == "partial"
    data = client.get("/bookmarks?status=failed").json()
    assert data["total"] == 1 and "synthetic-secret" not in json.dumps(data)
    assert client.get("/bookmarks?status=done").json()["total"] == 1
    instances = configure_chat(client, monkeypatch)
    client.post("/admin/jobs/start", json={"mode": "summarize", "scope": {"status": "failed"}, "confirmed": True})
    assert wait_job(client)["state"] == "done"
    assert len(instances[0].prompts) == 1
    assert client.get("/bookmarks?status=failed").json()["total"] == 0


async def test_pause_drains_inflight_work_and_restart_resumes_original_snapshot(tmp_path, monkeypatch):
    from facetmark.db import open_db
    settings = Settings(data_dir=tmp_path, use_mock_provider=True, enrich_concurrency=2)
    conn = open_db(settings.db_path)
    ids = [service.save_bookmark(conn, f"https://resume.test/{i}", title=f"item {i}", settings=settings)["bookmark_id"] for i in range(6)]
    conn.close()
    runner = admin.JobRunner(tmp_path)
    calls = []
    class Chat(Provider):
        async def embed(self, texts):
            raise AssertionError("No embeddings")
        async def chat_json(self, system, user):
            calls.append(user)
            runner.pause()
            await asyncio.sleep(0.01)
            return {"title": "Saved title", "summary": "saved summary"}
    monkeypatch.setattr(admin, "get_chat_provider", lambda s: Chat(s))
    job = runner.start(settings, fetch=False, limit=None, force=True, mode="summarize", bookmark_ids=ids)
    await runner._task
    assert job.state == "paused" and not job.pause_requested
    assert job.items_done == 2 and len(calls) == 2
    conn = open_db(settings.db_path)
    conn.execute("DELETE FROM bookmark WHERE id=?", (ids[-1],))
    conn.close()
    restarted = admin.JobRunner(tmp_path)
    saved = restarted.saved(job.id)
    assert saved["resumable"]
    # A different task must not erase this resume handle.
    other = restarted.start(settings, fetch=False, limit=None, force=False, mode="summarize", bookmark_ids=[ids[0]])
    await restarted._task
    assert other.state == "done" and restarted.saved(job.id)["resumable"]
    resumed = restarted.start(settings, fetch=False, limit=None, force=True, mode="summarize",
        bookmark_ids=ids, resume_id=job.id, snapshot_ready=True)
    await restarted._task
    assert resumed.state == "done" and resumed.items_done == 5
    assert len(calls) == 5  # two committed + three pending; no repeat or deleted item


async def test_summary_and_progress_rollback_together_on_callback_failure(tmp_path):
    from facetmark.db import open_db
    from facetmark.enrich import enrich_all
    from facetmark.providers import MockProvider
    settings = Settings(data_dir=tmp_path, use_mock_provider=True)
    conn = open_db(settings.db_path)
    bid = service.save_bookmark(conn, "https://atomic.test/page", title="atomic", settings=settings)["bookmark_id"]
    def failed_callback(target, enrichment, error):
        assert conn.execute("SELECT summary FROM enrichment WHERE bookmark_id=?", (bid,)).fetchone()
        raise RuntimeError("injected after summary before progress commit")
    with pytest.raises(RuntimeError, match="injected"):
        await enrich_all(conn, settings=settings, provider=MockProvider(settings), ids=[bid], progress=failed_callback)
    assert conn.execute("SELECT count(*) FROM enrichment").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM intent_query").fetchone()[0] == 0
    conn.close()
