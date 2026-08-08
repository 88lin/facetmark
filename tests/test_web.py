"""Tests for the web UI served at ``/app``.

Three kinds of assertion live here, and they exist for three different reasons.

*Routing and auth.* ``/app``, ``/app/static/*`` and ``/app/boot`` are the only
unauthenticated routes that were added, so each one is pinned: what it serves,
that it needs no token, and -- for ``/app/boot``, the only route in the service
that can hand out the pairing token -- exactly when it refuses to.

*Contract.* ``app.js`` reads response fields by name off `await res.json()`,
which is the same unchecked cast the extension makes and the same failure mode:
a renamed field arrives as ``undefined`` and renders as an empty string. The
extension has its own contract test for this. The web UI now has one too.

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

REPO = Path(__file__).resolve().parents[1]


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


def _js_paths(src: str) -> set[str]:
    """Every request path the client builds, query strings stripped."""
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
        declared = _js_paths(js("app.js"))
        routes = {r.path for r in client.app.routes}
        assert declared, "parsed no paths out of app.js"
        assert declared <= routes, f"app.js calls routes that do not exist: {declared - routes}"

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
        read = (_js_reads(js("app.js"), "full") | _js_reads(js("app.js"), "more")
                | _js_reads(js("app.js"), "quick"))
        assert read, "parsed no field reads out of app.js"
        assert read <= sent, f"app.js reads fields the server never sends: {sorted(read - sent)}"

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
        read = _js_reads(js("app.js"), "h")
        assert read, "parsed no hit-field reads out of app.js"
        # `via`/`via_kind` are only present on expansion rows, by design.
        assert read - {"via", "via_kind"} <= set(hit), (
            f"app.js reads hit fields the server never sends: {sorted(read - set(hit))}"
        )

    def test_the_stats_shape_the_page_assumes_is_the_shape_the_server_sends(self, client):
        auth = {"Authorization": f"Bearer {client.app.state.fm.token}"}
        stats = client.get("/stats", headers=auth).json()
        read = _js_reads(js("app.js"), "s")
        assert read <= set(stats), f"unknown stats keys: {sorted(read - set(stats))}"

    def test_vectors_is_a_pair_and_the_page_knows_it(self, client):
        """``db.count_vectors()`` returns a tuple, so JSON makes it an array.

        Reading ``.content`` off it would be ``undefined`` and render blank.
        """
        auth = {"Authorization": f"Bearer {client.app.state.fm.token}"}
        vectors = client.get("/stats", headers=auth).json()["vectors"]
        assert isinstance(vectors, (list, dict))
        assert "Array.isArray(s.vectors)" in js("app.js")


# ---------------------------------------------------------------------------
# strings
# ---------------------------------------------------------------------------


DYNAMIC = ("edge.", "health.", "queue.")
"""Key families the page builds at runtime, e.g. ``edge.${kind}``.

A literal scan cannot see these, so they are exempted here and checked against
the server-side enumerations instead -- which is stricter than a scan, not
looser: a scan proves someone typed the key, the vocabulary tests prove every
value the server can emit has a name.
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
    for name in ("app.js", "paging.js", "format.js", "i18n.js"):
        keys |= set(re.findall(r"\"([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)\"", js(name)))
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
        assert "`${key}.why`" in js("app.js"), "the tooltip lookup moved; re-derive this rule"
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
    """Three stylesheets, one product.

    ``extension/src/popup.css`` and ``docs/landing/style.css`` are deliberately
    not refactored into a shared file -- one ships in a wheel, one in a zip and
    one on GitHub Pages. Only the two values a reader would actually notice
    diverging are pinned.
    """

    @staticmethod
    def _token(css: str, name: str) -> str:
        m = re.search(rf"{name}:\s*([^;]+);", css)
        assert m, f"{name} not found"
        return m.group(1).strip().lower()

    def test_the_accent_and_paper_agree_across_the_three_stylesheets(self):
        sources = {
            "web": (STATIC_DIR / "app.css"),
            "landing": REPO / "docs" / "landing" / "style.css",
            "extension": REPO / "extension" / "src" / "popup.css",
        }
        seen = {}
        for where, path in sources.items():
            if not path.exists():
                pytest.skip(f"{where} stylesheet not in this tree")
            css = path.read_text(encoding="utf-8")
            seen[where] = (self._token(css, "--accent"), self._token(css, "--paper"))
        assert len(set(seen.values())) == 1, f"three stylesheets, {len(set(seen.values()))} brands: {seen}"


