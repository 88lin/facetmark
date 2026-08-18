"""Channel A, extraction, and the channel-B handoff.

Every HTTP call in this file is stubbed with respx. That is not only for speed:
the calibration library belongs to a real person, and nothing in this test suite
is allowed to touch a host it names.
"""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest
import respx

from facetmark.db import now, open_db
from facetmark.fetch import (
    DEFER_TO_BROWSER,
    Extraction,
    FetchPolicy,
    Verdict,
    complete_browser_item,
    crawl,
    enqueue_for_browser,
    extract,
    fetch_many,
    fetch_one,
    html_title,
    lease_browser_batch,
    looks_like_wall,
    meta_description,
    pending_targets,
    queue_stats,
    queue_waiting,
    save_result,
    store_body,
)
from facetmark.fetch.client import SMALL_DOC_BYTES, _classify_exception, _verdict_for_status
from facetmark.fetch.extract import MIN_USEFUL_CHARS
from facetmark.fetch.robots import RobotsCache
from facetmark.fetch.store import (
    BROWSER_RETRY_BACKOFF_S,
    LEASE_TTL_S,
    MAX_BROWSER_ATTEMPTS,
    retry_delay_s,
)
from facetmark.importers import import_bookmarks


def extract_mod():
    """The package re-exports ``extract`` as a function, which shadows the
    submodule of the same name; reach it explicitly."""
    import importlib

    return importlib.import_module("facetmark.fetch.extract")

PROSE = (
    "Retrieval augmented generation stitches a retriever onto a generator so that "
    "the model can cite something other than its own weights. The interesting part "
    "is not the generator; it is what the retriever was asked to index in the first "
    "place, because an index answers only the questions its keys were built for. "
    "This paragraph exists to be comfortably longer than the minimum useful length."
)


def article_html(body: str = PROSE, title: str = "On Retrieval") -> str:
    paras = "\n".join(f"<p>{body}</p>" for _ in range(3))
    return f"""<!doctype html><html><head><title>{title}</title>
    <meta name="description" content="A short description."></head>
    <body><nav>Home About</nav><article><h1>{title}</h1>{paras}</article>
    <footer>(c) 2026</footer></body></html>"""


# ---------------------------------------------------------------------------
# extraction tiers
# ---------------------------------------------------------------------------


class TestExtractionTiers:
    def test_a_normal_article_is_extracted_and_labelled(self):
        ex = extract(article_html(), url="https://example.com/a")
        assert ex.ok
        assert ex.extractor in {"trafilatura", "readability"}
        assert "retriever" in ex.text.lower()
        assert ex.title == "On Retrieval"

    def test_empty_html_yields_the_none_extractor_not_a_crash(self):
        ex = extract("", url="https://example.com/x", title_hint="Fallback")
        assert (ex.text, ex.extractor, ex.title) == ("", "none", "Fallback")
        assert not ex.ok

    def test_when_no_tier_finds_prose_metadata_still_reaches_the_index(self):
        # A page with a title and a description but no body. Returning nothing
        # here would silently drop the bookmark out of the content facet.
        html = (
            '<html><head><title>Tiny Page</title>'
            '<meta property="og:description" content="Only a description lives here.">'
            "</head><body><div></div></body></html>"
        )
        ex = extract(html, url="https://example.com/tiny")
        assert ex.extractor == "metadata"
        assert "Only a description" in ex.text
        assert ex.title == "Tiny Page"
        # Below MIN_USEFUL_CHARS, so `ok` is honest about it.
        assert not ex.ok

    def test_readability_catches_what_trafilatura_declines_to_guess(self, monkeypatch):
        mod = extract_mod()

        monkeypatch.setattr(mod, "_try_trafilatura", lambda html, url: "")
        ex = extract(article_html(), url="https://example.com/a")
        assert ex.extractor == "readability"
        assert len(ex.text) >= MIN_USEFUL_CHARS

    def test_last_resort_is_metadata_when_both_parsers_are_unavailable(self, monkeypatch):
        mod = extract_mod()

        monkeypatch.setattr(mod, "_try_trafilatura", lambda html, url: "")
        monkeypatch.setattr(mod, "_try_readability", lambda html: "")
        ex = extract(article_html(), url="https://example.com/a")
        assert ex.extractor == "metadata"
        assert "On Retrieval" in ex.text

    def test_a_parser_that_raises_is_a_tier_failure_not_a_fetch_failure(self, monkeypatch):
        mod = extract_mod()

        def boom(*a, **k):
            raise ValueError("malformed")

        monkeypatch.setattr(mod, "_try_readability", boom)
        ex = extract(article_html(), url="https://example.com/a")
        assert ex.extractor == "trafilatura"  # tier 1 still succeeded

    def test_short_body_beats_metadata_when_it_is_longer(self, monkeypatch):
        mod = extract_mod()

        monkeypatch.setattr(mod, "_try_trafilatura",
                            lambda html, url: "x" * (MIN_USEFUL_CHARS - 1))
        monkeypatch.setattr(mod, "_try_readability", lambda html: "")
        ex = extract(article_html(), url="https://example.com/a")
        assert ex.extractor == "trafilatura"
        assert len(ex.text) == MIN_USEFUL_CHARS - 1
        assert not ex.ok


class TestTitleAndMeta:
    def test_title_is_unescaped_and_whitespace_collapsed(self):
        assert html_title("<title>A &amp;  B</title>") == "A & B"

    def test_missing_title_is_empty_not_none(self):
        assert html_title("<html><body>x</body></html>") == ""

    @pytest.mark.parametrize(
        "html",
        [
            '<meta name="description" content="Hello there">',
            '<meta property="og:description" content="Hello there">',
            '<meta content="Hello there" name="description">',  # reversed attribute order
        ],
    )
    def test_description_is_found_regardless_of_attribute_order(self, html):
        assert meta_description(html) == "Hello there"


