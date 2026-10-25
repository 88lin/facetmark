"""Cloud-only synthetic site-import limits, redirects, persistence and Stop."""
from __future__ import annotations

import asyncio
import time
from dataclasses import replace

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from pydantic import ValidationError

from facetmark import crawl, crawl_jobs
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.crawl import crawl_site
from facetmark.crawl_jobs import CrawlRequest, CrawlRunner
from facetmark.db import open_db
from facetmark.fetch.client import FetchPolicy, _HostLimiter
from facetmark.fetch.store import store_body
from facetmark.service import save_bookmark


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path, use_mock_provider=True, fetch_per_host_min_interval=0,
                    health_enable_external=False, respect_robots=False)


@pytest.fixture
def conn():
    database = open_db(":memory:")
    yield database
    database.close()


def page(text):
    return httpx.Response(200, text="<html><title>Synthetic docs</title><body>" + text + "</body></html>",
                          headers={"content-type": "text/html; charset=utf-8"})


@respx.mock
async def test_failed_pages_consume_the_budget_and_do_not_overscan(conn, settings):
    respx.get("https://docs.example/").mock(return_value=page('<a href="/a">A</a><a href="/b">B</a><a href="/c">C</a>'))
    respx.get("https://docs.example/a").respond(404)
    b = respx.get("https://docs.example/b").respond(500)
    c = respx.get("https://docs.example/c").mock(return_value=page("C"))
    report = await crawl_site(conn, "https://docs.example/", max_pages=2, settings=settings)
    assert report.pages_attempted == 2 and report.pages_fetched == 1 and report.errors == 1
    assert not b.called and not c.called


@pytest.mark.parametrize("destination,same_domain,excluded,counter", [
    ("https://other.example/secret", True, (), "off_domain_skipped"),
    ("https://private.example/secret", False, ("private.example",), "privacy_skipped"),
    ("https://user:password@docs.example/secret", False, (), "skipped"),
    ("file:///etc/passwd", False, (), "skipped"),
])
@respx.mock
async def test_redirect_destinations_are_checked_before_any_request(conn, settings, destination, same_domain, excluded, counter):
    respx.get("https://docs.example/").respond(302, headers={"location": destination})
    report = await crawl_site(conn, "https://docs.example/", settings=settings.model_copy(
        update={"privacy_excluded_domains": excluded}), same_domain=same_domain)
    assert getattr(report, counter) == 1 and report.pages_fetched == 0
    assert len(respx.calls) == 1


@respx.mock
async def test_each_redirect_checks_robots_and_releases_the_same_host_slot(conn, settings):
    respx.get("https://docs.example/robots.txt").respond(200, text="User-agent: *\nDisallow: /denied\n")
    respx.get("https://docs.example/").respond(302, headers={"location": "/denied"})
    denied = respx.get("https://docs.example/denied").mock(return_value=page("denied"))
    st = settings.model_copy(update={"respect_robots": True, "fetch_per_host_concurrency": 1})
    report = await asyncio.wait_for(crawl_site(conn, "https://docs.example/", settings=st), 2)
    assert report.robots_denied == 1 and not denied.called
    respx.get("https://docs.example/").respond(302, headers={"location": "/allowed"})
    respx.get("https://docs.example/allowed").mock(return_value=page("Saved after a redirect."))
    report = await asyncio.wait_for(crawl_site(conn, "https://docs.example/", settings=st), 2)
    assert report.inserted == 1 and report.pages_fetched == 1


@respx.mock
async def test_crawl_uses_saved_fetch_limits_and_the_robots_switch(conn, settings, monkeypatch):
    seen = []
    original = crawl._HostLimiter

    def limiter(policy):
        seen.append(policy)
        return original(policy)

    monkeypatch.setattr(crawl, "_HostLimiter", limiter)
    respx.get("https://docs.example/").mock(return_value=page("Synthetic reading material."))
    st = settings.model_copy(update={"fetch_concurrency": 5, "fetch_per_host_concurrency": 1})
    await crawl_site(conn, "https://docs.example/", settings=st)
    assert seen[0].concurrency == 5 and seen[0].per_host_concurrency == 1
    assert not seen[0].respect_robots and len(respx.calls) == 1


@respx.mock
async def test_oversize_streams_are_closed_before_becoming_bookmarks(conn, settings, monkeypatch):
    closed = []

    class LargeStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(10):
                yield b"x" * 2048

        async def aclose(self):
            closed.append(True)

    real_policy = crawl.policy_from_settings
    monkeypatch.setattr(crawl, "policy_from_settings", lambda st: replace(real_policy(st), max_bytes=3000))
    respx.get("https://docs.example/").mock(return_value=httpx.Response(
        200, stream=LargeStream(), headers={"content-type": "text/html"}))
    report = await crawl_site(conn, "https://docs.example/", settings=settings)
    assert report.skipped == 1 and report.inserted == 0 and closed
    assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 0


