"""What the site says, checked against what is true.

`test_landing.py` is thorough about how these pages look: nine type sizes, five
leading rungs, contrast on every surface, structural parity between the two
languages, the committed HTML matching a fresh render. Twenty-five checks, and
not one of them asks whether a sentence on the page is *correct*.

So the footer advertised `facetmark v1.6.1` while the product was `2.0.0`, the
front page advertised `1,619 tests` against a suite of 1757, and two of the
seven documentation pages could not be reached at all from a phone. Each is a
claim the repository already knows the answer to.

The rule these tests enforce: a fact the repository knows is either filled in
from that source at build time, or asserted here. Never typed twice.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "docs" / "landing"

#: Every page the site builds, both languages. The nav offers all seven; the
#: question these tests ask is whether a reader can actually get to them.
DOC_PAGES = ("quickstart", "guide", "webui", "config", "integrations", "measured")
PAGE_FILES = tuple(
    f"{p}{s}.html" for p in ("index",) + DOC_PAGES for s in ("", ".zh")
)

#: A link the stylesheet hides below 700px: `nav.top a.hide-sm {display: none}`.
#: A page reachable *only* through one of these is not reachable on a phone.
HIDDEN_ON_PHONE = "hide-sm"

#: `<a ...>` with its attributes, so a link's classes can be read alongside its
#: target. Good enough for markup this file generates itself.
ANCHOR = re.compile(r"<a\s([^>]*?)>", re.I)
HREF = re.compile(r'href="([^"]+)"', re.I)
CLASS = re.compile(r'class="([^"]*)"', re.I)


def pages() -> dict[str, str]:
    out = {}
    for name in PAGE_FILES:
        path = LANDING / name
        assert path.exists(), f"{name} is not built"
        out[name] = path.read_text(encoding="utf-8")
    return out


@pytest.fixture(scope="module")
def built() -> dict[str, str]:
    return pages()


def links(html: str, *, phone_only: bool = False) -> set[str]:
    """Every local page this HTML links to.

    With ``phone_only``, drop the links the stylesheet hides below 700px, which
    is what a reader on a phone is actually offered.
    """
    found: set[str] = set()
    for attrs in ANCHOR.findall(html):
        href = HREF.search(attrs)
        if not href:
            continue
        target = href.group(1).split("#")[0]
        if not target.endswith(".html"):
            continue
        cls = CLASS.search(attrs)
        if phone_only and cls and HIDDEN_ON_PHONE in cls.group(1).split():
            continue
        found.add(target.split("/")[-1])
    return found


class TestEveryPageCanBeReached:
    """Two pages were orphaned on a phone.

    `webui`, `config` and `integrations` were added to the nav after the footer
    was written, and the nav drops three items below 700px to stay on one line.
    `measured` survived because the hero links it and the footer lists it;
    `config` and `integrations` were in neither, so on a 390px screen they could
    not be reached from anywhere on the site.
    """

    @pytest.mark.parametrize("page", PAGE_FILES)
    def test_on_a_phone_every_other_page_is_still_one_tap_away(self, built, page):
        lang = ".zh" if page.endswith(".zh.html") else ""
        want = {f"{p}{lang}.html" for p in ("index",) + DOC_PAGES} - {page}
        have = links(built[page], phone_only=True)
        missing = sorted(want - have)
        assert not missing, (
            f"{page} offers no route to {missing} on a screen under 700px -- "
            "every link to them is hidden there"
        )

    @pytest.mark.parametrize("page", PAGE_FILES)
    def test_the_full_nav_is_unchanged(self, built, page):
        """The phone fix must not have come out of the desktop nav."""
        lang = ".zh" if page.endswith(".zh.html") else ""
        want = {f"{p}{lang}.html" for p in ("index",) + DOC_PAGES} - {page}
        assert not sorted(want - links(built[page]))


class TestTheReferenceIsNotACulDeSac:
    """The guide is the reference layer; four pages are the task layer.

    They cover the same ground at different altitudes, which is a sound way to
    organise a manual -- but the links only went one way. The task pages link
    into the guide 48 times between them and the guide linked back exactly
    once, so 47 of those were a door into a room with no way out: a reader who
    lands on `guide.html#webui` had nothing to tell them a walkthrough of the
    same screens exists.
    """

    @pytest.fixture(scope="class")
    def companions(self) -> dict[str, str]:
        sys.path.insert(0, str(LANDING))
        try:
            import build as build_mod
        finally:
            sys.path.remove(str(LANDING))
        return dict(build_mod.GUIDE_COMPANIONS)

    def test_every_pairing_names_a_section_and_a_page_that_exist(self, companions):
        sys.path.insert(0, str(LANDING))
        try:
            import content_en
            import content_zh
        finally:
            sys.path.remove(str(LANDING))
        for lang in (content_en.EN, content_zh.ZH):
            anchors = {s[0] for s in lang["guide"]["sections"]}
            for anchor, page in companions.items():
                assert anchor in anchors, f"no guide section `{anchor}`"
                assert page in lang, f"no page `{page}`"
                assert lang[page].get("h1"), f"`{page}` has no title to link with"

    #: The task layer: the pages that say what to do, as opposed to the
    #: reference (`guide`), the pitch (`index`) and the evidence (`measured`).
    #: Named here rather than read off `GUIDE_COMPANIONS`, so this asserts the
    #: map is complete instead of agreeing with itself.
    TASK_PAGES = ("quickstart", "webui", "config", "integrations")

    @pytest.mark.parametrize("guide", ["guide.html", "guide.zh.html"])
    def test_the_guide_links_back_to_every_page_that_links_into_it(self, built, guide):
        """The invariant the defect broke: if a task page sends readers into
        the reference, the reference sends them back.

        Scoped to the task layer. `index` is the pitch and is one nav item away
        from everywhere, `measured` is the evidence and is nobody's how-to, and
        the guide's own anchors link into itself -- none of those wants eleven
        signposts pointing at it.
        """
        lang = ".zh" if guide.endswith(".zh.html") else ""
        inbound = {
            f"{p}{lang}.html" for p in self.TASK_PAGES
            if re.search(rf'href="guide{re.escape(lang)}\.html#', built[f"{p}{lang}.html"])
        }
        assert len(inbound) == len(self.TASK_PAGES), (
            f"only {sorted(inbound)} link into {guide} -- the pairing this "
            "asserts is with pages that do"
        )
        out = set(re.findall(r'class="seealso">[^<]*<a href="([^"]+)"', built[guide]))
        missing = sorted(inbound - out)
        assert not missing, f"{guide} is a dead end for {missing}"

    @pytest.mark.parametrize("guide", ["guide.html", "guide.zh.html"])
    def test_a_back_link_stays_in_the_reader_s_language(self, built, guide):
        lang = ".zh" if guide.endswith(".zh.html") else ""
        for target in re.findall(r'class="seealso">[^<]*<a href="([^"]+)"', built[guide]):
            assert target.endswith(f"{lang}.html"), f"{guide} points at {target}"

    def test_the_two_languages_offer_the_same_way_out(self, built, companions):
        counts = {
            g: len(re.findall(r'class="seealso"', built[g]))
            for g in ("guide.html", "guide.zh.html")
        }
        assert counts["guide.html"] == counts["guide.zh.html"] == len(companions), counts


class TestTheNumbersAreTrue:
    def test_the_footer_names_the_version_the_package_reports(self, built):
        """It said v1.6.1 for a 2.0.0 product. Now filled in at build time."""
        for name, html in built.items():
            assert f"facetmark v{self._version()}" in html, f"{name} does not name the version"

    def test_no_page_names_a_version_that_is_not_the_one_shipping(self, built):
        """The footer was one of six. The other four were inside the terminal
        samples -- `facetmark 1.6.1  http://127.0.0.1:8787`, which is what a
        reader compares against what their own machine just printed. The first
        version of this test looked for `v1.6.1` and those four have no `v`,
        so they went straight through it. Match the shape, not the string.
        """
        version = self._version()
        stale = []
        for name, html in built.items():
            for found in re.findall(r"facetmark v?(\d+\.\d+\.\d+)", html):
                if found != version:
                    stale.append(f"{name} says {found}")
        assert not stale, f"the package is {version}: {stale}"

    def test_no_placeholder_survives_the_build(self, built):
        """A token that never got substituted is worse than a stale number:
        it is visibly broken and says nothing at all."""
        for name, html in built.items():
            assert "@@" not in html, f"{name} has an unfilled placeholder"

    @staticmethod
    def _version() -> str:
        init = (ROOT / "src" / "facetmark" / "__init__.py").read_text(encoding="utf-8")
        return re.search(r'__version__\s*=\s*"([^"]+)"', init).group(1)

    def test_the_advertised_test_count_is_a_floor_the_suite_clears(self):
        """A precise count drifts on every commit, so the site rounds down and
        this asserts the rounding is still honest.

        The upper bound is not pedantry: a claim of 1,700 against a suite of
        5,000 is as wrong as one against 1,000, just in the direction that
        flatters. When it trips, raise the claim to the next round number.
        """
        claimed = self._claimed_tests()
        actual = self._collected()
        assert actual >= claimed, (
            f"the site advertises {claimed:,}+ tests and the suite collects "
            f"{actual:,}"
        )
        assert actual < claimed * 2, (
            f"the site advertises {claimed:,}+ tests and the suite collects "
            f"{actual:,} -- the claim is understated enough to be worth raising"
        )

    @staticmethod
    def _claimed_tests() -> int:
        text = (LANDING / "content_en.py").read_text(encoding="utf-8")
        m = re.search(r'\("Tests", "([\d,]+)\+?"\)', text)
        assert m, "no test-count claim found on the front page"
        return int(m.group(1).replace(",", ""))

    @staticmethod
    def _collected() -> int:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--collect-only", "--no-header", "-p",
             "no:cacheprovider"],
            cwd=ROOT, capture_output=True, text=True, timeout=600,
        )
        m = re.search(r"(\d+) tests? collected", r.stdout)
        assert m, f"could not read a count from pytest:\n{r.stdout[-2000:]}"
        return int(m.group(1))

    def test_the_python_floor_matches_what_the_package_requires(self, built):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        floor = re.search(r'requires-python\s*=\s*">=([\d.]+)"', pyproject).group(1)
        for name, html in built.items():
            assert f"{floor}+" in html, f"{name} does not state Python {floor}+"
