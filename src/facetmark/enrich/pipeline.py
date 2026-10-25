"""Run the enrichment call and persist its output.

Idempotency includes both the source hash and the language/writing contract.
An unchanged page costs nothing to re-index; changing summary instructions
makes its old derived text eligible for regeneration.
"""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import islice

from ..config import Settings, get_settings
from ..db import jdump, now
from ..providers import Provider, ProviderError, get_provider
from ..text import sync_fts, truncate_head_tail
from .prompts import SYSTEM, build_user_prompt, resolve_summary_language, summary_prompt_hash
from .schema import Enrichment, EnrichmentInvalid, coerce


@dataclass(slots=True)
class Target:
    bookmark_id: int
    url: str
    title: str
    folder: str
    body: str
    source_hash: str


@dataclass(slots=True)
class EnrichReport:
    considered: int = 0
    enriched: int = 0
    skipped_unchanged: int = 0
    failed: int = 0
    queries_generated: int = 0
    #: Pages the first call failed on and a half-length body recovered. Worth a
    #: field rather than a log line: a number that climbs means the configured
    #: ``body_truncate_chars`` does not fit the endpoint's per-slot context,
    #: and every one of these cost two calls instead of one.
    rescued_by_shorter_body: int = 0
    errors: list[str] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "considered": self.considered, "enriched": self.enriched,
            "skipped_unchanged": self.skipped_unchanged, "failed": self.failed,
            "queries_generated": self.queries_generated,
            "rescued_by_shorter_body": self.rescued_by_shorter_body,
            "errors": self.errors[:10], "usage": self.usage,
        }


def title_only_hash(title: str, url: str) -> str:
    """Stable source hash for a bookmark whose body was never fetched.

    Without this, every run would re-enrich every unfetchable page forever.
    """
    return "t:" + hashlib.sha256(f"{title}\x00{url}".encode()).hexdigest()


def iter_targets(
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
    force: bool = False,
    ids: Sequence[int] | None = None,
    require_body: bool = False,
    body_chars: int | None = None,
    prompt_hash: str | None = None,
):
    """Bookmarks whose enrichment is missing or stale.

    Privacy-excluded rows are absent by construction: they never reach a model.
    """
    where = ["b.indexable=1", "b.privacy_skipped=0"]
    params: list[object] = []
    if ids is not None:
        if not ids:
            return
        where.append(f"b.id IN ({','.join('?' * len(ids))})")
        params.extend(ids)
    if require_body:
        where.append("c.body_hash IS NOT NULL")
    body_sql = "c.body_text"
    if body_chars is not None:
        head = max(0, int(body_chars * 0.75))
        tail = max(0, body_chars - head)
        body_sql = (f"CASE WHEN length(c.body_text)<={body_chars} THEN c.body_text ELSE "
                    f"substr(c.body_text,1,{head})||' … '||substr(c.body_text,-{tail},{tail}) END") if body_chars else "''"
    sql = (
        f"SELECT b.id, b.url, b.title, b.folder, {body_sql} AS body_text, c.body_hash, e.source_hash, e.summary, e.prompt_hash, "
        "EXISTS(SELECT 1 FROM enrichment_failure ef WHERE ef.bookmark_id=b.id) AS failed "
        "FROM bookmark b "
        "LEFT JOIN content c    ON c.bookmark_id = b.id "
        "LEFT JOIN enrichment e ON e.bookmark_id = b.id "
        f"WHERE {' AND '.join(where)} ORDER BY b.id"
    )
    count = 0
    for r in conn.execute(sql, params):
        sh = r["body_hash"] or title_only_hash(r["title"] or "", r["url"])
        if (not force and not r["failed"] and r["summary"] and r["source_hash"] == sh
                and (prompt_hash is None or r["prompt_hash"] == prompt_hash)):
            continue
        yield Target(r["id"], r["url"], r["title"] or "", r["folder"] or "",
                     r["body_text"] or "", sh)
        count += 1
        if limit is not None and count >= limit:
            break


