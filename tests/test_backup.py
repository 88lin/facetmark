"""Portable backups, tested with isolated saved pages and conversations only."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from facetmark import db, library, service
from facetmark.api import create_app
from facetmark.configfile import update_config
from facetmark.fetch import store as fetchstore
from facetmark.importers import import_bookmarks
from facetmark.normalize import normalize_url

STAMP = 1_700_000_000
PAGE = "https://portable.test/saved-page"
BODY = "保存的正文。Portablebackup evidence survives a move to a new library."
SUMMARY = "目标语言摘要 portablebackupsummary"
INTENTS = ["如何恢复保存的收藏正文", "portable backup recovery"]


@pytest.fixture
def libraries():
    source, destination = db.open_db(":memory:"), db.open_db(":memory:")
    try:
        yield source, destination
    finally:
        destination.close()
        source.close()


def seed_page(conn, settings, *, url=PAGE, body=BODY, summary=SUMMARY, basis=None):
    bid = service.save_bookmark(conn, url, title="原始收藏标题", folder="阅读",
        tags=["备份"], date_added=STAMP, settings=settings)["bookmark_id"]
    if body is not None:
        saved = fetchstore.store_body(conn, bid, body=body, extractor="synthetic-extractor",
            channel="extension", http_status=200, final_url=url + "?canonical=1")
        source_hash = saved.body_hash
        conn.execute("UPDATE content SET fetched_at=? WHERE bookmark_id=?", (STAMP + 2, bid))
    else:
        source_hash = conn.execute("SELECT fm_title_hash(?,?)", ("原始收藏标题", url)).fetchone()[0]
    if summary is not None:
        conn.execute(
            "INSERT INTO enrichment(bookmark_id,ai_title,summary,language,prompt_hash,"
            "key_points,entities,topics,utility,content_type,basis,model,source_hash,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (bid, "AI 生成的中文标题", summary, "zh", "saved-prompt-hash",
             db.jdump(["保留正文", "重建本地索引"]), db.jdump(["Facetmark"]), db.jdump(["备份恢复"]),
             "用于离线查阅", "article", basis or ("body" if body is not None else "title"),
             "synthetic-summary-model", source_hash, STAMP + 3),
        )
        conn.executemany(
            "INSERT INTO intent_query(bookmark_id,text,kept,probe_rank,created_at,scored_at) "
            "VALUES(?,?,1,7,?,?)", [(bid, text, STAMP + 3, STAMP + 4) for text in INTENTS],
        )
    conn.commit()
    return bid


def citation(bid, url=PAGE, *, n=1, excerpt=BODY):
    return {"n": n, "bookmark_id": bid, "url": url, "title": "原始收藏标题",
        "ai_title": "AI 生成的中文标题", "summary": SUMMARY, "excerpt": excerpt,
        "basis": "body", "source_hash": "saved-citation-hash", "content_updated_at": STAMP + 2}


def seed_conversation(conn, conversation_id, *, pins=(), sources=(), pending=False, content="保存的回答 [1]"):
    conn.execute(
        "INSERT INTO chat_conversation(id,title,bookmark_ids,created_at,updated_at) VALUES(?,?,?,?,?)",
        (conversation_id, "保存的中文会话", db.jdump(list(pins)), STAMP + 5, STAMP + 6),
    )
    conn.executemany(
        "INSERT INTO chat_message(conversation_id,role,content,status,sources,model,request_id,created_at) "
        "VALUES(?,?,?,?,?,?,?,?)",
        [(conversation_id, "user", "怎样恢复收藏？", "complete", "[]", "", "saved-question", STAMP + 5),
         (conversation_id, "assistant", content, "pending" if pending else "complete",
          db.jdump(list(sources)), "synthetic-chat-model", "", STAMP + 6)],
    )
    conn.commit()


def bookmark_id(conn, url=PAGE):
    return conn.execute("SELECT id FROM bookmark WHERE url_hash=?", (normalize_url(url).hash,)).fetchone()[0]


def snapshot(conn):
    tables = ("bookmark", "content", "enrichment", "intent_query", "enrichment_failure",
        "fetch_queue", "chat_conversation", "chat_message", "fts_seg", "fts_tri")
    return {table: [tuple(row) for row in conn.execute(f"SELECT rowid,* FROM {table} ORDER BY rowid")]
        for table in tables}


def export(conn, channel, *, selected=None):
    if channel == "service":
        return service.export_bookmarks(conn, "tag:备份" if selected is not None else "", full=True)
    return library.export_library(conn, library.ExportRequest(ids=selected))


@pytest.mark.parametrize("channel", ["service", "desktop"])
def test_full_round_trip_restores_reading_language_intents_and_remaps_chat_ids(libraries, settings, channel):
    source, destination = libraries
    original_id = seed_page(source, settings)
    seed_conversation(source, "portable-conversation", pins=[original_id], sources=[citation(original_id)])
    filler = service.save_bookmark(destination, "https://local.test/unrelated", settings=settings)["bookmark_id"]
    assert filler == original_id  # A foreign row ID would resolve to this unrelated local bookmark.

    payload = export(source, channel)
    assert payload["facetmark"]["version"] == 2
    assert payload["facetmark"]["full"] is True and payload["facetmark"]["restorable"] is True
    stats = service.import_content(destination, json.dumps(payload, ensure_ascii=False), settings=settings)
    assert {key: stats[key] for key in (
        "inserted", "restored_bodies", "restored_summaries", "restored_conversations", "restored_messages"
    )} == {"inserted": 1, "restored_bodies": 1, "restored_summaries": 1,
        "restored_conversations": 1, "restored_messages": 2}
    assert not stats["warnings"], stats["warnings"]

    local_id = bookmark_id(destination)
    assert local_id != original_id
    reading = service.export_reading_data(destination, [local_id])[local_id]
    original = payload["bookmarks"][0]
    assert reading["content"] == original["content"]
    for key in ("ai_title", "summary", "summary_language", "prompt_hash", "topics", "entities",
                "key_points", "utility", "content_type", "basis", "model", "source_hash", "created_at"):
        assert reading["derived"][key] == original["derived"][key]
    assert reading["derived"]["intent_queries"] == INTENTS
    intents = destination.execute(
        "SELECT text,kept,probe_rank,scored_at FROM intent_query WHERE bookmark_id=? ORDER BY id", (local_id,)
    ).fetchall()
    assert [tuple(row) for row in intents] == [(text, 0, None, None) for text in INTENTS]
    assert local_id in {row[0] for row in destination.execute(
        "SELECT rowid FROM fts_tri WHERE fts_tri MATCH 'portablebackupsummary'"
    )}
    assert not db.vec_tables_exist(destination)

    conversation = destination.execute("SELECT * FROM chat_conversation WHERE id='portable-conversation'").fetchone()
    assert db.jload(conversation["bookmark_ids"]) == [local_id]
    assert conversation["created_at"] == STAMP + 5 and conversation["updated_at"] == STAMP + 6
    messages = destination.execute(
        "SELECT * FROM chat_message WHERE conversation_id=? ORDER BY id", (conversation["id"],)
    ).fetchall()
    assert [row["role"] for row in messages] == ["user", "assistant"]
    assert messages[0]["request_id"] == "saved-question"
    assert messages[1]["content"] == "保存的回答 [1]" and messages[1]["model"] == "synthetic-chat-model"
    assert db.jload(messages[1]["sources"])[0] == {**citation(original_id), "bookmark_id": local_id}

    before_repeat = snapshot(destination)
    repeated = service.import_content(destination, json.dumps(payload), settings=settings)
    assert repeated["inserted"] == 0
    assert all(repeated[key] == 0 for key in (
        "restored_bodies", "restored_summaries", "restored_conversations", "restored_messages"))
    after_repeat = snapshot(destination)
    for table in ("content", "enrichment", "intent_query", "chat_conversation", "chat_message"):
        assert after_repeat[table] == before_repeat[table]


def test_reimport_is_idempotent_and_existing_local_reading_and_conversation_win(libraries, settings):
    source, destination = libraries
    foreign_id = seed_page(source, settings)
    seed_conversation(source, "same-conversation", pins=[foreign_id], sources=[citation(foreign_id)])
    local_id = seed_page(destination, settings, body="LOCAL_BODY_WINS", summary="LOCAL_SUMMARY_WINS")
    seed_conversation(destination, "same-conversation", pins=[local_id], content="LOCAL_REPLY_WINS")
    before = snapshot(destination)
    archive = json.dumps(service.export_bookmarks(source, full=True), ensure_ascii=False)
    for _ in range(2):
        stats = service.import_content(destination, archive, settings=settings)
        assert stats["inserted"] == 0
        assert all(stats[key] == 0 for key in (
            "restored_bodies", "restored_summaries", "restored_conversations", "restored_messages"))
        after = snapshot(destination)
        for table in ("content", "enrichment", "intent_query", "chat_conversation", "chat_message"):
            assert after[table] == before[table]
    assert destination.execute("SELECT count(*) FROM bookmark").fetchone()[0] == 1


@pytest.mark.parametrize("existing_body", [False, True])
def test_restore_fills_missing_summary_and_resets_intents_without_replacing_saved_body(libraries, settings, existing_body):
    source, destination = libraries
    seed_page(source, settings)
    local_id = seed_page(destination, settings, body=BODY if existing_body else None, summary=None)
    conn_body = destination.execute("SELECT * FROM content WHERE bookmark_id=?", (local_id,)).fetchone()
    destination.execute("INSERT INTO enrichment_failure VALUES(?,?,?)", (local_id, "old synthetic failure", STAMP))
    destination.execute("INSERT INTO intent_query(bookmark_id,text,kept) VALUES(?,?,1)", (local_id, "obsolete query"))
    destination.commit()
    payload = service.export_bookmarks(source, full=True)
    payload["bookmarks"][0]["derived"]["intent_queries"] += INTENTS

    stats = service.import_content(destination, json.dumps(payload), settings=settings)
    assert stats["restored_bodies"] == int(not existing_body) and stats["restored_summaries"] == 1
    assert destination.execute("SELECT summary FROM enrichment WHERE bookmark_id=?", (local_id,)).fetchone()[0] == SUMMARY
    assert not destination.execute("SELECT 1 FROM enrichment_failure WHERE bookmark_id=?", (local_id,)).fetchone()
    assert [tuple(row) for row in destination.execute(
        "SELECT text,kept,probe_rank,scored_at FROM intent_query WHERE bookmark_id=? ORDER BY id", (local_id,)
    )] == [(text, 0, None, None) for text in INTENTS]
    if existing_body:
        assert tuple(destination.execute("SELECT * FROM content WHERE bookmark_id=?", (local_id,)).fetchone()) == tuple(conn_body)


def test_title_only_summary_restores_against_current_title_hash(libraries, settings):
    source, destination = libraries
    seed_page(source, settings, body=None)
    payload = service.export_bookmarks(source, full=True)
    stats = service.import_content(destination, json.dumps(payload), settings=settings)
    assert stats["restored_bodies"] == 0 and stats["restored_summaries"] == 1
    derived = service.export_reading_data(destination, [bookmark_id(destination)])[bookmark_id(destination)]["derived"]
    assert derived["basis"] == "title" and derived["summary_language"] == "zh"
    assert derived["intent_queries"] == INTENTS


@pytest.mark.parametrize("source_hash", ["different-page-fingerprint", ""])
def test_stale_saved_summary_is_skipped_while_saved_body_is_restored(libraries, settings, source_hash):
    source, destination = libraries
    seed_page(source, settings)
    payload = service.export_bookmarks(source, full=True)
    payload["bookmarks"][0]["derived"]["source_hash"] = source_hash
    stats = service.import_content(destination, json.dumps(payload), settings=settings)
    assert stats["restored_bodies"] == 1 and stats["restored_summaries"] == 0
    assert any("source differs" in warning for warning in stats["warnings"])
    assert destination.execute("SELECT body_text FROM content").fetchone()[0] == BODY
    assert destination.execute("SELECT count(*) FROM enrichment").fetchone()[0] == 0
    assert destination.execute("SELECT count(*) FROM intent_query").fetchone()[0] == 0


def test_newer_local_body_wins_and_summary_from_an_older_backup_is_skipped(libraries, settings):
    source, destination = libraries
    seed_page(source, settings)
    seed_page(destination, settings, body="NEWER_LOCAL_BODY", summary=None)
    payload = service.export_bookmarks(source, full=True)
    stats = service.import_content(destination, json.dumps(payload), settings=settings)
    assert stats["restored_bodies"] == 0 and stats["restored_summaries"] == 0
    assert any("source differs" in warning for warning in stats["warnings"])
    assert destination.execute("SELECT body_text FROM content").fetchone()[0] == "NEWER_LOCAL_BODY"
    assert destination.execute("SELECT count(*) FROM enrichment").fetchone()[0] == 0


def test_karakeep_metadata_summary_is_restorable_without_a_page_fingerprint(libraries, settings):
    source, destination = libraries
    seed_page(source, settings, body=None, basis="karakeep")
    payload = service.export_bookmarks(source, full=True)
    payload["bookmarks"][0]["derived"]["source_hash"] = "bridge-metadata-fingerprint"
    stats = service.import_content(destination, json.dumps(payload), settings=settings)
    assert stats["restored_summaries"] == 1
    assert destination.execute("SELECT summary,basis FROM enrichment").fetchone()["basis"] == "karakeep"


def test_unknown_citations_keep_original_urls_and_missing_pins_keep_restricted_scope(libraries, settings):
    source, destination = libraries
    foreign_id = seed_page(source, settings)
    seed_conversation(source, "partly-missing", pins=[foreign_id, -1], sources=[citation(foreign_id)], pending=True)
    payload = service.export_bookmarks(source, full=True)
    record = payload["conversations"][0]
    record["bookmark_urls"] = [PAGE + "?utm_source=portable#same-page", "https://missing.test/pinned"]
    record["missing_bookmarks"] = 1
    record["messages"][1]["status"] = "pending"
    sources = record["messages"][1]["sources"]
    sources[0]["url"] = PAGE + "?utm_source=portable#same-page"
    sources.append(citation(foreign_id, "https://missing.test/original-citation", n=2, excerpt="MISSING_SOURCE_EXCERPT"))
    filler = service.save_bookmark(destination, "https://local.test/unrelated", settings=settings)["bookmark_id"]
    assert filler == foreign_id

    stats = service.import_content(destination, json.dumps(payload), settings=settings)
    assert stats["restored_conversations"] == 1 and stats["restored_messages"] == 2
    local_id = bookmark_id(destination)
    pins = db.jload(destination.execute("SELECT bookmark_ids FROM chat_conversation").fetchone()[0])
    assert pins == [local_id, -1, -1]
    reply = destination.execute("SELECT status,sources FROM chat_message WHERE role='assistant'").fetchone()
    assert reply["status"] == "cancelled"
    restored = db.jload(reply["sources"])
    assert restored[0]["bookmark_id"] == local_id and restored[0]["url"] == sources[0]["url"]
    assert restored[1]["bookmark_id"] is None
    assert restored[1]["url"] == "https://missing.test/original-citation"
    assert restored[1]["excerpt"] == "MISSING_SOURCE_EXCERPT"


@pytest.mark.parametrize("channel", ["service", "desktop"])
def test_scoped_export_contains_only_conversations_whose_entire_reference_set_is_in_scope(conn, settings, channel):
    selected = seed_page(conn, settings)
    other = seed_page(conn, settings, url="https://outside.test/page", body="OUTSIDE_PAGE_BODY", summary="OUTSIDE_SUMMARY")
    conn.execute("UPDATE bookmark SET tags='[]' WHERE id=?", (other,))
    conn.commit()
    fixtures = [
        ("inside", [selected], [citation(selected)]),
        ("pin-only", [selected], []),
        ("source-only", [], [citation(selected)]),
        ("outside", [other], [citation(other, "https://outside.test/page", excerpt="OUTSIDE_ONLY_EXCERPT")]),
        ("mixed", [selected], [citation(selected), citation(other, "https://outside.test/page", n=2, excerpt="MIXED_OUTSIDE_EXCERPT")]),
        ("missing-pin", [selected, -1], [citation(selected)]),
        ("null-source", [selected], [citation(None, "https://outside.test/missing", excerpt="NULL_SOURCE_EXCERPT")]),
        ("missing-row", [selected], [citation(900_000, "https://outside.test/deleted", excerpt="DELETED_ROW_EXCERPT")]),
        ("unscoped", [], []),
    ]
    for name, pins, sources in fixtures:
        seed_conversation(conn, name, pins=pins, sources=sources, pending=name == "unscoped")

    payload = export(conn, channel, selected=[selected])
    assert [record["url"] for record in payload["bookmarks"]] == [PAGE]
    assert {record["id"] for record in payload["conversations"]} == {"inside", "pin-only", "source-only"}
    serialized = json.dumps(payload)
    assert "outside.test" not in serialized
    assert all(sentinel not in serialized for sentinel in (
        "OUTSIDE_PAGE_BODY", "OUTSIDE_SUMMARY", "OUTSIDE_ONLY_EXCERPT", "MIXED_OUTSIDE_EXCERPT",
        "NULL_SOURCE_EXCERPT", "DELETED_ROW_EXCERPT"))

    full = export(conn, channel)
    assert {record["id"] for record in full["conversations"]} == {record[0] for record in fixtures}
    unscoped = next(record for record in full["conversations"] if record["id"] == "unscoped")
    assert unscoped["messages"][-1]["status"] == "cancelled"


@pytest.mark.parametrize("header", [
    {}, {"version": 1, "full": True, "restorable": True},
    {"version": 2}, {"version": 2, "full": True}, {"version": 2, "restorable": True},
    {"version": 2, "full": False, "restorable": True}, {"version": 2, "full": True, "restorable": False},
    {"version": 2, "full": 1, "restorable": True}, {"version": 2, "full": True, "restorable": "true"},
    {"version": 3, "full": True, "restorable": True},
], ids=["unmarked", "v1", "v2-metadata", "missing-restorable", "missing-full", "not-full",
        "not-restorable", "numeric-full", "string-restorable", "future-version"])
def test_files_without_both_explicit_v2_markers_keep_metadata_only_contract(libraries, settings, header):
    source, destination = libraries
    bid = seed_page(source, settings)
    seed_conversation(source, "ignored-reading", pins=[bid], sources=[citation(bid)])
    payload = service.export_bookmarks(source, full=True)
    payload["facetmark"] = header
    # Invalid reading must also be ignored in a metadata-only file.
    payload["bookmarks"][0]["content"]["fetched_at"] = -1
    stats = service.import_content(destination, json.dumps(payload), settings=settings)
    assert stats["inserted"] == 1 and stats["parsed"] == 1
    assert all(stats[key] == 0 for key in (
        "restored_bodies", "restored_summaries", "restored_conversations", "restored_messages"))
    for table in ("content", "enrichment", "intent_query", "chat_conversation", "chat_message"):
        assert destination.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


@pytest.mark.parametrize("malformed", ["body-stamp", "summary-size", "request-id", "duplicate-question", "pin-limit", "conversation-shape"])
def test_malformed_full_backups_fail_before_any_metadata_or_reading_is_changed(libraries, settings, malformed):
    source, destination = libraries
    bid = seed_page(source, settings)
    seed_conversation(source, "validated-first", pins=[bid], sources=[citation(bid)])
    payload = service.export_bookmarks(source, full=True)
    if malformed == "body-stamp":
        payload["bookmarks"][0]["content"]["fetched_at"] = -1
    elif malformed == "summary-size":
        payload["bookmarks"][0]["derived"]["summary"] = "x" * 60_001
    elif malformed == "request-id":
        payload["conversations"][0]["messages"][0]["request_id"] = "invalid request id"
    elif malformed == "duplicate-question":
        payload["conversations"][0]["messages"].append(dict(payload["conversations"][0]["messages"][0]))
    elif malformed == "pin-limit":
        payload["conversations"][0]["missing_bookmarks"] = 12
    else:
        payload["conversations"] = {}
    local_id = seed_page(destination, settings, url="https://local.test/preserved")
    destination.execute("UPDATE bookmark SET title='OUTER_PENDING_EDIT' WHERE id=?", (local_id,))
    before = snapshot(destination)

    with pytest.raises(ValueError):
        import_bookmarks(destination, content=json.dumps(payload), settings=settings)
    assert snapshot(destination) == before
    assert destination.in_transaction


class SyntheticAbort(BaseException):
    pass


@pytest.mark.parametrize("failure", [RuntimeError, SyntheticAbort])
def test_failure_after_one_restored_body_rolls_back_import_savepoint_and_keeps_outer_transaction(libraries, settings, monkeypatch, failure):
    source, destination = libraries
    seed_page(source, settings)
    seed_page(source, settings, url="https://portable.test/second")
    local_id = seed_page(destination, settings, url="https://local.test/preserved")
    destination.execute("UPDATE bookmark SET title='OUTER_PENDING_EDIT' WHERE id=?", (local_id,))
    before = snapshot(destination)
    archive = json.dumps(service.export_bookmarks(source, full=True))
    original = fetchstore.store_body
    calls = []

    def fail_on_second(conn, bookmark_id, **values):
        calls.append(bookmark_id)
        if len(calls) == 2:
            raise failure("synthetic interruption during restore")
        return original(conn, bookmark_id, **values)

    with monkeypatch.context() as patch:
        patch.setattr(fetchstore, "store_body", fail_on_second)
        with pytest.raises(failure):
            import_bookmarks(destination, content=archive, settings=settings)
    assert len(calls) == 2
    assert snapshot(destination) == before
    assert destination.in_transaction
    # The released savepoint must leave the same connection usable for a retry.
    retried = import_bookmarks(destination, content=archive, settings=settings)
    assert retried.restored_bodies == 2 and retried.restored_summaries == 2
    assert destination.execute("SELECT title FROM bookmark WHERE id=?", (local_id,)).fetchone()[0] == "OUTER_PENDING_EDIT"


@pytest.mark.parametrize("channel", ["service", "desktop"])
def test_export_omits_credentials_and_vectors_even_when_both_are_stored_locally(conn, settings, monkeypatch, channel):
    secrets = {"api_key": "LEGACY_SECRET_91827364", "chat_api_key": "CHAT_SECRET_92837465",
        "embed_api_key": "EMBED_SECRET_93847566", "mcp_token": "MCP_SECRET_94857667"}
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(settings.data_dir))
    settings.ensure_dirs()
    update_config(secrets)
    bid = seed_page(conn, settings)
    db.ensure_vec_tables(conn, 8, "synthetic-portable-vector")
    db.upsert_content_vector(conn, bid, [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], text_hash="local-vector-fingerprint")
    intent_id = conn.execute("SELECT id FROM intent_query ORDER BY id LIMIT 1").fetchone()[0]
    db.upsert_intent_vector(conn, intent_id, [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    conn.commit()
    payload = export(conn, channel)
    text = json.dumps(payload)
    assert all(secret not in text for secret in secrets.values())
    assert all(name not in text for name in (*secrets, "embedding", "vec_content", "vec_intent", "local-vector-fingerprint"))
    assert set(payload) == {"facetmark", "bookmarks", "conversations"}
    assert payload["bookmarks"][0]["content"]["body_text"] == BODY


def test_desktop_download_can_be_uploaded_into_a_fresh_library_with_saved_conversation(settings, tmp_path):
    source_settings = settings.model_copy(update={"data_dir": tmp_path / "source-app"})
    destination_settings = settings.model_copy(update={"data_dir": tmp_path / "destination-app"})
    source_app = create_app(source_settings)
    with TestClient(source_app, client=("127.0.0.1", 42000)) as client:
        state = source_app.state.fm
        client.headers["Authorization"] = "Bearer " + state.token
        bid = seed_page(state.conn, state.settings)
        seed_conversation(state.conn, "downloaded-conversation", pins=[bid], sources=[citation(bid)])
        downloaded = client.post("/admin/library/export", json={"format": "json"})
        assert downloaded.status_code == 200, downloaded.text
        assert downloaded.headers["cache-control"] == "no-store"
        assert "attachment;" in downloaded.headers["content-disposition"]

    destination_app = create_app(destination_settings)
    with TestClient(destination_app, client=("127.0.0.1", 42000)) as client:
        state = destination_app.state.fm
        client.headers["Authorization"] = "Bearer " + state.token
        service.save_bookmark(state.conn, "https://local.test/filler", settings=state.settings)
        imported = client.post("/admin/import", content=downloaded.content,
            headers={"content-type": "application/json"})
        assert imported.status_code == 200, imported.text
        assert imported.json()["restored_conversations"] == 1
        local_id = bookmark_id(state.conn)
        reading = client.get(f"/bookmark/{local_id}?body=true")
        assert reading.status_code == 200 and reading.json()["body_text"] == BODY
        conversation = client.get("/chat/conversations/downloaded-conversation")
        assert conversation.status_code == 200, conversation.text
        assert conversation.json()["bookmark_ids"] == [local_id]
        assert conversation.json()["messages"][-1]["sources"][0]["bookmark_id"] == local_id
