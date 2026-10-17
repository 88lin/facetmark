"""Shared Web routing, pairing security and React delivery contracts.

Behavior, keyboard focus, languages, responsive layout and rendering run in
frontend/tests against the real service in CI. Legacy sketch palette assertions
were retired with the replaced visual system; auth boundaries remain here.
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from facetmark.api import PUBLIC_PATHS, create_app
from facetmark.config import Settings
from facetmark.web import BUNDLE_DIR

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



class TestTheRoutes:
    def test_the_page_is_served_without_a_token(self, client):
        """A page that needs a token to load cannot ask the reader for one."""
        r = client.get("/app")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")
        assert "<title>" in r.text

    def test_the_assets_are_served_without_a_token(self, client):
        for name in ([p.name for p in (BUNDLE_DIR / "static").glob("*") if p.is_file()]
                     if BUNDLE_DIR.is_dir() else ["app.css", "app.js"]):
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




def test_react_source_has_no_remote_runtime_dependencies():
    source = (REPO / 'frontend/index.html').read_text(encoding='utf-8')
    assert 'id="root"' in source
    assert not re.search(r'(src|href)="https?://', source)
    css = (REPO / 'frontend/src/styles.css').read_text(encoding='utf-8')
    assert 'fonts.googleapis.com' not in css
    assert 'Microsoft YaHei' in css
    assert 'prefers-reduced-motion' in css


def test_production_bundle_in_ci_is_the_react_entry():
    import os
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        pytest.skip('Frontend builds run in GitHub Actions')
    index = BUNDLE_DIR / 'index.html'
    assert index.is_file(), 'Build the React workbench before cloud tests'
    html = index.read_text(encoding='utf-8')
    assert 'id="root"' in html
    assert re.search(r'/app/static/[^"]+\.js', html)
    assert list((BUNDLE_DIR / 'static').glob('*.css'))


@pytest.mark.parametrize('foreground,background', [
    ('#242429','#ffffff'),('#65656f','#ffffff'),('#65656f','#eee8fb'),
    ('#6541c7','#eee8fb'),('#ffffff','#6541c7'),
    ('#f1f1f4','#202024'),('#b1b1bc','#202024'),('#b1b1bc','#352b4c'),
    ('#b79cf5','#352b4c'),('#20172f','#b79cf5'),
])
def test_workbench_text_and_selected_states_have_aa_contrast(foreground, background):
    def lum(value):
        channels = [int(value[i:i+2],16)/255 for i in (1,3,5)]
        linear = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in channels]
        return sum(c*w for c,w in zip(linear,(.2126,.7152,.0722), strict=True))
    lo, hi = sorted((lum(foreground),lum(background)))
    assert (hi+.05)/(lo+.05) >= 4.5
