#!/usr/bin/env python3
"""Flatten ``docs/landing`` into ``docs`` for GitHub Pages.

Pages is configured to serve ``/docs`` on the ``gh-pages`` branch, and it does
not follow a subdirectory.  So the site is authored in ``docs/landing`` -- where
``build.py`` and the content modules live next to their output -- and published
by copying the built artefacts one level up.

The generator is run first, on purpose: publishing HTML that does not match the
content modules is the one failure mode of a two-directory layout, and it is
silent.  ``--check`` does everything except write, so CI can assert that a
publish would be a no-op.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "landing"
DST = ROOT / "docs"

# Everything the browser asks for, and nothing the generator reads.  `tools/`
# and the content modules stay behind: they are how the site is made, not part
# of it.
PATTERNS = ("*.html", "*.css", "*.js")
ASSETS = "assets"


def _built_files() -> list[Path]:
    out: list[Path] = []
    for pat in PATTERNS:
        out += sorted(SRC.glob(pat))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="report what would change and exit non-zero if anything would",
    )
    ap.add_argument(
        "--skip-build",
        action="store_true",
        help="publish what is already on disk instead of regenerating first",
    )
    args = ap.parse_args()

    if not args.skip_build:
        subprocess.run([sys.executable, str(SRC / "build.py")], check=True, cwd=SRC)

    stale: list[str] = []
    for src in _built_files():
        dst = DST / src.name
        if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
            stale.append(src.name)
        if not args.check:
            shutil.copy2(src, dst)

    src_assets = SRC / ASSETS
    if src_assets.is_dir():
        for src in sorted(src_assets.iterdir()):
            if not src.is_file():
                continue
            dst = DST / ASSETS / src.name
            if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
                stale.append(f"{ASSETS}/{src.name}")
            if not args.check:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    if args.check:
        if stale:
            print(f"{len(stale)} file(s) would change:")
            for name in stale:
                print(f"  {name}")
            return 1
        print("docs/ is up to date with docs/landing/")
        return 0

    print(f"published {len(_built_files())} page(s) and assets to {DST}")
    if stale:
        print(f"  {len(stale)} file(s) changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
