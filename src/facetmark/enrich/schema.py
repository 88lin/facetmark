"""Coerce whatever the model returned into the shape the database expects.

Validation here is forgiving on purpose. A model that returns a string where an
array was asked for, or that invents a ``category`` field, has still done the
useful part of the work; rejecting the whole row would cost a paid call to get
back something equivalent. What is *not* forgiven is a missing summary and
missing queries at the same time -- that is a failed call, not a sloppy one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SUMMARY_MAX = 200

UTILITIES = frozenset({
    "reference", "tutorial", "tool", "news", "opinion", "documentation",
    "paper", "dataset", "product", "entertainment", "other",
})
CONTENT_TYPES = frozenset({
    "article", "docs", "repo", "video", "thread", "pdf", "slides",
    "landing", "forum", "other",
})

_WS = re.compile(r"\s+")


class EnrichmentInvalid(ValueError):
    """The reply had neither a summary nor any usable query."""


def _as_list(value: object, *, limit: int) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [p.strip() for p in re.split(r"[\n;]|(?<=[^\d]),", value)]
        items = [p for p in parts if p]
    elif isinstance(value, dict):
        items = [str(v).strip() for v in value.values()]
    elif isinstance(value, (list, tuple, set)):
        items = []
        for v in value:
            if isinstance(v, dict):
                # {"name": "...", "type": "..."} is a common model habit.
                v = v.get("name") or v.get("text") or v.get("value") or next(iter(v.values()), "")
            items.append(_WS.sub(" ", str(v)).strip())
    else:
        items = [str(value).strip()]
    out: list[str] = []
    seen: set[str] = set()
    for it in items:
        key = it.casefold()
        if it and key not in seen:
            seen.add(key)
            out.append(it)
    return out[:limit]


def _as_text(value: object, *, limit: int) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = " ".join(str(v) for v in value)
    s = _WS.sub(" ", str(value)).strip()
    return s[:limit]


def _as_enum(value: object, allowed: frozenset[str], default: str) -> str:
    s = _as_text(value, limit=40).lower().strip(" .")
    if s in allowed:
        return s
    # Models like to answer "tutorial/guide" or "Reference material".
    for token in re.split(r"[\s/,|-]+", s):
        if token in allowed:
            return token
    return default


@dataclass(slots=True)
class Enrichment:
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    utility: str = "other"
    content_type: str = "other"
    intent_queries: list[str] = field(default_factory=list)

    def as_row(self) -> dict:
        return {
            "summary": self.summary,
            "key_points": self.key_points,
            "entities": self.entities,
            "topics": self.topics,
            "utility": self.utility,
            "content_type": self.content_type,
        }


_QUERY_KEYS = ("intent_queries", "queries", "intent", "questions", "search_queries")


def coerce(payload: dict, *, max_queries: int = 8) -> Enrichment:
    if not isinstance(payload, dict):
        raise EnrichmentInvalid(f"expected an object, got {type(payload).__name__}")

    raw_q: object = None
    for k in _QUERY_KEYS:
        if payload.get(k):
            raw_q = payload[k]
            break

    e = Enrichment(
        summary=_as_text(payload.get("summary") or payload.get("abstract"), limit=SUMMARY_MAX),
        key_points=_as_list(payload.get("key_points") or payload.get("keypoints"), limit=6),
        entities=_as_list(payload.get("entities"), limit=12),
        topics=_as_list(payload.get("topics") or payload.get("tags"), limit=8),
        utility=_as_enum(payload.get("utility"), UTILITIES, "other"),
        content_type=_as_enum(payload.get("content_type") or payload.get("type"),
                              CONTENT_TYPES, "other"),
        intent_queries=[q for q in _as_list(raw_q, limit=max_queries * 2) if len(q) >= 3],
    )
    e.intent_queries = e.intent_queries[:max_queries]
    if not e.summary and not e.intent_queries:
        raise EnrichmentInvalid("reply carried neither a summary nor a query")
    return e
