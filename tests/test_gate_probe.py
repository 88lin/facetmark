"""Tests for the gate-precision probe generator.

The probe set exists to answer one question: when the gate fires on a query
that is *not* about save time, what does it cost? Every guard below protects
that question from being quietly turned into a different one.

Two failure modes are worth naming, because both would produce a clean-looking
number that means nothing:

* **A probe the gate cannot see.** If the time expression is one the product's
  resolver does not match, the gate never fires and the query measures the
  ranker's noise floor. Hence the invariants that every offered relative phrase
  and every pickable content year are recognised by the shipped ``classify()``.
* **A probe that is secretly episodic.** If the query says "the one I saved",
  the gate is *right* to fire and the measurement flips from precision back to
  recall -- which the W2/W3 run already measured. Hence ``_SAVE_WORDS`` and the
  test that keeps it a superset of the product's own marker list.

``scripts/`` is not a package, so both modules are loaded by path.
"""
from __future__ import annotations

import importlib.util
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from facetmark.search.understand import _VAGUE_EPISODIC, classify

UTC = timezone.utc  # datetime.UTC is 3.11+; CI matrix starts at 3.10

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "corpus" / "gen_gate_probe.py"
_NOW = 1785649110  # the indexed library's created_at, so windows land where they did


def _load():
    spec = importlib.util.spec_from_file_location("gen_gate_probe_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


gp = _load()


def test_import_does_not_run_main():
    assert callable(gp.main)


# ---------------------------------------------------------------------------
# the probe has to be visible to the thing it is probing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phrase", gp._REL_ZH + gp._REL_EN)
def test_offered_relative_phrases_fire_the_gate(phrase):
    """A relative word the resolver ignores would measure nothing at all."""
    u = classify(f"{phrase} 固态电池 solid state battery density", now_ts=_NOW)
    assert u.is_episodic
    assert "time:relative" in u.rule_hits


@pytest.mark.parametrize("year", [1990, 1999, 2000, 2015, 2025])
def test_pickable_content_years_fire_the_gate(year):
    """``_CONTENT_YEAR`` must stay inside the product's ``_ABS_YEAR`` band."""
    assert gp._CONTENT_YEAR.fullmatch(str(year))
    u = classify(f"{year} harbour dredging sediment", now_ts=_NOW)
    assert u.is_episodic
    assert "time:absolute_year" in u.rule_hits


@pytest.mark.parametrize("text", ["1989", "2026", "2030", "1976", "v2024x", "20240",
                                  "12015"])
def test_content_year_regex_rejects_out_of_band_and_embedded(text):
    """1990-2025 is the protocol's band. 2026 is the library's own "now": a page
    about 2026 saved in 2026 is not a probe, it is a coincidence."""
    assert gp._CONTENT_YEAR.search(text) is None


# ---------------------------------------------------------------------------
# a probe that is secretly episodic
# ---------------------------------------------------------------------------


def test_save_words_covers_the_products_vague_markers():
    """If the product learns a new vague marker, the probe set must learn it too.

    Otherwise a query using it would be scored as content while the gate fires
    on it correctly, and a correct firing would be counted as a misfire.
    """
    missing = [m for m in _VAGUE_EPISODIC if m.lower() not in gp._SAVE_WORDS]
    assert missing == [], f"probe generator is missing {missing}"


@pytest.mark.parametrize("text", [
    "我上次存的那篇固态电池综述",
    "那阵子看的电网事故复盘",
    "the reef paper I saved last spring",
    "BOOKMARKED post about hybrid schedules",
    "around the time of the grid failure",
])
def test_save_words_are_caught_case_insensitively(text):
    assert gp.save_words_in(text)


@pytest.mark.parametrize("text", [
    "2016年税法改写后个体工商户怎么申报",
    "recently reported gains in solid state cell density",
])
def test_clean_probes_carry_no_save_words(text):
    assert gp.save_words_in(text) == []


# ---------------------------------------------------------------------------
# year_in: a bare year, not a substring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("text", "year", "want"), [
    ("2016年税法改写", 2016, True),
    ("the 2016 rewrite", 2016, True),
    ("the 12016 rewrite", 2016, False),
    ("the 20161 rewrite", 2016, False),
    ("build v2016 of the tool", 2016, False),
    ("the 2016-2017 season", 2016, True),
])
def test_year_in_matches_whole_numbers_only(text, year, want):
    assert gp.year_in(text, year) is want