class TestWallDetection:
    @pytest.mark.parametrize(
        "marker",
        ["Just a moment...", "Verify you are human", "人机验证", "请登录", "Enable JavaScript"],
    )
    def test_known_gate_phrases_are_walls(self, marker):
        assert looks_like_wall(f"<html><body>{marker}</body></html>", marker)

    def test_a_large_document_yielding_no_text_is_a_client_rendered_shell(self):
        shell = "<html><body><div id='root'></div>" + ("<script>x=1;</script>" * 3000) + "</body></html>"
        assert len(shell) > 30_000
        assert looks_like_wall(shell, "")

    def test_a_small_document_yielding_no_text_is_just_small(self):
        assert not looks_like_wall("<html><body></body></html>", "")

    def test_a_real_article_is_not_a_wall(self):
        html = article_html()
        assert not looks_like_wall(html, extract(html).text)

    def test_a_wall_marker_only_in_noscript_still_counts(self):
        # Extraction throws <noscript> away, so checking the body alone would
        # miss exactly the pages this is meant to catch.
        html = "<html><body><noscript>Please enable JavaScript</noscript>" + \
               f"<article><p>{PROSE}</p></article></body></html>"
        ex = extract(html, url="https://example.com/n")
        assert "enable javascript" not in ex.text.lower()
        assert looks_like_wall(html, ex.text)


# ---------------------------------------------------------------------------
# verdict mapping
# ---------------------------------------------------------------------------


class TestVerdictMapping:
    @pytest.mark.parametrize(
        "status,expected",
        [
            (200, None), (204, None), (301, None),
            (401, Verdict.REFUSED), (403, Verdict.REFUSED), (429, Verdict.REFUSED),
            (404, Verdict.NOT_FOUND), (410, Verdict.NOT_FOUND),
            (400, Verdict.REFUSED), (418, Verdict.REFUSED),
            (500, Verdict.SERVER_ERROR), (503, Verdict.SERVER_ERROR),
        ],
    )
    def test_status_codes_map_to_verdicts(self, status, expected):
        assert _verdict_for_status(status) is expected

    def test_dns_failure_is_distinguished_from_a_dead_host(self):
        dns = httpx.ConnectError("[Errno -2] Name or service not known")
        refused = httpx.ConnectError("[Errno 111] Connection refused")
        assert _classify_exception(dns)[0] is Verdict.DNS_FAIL
        assert _classify_exception(refused)[0] is Verdict.UNREACHABLE

    def test_timeouts_and_redirect_loops_are_unreachable(self):
        assert _classify_exception(httpx.ReadTimeout("slow"))[0] is Verdict.UNREACHABLE
        assert _classify_exception(httpx.TooManyRedirects("loop"))[0] is Verdict.UNREACHABLE

    def test_only_recoverable_verdicts_defer_to_the_browser(self):
        # 404 must NOT go to the browser: a real 404 in a real tab is still 404,
        # and queueing it would waste the user's own bandwidth on a dead link.
        assert Verdict.NOT_FOUND not in DEFER_TO_BROWSER
        assert Verdict.DNS_FAIL not in DEFER_TO_BROWSER
        assert {Verdict.REFUSED, Verdict.WALL, Verdict.EMPTY, Verdict.SKIPPED} == set(
            DEFER_TO_BROWSER
        )


# ---------------------------------------------------------------------------
# channel A over stubbed HTTP
# ---------------------------------------------------------------------------


async def _one(url: str, **kw):
    async with httpx.AsyncClient(follow_redirects=True) as cl:
        return await fetch_one(cl, url, **kw)


