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


def caption(path):
    name = path.stem
    if name.startswith("polish-native-startup"):
        return f"{name} · 启动 HTML 的浏览器渲染，使用合成重启桥接；不是安装后的桌面截图"
    if name.startswith("polish-native-tray"):
        return f"{name} · 托盘 HTML 的浏览器渲染，使用合成动作桥接；原生开关行为由 Windows 安装验证另验"
    if name.startswith("polish-import-"):
        return f"{name} · 来源与导入界面的合成响应状态；真实导入接口另由回归测试验证"
    if name.startswith("polish-"):
        return f"{name} · 本轮控件、目录或首次使用状态"
    return name


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
    sources = [*Path("frontend/src").rglob("*.tsx"), *Path("frontend/src").rglob("*.ts"),
               *Path("frontend/src").rglob("*.css"),
               *map(Path, ["frontend/tests/collection-review.spec.ts",
                           "frontend/tests/workspace-polish.spec.ts", "frontend/tests/startup.spec.ts",
                           "frontend/tests/workspace-layout.spec.ts", "frontend/tests/native-menu.spec.ts",
                           "frontend/tests/visual-layout.ts", "frontend/package-lock.json",
                           "scripts/experience_server.py", "scripts/collection_review_fixture.py",
                           "scripts/collection_review_evidence.py", "scripts/desktop_assets.py",
                           "scripts/check_workspace_polish.cjs",
                           "scripts/stage_native_ui.py", "scripts/installed_tray_check.py",
                           "src/facetmark/workbench.py", "src/facetmark/api.py", "src/facetmark/library.py",
                           "src/facetmark/importers/base.py", "tests/test_workbench.py",
                           "desktop/splash/index.html", "desktop/splash/loading.js",
                           "desktop/splash/native-ui.css", "desktop/splash/mark.svg", "desktop/splash/tray.html", "desktop/splash/tray.js",
                           "desktop/src-tauri/src/tray_menu.rs", "desktop/src-tauri/src/window_state.rs", "desktop/src-tauri/src/main.rs",
                           "desktop/src-tauri/capabilities/tray-menu.json",
                           "desktop/src-tauri/tauri.conf.json", ".github/workflows/collection-review.yml"])]
    captures = sorted(destination.glob("*.png"))
    review_path = destination / "review.json"
    review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else {}
    provenance = {"revision": os.environ.get("GITHUB_SHA"), "run": os.environ.get("GITHUB_RUN_ID"),
                  "data": "CI temporary SQLite collection; synthetic content only; no personal browser profile",
                  "capture_count": len(captures),
                  "main_journey_capture_count": len(review.get("captures", [])),
                  "additional_state_capture_count": sum(p.stem.startswith("polish-") for p in captures),
                  "native_startup_scope": "Browser-rendered splash HTML with a synthetic Tauri restart bridge; "
                                          "installed Windows startup and lifecycle require the desktop workflow",
                  "main_journey_failure": review.get("failure"),
                  "source": {p.as_posix(): digest(p) for p in sources if p.exists()},
                  "captures": {p.name: digest(p) for p in destination.iterdir() if p.is_file()}}
    (destination / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    figures = "\n".join(f'<figure id="{html.escape(p.stem)}"><figcaption>{html.escape(caption(p))}</figcaption>'
                        f'<a href="{html.escape(p.name)}"><img src="{html.escape(p.name)}" alt="{html.escape(p.stem)}"></a></figure>'
                        for p in captures)
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    page += '<title>Facetmark 收藏工作区 · 本轮实际渲染</title><style>body{margin:0;padding:32px;background:#e9eff5;color:#162b43;'
    page += 'font:16px/1.7 system-ui,sans-serif}main{max-width:1440px;margin:auto}h1{font-size:28px}figure{margin:32px 0}'
    page += 'figcaption{margin-bottom:10px}img,video{max-width:100%;height:auto;border-radius:24px}a{color:#235fe5}</style><main>'
    page += '<h1>Facetmark 收藏工作区 · 细节打磨</h1><p>本轮页面与操作状态在 GitHub Actions 渲染；全部使用隔离合成数据。新增改动仍待用户复评。</p>'
    page += f'<p>Source: <code>{html.escape(os.environ.get("GITHUB_SHA", ""))}</code></p>'
    page += f'<p>共 {len(captures)} 张画面；其中主收藏旅程 {len(review.get("captures", []))} 张。其余为专项状态检查。</p>'
    page += '<p>启动 HTML 的截图使用合成重启桥接，只说明页面及指定状态；安装后的 Windows 启动与生命周期由桌面工作流另验。各用例是否通过请查看同包 Playwright 报告。</p>'
    page += '<p>专项启动、配对、来源发现和导入用例以合成响应控制失败与等待状态；主收藏旅程使用真实接口及临时 SQLite 库。没有访问个人浏览器资料。</p>'
    if review.get("failure"):
        page += '<p>主收藏旅程记录了失败；下方保留失败前的实际画面，请同时查看操作记录和测试报告。</p>'
    if video.exists():
        page += '<video controls src="collection-interactions.mp4"></video>'
    links = [("review.json", "主收藏操作记录"), ("capsule-frame-samples.json", "胶囊中间帧采样"),
             ("provenance.json", "源码与媒体版本")]
    page += figures + '<p>' + ' · '.join(f'<a href="{file}">{label}</a>' for file, label in links
                                       if (destination / file).exists()) + '</p></main></html>'
    (destination / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
