"""Fail packaging when the shared, offline workbench is absent from the wheel."""

from pathlib import Path
from zipfile import ZipFile

for wheel in Path("dist").glob("*.whl"):
    with ZipFile(wheel) as bundle:
        names = bundle.namelist()
        index = "facetmark/web/dist/index.html"
        assert index in names, "React index is missing from wheel"
        assert 'id="root"' in bundle.read(index).decode()
        assert any(n.startswith("facetmark/web/dist/static/") and n.endswith(".js") for n in names)
        print(f"{wheel.name}: shared React entry and assets present")