class TestFetchOne:
    @respx.mock
    async def test_a_good_page_comes_back_ok_with_a_body(self):
        respx.get("https://example.com/a").mock(
            return_value=httpx.Response(200, html=article_html())
        )
        r = await _one("https://example.com/a")
        assert r.verdict is Verdict.OK
        assert r.http_status == 200
        assert "retriever" in r.body.lower()
        assert r.title == "On Retrieval"
        assert not r.should_defer_to_browser

    @respx.mock
    async def test_a_bot_check_is_a_wall_and_defers(self):
        respx.get("https://example.com/cf").mock(
            return_value=httpx.Response(200, html="<html><body>Just a moment...</body></html>")
        )
        r = await _one("https://example.com/cf")
        assert r.verdict is Verdict.WALL
        assert r.should_defer_to_browser

    @respx.mock
    async def test_403_defers_and_is_never_retried_into_submission(self):
        route = respx.get("https://example.com/paywall").mock(
            return_value=httpx.Response(403)
        )
        r = await _one("https://example.com/paywall")
        assert r.verdict is Verdict.REFUSED
        assert r.should_defer_to_browser
        assert route.call_count == 1

    @respx.mock
    async def test_404_is_not_found_and_does_not_defer(self):
        respx.get("https://example.com/gone").mock(return_value=httpx.Response(404))
        r = await _one("https://example.com/gone")
        assert r.verdict is Verdict.NOT_FOUND
        assert not r.should_defer_to_browser

    @respx.mock
    async def test_a_pdf_is_not_html(self):
        respx.get("https://example.com/p.pdf").mock(
            return_value=httpx.Response(200, content=b"%PDF-1.7",
                                        headers={"content-type": "application/pdf"})
        )
        r = await _one("https://example.com/p.pdf")
        assert r.verdict is Verdict.NOT_HTML

    @respx.mock
    async def test_an_oversized_response_is_a_download_not_an_article(self):
        respx.get("https://example.com/big").mock(
            return_value=httpx.Response(200, content=b"<html>" + b"x" * 5000,
                                        headers={"content-type": "text/html"})
        )
        r = await _one("https://example.com/big", policy=FetchPolicy(max_bytes=1000))
        assert r.verdict is Verdict.TOO_LARGE

    @respx.mock
    async def test_a_server_error_is_kept_apart_from_a_refusal(self):
        respx.get("https://example.com/500").mock(return_value=httpx.Response(503))
        r = await _one("https://example.com/500")
        assert r.verdict is Verdict.SERVER_ERROR
        assert not r.should_defer_to_browser

    @respx.mock
    async def test_a_short_body_from_a_short_document_is_accepted_as_is(self):
        # Found by the P2 smoke test against example.com: a genuinely tiny page
        # was being deferred to the browser forever, where it would produce the
        # same tiny text. Short document + some text = that is the document.
        html = ("<html><head><title>Tiny</title></head><body><p>"
                + "A brief note about nothing much. " * 3 + "</p></body></html>")
        assert len(html) < SMALL_DOC_BYTES
        respx.get("https://example.com/short").mock(return_value=httpx.Response(200, html=html))
        r = await _one("https://example.com/short")
        assert r.verdict is Verdict.OK
        assert 0 < len(r.body) < MIN_USEFUL_CHARS
        assert not r.should_defer_to_browser

    @respx.mock
    async def test_a_thin_body_from_a_fat_document_defers_to_a_real_browser(self):
        html = ("<html><head><title>App</title></head><body><p>hi</p>"
                + "<div class='x'></div>" * 500 + "</body></html>")
        assert len(html) > SMALL_DOC_BYTES
        respx.get("https://example.com/thin").mock(return_value=httpx.Response(200, html=html))
        r = await _one("https://example.com/thin")
        assert r.verdict is Verdict.EMPTY
        assert r.should_defer_to_browser

    @respx.mock
    async def test_a_short_document_with_no_text_at_all_is_still_empty(self):
        respx.get("https://example.com/void").mock(
            return_value=httpx.Response(200, html="<html><body></body></html>")
        )
        r = await _one("https://example.com/void")
        assert r.verdict is Verdict.EMPTY

    @respx.mock
    async def test_redirects_are_followed_and_the_final_url_is_recorded(self):
        respx.get("https://example.com/old").mock(
            return_value=httpx.Response(301, headers={"location": "https://example.com/new"})
        )
        respx.get("https://example.com/new").mock(
            return_value=httpx.Response(200, html=article_html())
        )
        r = await _one("https://example.com/old")
        assert r.verdict is Verdict.OK
        assert r.final_url == "https://example.com/new"

    @respx.mock
    async def test_a_transport_error_becomes_a_verdict_not_an_exception(self):
        respx.get("https://nowhere.invalid/x").mock(
            side_effect=httpx.ConnectError("Name or service not known")
        )
        r = await _one("https://nowhere.invalid/x")
        assert r.verdict is Verdict.DNS_FAIL
        assert r.error

    async def test_non_http_schemes_are_skipped_without_a_request(self):
        for url in ("javascript:void(0)", "chrome://bookmarks", "data:text/html,x", "file:///c:/x"):
            r = await _one(url)
            assert r.verdict is Verdict.SKIPPED

    async def test_known_client_rendered_hosts_are_skipped_before_the_request(self):
        r = await _one("https://x.com/someone/status/1")
        assert r.verdict is Verdict.SKIPPED
        assert r.should_defer_to_browser  # the extension can still read it

    @respx.mock
    async def test_the_spa_skip_can_be_turned_off(self):
        respx.get("https://x.com/a").mock(return_value=httpx.Response(200, html=article_html()))
        r = await _one("https://x.com/a", policy=FetchPolicy(skip_spa_hosts=False))
        assert r.verdict is Verdict.OK


class TestFetchMany:
    @respx.mock
    async def test_results_come_back_in_input_order(self):
        urls = [f"https://example.com/{i}" for i in range(12)]
        for i, u in enumerate(urls):
            respx.get(u).mock(
                return_value=httpx.Response(200, html=article_html(title=f"Doc {i}"))
            )
        batch = await fetch_many(urls, policy=FetchPolicy(per_host_min_interval_s=0.0))
        assert [r.url for r in batch.results] == urls
        assert [r.title for r in batch.results] == [f"Doc {i}" for i in range(12)]

    @respx.mock
    async def test_the_batch_summary_counts_every_verdict(self):
        respx.get("https://example.com/ok").mock(
            return_value=httpx.Response(200, html=article_html()))
        respx.get("https://example.com/no").mock(return_value=httpx.Response(404))
        respx.get("https://example.com/403").mock(return_value=httpx.Response(403))
        batch = await fetch_many(
            ["https://example.com/ok", "https://example.com/no", "https://example.com/403"],
            policy=FetchPolicy(per_host_min_interval_s=0.0),
        )
        assert batch.by_verdict() == {"ok": 1, "not_found": 1, "refused": 1}
        assert len(batch.ok) == 1
        assert [r.url for r in batch.deferred] == ["https://example.com/403"]

    @respx.mock
    async def test_one_failure_does_not_take_down_the_batch(self):
        respx.get("https://a.example/1").mock(side_effect=httpx.ReadTimeout("slow"))
        respx.get("https://b.example/1").mock(
            return_value=httpx.Response(200, html=article_html()))
        batch = await fetch_many(["https://a.example/1", "https://b.example/1"],
                                 policy=FetchPolicy(per_host_min_interval_s=0.0))
        assert [r.verdict for r in batch.results] == [Verdict.UNREACHABLE, Verdict.OK]

    @respx.mock
    async def test_an_empty_input_is_not_an_error(self):
        batch = await fetch_many([])
        assert batch.results == [] and batch.by_verdict() == {}


