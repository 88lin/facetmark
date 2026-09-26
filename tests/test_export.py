"""``facetmark export``: a backup is a file you can read back.

The assertion that matters is the round trip -- export, import into an empty
library, and the two libraries hold the same rows. Everything else here is about
the places a round trip is lossy and whether it says so.
"""

from __future__ import annotations

import json

import pytest

from facetmark.config import Settings, reset_settings
from facetmark.db import open_db
from facetmark.importers import detect_and_parse, import_bookmarks
from facetmark.service import ExportRefused, export_bookmarks, save_bookmark

SEED = [
    ("https://github.com/pgvector/pgvector", "pgvector", "study", ["work", "rust"]),
    ("https://sqlite.org/fts5.html", "SQLite FTS5", "study", ["reading"]),
    ("https://example.com/plain", "plain page", "", []),
    ("https://cjk.example/tool", "中文标题", "读物", ["工具"]),
]


@pytest.fixture()
def st(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path, use_mock_provider=True,
                    health_enable_external=False)


@pytest.fixture()
def lib(st):
    conn = open_db(":memory:")
    for url, title, folder, tags in SEED:
        save_bookmark(conn, url, title=title, folder=folder, tags=tags, settings=st)
    conn.commit()
    yield conn
    conn.close()


def rows(conn) -> list[tuple]:
    return sorted(
        (r["url"], r["title"], r["folder"], r["folder_depth"], r["tags"])
        for r in conn.execute(
            "SELECT url, title, folder, folder_depth, tags FROM bookmark")
    )


class TestTheRoundTrip:
    def test_an_export_reimports_into_an_identical_library(self, lib, st, tmp_path):
        payload = export_bookmarks(lib)
        path = tmp_path / "backup.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        fresh = open_db(":memory:")
        try:
            stats = import_bookmarks(fresh, path, settings=st)
            assert stats.source == "facetmark_json"
            assert not stats.warnings, stats.warnings
            assert rows(fresh) == rows(lib)
        finally:
            fresh.close()

    def test_the_importer_recognises_it_without_being_told(self, lib):
        text = json.dumps(export_bookmarks(lib), ensure_ascii=False)
        assert detect_and_parse(text).source == "facetmark_json"

    def test_a_cjk_title_and_tag_survive(self, lib, st, tmp_path):
        path = tmp_path / "b.json"
        path.write_text(json.dumps(export_bookmarks(lib), ensure_ascii=False),
                        encoding="utf-8")
        fresh = open_db(":memory:")
        try:
            import_bookmarks(fresh, path, settings=st)
            got = fresh.execute(
                "SELECT title, tags FROM bookmark WHERE url LIKE '%cjk%'").fetchone()
            assert got["title"] == "中文标题"
            assert "工具" in got["tags"]
        finally:
            fresh.close()

    def test_two_exports_of_an_unchanged_library_differ_only_in_the_header(self, lib):
        a, b = export_bookmarks(lib), export_bookmarks(lib)
        assert a["bookmarks"] == b["bookmarks"]


class TestWhatItExports:
    def test_the_query_selects_a_subset(self, lib):
        got = export_bookmarks(lib, "tag:work")
        assert [b["url"] for b in got["bookmarks"]] == [
            "https://github.com/pgvector/pgvector"]
        assert got["facetmark"]["count"] == 1
        assert got["facetmark"]["query"] == "tag:work"

    def test_a_negation_selects_the_rest(self, lib):
        urls = {b["url"] for b in export_bookmarks(lib, "-tag:work")["bookmarks"]}
        assert "https://github.com/pgvector/pgvector" not in urls
        assert len(urls) == len(SEED) - 1

    def test_free_text_is_refused_with_the_fields_that_work(self, lib):
        """Ranking has no place in a backup: there is no honest answer to how
        many of a ranking belong in the file."""
        with pytest.raises(ExportRefused, match="filters, not free text"):
            export_bookmarks(lib, "postgres")

    def test_derived_data_is_left_out_by_default(self, lib):
        assert all("derived" not in b for b in export_bookmarks(lib)["bookmarks"])

    def test_full_adds_it_and_the_importer_still_reads_the_file(self, lib, st, tmp_path):
        payload = export_bookmarks(lib, full=True)
        assert all("derived" in b for b in payload["bookmarks"])
        path = tmp_path / "full.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        fresh = open_db(":memory:")
        try:
            import_bookmarks(fresh, path, settings=st)
            assert rows(fresh) == rows(lib)
        finally:
            fresh.close()

    def test_an_empty_library_exports_an_empty_list(self, st):
        conn = open_db(":memory:")
        try:
            got = export_bookmarks(conn)
            assert got["bookmarks"] == [] and got["facetmark"]["count"] == 0
        finally:
            conn.close()


