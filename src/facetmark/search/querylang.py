"""The query language: filters, phrases, negation and sort over free text.

Facetmark's lexical facet used to receive the raw query string and strip every
FTS5 metacharacter from it (see :data:`facetmark.text._FTS_STRIP_RE`), which
meant the data to answer a filter was in the database -- ``bookmark.domain``,
``bookmark.folder``, ``bookmark.date_added`` have existed since v1 -- and there
was no way to ask for it. This module is the port of hister's query builder
(``server/indexer/querybuilder``): a small hand-written lexer that recognises
the handful of shapes users actually type, a declarative field table as the
single source of truth for what exists, and a parsed representation every
consumer (lexical SQL, vector post-filter, snippet highlighting, the response
echo) can share.

The grammar, deliberately tiny:

* free words, as before: ``async rust``
* quoted phrases: ``"exact phrase"`` (also CJK quotes “ ” 「 」 『 』)
* negation: ``-term``, ``-"phrase"``, ``-domain:github.com``
* field filters: ``domain:github.com``, ``host:news.ycombinator.com``,
  ``url:docs``, ``title:rust``, ``folder:reading``, ``tag:work``
* field aliases: ``site:`` → ``domain:``
* alternation: ``(a|b)`` and fielded ``domain:(github.com|gitlab.com)``
* dates: ``before:2024-06-01``, ``after:30d``, ``added:2024``,
  ``added:2024-06..2024-09``, comparisons ``added:>2024-01-01``, ``added:<90d``
* prefix wildcard on free words: ``kuber*``
* directive: ``sort:date``, ``sort:-date``, ``sort:title``, ``sort:domain``,
  ``sort:open_count``

Two properties are load-bearing:

* **A plain query must be untouched.** ``async rust`` parses to itself with no
  filters, and :func:`parse_query` reports that via ``is_plain`` so callers can
  take their existing fast path bit-for-bit. Every existing test that does not
  use the new syntax must keep passing unchanged.
* **A colon is not a filter unless the name is one.** ``https://example.com/x``
  contains two colons; ``https`` and ``example.com`` are not fields, so the URL
  arrives at the lexical facet as one word, exactly as it does today. Only
  names in :data:`FIELDS` (or an alias) split a token.
"""

from __future__ import annotations

import calendar
import re
import time
from dataclasses import dataclass, field

__all__ = [
    "FIELDS",
    "FieldDef",
    "FieldFilter",
    "DateRange",
    "ParsedQuery",
    "SORT_KEYS",
    "parse_query",
    "QUERY_SYNTAX_HELP",
]


# ---------------------------------------------------------------------------
# the field table -- single source of truth (hister's searchschema, ported)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FieldDef:
    """One filterable field.

    ``kind`` decides how a value is executed: ``sql`` fields become predicates
    over ``bookmark`` (the column named here); ``date`` fields become
    ``date_added`` range bounds; ``directive`` tokens are peeled off the query
    entirely and never reach a facet.
    """

    name: str
    kind: str  # "sql" | "date" | "directive"
    column: str
    aliases: tuple[str, ...] = ()
    #: How a value matches. "exact_suffix" = domain equals v, or host ends with
    # ".v" (site:github.com covers gist.github.com). "contains" = substring.
    #: "tag" = exact element of the tags JSON array.
    match: str = "contains"
    description: str = ""


