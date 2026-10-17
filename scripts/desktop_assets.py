"""CI-only staging of the frozen backend and the small geometric app icon."""
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
source = root / 'dist/facetmark-service'
dest = root / 'desktop/src-tauri/binaries'
dest.mkdir(parents=True, exist_ok=True)
shutil.copy2(source / 'facetmark-service.exe', dest / 'facetmark-service-x86_64-pc-windows-msvc.exe')
shutil.copytree(source / '_internal', dest / '_internal', dirs_exist_ok=True)
icons = root / 'desktop/src-tauri/icons'
icons.mkdir(parents=True, exist_ok=True)
im = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((16, 16, 240, 240), radius=54, fill='#7554AD')
d.polygon([(78, 58), (178, 58), (178, 198), (128, 169), (78, 198)], fill='#FFFFFF')
d.rounded_rectangle((98, 89, 158, 99), radius=5, fill='#7554AD')
d.rounded_rectangle((98, 115, 143, 125), radius=5, fill='#B9A6D6')
im.save(icons / 'icon.png')
im.save(icons / 'icon.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
