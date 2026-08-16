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

from facetmark.admin import INDEX_STAGES, WRITABLE
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
    gradient_stops,
    luminance,
    painted,
    ratio,
    rules,
    strip_comments,
    value_of,
)

REPO = Path(__file__).resolve().parents[1]

#: The palette file cascades twice for palette I: the colourway itself, then
#: the semantic aliases every colourway shares. Resolving a token means
#: replaying both in order. (Palette A also carried a third block of AA
#: corrections; I ships display colours that already clear AA, so it has none.)
PALETTE_BLOCKS = (
    r'\[data-palette="I"\]',
    r':root,\s*\n\[data-palette\]',
)
DARK = r'html\[data-theme="dark"\]'
# The two selector prefixes that pin a rule to one theme. `:not(...)` rather
# than `[data-theme="light"]` for the light one, so the rule is also in force
# in the instant before the boot script writes the attribute.
THEME_SCOPE = {
    "dark": 'html[data-theme="dark"]',
    "light": 'html:not([data-theme="dark"])',
}


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


def _app_css() -> str:
    return (STATIC_DIR / "app.css").read_text(encoding="utf-8")


def _ladder(css: str, prefix: str) -> dict[str, str]:
    """Every `:root` custom property whose name starts with ``prefix``."""
    return {k: v for k, v in declarations(css, r":root").items() if k.startswith(prefix)}