FIELDS: dict[str, FieldDef] = {
    "domain": FieldDef(
        "domain", "sql", "domain", aliases=("site",), match="exact_suffix",
        description="Registrable domain, e.g. domain:github.com (covers subdomains).",
    ),
    "host": FieldDef(
        "host", "sql", "host", match="contains",
        description="Full hostname, e.g. host:news.ycombinator.com.",
    ),
    "url": FieldDef(
        "url", "sql", "url", match="contains",
        description="Substring of the raw URL, e.g. url:releases.",
    ),
    "title": FieldDef(
        "title", "sql", "title", match="contains",
        description="Substring of the page title, e.g. title:rust.",
    ),
    "folder": FieldDef(
        "folder", "sql", "folder", match="contains",
        description="Substring of the folder path, e.g. folder:reading.",
    ),
    "tag": FieldDef(
        "tag", "sql", "tags", match="tag",
        description="Exact tag, e.g. tag:work. Tags come from imports and the save API.",
    ),
    "after": FieldDef("after", "date", "date_added", aliases=("since",),
                      description="Saved at or after: after:2024-06-01 or after:7d."),
    "before": FieldDef("before", "date", "date_added", aliases=("until",),
                       description="Saved at or before: before:2024-06-01 or before:90d."),
    "added": FieldDef("added", "date", "date_added", aliases=("on", "saved"),
                      description="Saved within a period: added:2024, added:2024-06, "
                                  "added:2024-06-01..2024-09-01, added:>2024-01-01."),
    "sort": FieldDef("sort", "directive", "",
                     description="Result order: sort:date, sort:-date, sort:title, "
                                 "sort:domain, sort:open_count."),
}

#: Canonical name -> definition, plus every alias.
_FIELD_LOOKUP: dict[str, FieldDef] = {}
for _d in FIELDS.values():
    _FIELD_LOOKUP[_d.name] = _d
    for _a in _d.aliases:
        _FIELD_LOOKUP[_a] = _d

SORT_KEYS = frozenset({"date", "-date", "title", "-title", "domain", "-domain",
                       "open_count", "-open_count"})

_DAY = 86400
_MONTH = 30 * _DAY
_YEAR = 365 * _DAY

#: ``30d`` / ``2w`` / ``3m`` / ``1y`` -- hister's relative units, minus the
#: hour/minute forms that make no sense for a filing date. Long forms first:
#: regex alternation is leftmost-first, and ``mo`` must not shadow ``month``.
_RELATIVE = re.compile(
    r"^(\d{1,4})\s*(days?|weeks?|w|months?|mo|years?|y|d|m)$", re.IGNORECASE
)
_RELATIVE_SECONDS = {
    "day": _DAY, "days": _DAY, "d": _DAY,
    "week": 7 * _DAY, "weeks": 7 * _DAY, "w": 7 * _DAY,
    "month": _MONTH, "months": _MONTH, "mo": _MONTH, "m": _MONTH,
    "year": _YEAR, "years": _YEAR, "y": _YEAR,
}
_ABSOLUTE = re.compile(r"^(\d{4})(?:[-/.](\d{1,2}))?(?:[-/.](\d{1,2}))?$")
_RANGE = re.compile(r"^(\S+?)\.\.(\S+)$")
_COMPARISON = re.compile(r"^([<>]=?)(.+)$")

_MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

#: Opening and closing quote characters. Curly/CJK quotes arrive from phone
#: keyboards; :mod:`facetmark.search.understand` already treats them as
#: phrase markers, so the lexer has to agree with it.
_OPEN_QUOTES = {'"', "\u201c", "\u300c", "\u300e"}
_QUOTE_PAIRS = {"\u201c": "\u201d", "\u300c": "\u300d", "\u300e": "\u300f"}

_FIELD_PREFIX_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*):")


# ---------------------------------------------------------------------------
# date parsing
# ---------------------------------------------------------------------------


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year: int, month: int) -> int:
    if month == 2 and _is_leap(year):
        return 29
    return _MONTH_DAYS[month - 1]


def _to_unix(year: int, month: int, day: int, end_of_day: bool) -> int:
    """UTC midnight of that date, plus 86399 when the day is the inclusive end."""
    ts = calendar.timegm((year, month, day, 0, 0, 0))
    return ts + 86399 if end_of_day else ts


def _parse_absolute(value: str) -> tuple[int, int] | None:
    """A date or date prefix, as an inclusive [start, end] window in unix seconds.

    ``2024`` is the whole year, ``2024-06`` the whole month, ``2024-06-01`` the
    whole day. The end bound is inclusive so ``before:2024-06-01`` still
    matches a bookmark saved that day -- "before the 1st" in a filing context
    means "not after the 1st", and a 23:59 save is the same day to a human.
    """
    m = _ABSOLUTE.match(value)
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else None
    day = int(m.group(3)) if m.group(3) else None
    if month is None:
        return _to_unix(year, 1, 1, False), _to_unix(year, 12, 31, True)
    if not 1 <= month <= 12:
        return None
    if day is None:
        return _to_unix(year, month, 1, False), _to_unix(year, month, _days_in_month(year, month), True)
    if not 1 <= day <= _days_in_month(year, month):
        return None
    return _to_unix(year, month, day, False), _to_unix(year, month, day, True)


