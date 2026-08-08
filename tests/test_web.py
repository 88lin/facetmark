"""Tests for the web UI served at ``/app``.

Three kinds of assertion live here, and they exist for three different reasons.

*Routing and auth.* ``/app``, ``/app/static/*`` and ``/app/boot`` are the only
unauthenticated routes that were added, so each one is pinned: what it serves,
that it needs no token, and -- for ``/app/boot``, the only route in the service
that can hand out the pairing token -- exactly when it refuses to.

*Contract.* The page reads response fields by name off `await res.json()`,
which is the same unchecked cast the extension makes and the same failure mode:
a renamed field arrives as ``undefined`` and renders as an empty string. The
extension has its own contract test for this. The web UI now has one too.
The page is a set of ES modules rather than one file, so the scans below are
scoped to the module that owns each response: ``search.js`` holds the search
objects, ``library.js`` and ``derive.js`` hold the stats object, and the paths
and translation keys are collected across every module at once.

*Strings.* A missing translation is invisible until a reader hits that exact
screen in that exact language, so the key sets are compared here instead.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from facetmark.api import PUBLIC_PATHS, create_app
from facetmark.config import Settings
from facetmark.edges import WEIGHTS
from facetmark.health.verdicts import Status
from facetmark.web import INDEX_HTML, STATIC_DIR
from tests.palette import (
    Palette,
    backdrop_of,
    declarations,
    first_colour,
    painted,
    ratio,
    rules,
    value_of,
)

REPO = Path(__file__).resolve().parents[1]

#: The palette file cascades three times for palette A: the colourway itself,
#: the semantic aliases every colourway shares, then the AA corrections that
#: only A carries. Resolving a token means replaying all three in order.
PALETTE_BLOCKS = (
    r':root,\s*\n\[data-palette="A"\]',
    r':root,\s*\n\[data-palette\]',
    r':root:not\(\[data-palette\]\),\s*\n\[data-palette="A"\]',
)
DARK = r'html\[data-theme="dark"\]'


def _palette_tokens() -> dict[str, str]:
    css = (STATIC_DIR / "palettes.css").read_text(encoding="utf-8")
    tokens: dict[str, str] = {}
    for block in PALETTE_BLOCKS:
        tokens.update(declarations(css, block))
    return tokens


def _resolved(theme: str) -> Palette:
    """Every custom property in force, for one theme."""
    app = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
    tokens = {**_palette_tokens(), **declarations(app, r":root")}
    if theme == "dark":
        tokens.update(declarations(app, DARK))
    return Palette(tokens)


@pytest.fixture()
def st(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path / "fm", use_mock_provider=True)


@pytest.fixture()
def client(st):
    app = create_app(st)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def local(st):
    """A client whose TCP peer is loopback, which the default one is not.

    ``TestClient``'s default peer is the literal string ``testclient``, so a
    ``/app/boot`` test written against it passes for the wrong reason: it is
    refused because the peer is not loopback, never reaching the ``Host``
    check that is the point of the route.
    """
    app = create_app(st)
    with TestClient(app, client=("127.0.0.1", 51234)) as c:
        yield c


def js(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


def modules() -> list[str]:
    """Every ES module the page ships, discovered rather than listed.

    A module added to the directory and never imported is caught by the import
    graph test; a module listed here by hand and then renamed would silently
    stop being scanned, which is the failure this avoids.
    """
    return sorted(p.name for p in STATIC_DIR.glob("*.js"))


def all_js() -> str:
    return "\n".join(js(name) for name in modules())


def strings() -> dict[str, dict[str, str]]:
    return json.loads((STATIC_DIR / "strings.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------


class TestTheRoutes:
    def test_the_page_is_served_without_a_token(self, client):
        """A page that needs a token to load cannot ask the reader for one."""
        r = client.get("/app")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")
        assert "<title>" in r.text

    def test_the_assets_are_served_without_a_token(self, client):
        for name in ("app.css", "app.js", "strings.json", "paging.js", "format.js", "i18n.js"):
            r = client.get(f"/app/static/{name}")
            assert r.status_code == 200, name
            assert r.content, name

    def test_the_static_mount_does_not_escape_its_directory(self, client):
        assert client.get("/app/static/../api.py").status_code in (307, 404)

    def test_the_page_and_boot_are_the_only_public_routes_added(self):
        assert {"/app", "/app/boot"} <= PUBLIC_PATHS

    def test_every_other_route_still_rejects_an_unauthenticated_caller(self, client):
        """The enumerating test from ``test_api`` re-run against this app.

        Adding public paths is exactly how that test gets quietly weakened, so
        the count is asserted here as well: a route that becomes public by
        accident makes ``checked`` fall.
        """
        checked = 0
        for route in client.app.routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set()) or set()
            if path in PUBLIC_PATHS or "{" in path:
                continue
            for method in sorted(methods & {"GET", "POST"}):
                assert client.request(method, path, json={}).status_code == 401, f"{method} {path}"
                checked += 1
        assert checked >= 8

    def test_a_missing_install_says_so_instead_of_serving_a_blank_page(self, client, monkeypatch):
        """``.gitignore`` has ``*.html``; a wheel built without the negation
        would have every asset except the page. 503 names the cause."""
        monkeypatch.setattr("facetmark.api.INDEX_HTML", Path("/nonexistent/index.html"))
        r = client.get("/app")
        assert r.status_code == 503
        assert "web assets" in r.json()["detail"]


class TestPairing:
    def test_a_loopback_caller_is_handed_the_token(self, local):
        body = local.get("/app/boot", headers={"Host": "127.0.0.1:8787"}).json()
        assert body["paired"] is True
        assert body["reason"] == ""
        assert body["token"] == local.app.state.fm.token
        assert body["version"]

    @pytest.mark.parametrize("host", ["127.0.0.1:8787", "localhost:8787", "[::1]:8787", "localhost"])
    def test_the_loopback_names_a_browser_actually_uses_all_work(self, local, host):
        assert local.get("/app/boot", headers={"Host": host}).json()["paired"] is True

    @pytest.mark.parametrize("host", ["evil.example", "fm.local", "192.168.1.20:8787"])
    def test_a_rebound_dns_name_gets_no_token(self, local, host):
        """The regression this route exists for.

        Under DNS rebinding the peer *is* loopback -- it is the victim's own
        browser -- so a peer check alone would hand the token to a page on the
        open web. The ``Host`` header is the part that carries the attacker's
        domain, and it is the part that has to be checked.
        """
        body = local.get("/app/boot", headers={"Host": host}).json()
        assert body["paired"] is False
        assert body["token"] == ""
        assert body["reason"] == "host_not_loopback"

    def test_a_non_loopback_peer_gets_no_token(self, client):
        body = client.get("/app/boot", headers={"Host": "127.0.0.1:8787"}).json()
        assert body["paired"] is False
        assert body["token"] == ""
        assert body["reason"] == "peer_not_loopback"

    def test_the_answer_is_never_cached(self, local):
        """A cached ``paired: true`` would survive the condition that produced
        it, and a cached token would sit in the browser's disk cache."""
        r = local.get("/app/boot", headers={"Host": "127.0.0.1:8787"})
        assert r.headers["cache-control"] == "no-store"

    def test_the_page_itself_carries_no_token(self, client):
        """``index.html`` is served as a static file with no substitution.

        Templating the token into the markup is the obvious shortcut and it
        brings a ``</script>`` breakout with it. The token is fetched instead.
        """
        assert client.app.state.fm.token not in client.get("/app").text