class TestPoliteness:
    """The limits are the point of channel A. A crawler that ignores them gets
    the user's home IP blocked, which is a worse outcome than a slow index."""

    @respx.mock
    async def test_requests_to_one_host_are_spaced_apart(self):
        """The one ``/robots.txt`` read per host is exempt: it happens once,
        before the host limiter exists for that host, and it is the request the
        host asked us to make."""
        stamps: list[float] = []
        robots_hits = 0

        def handler(request):
            nonlocal robots_hits
            if request.url.path == "/robots.txt":
                robots_hits += 1
                return httpx.Response(404)
            stamps.append(time.monotonic())
            return httpx.Response(200, html=article_html())

        respx.get(url__startswith="https://slow.example/").mock(side_effect=handler)
        urls = [f"https://slow.example/{i}" for i in range(4)]
        await fetch_many(urls, policy=FetchPolicy(per_host_min_interval_s=0.05,
                                                  per_host_concurrency=1))
        assert robots_hits == 1, robots_hits
        # The limiter *reserves* evenly spaced slots and each request sleeps
        # until its own slot. A stopwatch inside the handler therefore also
        # measures however long the event loop was busy elsewhere, so on a
        # loaded machine one gap can come in short without the host having been
        # treated rudely -- the following request is still pinned to its
        # original reservation. Assert the contract that actually matters: the
        # i-th request does not start before i intervals have passed. The loose
        # per-gap floor stays, to catch a limiter that has stopped spacing at
        # all rather than one that merely jittered. The floor is 0.01, not
        # 0.02, because Windows' default timer resolution is ~15 ms and a real
        # 0.05 s gap can measure as 0.015 s there.
        assert len(stamps) == 4, stamps
        elapsed = [t - stamps[0] for t in stamps]
        for i, t in enumerate(elapsed):
            assert t >= i * 0.05 - 0.02, (i, elapsed)
        gaps = [b - a for a, b in zip(stamps, stamps[1:], strict=False)]
        assert all(g >= 0.01 for g in gaps), gaps

    @respx.mock
    async def test_never_more_than_the_allowed_requests_in_flight_per_host(self):
        live = 0
        peak = 0

        async def handler(request):
            nonlocal live, peak
            live += 1
            peak = max(peak, live)
            await asyncio.sleep(0.02)
            live -= 1
            return httpx.Response(200, html=article_html())

        respx.get(url__startswith="https://busy.example/").mock(side_effect=handler)
        await fetch_many(
            [f"https://busy.example/{i}" for i in range(8)],
            policy=FetchPolicy(per_host_concurrency=2, per_host_min_interval_s=0.0,
                               concurrency=8),
        )
        assert peak <= 2, peak

    @respx.mock
    async def test_different_hosts_are_not_serialised_against_each_other(self):
        async def handler(request):
            await asyncio.sleep(0.05)
            return httpx.Response(200, html=article_html())

        for i in range(6):
            respx.get(f"https://h{i}.example/p").mock(side_effect=handler)
        urls = [f"https://h{i}.example/p" for i in range(6)]

        t0 = time.monotonic()
        await fetch_many(urls, policy=FetchPolicy(concurrency=6,
                                                  per_host_min_interval_s=0.0))
        parallel = time.monotonic() - t0

        t0 = time.monotonic()
        await fetch_many(urls, policy=FetchPolicy(concurrency=1,
                                                  per_host_min_interval_s=0.0))
        serial = time.monotonic() - t0

        # An absolute bound would only measure the runner. What matters is that
        # six hosts overlap: the parallel pass must be well under the serial one.
        assert parallel < serial * 0.7, (parallel, serial)


# ---------------------------------------------------------------------------
# persistence + channel B handoff
# ---------------------------------------------------------------------------


@pytest.fixture
def db(conn):
    from tests.conftest import NETSCAPE_SAMPLE

    import_bookmarks(conn, content=NETSCAPE_SAMPLE)
    return conn


def _first_id(conn) -> int:
    return conn.execute("SELECT id FROM bookmark ORDER BY id LIMIT 1").fetchone()["id"]


class TestStoreBody:
    def test_a_stored_body_is_immediately_searchable_in_both_indexes(self, db):
        bid = _first_id(db)
        store_body(db, bid, body=PROSE, title="On Retrieval", extractor="trafilatura")
        row = db.execute("SELECT * FROM content WHERE bookmark_id=?", (bid,)).fetchone()
        assert row["char_count"] == len(PROSE)
        assert row["body_hash"] and row["body_seg"]
        for table, q in (("fts_tri", "retriever"), ("fts_seg", "retriever")):
            n = db.execute(f"SELECT COUNT(*) c FROM {table} WHERE {table} MATCH ?",
                           (q,)).fetchone()["c"]
            assert n == 1, table

    def test_refetching_unchanged_text_reports_no_change(self, db):
        bid = _first_id(db)
        first = store_body(db, bid, body=PROSE)
        again = store_body(db, bid, body=PROSE)
        assert first.changed is True and again.changed is False
        assert first.body_hash == again.body_hash

    def test_a_ticking_render_timestamp_is_not_a_content_change(self, db):
        # The same article, re-fetched a day later. Only the whitespace and the
        # rendered "last updated" clock moved. Treating that as a change would
        # re-run a paid enrichment on every crawl of every dynamic page.
        bid = _first_id(db)
        store_body(db, bid, body=PROSE + "\nLast updated 2026-08-01 10:23:45\n")
        later = PROSE.replace(" ", "  ") + "\nLast updated 2026-08-02 18:00:01\n"
        assert store_body(db, bid, body=later).changed is False

    def test_real_edits_do_count_as_a_change(self, db):
        bid = _first_id(db)
        store_body(db, bid, body=PROSE)
        assert store_body(db, bid, body=PROSE + " A new paragraph appeared.").changed is True

    def test_a_failure_never_destroys_a_body_we_already_have(self, db):
        bid = _first_id(db)
        store_body(db, bid, body=PROSE)
        from facetmark.fetch.client import FetchResult

        save_result(db, bid, FetchResult(url="u", verdict=Verdict.REFUSED, http_status=403))
        row = db.execute("SELECT body_text, error, http_status FROM content WHERE bookmark_id=?",
                         (bid,)).fetchone()
        assert row["body_text"] == PROSE
        assert row["http_status"] == 403 and row["error"]


