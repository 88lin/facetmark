"""Import pipeline: both file formats, de-duplication and idempotency."""

from __future__ import annotations

import datetime as dt

import pytest

from facetmark.config import Settings
from facetmark.importers import (
    chrome_json,
    decode_bookmark_bytes,
    detect_and_parse,
    import_bookmarks,
    netscape_html,
    read_text,
)


def _year(ts: int) -> int:
    # Not fromtimestamp: Windows raises OSError on negative values, and the
    # 1601 assertions below depend on those working.
    return (dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
            + dt.timedelta(seconds=ts)).year


def _rows(conn):
    return conn.execute("SELECT * FROM bookmark ORDER BY id").fetchall()


class TestFormatDetection:
    def test_netscape_is_recognised(self, netscape_sample):
        assert netscape_html.looks_like_netscape(netscape_sample)
        assert not chrome_json.looks_like_chrome_json(netscape_sample)
        assert detect_and_parse(netscape_sample).source == "netscape_html"

    def test_chrome_json_is_recognised(self, chrome_sample):
        assert chrome_json.looks_like_chrome_json(chrome_sample)
        assert detect_and_parse(chrome_sample).source == "chrome_json"

    def test_units_differ_between_the_two_formats(self, netscape_sample, chrome_sample):
        assert detect_and_parse(netscape_sample).timestamp_unit == "unix_s"
        assert detect_and_parse(chrome_sample).timestamp_unit == "webkit_us"

    def test_both_formats_yield_the_same_era(self, netscape_sample, chrome_sample):
        for sample in (netscape_sample, chrome_sample):
            years = {
                _year(int(b.date_added_raw))
                for b in detect_and_parse(sample).bookmarks
                if b.date_added_raw
            }
            assert years and all(2000 < y < 2100 for y in years)


class TestNetscapeParsing:
    def test_folder_hierarchy_is_reconstructed(self, netscape_sample):
        r = detect_and_parse(netscape_sample)
        by_url = {b.url: b for b in r.bookmarks}
        assert by_url["https://example.com/crdt-guide"].folder == "收藏夹栏/study"
        assert by_url["https://github.com/pola-rs/polars#readme"].folder == "收藏夹栏/工具"
        # A bookmark that is a *sibling* of a subfolder: the </DL> that closed
        # "工具" must pop exactly one level, not unwind the whole stack.
        assert by_url["https://example.net/sibling"].folder == "收藏夹栏"
        # Loose item in the root <DL>, outside every H3. Firefox and hand-edited
        # exports do produce these; the correct answer is "no folder", not the
        # name of the folder that happens to precede it.
        assert by_url["http://www.plain.example/no-folder/"].folder == ""

    def test_dd_note_is_attached_to_the_preceding_bookmark(self, netscape_sample):
        r = detect_and_parse(netscape_sample)
        note = next(b.note for b in r.bookmarks if b.url == "https://example.com/crdt-guide")
        assert "选型" in note

    def test_base64_favicons_do_not_leak_into_titles(self, netscape_sample):
        r = detect_and_parse(netscape_sample)
        assert all("base64" not in b.title for b in r.bookmarks)

    def test_cjk_titles_survive(self, netscape_sample):
        titles = [b.title for b in detect_and_parse(netscape_sample).bookmarks]
        assert "用 Automerge 做协同编辑的 CRDT 实践" in titles

    def test_html_entities_are_unescaped(self, netscape_sample):
        urls = [b.url for b in detect_and_parse(netscape_sample).bookmarks]
        assert "https://example.com/crdt-guide?utm_source=twitter&fbclid=abc" in urls

    def test_parser_is_not_line_dependent(self, netscape_sample):
        """Firefox and Safari do not put one element per line."""
        squashed = netscape_sample.replace("\n", " ")
        a = detect_and_parse(netscape_sample)
        b = detect_and_parse(squashed)
        assert len(b.bookmarks) == len(a.bookmarks)
        assert {x.folder for x in b.bookmarks} == {x.folder for x in a.bookmarks}

    def test_folder_and_depth_counts(self, netscape_sample):
        r = detect_and_parse(netscape_sample)
        assert r.folders == 3
        assert r.max_depth == 2

    def test_empty_document_warns_instead_of_raising(self):
        r = detect_and_parse("<html><body>nothing here</body></html>")
        assert r.bookmarks == []
        assert any("no <DT>" in w for w in r.warnings)


