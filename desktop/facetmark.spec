# Build in a clean CI virtual environment, never the developer's global Python.
from PyInstaller.utils.hooks import collect_all, collect_data_files
from pathlib import Path

root = Path(SPECPATH).parent

datas = collect_data_files('facetmark', includes=['web/**/*'])
binaries, hiddenimports = [], []
for package in ('sqlite_vec', 'jieba', 'trafilatura', 'readability'):
    data, binary, hidden = collect_all(package)
    datas += data
    binaries += binary
    hiddenimports += hidden
a = Analysis(
    [str(root / 'desktop/freeze.py')], pathex=[str(root / 'src')], datas=datas, binaries=binaries,
    hiddenimports=hiddenimports + ['uvicorn.logging', 'uvicorn.loops.asyncio',
        'uvicorn.protocols.http.h11_impl', 'uvicorn.lifespan.on'],
    excludes=['torch', 'transformers', 'sentence_transformers', 'pytest', 'IPython',
              'tkinter', 'matplotlib', 'scipy', 'pandas'],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='facetmark-service',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='facetmark-service')
