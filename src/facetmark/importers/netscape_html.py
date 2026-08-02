"""Netscape bookmark-file parser -- the ``bookmarks.html`` every browser exports.

Timestamps here are **Unix seconds**, not WebKit microseconds. See
:mod:`facetmark.importers.timestamps`.

The parser is a token scanner rather than a line reader. Chrome happens to emit
one element per line, but Firefox, Safari and various extensions do not, and a
line-based parser silently loses the folder hierarchy on those files.
"""

from __future__ import annotations

import html
import re

from .base import ImportResult, RawBookmark

#: Inline base64 favicons account for ~88% of a real export's bytes
#: (1.69 MB -> 0.20 MB on the calibration file). Strip before scanning.
_ICON_RE = re.compile(r'\s+ICON="[^"]*"', re.I)
_ICON_URI_RE = re.compile(r'\s+ICON_URI="[^"]*"', re.I)
_TAG_RE = re.compile(r"<[^>]+>")

_TOKEN_RE = re.compile(
    r"""
      <DT>\s*<H3(?P<h3attrs>[^>]*)>(?P<h3text>.*?)</H3>     # folder open
    | <DT>\s*<A\s+(?P<aattrs>[^>]*)>(?P<atext>.*?)</A>      # bookmark
    | (?P<dlclose></DL>)                                     # folder close
    | <DD>(?P<dd>.*?)(?=<DT|</DL|\Z)                         # note on previous item
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


def _attr(attrs: str, name: str) -> str | None:
    m = re.search(rf'\b{name}\s*=\s*"([^"]*)"', attrs, re.I)
    return m.group(1) if m else None


def _num(attrs: str, name: str) -> float | None:
    v = _attr(attrs, name)
    if v is None:
        return None
    v = v.strip()
    try:
        return float(v)
    except ValueError:
        return None


def _clean_text(s: str) -> str:
    return html.unescape(_TAG_RE.sub("", s)).strip()


def looks_like_netscape(text: str) -> bool:
    head = text[:4096].upper()
    return "NETSCAPE-BOOKMARK-FILE" in head or ("<DL>" in head and "<DT>" in head)


def parse(text: str) -> ImportResult:
    """Parse a Netscape bookmark export."""
    body = _ICON_URI_RE.sub("", _ICON_RE.sub("", text))

    bookmarks: list[RawBookmark] = []
    warnings: list[str] = []
    stack: list[str] = []
    folders = 0
    max_depth = 0

    for m in _TOKEN_RE.finditer(body):
        if m.group("h3text") is not None:
            name = _clean_text(m.group("h3text")) or "(unnamed)"
            stack.append(name)
            folders += 1
            max_depth = max(max_depth, len(stack))
        elif m.group("dlclose"):
            if stack:
                stack.pop()
        elif m.group("aattrs") is not None:
            attrs = m.group("aattrs")
            url = _attr(attrs, "HREF")
            if not url:
                continue
            tags_raw = _attr(attrs, "TAGS") or ""
            bookmarks.append(
                RawBookmark(
                    url=html.unescape(url).strip(),
                    title=_clean_text(m.group("atext")),
                    folder_path=list(stack),
                    date_added_raw=_num(attrs, "ADD_DATE"),
                    date_modified_raw=_num(attrs, "LAST_MODIFIED"),
                    tags=[t.strip() for t in tags_raw.split(",") if t.strip()],
                )
            )
        elif m.group("dd") is not None and bookmarks:
            note = _clean_text(m.group("dd"))
            if note:
                bookmarks[-1].note = note

    if stack:
        warnings.append(
            f"{len(stack)} unclosed <DL> element(s); folder paths near the end of "
            f"the file may be too deep"
        )
    if not bookmarks:
        warnings.append("no <DT><A HREF=...> elements found -- is this a bookmark export?")

    return ImportResult(
        bookmarks=bookmarks,
        timestamp_unit=None,  # filled in by the caller after unit detection
        source="netscape_html",
        folders=folders,
        max_depth=max_depth,
        warnings=warnings,
    )