class TestPendingTargets:
    def test_only_indexable_bookmarks_are_offered(self, db):
        urls = {u for _, u, _ in pending_targets(db)}
        assert all(u.startswith(("http://", "https://")) for u in urls)
        n_index = db.execute("SELECT COUNT(*) c FROM bookmark WHERE indexable=1").fetchone()["c"]
        assert len(urls) == n_index

    def test_a_privacy_excluded_bookmark_is_never_even_requested(self, db):
        bid = _first_id(db)
        db.execute("UPDATE bookmark SET privacy_skipped=1 WHERE id=?", (bid,))
        assert bid not in {i for i, _, _ in pending_targets(db)}

    def test_already_fetched_pages_are_skipped_unless_refetch_is_asked_for(self, db):
        bid = _first_id(db)
        store_body(db, bid, body=PROSE)
        assert bid not in {i for i, _, _ in pending_targets(db)}
        assert bid in {i for i, _, _ in pending_targets(db, refetch=True)}

    def test_a_failed_fetch_is_still_pending_because_no_body_was_stored(self, db):
        bid = _first_id(db)
        from facetmark.fetch.client import FetchResult

        save_result(db, bid, FetchResult(url="u", verdict=Verdict.SERVER_ERROR))
        assert bid in {i for i, _, _ in pending_targets(db)}

    def test_an_explicit_id_list_narrows_the_set(self, db):
        ids = [i for i, _, _ in pending_targets(db)]
        assert [i for i, _, _ in pending_targets(db, ids=ids[:2])] == ids[:2]
        assert pending_targets(db, ids=[]) == []


class TestBrowserQueue:
    def test_a_deferred_verdict_lands_in_the_queue(self, db):
        bid = _first_id(db)
        from facetmark.fetch.client import FetchResult

        out = save_result(db, bid, FetchResult(url="u", verdict=Verdict.WALL))
        assert out.queued_for_browser
        assert queue_stats(db) == {"pending": 1}

    def test_a_terminal_verdict_does_not(self, db):
        bid = _first_id(db)
        from facetmark.fetch.client import FetchResult

        out = save_result(db, bid, FetchResult(url="u", verdict=Verdict.NOT_FOUND))
        assert not out.queued_for_browser
        assert queue_stats(db) == {}

    def test_leasing_hands_out_work_and_marks_it_taken(self, db):
        ids = [i for i, _, _ in pending_targets(db)][:3]
        for i in ids:
            enqueue_for_browser(db, i, reason="wall")
        batch = lease_browser_batch(db, 2)
        assert len(batch) == 2
        assert all(item["url"].startswith("http") for item in batch)
        assert queue_stats(db) == {"leased": 2, "pending": 1}
        # A second poll does not hand out the same work twice.
        assert [b["bookmark_id"] for b in lease_browser_batch(db, 2)] == [ids[2]]

    def test_an_expired_lease_is_reclaimed_so_a_dead_tab_strands_nothing(self, db):
        bid = _first_id(db)
        enqueue_for_browser(db, bid, reason="wall")
        lease_browser_batch(db, 1)
        assert queue_stats(db) == {"leased": 1}
        db.execute("UPDATE fetch_queue SET leased_at = leased_at - ?", (LEASE_TTL_S + 60,))
        assert [b["bookmark_id"] for b in lease_browser_batch(db, 1)] == [bid]

    def test_a_body_from_the_extension_completes_the_item(self, db):
        bid = _first_id(db)
        enqueue_for_browser(db, bid, reason="refused")
        lease_browser_batch(db, 1)
        out = complete_browser_item(db, bid, body=PROSE, title="From a real tab")
        assert out.stored and out.changed
        assert queue_stats(db) == {"done": 1}
        row = db.execute("SELECT extractor, fetch_channel FROM content WHERE bookmark_id=?",
                         (bid,)).fetchone()
        assert (row["extractor"], row["fetch_channel"]) == ("extension", "b")

    def test_repeated_extension_failures_park_the_item_instead_of_looping(self, db):
        bid = _first_id(db)
        enqueue_for_browser(db, bid, reason="wall")
        for _ in range(MAX_BROWSER_ATTEMPTS):
            assert lease_browser_batch(db, 1), "the backoff should have expired by now"
            complete_browser_item(db, bid, body="", error="tab closed")
            _end_the_wait(db, bid)
        assert queue_stats(db) == {"failed": 1}
        assert lease_browser_batch(db, 5) == []
        # And it stays parked rather than being silently re-queued.
        assert enqueue_for_browser(db, bid, reason="wall") is False

    def test_privacy_excluded_bookmarks_are_never_leased_to_the_extension(self, db):
        bid = _first_id(db)
        enqueue_for_browser(db, bid, reason="wall")
        db.execute("UPDATE bookmark SET privacy_skipped=1 WHERE id=?", (bid,))
        assert lease_browser_batch(db, 5) == []