# ---------------------------------------------------------------------------
# content_year: what the page is about, not what its footer says
# ---------------------------------------------------------------------------


def test_content_year_accepts_a_single_mention():
    """Deliberate. Requiring two mentions cut the frame from 468 pages to 195,
    and the pages it cut were mostly about real years mentioned once."""
    body = "lava tubes were discovered in 2009 by the orbiter " + "x" * 400
    assert gp.content_year(body, save_year=2026, head_chars=2000) == 2009


def test_content_year_needs_one_mention_in_the_shown_slice():
    """The model is shown ``body[:body_chars]``; asking it to write about a year
    that only appears past that point is asking it to invent."""
    body = "dredging report. " + ("x" * 500) + " the 1998 survey and the 1998 follow-up"
    assert gp.content_year(body, save_year=2026, head_chars=100) is None
    assert gp.content_year(body, save_year=2026, head_chars=2000) == 1998


def test_content_year_excludes_the_save_year():
    """A query carrying the save year would make the wrong window right."""
    body = "the 2025 review of the 2025 budget, twice over"
    assert gp.content_year(body, save_year=2025, head_chars=2000) is None


def test_content_year_prefers_the_most_mentioned():
    body = "1998 and 1998 and 1998, plus 2011 and 2011, plus 2015"
    assert gp.content_year(body, save_year=2025, head_chars=2000) == 1998


def test_content_year_breaks_ties_toward_the_most_wrong_window():
    """Equal evidence, so take the year that makes the gate's window wrongest --
    that is the quantity the probe was built to price."""
    tie = "2011 and 2011 and 2020 and 2020"
    assert gp.content_year(tie, save_year=2024, head_chars=2000) == 2011
    assert gp.content_year(tie, save_year=2009, head_chars=2000) == 2020


# ---------------------------------------------------------------------------
# check_probe
# ---------------------------------------------------------------------------


def _probe(text, **kw):
    args = {
        "subtype": "p_year", "year": 2016, "save_year": 2026, "phrase": None,
        "title_toks": set(), "zh": False, "max_overlap": 0.6,
        "example_toks": set(),
        "page_toks": gp.tokens(
            "sole proprietors filing thresholds deduction schedule c 2016 "
            "rewrite pass through entities quarterly estimates coral "
            "transplant bleaching nursery survival density"),
    }
    args.update(kw)
    return gp.check_probe(text, **args)


def test_check_probe_accepts_a_clean_year_probe():
    assert _probe("what the 2016 rewrite did to sole proprietor filing thresholds") == ""


def test_check_probe_accepts_a_clean_relative_probe():
    assert _probe("recently measured coral transplant survival after bleaching",
                  subtype="p_relative", year=None, phrase="recently") == ""


def test_check_probe_rejects_a_missing_year():
    bad = _probe("what the rewrite did to sole proprietor filing thresholds")
    assert "2016" in bad


def test_check_probe_rejects_a_missing_relative_phrase():
    bad = _probe("measured coral transplant survival after bleaching",
                 subtype="p_relative", year=None, phrase="recently")
    assert "recently" in bad


def test_check_probe_rejects_the_save_year():
    bad = _probe("what the 2016 rewrite did to filing thresholds in 2026")
    assert "2026" in bad


def test_check_probe_rejects_save_vocabulary():
    bad = _probe("the 2016 rewrite page I saved about filing thresholds")
    assert "saved" in bad