def _parse_relative(value: str, now_ts: int | None) -> tuple[int, int] | None:
    """``30d`` as "the window ending now and starting 30 days ago".

    Returned as [start, end] unix seconds. The end is ``now_ts``; the caller
    supplies it so parsing stays pure and tests can pin it.
    """
    m = _RELATIVE.match(value)
    if not m or now_ts is None:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    span = n * _RELATIVE_SECONDS[unit]
    return now_ts - span, now_ts


def _parse_date_value(value: str, now_ts: int | None) -> tuple[int, int] | None:
    if (abs_value := _parse_absolute(value)) is not None:
        return abs_value
    return _parse_relative(value, now_ts)


# ---------------------------------------------------------------------------
# lexer
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Token:
    kind: str  # "word" | "quoted" | "alternation"
    text: str
    negated: bool = False
    field: str | None = None  # canonical field name, when the prefix matched
    start: int = 0
    end: int = 0

    def original(self) -> str:
        """Rebuild the token as typed, for fall-back-to-text paths."""
        prefix = ("-" if self.negated else "") + (f"{self.field}:" if self.field else "")
        if self.kind == "quoted":
            return f'{prefix}"{self.text}"'
        return prefix + self.text


def _read_quoted(s: str, i: int) -> tuple[str, int, bool]:
    """Read from an opening quote to its closing partner.

    Returns (text, next_index, closed). An unterminated quote swallows the rest
    of the string and is reported closed=False; the caller keeps it as a phrase
    anyway, because half a remembered quote is still an exact-string intention.
    """
    quote = s[i]
    closer = _QUOTE_PAIRS.get(quote, '"')
    j = i + 1
    out: list[str] = []
    while j < len(s):
        c = s[j]
        if c == "\\" and j + 1 < len(s) and s[j + 1] in {closer, "\\"}:
            out.append(s[j + 1])
            j += 2
            continue
        if c == closer:
            return "".join(out), j + 1, True
        out.append(c)
        j += 1
    return "".join(out), j, False


def _read_alternation(s: str, i: int) -> tuple[list[str], int, bool]:
    """Read a ``(...|...)`` group at depth 0 of ``|``.

    Nested groups are not supported as nested -- a paren inside a value stays
    literal text. Returns (parts, next_index, closed).
    """
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                body = s[i + 1 : j]
                parts = [p.strip() for p in body.split("|")]
                return [p for p in parts if p], j + 1, True
        j += 1
    return [], len(s), False


def _field_of(s: str, i: int) -> tuple[str | None, int]:
    """If a known field name (or alias) ends with ``:`` at position i, consume it.

    This is the URL guard: ``https:`` fails the lookup, so ``https://x`` stays
    one word. Only the names in :data:`FIELDS` can split a token, and none of
    them are URL schemes a user could have meant.
    """
    m = _FIELD_PREFIX_RE.match(s, i)
    if not m:
        return None, i
    d = _FIELD_LOOKUP.get(m.group(1).lower())
    if d is None:
        return None, i
    return d.name, m.end()


def _tokenize(s: str) -> list[_Token]:
    tokens: list[_Token] = []
    i, n = 0, len(s)
    while i < n:
        if s[i].isspace():
            i += 1
            continue
        start = i
        negated = False
        if s[i] == "-" and i + 1 < n and not s[i + 1].isspace():
            negated = True
            i += 1
        canonical, after_field = _field_of(s, i)
        i = after_field
        if i < n and s[i] in _OPEN_QUOTES:
            text, after, _closed = _read_quoted(s, i)
            tokens.append(_Token("quoted", text, negated, canonical, start, after))
            i = after
            continue
        if i < n and s[i] == "(":
            parts, after, closed = _read_alternation(s, i)
            if closed and parts:
                tokens.append(_Token("alternation", "|".join(parts), negated, canonical, start, after))
                i = after
                continue
            # An unclosed or empty group is not syntax. Fall through to the
            # word reader, which treats "(" as an ordinary character.
        j = i
        while j < n and not s[j].isspace():
            j += 1
        tokens.append(_Token("word", s[i:j], negated, canonical, start, j))
        i = j
    return tokens


