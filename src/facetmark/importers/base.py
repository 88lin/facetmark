"""Shared types for bookmark importers."""

from __future__ import annotations

from dataclasses import dataclass, field

#: Separator used to render a folder path for humans. It is *not* safe to split
#: on: measured on a real 96-folder export, 4 folder names contain a literal
#: ``/`` themselves ("AI/ML"-style names are common). Anything that needs the
#: ancestors must read :attr:`RawBookmark.folder_path`, never ``folder.split``.
FOLDER_SEP = "/"


def join_folder(parts: list[str] | tuple[str, ...]) -> str:
    """Render a folder path for display. Lossy when a name contains the separator."""
    return FOLDER_SEP.join(parts)


@dataclass(slots=True)
class RawBookmark:
    """A bookmark exactly as the source file described it, before normalisation."""

    url: str
    title: str = ""
    #: Authoritative, unambiguous ancestor chain, outermost first.
    folder_path: list[str] = field(default_factory=list)
    #: Raw timestamp in whatever unit the source uses; converted later.
    date_added_raw: float | None = None
    date_modified_raw: float | None = None
    #: ``<DD>`` note in Netscape exports; users sometimes keep real notes here.
    note: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def folder(self) -> str:
        """Human-readable path. For display and exact-identity comparison only."""
        return join_folder(self.folder_path)

    @property
    def folder_depth(self) -> int:
        return len(self.folder_path)


def folder_collisions(bookmarks: list[RawBookmark]) -> list[str]:
    """Distinct folder paths that render to the same display string.

    "a/b" at the root and "b" inside "a" are different folders that both render
    as ``a/b``. Rare, but if it happens the display string stops being a valid
    folder identity and folder co-location (facet F4) would silently merge them.
    """
    seen: dict[str, set[tuple[str, ...]]] = {}
    for b in bookmarks:
        if b.folder_path:
            seen.setdefault(b.folder, set()).add(tuple(b.folder_path))
    return sorted(k for k, v in seen.items() if len(v) > 1)


@dataclass(slots=True)
class ImportResult:
    bookmarks: list[RawBookmark]
    #: Detected timestamp unit, e.g. ``unix_s`` or ``webkit_us``.
    timestamp_unit: str | None
    source: str
    folders: int = 0
    max_depth: int = 0
    #: Non-fatal problems worth surfacing to the user.
    warnings: list[str] = field(default_factory=list)