class TestCrawl:
    @respx.mock
    async def test_end_to_end_a_crawl_stores_indexes_and_queues(self, db):
        targets = pending_targets(db)
        assert targets
        for n, (_bid, url, _t) in enumerate(targets):
            if n == 0:
                respx.get(url).mock(return_value=httpx.Response(403))
            else:
                respx.get(url).mock(
                    return_value=httpx.Response(200, html=article_html(title=f"Doc {n}")))
        rep = await crawl(db, policy=FetchPolicy(per_host_min_interval_s=0.0))
        assert rep.attempted == len(targets)
        assert rep.stored == len(targets) - 1
        assert rep.changed == rep.stored
        assert rep.queued == 1
        assert rep.as_dict()["by_verdict"] == {"ok": len(targets) - 1, "refused": 1}
        hits = db.execute(
            "SELECT COUNT(*) c FROM fts_seg WHERE fts_seg MATCH ?", ("retriever",)
        ).fetchone()["c"]
        assert hits == len(targets) - 1

    @respx.mock
    async def test_a_second_crawl_re_fetches_nothing(self, db):
        for _bid, url, _t in pending_targets(db):
            respx.get(url).mock(return_value=httpx.Response(200, html=article_html()))
        await crawl(db, policy=FetchPolicy(per_host_min_interval_s=0.0))
        rep = await crawl(db, policy=FetchPolicy(per_host_min_interval_s=0.0))
        assert rep.attempted == 0 and rep.as_dict()["by_verdict"] == {}

    @respx.mock
    async def test_progress_is_reported_per_url_so_a_ui_can_show_a_bar(self, db):
        seen = []
        for _bid, url, _t in pending_targets(db):
            respx.get(url).mock(return_value=httpx.Response(200, html=article_html()))
        await crawl(db, policy=FetchPolicy(per_host_min_interval_s=0.0),
                    progress=seen.append)
        assert len(seen) == len(db.execute(
            "SELECT id FROM bookmark WHERE indexable=1").fetchall())

    async def test_crawling_an_empty_pending_set_is_a_no_op(self):
        empty = open_db(":memory:")
        rep = await crawl(empty)
        assert rep.as_dict() == {"attempted": 0, "stored": 0, "changed": 0,
                                 "queued_for_browser": 0, "by_verdict": {}}


class _Interrupted(Exception):
    """Stands in for a Ctrl-C, without asking pytest to abort the session."""


class TestCrawlPersistsAsItGoes:
    """A crawl that dies at 95% must keep the 95%.

    Fetching a real library is tens of minutes of somebody else's bandwidth.
    Holding every body in memory until the last request returns means one
    Ctrl-C, one OOM, or one unhandled error costs the whole run and re-spends
    every one of those requests on the next attempt.
    """

    def _stored(self, db) -> int:
        return db.execute(
            "SELECT COUNT(*) c FROM content WHERE body_hash IS NOT NULL"
        ).fetchone()["c"]

    @respx.mock
    async def test_each_body_is_committed_before_the_next_one_arrives(self, db):
        targets = pending_targets(db)
        for n, (_bid, url, _t) in enumerate(targets):
            respx.get(url).mock(
                return_value=httpx.Response(200, html=article_html(title=f"Doc {n}")))
        counts: list[int] = []
        open_txn: list[bool] = []

        def watch(_res) -> None:
            counts.append(self._stored(db))
            open_txn.append(db.in_transaction)

        await crawl(db, policy=FetchPolicy(per_host_min_interval_s=0.0), progress=watch)
        # The old code wrote nothing until the batch was complete, which made
        # this list all zeroes.
        assert counts == list(range(1, len(targets) + 1))
        # And each row is committed, not merely written: a crash one page later
        # cannot take it back.
        assert open_txn == [False] * len(targets)

    async def test_an_interrupted_crawl_keeps_what_already_landed(self, tmp_path):
        path = tmp_path / "library.db"
        disk = open_db(path)
        from tests.conftest import NETSCAPE_SAMPLE

        import_bookmarks(disk, content=NETSCAPE_SAMPLE)
        targets = pending_targets(disk)
        assert len(targets) >= 3
        seen = 0

        def die_partway(_res) -> None:
            nonlocal seen
            seen += 1
            if seen == 2:
                raise _Interrupted("user gave up")

        with respx.mock:
            for _bid, url, _t in targets:
                respx.get(url).mock(return_value=httpx.Response(200, html=article_html()))
            with pytest.raises(_Interrupted):
                await crawl(disk, policy=FetchPolicy(concurrency=1,
                                                     per_host_min_interval_s=0.0),
                            progress=die_partway)
        disk.close()

        # Reopened from the file, so this is what actually survived the process.
        reopened = open_db(path)
        landed = self._stored(reopened)
        assert landed >= 2
        assert len(pending_targets(reopened)) == len(targets) - landed

        with respx.mock:
            for _bid, url, _t in targets:
                respx.get(url).mock(return_value=httpx.Response(200, html=article_html()))
            rep = await crawl(reopened, policy=FetchPolicy(per_host_min_interval_s=0.0))
        assert rep.attempted == len(targets) - landed
        assert self._stored(reopened) == len(targets)
        reopened.close()

    @respx.mock
    async def test_a_failure_mid_batch_still_counts_and_still_queues(self, db):
        targets = pending_targets(db)
        for n, (_bid, url, _t) in enumerate(targets):
            respx.get(url).mock(return_value=httpx.Response(403) if n == 1
                                else httpx.Response(200, html=article_html()))
        rep = await crawl(db, policy=FetchPolicy(per_host_min_interval_s=0.0))
        # Per-result accounting has to agree with the whole-batch tally it
        # replaced: results arrive out of order, ids are matched by URL.
        assert rep.stored == len(targets) - 1
        assert rep.queued == 1
        assert rep.as_dict()["by_verdict"] == {"ok": len(targets) - 1, "refused": 1}
        assert self._stored(db) == len(targets) - 1