def test_check_probe_still_applies_the_content_checks():
    """``check_content``'s title-overlap rule is not bypassed by the new ones."""
    title = gp.content_tokens("2016 rewrite filing thresholds")
    bad = _probe("2016 rewrite filing thresholds", title_toks=title)
    assert bad != ""


# ---------------------------------------------------------------------------
# the example must not poison the parrot check
# ---------------------------------------------------------------------------


def test_the_required_year_cannot_be_parroted():
    """The 1998 example plus a target whose content year is 1998 is the collision
    that would reject a query for writing the one word it was told to write.

    It does not, and the reason is structural rather than lucky: the parrot rule
    is ``(query & example) - page``, and ``content_year`` only returns years that
    are in the page. A digit filter over the example was written for this and
    then deleted as dead code; this test is what replaced it."""
    ex = gp._EXAMPLES[("p_year", False)][1]
    assert "1998" in gp.content_tokens(ex)          # 199x survives content_tokens
    body = ("the 1998 harbour dredging survey found sediment layers in the "
            "tidal basin ") * 4
    page_toks = gp.tokens("Revisiting the harbour dredging survey " + body)
    assert "1998" in page_toks
    assert gp.content_year(body, save_year=2026, head_chars=2500) == 1998
    text = "sediment layers the 1998 dredging survey found in the tidal basin"
    assert _probe(text, year=1998, example_toks=gp.content_tokens(ex),
                  page_toks=page_toks,
                  title_toks=gp.content_tokens("Revisiting the harbour dredging "
                                               "survey")) == ""


# ---------------------------------------------------------------------------
# prompt
# ---------------------------------------------------------------------------


def test_requirement_names_the_year_or_the_phrase():
    assert "2016" in gp.requirement_for("p_year", False, 2016, None)
    assert "2016" in gp.requirement_for("p_year", True, 2016, None)
    assert "去年" in gp.requirement_for("p_relative", True, None, "去年")


def test_prompt_carries_the_body_the_requirement_and_the_ban():
    t = {"title": "Revisiting the 1998 harbour dredging survey", "folder": "reading",
         "body_text": "sediment " * 400, "zh": False, "subtype": "p_year",
         "content_year": 1998, "phrase": None,
         "example_text": gp._EXAMPLES[("p_year", False)][1]}
    p = gp.prompt_for(t, 200, "")
    assert p.count("sediment") <= 30          # body truncated to 200 chars
    assert "1998" in p
    assert "bookmarked" in p
    assert "Answer in English" in p
    assert "rejected" not in p
    assert "rejected: too close" in gp.prompt_for(t, 200, "too close")


def test_prompt_switches_language_for_chinese_titles():
    t = {"title": "重读 1998 年那份港口疏浚调查", "folder": "阅读",
         "body_text": "泥沙" * 200, "zh": True, "subtype": "p_relative",
         "content_year": None, "phrase": "去年",
         "example_text": gp._EXAMPLES[("p_relative", True)][0]}
    p = gp.prompt_for(t, 200, "")
    assert "Answer in Chinese" in p
    assert "去年" in p


# ---------------------------------------------------------------------------
# target selection against a real schema
# ---------------------------------------------------------------------------


