"""Static assets for the local web UI served at ``/app``.

This package holds files, not code. It exists so the UI travels inside the
wheel: ``pip install facetmark && facetmark serve`` has to produce a working
page, with no build step and no network fetch, on a machine that never saw the
git checkout.

Two traps are worth naming here, because both fail silently.

**The ignore file.** ``.gitignore`` ignores ``*.html`` wholesale -- the rule
exists so that nobody commits a bookmark export by accident. Hatchling honours
VCS ignore files when it selects wheel contents, so ``index.html`` needs an
explicit negation in ``.gitignore`` or it is missing from *both* ``git add``
and the wheel. CI asserts the built wheel contains these files for that reason.

**The path.** ``__file__`` is right for a normal install and for an editable
one, and wrong for a zipimport. facetmark opens a SQLite database on disk and
therefore has never been importable from a zip, so ``__file__`` is honest here
in a way a comment can make explicit rather than leaving the reader to wonder.
"""

from __future__ import annotations

from pathlib import Path

#: Directory containing ``index.html`` and ``static/``.
WEB_DIR = Path(__file__).resolve().parent

#: Directory served at ``/app/static``.
STATIC_DIR = WEB_DIR / "static"

#: The single HTML document. Served verbatim, never templated -- see
#: :func:`facetmark.api._register` for why the token is fetched instead.
INDEX_HTML = WEB_DIR / "index.html"

__all__ = ["INDEX_HTML", "STATIC_DIR", "WEB_DIR"]
