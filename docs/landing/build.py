#!/usr/bin/env python3
"""Build the facetmark landing site.

Six static pages, no dependencies, no build chain:

    index.html     index.zh.html      the landing page
    guide.html     guide.zh.html      install -> import -> index -> search -> serve
    measured.html  measured.zh.html   every retrieval claim and its protocol

Copy is held in content_en.py / content_zh.py so that the two languages stay
structurally identical and drift is visible in a diff.  Run:

    python docs/landing/build.py
"""

from __future__ import annotations

import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from content_en import EN, REPO  # noqa: E402
from content_zh import ZH  # noqa: E402

# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

_TAG = re.compile(r"<[^>]+>")
_NUMISH = re.compile(r"^[+\-\u2212]?[\d.,]+\s*(pp|ms|s|%|\u00d7|x|/\s*[\d.,]+)?$")


def _plain(cell: str) -> str:
    return html.unescape(_TAG.sub("", cell)).strip()


def _is_num(cell: str) -> bool:
    p = _plain(cell)
    return bool(p) and bool(_NUMISH.match(p))


def esc(text: str) -> str:
    return html.escape(text, quote=False)


# --------------------------------------------------------------------------
# block renderer for the guide / measured mini-language
# --------------------------------------------------------------------------


def r_cb(label: str, code: str) -> str:
    """A code block with a copy button.  ``code`` is escaped, never trusted."""
    return (
        '<div class="cb">'
        f'<div class="cb-bar"><span>{esc(label)}</span>'
        f'<button type="button" data-copy data-label="{esc(COPY["label"])}" '
        f'data-done="{esc(COPY["done"])}">{esc(COPY["label"])}</button></div>'
        f"<pre><code>{esc(code.strip(chr(10)))}</code></pre>"
        "</div>"
    )


