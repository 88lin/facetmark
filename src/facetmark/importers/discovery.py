"""Where the browser actually keeps its bookmarks, per platform.

Split out of :mod:`facetmark.importers.chrome_json` because locating the file is
a different job from parsing it, and because the platform that matters most here
is the one this code is least likely to be developed on. The tables below are
written so the Windows branch can be exercised from a Linux CI runner: relative
paths use ``/`` and are joined component by component, so the same string is a
valid ``WindowsPath`` fragment and a valid ``PosixPath`` fragment. A branch that
can only run on the target machine is a branch nobody tests.

Two directory layouts exist in the wild:

``PROFILED``
    Chromium's own. ``<root>/<profile>/Bookmarks``, with ``Default`` for the
    first profile and ``Profile 1``, ``Profile 2``... after that. Users can also
    have profiles beyond the ones we guess, so the root is listed as well.
``FLAT``
    Opera's. One ``Bookmarks`` straight in the channel directory, and the
    channel name (``Opera Stable``, ``Opera GX Stable``) is what distinguishes
    two installs, so that is reported as the profile.
"""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

PROFILED = "profiled"
FLAT = "flat"

#: Guessed profile directories, in the order a user is likely to want them.
#: Anything else matching ``Profile *`` is discovered by listing the root.
_PROFILE_DIRS = ("Default", "Profile 1", "Profile 2", "Profile 3", "Profile 4")

# Windows. Chromium engines live under %LOCALAPPDATA%; Opera is one of the few
# that still uses roaming %APPDATA%, which is why it needs its own table.
_WIN_LOCAL = (
    ("Google/Chrome/User Data", "Chrome", PROFILED),
    ("Microsoft/Edge/User Data", "Edge", PROFILED),
    ("BraveSoftware/Brave-Browser/User Data", "Brave", PROFILED),
    ("Vivaldi/User Data", "Vivaldi", PROFILED),
    ("Chromium/User Data", "Chromium", PROFILED),
)
_WIN_ROAMING = (
    ("Opera Software/Opera Stable", "Opera", FLAT),
    ("Opera Software/Opera GX Stable", "Opera GX", FLAT),
)

# macOS: ~/Library/Application Support
_MAC_BASES = (
    ("Google/Chrome", "Chrome", PROFILED),
    ("Microsoft Edge", "Edge", PROFILED),
    ("BraveSoftware/Brave-Browser", "Brave", PROFILED),
    ("Vivaldi", "Vivaldi", PROFILED),
    ("Chromium", "Chromium", PROFILED),
    ("com.operasoftware.Opera", "Opera", FLAT),
    ("com.operasoftware.OperaGX", "Opera GX", FLAT),
)

# Linux: $XDG_CONFIG_HOME, defaulting to ~/.config
_LINUX_BASES = (
    ("google-chrome", "Chrome", PROFILED),
    ("microsoft-edge", "Edge", PROFILED),
    ("BraveSoftware/Brave-Browser", "Brave", PROFILED),
    ("vivaldi", "Vivaldi", PROFILED),
    ("chromium", "Chromium", PROFILED),
    ("opera", "Opera", FLAT),
)


def _under(base: str | Path, relative: str) -> Path:
    """Join a ``/``-separated fragment without depending on the host separator."""
    return Path(base).joinpath(*relative.split("/"))


def candidate_roots(
    *, os_name: str | None = None, platform: str | None = None
) -> list[tuple[Path, str, str]]:
    """``(root, browser, layout)`` for every place worth looking on this OS.

    Returned whether or not the directory exists; :func:`discover_bookmark_files`
    filters, and the CLI prints the misses so a user whose browser was installed
    somewhere unusual can see what was searched instead of a bare "not found".

    ``os_name`` and ``platform`` default to the running interpreter's and exist
    so the other two platforms' tables can be exercised from CI. They cannot be
    faked by patching :data:`os.name`, because ``pathlib.Path`` picks its
    concrete class from that attribute and a ``WindowsPath`` will not
    instantiate on POSIX -- the seam has to be an argument.
    """
    os_name = os.name if os_name is None else os_name
    platform = sys.platform if platform is None else platform
    if os_name == "nt":
        out: list[tuple[Path, str, str]] = []
        local = os.environ.get("LOCALAPPDATA")
        if local:
            out += [(_under(local, rel), name, kind) for rel, name, kind in _WIN_LOCAL]
        roaming = os.environ.get("APPDATA")
        if roaming:
            out += [(_under(roaming, rel), name, kind) for rel, name, kind in _WIN_ROAMING]
        return out
    home = Path.home()
    if platform == "darwin":
        base = home / "Library" / "Application Support"
        return [(_under(base, rel), name, kind) for rel, name, kind in _MAC_BASES]
    cfg = os.environ.get("XDG_CONFIG_HOME") or (home / ".config")
    return [(_under(cfg, rel), name, kind) for rel, name, kind in _LINUX_BASES]


def discover_bookmark_files(
    *, os_name: str | None = None, platform: str | None = None
) -> list[tuple[Path, str, str]]:
    """Find live Chromium-family bookmark files.

    Returns ``(path, browser, profile)`` triples for everything that exists, so
    the CLI can show the user a list instead of guessing which profile they
    meant. Reading is safe while the browser runs: Chromium writes the file
    atomically through a temp file plus rename, and it is JSON, not SQLite, so
    there is no lock to contend with.
    """
    found: list[tuple[Path, str, str]] = []
    for root, browser, layout in candidate_roots(os_name=os_name, platform=platform):
        if not root.is_dir():
            continue
        if layout == FLAT:
            f = root / "Bookmarks"
            if f.is_file():
                found.append((f, browser, root.name))
            continue
        profiles = list(_PROFILE_DIRS)
        with contextlib.suppress(OSError):
            profiles += sorted(
                d.name
                for d in root.iterdir()
                if d.is_dir() and d.name.startswith("Profile ") and d.name not in profiles
            )
        for prof in profiles:
            f = root / prof / "Bookmarks"
            if f.is_file():
                found.append((f, browser, prof))
    return found
