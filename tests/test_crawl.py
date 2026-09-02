"""``facetmark crawl``: the site walker ported from hister.

The tests mock the network with respx (the project's established tool for
this) and assert the three things the crawl promises: every fetched page
becomes a bookmark with its body, the walk stays on the start domain unless
told otherwise, and the page budget is honoured. Politeness itself -- robots,
per-host spacing -- is the fetch layer's and already tested there; here it
only has to be *used*, which the robots-denied case checks.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from facetmark.crawl import crawl_site, extract_links
from facetmark.db import open_db

PAGE_A = """<html><head><title>Docs index</title></head><body>
<p>Welcome to the documentation. Start with the guide.</p>
<a href="/guide">Guide</a>
<a href="/reference">Reference</a>
<a href="https://other.example/away">Off-site</a>
<a href="/guide#section">Fragment</a>
</body></html>"""

PAGE_B = """<html><head><title>Guide</title></head><body>
<p>The guide explains the whole system in one page.</p>
<a href="/guide">Self-link</a>
</body></html>"""

ROBOTS_ALLOW = "User-agent: *\nAllow: /\n"
ROBOTS_DENY = "User-agent: *\nDisallow: /\n"


def _page(html: str) -> httpx.Response:
    return httpx.Response(200, text=html, headers={"content-type": "text/html"})


@pytest.fixture()
def conn():
    c = open_db(":memory:")
    yield c
    c.close()


@pytest.fixture()
def settings(tmp_path):
    from facetmark.config import Settings

    return Settings(
        data_dir=tmp_path, use_mock_provider=True, embed_dim=32,
        embed_model="mock-embed", chat_model="mock-chat",
        health_enable_external=False,
    )


class TestExtractLinks:
    def test_relative_links_resolve_against_the_final_url(self):
        links = extract_links(PAGE_A, "https://docs.example/index")
        assert "https://docs.example/guide" in links
        assert "https://docs.example/reference" in links

    def test_fragments_are_stripped_so_they_dedupe(self):
        links = extract_links(PAGE_A, "https://docs.example/index")
        assert links.count("https://docs.example/guide") == 1

    def test_non_http_and_asset_links_are_dropped(self):
        html = '<a href="/x.png">img</a><a href="mailto:a@b">mail</a>'
        assert extract_links(html, "https://docs.example/") == []


class TestCrawlSite:
    @respx.mock
    async def test_pages_become_bookmarks_with_bodies(self, conn, settings):
        respx.get("https://docs.example/robots.txt").respond(
            200, text=ROBOTS_ALLOW, headers={"content-type": "text/plain"})
        respx.get("https://docs.example/").mock(return_value=_page(PAGE_A))
        respx.get("https://docs.example/guide").mock(return_value=_page(PAGE_B))

        rep = await crawl_site(conn, "https://docs.example/", max_pages=2,
                               settings=settings)

        assert rep.pages_fetched == 2
        assert rep.inserted == 2
        assert rep.bodies_stored == 2
        # Off-site link seen, counted, and not followed.
        assert rep.off_domain_skipped == 1
        rows = conn.execute(
            "SELECT url, title, source FROM bookmark ORDER BY id"
        ).fetchall()
        assert {r["source"] for r in rows} == {"crawl"}
        bodies = conn.execute(
            "SELECT bookmark_id, body_text FROM content WHERE body_text IS NOT NULL"
        ).fetchall()
        assert len(bodies) == 2
        assert conn.execute("SELECT COUNT(*) FROM fts_seg").fetchone()[0] == 2

    @respx.mock
    async def test_the_budget_stops_the_walk(self, conn, settings):
        respx.get("https://docs.example/robots.txt").respond(
            200, text=ROBOTS_ALLOW, headers={"content-type": "text/plain"})
        respx.get("https://docs.example/").mock(return_value=_page(PAGE_A))
        guide = respx.get("https://docs.example/guide").mock(return_value=_page(PAGE_B))

        rep = await crawl_site(conn, "https://docs.example/", max_pages=1,
                               settings=settings)
        assert rep.pages_fetched == 1
        assert rep.inserted == 1
        assert not guide.called

    @respx.mock
    async def test_an_existing_bookmark_is_not_duplicated(self, conn, settings):
        from facetmark.service import save_bookmark

        rec = save_bookmark(conn, "https://docs.example/guide", title="Guide",
                            settings=settings)
        respx.get("https://docs.example/robots.txt").respond(
            200, text=ROBOTS_ALLOW, headers={"content-type": "text/plain"})
        respx.get("https://docs.example/").mock(return_value=_page(PAGE_A))
        respx.get("https://docs.example/guide").mock(return_value=_page(PAGE_B))

        rep = await crawl_site(conn, "https://docs.example/", max_pages=5,
                               settings=settings)
        assert rep.inserted == 1
        assert rep.already_known == 1
        n = conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0]
        assert n == 2
        # The known row gained a body it did not have.
        body = conn.execute(
            "SELECT char_count FROM content WHERE bookmark_id=?",
            (rec["bookmark_id"],),
        ).fetchone()
        assert body["char_count"] > 0

    @respx.mock
    async def test_robots_denied_pages_are_counted_not_fetched(self, conn, settings):
        respx.get("https://docs.example/robots.txt").respond(
            200, text=ROBOTS_DENY, headers={"content-type": "text/plain"})
        page = respx.get("https://docs.example/").mock(return_value=_page(PAGE_A))

        rep = await crawl_site(conn, "https://docs.example/", settings=settings)
        assert rep.robots_denied == 1
        assert not page.called
        assert rep.inserted == 0

    @respx.mock
    async def test_off_domain_is_opt_in(self, conn, settings):
        respx.get("https://docs.example/robots.txt").respond(
            200, text=ROBOTS_ALLOW, headers={"content-type": "text/plain"})
        respx.get("https://other.example/robots.txt").respond(
            200, text=ROBOTS_ALLOW, headers={"content-type": "text/plain"})
        respx.get("https://docs.example/").mock(return_value=_page(PAGE_A))
        away = respx.get("https://other.example/away").mock(
            return_value=_page("<html><body>elsewhere</body></html>"))

        rep = await crawl_site(conn, "https://docs.example/", max_pages=5,
                               same_domain=True, settings=settings)
        assert rep.off_domain_skipped == 1
        assert not away.called

        # And on, when asked:
        rep2 = await crawl_site(conn, "https://docs.example/", max_pages=5,
                                same_domain=False, settings=settings)
        assert away.called
        assert rep2.off_domain_skipped == 0

    @respx.mock
    async def test_a_dead_page_does_not_end_the_crawl(self, conn, settings):
        respx.get("https://docs.example/robots.txt").respond(
            200, text=ROBOTS_ALLOW, headers={"content-type": "text/plain"})
        respx.get("https://docs.example/").mock(return_value=_page(PAGE_A))
        respx.get("https://docs.example/guide").mock(
            return_value=httpx.Response(404, text="gone"))
        respx.get("https://docs.example/reference").mock(return_value=_page(PAGE_B))

        rep = await crawl_site(conn, "https://docs.example/", max_pages=5,
                               settings=settings)
        assert rep.errors == 1
        assert rep.inserted == 2   # the start page and reference

    async def test_a_non_http_start_url_is_refused(self, conn, settings):
        rep = await crawl_site(conn, "javascript:alert(1)", settings=settings)
        assert rep.pages_fetched == 0
        assert rep.notes

    @respx.mock
    def test_the_cli_runs_the_crawl(self, settings, tmp_path, monkeypatch):
        # Sync on purpose: the CLI calls asyncio.run(), which refuses to start
        # inside an already-running loop -- which is what an async test is.
        from typer.testing import CliRunner

        from facetmark import cli

        db = tmp_path / "crawl.db"
        monkeypatch.setenv("FACETMARK_DATA_DIR", str(db.parent / "data"))
        respx.get("https://docs.example/robots.txt").respond(
            200, text=ROBOTS_ALLOW, headers={"content-type": "text/plain"})
        respx.get("https://docs.example/").mock(return_value=_page(PAGE_A))
        respx.get("https://docs.example/guide").mock(return_value=_page(PAGE_B))

        r = CliRunner().invoke(cli.app, [
            "crawl", "https://docs.example/", "--max-pages", "1", "--db", str(db),
        ])
        assert r.exit_code == 0, r.output
        assert "pages_fetched" in r.output
        from facetmark.db import connect

        c = connect(db)
        try:
            assert c.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 1
        finally:
            c.close()