class TestChromeJsonParsing:
    def test_all_roots_are_walked(self, chrome_sample):
        r = detect_and_parse(chrome_sample)
        urls = {b.url for b in r.bookmarks}
        assert "https://github.com/pola-rs/polars#readme" in urls  # from "other"
        assert "https://example.com/crdt-guide" in urls  # from "bookmark_bar"

    def test_nested_folder_path(self, chrome_sample):
        r = detect_and_parse(chrome_sample)
        b = next(x for x in r.bookmarks if "fts5" in x.url)
        assert b.folder.endswith("study")

    def test_malformed_json_is_reported_not_raised(self):
        r = chrome_json.parse('{"version": 1}')
        assert r.bookmarks == []
        assert any("roots" in w for w in r.warnings)

    def test_walk_order_is_stable(self, chrome_sample):
        a = [b.url for b in detect_and_parse(chrome_sample).bookmarks]
        b = [b.url for b in detect_and_parse(chrome_sample).bookmarks]
        assert a == b


class TestDeduplication:
    def test_tracking_only_duplicate_is_merged(self, conn, netscape_sample, settings):
        stats = import_bookmarks(conn, content=netscape_sample, settings=settings)
        assert stats.merged_duplicates == 1
        urls = [r["url_norm"] for r in _rows(conn)]
        assert urls.count("https://example.com/crdt-guide") == 1

    def test_merge_keeps_the_earliest_date_added(self, conn, netscape_sample, settings):
        import_bookmarks(conn, content=netscape_sample, settings=settings)
        row = conn.execute(
            "SELECT date_added FROM bookmark WHERE url_norm='https://example.com/crdt-guide'"
        ).fetchone()
        assert row["date_added"] == 1690391875  # not ...999

    def test_merge_keeps_the_longer_title(self, conn, netscape_sample, settings):
        import_bookmarks(conn, content=netscape_sample, settings=settings)
        row = conn.execute(
            "SELECT title FROM bookmark WHERE url_norm='https://example.com/crdt-guide'"
        ).fetchone()
        assert row["title"] == "用 Automerge 做协同编辑的 CRDT 实践"

    def test_anchor_meaningful_fragments_are_not_merged(self, conn, settings):
        doc = (
            "<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p>"
            '<DT><A HREF="https://github.com/o/r#readme" ADD_DATE="1690000000">a</A>'
            '<DT><A HREF="https://github.com/o/r#license" ADD_DATE="1690000001">b</A>'
            "</DL><p>"
        )
        import_bookmarks(conn, content=doc, settings=settings)
        assert len(_rows(conn)) == 2

    def test_ordinary_fragments_are_merged(self, conn, settings):
        doc = (
            "<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p>"
            '<DT><A HREF="https://blog.example/p#one" ADD_DATE="1690000000">a</A>'
            '<DT><A HREF="https://blog.example/p#two" ADD_DATE="1690000001">b</A>'
            "</DL><p>"
        )
        import_bookmarks(conn, content=doc, settings=settings)
        assert len(_rows(conn)) == 1


