"""Two CSS mistakes that a screenshot at reading width cannot show you.

Both were found by driving a real library on a 320px viewport, and both are the
same shape: a declaration that is silently inert, so the stylesheet says what it
wants and the browser does something else.

*An ellipsis on an inline box.* `overflow` and `text-overflow` do not apply to a
non-replaced inline box. `white-space: nowrap` does. So a rule carrying all
three keeps the text on one line and clips nothing, and whether it works comes
down to which tag the JavaScript happened to render -- `<div>` fine, `<span>` or
`<a>` broken. Two of the four rules were broken this way. The suggestion
dropdown's title ran 906px past a 390px viewport and gave the whole page a
horizontal scrollbar; the related list's title ran 63px past the sheet.

*A hard floor in an `auto-fill` grid.* `minmax(300px, 1fr)` cannot go below
300px, so in a 270px content box every track is still 300px and the grid hangs
off the side. `minmax(min(300px, 100%), 1fr)` is identical whenever there is
room and shrinks instead of overflowing when there is not.

Both are asserted over every rule rather than the ones that were wrong, because
the next instance will be in a rule nobody is thinking about. Counts are
asserted for the reason `test_banned_colours` gives: a scan that finds nothing
has to be told apart from a scan that looked at nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CSS = Path(__file__).resolve().parents[1] / "src" / "facetmark" / "web" / "static" / "app.css"

#: A rule whose box is blockified by its parent's layout rather than by itself.
#: A flex or grid item's `display` is blockified by the spec, so an inline value
#: on it is already a block box and the clip works. Each entry has to name why
#: the parent guarantees it -- "it looked fine" is how the two live bugs got in.
BLOCKIFIED_BY_PARENT = {
    ".tab > span:first-child": "`.tab` is `display: flex`, so its children are blockified",
}


def _rules(css: str) -> list[tuple[int, str, str]]:
    """``(line, selector, body)`` for every rule in the sheet.

    Comments are stripped first: several selectors are discussed in prose above
    the rule they describe, and a comment mentioning `display: block` must not
    be read as declaring it.
    """
    stripped = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css, flags=re.S)
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", stripped):
        sel = " ".join(m.group(1).split())
        if not sel or sel.startswith("@"):
            continue
        out.append((stripped[: m.start()].count("\n") + 1, sel, m.group(2)))
    return out


@pytest.fixture(scope="module")
def rules() -> list[tuple[int, str, str]]:
    found = _rules(CSS.read_text(encoding="utf-8"))
    assert len(found) > 200, f"only parsed {len(found)} rules out of app.css -- the reader broke"
    return found


class TestAnEllipsisNeedsABlockBox:
    def test_every_ellipsis_rule_declares_the_box_it_clips_against(self, rules):
        clippers = [(ln, sel, body) for ln, sel, body in rules
                    if "text-overflow" in body and "ellipsis" in body]
        assert len(clippers) >= 4, f"expected the sheet's ellipsis rules, found {len(clippers)}"

        inert = []
        for ln, sel, body in clippers:
            if sel in BLOCKIFIED_BY_PARENT:
                continue
            display = re.search(r"display:\s*([\w-]+)", body)
            # `-webkit-box` is the line-clamp idiom and is a block container too.
            if display and display.group(1) in {"block", "flex", "grid", "-webkit-box", "flow-root"}:
                continue
            inert.append(f"app.css:{ln} `{sel}` declares an ellipsis but not a block box")
        assert not inert, (
            "`overflow` and `text-overflow` are ignored on an inline box, so these clip "
            "nothing unless the element happens to be rendered as a div:\n  " + "\n  ".join(inert)
        )

    def test_the_blockified_allowlist_has_not_gone_stale(self, rules):
        """An allowlist entry for a rule that no longer exists is a lie."""
        present = {sel for _, sel, _ in rules}
        missing = sorted(set(BLOCKIFIED_BY_PARENT) - present)
        assert not missing, f"allowlisted selectors that are no longer in the sheet: {missing}"


class TestAnAutoFillGridMustBeAbleToShrink:
    def test_no_track_has_a_floor_wider_than_its_container_can_be(self, rules):
        css = CSS.read_text(encoding="utf-8")
        # Only the repeating grids: an explicit track list sized `minmax(120px,
        # 1fr)` is one column of a fixed layout and has its own media query.
        repeats = re.findall(
            r"repeat\(auto-(?:fill|fit),\s*minmax\((.+?),\s*1fr\)\)", css
        )
        assert len(repeats) >= 6, f"expected the sheet's auto grids, found {len(repeats)}"

        hard = [r.strip() for r in repeats if not r.strip().startswith("min(")]
        assert not hard, (
            "a minmax floor is hard, so on a narrow phone every track keeps this width and "
            f"the grid overflows the page. Use `min(Npx, 100%)`: {hard}"
        )
