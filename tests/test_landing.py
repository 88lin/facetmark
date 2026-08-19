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

from tests.palette import (
    Palette,
    declarations,
    luminance,
    ratio,
    rules,
    strip_comments,
)

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
        assert re.search(r"<html[^>]*data-palette=\"G\"", html), f"{name}: no palette pinned"

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


# ---------------------------------------------------------------------------
# typography and spacing
# ---------------------------------------------------------------------------
#
# The project owner's complaint about this site was not "it is broken", it was
# "字体字号需要重新设计 ... 挤压在一起、不对齐". Nothing in the suite could see
# that. The stylesheet had shipped 33 distinct font-sizes -- including
# 0.74/0.75/0.76/0.77/0.78/0.79/0.80/0.81/0.83rem, adjacent steps 0.16px apart
# -- 16 distinct letter-spacings and 58 distinct paddings, margins and gaps,
# and every one of them was green. Noise is not a bug in any single rule; it
# is a property of the whole file, so it needs a whole-file assertion.


def _stylesheet() -> str:
    return (LANDING / "style.css").read_text(encoding="utf-8")


def _declared(css: str, prefix: str) -> dict[str, str]:
    """Every `:root` custom property whose name starts with ``prefix``."""
    root = declarations(css, r":root")
    return {k: v for k, v in root.items() if k.startswith(prefix)}


def _used(css: str, prop: str) -> list[tuple[str, str]]:
    """(selector, value) for every declaration of ``prop``, longhands included.

    Matching is on the whole property name -- `font-size` must not also
    collect `font-size-adjust`, and `gap` must not collect `column-gap` twice.
    """
    out = []
    for selector, body in rules(css):
        for name, value in re.findall(r"([a-z-][\w-]*)\s*:\s*([^;{}]+)", body):
            if name == prop:
                out.append((selector, " ".join(value.split())))
    return out


def _used_family(css: str, *stems: str) -> list[tuple[str, str, str]]:
    """(selector, property, value) for a property and all of its longhands."""
    out = []
    for selector, body in rules(css):
        for name, value in re.findall(r"([a-z-][\w-]*)\s*:\s*([^;{}]+)", body):
            if any(name == s or name.startswith(f"{s}-") for s in stems):
                out.append((selector, name, " ".join(value.split())))
    return out


