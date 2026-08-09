"""Tests for the landing site's two content files and the pages built from them.

``docs/landing`` is two Python dicts and a renderer.  Nothing else in the repo
imports them, so nothing else catches the three ways they rot:

*Drift between the languages.*  A section added to ``content_en.py`` and not to
``content_zh.py`` does not fail the build -- it fails at ``KeyError`` for the
index, and silently for a doc page, which is worse: the Chinese reader just
never learns the feature exists.  The parity assertions below compare structure
only, never prose, so a translator can rewrite any sentence freely.

*Dead cross-links.*  The pages link into each other by ``#anchor``, and an
anchor is only ever a string in a dict.  Renaming a section id leaves every
link to it pointing at nothing, and a browser scrolls to the top rather than
erroring, so it looks like it worked.

*Stale HTML.*  The built pages are committed, so an edit to a content file that
is never followed by ``python docs/landing/build.py`` ships the old page.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from tests.palette import strip_comments

REPO = Path(__file__).resolve().parents[1]
LANDING = REPO / "docs" / "landing"


@pytest.fixture(scope="module")
def landing():
    """The three landing modules, imported the way ``build.py`` imports them."""
    sys.path.insert(0, str(LANDING))
    try:
        import build as build_mod
        import content_en
        import content_zh
    finally:
        sys.path.remove(str(LANDING))
    return build_mod, content_en.EN, content_zh.ZH


DOC_PAGES = ("quickstart", "guide", "measured")


def skeleton(block: tuple) -> tuple:
    """A content block reduced to the parts a translation must not change.

    Prose is dropped; what survives is the kind of block, and for the kinds
    that carry structure, the structure. A table has to keep its column count
    or the two languages render differently. A shot keeps only whether it has a
    dark variant -- the two languages point at *different* image files on
    purpose, because the UI in the screenshot is itself translated.
    """
    kind = block[0]
    if kind == "table":
        return ("table", len(block[1]), tuple(len(r) for r in block[2]))
    if kind == "cb":
        return ("cb", block[1])
    if kind == "callout":
        return ("callout", block[1])
    if kind in ("ul", "ol", "steps"):
        return (kind, len(block[1]))
    if kind == "shot":
        return ("shot", len(block) > 4)
    return (kind,)


class TestBilingualParity:
    def test_the_two_files_have_the_same_top_level_keys(self, landing):
        _, en, zh = landing
        assert set(en) == set(zh)

    @pytest.mark.parametrize("name", ["nav", "meta", "term_labels", "copy"])
    def test_the_shared_dictionaries_have_the_same_keys(self, landing, name):
        _, en, zh = landing
        assert set(en[name]) == set(zh[name])

    def test_the_footer_points_at_the_same_places_in_both_languages(self, landing):
        _, en, zh = landing
        cols_en, cols_zh = en["foot"]["cols"], zh["foot"]["cols"]
        assert len(cols_en) == len(cols_zh)
        for (_, links_en), (_, links_zh) in zip(cols_en, cols_zh, strict=True):
            # the Chinese footer links to the Chinese pages; compare targets
            # after folding that away, so a missing entry still shows up
            assert [h for _, h in links_en] == [
                h.replace(".zh.html", ".html") for _, h in links_zh
            ]

    def test_the_index_has_the_same_keys_and_the_same_number_of_cards(self, landing):
        _, en, zh = landing
        assert set(en["index"]) == set(zh["index"])
        for key, value in en["index"].items():
            if isinstance(value, list):
                assert len(value) == len(zh["index"][key]), key

    @pytest.mark.parametrize("page", DOC_PAGES)
    def test_each_page_has_the_same_sections_in_the_same_order(self, landing, page):
        _, en, zh = landing
        assert [s[0] for s in en[page]["sections"]] == [
            s[0] for s in zh[page]["sections"]
        ]

    @pytest.mark.parametrize("page", DOC_PAGES)
    def test_each_section_is_built_from_the_same_blocks(self, landing, page):
        _, en, zh = landing
        for (sid, _, blocks_en), (_, _, blocks_zh) in zip(
            en[page]["sections"], zh[page]["sections"], strict=True
        ):
            assert [skeleton(b) for b in blocks_en] == [
                skeleton(b) for b in blocks_zh
            ], sid


class TestTheLinks:
    """Every internal link resolves to a page that exists and an id that exists."""

    @staticmethod
    def _ids(t: dict) -> dict[str, set[str]]:
        ids = {page: {s[0] for s in t[page]["sections"]} for page in DOC_PAGES}
        # the index is not built from sections; its band ids are in build.py
        ids["index"] = {
            "queries", "facets", "pipeline", "app", "extension",
            "measured", "start", "interfaces", "faq", "promises",
        }
        return ids

    @staticmethod
    def _hrefs(t: dict) -> set[str]:
        found: set[str] = set()

        def walk(node) -> None:
            if isinstance(node, str):
                found.update(re.findall(r'href="([^"]+)"', node))
            elif isinstance(node, dict):
                for v in node.values():
                    walk(v)
            elif isinstance(node, (list, tuple)):
                for v in node:
                    walk(v)

        walk(t)
        return found

    @pytest.mark.parametrize("code", ["en", "zh"])
    def test_no_internal_link_points_at_a_missing_page_or_anchor(self, landing, code):
        _, en, zh = landing
        t = en if code == "en" else zh
        ids = self._ids(t)
        broken = []
        for href in self._hrefs(t):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            page, _, frag = href.partition("#")
            if page:
                stem = page.replace(".zh.html", "").replace(".html", "")
                if stem not in ids:
                    broken.append(href)
                    continue
                if not (LANDING / page).exists():
                    broken.append(href)
                    continue
            else:
                stem = "guide" if frag in ids["guide"] else None
            if frag and stem and frag not in ids[stem]:
                broken.append(href)
        assert not broken, f"{code}: dangling links {sorted(broken)}"


class TestTheAssets:
    @pytest.mark.parametrize("code", ["en", "zh"])
    def test_every_referenced_image_is_committed(self, landing, code):
        _, en, zh = landing
        t = en if code == "en" else zh
        refs: set[str] = set()

        def walk(node) -> None:
            if isinstance(node, str):
                if node.startswith("assets/"):
                    refs.add(node)
            elif isinstance(node, dict):
                for v in node.values():
                    walk(v)
            elif isinstance(node, (list, tuple)):
                for v in node:
                    walk(v)

        walk(t)
        assert refs, "no assets referenced at all -- the walker is broken"
        missing = [r for r in sorted(refs) if not (LANDING / r).exists()]
        assert not missing, f"{code}: referenced but not committed: {missing}"


class TestTheGeneratedPages:
    """The committed HTML is what the current content files render to.

    Rendering in-memory rather than shelling out to ``build.py``: the point is
    to compare, not to rewrite the files under a test run.
    """

    @pytest.mark.parametrize("code", ["en", "zh"])
    @pytest.mark.parametrize("page", ("index",) + DOC_PAGES)
    def test_the_committed_page_matches_a_fresh_render(self, landing, code, page):
        build_mod, en, zh = landing
        t = en if code == "en" else zh
        # build.py renders through a module-global set per language
        build_mod.COPY = t["copy"]
        body = (
            build_mod.page_index(t)
            if page == "index"
            else build_mod.page_doc(t, page)
        )
        rendered = build_mod.shell(t, page, body)
        name = f"{page}{'.zh' if code == 'zh' else ''}.html"
        committed = (LANDING / name).read_text(encoding="utf-8")
        assert rendered == committed, (
            f"{name} is stale -- run `python docs/landing/build.py`"
        )


class TestThePaletteWiring:
    """The landing site now reads the same vendored palette as the app.

    The stylesheet stays self-contained -- its own `:root` holds the colourway
    -- but the page also pins palette A and links the vendored file, because
    that is where ``--highlight-rgb`` and the other ``*-rgb`` triplets the
    highlighter wash reads come from. These assertions pin the wiring, not the
    colours: the values are upstream's, the seam is ours.
    """

    PAGES = tuple(f"{p}{s}.html" for p in ("index",) + DOC_PAGES for s in ("", ".zh"))

    @pytest.mark.parametrize("name", PAGES)
    def test_the_page_pins_the_palette_whose_contrast_was_checked(self, name):
        html = (LANDING / name).read_text(encoding="utf-8")
        assert re.search(r"<html[^>]*data-palette=\"A\"", html), f"{name}: no palette pinned"

    @pytest.mark.parametrize("name", PAGES)
    def test_the_palette_is_linked_before_the_stylesheet_that_consumes_it(self, name):
        """`style.css` reads tokens the palette declares. Load it first and the
        page renders one paint with every custom property unresolved."""
        html = (LANDING / name).read_text(encoding="utf-8")
        sheets = re.findall(r'<link rel="stylesheet" href="([^"]+)"', html)
        assert "palettes.css" in sheets, f"{name}: the palette is not linked"
        assert sheets.index("palettes.css") < sheets.index("style.css"), name

    @pytest.mark.parametrize("name", PAGES)
    def test_no_page_asks_a_font_cdn_for_anything(self, name):
        """These pages used to load Fraunces, Noto Serif SC and Caveat from
        Google Fonts. The project owner's own derived site loads no faces at
        all -- its stacks are `-apple-system` first -- and this site now
        matches it. A CDN request here would also be the one thing on the page
        that phones a third party, which a local-first tool should not do."""
        html = (LANDING / name).read_text(encoding="utf-8")
        for host in ("fonts.googleapis.com", "fonts.gstatic.com", "@import url(http"):
            assert host not in html, f"{name} reaches out to {host}"
        for family in ("Fraunces", "Noto+Serif+SC", "Caveat"):
            assert family not in html, f"{name} still names {family}"

    def test_the_stylesheet_defines_the_display_stack(self):
        """The headings read `--display`; if the token vanished they would
        fall back to the body sans with no error anywhere."""
        css = (LANDING / "style.css").read_text(encoding="utf-8")
        assert "--display:" in css, "no --display token"
        assert "--font-serif" not in css, "the CDN serif token is back"

    def test_the_display_headings_use_the_display_stack(self):
        css = (LANDING / "style.css").read_text(encoding="utf-8")
        rule = re.search(r"\.hero h1[^{]*\{([^}]*)\}", css)
        assert rule and "var(--display)" in rule.group(1), "hero h1 is not the display stack"
        assert "800" in rule.group(1), "hero h1 is not at the reference site's 800 weight"

    def test_the_text_stack_is_the_one_the_owner_specified(self):
        """Verbatim from `--f-sans` on repair.88lin.eu.org.

        The stack this replaced led with "Liberation Sans", Arimo, Arial.
        Arial is on the design system's own banned list, and the first Han
        face appeared only after three Latin ones, so Chinese fell through to
        whatever the browser picked. Order matters and is asserted: Apple
        first, then PingFang SC ahead of the Windows face.
        """
        css = (LANDING / "style.css").read_text(encoding="utf-8")
        stack = re.search(r"--sans:\s*([^;]+);", css)
        assert stack, "no --sans token"
        families = [f.strip().strip("\"'") for f in stack.group(1).split(",")]
        assert families[:2] == ["-apple-system", "BlinkMacSystemFont"], families[:2]
        assert "PingFang SC" in families, "the text stack names no Apple Han face"
        assert families.index("PingFang SC") < families.index("Microsoft YaHei")

    @pytest.mark.parametrize(
        "family", ["Inter", "Roboto", "Arial", "Fraunces", "Caveat", "Liberation Sans"]
    )
    def test_no_banned_family_is_named_anywhere(self, family):
        """The first three are banned by the design system. The last three
        were what this site actually shipped, which is how the ban went
        unnoticed: nothing was checking."""
        css = strip_comments((LANDING / "style.css").read_text(encoding="utf-8"))
        assert not re.search(rf"\b{re.escape(family)}\b", css), f"style.css still names {family}"

    def test_the_stat_numerals_align(self):
        """Dashboard-style numbers are tabular so a column of them does not
        wobble. `.stat .v` and `.bigstat` are the two display numerals."""
        css = (LANDING / "style.css").read_text(encoding="utf-8")
        for sel in (r"\.stat \.v", r"\.bigstat"):
            body = re.search(sel + r"\s*\{([^}]*)\}", css)
            assert body and "tabular-nums" in body.group(1), f"{sel} is not tabular"
