"""The three colour families the owner ruled out, measured on every surface.

`不要黑色界面 ... 颜色也不要咖啡色、棕色、浓绿色的色系，这一整个系列都不要`.
Three families, named as families rather than as values: coffee/brown, deep
green and teal, and dead near-black. Every other colour test in this repo asks
whether a pairing is *legible*; none of them asks whether a colour is one the
owner refused. Both of the palettes this project has shipped passed the
contrast sweeps while painting exactly what he did not want, which is why this
file exists.

Two halves, because either one alone has a hole a real change can walk through.

*The literals.* Every hex and `rgb()` written into the three stylesheets, into
the inline `style` attributes of the generated markup, and into the favicon.
This is the half that catches a hand-written value -- `--code-bg: #17160f` was
one, and no token-level check could see it.

*The resolved tokens.* Every `var()` a stylesheet consumes, followed through
the cascade to the literal it lands on, for both themes. This is the half that
catches a *deletion*. `palettes.css` is vendored verbatim and ships
`--success: #2E7955` (deep green) and `--warning: #8A6A00` (brown); all three
stylesheets override both. Remove an override and the literal half sees nothing
change while the page goes back to painting the banned colour. The vendored file
is never scanned directly -- it carries ten colourways and most of them are full
of hues this project does not use -- so following the tokens the sheets actually
read is the only honest way to reach it.

Alpha is dropped rather than composited. `rgba(var(--x-rgb), 0.08)` over cream
is a pale tint of x, and the instruction was about the family, not the strength:
a 8% brown still reads as beige. `Palette.rgb` composites, which is right for
contrast and wrong here, so this file resolves to the base triple instead.

Every count is asserted. A scan that finds nothing is indistinguishable from a
scan that looked at nothing, and this repo has shipped that mistake before --
`test_no_dark_panel_in_a_functional_area` named a token no stylesheet consumed
and could not have fired.
"""

from __future__ import annotations

import colorsys
import re
from pathlib import Path

import pytest

from tests.palette import Palette, declarations, rules, strip_comments

REPO = Path(__file__).resolve().parents[1]
LANDING = REPO / "docs" / "landing"
STATIC = REPO / "src" / "facetmark" / "web" / "static"
EXTENSION = REPO / "extension" / "src"

Rgb = tuple[int, int, int]


# ---------------------------------------------------------------------------
# the judgement
# ---------------------------------------------------------------------------


def hsl(rgb: Rgb) -> tuple[int, int, int]:
    """Hue in degrees, saturation and lightness in percent."""
    r, g, b = (c / 255 for c in rgb)
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return round(hue * 360), round(sat * 100), round(light * 100)


#: The three families, as regions of HSL rather than as lists of values, so a
#: new hue nobody has written yet is still caught.
#:
#: `BROWN` is the orange-through-yellow arc once it stops being bright: coffee,
#: chocolate, tan, khaki and olive are all the same arc at different lightness,
#: and above 62% it stops reading as brown and starts reading as cream or gold
#: -- which the palette does use, at 76%. The 6% saturation floor keeps warm
#: greys out of it.
#:
#: `DEEPGREEN` is green through teal below half lightness: bottle green, forest,
#: pine, petrol. Above 50% it is mint or sage, which is a different complaint.
#: The 12% floor keeps cool greys out. The ceiling is hue 195 because the
#: retired `--aqua` sat at 179 and petrol keeps reading as petrol up to about
#: there; past 195 it is a blue, and the palette does use one -- indigo, at 217.
#:
#: `DEADBLACK` is anything with almost no hue left below 14% lightness. The
#: night pages this project shipped and had rejected -- `#131310`, `#17160f`,
#: `#1c1b18` -- are all caught, though as it happens they are caught by BROWN:
#: each keeps a trace of warm hue, so it is in both regions at once and the
#: first branch names it. The violet night page `#241f2e` is in neither, at 15%
#: lightness and 19% saturation on hue 260.
FAMILIES: dict[str, str] = {
    "BROWN": "coffee, chocolate, tan, khaki and olive",
    "DEEPGREEN": "bottle green, forest, pine and petrol",
    "DEADBLACK": "near-black with the hue drained out",
}


def family(rgb: Rgb) -> str:
    hue, sat, light = hsl(rgb)
    if 15 <= hue <= 62 and sat >= 6 and light < 62:
        return "BROWN"
    if 70 <= hue <= 195 and light < 50 and sat >= 12:
        return "DEEPGREEN"
    if sat < 8 and light < 14:
        return "DEADBLACK"
    return ""


HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
#: `rgb()` / `rgba()` whose first channel is a number. The `rgba(var(--x-rgb),
#: a)` shape is reached through the var() branch instead, so it is not matched
#: here twice.
NUMERIC_RGB = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")
VAR = re.compile(r"var\(\s*(--[\w-]+)")
#: The `--*-rgb` channel tokens the palette ships, e.g. `36, 30, 46`.
TRIPLE = re.compile(r"^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*$")


