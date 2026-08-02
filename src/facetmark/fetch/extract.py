"""Three-tier body extraction.

Tier 1  trafilatura      Best boilerplate removal; wrong or empty on some
                         layouts, and returns nothing at all for pages whose
                         content is one short block.
Tier 2  readability-lxml The Arc90 heuristic. Coarser than trafilatura -- keeps
                         more navigation -- but succeeds on plain or unusual
                         markup where trafilatura declines to guess.
Tier 3  title + meta     Not really extraction. It exists because *something*
                         must reach the index: a bookmark with no body still has
                         to be findable by its title, and returning empty here
                         would silently drop it out of the content facet.

Each tier records which one produced the text, so the evaluation harness can
tell "the retriever failed" apart from "there was nothing to retrieve".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Below this many characters, a tier is treated as having failed and the next
#: one is tried. Cookie banners and "enable JavaScript" pages land here.
MIN_USEFUL_CHARS = 200

_WS = re.compile(r"[ \t\u00a0]+")
_BLANKS = re.compile(r"\n{3,}")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_META_DESC_RE = re.compile(
    r"""<meta\s[^>]*?(?:name|property)\s*=\s*["'](?:description|og:description)["'][^>]*?"""
    r"""content\s*=\s*["'](.*?)["']""",
    re.I | re.S,
)
_META_DESC_REV_RE = re.compile(
    r"""<meta\s[^>]*?content\s*=\s*["'](.*?)["'][^>]*?"""
    r"""(?:name|property)\s*=\s*["'](?:description|og:description)["']""",
    re.I | re.S,
)
_TAG = re.compile(r"<[^>]+>")

#: Phrases that mean "this is not the page, this is a wall". A 200 response
#: containing one of these is not a successful fetch.
WALL_MARKERS: tuple[str, ...] = (
    "enable javascript",
    "请开启 javascript",
    "javascript is required",
    "verify you are human",
    "checking your browser",
    "just a moment",
    "cf-browser-verification",
    "access denied",
    "attention required",
    "unusual traffic",
    "人机验证",
    "验证码",
    "滑动验证",
    "login to continue",
    "请登录",
    "登录后查看",
    "sign in to continue",
)


@dataclass(slots=True)
class Extraction:
    text: str
    title: str
    #: ``trafilatura`` | ``readability`` | ``metadata`` | ``none``
    extractor: str
    looks_like_wall: bool = False

    @property
    def ok(self) -> bool:
        return len(self.text) >= MIN_USEFUL_CHARS and not self.looks_like_wall


def _clean(text: str) -> str:
    text = _WS.sub(" ", text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [ln.strip() for ln in text.split("\n")]
    return _BLANKS.sub("\n\n", "\n".join(lines)).strip()


def _unescape(s: str) -> str:
    import html

    return html.unescape(_TAG.sub(" ", s)).strip()


def html_title(html: str) -> str:
    m = _TITLE_RE.search(html)
    return _WS.sub(" ", _unescape(m.group(1))) if m else ""


def meta_description(html: str) -> str:
    m = _META_DESC_RE.search(html) or _META_DESC_REV_RE.search(html)
    return _unescape(m.group(1)) if m else ""


def looks_like_wall(html: str, body: str) -> bool:
    """A 200 that is really a bot check, a login gate or a JS shell.

    Checked against the *raw* html as well as the extracted body: the marker is
    often in a ``<noscript>`` or a script string that extraction throws away.
    """
    hay = f"{html[:20000]}\n{body[:4000]}".lower()
    if any(m in hay for m in WALL_MARKERS):
        return True
    # A large HTML document that yields almost no text is a client-rendered
    # shell. Small documents are just small.
    return len(html) > 30_000 and len(body) < 120


def _try_trafilatura(html: str, url: str | None) -> str:
    try:
        import trafilatura
    except ImportError:  # pragma: no cover - declared dependency
        return ""
    try:
        got = trafilatura.extract(
            html, url=url, include_comments=False, include_tables=True,
            favor_recall=True, no_fallback=False,
        )
    except Exception:
        return ""
    return _clean(got or "")


def _try_readability(html: str) -> str:
    try:
        from readability import Document
    except ImportError:
        return ""
    try:
        summary = Document(html).summary(html_partial=True)
    except Exception:
        return ""
    return _clean(_unescape(summary))


def extract(html: str, *, url: str | None = None, title_hint: str = "") -> Extraction:
    """Run the tiers in order, stopping at the first that yields usable text."""
    if not html or not html.strip():
        return Extraction("", title_hint, "none")

    title = html_title(html) or title_hint

    body = _try_trafilatura(html, url)
    if len(body) >= MIN_USEFUL_CHARS:
        return Extraction(body, title, "trafilatura", looks_like_wall(html, body))

    alt = _try_readability(html)
    if len(alt) >= MIN_USEFUL_CHARS:
        return Extraction(alt, title, "readability", looks_like_wall(html, alt))

    # Neither tier cleared the bar. Keep the longer of the two anyway if it beat
    # metadata, so a genuinely short page is not thrown away.
    best = max((body, alt), key=len)
    desc = meta_description(html)
    meta_text = _clean("\n".join(x for x in (title, desc) if x))
    if len(best) > len(meta_text):
        return Extraction(best, title, "trafilatura" if best is body else "readability",
                          looks_like_wall(html, best))
    if meta_text:
        return Extraction(meta_text, title, "metadata", looks_like_wall(html, meta_text))
    return Extraction("", title, "none", looks_like_wall(html, ""))