class TestTheFolderPathIsLossyAndSaysSo:
    """The database stores a display path and forbids splitting it, so
    `folder_depth` is what tells the reader how to read the string back."""

    @pytest.mark.parametrize("folder,depth,expected", [
        ("read/write ratio", 1, ["read/write ratio"]),
        ("study/deep", 2, ["study", "deep"]),
        ("a/b", 0, ["a", "b"]),
    ])
    def test_depth_decides_how_the_string_is_read(self, folder, depth, expected):
        doc = {"facetmark": {"version": 1}, "bookmarks": [
            {"url": "https://x.test/", "title": "t",
             "folder": folder, "folder_depth": depth},
        ]}
        got = detect_and_parse(json.dumps(doc))
        assert got.bookmarks[0].folder_path == expected
        assert not got.warnings

    def test_a_disagreement_neither_reading_explains_is_reported(self):
        doc = {"facetmark": {"version": 1}, "bookmarks": [
            {"url": "https://x.test/", "title": "t", "folder": "a/b/c",
             "folder_depth": 2},
        ]}
        got = detect_and_parse(json.dumps(doc))
        assert got.warnings and "could not be reconstructed" in got.warnings[0]

    def test_a_folder_named_with_a_slash_round_trips(self, st):
        """What `POST /bookmark` records when handed `folder="read/write ratio"`."""
        conn = open_db(":memory:")
        save_bookmark(conn, "https://x.test/", title="t",
                      folder="read/write ratio", settings=st)
        conn.commit()
        text = json.dumps(export_bookmarks(conn), ensure_ascii=False)
        got = detect_and_parse(text)
        assert got.bookmarks[0].folder == "read/write ratio"
        assert not got.warnings
        conn.close()


class TestAFileFromAnotherVersion:
    def test_a_newer_format_is_read_and_flagged(self):
        doc = {"facetmark": {"version": 99}, "bookmarks": [
            {"url": "https://x.test/", "title": "t", "unknown_key": 1},
        ]}
        got = detect_and_parse(json.dumps(doc))
        assert len(got.bookmarks) == 1
        assert got.warnings and "format version 99" in got.warnings[0]

    def test_a_bookmark_without_a_url_is_skipped(self):
        doc = {"facetmark": {"version": 1}, "bookmarks": [
            {"title": "no url"}, {"url": "  ", "title": "blank"},
            {"url": "https://ok.test/", "title": "kept"},
        ]}
        got = detect_and_parse(json.dumps(doc))
        assert [b.url for b in got.bookmarks] == ["https://ok.test/"]

    def test_chrome_json_still_wins_its_own_files(self):
        """Both formats are JSON objects; the marker is what separates them."""
        chrome = {"roots": {"bookmark_bar": {"type": "folder", "name": "Bar",
                                             "children": [
            {"type": "url", "name": "n", "url": "https://c.test/",
             "date_added": "13300000000000000"}]}}}
        assert detect_and_parse(json.dumps(chrome)).source == "chrome_json"


class TestTheCommand:
    def _run(self, args, tmp_path, monkeypatch):
        from typer.testing import CliRunner

        from facetmark import cli

        monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("FACETMARK_USE_MOCK_PROVIDER", "1")
        reset_settings()
        try:
            return CliRunner().invoke(cli.app, args)
        finally:
            reset_settings()

    def test_it_writes_to_stdout_by_default(self, tmp_path, monkeypatch):
        r = self._run(["export", "-"], tmp_path, monkeypatch)
        assert r.exit_code == 0, r.output
        assert json.loads(r.stdout)["facetmark"]["version"] == 1

    def test_it_writes_to_a_file(self, tmp_path, monkeypatch):
        out = tmp_path / "out.json"
        r = self._run(["export", str(out)], tmp_path, monkeypatch)
        assert r.exit_code == 0, r.output
        assert json.loads(out.read_text(encoding="utf-8"))["bookmarks"] == []

    def test_free_text_exits_two_without_writing(self, tmp_path, monkeypatch):
        out = tmp_path / "nope.json"
        r = self._run(["export", str(out), "postgres"], tmp_path, monkeypatch)
        assert r.exit_code == 2
        assert not out.exists()
