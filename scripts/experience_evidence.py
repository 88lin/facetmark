"""Collect CI renders, never browser profiles, into a small review artifact."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, PngImagePlugin


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Render evidence is prepared in GitHub Actions only")
    target = Path("frontend/visual-evidence")
    target.mkdir(parents=True, exist_ok=True)
    sha = os.environ["GITHUB_SHA"]
    run = os.environ["GITHUB_RUN_ID"]
    captures = []
    for source in sorted(Path("frontend/screenshots").glob("*.png")):
        with Image.open(source) as picture:
            metadata = PngImagePlugin.PngInfo()
            metadata.add_text("Source", f"Facetmark shared React /app; commit {sha}; Actions {run}")
            metadata.add_text("Data", "Repository synthetic corpus; controlled failure cases are test fixtures")
            destination = target / source.name
            picture.save(destination, pnginfo=metadata)
            captures.append({"file": source.name, "width": picture.width, "height": picture.height,
                             "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()})
    for offset in range(0, len(captures), 6):
        batch = captures[offset:offset + 6]
        sheet = Image.new("RGB", (1200, 1104), "#e5e5e9")
        draw = ImageDraw.Draw(sheet)
        for index, record in enumerate(batch):
            with Image.open(target / record["file"]) as picture:
                picture.thumbnail((590, 338))
                x, y = (index % 2) * 600, (index // 2) * 368
                sheet.paste(picture, (x, y + 25))
                draw.text((x + 10, y + 6), record["file"], fill="#222222")
        sheet.save(target / f"contact-{offset // 6 + 1}.jpg", quality=88)
    recording = Path("frontend/recordings/facetmark-reading.webm")
    if recording.exists():
        shutil.copy2(recording, target / recording.name)
    (target / "provenance.json").write_text(json.dumps({
        "commit": sha, "run": run, "data": "synthetic only", "captures": captures,
        "recording": recording.name if recording.exists() else None,
        "workflow": f"https://github.com/88lin/facetmark/actions/runs/{run}",
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
