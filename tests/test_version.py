"""One version number, five places that state it.

``facetmark.__version__`` sat at 1.3.0 through the whole of 1.4.0, so
``facetmark version``, ``GET /health`` and the OpenAPI document all reported a
release that was two behind while ``pyproject.toml`` said otherwise. Nothing
failed, which is the problem: a version that only ever gets read by humans
drifts silently.

These tests are the cheapest possible fix -- no build step, no
``importlib.metadata`` lookup that a source checkout would answer differently
from an installed wheel, just the five files read as text and compared.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import facetmark
from facetmark.api import create_app
from facetmark.config import Settings

ROOT = Path(__file__).resolve().parents[1]

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _pyproject_version() -> str:
    # tomllib is 3.11+; this package supports 3.10, and the line is
    # unambiguous -- the only other `version` in the file is ruff's
    # `target-version`.
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    found = re.findall(r'^version = "([^"]+)"$', text, re.M)
    assert len(found) == 1, f"expected one project version line, got {found}"
    return found[0]


def _changelog_releases() -> list[tuple[str, str]]:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return re.findall(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", text, re.M)


def _cff() -> dict[str, str]:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    return {
        "version": re.search(r"^version: (.+)$", text, re.M).group(1).strip(),
        "date": re.search(r"^date-released: '?([\d-]+)'?$", text, re.M).group(1),
    }


class TestEveryFileAgreesOnTheVersion:
    def test_the_package_matches_the_project_metadata(self):
        assert facetmark.__version__ == _pyproject_version()

    def test_it_looks_like_a_version(self):
        assert SEMVER.match(facetmark.__version__)

    def test_the_browser_extension_matches(self):
        pkg = json.loads((ROOT / "extension" / "package.json").read_text(encoding="utf-8"))
        assert pkg["version"] == facetmark.__version__

    def test_the_citation_file_matches(self):
        assert _cff()["version"] == facetmark.__version__

    def test_the_newest_released_changelog_heading_matches(self):
        releases = _changelog_releases()
        assert releases, "CHANGELOG.md has no released section"
        assert releases[0][0] == facetmark.__version__

    def test_the_citation_date_is_the_release_date(self):
        assert _cff()["date"] == _changelog_releases()[0][1]


class TestTheExtensionManifestCannotDriftAgain:
    """The manifest is stamped at build time, so there is nothing to keep in sync.

    Checked from Python because the build is the only thing that produces a
    manifest and ``dist/`` is not committed; these two assertions are the
    cheapest way to notice if someone puts the literal back.
    """

    def test_the_source_manifest_declares_no_version(self):
        src = json.loads(
            (ROOT / "extension" / "src" / "manifest.json").read_text(encoding="utf-8")
        )
        assert "version" not in src
        assert src["manifest_version"] == 3

    def test_the_build_stamps_the_package_version(self):
        build = (ROOT / "extension" / "build.mjs").read_text(encoding="utf-8")
        assert "version: pkg.version" in build
        assert 'JSON.parse(await readFile("package.json"' in build


class TestTheChangelogIsOrdered:
    def test_releases_are_newest_first(self):
        keys = [tuple(int(p) for p in v.split(".")) for v, _ in _changelog_releases()]
        assert keys == sorted(keys, reverse=True)

    def test_no_version_is_released_twice(self):
        versions = [v for v, _ in _changelog_releases()]
        assert len(versions) == len(set(versions))


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(data_dir=tmp_path / "fm", use_mock_provider=True))
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client) -> dict:
    return {"Authorization": f"Bearer {client.app.state.fm.token}"}


class TestTheServiceReportsIt:
    def test_health_reports_the_same_string(self, client, auth):
        # The endpoint an operator actually reads when asking "what is running
        # on this box" -- the exact place the 1.3.0 drift was visible.
        body = client.get("/health", headers=auth).json()
        assert body["version"] == facetmark.__version__

    def test_the_openapi_document_agrees(self, client):
        assert client.get("/openapi.json").json()["info"]["version"] == (
            facetmark.__version__
        )


@pytest.mark.parametrize("path", ["pyproject.toml", "CITATION.cff", "CHANGELOG.md"])
def test_the_files_this_reads_exist(path):
    assert (ROOT / path).is_file()