@respx.mock
async def test_desktop_crawl_keeps_existing_reading_text(conn, settings):
    record = save_bookmark(conn, "https://docs.example/", title="Original saved title", settings=settings)
    bid = record["bookmark_id"]
    store_body(conn, bid, body="My existing saved reading text.", title="Original saved title")
    respx.get("https://docs.example/").mock(return_value=page("New text from the live site."))
    report = await crawl_site(conn, "https://docs.example/", settings=settings, keep_existing=True)
    assert report.already_known == 1 and report.bodies_stored == 0
    assert conn.execute("SELECT body_text FROM content WHERE bookmark_id=?", (bid,)).fetchone()[0] == "My existing saved reading text."
    assert conn.execute("SELECT title FROM bookmark WHERE id=?", (bid,)).fetchone()[0] == "Original saved title"


async def test_cancelling_a_batch_joins_all_children_before_returning(conn, settings, monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()
    count, stopped = 0, []

    async def read(_client, url, *_args, **_kwargs):
        nonlocal count
        if url.endswith("/"):
            return url, 200, '<html><body><a href="/a">A</a><a href="/b">B</a></body></html>'
        count += 1
        if count == 2:
            started.set()
        try:
            await release.wait()
        finally:
            stopped.append(url)

    monkeypatch.setattr(crawl, "_read_html", read)
    task = asyncio.create_task(crawl_site(conn, "https://docs.example/", settings=settings))
    try:
        await asyncio.wait_for(started.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(stopped) == 2
        assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 1
    finally:
        release.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_cancelled_host_spacing_wait_releases_the_acquired_slot(monkeypatch):
    limiter = _HostLimiter(FetchPolicy(per_host_concurrency=1, per_host_min_interval_s=30))
    first = await limiter.acquire("docs.example")
    first.release()
    waiting = asyncio.Event()
    original_sleep = asyncio.sleep

    async def sleep(_delay):
        waiting.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(crawl.asyncio, "sleep", sleep)
    task = asyncio.create_task(limiter.acquire("docs.example"))
    await asyncio.wait_for(waiting.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    monkeypatch.setattr(crawl.asyncio, "sleep", original_sleep)
    limiter._next_ok["docs.example"] = 0
    slot = await asyncio.wait_for(limiter.acquire("docs.example"), 1)
    slot.release()


async def test_runner_stop_and_restart_preserve_successful_pages(settings, monkeypatch):
    database = open_db(settings.db_path)
    database.close()
    entered = asyncio.Event()
    joined = []

    async def fake(conn, start_url, **options):
        save_bookmark(conn, start_url, title="Imported before stop", settings=settings)
        report = crawl.CrawlReport(start_url, pages_attempted=1, pages_fetched=1, inserted=1)
        options["on_progress"](report)
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            joined.append(conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0])

    monkeypatch.setattr(crawl_jobs, "crawl_site", fake)
    runner = CrawlRunner(settings.data_dir)
    runner.start(CrawlRequest(start_url="https://docs.example/"), settings)
    await asyncio.wait_for(entered.wait(), 2)
    result = await runner.cancel()
    assert result["state"] == "cancelled" and result["report"]["inserted"] == 1 and joined == [1]
    assert not runner.running and result["retryable"]
    assert CrawlRunner(settings.data_dir).current()["report"]["inserted"] == 1
    conn = open_db(settings.db_path)
    assert conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 1
    conn.close()


def test_crawl_request_has_a_real_bound_and_rejects_credentials():
    for values in ({"max_pages": 0}, {"max_pages": 501}, {"start_url": "file:///tmp/bookmarks"},
                   {"start_url": "https://a:b@docs.example/"}, {"start_url": "https://docs.example:99999/"}):
        with pytest.raises(ValidationError):
            CrawlRequest.model_validate({"start_url": "https://docs.example/", **values})


def test_desktop_import_status_survives_navigation_and_blocks_conflicting_changes(settings, monkeypatch):
    async def fake(conn, start_url, **options):
        save_bookmark(conn, start_url, title="Synthetic imported page", settings=settings)
        options["on_progress"](crawl.CrawlReport(start_url, pages_attempted=1, pages_fetched=1, inserted=1))
        await asyncio.Event().wait()

    monkeypatch.setattr(crawl_jobs, "crawl_site", fake)
    with TestClient(create_app(settings), client=("127.0.0.1", 40000)) as client:
        assert client.get("/admin/crawl").status_code == 401
        client.headers["Authorization"] = "Bearer " + client.app.state.fm.token
        result = client.post("/admin/crawl", json={"start_url": "https://docs.example/"})
        assert result.status_code == 200 and result.json()["state"] == "running"
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not client.get("/admin/crawl").json()["report"]["inserted"]:
            time.sleep(0.01)
        assert client.get("/bookmarks").status_code == 200
        assert client.get("/admin/crawl").json()["report"]["inserted"] == 1
        assert client.post("/admin/crawl", json={"start_url": "https://docs.example/"}).status_code == 409
        assert client.post("/admin/jobs/start", json={"mode": "fetch", "fetch": True}).status_code == 409
        assert client.put("/admin/settings", json={"values": {"fetch_concurrency": 3}}).status_code == 409
        assert client.post("/admin/library/bookmarks", json={"url": "https://docs.example/new", "title": "New"}).status_code == 409
        stopped = client.post("/admin/crawl/cancel", json={}).json()
        assert stopped["state"] == "cancelled" and stopped["report"]["inserted"] == 1
        assert client.put("/admin/settings", json={"values": {"fetch_concurrency": 3}}).status_code == 200
