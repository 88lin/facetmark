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


class TestTheNumbersAreTrue:
    def test_the_footer_names_the_version_the_package_reports(self, built):
        """It said v1.6.1 for a 2.0.0 product. Now filled in at build time."""
        init = (ROOT / "src" / "facetmark" / "__init__.py").read_text(encoding="utf-8")
        version = re.search(r'__version__\s*=\s*"([^"]+)"', init).group(1)
        for name, html in built.items():
            assert f"facetmark v{version}" in html, f"{name} does not name v{version}"
            assert "v1.6.1" not in html, f"{name} still names a version that shipped"

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