class TestIdempotency:
    def test_second_import_adds_nothing(self, conn, netscape_sample, settings):
        a = import_bookmarks(conn, content=netscape_sample, settings=settings)
        n = len(_rows(conn))
        b = import_bookmarks(conn, content=netscape_sample, settings=settings)
        assert len(_rows(conn)) == n
        assert b.inserted == 0
        assert b.updated == a.inserted

    def test_date_added_never_moves_forward(self, conn, settings):
        early = (
            "<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p>"
            '<DT><A HREF="https://e.com/p" ADD_DATE="1600000000">t</A></DL><p>'
        )
        late = early.replace("1600000000", "1700000000")
        import_bookmarks(conn, content=early, settings=settings)
        import_bookmarks(conn, content=late, settings=settings)
        assert conn.execute("SELECT date_added FROM bookmark").fetchone()[0] == 1600000000

    def test_reimport_does_not_wipe_fetched_content(self, conn, netscape_sample, settings):
        import_bookmarks(conn, content=netscape_sample, settings=settings)
        bid = _rows(conn)[0]["id"]
        conn.execute(
            "INSERT INTO content(bookmark_id, body_text, body_hash, char_count)"
            " VALUES(?,?,?,?)",
            (bid, "fetched body", "h", 12),
        )
        import_bookmarks(conn, content=netscape_sample, settings=settings)
        row = conn.execute("SELECT body_text FROM content WHERE bookmark_id=?", (bid,)).fetchone()
        assert row["body_text"] == "fetched body"

    def test_reimport_preserves_body_in_the_lexical_index(self, conn, netscape_sample, settings):
        import_bookmarks(conn, content=netscape_sample, settings=settings)
        bid = _rows(conn)[0]["id"]
        conn.execute(
            "INSERT INTO content(bookmark_id, body_text, body_seg, body_hash, char_count)"
            " VALUES(?,?,?,?,?)",
            (bid, "一段可检索的正文", "一段 可 检索 的 正文", "h", 8),
        )
        import_bookmarks(conn, content=netscape_sample, settings=settings)
        hit = conn.execute("SELECT rowid FROM fts_seg WHERE fts_seg MATCH ?", ('"检索"',)).fetchone()
        assert hit is not None and int(hit[0]) == bid


class TestMetadataAndFlags:
    def test_non_indexable_rows_are_flagged_not_dropped(self, conn, netscape_sample, settings):
        stats = import_bookmarks(conn, content=netscape_sample, settings=settings)
        assert stats.non_indexable == 1
        row = conn.execute("SELECT * FROM bookmark WHERE url LIKE 'data:%'").fetchone()
        assert row is not None and row["indexable"] == 0

    def test_domain_is_derived(self, conn, netscape_sample, settings):
        import_bookmarks(conn, content=netscape_sample, settings=settings)
        row = conn.execute(
            "SELECT domain, host FROM bookmark WHERE url_norm LIKE '%docs.example.org%'"
        ).fetchone()
        assert row["host"] == "docs.example.org"
        assert row["domain"] == "example.org"

    def test_privacy_excluded_domain_is_flagged(self, conn, netscape_sample, tmp_path):
        st = Settings(
            data_dir=tmp_path, use_mock_provider=True,
            privacy_excluded_domains=("example.com",),
        )
        stats = import_bookmarks(conn, content=netscape_sample, settings=st)
        assert stats.privacy_skipped >= 1
        row = conn.execute(
            "SELECT privacy_skipped FROM bookmark WHERE host='example.com'"
        ).fetchone()
        assert row["privacy_skipped"] == 1

    def test_privacy_matching_covers_subdomains(self, conn, tmp_path):
        doc = (
            "<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p>"
            '<DT><A HREF="https://mail.private.test/x" ADD_DATE="1690000000">m</A></DL><p>'
        )
        st = Settings(data_dir=tmp_path, privacy_excluded_domains=("private.test",))
        import_bookmarks(conn, content=doc, settings=st)
        assert conn.execute("SELECT privacy_skipped FROM bookmark").fetchone()[0] == 1

    def test_title_is_immediately_searchable(self, conn, netscape_sample, settings):
        import_bookmarks(conn, content=netscape_sample, settings=settings)
        hit = conn.execute(
            "SELECT rowid FROM fts_seg WHERE fts_seg MATCH ?", ('"分词"',)
        ).fetchone()
        assert hit is not None

    def test_note_is_searchable(self, conn, netscape_sample, settings):
        import_bookmarks(conn, content=netscape_sample, settings=settings)
        hit = conn.execute(
            "SELECT rowid FROM fts_seg WHERE fts_seg MATCH ?", ('"选型"',)
        ).fetchone()
        assert hit is not None


