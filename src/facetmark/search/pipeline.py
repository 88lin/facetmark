"""The query path, end to end.

    understand -> four facets -> RRF -> contextual weight -> metabolism
                -> rerank -> 1-hop expansion (separate group)

Two entry points, because the interface needs two speeds:

``quick_search``  synchronous, lexical only, no model call. This is the first
                  paint: the user has typed three characters and stopped, and
                  something has to be on screen in under 20 ms.
``search``        the full pipeline. One embedding call, optionally one chat
                  call for reranking. Replaces the first paint when it lands.

Progressive rendering is not a performance trick here, it is a correctness
concession: the lexical facet is the only one that is *always* right about
exact strings, and the only one that costs nothing. Showing it first means a
user searching for a remembered phrase gets their answer before the vector
facets have finished having an opinion.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from ..config import Settings, get_settings
from ..db import jload
from ..providers import Provider, get_provider
from .context import ContextSignals, build_context, window_filter
from .decay import cold_bookmark_ids, decay_hits
from .graph import Expansion, expand
from .lexical import lexical_lists
from .rerank import RerankDoc, Reranker, get_reranker, reorder
from .rrf import DEFAULT_K, Fused, rrf
from .understand import QueryUnderstanding, classify, classify_assisted
from .vectors import vector_lists

#: Per-facet fusion weights. Three of the four are 1.0 -- RRF's whole appeal is
#: that it does not need tuning, and weighting facets is the first step back
#: towards the score-normalisation swamp it was chosen to avoid. ``lex_tri`` is
#: the one exception: trigram matching fires on substrings inside unrelated
#: words, so it is damped rather than trusted equally with the word index.
DEFAULT_FACET_WEIGHTS: dict[str, float] = {
    "content": 1.0,
    "intent": 1.0,
    "lex_seg": 1.0,
    "lex_tri": 0.7,
}

VECTOR_FACETS = frozenset({"content", "intent"})
LEXICAL_FACETS = frozenset({"lex_seg", "lex_tri"})
ALL_FACETS = VECTOR_FACETS | LEXICAL_FACETS

SNIPPET_CHARS = 300


@dataclass(frozen=True, slots=True)
class Config:
    """One rung of the ablation ladder (and the shipped default)."""

    name: str
    facets: frozenset[str]
    context: bool = False
    graph: bool = False
    rerank: bool = False
    decay: bool = False

    def as_dict(self) -> dict:
        return {
            "name": self.name, "facets": sorted(self.facets), "context": self.context,
            "graph": self.graph, "rerank": self.rerank, "decay": self.decay,
        }


#: The ablation ladder from the design document. A is what every existing tool
#: does; each rung adds exactly one mechanism so the delta is attributable.
CONFIGS: dict[str, Config] = {
    "A": Config("A", frozenset({"content"})),
    "B": Config("B", frozenset({"content", "lex_seg", "lex_tri"})),
    "C": Config("C", ALL_FACETS),
    "D": Config("D", ALL_FACETS, context=True, graph=True),
    "E": Config("E", ALL_FACETS, context=True, graph=True, rerank=True),
}

#: What ``facetmark search`` and the API actually run: stage E plus metabolism.
#: Metabolism is deliberately outside the ladder -- it is a library-hygiene
#: feature, and leaving it on during ablation would let a cold-start synthetic
#: corpus move the numbers for reasons unrelated to retrieval.
FULL = Config("full", ALL_FACETS, context=True, graph=True, rerank=True, decay=True)


@dataclass(slots=True)
class SearchHit:
    bookmark_id: int
    url: str
    title: str
    score: float
    #: Score before the contextual multiplier and metabolism, i.e. raw RRF.
    base_score: float = 0.0
    facets: list[str] = field(default_factory=list)
    ranks: dict[str, int] = field(default_factory=dict)
    contributions: dict[str, float] = field(default_factory=dict)
    context_boost: float = 1.0
    context_reasons: list[str] = field(default_factory=list)
    cold: bool = False
    folder: str = ""
    domain: str = ""
    date_added: int | None = None
    snippet: str = ""
    utility: str = ""
    content_type: str = ""
    topics: list[str] = field(default_factory=list)
    #: Only set on rows in the expansion group.
    via: int | None = None
    via_kind: str = ""

    def as_dict(self) -> dict:
        d = {
            "bookmark_id": self.bookmark_id, "url": self.url, "title": self.title,
            "score": round(self.score, 6), "base_score": round(self.base_score, 6),
            "facets": self.facets, "ranks": self.ranks,
            "context_boost": round(self.context_boost, 4),
            "context_reasons": self.context_reasons, "cold": self.cold,
            "folder": self.folder, "domain": self.domain, "date_added": self.date_added,
            "snippet": self.snippet, "utility": self.utility,
            "content_type": self.content_type, "topics": self.topics,
        }
        if self.via is not None:
            d["via"] = self.via
            d["via_kind"] = self.via_kind
        return d


@dataclass(slots=True)
class SearchResponse:
    query: str
    hits: list[SearchHit] = field(default_factory=list)
    #: 1-hop neighbours of the top hits. Rendered as its own group, never
    #: interleaved with ``hits``.
    expanded: list[SearchHit] = field(default_factory=list)
    understanding: QueryUnderstanding | None = None
    config: str = "full"
    facet_sizes: dict[str, int] = field(default_factory=dict)
    context: dict | None = None
    #: True when the cold-layer demotion was lifted because nothing hot scored.
    rescued: bool = False
    reranker: str = ""
    took_ms: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "query": self.query,
            "hits": [h.as_dict() for h in self.hits],
            "expanded": [h.as_dict() for h in self.expanded],
            "understanding": self.understanding.as_dict() if self.understanding else None,
            "config": self.config,
            "facet_sizes": self.facet_sizes,
            "context": self.context,
            "rescued": self.rescued,
            "reranker": self.reranker,
            "took_ms": {k: round(v, 2) for k, v in self.took_ms.items()},
        }

    @property
    def ids(self) -> list[int]:
        return [h.bookmark_id for h in self.hits]


# ---------------------------------------------------------------------------
# hydration
# ---------------------------------------------------------------------------

_ROW_SQL = """
SELECT b.id, b.url, b.title, b.folder, b.domain, b.date_added,
       e.summary, e.utility, e.content_type, e.topics,
       substr(c.body_text, 1, 400) AS body_head