def _mini_db(path: Path, rows: list[tuple[str, str, int, str]]) -> str:
    """rows: (url, title, date_added, body)."""
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE bookmark (id INTEGER PRIMARY KEY, url TEXT, url_norm TEXT,
            url_hash TEXT, title TEXT, folder TEXT DEFAULT '', folder_depth INT
            DEFAULT 0, host TEXT DEFAULT '', domain TEXT DEFAULT '',
            date_added INTEGER, date_modified INTEGER, source TEXT,
            indexable INTEGER DEFAULT 1, privacy_skipped INTEGER DEFAULT 0,
            import_artifact INTEGER DEFAULT 0, open_count INTEGER DEFAULT 0,
            last_opened_at INTEGER, created_at INTEGER DEFAULT 0,
            updated_at INTEGER DEFAULT 0);
        CREATE TABLE content (bookmark_id INTEGER PRIMARY KEY, body_text TEXT,
            body_seg TEXT, body_hash TEXT, char_count INTEGER DEFAULT 0,
            lang TEXT, extractor TEXT, fetch_channel TEXT, http_status INTEGER,
            final_url TEXT, fetched_at INTEGER, error TEXT);
        CREATE TABLE session (id INTEGER PRIMARY KEY);
        CREATE TABLE bookmark_session (bookmark_id INTEGER, session_id INTEGER,
            PRIMARY KEY (bookmark_id, session_id));
    """)
    for i, (url, title, added, body) in enumerate(rows, start=1):
        c.execute("INSERT INTO bookmark (id, url, url_norm, url_hash, title, "
                  "host, date_added) VALUES (?,?,?,?,?,?,?)",
                  (i, url, url, f"h{i}", title, "e.com", added))
        c.execute("INSERT INTO content (bookmark_id, body_text, body_hash, "
                  "char_count) VALUES (?,?,?,?)", (i, body, f"b{i}", len(body)))
    c.commit()
    c.close()
    return str(path)


def test_pick_targets_keeps_only_pages_about_another_year(tmp_path):
    saved_2026 = int(datetime(2026, 3, 1, tzinfo=UTC).timestamp())
    about_1998 = "the 1998 dredging survey and the 1998 follow-up " + "x" * 400
    saved_2025 = int(datetime(2025, 3, 1, tzinfo=UTC).timestamp())
    db = _mini_db(tmp_path / "m.db", [
        ("https://e.com/a", "A", saved_2026, about_1998),
        # about its own save year -> the wrong window would be right
        ("https://e.com/b", "B", saved_2025, "the 2025 budget and the 2025 review "
         + "x" * 400),
        # 2026 is out of band: it is the library's own present
        ("https://e.com/c", "C", saved_2025, "the 2026 outlook and 2026 forecast "
         + "x" * 400),
        # year sits past the slice the model is shown
        ("https://e.com/e", "E", saved_2026, "x" * 400 + " the 2019 report"),
        # no body worth reading
        ("https://e.com/d", "D", saved_2026, "short"),
    ])
    out, frame = gp.pick_targets(db, n=10, min_chars=300, seed=1, head_chars=300)
    assert [o["url"] for o in out] == ["https://e.com/a"]
    assert out[0]["content_year"] == 1998
    assert out[0]["save_year"] == 2026
    assert frame == {"pages_with_body": 4, "pages_about_a_year": 1}


def _year_rows(n):
    return [(f"https://e.com/{i}", f"T{i}",
             int(datetime(2020 + i % 5, 6, 1, tzinfo=UTC).timestamp()),
             f"the 199{i % 10} survey and the 199{i % 10} follow-up " + "x" * 400)
            for i in range(n)]


def test_pick_targets_never_returns_a_page_twice(tmp_path):
    """One query per page is what makes the paired bootstrap downstream valid."""
    db = _mini_db(tmp_path / "m.db", _year_rows(30))
    out, _ = gp.pick_targets(db, n=12, min_chars=300, seed=7, head_chars=2500)
    urls = [o["url"] for o in out]
    assert len(urls) == len(set(urls))
    assert len(urls) <= 12
    assert all(o["neighbours"] == [] for o in out)


def test_pick_targets_takes_the_whole_frame_when_asked_for_more(tmp_path):
    """The run asks for 400 from a frame of 468, but the stratifier rounds per
    year and can return fewer than ``n``. When ``n`` exceeds the frame it must
    still return everything, or the shortfall would be silent."""
    db = _mini_db(tmp_path / "m.db", _year_rows(30))
    out, frame = gp.pick_targets(db, n=400, min_chars=300, seed=7, head_chars=2500)
    assert len(out) == frame["pages_about_a_year"] == 30