def targets(conn, **kwargs) -> list[Target]:
    return list(iter_targets(conn, **kwargs))


def count_unchanged(conn: sqlite3.Connection, prompt_hash: str | None = None) -> int:
    return conn.execute(
        "SELECT COUNT(*) c FROM bookmark b "
        "LEFT JOIN content c2   ON c2.bookmark_id = b.id "
        "JOIN enrichment e      ON e.bookmark_id = b.id "
        "WHERE b.indexable=1 AND b.privacy_skipped=0 "
        "  AND COALESCE(e.summary,'')!='' "
        "  AND e.source_hash = COALESCE(c2.body_hash, fm_title_hash(b.title,b.url)) "
        "  AND NOT EXISTS(SELECT 1 FROM enrichment_failure ef WHERE ef.bookmark_id=b.id) "
        + (" AND e.prompt_hash=?" if prompt_hash is not None else ""),
        (prompt_hash,) if prompt_hash is not None else (),
    ).fetchone()["c"]


def store_enrichment(
    conn: sqlite3.Connection,
    target: Target,
    enr: Enrichment,
    *,
    model: str,
    language: str = "",
    prompt_hash: str = "",
) -> int:
    """Write the enrichment, replace the candidate queries, refresh both FTS rows."""
    conn.execute(
        """
        INSERT INTO enrichment(bookmark_id, summary, key_points, entities, topics,
                               utility, content_type, basis, source_hash, model,
                               created_at, ai_title, language, prompt_hash)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(bookmark_id) DO UPDATE SET
            summary=excluded.summary, key_points=excluded.key_points,
            entities=excluded.entities, topics=excluded.topics,
            utility=excluded.utility, content_type=excluded.content_type,
            basis=excluded.basis, source_hash=excluded.source_hash,
            model=excluded.model, created_at=excluded.created_at,
            ai_title=excluded.ai_title, language=excluded.language, prompt_hash=excluded.prompt_hash
        """,
        (target.bookmark_id, enr.summary, jdump(enr.key_points), jdump(enr.entities),
         jdump(enr.topics), enr.utility, enr.content_type,
         "title" if not target.body else "body",
         target.source_hash, model, now(), enr.ai_title, language, prompt_hash),
    )
    conn.execute("DELETE FROM enrichment_failure WHERE bookmark_id=?", (target.bookmark_id,))
    # Candidate queries are regenerated wholesale; keeping stale ones around
    # would leave orphaned vectors pointing at text that no longer exists.
    old = [r["id"] for r in conn.execute(
        "SELECT id FROM intent_query WHERE bookmark_id=?", (target.bookmark_id,))]
    if old:
        conn.execute("DELETE FROM intent_query WHERE bookmark_id=?", (target.bookmark_id,))
        _drop_intent_vectors(conn, old)
    ts = now()
    conn.executemany(
        "INSERT INTO intent_query(bookmark_id, text, kept, created_at) VALUES(?,?,0,?)",
        [(target.bookmark_id, q, ts) for q in enr.intent_queries],
    )
    sync_fts(
        conn, target.bookmark_id,
        title=target.title, ai_title=enr.ai_title, body=target.body, summary=enr.summary,
        topics=enr.topics, entities=enr.entities, key_points=enr.key_points,
    )
    return len(enr.intent_queries)


def _drop_intent_vectors(conn: sqlite3.Connection, intent_ids: Sequence[int]) -> None:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='vec_intent'"
    ).fetchone()
    if not exists:
        return
    conn.executemany("DELETE FROM vec_intent WHERE intent_id=?", [(i,) for i in intent_ids])