# ---------------------------------------------------------------------------
# contract
# ---------------------------------------------------------------------------


def _decomment(src: str) -> str:
    """Drop comments before scanning for paths and keys.

    The modules name the endpoints they deliberately do not call, and a scan
    that cannot tell prose from code reads those mentions as calls.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", src)


def _js_paths(src: str) -> set[str]:
    """Every request path the client builds, query strings stripped."""
    src = _decomment(src)
    out = set()
    for lit in re.findall(r"[\"`](/[^\"`${]*)[\"`]", src):
        out.add(lit.split("?", 1)[0])
    return {p for p in out if not p.startswith("/app/static")}


def _js_reads(src: str, obj: str) -> set[str]:
    """Field names read off ``obj`` by name, e.g. ``full.hits``.

    The lookbehind is load-bearing: ``\\b`` also matches inside ``ui.more``, the
    DOM node, and would report ``appendChild`` as a field the server owes us.
    """
    return set(re.findall(rf"(?<![.\w$]){obj}(?:\?)?\.(\w+)", src))


class TestTheWebContract:
    """`await res.json()` is an unchecked cast in JavaScript too.

    The extension has the same boundary and the same test; this is the second
    client of the same API, so a renamed field now fails in two places rather
    than rendering as an empty string in one.
    """

    def test_every_path_the_page_calls_is_a_real_route(self, client):
        declared = _js_paths(all_js())
        routes = {r.path for r in client.app.routes}
        assert declared, "parsed no paths out of the page's modules"
        assert declared <= routes, f"the page calls routes that do not exist: {declared - routes}"

    def test_the_endpoints_the_page_deliberately_leaves_alone_stay_alone(self, client):
        """``/queue/next`` and ``/queue/complete`` are a worker lease protocol.

        A browser that leases an item and then navigates away never completes
        it, and the item sits leased until the lease expires. The page shows
        ``/queue/stats`` and takes no work off the queue. This is a decision,
        not an omission, so it is pinned: wiring either one should require
        deleting this test and saying why.
        """
        routes = {r.path for r in client.app.routes}
        for path in ("/queue/next", "/queue/complete"):
            assert path in routes, f"{path} was removed; this test is stale"
            assert path not in _js_paths(all_js()), f"the page now calls {path}"

    def test_the_response_fields_the_page_reads_are_fields_the_server_sends(self, client):
        st = client.app.state.fm.settings
        conn = client.app.state.fm.conn
        from facetmark import service
        from facetmark.text import sync_fts

        rec = service.save_bookmark(conn, "https://a.example/rust", title="Rust ownership",
                                    settings=st)
        sync_fts(conn, rec["bookmark_id"], title="Rust ownership", body="borrow checker rust")
        conn.commit()

        auth = {"Authorization": f"Bearer {client.app.state.fm.token}"}
        sent = set(client.post("/search", json={"q": "rust"}, headers=auth).json())
        # `rows`/`cursor` names are local; these are the two response objects.
        src = js("search.js")
        read = _js_reads(src, "full") | _js_reads(src, "more") | _js_reads(src, "quick")
        assert read, "parsed no field reads out of search.js"
        assert read <= sent, f"search.js reads fields the server never sends: {sorted(read - sent)}"

    def test_the_hit_fields_the_page_reads_are_fields_the_server_sends(self, client):
        st = client.app.state.fm.settings
        conn = client.app.state.fm.conn
        from facetmark import service
        from facetmark.text import sync_fts

        rec = service.save_bookmark(conn, "https://a.example/rust", title="Rust ownership",
                                    settings=st)
        sync_fts(conn, rec["bookmark_id"], title="Rust ownership", body="borrow checker rust")
        conn.commit()

        auth = {"Authorization": f"Bearer {client.app.state.fm.token}"}
        hit = client.post("/search", json={"q": "rust"}, headers=auth).json()["hits"][0]
        read = _js_reads(js("search.js"), "h")
        assert read, "parsed no hit-field reads out of search.js"
        # `via`/`via_kind` are only present on expansion rows, by design.
        assert read - {"via", "via_kind"} <= set(hit), (
            f"search.js reads hit fields the server never sends: {sorted(read - set(hit))}"
        )

    def test_the_stats_shape_the_page_assumes_is_the_shape_the_server_sends(self, client):
        auth = {"Authorization": f"Bearer {client.app.state.fm.token}"}
        stats = client.get("/stats", headers=auth).json()
        # `derive.js` does the arithmetic, `library.js` draws it, `search.js`
        # reads it to decide which set-up panel a first-run reader needs.
        read = set()
        for name in ("derive.js", "library.js", "search.js"):
            read |= _js_reads(js(name), "s")
        assert read, "parsed no stats-field reads out of the page's modules"
        assert read <= set(stats), f"unknown stats keys: {sorted(read - set(stats))}"

    def test_vectors_is_a_pair_and_the_page_knows_it(self, client):
        """``db.count_vectors()`` returns a tuple, so JSON makes it an array.

        Reading ``.content`` off it would be ``undefined`` and render blank.
        """
        auth = {"Authorization": f"Bearer {client.app.state.fm.token}"}
        vectors = client.get("/stats", headers=auth).json()["vectors"]
        assert isinstance(vectors, (list, dict))
        # Absent the vector tables the server sends `{}`, not a pair, so the
        # guard has to be a type check rather than a truthiness check.
        assert "Array.isArray(s.vectors)" in js("derive.js")
        assert "Array.isArray(s?.vectors)" in js("search.js")


# ---------------------------------------------------------------------------
# strings
# ---------------------------------------------------------------------------


DYNAMIC = ("edge.", "health.", "queue.", "unit.")
"""Key families the page builds at runtime, e.g. ``edge.${kind}``.

