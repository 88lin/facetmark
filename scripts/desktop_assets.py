"""CI-only staging and supersampled rendering of the porcelain folded-F icon."""
import hashlib
import json
import os
import shutil
from pathlib import Path

from brand_assets import app_icon, icon_evidence
from PIL import Image

if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
    raise SystemExit('Desktop asset staging and rendering require a disposable GitHub-hosted runner')





root = Path(__file__).resolve().parents[1]
source = root / 'dist/facetmark-service'
dest = root / 'desktop/src-tauri/binaries'
dest.mkdir(parents=True, exist_ok=True)
shutil.copy2(source / 'facetmark-service.exe', dest / 'facetmark-service-x86_64-pc-windows-msvc.exe')
shutil.copytree(source / '_internal', dest / '_internal', dirs_exist_ok=True)
icons = root / 'desktop/src-tauri/icons'
icons.mkdir(parents=True, exist_ok=True)
im = app_icon()
im.save(icons / 'icon.png')
sizes = [(size, size) for size in [16, 20, 24, 32, 48, 64, 128, 256]]
im.save(icons / 'icon.ico', sizes=sizes)
with Image.open(icons / 'icon.ico') as encoded:
    assert encoded.ico.sizes() == set(sizes)
    for size in sizes:
        assert encoded.ico.getimage(size).size == size
evidence = root / '.desktop-build/evidence'
icon_evidence(im, evidence)
shutil.copy2(icons / 'icon.ico', evidence / 'app-icon.ico')
(evidence / 'desktop-icon.json').write_text(json.dumps({
    'revision': os.environ.get('GITHUB_SHA'), 'direction': 'porcelain tile and blue folded-F geometry',
    'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'renderer_sha256': hashlib.sha256((root / 'scripts/brand_assets.py').read_bytes()).hexdigest(),
    'png_sha256': hashlib.sha256((icons / 'icon.png').read_bytes()).hexdigest(),
    'ico_sha256': hashlib.sha256((icons / 'icon.ico').read_bytes()).hexdigest(),
    'encoded_sizes': sizes, 'user_review': 'pending',
}, indent=2), encoding='utf-8')