def _from_hex(lit: str) -> Rgb | None:
    body = lit.lstrip("#")
    if len(body) == 3:
        body = "".join(c * 2 for c in body)
    if len(body) not in (6, 8):  # #rgba and other lengths carry no opaque base
        return None
    return (int(body[0:2], 16), int(body[2:4], 16), int(body[4:6], 16))


def bases(value: str, pal: Palette | None = None, seen: frozenset[str] = frozenset()) -> list[tuple[str, Rgb]]:
    """(source text, base RGB) for every colour a value is made of.

    `var()` chains are followed when a palette is supplied, so one call reaches
    both what the stylesheet wrote and what the vendored file behind it says.
    Shadows -- any triple that is all zeroes -- drop out: `rgba(0, 0, 0, 0.05)`
    is the design system's own shadow literal, it is not brand colour, and
    judging it would report every elevation step as dead black.
    """
    out: list[tuple[str, Rgb]] = []
    for lit in HEX.findall(value):
        rgb = _from_hex(lit)
        if rgb and rgb != (0, 0, 0):
            out.append((lit, rgb))
    for m in NUMERIC_RGB.finditer(value):
        rgb = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if rgb != (0, 0, 0):
            out.append((m.group(0) + ", ...)", rgb))
    if pal is None:
        return out
    for name in VAR.findall(value):
        if name in seen or name not in pal.tokens:
            continue
        raw = pal.raw(name)
        m = TRIPLE.match(raw)
        if m:
            rgb = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if rgb != (0, 0, 0):
                out.append((f"{name} -> {raw.strip()}", rgb))
            continue
        for text, rgb in bases(raw, pal, seen | {name}):
            out.append((f"{name} -> {text}", rgb))
    return out


# ---------------------------------------------------------------------------
# the surfaces
# ---------------------------------------------------------------------------

#: Palette G -- Orchid -- cascades twice: the colourway, then the semantic
#: aliases every colourway shares. Palette A also carried a third block of AA
#: corrections; G ships display colours that already clear AA and has none.
PALETTE_BLOCKS = (
    r'\[data-palette="G"\]',
    r':root,\s*\n\[data-palette\]',
)

#: Each stylesheet, the palette file it reads, the selector its night block
#: uses, and the floor on how many colours the scan has to find in it. The
#: floors are the counts as shipped, minus a little room to edit: they are here
#: so that a scan which suddenly sees half the file fails instead of passing.
SHEETS = {
    "site style.css": (LANDING / "style.css", LANDING / "palettes.css",
                       r':root\[data-theme="dark"\]', 120),
    "app app.css": (STATIC / "app.css", STATIC / "palettes.css",
                    r'html\[data-theme="dark"\]', 120),
    "extension popup.css": (EXTENSION / "popup.css", STATIC / "palettes.css",
                            r"@media \(prefers-color-scheme: dark\)\s*\{\s*:root", 30),
}

#: Generated markup, the source pages plus the app shell. Stage 6 lesson 6: a
#: test that reads a stylesheet cannot see an inline `style` attribute.
def _markup() -> list[Path]:
    return (
        sorted(LANDING.glob("*.html"))
        + [REPO / "src" / "facetmark" / "web" / "index.html"]
    )


#: The landing copy and the app shell copy. They are pinned byte-identical
#: elsewhere; scanning each is cheap and means a hand-edited copy cannot hide
#: behind that pin.
FAVICONS = (
    LANDING / "assets" / "favicon.svg",
    STATIC / "favicon.svg",
)


def _table(sheet: Path, palettes: Path, dark: str, theme: str) -> Palette:
    css = sheet.read_text(encoding="utf-8")
    tokens: dict[str, str] = {}
    for block in PALETTE_BLOCKS:
        tokens.update(declarations(palettes.read_text(encoding="utf-8"), block))
    tokens.update(declarations(css, r":root"))
    if theme == "dark":
        tokens.update(declarations(css, dark))
    return Palette(tokens)