# ---------------------------------------------------------------------------
# the parsed representation
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class FieldFilter:
    """One ``field:value`` (or ``field:(a|b)``) constraint."""

    field: str
    values: list[str]
    negated: bool = False

    @property
    def defn(self) -> FieldDef:
        return FIELDS[self.field]


@dataclass(slots=True)
class DateRange:
    """A ``date_added`` window. Both bounds are inclusive unix seconds."""

    start: int | None
    end: int | None

    def merge(self, other: DateRange) -> DateRange:
        """Intersect two ranges -- ``after:7d before:2024-06-01`` narrows both."""
        starts = [x for x in (self.start, other.start) if x is not None]
        ends = [x for x in (self.end, other.end) if x is not None]
        return DateRange(max(starts) if starts else None, min(ends) if ends else None)


@dataclass(slots=True)
class ParsedQuery:
    original: str
    #: Free text left after every directive, field filter and date was peeled
    #: off. This is what the FTS match and the embedding see.
    text: str = ""
    #: Quoted phrases the user asked for verbatim.
    phrases: list[str] = field(default_factory=list)
    #: Free words the user asked to exclude.
    negatives: list[str] = field(default_factory=list)
    #: Free words with a trailing ``*`` (the star stripped, kept as intent).
    prefixes: list[str] = field(default_factory=list)
    field_filters: list[FieldFilter] = field(default_factory=list)
    dates: DateRange | None = None
    #: ``sort`` argument as typed, canonical (e.g. "date", "-date").
    sort: str | None = None
    #: True when nothing in the input used any syntax at all.
    is_plain: bool = True

    @property
    def has_filters(self) -> bool:
        return bool(self.field_filters) or self.dates is not None

    def all_words(self) -> list[str]:
        """Words for snippet targeting: free words plus the words of phrases."""
        out: list[str] = []
        for p in self.phrases:
            out.extend(p.split())
        out.extend(w for w in self.text.split() if w)
        # longest first: a match on the longest term is the match worth showing
        return sorted(dict.fromkeys(out), key=len, reverse=True)

    def as_echo(self) -> dict:
        """A compact echo for the response, so a client can show what applied."""
        return {
            "text": self.text,
            "phrases": list(self.phrases),
            "negatives": list(self.negatives),
            "field_filters": [
                {"field": f.field, "values": list(f.values), "negated": f.negated}
                for f in self.field_filters
            ],
            "dates": None if self.dates is None else [self.dates.start, self.dates.end],
            "sort": self.sort,
        }


QUERY_SYNTAX_HELP = (
    'Filters: domain:github.com  host:news.ycombinator.com  url:releases  '
    'title:rust  folder:reading  tag:work · exclude with - (e.g. -domain:pinterest.com) · '
    'phrases: "exact words" · alternation: domain:(github.com|gitlab.com) · '
    'dates: after:30d before:2024-06-01 added:2024 added:2024-06..2024-09 · '
    'prefix: kuber* · order: sort:date / sort:-date / sort:title / sort:domain'
)


# ---------------------------------------------------------------------------
# the parser
# ---------------------------------------------------------------------------


