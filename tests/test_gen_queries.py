"""Tests for the corpus query generator's text-less page path.

``scripts/`` is not a package, so the module is loaded by path. That only works
because the file guards its ``main()`` -- it used to call it at import time,
which is why none of this was testable before.

Only the pure parts are exercised here: word extraction, pool selection, and
prompt construction. The generation loop needs a chat model and is covered by
the drop-rate counters it prints, not by unit tests.
"""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "corpus" / "gen_queries.py"


def _load():
    spec = importlib.util.spec_from_file_location("gen_queries_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


gq = _load()


def test_import_does_not_run_main():
    """A bare ``main()`` at module scope makes the file impossible to test."""
    assert callable(gq.main)


# ---------------------------------------------------------------------------
# words in the address
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("url", "want"), [
    # camel case split, extension and date path segments dropped
    ("https://e.com/blog/2023/08/How-ToUse-Rust-Async/index.html",
     ["how", "to", "use", "rust", "async"]),
    # percent-escaped CJK survives; "wiki" is structural
    ("https://zh.wikipedia.org/wiki/%E5%85%89%E5%90%88%E4%BD%9C%E7%94%A8",
     ["光合作用"]),
    # a hash and an opaque id leave nothing behind
    ("https://app.e.com/a3f9c2b81d4e/view?id=99", []),
    ("https://news.ycombinator.com/", []),
])
def test_url_slug_words(url, want):
    assert gq.url_slug_words(url) == want


def test_url_slug_words_deduplicates_and_limits():
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"]
    url = "https://e.com/" + "/".join(["rust"] * 5 + words)
    got = gq.url_slug_words(url, limit=6)
    assert got[0] == "rust"
    assert len(got) == 6
    assert len(set(got)) == 6


def test_example_without_content_leaves_two_keys():
    for block in gq.EXAMPLES_EN + gq.EXAMPLES_ZH:
        stripped = gq.example_without_content(block)
        assert '"content"' not in stripped
        assert '"vague"' in stripped and '"hint"' in stripped


# ---------------------------------------------------------------------------
# target pools
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE bookmark (id INTEGER PRIMARY KEY, url TEXT, title TEXT,
                       folder TEXT, date_added INTEGER, host TEXT,
                       indexable INTEGER DEFAULT 1);
CREATE TABLE content (bookmark_id INTEGER, body_text TEXT, body_hash TEXT,
                      char_count INTEGER, lang TEXT);
CREATE TABLE bookmark_session (bookmark_id INTEGER, session_id INTEGER);
"""

#: id, url, title, char_count (None means "no content row at all")
_ROWS = [
    (1, "https://e.com/rust-async-guide", "Rust async guide", 5000),
    (2, "https://e.com/sous-vide-brisket", "Sous vide brisket", 900),
    (3, "https://e.com/short-note", "Short note", 400),
    (4, "https://e.com/tiny", "Tiny", 50),
    (5, "https://e.com/login", "", 0),               # no title, no slug words
    (6, "https://e.com/photosynthesis-explained", "Photosynthesis", 0),
    (7, "https://e.com/kubernetes-operators", "Operators", None),
    (8, "https://e.com/9f8e7d6c5b4a3210", "", 0),    # opaque id, unusable
]


@pytest.fixture
def db(tmp_path) -> str:
    path = tmp_path / "lib.db"
    c = sqlite3.connect(path)
    c.executescript(_SCHEMA)
    for i, (bid, url, title, chars) in enumerate(_ROWS):
        c.execute("INSERT INTO bookmark (id, url, title, folder, date_added, host) "
                  "VALUES (?,?,?,?,?,?)",
                  (bid, url, title, "tech", 1700000000 + i * 86400, "e.com"))
        if chars is None:
            continue
        c.execute("INSERT INTO content VALUES (?,?,?,?,?)",
                  (bid, "x" * chars, "h" if chars else None, chars, "en"))
    c.commit()
    c.close()
    return str(path)


def test_pick_targets_respects_min_chars(db):
    assert {t["id"] for t in gq.pick_targets(db, 10, 800, seed=1)} == {1, 2}
    assert {t["id"] for t in gq.pick_targets(db, 10, 300, seed=1)} == {1, 2, 3}


def test_pick_bodyless_targets_finds_pages_with_no_text(db):
    out, unusable = gq.pick_bodyless_targets(db, 10, seed=1)
    # 6 has a title, 7 has no content row at all but a readable slug.
    assert {t["id"] for t in out} == {6, 7}
    # 5 and 8 carry nothing a query could honestly be written from.
    assert unusable == 2
    assert all(t["kind"] == "bodyless" for t in out)
    assert gq.url_slug_words(_ROWS[6][1]) == ["kubernetes", "operators"]


def test_body_and_bodyless_pools_do_not_overlap(db):
    body = {t["id"] for t in gq.pick_targets(db, 10, 300, seed=1)}
    bodyless = {t["id"] for t in gq.pick_bodyless_targets(db, 10, seed=1)[0]}
    assert not body & bodyless


def test_bodyless_share_excludes_pages_neither_pool_can_reach(db):
    # min_chars=300 -> body pool {1,2,3}, text-less pool {5,6,7,8}; page 4
    # (50 chars) is in neither and must not be in the denominator.
    assert gq.bodyless_share(db, 300) == pytest.approx(4 / 7)
    assert gq.bodyless_share(db, 800) == pytest.approx(4 / 6)


# ---------------------------------------------------------------------------
# the prompt
# ---------------------------------------------------------------------------


def _target(**over):
    t = {"title": "Photosynthesis", "url": "https://e.com/photosynthesis-explained",
         "folder": "science", "neighbours": ["Another page"], "body_text": "",
         "slug": ["photosynthesis", "explained"], "kind": "bodyless",
         "zh": False, "example": 0}
    t.update(over)
    return t


def test_bodyless_prompt_asks_for_two_keys_and_shows_no_body():
    p = gq.prompt_for(_target(), body_chars=2500, subtype="year", feedback={})
    assert "PAGE TEXT" not in p
    assert 'JSON only: {"vague": "...", "hint": "..."}' in p
    assert '"content"' not in p.split("Do NOT write")[0]
    assert "photosynthesis, explained" in p


def test_body_prompt_is_unchanged_and_still_asks_for_content():
    t = _target(kind="body", body_text="Chlorophyll absorbs light " * 50)
    p = gq.prompt_for(t, body_chars=2500, subtype="year", feedback={})
    assert "PAGE TEXT" in p
    assert 'JSON only: {"content": "...", "vague": "...", "hint": "..."}' in p


def test_untitled_bodyless_page_does_not_render_an_empty_title_line():
    p = gq.prompt_for(_target(title=""), body_chars=2500, subtype="year",
                      feedback={})
    assert "TITLE: (untitled)" in p
