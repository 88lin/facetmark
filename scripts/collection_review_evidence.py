"""Package current collection cloud captures; this script never runs the app."""
from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import subprocess
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Package collection runtime evidence in GitHub Actions only")
    destination = Path("collection-review-evidence")
    destination.mkdir(exist_ok=True)
    for source in Path("frontend/screenshots/collection-review").glob("*"):
        shutil.copy2(source, destination / source.name)
    video = Path("frontend/recordings/facetmark-collection-review.webm")
    if video.exists():
        subprocess.run(["ffmpeg", "-y", "-i", str(video), "-vf", "scale=1440:-2", "-c:v", "libx264",
                        "-crf", "25", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        str(destination / "collection-interactions.mp4")], check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(video), "-vf", "fps=1,scale=480:-2,tile=3x4",
                        "-frames:v", "1", str(destination / "interaction-storyboard.jpg")],
                       check=True, capture_output=True)
    sources = [*Path("frontend/src").rglob("*.tsx"), *Path("frontend/src").rglob("*.css"),
               Path("frontend/tests/collection-review.spec.ts"), Path("scripts/collection_review_fixture.py")]
    provenance = {"revision": os.environ.get("GITHUB_SHA"), "run": os.environ.get("GITHUB_RUN_ID"),
                  "data": "CI temporary SQLite collection; synthetic content only; no personal browser profile",
                  "source": {p.as_posix(): digest(p) for p in sources if p.exists()},
                  "captures": {p.name: digest(p) for p in destination.iterdir() if p.is_file()}}
    (destination / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    figures = "\n".join(f'<figure id="{html.escape(p.stem)}"><figcaption>{html.escape(p.stem)}</figcaption>'
                        f'<a href="{html.escape(p.name)}"><img src="{html.escape(p.name)}" alt="{html.escape(p.stem)}"></a></figure>'
                        for p in sorted(destination.glob("*.png")))
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    page += '<title>Facetmark 收藏工作区 · 本轮实际渲染</title><style>body{margin:0;padding:32px;background:#e9eff5;color:#162b43;'
    page += 'font:16px/1.7 system-ui,sans-serif}main{max-width:1440px;margin:auto}h1{font-size:28px}figure{margin:32px 0}'
    page += 'figcaption{margin-bottom:10px}img,video{max-width:100%;height:auto;border-radius:24px}a{color:#235fe5}</style><main>'
    page += '<h1>Facetmark 收藏工作区</h1><p>本轮实际 React 页面，GitHub Actions 渲染；全部为隔离合成收藏。视觉仍待用户评价。</p>'
    page += f'<p>Source: <code>{html.escape(os.environ.get("GITHUB_SHA", ""))}</code></p>'
    if video.exists():
        page += '<video controls src="collection-interactions.mp4"></video>'
    page += figures + '<p><a href="review.json">操作记录</a> · <a href="provenance.json">源码与媒体版本</a></p></main></html>'
    (destination / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