async def enrich_all(
    conn: sqlite3.Connection,
    *,
    provider: Provider | None = None,
    settings: Settings | None = None,
    limit: int | None = None,
    force: bool = False,
    ids: Sequence[int] | None = None,
    concurrency: int | None = None,
    progress=None,
    after_commit=None,
) -> EnrichReport:
    s = settings or get_settings()
    prov = provider or get_provider(s)
    concurrency = concurrency if concurrency is not None else s.enrich_concurrency
    language = resolve_summary_language(s.summary_language)
    prompt_hash = summary_prompt_hash(language, s.summary_prompt)
    todo = iter_targets(conn, limit=limit, force=force, ids=ids, body_chars=s.body_truncate_chars,
                        prompt_hash=prompt_hash)
    rep = EnrichReport(skipped_unchanged=count_unchanged(conn, prompt_hash) if ids is None else 0)

    gate = asyncio.Semaphore(concurrency)

    async def attempt(t: Target, budget: int) -> Enrichment:
        prompt = build_user_prompt(
            title=t.title, url=t.url, folder=t.folder,
            body=truncate_head_tail(t.body, budget),
            n_queries=s.intent_generate_n,
            language=language, custom_prompt=s.summary_prompt,
        )
        payload = await prov.chat_json(SYSTEM, prompt)
        result = coerce(payload, max_queries=s.intent_generate_n)
        if not result.ai_title or not result.summary:
            raise EnrichmentInvalid("reply must include a generated title and summary")
        return result

    async def one(t: Target) -> tuple[Target, Enrichment | None, str, bool]:
        async with gate:
            try:
                return t, await attempt(t, s.body_truncate_chars), "", False
            except (ProviderError, EnrichmentInvalid) as first:
                # Nearly every failure observed on a 2,376-page run was the
                # reply running out of room mid-object: the server's per-slot
                # context has to hold prompt *and* completion, and a CJK page
                # at the full truncation budget can spend 4,000+ tokens of it
                # on the prompt alone. A client cannot see the server's slot
                # size, so it cannot compute the right budget -- but halving
                # the body is a cheap, provider-agnostic way to find out. It
                # also helps the read timeouts, since prefill dominates.
                shorter = max(600, s.body_truncate_chars // 2)
                if shorter >= s.body_truncate_chars or not t.body:
                    return t, None, f"{t.url}: {first}", False
                try:
                    return t, await attempt(t, shorter), "", True
                except (ProviderError, EnrichmentInvalid) as second:
                    return t, None, f"{t.url}: {first} | retry@{shorter}: {second}", False

    tasks = []
    try:
        while batch := list(islice(todo, 64)):
            rep.considered += len(batch)
            tasks = [asyncio.create_task(one(t)) for t in batch]
            for coro in asyncio.as_completed(tasks):
                t, enr, err, shortened = await coro
                conn.execute("SAVEPOINT enrichment_item")
                try:
                    if enr is None:
                        from ..admin import safe_error
                        err = safe_error(ProviderError(err), s)
                        rep.failed += 1
                        if len(rep.errors) < 10:
                            rep.errors.append(err)
                        conn.execute("INSERT INTO enrichment_failure(bookmark_id,error,updated_at) VALUES(?,?,?) "
                                     "ON CONFLICT(bookmark_id) DO UPDATE SET error=excluded.error,updated_at=excluded.updated_at",
                                     (t.bookmark_id, err[:1000], now()))
                    else:
                        rep.queries_generated += store_enrichment(
                            conn, t, enr, model=getattr(prov, 'chat_model_in_use', None) or s.chat_model,
                            language=language, prompt_hash=prompt_hash)
                        rep.enriched += 1
                        rep.rescued_by_shorter_body += int(shortened)
                    if progress is not None:
                        progress(t, enr, err)
                except BaseException:
                    conn.execute("ROLLBACK TO enrichment_item")
                    conn.execute("RELEASE enrichment_item")
                    raise
                conn.execute("RELEASE enrichment_item")
                if after_commit is not None:
                    after_commit()

    finally:
        # The owner closes the database/provider as soon as this unwinds.
        # as_completed does not cancel its children when its caller is stopped.
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    conn.commit()
    rep.usage = prov.usage.as_dict()
    return rep
