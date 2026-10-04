"""Fail packaging when the shared, offline workbench is absent from the wheel."""

from pathlib import Path
from tarfile import open as open_tar
from zipfile import ZipFile

wheels = list(Path("dist").glob("*.whl"))
sdists = list(Path("dist").glob("*.tar.gz"))
assert wheels and sdists, "Expected both wheel and source distribution"
for wheel in wheels:
    with ZipFile(wheel) as bundle:
        names = bundle.namelist()
        index = "facetmark/web/dist/index.html"
        assert index in names, "React index is missing from wheel"
        assert 'id="root"' in bundle.read(index).decode()
        assert any(n.startswith("facetmark/web/dist/static/") and n.endswith(".js") for n in names)
        print(f"{wheel.name}: shared React entry and assets present")

for sdist in sdists:
    with open_tar(sdist) as bundle:
        names = bundle.getnames()
        assert any(n.endswith("/src/facetmark/web/dist/index.html") for n in names), "React entry missing from source distribution"
        assert any("/src/facetmark/web/dist/static/" in n and n.endswith(".js") for n in names), "React assets missing from source distribution"
        print(f"{sdist.name}: shared React resources present")
