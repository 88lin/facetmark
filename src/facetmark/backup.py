"""Portable reading/chat restoration, without credentials or foreign vectors.

Version 2 full exports are explicitly restorable. Merge fills missing reading
data and adds missing conversations; existing local text and replies win.
Bookmark references are remapped by URL, never by another database's row IDs.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from .db import in_chunks, jdump, jload, now
from .normalize import normalize_url
from .text import sync_fts

Short = Annotated[str, Field(max_length=2048)]
Stamp = Annotated[int, Field(ge=0, le=2**63 - 1)]


class SavedBody(BaseModel):
    body_text: str | None = Field(default=None, max_length=2_000_000)
    fetched_at: Stamp | None = None
    extractor: Short | None = None
    fetch_channel: Short | None = None
    http_status: int | None = None
    final_url: str | None = Field(default=None, max_length=8192)


class SavedEnrichment(BaseModel):
    ai_title: str = Field(default="", max_length=2048)
    summary: str = Field(default="", max_length=60_000)
    summary_language: Short = ""
    prompt_hash: Short = ""
    topics: list[Short] = Field(default_factory=list, max_length=100)
    entities: list[Short] = Field(default_factory=list, max_length=100)
    key_points: list[Short] = Field(default_factory=list, max_length=100)
    intent_queries: list[Short] = Field(default_factory=list, max_length=100)
    utility: Short = ""
    content_type: Short = ""
    basis: Short = ""
    model: Short = ""
    source_hash: Short = ""
    created_at: Stamp | None = None


class ReadingRecord(BaseModel):
    url: str = Field(max_length=8192)
    content: SavedBody | None = None
    derived: SavedEnrichment | None = None


class SavedSource(BaseModel):
    n: int = Field(ge=1, le=12)
    bookmark_id: int | None = None
    title: Short = ""
    ai_title: Short = ""
    url: str = Field(max_length=8192)
    summary: str | None = Field(default=None, max_length=2048)
    excerpt: str = Field(default="", max_length=4000)
    basis: Short = "title"
    source_hash: Short = ""
    content_updated_at: Stamp | None = None


class SavedMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(default="", max_length=60_000)
    status: Literal["complete", "pending", "error", "cancelled"] = "complete"
    sources: list[SavedSource] = Field(default_factory=list, max_length=12)
    model: Short = ""
    request_id: str = Field(default="", max_length=128, pattern=r"^[\w.-]*$")
    created_at: Stamp


class SavedConversation(BaseModel):
    id: str = Field(min_length=1, max_length=128, pattern=r"^[\w.-]+$")
    title: str = Field(default="", max_length=120)
    bookmark_urls: list[str] = Field(default_factory=list, max_length=12)
    missing_bookmarks: int = Field(default=0, ge=0, le=12)
    created_at: Stamp
    updated_at: Stamp
    messages: list[SavedMessage] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def unique_questions(self):
        ids = [message.request_id for message in self.messages if message.role == "user" and message.request_id]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate question request IDs in a conversation")
        if len(self.bookmark_urls) + self.missing_bookmarks > 12:
            raise ValueError("too many pinned bookmarks")
        return self


def prepare(reading: list[dict], conversations: list[dict]) -> tuple[list[ReadingRecord], list[SavedConversation]]:
    # Validate before importing any bookmark metadata, so a malformed backup
    # cannot report half a restored library as a successful import.
    if not isinstance(reading, list) or not isinstance(conversations, list):
        raise ValueError("reading data and conversations must be arrays")
    return ([ReadingRecord.model_validate(record) for record in reading],
            [SavedConversation.model_validate(record) for record in conversations])


def export_conversations(conn: sqlite3.Connection, ids: list[int], *, all_scope: bool) -> list[dict]:
    selected = set(ids)
    out = []
    for row in conn.execute("SELECT * FROM chat_conversation ORDER BY created_at,id"):
        pins = jload(row["bookmark_ids"])
        messages = [{**dict(message), "sources": jload(message["sources"])} for message in conn.execute(
            "SELECT role,content,status,sources,model,request_id,created_at FROM chat_message WHERE conversation_id=? ORDER BY id",
            (row["id"],))]
        refs = {value for value in pins if isinstance(value, int) and value > 0}
        refs.update(source["bookmark_id"] for message in messages for source in message["sources"]
                    if isinstance(source.get("bookmark_id"), int) and source["bookmark_id"] > 0)
        # A scoped export must not smuggle another bookmark's quoted text out
        # through a mixed conversation. Include the complete conversation only.
        missing_ref = any(not isinstance(value, int) or value <= 0 for value in pins)
        missing_ref |= any(not isinstance(source.get("bookmark_id"), int) or source["bookmark_id"] <= 0
                           for message in messages for source in message["sources"])
        if not all_scope and (missing_ref or not refs or not refs.issubset(selected)):
            continue
        urls = {}
        for batch in in_chunks(list(refs)):
            marks = ",".join("?" for _ in batch)
            urls.update({entry["id"]: entry["url"] for entry in conn.execute(
                f"SELECT id,url FROM bookmark WHERE id IN ({marks})", batch)})
        if not all_scope and set(urls) != refs:
            continue
        for message in messages:
            if message["status"] == "pending":
                message["status"] = "cancelled"
            for source in message["sources"]:
                if source.get("bookmark_id") in urls:
                    source["url"] = urls[source["bookmark_id"]]
        out.append({"id": row["id"], "title": row["title"], "created_at": row["created_at"],
                    "updated_at": row["updated_at"], "bookmark_urls": [urls[bid] for bid in pins if bid in urls],
                    "missing_bookmarks": sum(bid not in urls for bid in pins), "messages": messages})
    return out


def restore(conn: sqlite3.Connection, prepared, stats) -> None:
    from .fetch.store import clear_queue_item, store_body

    reading, conversations = prepared
    for record in reading:
        bookmark = conn.execute("SELECT * FROM bookmark WHERE url_hash=?", (normalize_url(record.url).hash,)).fetchone()
        if bookmark is None:
            continue
        bid = bookmark["id"]
        body = conn.execute("SELECT body_text,body_hash FROM content WHERE bookmark_id=?", (bid,)).fetchone()
        incoming = record.content
        if incoming and incoming.body_text and not (body and body["body_text"]):
            store_body(conn, bid, body=incoming.body_text, extractor=incoming.extractor or "backup",
                       channel=incoming.fetch_channel or "backup", http_status=incoming.http_status,
                       final_url=incoming.final_url or bookmark["url"])
            if incoming.fetched_at is not None:
                conn.execute("UPDATE content SET fetched_at=? WHERE bookmark_id=?", (incoming.fetched_at, bid))
            clear_queue_item(conn, bid, state="done")
            stats.restored_bodies += 1
            body = conn.execute("SELECT body_text,body_hash FROM content WHERE bookmark_id=?", (bid,)).fetchone()
        existing = conn.execute("SELECT * FROM enrichment WHERE bookmark_id=?", (bid,)).fetchone()
        derived = record.derived
        if derived and derived.summary and not (existing and existing["summary"]):
            expected = body["body_hash"] if body and body["body_hash"] else conn.execute(
                "SELECT fm_title_hash(?,?)", (bookmark["title"], bookmark["url"])).fetchone()[0]
            if derived.source_hash != expected and derived.basis != "karakeep":
                stats.warnings.append("Saved summary skipped because its source differs from the current page")
            else:
                from .library import retire_derived
                retire_derived(conn, bid)
                conn.execute("INSERT OR REPLACE INTO enrichment(bookmark_id,summary,key_points,entities,topics,utility,"
                             "content_type,source_hash,model,created_at,basis,ai_title,language,prompt_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (bid, derived.summary, jdump(derived.key_points), jdump(derived.entities), jdump(derived.topics),
                              derived.utility, derived.content_type, expected, derived.model, derived.created_at or now(),
                              derived.basis or ("body" if body and body["body_text"] else "title"), derived.ai_title,
                              derived.summary_language, derived.prompt_hash))
                conn.execute("DELETE FROM enrichment_failure WHERE bookmark_id=?", (bid,))
                conn.executemany("INSERT INTO intent_query(bookmark_id,text,kept,created_at) VALUES(?,?,0,?)",
                                 [(bid, text, now()) for text in dict.fromkeys(derived.intent_queries)])
                stats.restored_summaries += 1
        enrichment = conn.execute("SELECT * FROM enrichment WHERE bookmark_id=?", (bid,)).fetchone()
        sync_fts(conn, bid, title=bookmark["title"], ai_title=enrichment["ai_title"] if enrichment else "",
                 body=body["body_text"] if body else "", summary=enrichment["summary"] if enrichment else "",
                 topics=jload(enrichment["topics"]) if enrichment else [],
                 entities=jload(enrichment["entities"]) if enrichment else [],
                 key_points=jload(enrichment["key_points"]) if enrichment else [], tags=jload(bookmark["tags"]))
    for record in conversations:
        if conn.execute("SELECT 1 FROM chat_conversation WHERE id=?", (record.id,)).fetchone():
            continue

        def resolve(url: str) -> int | None:
            row = conn.execute("SELECT id FROM bookmark WHERE url_hash=?", (normalize_url(url).hash,)).fetchone()
            return row[0] if row else None

        # Missing pins keep a restricted scope. Dropping them all would turn a
        # single-page conversation into an unrelated full-library question.
        pins = [resolve(url) or -1 for url in record.bookmark_urls] + [-1] * record.missing_bookmarks
        conn.execute("INSERT INTO chat_conversation(id,title,bookmark_ids,created_at,updated_at) VALUES(?,?,?,?,?)",
                     (record.id, record.title, jdump(pins), record.created_at, record.updated_at))
        for message in record.messages:
            sources = [{**source.model_dump(), "bookmark_id": resolve(source.url)} for source in message.sources]
            conn.execute("INSERT INTO chat_message(conversation_id,role,content,status,sources,model,request_id,created_at) VALUES(?,?,?,?,?,?,?,?)",
                         (record.id, message.role, message.content, "cancelled" if message.status == "pending" else message.status,
                          jdump(sources), message.model, message.request_id, message.created_at))
            stats.restored_messages += 1
        stats.restored_conversations += 1