class TestTheTypeScale:
    """One ladder for size, one for leading, one for tracking.

    Each test asserts the same two things: the ladder exists with the number
    of rungs it is supposed to have, and nothing in the file steps off it.
    The second half is the one that matters -- a scale nobody is held to is
    just four more tokens in a file that already had too many values.
    """

    def test_the_size_ladder_has_nine_rungs(self):
        """Nine, not the eight the plan promised.

        `--fs-0` is 11px and exists for one reason: the pipeline diagram is a
        fixed-geometry SVG whose labels sit between drawn arrows, and 12px
        text overruns them. It is excluded from prose by convention, not by
        the test, which cannot see what an element contains.
        """
        css = _stylesheet()
        steps = _declared(css, "--fs-")
        assert sorted(steps) == [f"--fs-{n}" for n in range(9)], sorted(steps)

    def test_no_rule_names_a_size_the_ladder_does_not(self):
        """Absolute sizes come from the ladder; relative ones may not.

        `em`, `%` and `inherit` are allowed because they cannot introduce a
        step -- they scale whatever their parent is set to, so inline code
        stays 0.88 of its paragraph whichever rung the paragraph is on. A
        `rem` or a `px` here is a new absolute size, which is how 33 of them
        accumulated, and the roster is capped so the relative escape hatch
        cannot become the new sprawl.
        """
        css = _stylesheet()
        loose = []
        for selector, value in _used(css, "font-size"):
            if re.fullmatch(r"var\(--fs-[0-8]\)", value):
                continue
            if value == "inherit" or re.fullmatch(r"[\d.]+(?:em|%)", value):
                loose.append((selector, value))
                continue
            raise AssertionError(f"{selector} sets font-size: {value}, off the ladder")
        assert len(loose) <= 8, f"too many relative sizes to still be exceptions: {loose}"

    def test_the_leading_ladder_has_five_rungs_and_one_exemption(self):
        """Five, not the four the plan promised: `--lh-code` was split out
        when the code panels stopped sharing the prose measure.

        `line-height: 1` is exempt and is not a sixth rung. It is what a box
        that holds exactly one line -- a 34px control, a numbered circle --
        needs in order to centre its own text; giving it 1.15 pushes the
        glyph off centre, which is a share of the "偏上" the owner reported.
        """
        css = _stylesheet()
        rungs = _declared(css, "--lh-")
        assert sorted(rungs) == ["--lh-body", "--lh-cjk", "--lh-code",
                                 "--lh-snug", "--lh-tight"], sorted(rungs)
        for selector, value in _used(css, "line-height"):
            assert re.fullmatch(r"var\(--lh-[a-z]+\)|1", value), (
                f"{selector} sets line-height: {value}, off the ladder"
            )

    def test_the_tracking_ladder_has_four_rungs_and_no_strays(self):
        """Four, not the three the plan promised.

        One caps step could not do the job: 0.08em is right on a 12px badge,
        but the same 12px eyebrow standing next to a 52px headline needs the
        extra air or it reads as a typo instead of a label. The file had
        sixteen tracking values before this; it now has four, and the
        negative one is Latin-only -- see the Chinese test below.
        """
        css = _stylesheet()
        rungs = _declared(css, "--ls-")
        assert sorted(rungs) == ["--ls-caps", "--ls-caps-wide",
                                 "--ls-display", "--ls-none"], sorted(rungs)
        for selector, value in _used(css, "letter-spacing"):
            assert re.fullmatch(r"var\(--ls-[a-z-]+\)", value), (
                f"{selector} sets letter-spacing: {value}, off the ladder"
            )

    def test_chinese_headings_are_not_letter_spaced(self):
        """`--ls-display` is -0.022em, and negative tracking is for Latin.

        A Han glyph fills its em box edge to edge; there is no sidebearing to
        take the 0.022em out of, so the columns start touching. This shipped
        for the whole life of the site: `h1..h4 { letter-spacing: -0.018em }`
        with no language condition, on pages served to Chinese readers.

        The reset is asserted by *effect*, not by its selector text: whatever
        the zh rule is written as, it has to name the display elements and it
        has to out-specify the plain element rules. Pinning the selector
        instead would freeze one implementation of a fix that has several.
        """
        css = strip_comments(_stylesheet())
        resets = [
            (selector, body)
            for selector, body in rules(css)
            if ":lang(zh)" in selector or 'lang="zh"' in selector
        ]
        assert resets, "nothing in the stylesheet is scoped to Chinese"
        zeroed = [
            selector
            for selector, body in resets
            if re.search(r"letter-spacing:\s*var\(--ls-none\)", body)
        ]
        assert zeroed, f"no zh rule zeroes tracking; zh rules are {[s for s, _ in resets]}"
        covered = " ".join(zeroed)
        for element in ("h1", "h2", "h3", "h4"):
            assert re.search(rf"\b{element}\b", covered), (
                f"the zh tracking reset does not reach {element}: {zeroed}"
            )

    def test_the_chinese_page_gets_its_own_measure(self):
        """1.65 reads as comfortable in Latin and as cramped in Han, because
        the glyphs are square and leave no internal white. Both languages
        shared 1.68 before this."""
        css = _stylesheet()
        rungs = _declared(css, "--lh-")
        assert float(rungs["--lh-cjk"]) > float(rungs["--lh-body"]), rungs
        body_rules = [
            body
            for selector, body in rules(strip_comments(css))
            if ":lang(zh)" in selector and re.search(r"\bbody\b", selector)
        ]
        assert any("var(--lh-cjk)" in b for b in body_rules), (
            "the Chinese pages still read at the Latin measure"
        )


