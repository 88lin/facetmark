"""The query language: field filters, negation, phrases, alternation and sort.

Ported from hister's query language (github.com/asciimoo/hister,
``server/indexer/querybuilder``), adapted to facetmark's bookmark model and to
a pipeline whose ranking is measured rather than tuned.

The design constraint that shaped this port: **a query without syntax must
produce byte-identical behaviour to the pre-language pipeline.** The parser
therefore only recognises a token as syntax when it could not be plain text --
``field:`` is only a filter when ``field`` is one of the known names, so
``note: something`` and ``https://example.com`` stay ordinary terms, and a
hyphen inside a word is never a negation. Everything the language strips from
the free text (filters, sort directives) is removed from the string the facets
see; everything it leaves stays verbatim. The regression tests pin the
no-syntax path against the old output.

Ranking discipline: the language is a *filter*, not a ranker. Filters cut the
candidate pool after fusion and never move a surviving document's score, and
``sort:`` re-orders the pool only when the query asks for it. That is what
keeps this outside the "retrieval-quality change needs a protocol" rule in
CONTRIBUTING.md: the default ranking of an unfiltered query is untouched, and
a filtered query is a different question rather than a different answer.

Supported syntax (hister-compatible where the fields exist)::

    title:encryption                  field filter, substring match
    domain:github.com  site:github.com   site: is an alias of domain:
    url:*/docs/*                      * wildcards on url/title/domain/folder
    text:"GDPR compliance"            body-text substring
    folder:study topic:postgres       facetmark-specific fields
    tag:work                          exact element of the user's own tags
    lang:zh opened:10..               language filter, open-count range
    added:>90d added:>=2026-04-01     relative age or absolute date
    before:2026-05-01 after:2024-01-01   absolute-date aliases for added:
    -facebook -domain:facebook.com    negation of a term or a field
    -"social media"                   negated phrase
    "privacy policy"                  exact phrase (lexical facet)
    (security|privacy)                alternation, expands to OR terms
    sort:date sort:-date sort:domain  ordering directive

Relative durations compare against the *age* of the bookmark (``added:>90d``
means saved more than 90 days ago), absolute dates compare against the
timestamp itself -- both exactly as hister's query-language guide defines them.
"""

from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass, field

from ..db import in_chunks

#: Canonical field names. ``site`` is an alias of ``domain``; ``before`` and
#: ``after`` are absolute-date aliases of ``added``. A ``field:`` token whose
#: name is not in this table is plain text -- that is the compatibility rule.
FIELDS: dict[str, str] = {
    "domain": "domain",
    "site": "domain",
    "url": "url",
    "title": "title",
    "text": "text",
    "folder": "folder",
    "tag": "tag",
    "topic": "topic",
    "lang": "lang",
    "added": "added",
    "saved": "added",
    "before": "added",
    "after": "added",
    "opened": "opened",
}

#: Values ``sort:`` understands. ``date`` and ``added`` are the same key.
SORTS: dict[str, str] = {
    "relevance": "relevance",
    "date": "date",
    "added": "date",
    "domain": "domain",
    "title": "title",
    "url": "url",
}

#: One relative unit in seconds. Weeks are 7 days; a year is 365 days, which
#: is what "added:>1y" has to mean on a unix-seconds column that has no
#: calendar. Ranges that need calendar arithmetic (months) are absolute dates.
_DURATION_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000}