def _resolve_date(field: str, value: str, now_ts: int | None) -> DateRange | None:
    """Turn a date-field value into a range, or None when it is not a date.

    A non-date value falls back to free text; the caller rebuilds the token
    verbatim so no words are ever lost.
    """
    comp = _COMPARISON.match(value)
    if comp:
        op, rest = comp.group(1), comp.group(2)
        window = _parse_date_value(rest, now_ts)
        if window is None:
            return None
        start, end = window
        # The arrow points the way a filing date moves: ``added:>2024`` is
        # "later than the end of 2024", ``added:<90d`` is "older than 90 days".
        if op in (">", ">="):
            return DateRange(end + 1 if op == ">" else end, None)
        return DateRange(None, start - 1 if op == "<" else start)

    if field == "before":
        window = _parse_date_value(value, now_ts)
        return None if window is None else DateRange(None, window[1])
    if field == "after":
        window = _parse_date_value(value, now_ts)
        return None if window is None else DateRange(window[0], None)

    rng = _RANGE.match(value)
    if rng:
        lo = _parse_date_value(rng.group(1), now_ts)
        hi = _parse_date_value(rng.group(2), now_ts)
        if lo is None or hi is None:
            return None
        return DateRange(lo[0], hi[1])
    window = _parse_date_value(value, now_ts)
    return None if window is None else DateRange(window[0], window[1])


def parse_query(query: str, *, now_ts: int | None = None) -> ParsedQuery:
    """Parse a user query into text + filters. Never raises, never loses words.

    Anything that does not parse as grammar is preserved as free text: an
    unknown ``field:value`` stays verbatim (the field name is not one of ours),
    an invalid date stays verbatim, an unclosed paren stays verbatim. The
    worst case of a typo is the behaviour the user already had.
    """
    if now_ts is None:
        now_ts = int(time.time())

    out = ParsedQuery(original=query, text="")
    if not query or not query.strip():
        return out

    tokens = _tokenize(query.strip())
    text_parts: list[str] = []
    plain = True

    for t in tokens:
        # --- directive -----------------------------------------------------
        if t.field == "sort":
            # An invalid sort key is not a filter either -- "sort:garbage" is
            # ordinary text, exactly as hister treats unknown directives. The
            # negated form never applies, so it falls through to text too.
            value = (t.text.split("|")[0] if t.kind == "alternation" else t.text).strip().lower()
            if not t.negated and value in SORT_KEYS:
                out.sort = value
                plain = False
                continue
            text_parts.append(t.original())
            continue

        # --- date fields ---------------------------------------------------
        if t.field in ("after", "before", "added"):
            if t.negated:
                # A negated date has no clean semantics ("not saved in June"?).
                # Keep the token as text rather than guessing.
                text_parts.append(t.original())
                plain = False
                continue
            value = t.text.split("|")[0] if t.kind == "alternation" else t.text
            rng = _resolve_date(t.field, value, now_ts)
            if rng is not None:
                out.dates = rng if out.dates is None else out.dates.merge(rng)
                plain = False
                continue
            text_parts.append(t.original())
            continue

        # --- sql fields ------------------------------------------------------
        if t.field is not None:
            values = t.text.split("|") if t.kind == "alternation" else [t.text]
            values = [v for v in values if v]
            if values:
                out.field_filters.append(FieldFilter(t.field, values, t.negated))
                plain = False
                continue
            text_parts.append(t.original())
            continue

        # --- free syntax -----------------------------------------------------
        if t.kind == "quoted":
            if t.negated:
                out.negatives.append(t.text)
            else:
                out.phrases.append(t.text)
            plain = False
            continue
        if t.kind == "alternation":
            # Free-text alternation: the FTS builder ORs every word already, so
            # emitting the words keeps lexical semantics; the vector facets see
            # the words too. Negated alternation excludes each word.
            for v in t.text.split("|"):
                if v:
                    if t.negated:
                        out.negatives.append(v)
                    else:
                        text_parts.append(v)
                    plain = False
            continue

        word = t.text
        if t.negated:
            out.negatives.append(word)
            plain = False
            continue
        if word.endswith("*") and len(word.rstrip("*")) >= 2:
            out.prefixes.append(word.rstrip("*"))
            text_parts.append(word.rstrip("*"))
            plain = False
            continue
        text_parts.append(word)

    out.text = " ".join(text_parts)
    # A plain query round-trips exactly: text is the whitespace-normalised
    # original, which is what the FTS builder consumed before this module
    # existed, and every caller can keep its existing fast path.
    out.is_plain = plain and not out.phrases and not out.negatives and not out.prefixes
    if out.is_plain:
        out.text = " ".join(query.split())
    return out
