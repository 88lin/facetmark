"""Removed bookmarks must not lend their identity to unrelated new pages."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from facetmark import service
from facetmark.bridges import karakeep
from facetmark.db import connect, get_meta, next_bookmark_id, open_db, set_meta
from facetmark.importers import import_bookmarks
from facetmark.normalize import normalize_url
from tests.test_library import BASE, create
from tests.test_library import client as client


def insert_number(conn, number):
    url = normalize_url(f"https://identity.example/{number}")
    conn.execute("INSERT INTO bookmark(id,url,url_norm,url_hash,title,created_at,updated_at) "
                 "VALUES(?,?,?,?,?,1,1)", (number, url.original, url.normalized, url.hash, f"Page {number}"))


@pytest.mark.parametrize("entry", ["manual", "save", "import", "karakeep"])
def test_every_creation_entry_preserves_a_removed_identity(client, entry):
    old = create(client, "removed-identity")
    assert client.delete(f"{BASE}/bookmarks/{old}").status_code == 200
    state = client.app.state.fm
    url = "https://identity.example/replacement"
    if entry == "manual":
        replacement = create(client, "manual-replacement")
    elif entry == "save":
        replacement = service.save_bookmark(state.conn, url, settings=state.settings)["bookmark_id"]
    elif entry == "import":
        result = import_bookmarks(state.conn, content=f'<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p><DT><A HREF="{url}">Replacement</A></DL><p>', settings=state.settings)
        assert result.inserted == 1
        replacement = state.conn.execute("SELECT id FROM bookmark WHERE url=?", (url,)).fetchone()[0]
    else:
        result = asyncio.run(karakeep.add_documents(state.conn, [{"id": "replacement", "userId": "local",
                              "url": url, "title": "Replacement"}], settings=state.settings, embed=False))
        assert result["created"] == 1
        replacement = state.conn.execute("SELECT id FROM bookmark WHERE url=?", (url,)).fetchone()[0]
    assert replacement > old
    assert client.get(f"/bookmark/{old}").status_code == 404
    assert client.get(f"/bookmark/{replacement}").status_code == 200


def test_direct_insert_then_delete_also_preserves_its_number(conn):
    insert_number(conn, 500)
    conn.execute("DELETE FROM bookmark WHERE id=500")
    assert next_bookmark_id(conn) == 501


def test_upgrading_retains_numbers_in_saved_chat_pins_and_sources(tmp_path):
    path = tmp_path / "identity.db"
    conn = open_db(path)
    insert_number(conn, 7)
    conn.execute("INSERT INTO chat_conversation(id,title,bookmark_ids,created_at,updated_at) "
                 "VALUES('legacy','Saved reading','[81]',1,1)")
    conn.execute("INSERT INTO chat_message(conversation_id,role,content,sources,created_at) "
                 "VALUES('legacy','assistant','Saved quotation','[{\"bookmark_id\":93}]',1)")
    conn.execute("INSERT INTO chat_conversation(id,title,bookmark_ids,created_at,updated_at) "
                 "VALUES('damaged','Older unreadable scope','not-json',1,1)")
    conn.execute("INSERT INTO chat_message(conversation_id,role,sources,created_at) "
                 "VALUES('damaged','assistant','[null,\"bad\",3,{\"bookmark_id\":\"wrong\"}]',1)")
    # Simulate the preceding schema, where these pages had already been
    # removed but their conversation and citation remain intentionally saved.
    conn.execute("DROP TABLE library_operation")
    conn.execute("DROP TRIGGER IF EXISTS bookmark_identity_before_delete")
    conn.execute("DELETE FROM meta WHERE key='bookmark_id_highwater'")
    set_meta(conn, "schema_version", "11")
    conn.close()
    upgraded = open_db(path)
    try:
        assert upgraded.execute("SELECT id,title FROM bookmark").fetchone()[0] == 7
        assert upgraded.execute("SELECT bookmark_ids FROM chat_conversation WHERE id='legacy'").fetchone()[0] == "[81]"
        assert upgraded.execute("SELECT content FROM chat_message WHERE conversation_id='legacy'").fetchone()[0] == "Saved quotation"
        assert upgraded.execute("SELECT bookmark_ids FROM chat_conversation WHERE id='damaged'").fetchone()[0] == "not-json"
        assert next_bookmark_id(upgraded) == 94
    finally:
        upgraded.close()


def test_separate_connections_reserve_distinct_numbers_and_reopen_remembers_them(tmp_path):
    path = tmp_path / "writers.db"
    open_db(path).close()

    def reserve(_):
        conn = connect(path)
        try:
            return [next_bookmark_id(conn) for _ in range(12)]
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        numbers = [number for batch in pool.map(reserve, range(4)) for number in batch]
    assert sorted(numbers) == list(range(1, 49))
    reopened = open_db(path)
    try:
        assert get_meta(reopened, "bookmark_id_highwater") == "48"
        assert next_bookmark_id(reopened) == 49
    finally:
        reopened.close()