A literal scan cannot see these, so they are exempted here and checked against
the server-side enumerations instead -- which is stricter than a scan, not
looser: a scan proves someone typed the key, the vocabulary tests prove every
value the server can emit has a name. ``unit.`` is the one family whose
enumeration is client-side, in ``uptimeParts``; it gets the same treatment.
"""


def _asked(key: str, asked: set[str]) -> bool:
    """Is ``key`` reachable at runtime?"""
    if key in asked or key.startswith(DYNAMIC):
        return True
    if not key.endswith(".why"):
        return False
    # `hitRow` derives a chip's tooltip id as `${key}.why` from the key it just
    # rendered, so a `.why` string is asked for exactly when its chip is.
    base = key[: -len(".why")]
    return base in asked or base.startswith(DYNAMIC)


def _keys_asked_for() -> set[str]:
    """Every translation key the page asks for at runtime.

    Dotted string literals rather than ``t("...")`` calls: the naive call-site
    regex also matches ``get("q")`` and misses ``tOr`` and the template forms.
    Dynamic families such as ``edge.${kind}`` cannot be seen this way at all,
    which is what the vocabulary tests below are for.
    """
    keys: set[str] = set()
    for name in modules():
        keys |= set(
            re.findall(r"\"([a-z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)+)\"", _decomment(js(name)))
        )
    html = INDEX_HTML.read_text(encoding="utf-8")
    keys |= set(re.findall(r'data-i18n="([^"]+)"', html))
    for group in re.findall(r'data-i18n-attr="([^"]+)"', html):
        for pair in group.split(","):
            keys.add(pair.split(":")[1].strip())
    # `.js` module specifiers look exactly like dotted keys.
    return {k for k in keys if not k.endswith((".js", ".json", ".css", ".html"))}


class TestTheStrings:
    def test_the_two_languages_have_the_same_keys(self):
        s = strings()
        assert set(s) == {"en", "zh"}
        missing = set(s["en"]) - set(s["zh"])
        extra = set(s["zh"]) - set(s["en"])
        assert not missing, f"never translated: {sorted(missing)}"
        assert not extra, f"translated but not in English: {sorted(extra)}"

    def test_every_key_the_page_asks_for_exists_in_both(self):
        s = strings()
        for lang in ("en", "zh"):
            missing = sorted(_keys_asked_for() - set(s[lang]))
            assert not missing, f"{lang} is missing {missing}"

    def test_no_string_is_declared_and_never_used(self):
        """Dynamic families are listed by prefix rather than exempted wholesale.

        An unused string is not a bug, but it is usually a rename that only got
        halfway, and the ones left over here are the ones built at runtime.
        """
        asked = _keys_asked_for()
        unused = sorted(k for k in strings()["en"] if not _asked(k, asked))
        assert not unused, f"declared but never asked for: {unused}"

    def test_every_tooltip_explains_a_string_the_page_can_show(self):
        """The `.why` family is the hover text behind each result-row chip.

        It is built by concatenation, so a literal scan cannot see it and the
        test above has to exempt it. This is the compensating check: an orphan
        tooltip -- one whose chip was renamed or removed -- is text no reader
        can ever reach, and it would otherwise sit in the file forever.
        """
        assert "`${key}.why`" in js("search.js"), "the tooltip lookup moved; re-derive this rule"
        en = strings()["en"]
        for key in en:
            if key.endswith(".why"):
                assert key[: -len(".why")] in en, f"{key} explains a string that does not exist"

    def test_every_edge_kind_the_ranker_can_report_has_a_name(self):
        """``via_kind`` is rendered as ``edge.${kind}``.

        A kind added to ``WEIGHTS`` without a string here shows the reader the
        raw identifier -- or, before ``tOr``, the literal text ``edge.foo``.
        """
        s = strings()
        for lang in ("en", "zh"):
            for kind in WEIGHTS:
                assert f"edge.{kind}" in s[lang], f"{lang} has no name for edge kind {kind}"

    def test_every_link_health_verdict_has_a_name(self):
        s = strings()
        verdicts = {v.value for v in Status} | {"unchecked"}
        for lang in ("en", "zh"):
            for v in verdicts:
                assert f"health.{v}" in s[lang], f"{lang} has no name for verdict {v}"

    def test_every_uptime_unit_has_a_name(self):
        """``uptimeParts`` emits ``{n, unit}`` and the unit is rendered as
        ``unit.${p.unit}``. The enumeration lives in ``format.js``."""
        s = strings()
        units = set(re.findall(r'unit:\s*"(\w+)"', js("format.js")))
        assert units == {"d", "h", "m", "s"}, f"uptimeParts emits {sorted(units)}"
        for lang in ("en", "zh"):
            for u in units:
                assert f"unit.{u}" in s[lang], f"{lang} has no name for unit {u}"

    def test_every_queue_state_has_a_name(self):
        s = strings()
        for lang in ("en", "zh"):
            for state in ("pending", "leased", "done", "failed"):
                assert f"queue.{state}" in s[lang], f"{lang} has no name for queue state {state}"

    def test_the_placeholders_survive_translation(self):
        """``{n}`` interpolated by name: a translator dropping one leaves a
        sentence with a hole, and inventing one leaves a literal ``{count}``."""
        s = strings()
        for key, en in s["en"].items():
            assert set(re.findall(r"\{(\w+)\}", s["zh"][key])) == set(
                re.findall(r"\{(\w+)\}", en)
            ), f"{key}: placeholders differ between languages"


# ---------------------------------------------------------------------------
# packaging and brand
# ---------------------------------------------------------------------------


class TestPackaging:
    def test_the_assets_are_reachable_as_package_data(self):
        """``importlib.resources``, not a path relative to the repo: this is
        what an installed wheel looks like from the inside."""
        from importlib.resources import files

        root = files("facetmark.web")
        assert (root / "index.html").is_file()
        assert (root / "static" / "app.css").is_file()
        assert (root / "static" / "strings.json").is_file()

    def test_git_does_not_ignore_the_page(self):
        """``.gitignore`` line 23 is ``*.html``, and hatchling honours it when
        selecting wheel contents. Without the negation, ``pip install
        facetmark`` serves a 404 at ``/app`` and nothing here would notice."""
        text = (REPO / ".gitignore").read_text(encoding="utf-8")
        assert "!src/facetmark/web/*.html" in text

    def test_the_page_asks_for_assets_by_absolute_path(self):
        """The page is served at ``/app`` with no trailing slash, so a relative
        ``static/app.css`` resolves to ``/static/app.css`` and 404s."""
        html = INDEX_HTML.read_text(encoding="utf-8")
        for ref in re.findall(r'(?:href|src)="([^"]+)"', html):
            if ref.startswith(("http", "data:", "#")):
                continue
            assert ref.startswith("/app/static/"), f"{ref} will not resolve from /app"


class TestTheBrand:
    """One palette file, vendored twice, edited never.

    The colours are not facetmark's to choose. They come from the project
    owner's design system as a whole file, copied in twice because the page and
    the documentation site are published by different pipelines. What is worth
    testing is not the values -- upstream owns those -- but the seam: that the
    two copies have not drifted, that the page still points at the one palette
    whose contrast has been checked, and that `app.css` has not started
    inventing colours of its own alongside the ones it was given.
    """

    def test_the_two_copies_of_the_palette_are_the_same_file(self):
        """A copy is only safe while it is a copy."""
        page = (STATIC_DIR / "palettes.css").read_bytes()
        site = (REPO / "docs" / "landing" / "palettes.css").read_bytes()
        assert page == site, "the two vendored palettes have drifted apart"

    def test_the_palette_says_where_it_came_from(self):
        """Vendored code without provenance is code nobody dares update."""
        head = (STATIC_DIR / "palettes.css").read_text(encoding="utf-8")[:1400]
        assert "github.com/88lin/mydesign-system" in head
        assert re.search(r"commit:\s*[0-9a-f]{7,40}", head), "no upstream commit pinned"

    def test_the_page_pins_the_palette_whose_contrast_was_checked(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        assert re.search(r"<html[^>]*data-palette=\"A\"", html), "no palette pinned on <html>"

    def test_the_palette_is_linked_before_the_stylesheet_that_consumes_it(self):
        """`app.css` reads tokens the palette declares. Load it first and the
        page renders one paint with every custom property unresolved."""
        html = INDEX_HTML.read_text(encoding="utf-8")
        sheets = re.findall(r'<link rel="stylesheet" href="([^"]+)"', html)
        assert "/app/static/palettes.css" in sheets, "the palette is not linked"
        assert sheets.index("/app/static/palettes.css") < sheets.index("/app/static/app.css")

    def test_the_stylesheet_names_no_colour_the_palette_did_not(self):
        """Everything above the dark block must be a token reference.

        The design system's brand rules forbid hardcoded colour values in
        shared components, and a stray hex is how a palette swap silently
        stops working. Black shadows and the modal scrim are exempt: they are
        the design system's own literals, and they are not brand colour.
        """
        css, night = self._split()
        assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", css), "hardcoded hex above the dark block"
        for literal in re.findall(r"rgba?\(\s*\d[^)]*\)", css):
            channels = [c.strip() for c in literal.split("(")[1].rstrip(")").split(",")]
            assert set(channels[:3]) == {"0"}, f"{literal} is a colour, not a shadow"
        assert night, "the dark block vanished; this test is now measuring nothing"

    def test_the_night_block_only_darkens_what_the_palette_already_named(self):
        """The dark theme is facetmark's own extension -- upstream ships light
        palettes only -- so it is held to an allowlist. Every token it sets
        must already be named by the palette or by this stylesheet's own
        `:root`, or the page has grown a second palette in a place nobody
        thinks to look."""
        app = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        known = set(_palette_tokens()) | set(declarations(app, r":root"))
        night = declarations(app, DARK)
        invented = sorted(set(night) - known)
        assert not invented, f"the dark block invents tokens the palette never had: {invented}"

    def test_the_night_block_covers_every_colour_the_page_reads(self):
        """A token the light theme paints and the dark theme forgets renders
        as its light value on a dark surface. Both themes resolve here, so the
        omission would surface as a contrast failure rather than a crash --
        this names it directly instead."""
        night = declarations((STATIC_DIR / "app.css").read_text(encoding="utf-8"), DARK)
        assert "--link" in night, "--link must be re-pointed for dark, the deep brand step is unreadable"
        assert len(night) == 24, f"the dark block is now {len(night)} tokens; review each addition"

    @staticmethod
    def _split() -> tuple[str, str]:
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        cut = css.index('html[data-theme="dark"]')
        return css[:cut], css[cut:]


class TestTheAppScene:
    """The four things the design system forbids on a functional page.

    `references/scene-app.md` ends with a short list of taboos, and three of
    them are the kind of rule that gets broken by a well-meaning single commit
    six months from now. They are cheap to check, so they are checked. The
    fourth -- no long decorative prose -- is a judgement call and is left to
    review.
    """

    def test_no_dark_panel_in_a_functional_area(self):
        """`深色只用于夜间模式场景`. A dark slab in the middle of a light page
        reads as a terminal, and the one place it crept in was a shell command
        inside a warning notice."""
        light, _ = TestTheBrand._split()
        offenders = [sel for sel, body in rules(light) if "--dark-panel" in body]
        assert not offenders, f"dark panel painted in: {offenders}"

    def test_no_heading_is_larger_than_the_scene_allows(self):
        """`App内标题控制在1.2rem以内`. The dashboard numerals are not headings
        and are not covered; they are the whole point of that card."""
        light, _ = TestTheBrand._split()
        numerals = re.compile(r"\.num\b")
        for selector, body in rules(light):
            size = value_of(body, "font-size")
            if not size or numerals.search(selector):
                continue
            for rem in re.findall(r"([\d.]+)rem", size):
                assert float(rem) <= 1.2, f"{selector} sets {size}, over the 1.2rem cap"

    def test_the_page_does_not_wait_for_an_animation_to_show_its_data(self):
        """`不要用Scroll Reveal（App页面要即时加载）`. The landing site reveals
        on scroll; the app must not, or a reader who lands mid-page sees empty
        cards until they move the mouse."""
        assert "IntersectionObserver" not in all_js(), "the app page reveals on scroll"


class TestTheContrast:
    """Every piece of text on the page, measured against what is behind it.

    The earlier version of this class pinned two tokens by hand. That scaled
    badly: a token is only legible in context, and the context is the rule that
    uses it. So this reads `app.css` instead -- every rule that sets a colour,
    resolved through the palette, composited over whatever is actually behind
    it -- and grades all of them, in both themes.

    "Behind it" is the part worth spelling out. A rule with its own background
    is measured against that background over each page surface, because a tint
    like `rgba(var(--brand-rgb), .1)` is transparent and the surface shows
    through. A rule without one is measured against its nearest painted
    ancestor: `.hit .title` is never seen outside `.hit`, and grading it
    against the page background would ask a question the interface never poses.
    Only when nothing paints an ancestor does it fall back to the three
    surfaces the page actually uses.
    """

    #: The backgrounds the page paints large enough to sit text on. Checked by
    #: `test_these_are_the_only_surfaces`, so the list cannot quietly go stale.
    SURFACES = ("--cream", "--cream-dark", "--card-bg")

    #: WCAG 1.4.3 scores 18.66px bold and up at 3:1. These are the dashboard
    #: numerals, `clamp(1.7rem, 4vw, 2.4rem)` at weight 700.
    LARGE = {".num b", ".num.pop b", ".num.ok b", ".num.warn b"}

    #: WCAG 1.4.3 exempts disabled controls.
    EXEMPT = {".btn:disabled"}

    def test_these_are_the_only_surfaces_the_page_sits_text_on(self):
        """`SURFACES` is an input to the sweep below, so it is derived rather
        than trusted. Anything else painting a full-width background would
        widen the sweep, and this is where that shows up."""
        surfaces = painted((STATIC_DIR / "app.css").read_text(encoding="utf-8"))
        wide = {"body", ".top", ".sheet", ".card", ".hit", ".num"}
        used = {v for k, v in surfaces.items() if k in wide}
        assert used <= {f"var({s})" for s in self.SURFACES}, f"unlisted page surface: {used}"

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_every_line_of_text_clears_aa_against_what_is_behind_it(self, theme):
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        pal = _resolved(theme)
        surfaces = painted(css)
        checked, failures = 0, []
        for selector, body in rules(css):
            ink = first_colour(value_of(body, "color") or "")
            if not ink:
                continue
            own = first_colour(value_of(body, "background-color") or value_of(body, "background") or "")
            for one in (s.strip() for s in selector.split(",")):
                if one in self.EXEMPT:
                    continue
                checked += 1
                stack = [layer for layer in (own, backdrop_of(one, surfaces)) if layer]
                floor = 3.0 if one in self.LARGE else 4.5
                worst, where = None, None
                for surface in self.SURFACES:
                    behind = pal.rgb(f"var({surface})")
                    for layer in reversed(stack):
                        behind = pal.rgb(layer, behind)
                    got = ratio(pal.rgb(ink, behind), behind)
                    if worst is None or got < worst:
                        worst, where = got, " over ".join([*stack, surface])
                    if stack and not pal.has_alpha(stack[0]):
                        break  # opaque: the page surface cannot show through
                if worst < floor:
                    failures.append(f"{one}: {ink} on {where} is {worst:.2f}:1, below {floor}:1")
        assert checked > 60, f"only {checked} rules measured; the sweep stopped seeing the file"
        assert not failures, f"{theme}: " + "; ".join(failures)

    def test_the_muted_ink_clears_aa_on_every_surface_in_both_themes(self):
        """Kept from the hand-written version, because `--ink-faint` is the
        token most likely to be reached for by someone adding a rule, and the
        sweep above only sees the rules that already exist."""
        for theme in ("light", "dark"):
            pal = _resolved(theme)
            for surface in self.SURFACES:
                behind = pal.rgb(f"var({surface})")
                got = ratio(pal.rgb("var(--ink-faint)"), behind)
                assert got >= 4.5, f"{theme} --ink-faint on {surface} is {got:.2f}:1"

    def test_the_link_colour_is_the_reason_the_deep_brand_step_exists(self):
        """`--brand-text` is the palette's AA correction for white. The page
        also paints text on `--cream-dark`, where it drops to 4.43:1, so
        `--link` points one step deeper. If someone collapses the alias back
        this fails before the sweep does, with the reason attached."""
        pal = _resolved("light")
        cream = pal.rgb("var(--cream-dark)")
        assert ratio(pal.rgb("var(--brand-text)"), cream) < 4.5, "the palette moved; drop --link"
        assert ratio(pal.rgb("var(--link)"), cream) >= 4.5