def _report(rows: list[tuple[str, str, str, str, Rgb]]) -> str:
    lines = []
    for fam, where, prop, text, rgb in rows:
        hue, sat, light = hsl(rgb)
        lines.append(
            f"{fam} ({FAMILIES[fam]}): {text} = rgb{rgb} "
            f"H{hue} S{sat}% L{light}%  in  {where} {{ {prop} }}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# the tests
# ---------------------------------------------------------------------------


class TestNoColourFallsInAFamilyTheOwnerRuledOut:
    @pytest.mark.parametrize("label", list(SHEETS))
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_the_stylesheet_paints_nothing_from_a_banned_family(self, label, theme):
        sheet, palettes, dark, floor = SHEETS[label]
        css = strip_comments(sheet.read_text(encoding="utf-8"))
        pal = _table(sheet, palettes, dark, theme)
        rows, checked = [], 0
        for selector, body in rules(css):
            for decl in body.split(";"):
                if ":" not in decl:
                    continue
                prop, value = decl.split(":", 1)
                for text, rgb in bases(value, pal):
                    checked += 1
                    if fam := family(rgb):
                        rows.append((fam, selector.strip()[:60], prop.strip(), text, rgb))
        assert checked >= floor, (
            f"{label} {theme}: the scan only resolved {checked} colours, below the "
            f"{floor} this file paints; it is not measuring what it claims to"
        )
        assert not rows, (
            f"{label}, {theme} theme -- {len(rows)} colour(s) in a ruled-out "
            f"family:\n{_report(rows)}"
        )

    def test_the_generated_markup_carries_no_banned_inline_colour(self):
        rows, checked, attributes = [], 0, 0
        for path in _markup():
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r'style="([^"]*)"', text):
                attributes += 1
                for lit, rgb in bases(m.group(1)):
                    checked += 1
                    if fam := family(rgb):
                        rows.append((fam, path.name, "style", lit, rgb))
            for m in re.finditer(r'(?:fill|stroke|stop-color|color)="([^"]*)"', text):
                for lit, rgb in bases(m.group(1)):
                    checked += 1
                    if fam := family(rgb):
                        rows.append((fam, path.name, "presentation attribute", lit, rgb))
        # The markup is *meant* to carry no colour of its own -- the widths on
        # the bar charts are the only inline styles the generator writes. So the
        # honest floor is on the attributes examined, not on colours found:
        # zero colours is the expected answer, zero attributes means the scan
        # missed the markup entirely.
        assert attributes >= 20, (
            f"only {attributes} inline style attributes examined across "
            f"{len(_markup())} pages; the markup scan is not reaching them"
        )
        assert not rows, f"{len(rows)} inline colour(s) in a ruled-out family:\n{_report(rows)}"

    @pytest.mark.parametrize("path", FAVICONS, ids=lambda p: str(p.relative_to(REPO)))
    def test_the_mark_carries_no_banned_colour(self, path):
        rows, checked = [], 0
        for m in re.finditer(r'(?:fill|stroke|stop-color)="([^"]*)"', path.read_text(encoding="utf-8")):
            for lit, rgb in bases(m.group(1)):
                checked += 1
                if fam := family(rgb):
                    rows.append((fam, path.name, "fill", lit, rgb))
        assert checked >= 5, f"{path.name}: only {checked} fills found; the mark has five"
        assert not rows, f"{path.name}:\n{_report(rows)}"

    def test_the_judgement_still_recognises_what_it_was_written_for(self):
        """The classifier is the whole test, so it is checked against the values
        that caused the complaint rather than trusted.

        Left column: shipped and rejected. Right column: shipped and kept --
        including the two that sit just outside a boundary, because a family
        test that also catches the page's own gold and its violet night surface
        is a test that will be deleted rather than fixed.
        """
        # The three rejected night pages keep a trace of warm hue, so each one
        # is inside BROWN's arc and inside DEADBLACK's region at the same time
        # -- `#1c1b18` is hue 45 at 8% saturation and 10% lightness, which is
        # both "olive with the light off" and "black that never quite drained".
        # Which name the classifier reaches first is branch order, not a fact
        # about the colour, so those three are allowed either answer. `#0a0a0a`
        # pins DEADBLACK on its own, so the region cannot rot into dead code.
        banned: dict[str, set[str]] = {
            "#17160f": {"BROWN", "DEADBLACK"},  # the code panel on every doc page
            "#131310": {"BROWN", "DEADBLACK"},  # the first night page
            "#1c1b18": {"BROWN", "DEADBLACK"},  # the second one
            "#0a0a0a": {"DEADBLACK"},           # hueless, so only one name fits
            "#4f9a6b": {"DEEPGREEN"},           # --mint, the retired lane hue
            "#3e9290": {"DEEPGREEN"},           # --aqua
            "#c97845": {"BROWN"},               # --peach
            "#2e7955": {"DEEPGREEN"},           # the vendored --success
            "#8a6a00": {"BROWN"},               # the vendored --warning
            "#6f5a3a": {"BROWN"},               # plain coffee, for the arc itself
        }
        for lit, expected in banned.items():
            got = family(_from_hex(lit))
            assert got in expected, (
                f"{lit} judged {got or 'clean'}, expected {' or '.join(sorted(expected))}"
            )
        for lit in ("#f6dc8e", "#fcf3d9", "#241f2e", "#241e2e", "#71519b",
                    "#523776", "#b54070", "#fdfbf7", "#6b6675", "#c9bdd9"):
            got = family(_from_hex(lit))
            assert not got, f"{lit} is in the shipped palette and was judged {got}"