class TestReadText:
    @pytest.mark.parametrize(
        "enc",
        ["utf-8", "utf-8-sig", "gb18030"],
    )
    def test_encodings_round_trip(self, tmp_path, enc):
        p = tmp_path / f"b-{enc}.html"
        content = '<DT><A HREF="https://e.com/x" ADD_DATE="1690000000">中文标题</A>'
        p.write_bytes(content.encode(enc))
        assert "中文标题" in read_text(p)

    def test_undecodable_bytes_do_not_raise(self, tmp_path):
        p = tmp_path / "bad.html"
        p.write_bytes(b"\xff\xfe\x00\x01<DT><A HREF=\"https://e.com\">x</A>")
        assert isinstance(read_text(p), str)

    def test_the_ladder_is_shared_with_callers_that_have_no_file(self):
        """``read_text`` is this function plus a ``read_bytes``.

        The web upload holds a request body rather than a path, and when it had
        its own decode -- UTF-8 with ``errors="replace"`` -- it stored
        ``Caf\ufffd`` and reported success. One ladder, two entry points.
        """
        assert decode_bookmark_bytes("Caf\xe9 notes".encode("cp1252")) == "Caf\xe9 notes"
        assert decode_bookmark_bytes("\u4e2d\u6587\u6807\u9898".encode("gb18030")) == "\u4e2d\u6587\u6807\u9898"
        assert decode_bookmark_bytes("Caf\xe9 \u4e2d\u6587".encode("utf-8")) == "Caf\xe9 \u4e2d\u6587"
        assert decode_bookmark_bytes(b"\xef\xbb\xbfCaf\xc3\xa9") == "Caf\xe9"
        assert isinstance(decode_bookmark_bytes(b"\x81\x8d\x8f\x90\x9d"), str)

    def test_declared_windows_charset_beats_ambiguous_gb18030(self):
        raw = (
            b'<META HTTP-EQUIV="Content-Type" '
            b'CONTENT="text/html; charset=windows-1252">'
            b'<DT><A HREF="https://e.com/x" ADD_DATE="1690000000">'
            b'Sqlite intern\xe4ls</A>'
        )
        assert "Sqlite intern\u00e4ls" in decode_bookmark_bytes(raw)

    def test_compact_declared_charset_is_supported(self):
        raw = (
            b'<meta charset="windows-1252">'
            b'<DT><A HREF="https://e.com/x" ADD_DATE="1690000000">'
            b'Caf\xe9 notes</A>'
        )
        assert "Caf\u00e9 notes" in decode_bookmark_bytes(raw)

    def test_read_text_delegates_rather_than_repeating_the_ladder(self, tmp_path):
        p = tmp_path / "b.html"
        raw = "Caf\xe9 notes".encode("cp1252")
        p.write_bytes(raw)
        assert read_text(p) == decode_bookmark_bytes(raw)


class TestFolderPathsMeasuredOnRealData:
    """Two properties the 1697-entry calibration export made visible.

    Neither is exotic: 4 of that file's 96 folder names contain a literal "/",
    and 124 of its 1697 bookmarks (7.3%) sit loose in the root <DL> outside
    every folder.
    """

    SLASHY = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
    <DT><H3>AI/ML</H3>
    <DL><p>
        <DT><A HREF="https://a.example/1" ADD_DATE="1700000000">in a slashy folder</A>
    </DL><p>
    <DT><H3>AI</H3>
    <DL><p>
        <DT><H3>ML</H3>
        <DL><p>
            <DT><A HREF="https://a.example/2" ADD_DATE="1700000001">in a nested folder</A>
        </DL><p>
    </DL><p>
    <DT><A HREF="https://a.example/3" ADD_DATE="1700000002">loose at the root</A>
