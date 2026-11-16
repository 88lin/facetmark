"""Render the extension's source icons on an isolated Actions runner."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from brand_assets import app_icon
from PIL import Image


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    icons = root / "extension/src/icons"
    icon = app_icon()
    for size in (16, 48, 128):
        icon.resize((size, size), Image.Resampling.LANCZOS).save(icons / f"icon{size}.png")
    original = root / "desktop/splash/mark.svg"
    (icons / "favicon.svg").write_bytes(original.read_bytes())
    evidence = root / ".extension-build/evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    icon.save(evidence / "extension-icon.png")
    (evidence / "extension-icons.json").write_text(json.dumps({
        "revision": os.environ.get("GITHUB_SHA"),
        "renderer_sha256": hashlib.sha256((root / "scripts/brand_assets.py").read_bytes()).hexdigest(),
        "icons": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(icons.glob("*")) if path.is_file()},
        "visual_approval": "pending",
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
