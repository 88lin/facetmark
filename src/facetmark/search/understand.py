"""Query understanding: what kind of forgetting is this query trying to undo?

Four labels, and they **coexist** -- ``"docker compose" 去年配的那个`` is
lexical *and* episodic at once, and forcing a single label would throw away
half the query.

``navigational``  the user knows the destination: a domain, a product name.
``lexical``       the user remembers exact surface text: a quoted phrase, an
                  identifier, a filename.
``semantic``      the user remembers what the page was about.
``episodic``      the user remembers *when* or *alongside what* they saved it.

Rules first, model second
-------------------------
Every rule below is a zero-latency, zero-cost, deterministic string test. They
are not a fallback for the model; they are the primary path, because the
signals they detect (quotes, ``snake_case``, ``去年``) are unambiguous and a
model round-trip to re-derive them would add 300-800 ms to every keystroke's
worth of search. The model is only consulted when *no* rule fires, and even
then only if a non-mock provider is configured -- the offline demo must never
block on a network call.

Time expressions split in two, and the split matters
-----------------------------------------------------
*Absolute or relative* expressions (``去年``, ``上个月``, ``in March``) resolve
to a concrete window right here. *Content-anchored* ones (``配 Docker 那阵子``)
cannot: there is no calendar in the phrase, only a topic. Those set
``episodic`` with no window, and :mod:`facetmark.search.context` derives the
window from where the topic's own matches actually cluster in time.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# lexical-intent rules
# --------------------------------------------------------------------------

_QUOTED = re.compile(r'["\u201c\u300c\u300e\'](.{2,}?)["\u201d\u300d\u300f\']')
#: camelCase, PascalCase followed by lowercase, snake_case, kebab-in-code,
#: dotted paths, ALL_CAPS >= 3. Deliberately not matching a plain capitalised
#: English word, which would label half of all queries as lexical.
_IDENTIFIER = re.compile(
    r"(?:[a-z]+[A-Z][a-zA-Z]*)"          # camelCase
    r"|(?:[A-Za-z]+_[A-Za-z0-9_]+)"      # snake_case
    r"|(?:\b[A-Z]{3,}\b)"                # ALLCAPS
    r"|(?:\b\w+\.(?:py|js|ts|tsx|md|json|yaml|yml|toml|rs|go|java|c|cpp|h|sh)\b)"
)
_URLISH = re.compile(r"https?://\S+")
_DOMAINISH = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|cn|org|net|io|dev|ai|me|co|edu|gov|app|xyz|top|info|so|sh|fm|tv)\b",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------
# time expressions
# --------------------------------------------------------------------------

_DAY = 86400
_MONTH = 30 * _DAY
_YEAR = 365 * _DAY

#: Vague episodic markers: they prove the user is reaching for an episode, but
#: carry no calendar information at all. These trigger anchor-then-window.
_VAGUE_EPISODIC = (
    "那阵子", "那段时间", "那会儿", "那时候", "当时", "刚开始", "最初",
    "一开始", "同一批", "同时期", "前后", "顺手存的", "一起存",
    "back when", "around the time", "at the time", "same batch",
    "along with", "when i was",
)

#: (pattern, seconds_ago_start, seconds_ago_end). The window is
#: ``[now - start, now - end]``.
_RELATIVE: tuple[tuple[str, int, int], ...] = (
    (r"今天|today", 1 * _DAY, 0),
    (r"昨天|yesterday", 2 * _DAY, 0),
    (r"前天", 3 * _DAY, 0),
    (r"这几天|前几天|最近几天|past few days|last few days", 7 * _DAY, 0),
    (r"本周|这周|这个星期|this week", 7 * _DAY, 0),
    (r"上周|上个星期|last week", 14 * _DAY, 5 * _DAY),
    (r"这个月|本月|this month", _MONTH, 0),
    (r"上个月|上月|last month", 2 * _MONTH, int(0.5 * _MONTH)),
    (r"最近|recently|lately", 3 * _MONTH, 0),
    (r"今年|this year", _YEAR, 0),
    (r"去年|last year", 2 * _YEAR, int(0.7 * _YEAR)),
    (r"前年", 3 * _YEAR, int(1.7 * _YEAR)),
)

_N_AGO = re.compile(
    r"(\d{1,3})\s*(?:个)?\s*(天|日|周|星期|月|年|day|days|week|weeks|month|months|year|years)\s*(?:前|ago)"
)
_UNIT_SECONDS = {
    "天": _DAY, "日": _DAY, "day": _DAY, "days": _DAY,
    "周": 7 * _DAY, "星期": 7 * _DAY, "week": 7 * _DAY, "weeks": 7 * _DAY,
    "月": _MONTH, "month": _MONTH, "months": _MONTH,
    "年": _YEAR, "year": _YEAR, "years": _YEAR,
}
_ABS_YEAR = re.compile(r"\b(19[89]\d|20[0-4]\d)\s*年?\b")


@dataclass(slots=True)
class QueryUnderstanding:
    """What we believe the query is, and why."""

    query: str
    labels: set[str] = field(default_factory=set)
    #: Names of the rules that fired. Kept so a user can be shown *why* their
    #: search was treated as episodic, instead of the system silently
    #: reinterpreting what they typed.
    rule_hits: list[str] = field(default_factory=list)
    #: Absolute window in unix seconds, when the query itself pinned one down.
    time_window: tuple[int, int] | None = None
    #: 0.0-1.0. Drives the episodic boost interpolation (1.0 -> 1.5x).
    episodic_confidence: float = 0.0
    #: Exact phrases the user quoted; the lexical facet gets these verbatim.
    phrases: list[str] = field(default_factory=list)
    source: str = "rules"

    @property
    def is_episodic(self) -> bool:
        return "episodic" in self.labels

    @property
    def episodic_boost(self) -> float:
        """1.0 (no episodic signal) .. 1.5 (a dated, unambiguous episode)."""
        return 1.0 + 0.5 * self.episodic_confidence

    def as_dict(self) -> dict:
        return {
            "query": self.query,
            "labels": sorted(self.labels),
            "rule_hits": list(self.rule_hits),
            "time_window": list(self.time_window) if self.time_window else None,
            "episodic_confidence": round(self.episodic_confidence, 3),
            "phrases": list(self.phrases),
            "source": self.source,
        }


def _resolve_time(query: str, now_ts: int) -> tuple[tuple[int, int] | None, str | None]:
    lowered = query.lower()

    m = _N_AGO.search(lowered)
    if m:
        n = int(m.group(1))
        unit = _UNIT_SECONDS[m.group(2)]
        centre = now_ts - n * unit
        half = max(unit // 2, _DAY)
        return (centre - half, min(centre + half, now_ts)), "n_ago"

    for pattern, start_ago, end_ago in _RELATIVE:
        if re.search(pattern, lowered):
            return (now_ts - start_ago, now_ts - end_ago), "relative"

    m = _ABS_YEAR.search(query)
    if m:
        year = int(m.group(1))
        # struct_time -> epoch in UTC, without pulling in a tz database.
        import calendar

        start = calendar.timegm((year, 1, 1, 0, 0, 0, 0, 1, 0))
        end = calendar.timegm((year + 1, 1, 1, 0, 0, 0, 0, 1, 0))
        return (start, end), "absolute_year"

    return None, None


def classify(query: str, *, now_ts: int | None = None) -> QueryUnderstanding:
    """Label a query using rules only. Never touches the network."""
    now_ts = int(time.time()) if now_ts is None else int(now_ts)
    u = QueryUnderstanding(query=query)
    text = query.strip()
    if not text:
        return u

    for m in _QUOTED.finditer(text):
        u.phrases.append(m.group(1).strip())
    if u.phrases:
        u.labels.add("lexical")
        u.rule_hits.append("quoted")

    if _IDENTIFIER.search(text):
        u.labels.add("lexical")
        u.rule_hits.append("identifier")

    if _URLISH.search(text):
        u.labels.update({"navigational", "lexical"})
        u.rule_hits.append("url")
    elif _DOMAINISH.search(text):
        u.labels.add("navigational")
        u.rule_hits.append("domain")

    window, kind = _resolve_time(text, now_ts)
    if window is not None:
        u.labels.add("episodic")
        u.time_window = window
        u.episodic_confidence = 1.0
        u.rule_hits.append(f"time:{kind}")

    lowered = text.lower()
    if any(marker in lowered for marker in _VAGUE_EPISODIC):
        u.labels.add("episodic")
        u.rule_hits.append("episodic_marker")
        # A vague marker is weaker evidence than a resolvable date, and must
        # not overwrite a confidence that a date already earned.
        u.episodic_confidence = max(u.episodic_confidence, 0.6)

    # A query is semantic unless it is *purely* a destination lookup. Even a
    # quoted phrase usually still describes a topic worth matching on meaning.
    if u.labels != {"navigational"}:
        u.labels.add("semantic")
    if not u.labels:
        u.labels.add("semantic")
    return u


# --------------------------------------------------------------------------
# optional model-assisted path
# --------------------------------------------------------------------------

_LLM_SYSTEM = (
    "You label bookmark search queries. Reply with JSON only."
)
_LLM_TEMPLATE = """Label this bookmark search query.