class TestTheSpacingGrid:
    """Eight steps on a 4px grid, and nothing between them.

    "挤压在一起，不对齐" is what 58 distinct paddings, margins and gaps look
    like from the outside. Two cards 22px and 24px apart do not read as
    slightly different, they read as broken, and no amount of care in any one
    rule fixes it -- only a grid does.
    """

    #: Below this, a value is a hairline: the 1px that keeps inline code from
    #: touching its own background edge, the 2-3px optical nudges that centre
    #: a glyph in a pill. Snapping those to 4px is visible and wrong, and they
    #: cannot cause the misalignment this class is about, because nothing is
    #: aligned to within 3px by eye anyway.
    HAIRLINE = 3

    def test_every_gap_and_pad_comes_from_the_grid(self):
        css = _stylesheet()
        grid = _declared(css, "--sp-")
        assert sorted(grid) == [f"--sp-{n}" for n in range(1, 9)], sorted(grid)
        allowed = set(grid.values())
        assert allowed == {"4px", "8px", "12px", "16px", "24px", "32px", "48px", "72px"}, grid

        offenders = []
        for selector, prop, value in _used_family(css, "padding", "margin", "gap",
                                                  "row-gap", "column-gap"):
            for raw in re.findall(r"-?[\d.]+px", value):
                if abs(float(raw[:-2])) > self.HAIRLINE:
                    offenders.append(f"{selector} {{ {prop}: {value} }}")
                    break
        assert not offenders, "off-grid spacing: " + "; ".join(offenders)

    def test_the_grid_is_actually_used(self):
        """The previous assertion is also satisfied by a file with no spacing
        in it at all. This one fails if the tokens are declared and ignored."""
        css = _stylesheet()
        uses = [
            v for _, _, v in _used_family(css, "padding", "margin", "gap",
                                          "row-gap", "column-gap")
            if "var(--sp-" in v
        ]
        assert len(uses) > 120, f"only {len(uses)} spacing declarations read the grid"

    #: Properties an inline style may not name a raw length for. `max-width`,
    #: `justify-content` and the bar widths are layout, not rhythm, so they are
    #: not in here.
    RHYTHM = ("margin", "padding", "gap", "row-gap", "column-gap")

    @pytest.mark.parametrize("code", ["en", "zh"])
    @pytest.mark.parametrize("page", ("index",) + DOC_PAGES)
    def test_the_markup_does_not_hand_tune_a_gap_the_grid_owns(self, code, page):
        """The one place the stylesheet's ladder cannot reach.

        The assertion above reads the stylesheet, so five `style="margin-top:
        18px"` in the renderer sat off-grid through the whole redesign and no
        test was even looking at them. An inline gap is allowed -- it is often
        the honest place for a one-off -- but it takes its value off the same
        eight steps as everything else.
        """
        name = f"{page}{'.zh' if code == 'zh' else ''}.html"
        html = (LANDING / name).read_text(encoding="utf-8")
        offenders = []
        for style in re.findall(r'style="([^"]*)"', html):
            for decl in style.split(";"):
                prop, _, value = decl.partition(":")
                prop = prop.strip()
                if not any(prop == x or prop.startswith(x + "-") for x in self.RHYTHM):
                    continue
                for raw in re.findall(r"-?[\d.]+px", value):
                    if abs(float(raw[:-2])) > self.HAIRLINE:
                        offenders.append(f"{prop}: {value.strip()}")
        assert not offenders, f"{name} hand-tunes: " + "; ".join(sorted(set(offenders)))


# ---------------------------------------------------------------------------
# surfaces
# ---------------------------------------------------------------------------


