"""Chromium ``Bookmarks`` JSON parser (Chrome, Edge, Brave, Vivaldi, Opera).

Timestamps here really are **WebKit microseconds since 1601-01-01**, which is the
case the design doc assumed for everything. See
:mod:`facetmark.importers.timestamps`.

Reading the live file is safe: Chromium writes it atomically via a temp file plus
rename, and we only ever read. The file is not a SQLite database, so there is no
lock to contend with.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

from .base import ImportResult, RawBookmark


def looks_like_chrome_json(text: str) -> bool:
    head = text[:2048]
    return '"roots"' in head and ("bookmark_bar" in head or "children" in head)


def _walk(
    node: dict,
    path: list[str],
    out: list[RawBookmark],
    stats: dict[str, int],
) -> None:
    ntype = node.get("type")
    if ntype == "url":
        url = node.get("url") or ""
        if not url:
            return
        out.append(
            RawBookmark(
                url=url,
                title=(node.get("name") or "").strip(),
                folder_path=list(path),
                date_added_raw=_as_num(node.get("date_added")),
                date_modified_raw=_as_num(node.get("date_last_used")),
            )
        )
        return

    children = node.get("children")
    if isinstance(children, list):
        name = (node.get("name") or "").strip()
        new_path = [*path, name] if name else list(path)
        stats["folders"] += 1
        stats["max_depth"] = max(stats["max_depth"], len(new_path))
        for child in children:
            if isinstance(child, dict):
                _walk(child, new_path, out, stats)


def _as_num(v: object) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse(text: str) -> ImportResult:
    data = json.loads(text)
    roots = data.get("roots")
    if not isinstance(roots, dict):
        return ImportResult(
            bookmarks=[],
            timestamp_unit=None,
            source="chrome_json",
            warnings=["no 'roots' object -- not a Chromium Bookmarks file"],
        )

    out: list[RawBookmark] = []
    stats = {"folders": 0, "max_depth": 0}
    # Stable order so repeated imports produce identical ids.
    for key in sorted(roots.keys()):
        node = roots[key]
        if isinstance(node, dict):
            _walk(node, [], out, stats)

    warnings: list[str] = []
    if not out:
        warnings.append("no bookmarks found in any root")

    return ImportResult(
        bookmarks=out,
        timestamp_unit=None,
        source="chrome_json",
        folders=stats["folders"],
        max_depth=stats["max_depth"],
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Locating the live file. Windows is the primary target, so it is listed first.
# ---------------------------------------------------------------------------

_WINDOWS_BASES = (
    (r"Google\Chrome\User Data", "Chrome"),
    (r"Microsoft\Edge\User Data", "Edge"),
    (r"BraveSoftware\Brave-Browser\User Data", "Brave"),
    (r"Vivaldi\User Data", "Vivaldi"),
    (r"Chromium\User Data", "Chromium"),
)
_MAC_BASES = (
    ("Google/Chrome", "Chrome"),
    ("Microsoft Edge", "Edge"),
    ("BraveSoftware/Brave-Browser", "Brave"),
    ("Vivaldi", "Vivaldi"),
    ("Chromium", "Chromium"),
)
_LINUX_BASES = (
    ("google-chrome", "Chrome"),
    ("microsoft-edge", "Edge"),
    ("BraveSoftware/Brave-Browser", "Brave"),
    ("vivaldi", "Vivaldi"),
    ("chromium", "Chromium"),
)

_PROFILE_DIRS = ("Default", "Profile 1", "Profile 2", "Profile 3", "Profile 4")


def _candidate_roots() -> list[tuple[Path, str]]:
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            return []
        return [(Path(local) / rel, name) for rel, name in _WINDOWS_BASES]
    home = Path.home()
    if os.uname().sysname == "Darwin":  # type: ignore[attr-defined]
        base = home / "Library" / "Application Support"
        return [(base / rel, name) for rel, name in _MAC_BASES]
    cfg = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    return [(cfg / rel, name) for rel, name in _LINUX_BASES]


def discover_bookmark_files() -> list[tuple[Path, str, str]]:
    """Find live Chromium bookmark files.

    Returns ``(path, browser, profile)`` triples for everything that exists, so
    the CLI can show the user a list instead of guessing which profile they meant.
    """
    found: list[tuple[Path, str, str]] = []
    for root, browser in _candidate_roots():
        if not root.is_dir():
            continue
        profiles = list(_PROFILE_DIRS)
        with contextlib.suppress(OSError):
            profiles += [
                d.name
                for d in root.iterdir()
                if d.is_dir() and d.name.startswith("Profile ") and d.name not in profiles
            ]
        for prof in profiles:
            f = root / prof / "Bookmarks"
            if f.is_file():
                found.append((f, browser, prof))
    return found
