"""facetmark's own export format, and the parser that reads it back.

``facetmark export`` writes this and ``facetmark import`` recognises it, which
is the only arrangement that makes an export a backup rather than a dump. The
shape is borrowed from hister, whose ``export`` writes JSON its own
``import file`` detects (``isHisterJSONExport``); so is the idea that an export
can be a *subset*, since both tools already have a query language that can say
which one.

What is exported is the source of truth and nothing else: the URL, what the
user called it, where they filed it, when they saved it, and their tags.
Summaries, topics, vectors and sessions are all derived, all fingerprinted, and
all rebuilt by ``facetmark index`` -- writing them into a backup would make the
file enormous and would restore a snapshot of an old model's opinions. The
``--full`` flag adds them anyway for anyone who wants to read the file, and
this parser ignores the extra keys on the way back in.

Timestamps are written as unix seconds, which is what the database stores, so
the unit detection the browser formats need has an easy time of it on the way
back in.
"""

from __future__ import annotations

import json

from .base import ImportResult, RawBookmark

#: The key whose presence means "facetmark wrote this". A version rather than a
#: bare marker because the reader has to be able to refuse a file from a format
#: it does not know, and "unknown version" is a better error than a silently
#: half-read library.
MARKER = "facetmark"
FORMAT_VERSION = 1


def looks_like_facetmark_export(text: str) -> bool:
    """Cheap sniff on the head of the file, like the other parsers do."""
    head = text[:2048]
    return f'"{MARKER}"' in head and '"bookmarks"' in head


def parse(text: str) -> ImportResult:
    warnings: list[str] = []
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return ImportResult(bookmarks=[], timestamp_unit=None,
                            source="facetmark_json",
                            warnings=[f"not valid JSON: {exc}"])
    if not isinstance(doc, dict):
        return ImportResult(bookmarks=[], timestamp_unit=None,
                            source="facetmark_json",
                            warnings=["expected a JSON object"])

    header = doc.get(MARKER) or {}
    version = header.get("version") if isinstance(header, dict) else None
    if version is not None and int(version) > FORMAT_VERSION:
        warnings.append(
            f"this file is format version {version}; this build reads "
            f"{FORMAT_VERSION}. Unknown fields were ignored."
        )

    out: list[RawBookmark] = []
    folders: set[str] = set()
    ambiguous: set[str] = set()
    depth = 0
    for raw in doc.get("bookmarks") or []:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or "").strip()
        if not url:
            continue
        path = raw.get("folder_path")
        if not isinstance(path, list):
            # The database stores the *display* path and warns against splitting
            # it, because a folder name may itself contain '/'. An export can
            # only write what is stored, so `folder_depth` is what says how to
            # read it back: depth 1 means one folder whose name happens to
            # contain a slash -- which is exactly what `POST /bookmark` records
            # when it is handed `folder="read/write ratio"`. Only a disagreement
            # neither reading explains is a warning.
            display = str(raw.get("folder") or "")
            parts = [p for p in display.split("/") if p.strip()] if display else []
            depth_said = raw.get("folder_depth")
            if not isinstance(depth_said, int) or not depth_said:
                path = parts
            elif depth_said == 1:
                path = [display] if display else []
            elif depth_said == len(parts):
                path = parts
            else:
                path = parts
                ambiguous.add(display)
        path = [str(p).strip() for p in path if str(p).strip()]
        tags = [str(t).strip() for t in (raw.get("tags") or []) if str(t).strip()]
        added = raw.get("date_added")
        out.append(RawBookmark(
            url=url,
            title=str(raw.get("title") or "").strip(),
            folder_path=path,
            date_added_raw=float(added) if isinstance(added, (int, float)) else None,
            note=str(raw.get("note") or ""),
            tags=tags,
        ))
        if path:
            folders.add("/".join(path))
            depth = max(depth, len(path))

    if ambiguous:
        warnings.append(
            f"{len(ambiguous)} folder path(s) contain a '/' in a folder name, so "
            f"the nesting could not be reconstructed exactly: "
            f"{', '.join(sorted(ambiguous)[:3])}"
        )
    return ImportResult(
        bookmarks=out,
        # Left to `detect_and_parse`, like every other parser: the column is
        # written in unix seconds and detection says so, and hard-coding it
        # here would only be overwritten a moment later.
        timestamp_unit=None,
        source="facetmark_json",
        folders=len(folders),
        max_depth=depth,
        warnings=warnings,
    )