class TestExtractionDataclass:
    def test_ok_requires_both_length_and_not_being_a_wall(self):
        assert Extraction("x" * MIN_USEFUL_CHARS, "t", "trafilatura").ok
        assert not Extraction("x" * (MIN_USEFUL_CHARS - 1), "t", "trafilatura").ok
        assert not Extraction("x" * MIN_USEFUL_CHARS, "t", "trafilatura", True).ok


def _end_the_wait(db, bookmark_id: int) -> None:
    """Pretend the backoff deadline has passed, without sleeping through it."""
    db.execute("UPDATE fetch_queue SET next_attempt_at=NULL WHERE bookmark_id=?", (bookmark_id,))


def _retry_at(db, bookmark_id: int) -> int | None:
    row = db.execute(
        "SELECT next_attempt_at FROM fetch_queue WHERE bookmark_id=?", (bookmark_id,)
    ).fetchone()
    return row["next_attempt_at"]


class TestBrowserQueueBackoff:
    """A failed item waits before it is offered again.

    The extension polls; without a deadline an item that failed because the host
    was rate-limiting would burn all three of its attempts inside a minute and
    be parked for a reason that would have cleared on its own.
    """

    def _queued(self, db) -> int:
        bid = _first_id(db)
        enqueue_for_browser(db, bid, reason="wall")
        return bid

    def test_a_failure_is_not_handed_straight_back(self, db):
        bid = self._queued(db)
        lease_browser_batch(db, 1)
        complete_browser_item(db, bid, body="", error="tab closed")
        assert queue_stats(db) == {"pending": 1}  # still live, just not yet
        assert lease_browser_batch(db, 5) == []

    def test_it_comes_back_once_the_wait_is_over(self, db):
        bid = self._queued(db)
        lease_browser_batch(db, 1)
        complete_browser_item(db, bid, body="", error="tab closed")
        _end_the_wait(db, bid)
        assert [b["bookmark_id"] for b in lease_browser_batch(db, 5)] == [bid]

    def test_the_wait_gets_longer_with_every_attempt(self, db):
        bid = self._queued(db)
        waits = []
        for _ in range(MAX_BROWSER_ATTEMPTS - 1):
            lease_browser_batch(db, 1)
            before = now()
            complete_browser_item(db, bid, body="", error="tab closed")
            waits.append(_retry_at(db, bid) - before)
            _end_the_wait(db, bid)
        assert waits == list(BROWSER_RETRY_BACKOFF_S[: MAX_BROWSER_ATTEMPTS - 1])
        assert waits == sorted(waits) and waits[0] < waits[-1]

    def test_the_last_wait_is_reused_if_there_are_more_attempts_than_steps(self):
        assert retry_delay_s(len(BROWSER_RETRY_BACKOFF_S) + 3) == BROWSER_RETRY_BACKOFF_S[-1]
        assert retry_delay_s(0) == BROWSER_RETRY_BACKOFF_S[0]

    def test_a_parked_item_is_not_waiting_for_anything(self, db):
        bid = self._queued(db)
        for _ in range(MAX_BROWSER_ATTEMPTS):
            lease_browser_batch(db, 1)
            complete_browser_item(db, bid, body="", error="tab closed")
            _end_the_wait(db, bid)
        assert queue_stats(db) == {"failed": 1}
        assert _retry_at(db, bid) is None
        assert queue_waiting(db) == 0

    def test_waiting_is_counted_apart_from_pending(self, db):
        ids = [i for i, _, _ in pending_targets(db)][:2]
        for i in ids:
            enqueue_for_browser(db, i, reason="wall")
        assert queue_waiting(db) == 0
        lease_browser_batch(db, 1)
        complete_browser_item(db, ids[0], body="", error="tab closed")
        assert queue_stats(db)["pending"] == 2
        assert queue_waiting(db) == 1  # one of the two is serving its wait

    def test_asking_for_it_again_clears_the_wait(self, db):
        bid = self._queued(db)
        lease_browser_batch(db, 1)
        complete_browser_item(db, bid, body="", error="tab closed")
        assert _retry_at(db, bid) is not None
        enqueue_for_browser(db, bid, reason="wall")  # a deliberate re-request
        assert _retry_at(db, bid) is None
        assert [b["bookmark_id"] for b in lease_browser_batch(db, 5)] == [bid]

    def test_a_success_clears_the_wait(self, db):
        bid = self._queued(db)
        lease_browser_batch(db, 1)
        complete_browser_item(db, bid, body="", error="tab closed")
        _end_the_wait(db, bid)
        lease_browser_batch(db, 1)
        complete_browser_item(db, bid, body=PROSE, title="second time lucky")
        assert queue_stats(db) == {"done": 1}
        assert _retry_at(db, bid) is None

    def test_a_dead_tab_is_retried_without_a_wait(self, db):
        """An expired lease says nothing about the host, only about the tab."""
        bid = self._queued(db)
        lease_browser_batch(db, 1)
        db.execute("UPDATE fetch_queue SET leased_at = leased_at - ?", (LEASE_TTL_S + 60,))
        assert [b["bookmark_id"] for b in lease_browser_batch(db, 1)] == [bid]


# ---------------------------------------------------------------------------
# the failure taxonomy a real crawl actually produced
# ---------------------------------------------------------------------------