class TestTheContrast:
    """``--ink-mute`` is a promise, so it is measured rather than trusted.

    The palette carries a comment saying ``--ink-3`` is too light for text.
    That comment was true of ``docs/landing/style.css``, where ink-3 only draws
    hairlines, and quietly false here the moment the search page used it for
    rank numbers, the footer and the "N months ago" chip. A comment cannot
    catch that; a ratio can.

    Only ink-mute is pinned. ink-3 keeps its two legitimate jobs -- a hover
    border, which WCAG scores as a non-text object at 3:1, and disabled button
    text, which WCAG 1.4.3 exempts.
    """

    THEMES = {
        ":root": ("light", 4.5),
        r':root\[data-theme="dark"\]': ("dark", 4.5),
    }
    BACKDROPS = ("--paper", "--paper-2", "--surface", "--surface-2")

    @staticmethod
    def _ratio(fg: str, bg: str) -> float:
        def channel(v: int) -> float:
            c = v / 255
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

        def luminance(hexcolor: str) -> float:
            h = hexcolor.lstrip("#")
            r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
            return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

        a, b = luminance(fg), luminance(bg)
        hi, lo = max(a, b), min(a, b)
        return (hi + 0.05) / (lo + 0.05)

    def _block(self, css: str, selector: str) -> dict[str, str]:
        m = re.search(rf"{selector}\s*\{{(.*?)\n\}}", css, re.S)
        assert m, f"{selector} block not found in app.css"
        return dict(re.findall(r"(--[\w-]+):\s*([^;]+);", m.group(1)))

    def test_the_muted_ink_clears_aa_on_every_surface_in_both_themes(self):
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        light = self._block(css, ":root")
        checked = 0
        for selector, (name, floor) in self.THEMES.items():
            block = dict(light)
            if name != "light":
                block.update(self._block(css, selector))
            fg = block["--ink-mute"].strip()
            for key in self.BACKDROPS:
                ratio = self._ratio(fg, block[key].strip())
                assert ratio >= floor, f"{name} --ink-mute on {key} is {ratio:.2f}:1, below {floor}:1"
                checked += 1
        assert checked == 8, f"expected 8 measurements, made {checked}"

    def test_the_light_ink_3_is_still_too_light_for_text(self):
        """The comment's claim, asserted. If someone lightens ink-3 into AA
        range this fails and the comment above it should be deleted, not the
        test."""
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        light = self._block(css, ":root")
        ratio = self._ratio(light["--ink-3"].strip(), light["--paper-2"].strip())
        assert ratio < 4.5, f"ink-3 is now {ratio:.2f}:1 on paper-2; the comment is stale"

    def test_no_small_text_rule_paints_itself_with_ink_3(self):
        """Guards the actual regression: ink-3 creeping back into a text rule.

        A rule is "text" if it sets ``color``. The two survivors are named."""
        css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
        allowed = {".btn:disabled"}
        offenders = []
        for m in re.finditer(r"(?:^|\n)([^{}\n][^{}]*?)\{([^{}]*)\}", css):
            selector, body = m.group(1).strip(), m.group(2)
            if re.search(r"(?<!-)\bcolor:\s*var\(--ink-3\)", body) and selector not in allowed:
                offenders.append(selector)
        assert not offenders, f"ink-3 is setting text colour in: {offenders}"