FROM bookmark b
LEFT JOIN enrichment e ON e.bookmark_id = b.id
LEFT JOIN content    c ON c.bookmark_id = b.id
WHERE b.id IN ({marks})
"""


def _snippet(summary: str | None, body_head: str | None) -> str:
    text = (summary or "").strip() or (body_head or "").strip()
    text = " ".join(text.split())
    return text[:SNIPPET_CHARS]


def hydrate(conn: sqlite3.Connection, ids: Sequence[int]) -> dict[int, dict]:
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    rows = conn.execute(_ROW_SQL.format(marks=marks), list(ids)).fetchall()
    return {int(r["id"]): dict(r) for r in rows}


def _to_hit(row: Mapping, fused: Fused | None = None) -> SearchHit:
    return SearchHit(
        bookmark_id=int(row["id"]),
        url=str(row["url"]),
        title=str(row["title"] or ""),
        score=fused.score if fused else 0.0,
        base_score=fused.score if fused else 0.0,
        facets=fused.facets if fused else [],
        ranks=dict(fused.ranks) if fused else {},
        contributions=dict(fused.contributions) if fused else {},
        folder=str(row["folder"] or ""),
        domain=str(row["domain"] or ""),
        date_added=int(row["date_added"]) if row["date_added"] else None,
        snippet=_snippet(row["summary"], row["body_head"]),
        utility=str(row["utility"] or ""),
        content_type=str(row["content_type"] or ""),
        topics=jload(row["topics"], []),
    )


# ---------------------------------------------------------------------------
# fast path
# ---------------------------------------------------------------------------


def quick_search(
    conn: sqlite3.Connection, query: str, *, limit: int = 20, k: int = DEFAULT_K
) -> SearchResponse:
    """Lexical-only first paint. Synchronous, no model call, no network."""
    t0 = time.perf_counter()
    u = classify(query)
    lists = lexical_lists(conn, query, limit=max(limit * 3, 30))
    fused = rrf(lists, k=k, weights=DEFAULT_FACET_WEIGHTS, limit=limit)
    rows = hydrate(conn, [f.doc_id for f in fused])
    hits = [_to_hit(rows[f.doc_id], f) for f in fused if f.doc_id in rows]
    return SearchResponse(
        query=query, hits=hits, understanding=u, config="quick",
        facet_sizes={k2: len(v) for k2, v in lists.items()},
        took_ms={"total": (time.perf_counter() - t0) * 1000},
    )


# ---------------------------------------------------------------------------
# full path
# ---------------------------------------------------------------------------


async def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    config: Config = FULL,
    provider: Provider | None = None,
    settings: Settings | None = None,
    reranker: Reranker | None = None,
    understanding: QueryUnderstanding | None = None,
    assist: bool = False,
    now_ts: int | None = None,
    expand_limit: int = 8,
) -> SearchResponse:
    """Run the full retrieval pipeline for one query."""
    s = settings or get_settings()
    prov = provider or get_provider(s)
    timings: dict[str, float] = {}
    t_start = time.perf_counter()

    def mark(name: str, t0: float) -> None:
        timings[name] = (time.perf_counter() - t0) * 1000

    # --- 1. understanding -------------------------------------------------
    t0 = time.perf_counter()
    if understanding is None:
        understanding = (
            await classify_assisted(query, provider=prov, now_ts=now_ts)
            if assist
            else classify(query, now_ts=now_ts)
        )
    mark("understand", t0)

    per_facet = max(s.candidates_per_facet, limit)

    # --- 2. facets --------------------------------------------------------
    t0 = time.perf_counter()
    lists: dict[str, list[int]] = {}
    if config.facets & LEXICAL_FACETS:
        for name, ids in lexical_lists(conn, query, limit=per_facet).items():
            if name in config.facets:
                lists[name] = ids
    mark("lexical", t0)

    t0 = time.perf_counter()
    if config.facets & VECTOR_FACETS:
        vlists, _vec = await vector_lists(
            conn, query, provider=prov, settings=s, limit=per_facet,
            want_content="content" in config.facets,
            want_intent="intent" in config.facets,
        )
        lists.update(vlists)
    mark("vectors", t0)

    # --- 3. fusion --------------------------------------------------------
    t0 = time.perf_counter()
    fused = rrf(lists, k=s.rrf_k, weights=DEFAULT_FACET_WEIGHTS)
    mark("fuse", t0)

    # A purely episodic query ("上个月存的那些") has no topic for any facet to
    # match. The window *is* the query, so it becomes the candidate set.
    if not fused and understanding.time_window is not None:
        ids = window_filter(conn, understanding.time_window)[: per_facet]
        fused = rrf({"episodic_window": ids}, k=s.rrf_k)
        lists["episodic_window"] = ids

    ctx: ContextSignals | None = None
    if config.context and fused:
        t0 = time.perf_counter()
        head = [f.doc_id for f in fused[:200]]
        ctx = build_context(
            conn,
            anchors=[f.doc_id for f in fused],
            candidates=head,
            query_window=understanding.time_window,
            episodic_confidence=understanding.episodic_confidence,
        )
        for f in fused:
            f.score *= ctx.boost(f.doc_id)
        fused = sorted(fused, key=lambda f: (-f.score, f.doc_id))
        mark("context", t0)

    # --- 4. metabolism ----------------------------------------------------
    rescued = False
    cold: set[int] = set()
    if config.decay and fused:
        t0 = time.perf_counter()
        cold = cold_bookmark_ids(
            conn, age_days=s.decay_age_days,
            ids=[f.doc_id for f in fused], now_ts=now_ts,
        )
        fused, outcome = decay_hits(
            fused, cold, factor=s.decay_factor, rescue_threshold=s.decay_rescue_threshold
        )
        rescued = outcome.rescued
        mark("decay", t0)

    page = fused[:limit]
    rows = hydrate(conn, [f.doc_id for f in page])
    hits: list[SearchHit] = []
    for f in page:
        row = rows.get(f.doc_id)
        if row is None:
            continue
        hit = _to_hit(row, f)
        hit.cold = f.doc_id in cold
        if ctx is not None:
            hit.context_boost = ctx.boost(f.doc_id)
            hit.context_reasons = ctx.reasons(f.doc_id)
            hit.base_score = f.score / hit.context_boost if hit.context_boost else f.score
        hits.append(hit)

    # --- 5. rerank --------------------------------------------------------
    rr_name = ""
    if config.rerank and hits:
        t0 = time.perf_counter()
        rr = reranker or get_reranker(s, prov)
        rr_name = rr.name
        docs = [RerankDoc(h.bookmark_id, h.title, h.snippet) for h in hits]
        scores = await rr.score(query, docs)
        if len(scores) == len(hits):
            hits = reorder(hits, scores, depth=len(hits))
        mark("rerank", t0)

    # --- 6. one hop out, as its own group ---------------------------------
    expansions: list[Expansion] = []
    if config.graph and hits:
        t0 = time.perf_counter()
        expansions = expand(
            conn,
            [(h.bookmark_id, h.score) for h in hits],
            factor=s.graph_expand_factor,
            limit=expand_limit,
            exclude=[f.doc_id for f in fused],
        )
        mark("expand", t0)

    exp_rows = hydrate(conn, [e.doc_id for e in expansions])
    expanded: list[SearchHit] = []
    for e in expansions:
        row = exp_rows.get(e.doc_id)
        if row is None:
            continue
        h = _to_hit(row)
        h.score = e.score
        h.base_score = e.score
        h.via = e.via
        h.via_kind = e.kind
        expanded.append(h)

    timings["total"] = (time.perf_counter() - t_start) * 1000
    return SearchResponse(
        query=query, hits=hits, expanded=expanded, understanding=understanding,
        config=config.name, facet_sizes={k: len(v) for k, v in lists.items()},
        context=ctx.as_dict() if ctx else None, rescued=rescued,
        reranker=rr_name, took_ms=timings,
    )