class TestRealWorldFailureModes:
    """The twelve ways 2,376 real pages failed, pinned as regressions.

    Measured over the W1 corpus: ``HTTP 403`` x104, ``empty`` x62, ``HTTP 404``
    x54, ``wall`` x52, ``HTTP 429`` x26, DNS x20, timeout x18, server
    disconnected x16, client-rendered host x9, TLS verification x8. Each row
    below is one of those, asserted at the level that decides what happens next
    -- the verdict, and whether the browser channel gets a turn.
    """

    @pytest.mark.parametrize(
        "exc,verdict,fragment",
        [
            (httpx.ConnectError("[Errno -2] Name or service not known"),
             Verdict.DNS_FAIL, "name or service"),
            (httpx.ConnectError("[Errno -5] No address associated with hostname"),
             Verdict.UNREACHABLE, "no address"),
            (httpx.ReadTimeout("timed out"), Verdict.UNREACHABLE, "timeout"),
            (httpx.ConnectTimeout("handshake timed out"), Verdict.UNREACHABLE, "timeout"),
            (httpx.RemoteProtocolError("Server disconnected without sending a response."),
             Verdict.UNREACHABLE, "server disconnected"),
            (httpx.ConnectError(
                "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                "unable to get local issuer certificate"),
             Verdict.UNREACHABLE, "certificate verify failed"),
        ],
    )
    @respx.mock
    async def test_a_transport_failure_names_itself_in_the_error(self, exc, verdict, fragment):
        respx.get("https://example.com/x").mock(side_effect=exc)
        r = await _one("https://example.com/x")
        assert r.verdict is verdict
        assert fragment in r.error.lower()

    @pytest.mark.parametrize("status", [403, 429])
    @respx.mock
    async def test_a_rate_limit_or_a_refusal_gets_the_browser_a_turn(self, status):
        respx.get("https://example.com/x").mock(return_value=httpx.Response(status))
        r = await _one("https://example.com/x")
        assert r.verdict is Verdict.REFUSED and r.should_defer_to_browser

    @pytest.mark.parametrize("status", [404, 410, 500, 503])
    @respx.mock
    async def test_a_dead_or_broken_url_does_not_spend_the_users_browser(self, status):
        respx.get("https://example.com/x").mock(return_value=httpx.Response(status))
        r = await _one("https://example.com/x")
        assert not r.should_defer_to_browser

    @respx.mock
    async def test_robots_denial_is_the_one_refusal_the_browser_may_not_undo(self):
        respx.get("https://tidy.example/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /private/\n"))
        r = await _one("https://tidy.example/private/page",
                       policy=FetchPolicy(respect_robots=True),
                       robots=RobotsCache())
        assert r.verdict is Verdict.ROBOTS_DENIED
        assert not r.should_defer_to_browser

    @respx.mock
    async def test_a_client_rendered_host_is_refused_early_but_still_deferred(self):
        r = await _one("https://twitter.com/someone/status/1")
        assert r.verdict is Verdict.SKIPPED and r.should_defer_to_browser
        assert not respx.calls

    @respx.mock
    async def test_an_extractor_crash_becomes_a_verdict_not_an_exception(self, monkeypatch):
        def boom(*a, **k):
            raise RecursionError("maximum recursion depth exceeded")

        monkeypatch.setattr("facetmark.fetch.client.extract", boom)
        respx.get("https://example.com/x").mock(
            return_value=httpx.Response(200, html=article_html()))
        r = await _one("https://example.com/x")
        assert r.verdict is Verdict.EMPTY
        assert "RecursionError" in r.error
        assert r.should_defer_to_browser

    @respx.mock
    async def test_one_pathological_page_does_not_take_the_batch_with_it(self, monkeypatch):
        """`gather` without `return_exceptions` loses every already-fetched
        result in the batch, and breaks the input-order contract `crawl` zips
        bookmark ids against."""
        real = fetch_one

        async def sometimes_explodes(client, url, **kw):
            if url.endswith("/2"):
                raise ValueError("something nobody anticipated")
            return await real(client, url, **kw)

        monkeypatch.setattr("facetmark.fetch.client.fetch_one", sometimes_explodes)
        urls = [f"https://example.com/{i}" for i in range(4)]
        for u in urls:
            respx.get(u).mock(return_value=httpx.Response(200, html=article_html()))
        batch = await fetch_many(urls, policy=FetchPolicy(per_host_min_interval_s=0.0))
        assert [r.url for r in batch.results] == urls
        assert len(batch.ok) == 3
        bad = batch.results[2]
        assert bad.verdict is Verdict.UNREACHABLE and "ValueError" in bad.error

    @respx.mock
    async def test_a_mixed_batch_records_every_failure_and_queues_only_the_winnable(self, db):
        targets = pending_targets(db)
        assert len(targets) >= 5
        plan = [
            httpx.Response(200, html=article_html(title="Good")),
            httpx.Response(403),
            httpx.Response(404),
            httpx.Response(200, html="<html><body><h1>Are you a robot?</h1>"
                                     "<p>Checking your browser.</p></body></html>"),
        ]
        exhausted = httpx.ConnectError("[Errno -2] Name or service not known")
        for n, (_bid, url, _t) in enumerate(targets):
            if n < len(plan):
                respx.get(url).mock(return_value=plan[n])
            else:
                respx.get(url).mock(side_effect=exhausted)

        rep = await crawl(db, policy=FetchPolicy(per_host_min_interval_s=0.0))
        counts = rep.as_dict()["by_verdict"]
        assert counts["ok"] == 1
        assert counts["refused"] == 1
        assert counts["not_found"] == 1
        assert counts["wall"] == 1
        assert counts["dns_fail"] == len(targets) - 4
        assert rep.attempted == len(targets)

        # Every failure leaves a reason on the row, not a blank.
        blank = db.execute(
            "SELECT COUNT(*) c FROM content WHERE COALESCE(error,'')='' "
            "AND COALESCE(char_count,0)=0"
        ).fetchone()["c"]
        assert blank == 0
        # 403 and the wall are winnable in a real tab; 404 and DNS are not.
        assert queue_stats(db)["pending"] == 2