def _used(css: str, prop: str) -> list[tuple[str, str]]:
    """(selector, value) for every declaration of ``prop``.

    Matching is on the whole property name, so `font-size` does not also
    collect `font-size-adjust` and `gap` does not collect `column-gap` twice.
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


def _alpha_of(pal: Palette, value: str) -> float:
    """How opaque a colour expression is, measured rather than parsed.

    ``rgba(var(--highlight-rgb), 0.15)`` hides its alpha behind a token, and
    ``var(--tint-lex)`` hides the whole expression behind another one. Painting
    the same colour over white and over black and reading the gap back out
    works whatever shape the value takes; integer rounding costs a few
    thousandths, which is why comparisons below carry a tolerance.
    """
    over_white = pal.rgb(value, (255, 255, 255))
    over_black = pal.rgb(value, (0, 0, 0))
    return 1 - max(w - b for w, b in zip(over_white, over_black, strict=True)) / 255


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


DYNAMIC = ("edge.", "health.", "queue.", "settings.f.", "settings.h.", "settings.src.",
           "settings.probe.", "stage.", "unit.")
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

    def test_every_writable_setting_has_a_label_and_an_explanation(self):
        """The settings form is built from ``WRITABLE``, one field per key.

        Two strings each: the label above the box and the sentence under it.
        A key added to ``WRITABLE`` without them renders a box captioned
        ``settings.f.embed_dim``, which is worse than not exposing it at all.
        """
        s = strings()
        for lang in ("en", "zh"):
            for key in WRITABLE:
                assert f"settings.f.{key}" in s[lang], f"{lang} has no label for {key}"
                assert f"settings.h.{key}" in s[lang], f"{lang} does not explain {key}"

    def test_every_source_a_setting_can_come_from_has_a_name(self):
        """``settings_view`` tags each row env, file or default."""
        s = strings()
        for lang in ("en", "zh"):
            for source in ("env", "file", "default"):
                assert f"settings.src.{source}" in s[lang], f"{lang} cannot say {source}"

    def test_every_index_stage_has_a_name(self):
        """The progress bar draws one tile per stage, named ``stage.${name}``.

        The enumeration is the server's, and the job document reports stages by
        the same names, so a stage renamed on one side shows the other side's
        raw identifier.
        """
        s = strings()
        for lang in ("en", "zh"):
            for stage in INDEX_STAGES:
                assert f"stage.{stage}" in s[lang], f"{lang} has no name for stage {stage}"

    def test_both_halves_of_the_connection_probe_have_a_name(self):
        """``/admin/settings/test`` reports chat and embed independently."""
        s = strings()
        for lang in ("en", "zh"):
            for half in ("chat", "embed"):
                assert f"settings.probe.{half}" in s[lang], f"{lang} cannot say {half}"

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
        assert re.search(r"<html[^>]*data-palette=\"I\"", html), "no palette pinned on <html>"

    def test_the_palette_is_linked_before_the_stylesheet_that_consumes_it(self):
        """`app.css` reads tokens the palette declares. Load it first and the
        page renders one paint with every custom property unresolved."""
        html = INDEX_HTML.read_text(encoding="utf-8")
        sheets = re.findall(r'<link rel="stylesheet" href="([^"]+)"', html)
        assert "/app/static/palettes.css" in sheets, "the palette is not linked"
        assert sheets.index("/app/static/palettes.css") < sheets.index("/app/static/app.css")

    #: The only literal colours allowed above the dark block, and the only
    #: place they may appear: inside the fence in `:root`. The three display
    #: hues are lifted from other colourways the vendored file already carries
    #: -- indigo from B, orchid from G, plum from C -- rather than mixed by
    #: hand. The `-ink` steps and the washes are derived: lightness walked
    #: until each ink cleared 4.5:1 on every surface and wash it can reach and
    #: each wash cleared that floor for both the body and the muted ink, while
    #: staying at least 3.30 dE00 from the other lanes. `TestTheContrast` and
    #: `TestTheTint` re-measure them on every run, so a wrong value here fails
    #: there rather than shipping.
    EXTENDED = {
        "--indigo": "#33548a",
        "--indigo-ink": "#233c68",
        "--indigo-soft": "#dfecfb",
        "--iris-soft": "#eee6fa",
        "--orchid": "#8a2f84",
        "--orchid-ink": "#662061",
        "--orchid-soft": "#ffdbfd",
        "--plum": "#7a3560",
        "--plum-ink": "#5b2349",
        "--plum-soft": "#f7f2f5",
        "--rose-soft": "#fee1ed",
    }

    FENCE = re.compile(
        r"/\* extended palette --[^*]*(?:\*(?!/)[^*]*)*\*/(.*?)/\* end extended palette \*/",
        re.S,
    )

    def test_the_stylesheet_names_no_colour_the_palette_did_not(self):
        """Everything above the dark block must be a token reference, with one
        fenced exception.

        The design system's brand rules forbid hardcoded colour values in
        shared components, and a stray hex is how a palette swap silently
        stops working. Black shadows and the modal scrim are exempt: they are
        the design system's own literals, and they are not brand colour.

        The exception is deliberate and is the reason the rebuild could
        happen at all. Palette A ships three hues, which is what produced a
        search screen of twenty identical white cards. The owner's own derived
        site runs nine. The extra six cannot go in `palettes.css` -- that file
        is vendored verbatim and pinned byte-for-byte against the site's copy
        by `tests/test_landing.py` -- so they live in `:root` between two
        markers, and this test still refuses every hex outside them and every
        name inside them that is not on the list above.
        """
        css, night = self._split()
        fenced = self.FENCE.search(css)
        assert fenced, "the extended palette fence is missing or malformed"

        outside = css[: fenced.start()] + css[fenced.end() :]
        assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", outside), "hardcoded hex outside the fence"
        for literal in re.findall(r"rgba?\(\s*\d[^)]*\)", outside):
            channels = [c.strip() for c in literal.split("(")[1].rstrip(")").split(",")]
            assert set(channels[:3]) == {"0"}, f"{literal} is a colour, not a shadow"

        inside = dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{3,8})\s*;", fenced.group(1)))
        assert inside == self.EXTENDED, (
            "the fence no longer matches the list this test names; "
            f"unexpected {sorted(set(inside) - set(self.EXTENDED))}, "
            f"missing {sorted(set(self.EXTENDED) - set(inside))}"
        )
        assert not re.findall(
            r"rgba?\(\s*\d[^)]*\)", fenced.group(1)
        ), "the fence is for named hexes only; an rgba here would dodge the sweep"
        assert night, "the dark block vanished; this test is now measuring nothing"

    def test_the_fence_sits_inside_the_root_block(self):
        """A fence anywhere else would be a licence to hardcode colour in a
        component, which is the thing the test above exists to prevent."""
        css, _ = self._split()
        root = re.search(r":root\s*\{(.*?)\n\}", css, re.S)
        assert root, "no :root block"
        assert self.FENCE.search(root.group(1)), "the extended palette is not inside :root"

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
        assert "--mark-band" in night, (
            "--mark-band must be re-pointed for dark: full-strength yellow under "
            "near-white ink is 1.6:1, and the highlighter is a wash, not a block"
        )
        assert "--select-band" in night, (
            "--select-band must be re-pointed for dark: the daylight .28 wash over "
            "a near-black page leaves a selection the night ink cannot be read on"
        )
        assert "--tint-lex" in night, (
            "--tint-lex must be re-pointed for dark: daylight-strength yellow over "
            "a near-black panel reads olive, not as a tint of the page"
        )
        for token in self.EXTENDED:
            assert token in night, (
                f"{token} has no night step: the extended palette is tuned for a cream page "
                "and renders at daylight strength on a near-black one"
            )
        assert len(night) == 39, f"the dark block is now {len(night)} tokens; review each addition"

    @staticmethod
    def _split() -> tuple[str, str]:
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        cut = css.index('html[data-theme="dark"]')
        return css[:cut], css[cut:]


class TestTheAppScale:
    """One ladder for size, one for leading, one for tracking, one for space
    -- and the same four the landing site climbs.

    This half of the product was left behind. Stage 6 collapsed
    `docs/landing/style.css` from 33 absolute sizes to nine rungs and from 58
    ad-hoc paddings to an eight-step grid; `app.css` kept shipping 30 distinct
    font sizes -- the run 0.72 / 0.74 / 0.75 / 0.76 / 0.78 / 0.80 / 0.82 /
    0.84 / 0.85 / 0.86rem is nine neighbours inside three pixels -- and 54
    distinct spacing literals. A browser measuring the library view found its
    section gaps at 30 / 22 / 18 / 16 / 14 / 12 / 10 / 9 / 8 / 6px. That is
    what "挤压在一起，不对齐" looks like from the outside, and no amount of
    care in any one rule fixes it; only a grid does.

    The rungs are asserted equal to the landing site's rather than merely
    present. Two scales that agree today and are pinned nowhere are two scales
    that disagree in six months, which is exactly the state this class was
    written to end.
    """

    #: Below this a value is a hairline -- the 1px that keeps inline code off
    #: its own background edge, the 2-3px nudge that centres a glyph in a
    #: pill. Snapping those to 4px is visible and wrong, and nothing is
    #: aligned to within 3px by eye anyway.
    HAIRLINE = 3

    def test_the_two_surfaces_agree_on_the_scale(self):
        """The app and the site are one product. A reader moves between them
        in one click, and a 13px caption on one side next to a 13.6px caption
        on the other is the drift this pins shut."""
        app, site = _app_css(), (REPO / "docs" / "landing" / "style.css").read_text("utf-8")
        for prefix in ("--fs-", "--lh-", "--ls-", "--sp-"):
            mine, theirs = _ladder(app, prefix), _ladder(site, prefix)
            assert mine == theirs, (
                f"the {prefix} ladders have drifted: app {mine} vs site {theirs}"
            )

    def test_no_rule_names_a_size_the_ladder_does_not(self):
        """A rung is only a rung while everything stands on it."""
        css = _app_css()
        rungs = _ladder(css, "--fs-")
        assert sorted(rungs) == [f"--fs-{n}" for n in range(9)], sorted(rungs)
        for selector, value in _used(css, "font-size"):
            assert re.fullmatch(r"var\(--fs-[0-8]\)", value), (
                f"{selector} sets font-size: {value}, off the ladder"
            )

    def test_the_leading_and_tracking_come_off_the_ladder_too(self):
        """`line-height: 1` is exempt and is not a sixth rung: it is what a
        box holding exactly one line -- a 32px numeral, a round close button
        -- needs to centre its own glyph. The file had ten leadings and four
        unrelated trackings before this."""
        css = _app_css()
        assert sorted(_ladder(css, "--lh-")) == [
            "--lh-body", "--lh-cjk", "--lh-code", "--lh-snug", "--lh-tight",
        ]
        assert sorted(_ladder(css, "--ls-")) == [
            "--ls-caps", "--ls-caps-wide", "--ls-display", "--ls-none",
        ]
        for selector, value in _used(css, "line-height"):
            assert re.fullmatch(r"var\(--lh-[a-z]+\)|1", value), (
                f"{selector} sets line-height: {value}, off the ladder"
            )
        for selector, value in _used(css, "letter-spacing"):
            assert re.fullmatch(r"var\(--ls-[a-z-]+\)", value), (
                f"{selector} sets letter-spacing: {value}, off the ladder"
            )

    def test_every_gap_and_pad_comes_from_the_grid(self):
        css = _app_css()
        grid = _ladder(css, "--sp-")
        assert sorted(grid) == [f"--sp-{n}" for n in range(1, 9)], sorted(grid)
        offenders = []
        for selector, prop, value in _used_family(
            css, "padding", "margin", "gap", "row-gap", "column-gap"
        ):
            for raw in re.findall(r"-?[\d.]+px", value):
                if abs(float(raw[:-2])) > self.HAIRLINE:
                    offenders.append(f"{selector} {{ {prop}: {value} }}")
                    break
        assert not offenders, "off-grid spacing: " + "; ".join(offenders)

    def test_the_ladders_are_actually_used(self):
        """Every assertion above is also satisfied by a stylesheet that sets
        no sizes and no spacing at all. This is the one that fails if the
        tokens are declared and then ignored -- the mistake `--dark-panel`
        already made in this file, where a token nothing consumed left a test
        with nothing to measure for the whole life of the page.
        """
        css = _app_css()
        sizes = [v for _, v in _used(css, "font-size") if "var(--fs-" in v]
        space = [
            v
            for _, _, v in _used_family(css, "padding", "margin", "gap",
                                        "row-gap", "column-gap")
            if "var(--sp-" in v
        ]
        assert len(sizes) > 60, f"only {len(sizes)} rules read the size ladder"
        assert len(space) > 120, f"only {len(space)} rules read the spacing grid"

    def test_the_chinese_interface_gets_its_own_leading(self):
        """Han glyphs fill their em box edge to edge, so 1.65 reads as
        comfortable in Latin and as packed in Chinese, and the -0.022em that
        tightens a Latin heading has no sidebearing to take it out of and
        collides the characters instead.

        `app.js` writes `lang="zh-CN"` on the root when the language pill is
        used, and until now nothing in this stylesheet read it: the Chinese
        app was the English app with Chinese words in it. Asserted by effect
        rather than by selector text, so a different fix with the same result
        still passes.
        """
        css = strip_comments(_app_css())
        zh = [(s, b) for s, b in rules(css) if ":lang(zh)" in s or 'lang="zh"' in s]
        assert zh, "nothing in the stylesheet is scoped to Chinese"
        assert any(
            re.search(r"\bbody\b", s) and "var(--lh-cjk)" in b for s, b in zh
        ), f"the Chinese interface still reads at the Latin measure; zh rules: {[s for s, _ in zh]}"
        zeroed = " ".join(s for s, b in zh if "letter-spacing: var(--ls-none)" in b)
        assert zeroed, "no zh rule zeroes tracking"
        for element in ("h1", "h2", "h3", ".page-title"):
            assert re.search(rf"{re.escape(element)}\b", zeroed), (
                f"the zh tracking reset does not reach {element}: {zeroed}"
            )


class TestTheAppScene:
    """The four things the design system forbids on a functional page.

    `references/scene-app.md` ends with a short list of taboos, and three of
    them are the kind of rule that gets broken by a well-meaning single commit
    six months from now. They are cheap to check, so they are checked. The
    fourth -- no long decorative prose -- is a judgement call and is left to
    review.
    """

    #: A light page's surfaces have to stay light. Shared with
    #: `tests/test_landing.py`, deliberately: the two stylesheets should agree
    #: on where a tint stops being a tint and starts being a panel. 0.05 is an
    #: order of magnitude above `--ink`.
    DAYLIGHT_FLOOR = 0.05

    #: The modal scrim, and the only thing on the page allowed to be darker
    #: than the page. It is `rgba(0, 0, 0, .6)` over the whole viewport and
    #: dimming what is behind it is the entire job; the same literal is
    #: already exempted by name in
    #: `test_the_stylesheet_names_no_colour_the_palette_did_not`.
    SCRIM = ".overlay"

    def test_no_dark_panel_in_a_functional_area(self):
        """`深色只用于夜间模式场景`. A dark slab in the middle of a light page
        reads as a terminal, and the one place it crept in was a shell command
        inside a warning notice.

        Two halves, because the first one on its own was decorative. Naming
        the `--dark-panel` token catches the copy-paste that started this, but
        that token is declared in `palettes.css` and consumed nowhere, so the
        check has never had anything to measure and could not fire. The
        landing stylesheet proved what that blindness costs: it painted every
        command block `#17160f`, a hand-written hex no token scan would ever
        see, and the owner's "黑不溜秋的黑色的统统全部换掉" was aimed straight
        at it. So the second half resolves every background this stylesheet
        paints -- token, literal, or wash -- composites it over the page it
        lands on, and reads the luminance back.
        """
        light, _ = TestTheBrand._split()
        offenders = [sel for sel, body in rules(light) if "--dark-panel" in body]
        assert not offenders, f"dark panel painted in: {offenders}"

        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        palette = _resolved("light")
        page = palette.rgb("var(--cream)", (255, 255, 255))
        failures = []
        for selector, shade, measured in self._backgrounds(css, "light", palette, page):
            if selector == self.SCRIM or measured >= self.DAYLIGHT_FLOOR:
                continue
            failures.append(f"{selector} paints {shade} (luminance {measured:.4f})")
        assert not failures, (
            f"slabs below the {self.DAYLIGHT_FLOOR} daylight floor: " + "; ".join(failures)
        )

    def test_the_night_page_has_no_holes_punched_in_it(self):
        """The same rule read from the other side.

        Dark mode does not ban darkness, so the floor above says nothing here.
        What it can still get wrong is depth: a surface painted *below* the
        page reads as a hole cut through the screen rather than a card resting
        on it, and it is the same mistake -- a slab that ignores the scene --
        wearing the other theme. The night stack is built upward from
        `--cream`, so the page itself is the floor.
        """
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        palette = _resolved("dark")
        page = palette.rgb("var(--cream)", (0, 0, 0))
        floor = luminance(page)
        failures = []
        for selector, shade, measured in self._backgrounds(css, "dark", palette, page):
            if selector == self.SCRIM or measured >= floor - 1e-6:
                continue
            failures.append(f"{selector} paints {shade} (luminance {measured:.4f})")
        assert not failures, (
            f"surfaces sunk below the night page ({floor:.4f}): " + "; ".join(failures)
        )

    #: The night stack, page first, each surface resting on the one before it:
    #: the page, the sunken well a KPI tile sits in, the card, the preview
    #: panel inside a card.
    NIGHT_STACK = ("--cream", "--cream-dark", "--card-bg", "--preview-bg")

    #: How far apart two neighbouring night surfaces have to be before the
    #: step between them is a step a reader can see. 1.12 with the stack as
    #: shipped measuring 1.17 / 1.15 / 1.16 -- and the stack this replaced
    #: measuring 1.08 / 1.01 / 1.04, a card one percent brighter than the well
    #: it sat in, which is why the night app photographed as one flat slab.
    NIGHT_STEP = 1.12

    def test_the_night_surfaces_are_a_ladder_and_not_one_slab(self):
        """The rule above says no surface may sink below the page. That is
        satisfied perfectly by painting all four the same colour, which is
        very nearly what this file shipped: `#14161c`, `#1b1e26`, `#1c1f28`,
        `#23252c` -- a card 0.8% brighter than the well behind it.

        Depth in a dark interface is the only thing separating a card from the
        page, because the shadows that do that job in daylight are invisible
        on a near-black background. So the stack is asserted as a ladder:
        strictly increasing, and every rung far enough from its neighbour to
        be seen rather than merely to differ.
        """
        palette = _resolved("dark")
        rungs = [
            (token, luminance(palette.rgb(f"var({token})", (0, 0, 0))))
            for token in self.NIGHT_STACK
        ]
        for (lower, dim), (upper, lit) in zip(rungs, rungs[1:], strict=False):
            step = (lit + 0.05) / (dim + 0.05)
            assert step >= self.NIGHT_STEP, (
                f"{upper} ({lit:.4f}) is only {step:.3f}x above {lower} ({dim:.4f}); "
                f"the night stack needs {self.NIGHT_STEP}x to read as a step"
            )

    @staticmethod
    def _backgrounds(css, theme, palette, page):
        """Every background this theme can actually paint, already composited.

        A rule whose selector names the other theme cannot fire here, and
        grading it anyway asks a question the interface never poses -- the
        same filter `TestTheContrast` applies for the same reason.
        """
        other = 'html[data-theme="dark"]' if theme == "light" else 'html:not([data-theme="dark"])'
        for selector, body in rules(css):
            if other in selector:
                continue
            value = value_of(body, "background-color") or value_of(body, "background")
            shade = first_colour(value) if value else None
            if not shade:
                continue
            measured = luminance(palette.rgb(shade, page))
            for one in (s.strip() for s in selector.split(",")):
                yield one, shade, measured

    #: Selectors allowed past the body ceiling, and why each one is on the
    #: list. Everything absent from it is body-level text and still capped at
    #: 1.2rem, which is what keeps a dense result list dense.
    DISPLAY = {
        r"\.num\b": "dashboard numerals -- the whole point of that card",
        r"\.page-title\b": "the one heading per screen; without it a screen starts mid-list",
        r"\.bignum\b": "design system component 8, the oversized decorative numeral",
    }
    CEILING_BODY = 1.2
    CEILING_DISPLAY = 2.6

    def test_no_heading_is_larger_than_the_scene_allows(self):
        """`App内标题控制在1.2rem以内`, with five named exceptions.

        The 1.2rem cap came from `scene-app.md` and was applied to everything,
        including the page title and the setup wizard's step numerals. The
        result was a screen with no typographic top: every line the same size,
        so nothing read as a heading and the eye had nowhere to land. The
        project owner rejected it and pointed at their own derived site, whose
        section heads run 800 weight and well past 1.2rem.

        So the cap now applies to body-level text, where it is doing real
        work, and five display selectors are named and given a ceiling of
        their own. The list is the point: an unnamed selector is still capped,
        so the exception cannot spread by being convenient.

        The sizes are tokens now, and a `rem` scan of `var(--fs-4)` finds no
        digits at all -- which would have left this test passing every rule in
        the file without measuring one of them, the same silent retirement
        `test_no_dark_panel_in_a_functional_area` suffered. So the rung is
        resolved through the ladder first, and the count of what was graded is
        asserted alongside the caps.
        """
        light, _ = TestTheBrand._split()
        ladder = _ladder(_app_css(), "--fs-")
        display = {re.compile(p) for p in self.DISPLAY}
        graded = 0
        for selector, body in rules(light):
            size = value_of(body, "font-size")
            if not size:
                continue
            rung = re.fullmatch(r"var\((--fs-\d)\)", size)
            assert rung and rung.group(1) in ladder, f"{selector} sets {size}, off the ladder"
            resolved = ladder[rung.group(1)]
            cap = (
                self.CEILING_DISPLAY
                if any(p.search(selector) for p in display)
                else self.CEILING_BODY
            )
            for rem in re.findall(r"([\d.]+)rem", resolved):
                assert float(rem) <= cap, (
                    f"{selector} sets {size} = {resolved}, over the {cap}rem cap"
                )
            graded += 1
        assert graded >= 60, f"only {graded} sized rules were graded; the cap has gone quiet"

    def test_the_display_exceptions_are_all_still_used(self):
        """An exception that no longer matches anything is an exception
        someone can widen without noticing what it was for."""
        light, _ = TestTheBrand._split()
        selectors = [s for s, _ in rules(light)]
        for pattern, why in self.DISPLAY.items():
            probe = re.compile(pattern)
            assert any(probe.search(s) for s in selectors), f"nothing matches {pattern} ({why})"

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
    LARGE = {".num b", ".num.gold b", ".num.edge b", ".num.ink b"}

    #: WCAG 1.4.3 exempts disabled controls.
    EXEMPT = {".btn:disabled"}

    def test_these_are_the_only_surfaces_the_page_sits_text_on(self):
        """`SURFACES` is an input to the sweep below, so it is derived rather
        than trusted. Anything else painting a full-width background would
        widen the sweep, and this is where that shows up.

        `.hit` and `.num` used to be on this list and are not any more, because
        neither is a surface now. A result row below the fold paints nothing at
        all -- it is a line with a hairline under it -- and the rows and KPI
        cards that do paint carry a coloured wash rather than one of the three
        page colours. That is the rebuild: a wash is not a surface, it is a
        layer over one, and the right machine for grading a layer is
        ``TestTheTint``, which reads both ends of it. Every one of them is
        named there.
        """
        surfaces = painted((STATIC_DIR / "app.css").read_text(encoding="utf-8"))
        wide = {"body", ".top", ".sheet", ".card"}
        used = {v for k, v in surfaces.items() if k in wide}
        assert used <= {f"var({s})" for s in self.SURFACES}, f"unlisted page surface: {used}"

    def test_every_gradient_leads_with_its_strongest_stop(self):
        """The convention `palette.first_colour` leans on, stated out loud.

        A gradient has no single colour, so the auditor reads its first stop
        and grades text against that. That is the honest choice only while the
        first stop is the heaviest one: reverse a wash and the sweep would
        measure the corner where the tint has almost run out while the reader
        looks at the corner where it has not. The design system writes its
        145deg washes strong-corner-first, and this keeps them that way.
        """
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        pal = _resolved("light")
        found = 0
        for selector, body in rules(css):
            for prop in ("background", "background-image"):
                stops = gradient_stops(value_of(body, prop) or "")
                if len(stops) < 2:
                    continue
                found += 1
                alphas = [_alpha_of(pal, stop) for stop in stops]
                assert alphas[0] + 0.005 >= max(alphas), (
                    f"{selector} ({prop}) starts at alpha {alphas[0]:.2f} and "
                    f"peaks at {max(alphas):.2f}; the sweep only reads the first"
                )
        assert found >= 3, f"only {found} gradients seen; the scan stopped reading the file"

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
                # A rule that names a theme in its selector can only fire in
                # that theme, so grading it in the other one asks a question
                # the page never poses -- and answers it with tokens that rule
                # will never see. Two rules use this; both are commented at
                # the site of the exception.
                if one.startswith(THEME_SCOPE["dark"]) and theme != "dark":
                    continue
                if one.startswith(THEME_SCOPE["light"]) and theme != "light":
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

    def test_the_link_colour_is_the_seam_between_the_two_themes(self):
        """Palette A shipped `--brand-text` as an AA correction for white, and
        it still dropped to 4.43:1 on `--cream-dark`, so `--link` had to point
        one step deeper and this test asserted exactly that.

        Palette I needs no correction. `--brand-text` clears the floor on every
        surface the page paints -- 6.06:1 on `--cream`, 5.52:1 on
        `--cream-dark`, 6.16:1 on `--card-bg`, 4.95:1 on the weakest wash and
        4.64:1 under the highlighter band -- so the old premise is simply not
        true any more, and a test whose premise is false is worse than no test.

        What `--link` is still for is the seam. In daylight it is a real step
        deeper than brand text, which is what keeps a link in running prose
        separable from the brand-coloured labels around it. At night the
        lightened brand step is already the lightest readable violet on a
        near-black panel and a *deeper* one would read worse, so the two
        collapse onto one value. Delete either half of that and this fails with
        the reason attached rather than leaving the sweep to notice.
        """
        day, night = _resolved("light"), _resolved("dark")
        deep = ratio(day.rgb("var(--link)"), day.rgb("var(--cream)"))
        flat = ratio(day.rgb("var(--brand-text)"), day.rgb("var(--cream)"))
        assert deep > flat, (
            f"daylight --link ({deep:.2f}:1) is no deeper than --brand-text "
            f"({flat:.2f}:1); the token buys nothing"
        )
        assert night.rgb("var(--link)") == night.rgb("var(--brand-text)"), (
            "the night --link must collapse onto the lightened brand step"
        )
        for theme, pal in (("light", day), ("dark", night)):
            for surface in TestTheContrast.SURFACES:
                got = ratio(pal.rgb("var(--link)"), pal.rgb(f"var({surface})"))
                assert got >= 4.5, f"{theme} --link on {surface} is {got:.2f}:1"


class TestTheTint:
    """The two things the sweep above structurally cannot see.

    ``TestTheContrast`` grades the rule that *sets* a colour. That misses two
    shapes, and both of them are shipped by this stylesheet:

    *Inherited ink on a tinted panel.* ``.caps`` and ``.dim`` declare
    ``--ink-faint`` at the top level, where it clears AA by 0.37. Put either
    one inside a tinted base card and the wash eats more than that -- the four
    variants land between 4.06:1 and 4.42:1 -- but the sweep still grades the
    top-level rule against the bare page and passes it. So the tints are
    measured here directly, against every ink that can reach them.

    *The highlighter.* ``.mark`` paints ``background-image``, which is not a
    background colour and is invisible to ``painted()``. The band is a real
    surface with real text on it, so it is graded by hand.
    """

    #: Every tinted surface, keyed by the class that paints it. The values are
    #: the strongest stop of each wash -- the corner that costs a reader the
    #: most contrast. The test below checks the claim against the stylesheet
    #: rather than trusting it, and the sweep grades every stop, not just this
    #: one, because a thin corner on a dark page is the worse end there.
    #:
    #: This was five entries when the only tinted things on the page were the
    #: base cards. The rebuild puts a wash under the top three result rows, the
    #: graph-expansion rows, the three setup frames and the four KPI cards --
    #: that is the point of it, and it is also eleven new surfaces with text on
    #: them. Listing them here is what puts them through the same machine.
    TINTS = {
        ".tint": "var(--tint-content)",
        ".tint.lex": "var(--tint-lex)",
        ".tint.intent": "var(--tint-intent)",
        ".tint.context": "var(--tint-context)",
        ".tint.plain": "var(--tint-plain)",
        # The result list. Hue by the path that found the row; plum for the
        # rows that were walked to rather than ranked.
        ".hit.lead": "var(--iris-soft)",
        ".hit.lead.f-lex": "var(--highlight-soft)",
        ".hit.lead.f-tri": "var(--indigo-soft)",
        ".hit.lead.f-intent": "var(--orchid-soft)",
        ".hit.near": "var(--plum-soft)",
        # The three first-run frames.
        ".sketch": "var(--iris-soft)",
        ".sketch.lex": "var(--highlight-soft)",
        ".sketch.intent": "var(--orchid-soft)",
        # The dashboard KPI row.
        ".num": "var(--iris-soft)",
        ".num.gold": "var(--highlight-soft)",
        ".num.edge": "var(--plum-soft)",
        ".num.ink": "var(--cream-dark)",
        # Synthesis: the claim list is one frame, and a source jumped to from
        # a citation is lit rather than bordered.
        ".claims": "var(--iris-soft)",
        ".src.lit": "var(--highlight-soft)",
        # Sittings, component 34. The hue rotates and means nothing; it is
        # measured here anyway, because a reader still has to read off it.
        ".sitting": "var(--iris-soft)",
        ".sitting.f-lex": "var(--highlight-soft)",
        ".sitting.f-edge": "var(--plum-soft)",
        ".sitting.f-intent": "var(--orchid-soft)",
        ".sitting.f-tri": "var(--indigo-soft)",
        # The system page, where the hue does mean something.
        ".card.hue": "var(--iris-soft)",
        ".card.hue.lex": "var(--highlight-soft)",
        ".card.hue.ctx": "var(--rose-soft)",
        ".card.hue.edge": "var(--plum-soft)",
    }

    #: The inks that can land on a tint by inheritance. `--ink-faint` is
    #: deliberately absent: the stylesheet re-points it, and
    #: `test_the_faintest_ink_is_re_pointed_inside_a_tint` is why.
    INHERITED = ("--ink", "--ink-light")

    def _washes(self) -> dict[str, list[str]]:
        """Every colour layer each variant can put between text and the page."""
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        out: dict[str, list[str]] = {}
        for selector, body in rules(css):
            if selector not in self.TINTS:
                continue
            value = value_of(body, "background") or ""
            assert value_of(body, "background-color") is None, (
                f"{selector} declares a flat colour as well as a wash; the two "
                "composite, so the card renders at close to twice its alpha"
            )
            assert value_of(body, "background-image") is None, (
                f"{selector} splits its wash across two longhands"
            )
            out[selector] = gradient_stops(value) or [first_colour(value)]
        return out

    def test_each_tint_is_one_layer_and_leads_with_the_token_it_is_named_for(self):
        """One declaration, one token, no stacking.

        The first cut at this put a flat `background-color` under the gradient
        so `painted()` had a colour it could read. Both layers composite: the
        cards rendered at close to twice their declared alpha while the sweep
        graded the single, lighter layer. The auditor reads gradient stops now,
        so each variant is one shorthand and the alpha in the token is the
        alpha on screen -- which is also what lets the dark block re-point one
        wash without forking the rule.
        """
        washes = self._washes()
        assert set(washes) == set(self.TINTS), f"tint variants moved: {sorted(washes)}"
        for selector, stops in washes.items():
            assert stops[0] == self.TINTS[selector], f"{selector} leads with {stops[0]}"

    def test_the_night_yellow_is_weaker_than_the_daylight_one(self):
        """Yellow is the one hue that does not survive the trip to a near-black
        page: at daylight strength the lexical card reads olive. If someone
        collapses the two back into one value this says which direction the
        difference is meant to run, rather than leaving a bare number."""
        day = _resolved("light").raw("--tint-lex")
        night = _resolved("dark").raw("--tint-lex")
        assert day != night, "the night yellow is back to daylight strength"
        assert float(night.rstrip(")").rsplit(",", 1)[1]) < float(day.rstrip(")").rsplit(",", 1)[1])

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_every_ink_that_can_reach_a_tint_clears_aa_on_it(self, theme):
        """Both ends of every wash, not just the thick one.

        Which end is worse depends on the theme: on cream a heavier wash is a
        darker surface under dark ink, on near-black it is a lighter surface
        under light ink. Grading the strongest stop alone would be
        conservative in daylight and optimistic at night, so both are graded.
        """
        pal = _resolved(theme)
        failures = []
        for selector, stops in self._washes().items():
            for tint in stops:
                for ink in self.INHERITED:
                    for surface in TestTheContrast.SURFACES:
                        behind = pal.rgb(tint, pal.rgb(f"var({surface})"))
                        got = ratio(pal.rgb(f"var({ink})"), behind)
                        if got < 4.5:
                            failures.append(f"{selector}: {ink} over {tint} over {surface} is {got:.2f}:1")
                        if not pal.has_alpha(tint):
                            break
        assert not failures, f"{theme}: " + "; ".join(failures)

    def test_the_faintest_ink_is_re_pointed_inside_a_tint(self):
        """Without this rule the tints are the one place on the page where
        secondary text is quietly sub-AA, and nothing else would say so."""
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        body = dict(rules(css)).get(".tint .caps, .tint .dim")
        assert body, "the tint no longer re-points .caps and .dim"
        assert value_of(body, "color") == "var(--ink-light)"
        sunk = []
        for theme in ("light", "dark"):
            pal = _resolved(theme)
            for selector, tint in self.TINTS.items():
                for surface in TestTheContrast.SURFACES:
                    behind = pal.rgb(tint, pal.rgb(f"var({surface})"))
                    got = ratio(pal.rgb("var(--ink-faint)"), behind)
                    if got < 4.5:
                        sunk.append(f"{theme} {selector} over {surface} {got:.2f}:1")
        assert sunk, (
            "--ink-faint now clears AA on every tint and every surface, so the "
            "re-point above is dead weight; delete it and this test with it"
        )

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_the_highlighter_band_is_a_surface_text_survives(self, theme):
        pal = _resolved(theme)
        for surface in TestTheContrast.SURFACES:
            band = pal.rgb("var(--mark-band)", pal.rgb(f"var({surface})"))
            got = ratio(pal.rgb("var(--ink)"), band)
            assert got >= 4.5, f"{theme}: --ink on the band over {surface} is {got:.2f}:1"


class TestTheFontPolicy:
    """The page renders in the reader's system faces and downloads nothing.

    The earlier version vendored two decorative Latin faces under
    `static/fonts/`: Caveat for a handwritten corner label and Fraunces for a
    numeral. 94 KB of woff2, neither containing a single Han glyph, shipped in
    the wheel and served to every reader including the Chinese ones the label
    was written for.

    The project owner's own derived site, repair.88lin.eu.org, loads no faces
    at all. Its four stacks are system faces led by `-apple-system`, and its
    `--f-sans` puts `PingFang SC` ahead of any Windows face. facetmark now
    ships exactly those stacks, on both surfaces, and these tests hold that:
    no `@font-face`, no CDN, no banned family, Apple first, Han second.
    """

    BANNED = (
        # The design system's own list.
        "Inter",
        "Roboto",
        "Arial",
        # What this project actually shipped, which is how the ban went
        # unnoticed for as long as it did: nothing was checking.
        "Fraunces",
        "Caveat",
        "Liberation Sans",
    )

    @staticmethod
    def _surfaces() -> dict[str, str]:
        """Every surface that can name a face, with comments removed.

        Comments have to go or the test measures its own prose: the paragraph
        in `app.css` explaining why Caveat was deleted contains the word
        Caveat, and this class's own docstring names all six banned families.
        """
        out = {"index.html": re.sub(r"<!--.*?-->", "", INDEX_HTML.read_text(encoding="utf-8"), flags=re.S)}
        for path in sorted(STATIC_DIR.glob("*.css")):
            out[path.name] = strip_comments(path.read_text(encoding="utf-8"))
        return out

    def test_the_page_downloads_no_face_at_all(self):
        css = strip_comments((STATIC_DIR / "app.css").read_text(encoding="utf-8"))
        assert "@font-face" not in css, "app.css declares a downloadable face"
        assert not (STATIC_DIR / "fonts").exists(), "static/fonts is back"

    def test_no_stylesheet_or_page_reaches_a_font_cdn(self):
        """The failure this prevents is silent: the page looks right on the
        machine that built it and leaks on every other one."""
        for name, text in self._surfaces().items():
            for host in ("fonts.googleapis.com", "fonts.gstatic.com", "@import url(http"):
                assert host not in text, f"{name} reaches out to {host}"

    def test_the_text_stack_is_the_one_the_owner_specified(self):
        """Verbatim from `--f-sans` on the reference site. Order is asserted
        because order is the whole point: the stack this replaced had
        `"Segoe UI"` in second place, so a Windows reader got the Windows UI
        face and a Chinese reader reached PingFang SC only after it."""
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        stack = re.search(r"--font-sans:\s*([^;]+);", css)
        assert stack, "no --font-sans token"
        families = [f.strip().strip('"') for f in stack.group(1).split(",")]
        assert families[:2] == ["-apple-system", "BlinkMacSystemFont"], families[:2]
        assert "PingFang SC" in families, "the text stack names no Apple Han face"
        assert families.index("PingFang SC") < families.index("Microsoft YaHei")
        assert families[-1] == "sans-serif", "the stack has no generic tail"

    def test_the_display_and_mono_stacks_are_too(self):
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        display = re.search(r"--font-display:\s*([^;]+);", css)
        assert display and display.group(1).strip().startswith("-apple-system"), display
        mono = re.search(r"--font-mono:\s*([^;]+);", css)
        assert mono and mono.group(1).strip().startswith("ui-monospace"), mono

    @pytest.mark.parametrize("family", BANNED)
    def test_no_banned_family_is_named_anywhere(self, family):
        """Word boundaries, because `setInterval` and `Interleaving` are not
        the typeface Inter and a test that says they are gets disabled."""
        pattern = re.compile(rf"\b{re.escape(family)}\b")
        for name, text in self._surfaces().items():
            assert not pattern.search(text), f"{name} still names {family}"

    def test_the_two_surfaces_agree_on_the_text_stack(self):
        """A reader who moves from the site to the app should not watch the
        typeface change. Both files now carry the same four stacks, so the
        only way they can drift is if someone edits one of them."""
        app = re.search(
            r"--font-sans:\s*([^;]+);", (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        )
        site = re.search(
            r"--sans:\s*([^;]+);",
            (REPO / "docs" / "landing" / "style.css").read_text(encoding="utf-8"),
        )
        assert app and site
        norm = lambda m: [f.strip().strip("\"'") for f in m.group(1).split(",")]  # noqa: E731
        assert norm(app) == norm(site), "the app and the site disagree about the text stack"