Query: {query}

Return JSON:
{{"labels": ["navigational"|"lexical"|"semantic"|"episodic", ...],
  "episodic_confidence": 0.0-1.0,
  "rewritten": "a fuller phrasing of the same intent, same language as the query"}}

Rules:
- "episodic" only if the query refers to WHEN it was saved or WHAT ELSE was
  saved around it. A topic alone is not episodic.
- "navigational" only if a specific site or product is named.
- Always include at least one label."""

_CACHE: dict[str, QueryUnderstanding] = {}
_CACHE_MAX = 512


def _cache_key(query: str) -> str:
    return hashlib.blake2b(query.strip().lower().encode("utf-8"), digest_size=12).hexdigest()


async def classify_assisted(
    query: str, *, provider=None, now_ts: int | None = None
) -> QueryUnderstanding:
    """Rules, then one cached model call only if no rule fired.

    Returns the rule result unchanged when any rule matched, when no provider
    is configured, or when the model call fails -- the search must degrade to
    "slightly less well understood", never to "unavailable".
    """
    u = classify(query, now_ts=now_ts)
    if u.rule_hits or provider is None:
        return u

    key = _cache_key(query)
    cached = _CACHE.get(key)
    if cached is not None:
        out = QueryUnderstanding(
            query=query, labels=set(cached.labels), rule_hits=list(cached.rule_hits),
            time_window=cached.time_window, episodic_confidence=cached.episodic_confidence,
            phrases=list(cached.phrases), source="cache",
        )
        return out

    try:
        payload = await provider.chat_json(
            system=_LLM_SYSTEM, user=_LLM_TEMPLATE.format(query=query)
        )
    except Exception:
        return u

    labels = {
        str(x).strip().lower()
        for x in (payload.get("labels") or [])
        if str(x).strip().lower() in {"navigational", "lexical", "semantic", "episodic"}
    }
    if labels:
        u.labels = labels
        u.rule_hits.append("llm")
        u.source = "llm"
    try:
        conf = float(payload.get("episodic_confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    if "episodic" in u.labels:
        u.episodic_confidence = max(u.episodic_confidence, min(max(conf, 0.0), 1.0))
    if not u.labels:
        u.labels.add("semantic")

    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = u
    return u


def clear_cache() -> None:
    _CACHE.clear()