class TestTheSurfaces:
    """No black slabs -- measured, not pattern-matched.

    `brand-dna.md:144` bans `#000` outright and `:167` allows a dark panel
    only on a full-bleed HTML page. The app-side guard for this,
    `test_no_dark_panel_in_a_functional_area`, looks for the `--dark-panel`
    token in `app.css`. It has never once fired, and could not: this
    stylesheet is a different file, and what it shipped was
    `--code-bg: #17160f`, luminance 0.0079, hand-written. Every command block
    on every documentation page was that colour, which is the "黑不溜秋的黑"
    the owner asked to have removed. A rule that names a token cannot see a
    literal; this one resolves the colour and reads its luminance instead.
    """

    #: The scopes that re-point surface tokens, and whether the page inside
    #: each one is light or dark. There were four: `.band.invert` flipped a
    #: section of a light page to dark and the dark theme flipped it back. That
    #: component is gone -- the owner ruled out dark slabs in daylight, and the
    #: alternating band it was used for now paints `--cream-deep` -- so two
    #: scopes are all a page can be in.
    SCOPES = (
        (r":root", "light"),
        (r':root\[data-theme="dark"\]', "dark"),
    )

    #: Tokens that end up behind something. Ink tokens are excluded on
    #: purpose: `--ink` is #241e2e and is *supposed* to be that dark.
    SURFACES = (
        "--cream", "--cream-dark", "--cream-deep", "--surface-2", "--card-bg",
        "--win-bar", "--win-body", "--info-soft",
        "--warning-soft", "--success-soft", "--danger-soft",
        "--highlight-soft",
        "--indigo-soft", "--indigo-ink-soft", "--iris-soft",
        "--orchid-soft", "--plum-soft", "--rose-soft",
    )

    #: A light page's surfaces have to stay light. 0.05 is an order of
    #: magnitude above `--ink`, and roughly where a colour stops reading as
    #: "a tint of the page" and starts reading as "a panel laid over it".
    DAYLIGHT_FLOOR = 0.05

    #: And a dark page still has to be a page, not an unlit screen. The night
    #: mode shipped `--cream: #131310`, luminance 0.0064; at that level the
    #: four elevation steps above it cannot be told apart, which is why the
    #: owner's "黑不溜秋" complaint covered dark mode too. Today's #241f2e is
    #: 0.0155 -- the violet night page, one step lighter again than the neutral
    #: #1c1b18 it replaced.
    MIDNIGHT_FLOOR = 0.0095

    #: The one panel allowed to be darker than its page, and the only place
    #: `brand-dna.md:167` permits it: the presentation terminal on the home
    #: page, which is a picture of a terminal and has to look like one. It is
    #: emitted exactly once, by `build.py`.
    NAMED_PANEL = ".win.dark"

    def _scope_tokens(self, css: str) -> dict[str, dict[str, str]]:
        base: dict[str, str] = {}
        for block in (r'\[data-palette="G"\]',
                      r':root,\s*\n\[data-palette\]'):
            base.update(declarations((LANDING / "palettes.css").read_text(), block))
        light = {**base, **declarations(css, r":root")}
        out = {}
        for pattern, kind in self.SCOPES:
            out[pattern] = {"kind": kind, "tokens": {**light, **declarations(css, pattern)}}
        return out

    def test_no_surface_is_a_black_slab(self):
        css = _stylesheet()
        failures = []
        for pattern, scope in self._scope_tokens(css).items():
            palette = Palette(scope["tokens"])
            page = luminance(palette.rgb(scope["tokens"]["--cream"]))
            floor = self.DAYLIGHT_FLOOR if scope["kind"] == "light" else page
            for token in self.SURFACES:
                if token not in scope["tokens"]:
                    continue
                shade = luminance(palette.rgb(scope["tokens"][token]))
                if shade < floor:
                    failures.append(
                        f"{pattern} {token} = {scope['tokens'][token]} "
                        f"(luminance {shade:.4f} < {floor:.4f})"
                    )
        assert not failures, "surfaces darker than the page they sit on: " + "; ".join(failures)

    def test_the_night_page_is_not_an_unlit_screen(self):
        css = _stylesheet()
        night = declarations(css, r':root\[data-theme="dark"\]')
        page = luminance(Palette(night).rgb(night["--cream"]))
        assert page >= self.MIDNIGHT_FLOOR, (
            f"the night page is {night['--cream']} (luminance {page:.4f}); "
            "there is no room above it for four elevation steps"
        )
        steps = [
            luminance(Palette(night).rgb(night[t]))
            for t in ("--cream", "--cream-dark", "--surface-2", "--card-bg")
        ]
        assert steps == sorted(steps), f"the night elevation stack is not monotonic: {steps}"
        for lower, upper in zip(steps, steps[1:], strict=False):
            assert upper / lower >= 1.1, (
                f"two night layers are {upper / lower:.3f}x apart, which is not a step"
            )

    def test_only_the_named_panel_paints_below_the_floor(self):
        """The literal-hex half of the same rule.

        `--code-bg: #17160f` was a hand-written hex inside a rule, not a
        palette token, so a token-level check walks straight past it. This
        walks every rule in the file, resolves any hex it paints with, and
        allows exactly one selector to go dark.
        """
        css = _stylesheet()
        # One scope renders dark now, and it is graded against its own page.
        # There used to be a second -- the inverted band, which darkened one
        # section of a daylight page and needed its own floor because it was
        # *lighter* than the night page. That component is gone.
        floors = {}
        for pattern, marker in ((r':root\[data-theme="dark"\]', ':root[data-theme="dark"]'),):
            block = declarations(css, pattern)
            floors[marker] = luminance(Palette(block).rgb(block["--cream"]))

        offenders = []
        for selector, body in rules(css):
            if selector == self.NAMED_PANEL:
                continue
            dark = [m for m in floors if m in selector]
            floor = self.DAYLIGHT_FLOOR if not dark else min(floors[m] for m in dark)
            for name, value in re.findall(r"([a-z-][\w-]*)\s*:\s*([^;{}]+)", body):
                paints = name in ("background", "background-color") or any(
                    name == t for t in self.SURFACES
                )
                if not paints:
                    continue
                for hex_value in re.findall(r"#[0-9a-fA-F]{6}\b", value):
                    shade = luminance(Palette({}).rgb(hex_value))
                    if shade < floor:
                        offenders.append(f"{selector} {{ {name}: {hex_value} }} = {shade:.4f}")
        assert not offenders, (
            "hand-written near-black surfaces: " + "; ".join(offenders)
        )

    def test_the_one_dark_panel_is_still_the_one_that_was_signed_off(self):
        """The exemption above is only safe while it stays a single panel on
        a single page. `build.py` emits `.win dark` once, for the terminal
        demo in the hero; every other code block on the site is `.win lite`.
        """
        build = (LANDING / "build.py").read_text(encoding="utf-8")
        assert build.count('class="win dark') == 1, (
            "the dark window shell is emitted more than once"
        )
        css = _stylesheet()
        assert any(sel == self.NAMED_PANEL for sel, _ in rules(css)), "no .win.dark rule"
        # Comments removed first: the token block explains what these four
        # tokens were and why they went, and that prose is worth keeping.
        live = strip_comments(css)
        for stale in ("--code-bg", "--code-bar", "--code-note", "--code-line"):
            assert stale not in live, f"{stale} is back"


