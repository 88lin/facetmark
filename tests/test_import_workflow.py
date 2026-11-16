"""Import receipts and previews use isolated data and never fetch a page."""
from __future__ import annotations

import asyncio
import json
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from facetmark import crawl_jobs, import_workflow, library
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.crawl import CrawlReport
from facetmark.crawl_jobs import CrawlRequest, CrawlRunner
from facetmark.db import open_db


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "imports", use_mock_provider=True,
                    health_enable_external=False)


@pytest.fixture
def conn():
    database = open_db(":memory:")
    yield database
    database.close()


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), client=("127.0.0.1", 40404)) as value:
        value.headers["Authorization"] = "Bearer " + value.app.state.fm.token
        yield value


def draft(**values):
    return import_workflow.UrlDraft(text="https://one.example/page", **values)


def ready(conn, value=None):
    value = value or draft()
    candidate = import_workflow.preview(conn, value)
    return import_workflow.UrlApply(**value.model_dump(), revision=candidate["revision"],
                                    request_id=uuid.uuid4().hex)


def test_preview_classifies_tracking_duplicates_invalid_and_existing_without_mutation(conn, settings):
    saved = library.create_bookmark(conn, library.CreateBookmark(
        url="https://existing.example/page", title="Keep my title"), settings=settings)
    candidate = import_workflow.preview(conn, import_workflow.UrlDraft(text=(
        "https://one.example/page\tNew title\n"
        "https://one.example/page?utm_source=test\n"
        "https://existing.example/page\tDo not replace\n"
        "javascript:alert(1)\nhttps://user:password@one.example/private")))
    assert candidate["counts"] == {"new": 1, "existing": 1, "duplicate": 1, "invalid": 2}
    assert candidate["items"][2]["bookmark_id"] == saved["bookmark_id"]
    assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM import_run").fetchone()[0] == 0


def test_apply_keeps_existing_records_and_records_each_item_and_folder(conn, settings):
    library.create_bookmark(conn, library.CreateBookmark(
        url="https://existing.example/", title="Local title", folder="Original"), settings=settings)
    value = import_workflow.UrlDraft(text="https://new.example/\t中文标题\nhttps://existing.example/\tChanged\nbad URL",
                                    folder="资料 / 工具")
    result = import_workflow.apply(conn, ready(conn, value), settings)
    assert result["inserted"] == 1 and result["merged_duplicates"] == 1 and result["skipped"] == 1
    assert [item["status"] for item in result["items"]] == ["imported", "existing", "invalid"]
    rows = conn.execute("SELECT title,folder FROM bookmark ORDER BY id").fetchall()
    assert tuple(rows[0]) == ("Local title", "Original")
    assert tuple(rows[1]) == ("中文标题", "资料 / 工具")
    history = conn.execute("SELECT state,result FROM import_run").fetchone()
    assert history["state"] == "partial" and json.loads(history["result"]) == result


def test_lost_response_retry_returns_saved_receipt_even_after_library_changed(conn, settings):
    body = ready(conn)
    first = import_workflow.apply(conn, body, settings)
    library.create_bookmark(conn, library.CreateBookmark(url="https://another.example/"), settings=settings)
    assert import_workflow.apply(conn, body, settings) == first
    assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM import_run").fetchone()[0] == 1


def test_receipt_cannot_be_reused_for_different_content(conn, settings):
    body = ready(conn)
    import_workflow.apply(conn, body, settings)
    with pytest.raises(HTTPException) as error:
        import_workflow.apply(conn, body.model_copy(update={"folder": "Other"}), settings)
    assert error.value.status_code == 409
    assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 1


def test_stale_preview_requires_review_again_and_applies_nothing(conn, settings):
    body = ready(conn)
    library.create_bookmark(conn, library.CreateBookmark(url="https://changed.example/"), settings=settings)
    with pytest.raises(HTTPException) as error:
        import_workflow.apply(conn, body, settings)
    assert error.value.status_code == 409
    assert conn.execute("SELECT COUNT(*) FROM import_run").fetchone()[0] == 0


@pytest.mark.parametrize("text", [" \n\t", "\n".join(f"https://example.org/{i}" for i in range(501))])
def test_empty_or_oversized_batches_are_refused_before_mutation(conn, text):
    with pytest.raises(HTTPException) as error:
        import_workflow.preview(conn, import_workflow.UrlDraft(text=text))
    assert error.value.status_code == 422
    assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 0


def test_apply_rolls_back_the_batch_if_a_later_insert_fails(conn, settings, monkeypatch):
    body = ready(conn, import_workflow.UrlDraft(text="https://one.example/\nhttps://two.example/"))
    real = library.create_bookmark
    calls = 0

    def fails(database, value, **options):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Synthetic write failure")
        return real(database, value, **options)

    monkeypatch.setattr(library, "create_bookmark", fails)
    with pytest.raises(RuntimeError, match="Synthetic"):
        import_workflow.apply(conn, body, settings)
    assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM import_run").fetchone()[0] == 0