_REL_RE = re.compile(r"^([<>]=?)(\d+(?:\.\d+)?)([smhdwy])$", re.IGNORECASE)
_ABS_RE = re.compile(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$")
_RANGE_RE = re.compile(r"^(\S+)\.\.(\S*)$")

# A quoted phrase: from the opening quote to the next quote or end of string.
_QUOTE_RE = re.compile(r'"([^"]*)"')

_WILDCARD_RE = re.compile(r"[*]")


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Term:
    """One piece of free text the facets should match.

    ``raw`` keeps the quotes for the lexical path (FTS5 phrase); ``plain`` is
    what the embedding path and the UI should see.
    """

    raw: str
    plain: str
    negated: bool = False
    is_phrase: bool = False


@dataclass(frozen=True, slots=True)
class FieldFilter:
    field: str          # canonical (site->domain, before/after->added)
    value: str          # as typed; may carry * wildcards, | alternation, date ops
    negate: bool
    alias: str = ""     # the name the user actually typed, for the echo


@dataclass(slots=True)
class ParsedQuery:
    """A query split into ``what to match`` and ``what to require``."""

    terms: list[Term] = field(default_factory=list)
    filters: list[FieldFilter] = field(default_factory=list)
    sort: str = ""
    #: Filters whose value did not parse are kept here verbatim so they can be
    #: reported back rather than silently swallowed.
    ignored: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Free text for the lexical facet; phrases keep their quotes."""
        return " ".join(t.raw for t in self.terms if not t.negated)

    @property
    def plain_text(self) -> str:
        """Free text with the syntax stripped -- what an embedding should see."""
        return " ".join(t.plain for t in self.terms if not t.negated)

    @property
    def has_filters(self) -> bool:
        return bool(self.filters) or any(t.negated for t in self.terms)

    @property
    def has_syntax(self) -> bool:
        return bool(self.filters) or bool(self.sort) or any(t.negated for t in self.terms)

    def echo(self) -> dict:
        """What the response should say about the parsed query."""
        out: dict = {}
        if self.filters:
            out["fields"] = [
                {"field": f.field, "value": f.value, "negate": f.negate} for f in self.filters
            ]
        if any(t.negated for t in self.terms):
            out["exclude"] = [t.plain for t in self.terms if t.negated]
        if self.sort:
            out["sort"] = self.sort
        if self.ignored:
            out["ignored"] = self.ignored
        return out


def _split_value(value: str) -> list[str]:
    """Alternation parts: ``a|b`` -> ``["a", "b"]``; parens already stripped."""
    parts = [p for p in (s.strip().strip('"') for s in value.split("|")) if p]
    return parts or [value]


def parse_query(query: str, *, now: float | None = None) -> ParsedQuery:
    """Split a raw query into terms, filters and a sort directive.

    Tokenisation keeps quoted spans together, so ``"privacy policy"`` is one
    token and ``domain:"example.com"`` is one filter. Recognition is
    conservative: only known field names bind ``:``, and a leading ``-`` is a
    negation only when something follows it.
    """
    q = (query or "").strip()
    parsed = ParsedQuery()
    if not q:
        return parsed

    now = time.time() if now is None else now

    # Walk the string splitting on whitespace, but a quote opens a span that
    # runs to the next quote (or end of input). Unclosed quotes are content,
    # not an error: the user is still typing.
    tokens: list[tuple[str, bool]] = []   # (token, was_quoted)
    i = 0
    while i < len(q):
        while i < len(q) and q[i].isspace():
            i += 1
        if i >= len(q):
            break
        if q[i] == '"':
            m = _QUOTE_RE.match(q, i)
            if m and m.end() < len(q) and not q[m.end()].isspace() and q[i : m.end()].count('"') == 2:
                # A quoted span glued to a following word ("foo"bar) is one
                # token by hister's lexer too; keep them joined.
                j = m.end()
                while j < len(q) and not q[j].isspace():
                    j += 1
                tokens.append((q[i:j], True))
                i = j
            elif m:
                tokens.append((m.group(0), True))
                i = m.end()
            else:
                # Unterminated quote: treat the rest as one quoted token.
                tokens.append((q[i:], True))
                i = len(q)
        else:
            # A word, with hister's rule that a quote *inside* a word keeps the
            # word together: ``text:"GDPR compliance"`` is one token, because
            # the quote opened a span that whitespace does not close.
            j = i
            inside = False
            while j < len(q):
                ch = q[j]
                if ch == '"':
                    inside = not inside
                elif ch.isspace() and not inside:
                    break
                j += 1
            tokens.append((q[i:j], False))
            i = j

    for raw, quoted in tokens:
        negated = False
        body = raw
        if not quoted and body.startswith("-") and len(body) > 1:
            negated = True
            body = body[1:]
        # A quoted token may itself start with a "-" glued inside the quotes.
        if quoted and body.startswith('-') and len(body) > 2 and body.endswith('"'):
            inner = body[1:-1]
            if inner.startswith("-") and len(inner) > 1:
                negated = True
                inner = inner[1:]
                body = f'"{inner}"'

        if quoted:
            inner = body[1:-1] if body.startswith('"') and body.endswith('"') else body
            # `field:"value"` / `-field:"value"`: a filter with a quoted value.
            fm = re.match(r"^([A-Za-z_]+):\"(.*)\"$", body) if ":" in body else None
            if fm and fm.group(1).lower() in FIELDS:
                parsed.filters.append(
                    FieldFilter(FIELDS[fm.group(1).lower()], fm.group(2), negated,
                                alias=fm.group(1).lower())
                )
                continue
            # A filter with a quoted value and trailing text glued on is rare
            # enough to fall through as a phrase.
            if negated or inner:
                parsed.terms.append(Term(raw=f'"{inner}"', plain=inner, negated=negated,
                                         is_phrase=True))
            continue

        # Unquoted token: field filter, sort directive, or free text.
        if ":" in body:
            name, _, value = body.partition(":")
            low = name.lower()
            # `-field:"value"` keeps its quotes through tokenisation; a
            # value that is one quoted string is that string.
            if value.startswith('"') and value.endswith('"') and len(value) >= 2:
                value = value[1:-1]
            if low == "sort" and value:
                key = value.lower()
                if key in SORTS:
                    parsed.sort = SORTS[key]
                    continue
                if key.startswith("-") and key[1:] in SORTS:
                    parsed.sort = "-" + SORTS[key[1:]]
                    continue
                # An unknown sort value is a mistake the caller should see, not
                # a term to silently index.
                parsed.ignored.append(body)
                continue
            if low in FIELDS and value:
                # Strip one layer of parens from an alternation value.
                v = value
                if v.startswith("(") and v.endswith(")"):
                    v = v[1:-1]
                parsed.filters.append(FieldFilter(FIELDS[low], v, negated, alias=low))
                continue

        # Alternation: ``(...|...)`` or a bare ``a|b`` is one term per part.
        if body.startswith("(") and body.endswith(")"):
            body = body[1:-1]
        if "|" in body and not _WILDCARD_RE.search(body):
            parts = _split_value(body)
            if negated:
                for p in parts:
                    parsed.terms.append(Term(raw=p, plain=p, negated=True))
            else:
                # The lexical facet ORs terms anyway, so expanding alternation
                # into separate terms is the same query with one code path.
                for p in parts:
                    parsed.terms.append(Term(raw=p, plain=p))
            continue

        if body:
            # ``-"a phrase"`` arrives here (the '-' stopped the quoted path);
            # recognise the phrase so negation matches it as one unit.
            is_phrase = body.startswith('"') and body.endswith('"') and len(body) >= 2
            plain = body[1:-1] if is_phrase else body
            parsed.terms.append(Term(raw=body, plain=plain, negated=negated,
                                     is_phrase=is_phrase))

    # ``before:``/``after:`` are sugar: fold them into an op on ``added``.
    folded: list[FieldFilter] = []
    for f in parsed.filters:
        if f.alias in ("before", "after") and not f.negate \
                and not _REL_RE.match(f.value) and not f.value.startswith(("<", ">")):
            op = "<" if f.alias == "before" else ">="
            folded.append(FieldFilter("added", op + f.value, False, alias=f.alias))
        else:
            folded.append(f)
    parsed.filters = folded
    return parsed


# ---------------------------------------------------------------------------
# date values
# ---------------------------------------------------------------------------


def _abs_ts(y: int, m: int, d: int) -> int | None:
    import calendar
    import datetime as _dt

    try:
        return int(calendar.timegm(_dt.datetime(y, m, d, tzinfo=_dt.timezone.utc).timetuple()))
    except ValueError:
        return None


def resolve_date_value(value: str, *, now: float) -> tuple[str, int] | None:
    """An *operator* date value -> ``(comparison, unix_seconds)``.

    Handles ``>90d``, ``<=2w``, ``>=2026-04-01``, ``<2026-05-01``. Relative
    values compare against *age* (``>90d`` = saved more than 90 days ago),
    absolute values against the timestamp; both are rewritten here onto a
    single comparison against ``date_added`` so the caller never sees the
    difference. Returns ``None`` for bare values and unparseable text.
    """
    v = value.strip()
    if not v:
        return None
    op = ""
    if v[:1] in "<>":
        op, v = v[:1], v[1:]
        if v[:1] == "=":
            op, v = op + "=", v[1:]
    if not op:
        return None

    m = _REL_RE.match(op + v)
    if m:
        # Relative: comparison is against age, so invert onto the timestamp.
        n, unit = float(m.group(2)), m.group(3).lower()
        ts = int(now - n * _DURATION_UNITS[unit])
        invert = {">": "<", ">=": "<=", "<": ">", "<=": ">="}
        return (invert[m.group(1)], ts)

    am = _ABS_RE.match(v)
    if am is None:
        return None
    y, mo, d = int(am.group(1)), int(am.group(2) or 1), int(am.group(3) or 1)
    ts = _abs_ts(y, mo, d)
    if ts is None:
        return None
    return (op, ts)


def resolve_date_span(value: str) -> tuple[int, int] | None:
    """A *bare* absolute value -> the ``(lo, hi)`` seconds it names.

    ``2026-04-01`` is that day, ``2026-04`` that month, ``2026`` that year.
    Returns ``None`` for anything else -- including bare relative durations,
    which the grammar does not define and which degrade to ignored tokens
    rather than being guessed at.
    """
    am = _ABS_RE.match(value.strip())
    if am is None:
        return None
    y, mo, d = int(am.group(1)), int(am.group(2) or 1), int(am.group(3) or 1)
    lo = _abs_ts(y, mo, d)
    if lo is None:
        return None
    if am.group(3):
        return (lo, _day_after(y, mo, d))
    if am.group(2):
        return (lo, _month_after(y, mo))
    return (lo, _month_after(y, 12))


def _day_after(y: int, m: int, d: int) -> int:
    import datetime as _dt

    return int((_dt.datetime(y, m, d, tzinfo=_dt.timezone.utc) + _dt.timedelta(days=1)).timestamp())


def _month_after(y: int, m: int) -> int:
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    return _abs_ts(y2, m2, 1) or 0


def _date_range(value: str, *, now: float) -> tuple[int, int] | None:
    """``a..b`` -> ``(lo, hi)`` unix seconds, or None when unparseable.

    Each side may be a bare absolute value (``2026-04-01``, ``2026-04``) or an
    operator form (``>=2026-04-01``, ``<7d``); an empty right side means "no
    upper bound".
    """
    m = _RANGE_RE.match(value)
    if not m:
        return None

    def bound(side: str) -> int | None:
        if not side:
            return 2**62
        span = resolve_date_span(side)
        if span is not None:
            return span[0]
        op = resolve_date_value(side, now=now)
        return op[1] if op else None

    lo = bound(m.group(1))
    hi = bound(m.group(2))
    if lo is None:
        return None
    return (lo, hi if hi is not None else 2**62)


# ---------------------------------------------------------------------------
# SQL resolution
# ---------------------------------------------------------------------------


def _like(value: str, *, wrap: str) -> str:
    """A field value into a LIKE pattern: ``*`` widens, ``%``/``_`` are literal."""
    v = value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    v = v.replace("*", "%")
    return wrap.format(v)


def _value_sql(column: str, value: str, *, wrap: str = "%{}%") -> tuple[str, list[str]]:
    """One equality/substring/wildcard predicate over a plain column.

    A value carrying ``*`` is used exactly as written -- the asterisks are the
    user's statement of where matching should happen (``domain:*.github.io``).
    A value without them gets the caller's default wrapping: substring for
    ``url``/``title``/``folder``/``text``, exact for ``domain``.
    """
    if _WILDCARD_RE.search(value):
        return (f"{column} LIKE ? ESCAPE '\\'", [_like(value, wrap="{}")])
    return (f"{column} LIKE ? ESCAPE '\\'", [_like(value, wrap=wrap)])


def _values_sql(column: str, values: list[str], *, wrap: str = "%{}%") -> tuple[str, list[str]]:
    """Alternation over one column: OR of per-value predicates."""
    parts, params = [], []
    for v in values:
        p, q = _value_sql(column, v, wrap=wrap)
        parts.append(p)
        params.extend(q)
    return (" OR ".join(parts) if parts else "1=1", params)


def _field_sql(f: FieldFilter, *, now: float) -> tuple[str, list[str]] | None:
    """One filter -> a predicate on ``bookmark.id``.

    Returns ``None`` when the filter's value is not parseable (date grammar);
    the caller degrades it to an ignored token. Negation is handled by the
    caller, which needs set subtraction rather than SQL ``NOT`` -- ``NOT``
    would also drop rows that are NULL, and a bookmark with no ``content``
    row is normal.
    """
    if f.field == "domain":
        return _values_sql("domain", _split_value(f.value), wrap="{}")
    if f.field == "url":
        return _values_sql("url", _split_value(f.value))
    if f.field == "title":
        return _values_sql("title", _split_value(f.value))
    if f.field == "folder":
        return _values_sql("folder", _split_value(f.value))
    if f.field == "text":
        parts, params = [], []
        for v in _split_value(f.value):
            # Through `_value_sql` rather than a hand-rolled pattern, so
            # `text:` gets the same wildcard and escaping rules as the columns
            # above -- which is what that helper's docstring already promises.
            inner, ps = _value_sql("c.body_text", v)
            parts.append(
                "EXISTS (SELECT 1 FROM content c WHERE c.bookmark_id = b.id "
                f"AND {inner})"
            )
            params.extend(ps)
        return (" OR ".join(parts) if parts else "1=1", params)
    if f.field == "tag":
        # Exact element of the tags JSON array, not a substring: tags are a
        # closed vocabulary the user typed themselves, so `tag:work` matching
        # `workshop` would be a filter that quietly widens. One EXISTS covers
        # the whole alternation -- `tag:(work|rust)` is one membership test.
        vals = _split_value(f.value)
        marks = ",".join("?" * len(vals))
        return (
            "EXISTS (SELECT 1 FROM json_each(b.tags) "
            f"WHERE json_each.value IN ({marks}))",
            vals,
        )
    if f.field == "topic":
        parts, params = [], []
        for v in _split_value(f.value):
            parts.append(
                "EXISTS (SELECT 1 FROM enrichment e WHERE e.bookmark_id = b.id "
                "AND e.topics LIKE ? ESCAPE '\\')"
            )
            params.append('%"' + v.replace('"', "").replace("%", r"\%") + '"%')
        return (" OR ".join(parts) if parts else "1=1", params)
    if f.field == "lang":
        parts, params = [], []
        for v in _split_value(f.value):
            parts.append(
                "EXISTS (SELECT 1 FROM content c WHERE c.bookmark_id = b.id "
                "AND lower(c.lang) = lower(?))"
            )
            params.append(v)
        return (" OR ".join(parts) if parts else "1=1", params)
    if f.field == "opened":
        vals = _split_value(f.value)
        preds: list[str] = []
        params: list[str] = []
        for v in vals:
            rm = _RANGE_RE.match(v)
            if rm:
                lo, hi = rm.group(1), rm.group(2)
                if lo:
                    preds.append("b.open_count >= ?")
                    params.append(lo)
                if hi:
                    preds.append("b.open_count <= ?")
                    params.append(hi)
            elif v.isdigit():
                preds.append("b.open_count = ?")
                params.append(v)
            else:
                return None
        return (" AND ".join(preds) if preds else "1=1", params)
    if f.field == "added":
        # Range form first: ``added:2026-01-01..2026-03-31`` or ``..7d``.
        rng = _date_range(f.value, now=now)
        if rng is not None:
            return ("b.date_added >= ? AND b.date_added < ?", [str(rng[0]), str(rng[1])])
        span = resolve_date_span(f.value)
        if span is not None:
            return ("b.date_added >= ? AND b.date_added < ?", [str(span[0]), str(span[1])])
        r = resolve_date_value(f.value, now=now)
        if r is None:
            # A bare relative value ("90d") is not a date filter at all; only
            # forms with an operator or an absolute date are.
            return None
        op, ts = r
        sql_op = {">": ">", ">=": ">=", "<": "<", "<=": "<="}[op]
        return (f"b.date_added {sql_op} ?", [str(ts)])
    return None


def filter_sets(
    conn: sqlite3.Connection, parsed: ParsedQuery, *, now: float | None = None
) -> tuple[set[int] | None, set[int], list[str]]:
    """Resolve the filters to ``(include, exclude, ignored)``.

    ``include`` is ``None`` when no positive filter constrains the pool, so
    "unconstrained" stays distinguishable from "matches nothing". Every set is
    over bookmark ids. Filters that do not parse land in ``ignored`` verbatim.
    """
    now = time.time() if now is None else now
    include: set[int] | None = None
    exclude: set[int] = set()
    ignored: list[str] = []

    for f in parsed.filters:
        sql = _field_sql(f, now=now)
        if sql is None:
            ignored.append(f"{f.alias or f.field}:{f.value}")
            continue
        where, params = sql
        ids = {
            int(r[0])
            for r in conn.execute(
                f"SELECT b.id FROM bookmark b WHERE {where}", params
            ).fetchall()
        }
        if f.negate:
            exclude |= ids
        elif include is None:
            include = ids
        else:
            include &= ids

    # Negated free-text terms: excluded by lexical match, so `-facebook` on a
    # library without any facebook bookmark costs nothing and excludes
    # nothing. Phrases match as phrases.
    for t in parsed.terms:
        if not t.negated:
            continue
        exclude |= _lexical_match_ids(conn, t.plain, is_phrase=t.is_phrase)

    return include, exclude, ignored


def _lexical_match_ids(conn: sqlite3.Connection, text: str, *, is_phrase: bool) -> set[int]:
    """Ids whose title/summary/body contain the term, for negation.

    Deliberately the *word* index rather than the trigram one: a negation on
    ``security`` should not exclude a page that merely contains ``insecurity``
    -- exclusion is the operation where a false positive is the expensive
    direction, so it uses the tighter matcher.
    """
    if not text:
        return set()
    from .lexical import lexical_lists  # local import: pipeline imports us too

    out: set[int] = set()
    if is_phrase:
        phrase = " ".join(text.split())
        try:
            rows = conn.execute(
                'SELECT rowid FROM fts_seg WHERE fts_seg MATCH ?',
                (f'"{phrase.replace(chr(34), chr(34) * 2)}"',),
            ).fetchall()
            out = {int(r[0]) for r in rows}
        except sqlite3.OperationalError:
            out = set()
        # A phrase in the title is worth excluding on even when the body index
        # has never seen the page: titles are always indexed. Through `_like`
        # because the SQL declares an ESCAPE: a `%` or `_` inside the phrase
        # is a character the user typed, not a wildcard, and left raw it would
        # make `-"100%"` exclude the whole library.
        like = _like(phrase, wrap="%{}%")
        out |= {
            int(r[0]) for r in conn.execute(
                "SELECT id FROM bookmark WHERE title LIKE ? ESCAPE '\\'", (like,)
            ).fetchall()
        }
        return out
    for ids in lexical_lists(conn, text, limit=1000).values():
        out |= set(ids)
    like = _like(text, wrap="%{}%")
    out |= {
        int(r[0]) for r in conn.execute(
            "SELECT id FROM bookmark WHERE title LIKE ? ESCAPE '\\'", (like,)
        ).fetchall()
    }
    return out


#: Columns the sort directives need, fetched once per pool and sorted in
#: Python. SQL ``ORDER BY`` would be simpler were it not for ``in_chunks``:
#: a pool larger than one ``IN (...)`` batch is ordered per batch, and the
#: batches are in id order, which silently mis-orders anything past 900 rows.
#: The pools here are bounded by ``max_candidate_depth`` (2000), so a Python
#: sort over that many small tuples is both correct and cheap.
_SORT_COLUMNS = "id, date_added, domain, title, url"

#: Newest-first: the order a browse gets when the query names none. A named
#: constant because :func:`pool_from_filters` needs a spec that cannot be
#: ``None``, and ``sort:relevance`` is a legal directive that names no
#: orderable column.
_DATE_DESC = (lambda r: (r["date_added"] or 0, r["id"]), True)


def _sort_spec(sort: str):
    """``(key_fn, reverse)`` over rows from :func:`_row_map`, or ``None``.

    ``None`` means "this directive is not an ordering over columns" -- either
    an unknown value or ``relevance``, which is the fusion's own order and so
    is a no-op for anything already ranked.

    Reverse sorts keep the id tiebreak ascending by negating it inside the key
    and letting ``reverse=True`` undo exactly that negation.
    """
    if sort == "date":
        return _DATE_DESC
    if sort == "-date":
        return (lambda r: (r["date_added"] or 2**62, r["id"]), False)
    if sort == "domain":
        return (lambda r: ((r["domain"] or "").lower(), r["id"]), False)
    if sort == "-domain":
        return (lambda r: ((r["domain"] or "").lower(), -r["id"]), True)
    if sort == "title":
        return (lambda r: ((r["title"] or "").lower(), r["id"]), False)
    if sort == "-title":
        return (lambda r: ((r["title"] or "").lower(), -r["id"]), True)
    if sort == "url":
        return (lambda r: ((r["url"] or "").lower(), r["id"]), False)
    if sort == "-url":
        return (lambda r: ((r["url"] or "").lower(), -r["id"]), True)
    return None


def _row_map(conn: sqlite3.Connection, ids: list[int]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for batch in in_chunks(ids):
        marks = ",".join("?" * len(batch))
        for r in conn.execute(
            f"SELECT {_SORT_COLUMNS} FROM bookmark WHERE id IN ({marks})", batch
        ).fetchall():
            out[int(r["id"])] = dict(r)
    return out


def pool_from_filters(
    conn: sqlite3.Connection, parsed: ParsedQuery, *, limit: int, now: float | None = None
) -> list[int]:
    """The candidate pool for a query whose filters left no free text.

    Ordered by the requested sort, or newest-first when unspecified: a pure
    filter browses (``domain:github.com``), and a browse is a timeline, not a
    relevance contest. ``sort:relevance`` names an order this path does not
    have -- nothing was scored, because the filters *are* the retrieval -- so
    it falls back to that same newest-first default.
    """
    now = time.time() if now is None else now
    include, exclude, _ = filter_sets(conn, parsed, now=now)
    if include is None:
        include = {int(r[0]) for r in conn.execute("SELECT id FROM bookmark").fetchall()}
    ids = sorted(include - exclude)
    if not ids:
        return []
    key, rev = _sort_spec(parsed.sort) or _DATE_DESC
    rows = _row_map(conn, ids)
    ordered = sorted(ids, key=lambda i: key(rows[i]), reverse=rev)
    return ordered[:limit]


def sort_pool(
    conn: sqlite3.Connection, doc_ids: list[int], sort: str
) -> list[int]:
    """Re-order a pool by a sort directive, id as the final tiebreak."""
    if not sort or sort == "relevance" or not doc_ids:
        return doc_ids
    spec = _sort_spec(sort)
    if spec is None:
        return doc_ids
    rows = _row_map(conn, doc_ids)
    key, rev = spec
    return sorted(doc_ids, key=lambda i: key(rows[i]), reverse=rev)


def apply_filters(
    conn: sqlite3.Connection,
    parsed: ParsedQuery,
    pool: list[int],
    *,
    now: float | None = None,
) -> list[int]:
    """Post-filter a fused pool by the query's filters, in pool order."""
    if not parsed.has_filters:
        return pool
    include, exclude, _ = filter_sets(conn, parsed, now=now)
    if include is None and not exclude:
        return pool
    return [i for i in pool if (include is None or i in include) and i not in exclude]


__all__ = [
    "FIELDS",
    "SORTS",
    "FieldFilter",
    "ParsedQuery",
    "Term",
    "apply_filters",
    "filter_sets",
    "parse_query",
    "pool_from_filters",
    "resolve_date_span",
    "resolve_date_value",
    "sort_pool",
]