class TestTheLandingContrast:
    """Every ink, on every surface, in every scope the page can be in.

    The app stylesheet has had a contrast sweep since the first pass. This one
    had none, and it is the harder of the two files: `.band.invert` re-points
    the whole colourway inside its own subtree, and the dark theme re-points it
    back, so any given rule renders under four different token tables and a
    fix that lands in one can leave the other three broken. That is not
    hypothetical -- it is how two bugs shipped:

    *The washes.* The inverted band flipped `--ink` to cream and left the nine
    card washes at their daylight values, so the three cards under the pipeline
    diagram measured 1.07, 1.01 and 1.03 to one. Invisible text, on the busiest
    page on the site, in the default theme.

    *The window shell.* Same omission, one component over, found by this test
    while it was being written: `--win-bar` and `--win-body` were not
    re-pointed either, so a code panel in that band would have measured 1.09
    and 1.03. Nothing puts one there yet, which is exactly why a person would
    not have found it.

    A per-rule sweep would have missed both, because the text in question sets
    no colour of its own -- it inherits. So this grades the token table
    directly: the cross product of what ink can arrive with what surface can be
    underneath it.
    """

    #: The token tables a page can actually be in. There were four, because
    #: `[data-theme="dark"] .band.invert` was a dark page turned back to
    #: daylight and no rule about the theme attribute predicts that. The
    #: inverted band is gone, so two is the whole space -- but the docstring
    #: above stays, because the two bugs it records are the reason this sweep
    #: grades the token table rather than the rules.
    SCOPES = {
        "day": (r":root",),
        "night": (r":root", r':root\[data-theme="dark"\]'),
    }

    #: Anything a card, callout, badge, table row or code panel is painted
    #: with. Several are `rgba()` at night, so each is composited over its
    #: own scope's page colour before being measured.
    SURFACES = (
        "--cream", "--cream-dark", "--cream-deep", "--surface-2", "--card-bg",
        "--indigo-soft", "--indigo-ink-soft", "--iris-soft",
        "--orchid-soft", "--plum-soft", "--rose-soft", "--info-soft",
        "--success-soft", "--warning-soft", "--danger-soft",
        "--highlight-soft", "--win-bar", "--win-body",
    )

    #: The paper a wash itself can be painted onto: the five-step ladder plus
    #: the code panel. A wash never lands on another wash, so sweeping a tint
    #: across the whole of `SURFACES` above would grade pairings that cannot
    #: happen; sweeping it across only the page could not see the four that
    #: were happening.
    PAPER = ("--cream", "--cream-dark", "--cream-deep", "--surface-2",
             "--card-bg", "--win-bar", "--win-body")

    #: The two inks prose inherits. A heading and a paragraph inside a tinted
    #: card declare no colour, so these are what actually lands on the wash.
    PROSE = ("--ink", "--ink-light")

    #: `--ink-faint` is not in that list because in this stylesheet it is not
    #: an ink: it is the colour of a hover border, an arrowhead, a legend
    #: swatch and a progress fill. WCAG grades those at 3:1, not 4.5:1, and
    #: holding a hairline to body-text contrast would only push it until it
    #: stopped reading as a hairline. `test_the_hairline_ink_is_never_prose`
    #: is what keeps that claim true.
    HAIRLINE_FLOOR = 3.0

    def _table(self, blocks: tuple[str, ...]) -> Palette:
        tokens: dict[str, str] = {}
        for block in (r'\[data-palette="G"\]',
                      r':root,\s*\n\[data-palette\]'):
            tokens.update(declarations((LANDING / "palettes.css").read_text(), block))
        css = _stylesheet()
        for block in blocks:
            tokens.update(declarations(css, block))
        return Palette(tokens)

    @pytest.mark.parametrize("scope", list(SCOPES))
    def test_prose_clears_aa_on_every_surface_it_can_land_on(self, scope):
        palette = self._table(self.SCOPES[scope])
        page = palette.rgb("var(--cream)")
        failures = []
        for surface in self.SURFACES:
            behind = palette.rgb(f"var({surface})", page)
            for ink in self.PROSE:
                got = ratio(palette.rgb(f"var({ink})", behind), behind)
                if got < 4.5:
                    failures.append(f"{ink} on {surface} is {got:.2f}:1")
        assert not failures, f"{scope}: " + "; ".join(failures)

    @pytest.mark.parametrize("scope", list(SCOPES))
    def test_the_hairline_ink_clears_the_non_text_floor(self, scope):
        palette = self._table(self.SCOPES[scope])
        page = palette.rgb("var(--cream)")
        for surface in self.SURFACES:
            behind = palette.rgb(f"var({surface})", page)
            got = ratio(palette.rgb("var(--ink-faint)", behind), behind)
            assert got >= self.HAIRLINE_FLOOR, (
                f"{scope}: --ink-faint on {surface} is {got:.2f}:1, "
                "below the 3:1 non-text floor"
            )

    def test_the_hairline_ink_is_never_prose(self):
        """The exemption above is only honest while it holds.

        It did not, quietly: `.dpar-h i::before` painted its separator dot
        with `--ink-faint`, 3.59:1 on the page. axe cannot see it -- the
        contrast rule grades text nodes and that is generated content -- so
        it survived every scan the site has ever had.
        """
        offenders = [
            selector
            for selector, body in rules(_stylesheet())
            if re.search(r"(?:^|;)\s*color\s*:\s*var\(--ink-faint\)", body)
        ]
        assert not offenders, (
            f"--ink-faint is being used as text colour in {offenders}; it is graded "
            "at the 3:1 non-text floor, so it is not allowed to carry prose"
        )

    @pytest.mark.parametrize("scope", list(SCOPES))
    def test_a_semantic_ink_is_legible_on_its_own_tint(self, scope):
        """`.callout.warn` is `--warning` on `--warning-soft`, and the pairing
        is invisible in the stylesheet: two tokens, two rules, no place where
        they are written next to each other. The night theme shipped without a
        `--warning-soft` step for exactly that reason -- success and danger got
        one, warning was missed, and every warning callout stayed a daylight
        yellow panel under near-white text.

        The tint is swept over every surface, not just the page. Composited
        over the page only, this test passed while four components were failing
        in the browser: a badge sits in a card, not on the page, and a
        translucent wash over the lightest surface comes out lighter than the
        one that was measured. The warn badge was 5.88 on the page and 3.21 in
        a card, and only the second number is the one a reader gets.
        """
        palette = self._table(self.SCOPES[scope])
        pairs = (
            ("--success", "--success-soft"),
            ("--warning", "--warning-soft"),
            ("--danger-strong", "--danger-soft"),
            ("--accent-ink", "--info-soft"),
            ("--indigo-ink", "--indigo-soft"),
            ("--indigo-ink", "--indigo-ink-soft"),
            ("--iris-ink", "--iris-soft"),
            ("--orchid-ink", "--orchid-soft"),
            ("--plum-ink", "--plum-soft"),
            ("--rose-ink", "--rose-soft"),
        )
        failures = []
        for surface in self.PAPER:
            page = palette.rgb(f"var({surface})")
            for ink, tint in pairs:
                behind = palette.rgb(f"var({tint})", page)
                got = ratio(palette.rgb(f"var({ink})", behind), behind)
                if got < 4.5:
                    failures.append(f"{ink} on {tint} over {surface} is {got:.2f}:1")
        assert not failures, f"{scope}: " + "; ".join(failures)