def test_file_receipt_is_atomic_persistent_and_does_not_repeat_updates(client):
    raw = b'<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><DT><A HREF="https://synthetic.example/">Synthetic</A></DL>'
    headers = {"x-import-id": uuid.uuid4().hex, "x-filename": "bookmarks.html"}
    first = client.post("/admin/import", content=raw, headers=headers)
    second = client.post("/admin/import", content=raw, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() and first.json()["inserted"] == 1
    history = client.get("/admin/import/history").json()
    assert len(history["items"]) == 1 and history["items"][0]["label"] == "bookmarks.html"


def test_invalid_file_does_not_report_success_and_preserves_failure_receipt(client):
    response = client.post("/admin/import", content=b"<html>Not a bookmark export</html>",
                           headers={"x-import-id": uuid.uuid4().hex})
    assert response.status_code == 400
    assert client.app.state.fm.conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 0
    item = client.get("/admin/import/history").json()["items"][0]
    assert item["state"] == "failed" and "no changes" in item["error"]


@pytest.mark.parametrize("method,path", [
    ("POST", "/admin/import/urls/preview"), ("POST", "/admin/import/urls"),
    ("GET", "/admin/import/history"), ("GET", "/admin/import/history/synthetic_receipt_1"),
])
def test_import_preview_and_history_keep_the_token_and_loopback_gates(client, settings, method, path):
    assert client.request(method, path, json={}, headers={"Authorization": ""}).status_code == 401
    with TestClient(create_app(settings), client=("10.0.0.9", 40404)) as remote:
        remote.headers["Authorization"] = "Bearer " + remote.app.state.fm.token
        assert remote.request(method, path, json={}).status_code == 403


def test_history_paginates_and_omits_large_item_lists_from_overview(client):
    conn = client.app.state.fm.conn
    with library.transaction(conn):
        for number in range(23):
            import_workflow.record(conn, source="urls", label=str(number), result={
                "inserted": 1, "items": [{"url": "https://synthetic.example/", "line": 1}]})
    first = client.get("/admin/import/history?limit=20").json()
    second = client.get("/admin/import/history?limit=20&offset=20").json()
    assert len(first["items"]) == 20 and first["has_more"]
    assert len(second["items"]) == 3 and not second["has_more"]
    assert not {item["id"] for item in first["items"]} & {item["id"] for item in second["items"]}
    assert "items" not in first["items"][0]["result"]
    detail = client.get("/admin/import/history/" + first["items"][0]["id"]).json()
    assert detail["result"]["items"][0]["line"] == 1
    assert client.get("/admin/import/history/invalid").status_code == 422


@pytest.mark.parametrize("busy", ["health_running", "model_users"])
def test_file_import_waits_for_other_active_writers(client, busy):
    setattr(client.app.state.fm, busy, 1)
    response = client.post("/admin/import", content=b'<!DOCTYPE NETSCAPE-Bookmark-file-1><DL></DL>')
    assert response.status_code == 409


@pytest.mark.parametrize("immediate_cancel", [False, True])
async def test_site_import_keeps_history_even_when_cancelled_before_coroutine_starts(settings, monkeypatch, immediate_cancel):
    async def fake(conn, start_url, **options):
        report = CrawlReport(start_url, pages_attempted=1, pages_fetched=1, inserted=1)
        options["on_progress"](report)
        return report

    monkeypatch.setattr(crawl_jobs, "crawl_site", fake)
    runner = CrawlRunner(settings.data_dir)
    started = runner.start(CrawlRequest(start_url="https://synthetic.example/"), settings)
    if immediate_cancel:
        await runner.cancel()
    else:
        await asyncio.wait_for(runner.task, 2)
    conn = open_db(settings.db_path)
    try:
        row = conn.execute("SELECT state,source,result FROM import_run WHERE id=?", (started["id"],)).fetchone()
        assert row is not None and row["source"] == "site"
        assert row["state"] == ("cancelled" if immediate_cancel else "done")
        if not immediate_cancel:
            assert json.loads(row["result"])["inserted"] == 1
    finally:
        conn.close()


def test_restarting_marks_unfinished_site_history_as_interrupted(settings):
    settings.ensure_dirs()
    conn = open_db(settings.db_path)
    with library.transaction(conn):
        identity = import_workflow.record(conn, source="site", label="https://synthetic.example/",
                                          result={}, state="running")
    conn.close()
    with TestClient(create_app(settings), client=("127.0.0.1", 40404)) as client:
        client.headers["Authorization"] = "Bearer " + client.app.state.fm.token
        item = client.get("/admin/import/history/" + identity).json()
        assert item["state"] == "interrupted"
