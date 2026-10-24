"""Stage the same offline text faces for the native startup and tray windows."""
import os
import shutil
from pathlib import Path

if os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("Stage native UI assets in GitHub Actions only")

root = Path(__file__).resolve().parents[1]
destination = root / "desktop/splash/fonts"
destination.mkdir(parents=True, exist_ok=True)
for name in ["inter-latin.woff2", "noto-sans-sc.woff2"]:
    shutil.copy2(root / "frontend/src/assets/fonts" / name, destination / name)
