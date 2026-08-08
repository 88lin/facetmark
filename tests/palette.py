"""Resolve the stylesheet's custom properties and measure WCAG contrast.

Shared by ``tests/test_web.py`` and ``tests/test_landing.py``: both stylesheets
consume the same vendored ``palettes.css``, so both need the same resolver.

The maths is WCAG 2.1's relative luminance and contrast ratio, ported from
``scripts/validate-palettes.mjs`` in the upstream design system so the two
projects grade the same colours the same way.
"""

from __future__ import annotations

import re

Rgb = tuple[int, int, int]


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def declarations(css: str, selector: str) -> dict[str, str]:
    """The custom properties declared in the first block matching ``selector``.

    ``selector`` is a regex, because the palette file groups selectors
    (``:root,\\n[data-palette="A"]``) and the dark block is an attribute
    selector.
    """
    m = re.search(rf"(?:^|\n){selector}\s*\{{(.*?)\n\}}", strip_comments(css), re.S)
    if not m:
        raise AssertionError(f"no block matching {selector!r}")
    return {k: v.strip() for k, v in re.findall(r"(--[\w-]+):\s*([^;]+);", m.group(1))}


def rules(css: str) -> list[tuple[str, str]]:
    """(selector, body) for every non-nested rule, comments removed."""
    out = []
    for m in re.finditer(r"(?:^|\n)([^{}\n@][^{}]*?)\{([^{}]*)\}", strip_comments(css)):
        out.append((" ".join(m.group(1).split()), m.group(2)))
    return out


def painted(css: str) -> dict[str, str]:
    """Every selector that paints a background, in declaration order.

    The value is the colour expression only: ``background`` is a shorthand and
    may carry a gradient or a position after the colour.
    """
    out: dict[str, str] = {}
    for sel, body in rules(css):
        value = value_of(body, "background-color") or value_of(body, "background")
        colour = first_colour(value) if value else None
        if not colour:
            continue
        for one in sel.split(","):
            out[one.strip()] = colour
    return out


def _compound_bg(compound: str, surfaces: dict[str, str]) -> str | None:
    """The background painted on one compound selector, e.g. ``.num.pop``.

    An element written ``.num.pop`` is matched by the ``.num`` rule too, so if
    the compound itself paints nothing its parts are tried, last declaration
    first, which is how the cascade would resolve a specificity tie.
    """
    if compound in surfaces:
        return surfaces[compound]
    order = list(surfaces)
    parts = re.findall(r"[.#]?[\w-]+(?:\[[^\]]*\])?", compound)
    known = [p for p in parts if p in surfaces]
    if not known:
        return None
    return surfaces[max(known, key=order.index)]


def backdrop_of(selector: str, surfaces: dict[str, str]) -> str | None:
    """The colour an element sits on, read off its nearest painted ancestor.

    ``.hit .title`` has no background of its own but is never seen anywhere
    except inside ``.hit``, so grading it against the page background asks a
    question the interface never poses.
    """
    parts = selector.split()
    for i in range(len(parts) - 1, 0, -1):
        hit = _compound_bg(parts[i - 1], surfaces)
        if hit:
            return hit
    return None


def value_of(body: str, prop: str) -> str | None:
    """The declared value of ``prop`` in a rule body, or None."""
    m = re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;]+)", body)
    return m.group(1).strip() if m else None


def first_colour(value: str) -> str | None:
    """The leading colour token of a value, counting parentheses.

    ``rgba(var(--ink-rgb), .06)`` nests one function inside another, so a
    non-greedy ``\\([^)]*\\)`` stops at the wrong bracket and hands back
    ``rgba(var(--ink-rgb)``. This walks the string instead.
    """
    value = value.strip()
    m = re.match(r"(var|rgba|rgb|hsl|hsla)\(", value)
    if m:
        depth = 0
        for i, ch in enumerate(value):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return value[: i + 1]
        return None
    m = re.match(r"#[0-9a-fA-F]{3,8}\b", value)
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# colour
# ---------------------------------------------------------------------------


def _hex_to_rgb(text: str) -> Rgb:
    h = text.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _over(fg: Rgb, alpha: float, bg: Rgb) -> Rgb:
    return tuple(round(alpha * f + (1 - alpha) * b) for f, b in zip(fg, bg, strict=True))  # type: ignore[return-value]


class Palette:
    """A resolved set of custom properties.

    Values are kept as source text and resolved on demand, because ``var()``
    chains and ``rgba(var(--x-rgb), a)`` both need the whole table to be
    present before any of them can be evaluated.
    """

    def __init__(self, tokens: dict[str, str]):
        self.tokens = dict(tokens)

    def raw(self, name: str) -> str:
        if name not in self.tokens:
            raise AssertionError(f"token {name} is not defined")
        return self.tokens[name]

    def rgb(self, value: str, backdrop: Rgb = (255, 255, 255)) -> Rgb:
        """Flatten a colour expression to opaque RGB over ``backdrop``."""
        value = value.strip()

        m = re.fullmatch(r"var\((--[\w-]+)\)", value)
        if m:
            return self.rgb(self.raw(m.group(1)), backdrop)

        if value.startswith("#"):
            return _hex_to_rgb(value)

        m = re.fullmatch(r"rgba?\(\s*(.+?)\s*\)", value)
        if m:
            inner = m.group(1)
            chan = re.fullmatch(r"var\((--[\w-]+)\)\s*,\s*([\d.]+)", inner)
            if chan:
                triple = self.raw(chan.group(1))
                base = tuple(int(x) for x in triple.split(","))
                return _over(base, float(chan.group(2)), backdrop)  # type: ignore[arg-type]
            parts = [p.strip() for p in re.split(r"[,/]", inner)]
            base = tuple(int(float(p)) for p in parts[:3])
            alpha = float(parts[3]) if len(parts) > 3 else 1.0
            return _over(base, alpha, backdrop)  # type: ignore[arg-type]

        raise AssertionError(f"cannot resolve colour {value!r}")

    def has_alpha(self, value: str) -> bool:
        value = value.strip()
        m = re.fullmatch(r"var\((--[\w-]+)\)", value)
        if m:
            return self.has_alpha(self.raw(m.group(1)))
        return value.startswith("rgba(")


def luminance(rgb: Rgb) -> float:
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: Rgb, bg: Rgb) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)