def r_table(head: list[str], rows: list[list[str]], win: tuple[int, ...] = ()) -> str:
    out = ['<div class="tw"><table><thead><tr>']
    out += [f"<th>{h}</th>" for h in head]
    out.append("</tr></thead><tbody>")
    for i, row in enumerate(rows):
        cls = ' class="win"' if i in win else ""
        out.append(f"<tr{cls}>")
        for j, cell in enumerate(row):
            tag = "th" if False else "td"
            klass = ' class="num"' if j and _is_num(cell) else ""
            out.append(f"<{tag}{klass}>{cell}</{tag}>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def r_block(b: tuple) -> str:
    kind = b[0]
    if kind == "p":
        return f"<p>{b[1]}</p>"
    if kind == "h3":
        return f"<h3>{b[1]}</h3>"
    if kind == "ul":
        return "<ul>" + "".join(f"<li>{x}</li>" for x in b[1]) + "</ul>"
    if kind == "ol":
        return "<ol>" + "".join(f"<li>{x}</li>" for x in b[1]) + "</ol>"
    if kind == "steps":
        return '<ol class="steps">' + "".join(f"<li>{x}</li>" for x in b[1]) + "</ol>"
    if kind == "cb":
        return r_cb(b[1], b[2])
    if kind == "table":
        return r_table(b[1], b[2], tuple(b[3]) if len(b) > 3 else ())
    if kind == "callout":
        return (
            f'<div class="callout {b[1]}"><div class="t">{b[2]}</div>{b[3]}</div>'
        )
    if kind == "raw":
        return b[1]
    raise ValueError(f"unknown block: {kind!r}")


def r_blocks(blocks: list[tuple]) -> str:
    return "".join(r_block(b) for b in blocks)


# --------------------------------------------------------------------------
# the pipeline diagram
#
# Hand-authored SVG rather than an image, so it inherits the theme tokens,
# stays sharp at any zoom, and the text is selectable and translatable.
# --------------------------------------------------------------------------

DIAGRAM = {
    "en": {
        "q": ("your query", "one line, typed"),
        "u": ("understand", "language, intent"),
        "f": [
            ("lexical \u00b7 trigram", "FTS5 over characters", "off by default"),
            ("lexical \u00b7 segments", "FTS5 over words", "off by default"),
            ("content", "vector over the page body", ""),
            ("intent", "vectors over generated questions", "off by default"),
        ],
        "rrf": ("RRF", "k = 60"),
        "post": ("post-stages", ["context gate", "cold layer", "reranker"]),
        "hits": ("hits", "ranked"),
        "graph": ("1-hop graph", "session + semantic edges"),
        "linked": ("linked", "separate group"),
        "legend_on": "shipped default path",
        "legend_off": "built, wired, off by default",
        "branch": "branches off the fusion step",
    },
    "zh": {
        "q": ("\u4f60\u7684\u95ee\u9898", "\u6253\u51fa\u6765\u7684\u4e00\u53e5\u8bdd"),
        "u": ("\u7406\u89e3", "\u8bed\u8a00\u3001\u610f\u56fe"),
        "f": [
            (
                "\u8bcd\u9762 \u00b7 \u4e09\u5143\u7ec4",
                "FTS5\uff0c\u6309\u5b57\u7b26\u5207",
                "\u9ed8\u8ba4\u5173\u95ed",
            ),
            (
                "\u8bcd\u9762 \u00b7 \u5206\u8bcd",
                "FTS5\uff0c\u6309\u8bcd\u5207",
                "\u9ed8\u8ba4\u5173\u95ed",
            ),
            ("\u5185\u5bb9", "\u6b63\u6587\u7684\u5411\u91cf", ""),
            (
                "\u610f\u56fe",
                "\u751f\u6210\u95ee\u53e5\u7684\u5411\u91cf",
                "\u9ed8\u8ba4\u5173\u95ed",
            ),
        ],
        "rrf": ("RRF \u878d\u5408", "k = 60"),
        "post": (
            "\u540e\u7f6e\u9636\u6bb5",
            ["\u60c5\u666f\u95f8\u95e8", "\u51b7\u5c42", "\u91cd\u6392"],
        ),
        "hits": ("\u7ed3\u679c", "\u5df2\u6392\u5e8f"),
        "graph": (
            "\u4e00\u8df3\u56fe\u6269\u5c55",
            "\u4f1a\u8bdd\u8fb9 + \u8bed\u4e49\u8fb9",
        ),
        "linked": ("\u76f8\u5173", "\u5355\u72ec\u4e00\u7ec4"),
        "legend_on": "\u9ed8\u8ba4\u771f\u6b63\u8d70\u7684\u8def\u5f84",
        "legend_off": "\u5199\u597d\u4e86\u3001\u63a5\u597d\u4e86\uff0c\u9ed8\u8ba4\u5173\u7740",
        "branch": "\u4ece\u878d\u5408\u8fd9\u4e00\u6b65\u5206\u51fa\u53bb",
    },
}

FACET_Y = (10, 88, 166, 244)  # boxes are 62 tall: title, subtitle, default note
FACET_H = 62
MID = FACET_Y[2] + FACET_H // 2  # everything on the spine lines up with `content`
ON = 2  # the content facet is the only one on by default


def _box(x, y, w, h, cls="d-box", r=9):
    return f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" stroke-width="1.5"/>'


def _t(x, y, s, cls="d-t", anchor="middle"):
    return f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{esc(s)}</text>'


def diagram(lang: str) -> str:
    d = DIAGRAM[lang]
    p: list[str] = []

    p.append('<svg viewBox="0 0 1020 430" role="img" xmlns="http://www.w3.org/2000/svg" '
             f'aria-label="{esc(d["q"][0])} \u2192 {esc(d["rrf"][0])} \u2192 {esc(d["hits"][0])}">')
    p.append(
        '<defs>'
        '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">'
        '<path class="d-head" d="M0,0 L10,5 L0,10 z"/></marker>'
        '<marker id="ahOn" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">'
        '<path class="d-head-on" d="M0,0 L10,5 L0,10 z"/></marker>'
        "</defs>"
    )

    m = MID

    # your query -> understand
    p.append(_box(10, m - 27, 130, 54, "d-box-key"))
    p.append(_t(75, m - 4, d["q"][0]))
    p.append(_t(75, m + 13, d["q"][1], "d-s"))
    p.append(f'<path class="d-arrow" d="M140,{m} H166" stroke-width="1.6" marker-end="url(#ah)"/>')

    p.append(_box(178, m - 27, 108, 54))
    p.append(_t(232, m - 4, d["u"][0]))
    p.append(_t(232, m + 13, d["u"][1], "d-s"))

    # understand -> four facets -> RRF
    for i, y in enumerate(FACET_Y):
        cy = y + FACET_H // 2
        on = i == ON
        acls = "d-arrow-on" if on else "d-arrow"
        mark = "url(#ahOn)" if on else "url(#ah)"
        w = "2" if on else "1.4"
        p.append(
            f'<path class="{acls}" d="M286,{m} C304,{m} 302,{cy} 320,{cy}" '
            f'stroke-width="{w}" marker-end="{mark}"/>'
        )
        p.append(_box(326, y, 218, FACET_H, "d-box-on" if on else "d-box"))
        title, sub, off = d["f"][i]
        p.append(_t(435, y + 21, title))
        p.append(_t(435, y + 38, sub, "d-s"))
        if off:
            p.append(_t(435, y + 54, off, "d-s-off"))
        p.append(
            f'<path class="{acls}" d="M544,{cy} C568,{cy} 570,{m} 594,{m}" '
            f'stroke-width="{w}" marker-end="{mark}"/>'
        )

    # RRF
    p.append(_box(600, m - 27, 102, 54, "d-box-on"))
    p.append(_t(651, m - 4, d["rrf"][0]))
    p.append(_t(651, m + 13, d["rrf"][1], "d-s"))

    # RRF -> post-stages -> hits
    p.append(f'<path class="d-arrow-on" d="M702,{m} H734" stroke-width="2" marker-end="url(#ahOn)"/>')
    p.append(_box(740, m - 46, 126, 92))
    p.append(_t(803, m - 25, d["post"][0]))
    for k, line in enumerate(d["post"][1]):
        p.append(_t(803, m - 5 + k * 17, line, "d-s"))
    p.append(f'<path class="d-arrow-on" d="M866,{m} H898" stroke-width="2" marker-end="url(#ahOn)"/>')
    p.append(_box(904, m - 27, 106, 54, "d-box-key"))
    p.append(_t(957, m - 4, d["hits"][0]))
    p.append(_t(957, m + 13, d["hits"][1], "d-s"))

    # graph expansion, returned as a separate group rather than mixed in
    gy = 306
    p.append(
        f'<path class="d-arrow" d="M651,{m + 27} V{gy + 15} Q651,{gy + 27} 663,{gy + 27} H694" '
        'stroke-width="1.5" marker-end="url(#ah)"/>'
    )
    p.append(_box(700, gy, 166, 54))
    p.append(_t(783, gy + 23, d["graph"][0]))
    p.append(_t(783, gy + 39, d["graph"][1], "d-s"))
    p.append(f'<path class="d-arrow" d="M866,{gy + 27} H898" stroke-width="1.5" marker-end="url(#ah)"/>')
    p.append(_box(904, gy, 106, 54, "d-box-key"))
    p.append(_t(957, gy + 23, d["linked"][0]))
    p.append(_t(957, gy + 39, d["linked"][1], "d-s"))

    # legend
    p.append('<path class="d-arrow-on" d="M14,404 H46" stroke-width="2.4"/>')
    p.append(_t(54, 408, d["legend_on"], "d-s", "start"))
    p.append('<path class="d-arrow" d="M300,404 H332" stroke-width="1.6" stroke-dasharray="5 3"/>')
    p.append(_t(340, 408, d["legend_off"], "d-s", "start"))
    p.append("</svg>")
    return "".join(p)


def _dn(title: str, sub: str, off: str = "", cls: str = "") -> str:
    """One node of the stacked (narrow-screen) diagram."""
    s = f'<div class="dn{(" " + cls) if cls else ""}"><b>{esc(title)}</b>'
    if sub:
        s += f"<i>{esc(sub)}</i>"
    if off:
        s += f"<s>{esc(off)}</s>"
    return s + "</div>"


def diagram_stack(lang: str) -> str:
    """A vertical rewrite of the same pipeline for phone widths.

    Below ~880px the wide SVG would either shrink its labels to ~8px or force
    three screens of sideways scrolling, so narrow screens get this instead.
    Same nodes, same wording, same on/off colouring.
    """
    d = DIAGRAM[lang]
    a_on = '<div class="darr" aria-hidden="true"></div>'
    a_off = '<div class="darr mut" aria-hidden="true"></div>'
    p = ['<div class="dstack">']
    p.append(_dn(d["q"][0], d["q"][1], cls="key"))
    p.append(a_on)
    p.append(_dn(d["u"][0], d["u"][1]))
    p.append(a_on)
    p.append('<div class="dgrid">')
    for k, (title, sub, off) in enumerate(d["f"]):
        p.append(_dn(title, sub, off, "on" if k == ON else "off"))
    p.append("</div>")
    p.append(a_on)
    p.append(_dn(d["rrf"][0], d["rrf"][1], cls="on"))
    p.append(a_on)
    p.append(_dn(d["post"][0], " \u00b7 ".join(d["post"][1])))
    p.append(a_on)
    p.append(_dn(d["hits"][0], d["hits"][1], cls="key"))
    p.append(f'<p class="dbr">{esc(d["branch"])}</p>')
    p.append(_dn(d["graph"][0], d["graph"][1]))
    p.append(a_off)
    p.append(_dn(d["linked"][0], d["linked"][1], cls="key"))
    p.append(
        '<p class="dlegend"><span class="k on"></span>'
        f'{esc(d["legend_on"])}<span class="k off"></span>{esc(d["legend_off"])}</p>'
    )
    p.append("</div>")
    return "".join(p)


# --------------------------------------------------------------------------
# terminal: a static first frame so the block is never empty without JS
# --------------------------------------------------------------------------

DEMO1 = {
    "q": "sqlite-vec latency shard recall",
    "kind": "content",
    "ms": "17.0",
    "target": 2,
    "hits": [
        ("Why chromadb changes the recall story", "0.0776"),
        ("sqlite-vec: notes on embedding", "0.0829"),
        ("hnswlib-5: notes on index", "0.0768"),
        ("qdrant-6: notes on persistence", "0.0767"),
        ("Evaluating pgvector-6 for filter", "0.0777"),
    ],
}


def term_static(t: dict) -> str:
    lab = t["term_labels"]
    d = DEMO1
    out = [
        f'<div><span class="pr">$</span> facetmark search <span class="q">"{esc(d["q"])}"</span></div>',
        f'<div class="dim">// {esc(lab[d["kind"]])}</div>',
        "<div>&nbsp;</div>",
    ]
    for i, (title, score) in enumerate(d["hits"], 1):
        tgt = " tgt" if i == d["target"] else ""
        out.append(
            f'<div class="hit{tgt}"><span class="n">{i}</span>'
            f'<span class="t">{esc(title)}</span><span class="sc">{score}</span></div>'
        )
    out.append("<div>&nbsp;</div>")
    out.append(
        f'<div class="dim">5 {esc(lab["hits"])} \u00b7 {d["ms"]} ms \u00b7 '
        f'{esc(lab["found"])} {d["target"]}</div>'
    )
    return "".join(out)


# --------------------------------------------------------------------------
# page shell
# --------------------------------------------------------------------------

THEME_BOOT = (
    "(function(){try{var t=localStorage.getItem('fm-theme');"
    "if(!t)t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';"
    "document.documentElement.setAttribute('data-theme',t);}catch(e){}})();"
)


def nav_html(t: dict, page: str) -> str:
    z = t["code"] == "zh"
    suffix = ".zh.html" if z else ".html"
    items = [
        ("home", "index" + suffix, page == "index", False),
        ("guide", "guide" + suffix, page == "guide", False),
        ("measured", "measured" + suffix, page == "measured", False),
        ("gh", REPO, False, True),
    ]
    out = ['<nav class="top">']
    for key, href, on, small in items:
        cls = []
        if on:
            cls.append("on")
        if small:
            cls.append("hide-sm")
        c = f' class="{" ".join(cls)}"' if cls else ""
        rel = ' rel="noopener"' if href.startswith("http") else ""
        out.append(f'<a href="{href}"{c}{rel}>{esc(t["nav"][key])}</a>')
    out.append(
        f'<a class="ctl" data-lang-switch href="#" title="{esc(t["other_title"])}" '
        f'hreflang="{t["other_code"]}">{esc(t["other_label"])}</a>'
    )
    aria = "\u5207\u6362\u6df1\u8272\u6a21\u5f0f" if z else "Toggle dark mode"
    out.append(
        '<button class="ctl" type="button" data-theme-toggle '
        f'aria-label="{esc(aria)}">\u263e</button>'
    )
    out.append("</nav>")
    return "".join(out)


def foot_html(t: dict) -> str:
    out = ['<footer class="site"><div class="wrap"><div class="foot">']
    for heading, links in t["foot"]["cols"]:
        out.append(f"<div><h4>{esc(heading)}</h4><ul>")
        for label, href in links:
            rel = ' rel="noopener"' if href.startswith("http") else ""
            out.append(f'<li><a href="{href}"{rel}>{esc(label)}</a></li>')
        out.append("</ul></div>")
    out.append('</div><div class="foot-bar">')
    out += [f"<span>{esc(x)}</span>" for x in t["foot"]["bar"]]
    out.append("</div></div></footer>")
    return "".join(out)


def shell(t: dict, page: str, body: str) -> str:
    title, desc = t["meta"][page]
    z = t["code"] == "zh"
    stem = {"index": "index", "guide": "guide", "measured": "measured"}[page]
    canon_en = f"{stem}.html"
    canon_zh = f"{stem}.zh.html"
    return (
        "<!doctype html>\n"
        f'<html lang="{t["html_lang"]}">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n"
        f'<meta name="description" content="{html.escape(desc, quote=True)}">\n'
        f'<meta name="color-scheme" content="light dark">\n'
        f'<meta property="og:title" content="{html.escape(title, quote=True)}">\n'
        f'<meta property="og:description" content="{html.escape(desc, quote=True)}">\n'
        '<meta property="og:type" content="website">\n'
        f'<link rel="alternate" hreflang="en" href="{canon_en}">\n'
        f'<link rel="alternate" hreflang="zh-CN" href="{canon_zh}">\n'
        f'<link rel="alternate" hreflang="x-default" href="{canon_en}">\n'
        '<link rel="icon" href="data:image/svg+xml,'
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
        "%3Crect width='32' height='32' rx='7' fill='%23ff9400'/%3E"
        "%3Cpath d='M0 0h32v32z' fill='%230279ee'/%3E%3C/svg%3E\">\n"
        '<link rel="stylesheet" href="style.css">\n'
        f"<script>{THEME_BOOT}</script>\n"
        "</head>\n<body>\n"
        f'<a class="skip" href="#main">{esc(t["skip"])}</a>\n'
        '<div class="progress" aria-hidden="true"></div>\n'
        '<header class="site"><div class="site-inner">'
        f'<a class="logo" href="index{".zh" if z else ""}.html">'
        '<span class="mark" aria-hidden="true"></span>'
        '<span class="word">facetmark</span></a>'
        f"{nav_html(t, page)}</div></header>\n"
        f"{body}\n"
        f"{foot_html(t)}\n"
        '<script src="site.js" defer></script>\n'
        "</body>\n</html>\n"
    )


# --------------------------------------------------------------------------
# index page
# --------------------------------------------------------------------------


def page_index(t: dict) -> str:
    i = t["index"]
    lab = t["term_labels"]
    o: list[str] = ['<main id="main">']

    # ---- hero -------------------------------------------------------------
    o.append('<section class="hero"><div class="hero-inner"><div>')
    o.append(f'<span class="kicker">{esc(i["kicker"])}</span>')
    o.append(f'<h1>{i["h1"]}</h1>')
    o.append(f'<p class="lede">{i["lede"]}</p>')
    o.append('<div class="cta">')
    for label, href, primary in i["cta"]:
        rel = ' rel="noopener"' if href.startswith("http") else ""
        o.append(
            f'<a class="btn{" primary" if primary else ""}" href="{href}"{rel}>{esc(label)}</a>'
        )
    o.append('</div><div class="chips">')
    for k, v in i["chips"]:
        o.append(f'<span class="chip">{esc(k)} <b>{esc(v)}</b></span>')
    o.append("</div></div><div>")
    o.append(
        '<div class="term"><div class="term-bar">'
        "<i></i><i></i><i></i>"
        f'<span>{esc(i["term_title"])}</span></div>'
        f'<div class="term-body" id="term-body"'
        f' data-t-hits="{html.escape(lab["hits"], quote=True)}"'
        f' data-t-found="{html.escape(lab["found"], quote=True)}"'
        f' data-t-missed="{html.escape(lab["missed"], quote=True)}"'
        f' data-t-content="{html.escape(lab["content"], quote=True)}"'
        f' data-t-vague="{html.escape(lab["vague"], quote=True)}"'
        f' data-t-episodic="{html.escape(lab["episodic"], quote=True)}">'
        f"{term_static(t)}</div>"
        f'<div class="term-note">{i["term_note"]}</div></div>'
    )
    o.append("</div></div></section>")

    # ---- three kinds of query --------------------------------------------
    o.append('<section class="band" id="queries"><div class="wrap">')
    o.append(f'<p class="seclabel">{esc(i["prob_label"])}</p>')
    o.append(f'<h2 class="reveal">{i["prob_h2"]}</h2>')
    o.append(f'<p class="lede read reveal">{i["prob_lede"]}</p>')
    o.append('<div class="grid g3 reveal">')
    for eyebrow, title, body, example, value, metric, cls in i["prob_cards"]:
        o.append(
            f'<article class="card"><div class="eyebrow">{esc(eyebrow)}</div>'
            f"<h3>{title}</h3><p>{body}</p>"
            f'<p class="ex">{example}</p>'
            f'<div class="stat"><div class="v{" " + cls if cls else ""}">{esc(value)}</div>'
            f'<div class="k">{esc(metric)}</div></div></article>'
        )
    o.append("</div>")
    o.append(f'<p class="tiny reveal">{i["prob_note"]}</p>')
    o.append("</div></section>")

    # ---- the four facets --------------------------------------------------
    o.append('<section class="band alt" id="facets"><div class="wrap">')
    o.append(f'<p class="seclabel">{esc(i["fac_label"])}</p>')
    o.append(f'<h2 class="reveal">{i["fac_h2"]}</h2>')
    o.append(f'<p class="lede read reveal">{i["fac_lede"]}</p>')
    o.append('<div class="reveal">')
    o.append(r_table(i["fac_head"], [list(r) for r in i["fac_rows"]]))
    o.append("</div>")
    o.append(f'<p class="tiny reveal">{i["fac_note"]}</p>')
    o.append("</div></section>")

    # ---- pipeline ---------------------------------------------------------
    o.append('<section class="band" id="pipeline"><div class="wrap">')
    o.append(f'<p class="seclabel">{esc(i["pipe_label"])}</p>')
    o.append(f'<h2 class="reveal">{i["pipe_h2"]}</h2>')
    o.append(f'<p class="lede read reveal">{i["pipe_lede"]}</p>')
    o.append('<div class="diagram reveal"><div class="dscroll">')
    o.append(diagram(t["code"]))
    o.append("</div>")
    o.append(diagram_stack(t["code"]))
    o.append("</div>")
    o.append('<div class="grid g3 reveal" style="margin-top:18px">')
    for title, body in i["pipe_after"]:
        o.append(f'<article class="card"><h3>{esc(title)}</h3><p>{body}</p></article>')
    o.append("</div></div></section>")

    # ---- screenshots ------------------------------------------------------
    o.append('<section class="band alt" id="extension"><div class="wrap">')
    o.append(f'<p class="seclabel">{esc(i["shot_label"])}</p>')
    o.append(f'<h2 class="reveal">{i["shot_h2"]}</h2>')
    o.append(f'<p class="lede read reveal">{i["shot_lede"]}</p>')
    o.append('<div class="grid g3 reveal">')
    for src, alt, cap in i["shots"]:
        o.append(
            f'<figure class="shot" style="margin:0">'
            f'<a href="{src}" target="_blank" rel="noopener">'
            f'<img src="{src}" alt="{html.escape(alt, quote=True)}" loading="lazy"></a>'
            f'<figcaption class="cap">{cap}</figcaption></figure>'
        )
    o.append("</div>")
    o.append(f'<p class="tiny reveal">{i["shot_note"]}</p>')
    o.append("</div></section>")

    # ---- measured ---------------------------------------------------------
    o.append('<section class="band" id="measured"><div class="wrap">')
    o.append(f'<p class="seclabel">{esc(i["meas_label"])}</p>')
    o.append(f'<h2 class="reveal">{i["meas_h2"]}</h2>')
    o.append(f'<p class="lede read reveal">{i["meas_lede"]}</p>')
    o.append('<div class="grid g3 reveal" style="margin-bottom:26px">')
    for v, k, cls in i["meas_stats"]:
        o.append(
            f'<div class="card"><div class="stat">'
            f'<div class="v{" " + cls if cls else ""}">{esc(v)}</div>'
            f'<div class="k">{esc(k)}</div></div></div>'
        )
    o.append("</div>")
    o.append('<div class="grid g2"><div>')
    o.append(f'<h3>{esc(i["meas_bars_title"])}</h3>')
    o.append('<div class="bars">')
    for label, val, pct, win in i["meas_bars"]:
        o.append(
            f'<div class="bar-row"><div class="lb">{label}</div>'
            f'<div class="bar-track"><div class="bar-fill{" win" if win else ""}" '
            f'style="--w:{pct}%"></div></div>'
            f'<div class="vv">{esc(val)}</div></div>'
        )
    o.append("</div></div><div class='reveal'>")
    o.append(i["meas_body"])
    suffix = ".zh.html" if t["code"] == "zh" else ".html"
    o.append(f'<p><a class="btn" href="measured{suffix}">{esc(i["meas_cta"])}</a></p>')
    o.append("</div></div></div></section>")

    # ---- quick start ------------------------------------------------------
    o.append('<section class="band alt" id="start"><div class="wrap">')
    o.append(f'<p class="seclabel">{esc(i["qs_label"])}</p>')
    o.append(f'<h2 class="reveal">{i["qs_h2"]}</h2>')
    o.append(f'<p class="lede read reveal">{i["qs_lede"]}</p>')
    o.append('<div class="grid g2 reveal"><div>')
    o.append(r_cb("shell", i["qs_code"]))
    o.append(f'<div class="callout"><p>{i["qs_offline"]}</p></div>')
    o.append("</div><div>")
    o.append('<ol class="steps">' + "".join(f"<li>{s}</li>" for s in i["qs_steps"]) + "</ol>")
    o.append("</div></div></div></section>")

    # ---- interfaces -------------------------------------------------------
    o.append('<section class="band" id="interfaces"><div class="wrap">')
    o.append(f'<p class="seclabel">{esc(i["if_label"])}</p>')
    o.append(f'<h2 class="reveal">{i["if_h2"]}</h2>')
    o.append('<div class="grid g3 reveal">')
    for _slug, title, body, href, cta in i["if_cards"]:
        o.append(
            f'<article class="card"><h3>{esc(title)}</h3><p>{body}</p>'
            f'<p><a href="{href}">{esc(cta)} \u2192</a></p></article>'
        )
    o.append("</div></div></section>")

    # ---- faq --------------------------------------------------------------
    o.append('<section class="band alt" id="faq"><div class="wrap">')
    o.append(f'<p class="seclabel">{esc(i["faq_label"])}</p>')
    o.append(f'<h2 class="reveal">{i["faq_h2"]}</h2>')
    o.append('<div class="read reveal">')
    for q, a in i["faq"]:
        o.append(
            f"<details class=\"faq\"><summary>{esc(q)}</summary>"
            f'<div class="a">{a}</div></details>'
        )
    o.append("</div></div></section>")

    # ---- boundaries -------------------------------------------------------
    o.append('<section class="band" id="promises"><div class="wrap">')
    o.append(f'<p class="seclabel">{esc(i["bnd_label"])}</p>')
    o.append(f'<h2 class="reveal">{i["bnd_h2"]}</h2>')
    o.append('<div class="grid g3 reveal">')
    for title, body in i["bnd"]:
        o.append(f'<article class="card"><h3>{esc(title)}</h3><p>{body}</p></article>')
    o.append("</div></div></section>")

    # ---- end --------------------------------------------------------------
    o.append('<section class="band alt"><div class="wrap center">')
    o.append(f'<h2 class="reveal">{i["end_h2"]}</h2>')
    o.append(
        f'<p class="lede reveal" style="margin-left:auto;margin-right:auto;max-width:640px">'
        f'{i["end_p"]}</p>'
    )
    o.append('<div class="cta reveal" style="justify-content:center">')
    for label, href, primary in i["end_cta"]:
        rel = ' rel="noopener"' if href.startswith("http") else ""
        o.append(
            f'<a class="btn{" primary" if primary else ""}" href="{href}"{rel}>{esc(label)}</a>'
        )
    o.append("</div></div></section>")

    o.append("</main>")
    return "".join(o)


# --------------------------------------------------------------------------
# guide / measured
# --------------------------------------------------------------------------


def page_doc(t: dict, key: str) -> str:
    d = t[key]
    o = ['<main id="main">']
    o.append(
        f'<div class="pagehead"><div class="wrap"><h1>{esc(d["h1"])}</h1>'
        f'<p class="lede">{d["lede"]}</p></div></div>'
    )
    o.append('<div class="wrap"><div class="doc">')

    o.append(f'<aside class="toc"><div class="h">{esc(d["toc_title"])}</div><ol>')
    for sid, title, _ in d["sections"]:
        o.append(f'<li><a href="#{sid}">{esc(title)}</a></li>')
    o.append("</ol></aside>")

    o.append("<article>")
    for n, (sid, title, blocks) in enumerate(d["sections"], 1):
        o.append(
            f'<section id="{sid}"><h2><span class="n">{n:02d}</span>'
            f"<span>{esc(title)}</span></h2>{r_blocks(blocks)}</section>"
        )
    o.append("</article></div></div></main>")
    return "".join(o)


# --------------------------------------------------------------------------

COPY = EN["copy"]  # rebound per language in build()


def build() -> None:
    global COPY
    written = []
    for t in (EN, ZH):
        COPY = t["copy"]
        z = t["code"] == "zh"
        pages = {
            f'index{".zh" if z else ""}.html': shell(t, "index", page_index(t)),
            f'guide{".zh" if z else ""}.html': shell(t, "guide", page_doc(t, "guide")),
            f'measured{".zh" if z else ""}.html': shell(
                t, "measured", page_doc(t, "measured")
            ),
        }
        for name, doc in pages.items():
            path = os.path.join(HERE, name)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(doc)
            written.append((name, len(doc)))

    for name, size in written:
        print(f"  {name:<20} {size / 1024:7.1f} KB")


if __name__ == "__main__":
    build()