</DL><p>
"""

    def test_folder_path_is_authoritative_display_string_is_not(self):
        by_url = {b.url: b for b in detect_and_parse(self.SLASHY).bookmarks}
        one, two = by_url["https://a.example/1"], by_url["https://a.example/2"]
        # Both render identically...
        assert one.folder == two.folder == "AI/ML"
        # ...but they are different folders at different depths, and splitting
        # the display string on "/" gets the first one wrong.
        assert one.folder_path == ["AI/ML"] and one.folder_depth == 1
        assert two.folder_path == ["AI", "ML"] and two.folder_depth == 2
        assert one.folder.split("/") != one.folder_path

    def test_the_ambiguity_is_reported_not_swallowed(self):
        r = detect_and_parse(self.SLASHY)
        assert any("ambiguous" in w and "AI/ML" in w for w in r.warnings)

    def test_loose_root_bookmarks_get_no_folder_and_depth_zero(self):
        b = {x.url: x for x in detect_and_parse(self.SLASHY).bookmarks}["https://a.example/3"]
        assert b.folder == "" and b.folder_path == [] and b.folder_depth == 0

    def test_folder_depth_reaches_the_database(self, conn):
        import_bookmarks(conn, content=self.SLASHY)
        rows = dict(
            conn.execute("SELECT url, folder_depth FROM bookmark").fetchall()  # type: ignore[arg-type]
        )
        assert rows["https://a.example/1"] == 1
        assert rows["https://a.example/2"] == 2
        assert rows["https://a.example/3"] == 0


class TestTagsRoundTrip:
    """Tags were parsed since 1.0 and dropped at staging; v6 keeps them.

    The Netscape ``TAGS="a,b"`` attribute is the one piece of user-authored
    metadata the importers already understood, and losing it meant the user's
    own filing vocabulary -- the vocabulary no other facet can reconstruct --
    never reached the index.
    """

    TAGGED = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><A HREF="https://example.com/a" ADD_DATE="1690000000" TAGS="rust,systems">Rust guide</A>
    <DT><A HREF="https://example.com/b" ADD_DATE="1690000100" TAGS="ml, paper">attention paper</A>
    <DT><A HREF="https://example.com/no-tags" ADD_DATE="1690000200">plain</A>
</DL><p>
"""

    def test_tags_land_in_the_database(self, conn):
        import_bookmarks(conn, content=self.TAGGED)
        got = {
            r["url"]: r["tags"]
            for r in conn.execute("SELECT url, tags FROM bookmark").fetchall()  # type: ignore[arg-type]
        }
        import json

        assert json.loads(got["https://example.com/a"]) == ["rust", "systems"]
        # Whitespace around a comma is trimmed, exactly as the parser already did
        assert json.loads(got["https://example.com/b"]) == ["ml", "paper"]
        assert json.loads(got["https://example.com/no-tags"]) == []

    def test_tags_are_reachable_as_free_text(self, conn):
        """A tag is a word the user typed, so the word index must see it."""
        import_bookmarks(conn, content=self.TAGGED)
        rows = list(conn.execute("SELECT extra FROM fts_seg"))  # type: ignore[arg-type]
        assert any("systems" in r["extra"] for r in rows)

    def test_reimport_unions_tags_it_does_not_replace_them(self, conn):
        """Import is an edit, not a restore: an earlier tag survives a re-import."""
        import_bookmarks(conn, content=self.TAGGED)
        edited = self.TAGGED.replace(
            'TAGS="rust,systems"', 'TAGS="rust,async"'
        )
        import_bookmarks(conn, content=edited)
        import json

        tags = json.loads(
            conn.execute(
                "SELECT tags FROM bookmark WHERE url='https://example.com/a'"
            ).fetchone()[0]
        )
        assert sorted(tags) == ["async", "rust", "systems"]

    def test_a_tag_survives_the_duplicate_collapse_within_one_file(self, conn):
        dup = self.TAGGED.replace(
            '<DT><A HREF="https://example.com/a" ADD_DATE="1690000000" TAGS="rust,systems">Rust guide</A>',
            '<DT><A HREF="https://example.com/a?utm_source=x" ADD_DATE="1690000000"'
            ' TAGS="rust,systems">Rust guide</A>\n'
            '    <DT><A HREF="https://example.com/a" ADD_DATE="1680000000"'
            ' TAGS="extra">Rust guide again</A>',
            1,
        )
        import_bookmarks(conn, content=dup)
        import json

        # One row survives the collapse; the kept display URL is whichever
        # observation was seen first, so select by the tags themselves.
        tags = json.loads(
            conn.execute(
                "SELECT tags FROM bookmark WHERE url LIKE 'https://example.com/a%'"
            ).fetchone()[0]
        )
        assert "systems" in tags and "extra" in tags
