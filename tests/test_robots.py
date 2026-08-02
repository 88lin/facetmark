"""robots.txt parsing, caching, and the two call sites that honour it.

Every HTTP call is stubbed with respx. The point of this file is that a sweep
over a few thousand hosts asks each one for permission first, once, and then
does what it is told -- including the awkward cases where what it is told is
ambiguous.
"""

from __future__ import annotations

import time

import httpx
import pytest
import respx

from facetmark.fetch.client import (
    DEFER_TO_BROWSER,
    FetchPolicy,
    Verdict,
    _HostLimiter,
    fetch_many,
)
from facetmark.fetch.robots import (
    DEFAULT_ROBOTS_TOKEN,
    MAX_ROBOTS_BYTES,
    RobotsCache,
    parse_robots,
)
from facetmark.health import probe_many

ARTICLE = (
    "<html><head><title>A page</title></head><body><article>"
    + "<p>" + ("real prose about a real topic. " * 40) + "</p>"
    + "</article></body></html>"
)


# ---------------------------------------------------------------------------
# Parsing. RFC 9309 s2.2.
# ---------------------------------------------------------------------------

class TestRuleMatching:
    def test_no_rules_allows_everything(self):
        assert parse_robots("", "x").allows("/anything")

    def test_a_prefix_disallow_blocks_below_it(self):
        r = parse_robots("User-agent: *\nDisallow: /admin/", "x")
        assert not r.allows("/admin/panel")
        assert r.allows("/public/panel")

    def test_the_longest_matching_rule_wins(self):
        r = parse_robots(
            "User-agent: *\nDisallow: /a/\nAllow: /a/b/\nDisallow: /a/b/c/", "x"
        )
        assert not r.allows("/a/x")
        assert r.allows("/a/b/x")
        assert not r.allows("/a/b/c/x")

    def test_allow_breaks_a_tie_of_equal_length(self):
        r = parse_robots("User-agent: *\nDisallow: /page\nAllow: /page", "x")
        assert r.allows("/page")

    def test_allow_breaks_the_tie_regardless_of_line_order(self):
        r = parse_robots("User-agent: *\nAllow: /page\nDisallow: /page", "x")
        assert r.allows("/page")

    def test_star_matches_any_run_of_characters(self):
        r = parse_robots("User-agent: *\nDisallow: /*/private", "x")
        assert not r.allows("/anything/private")
        assert not r.allows("/a/b/c/private")
        assert r.allows("/private")

    def test_dollar_anchors_the_end_of_the_path(self):
        r = parse_robots("User-agent: *\nDisallow: /*.php$", "x")
        assert not r.allows("/index.php")
        assert r.allows("/index.php?q=1")
        assert r.allows("/index.phps")

    def test_an_empty_disallow_allows_everything(self):
        """``Disallow:`` with no value is the documented way to say "come in",
        and is not the same as the line being absent."""
        r = parse_robots("User-agent: *\nDisallow:", "x")
        assert r.allows("/anything")

    def test_an_empty_disallow_does_not_erase_a_real_rule(self):
        r = parse_robots("User-agent: *\nDisallow: /admin\nDisallow:", "x")
        assert not r.allows("/admin")

    def test_a_rule_without_a_leading_slash_is_still_a_path(self):
        r = parse_robots("User-agent: *\nDisallow: admin", "x")
        assert not r.allows("/admin")

    def test_comments_and_blank_lines_are_ignored(self):
        r = parse_robots(
            "# a comment\n\nUser-agent: *  # trailing\nDisallow: /admin  # here too\n", "x"
        )
        assert not r.allows("/admin")

    def test_field_names_are_case_insensitive(self):
        r = parse_robots("USER-AGENT: *\nDISALLOW: /admin", "x")
        assert not r.allows("/admin")


class TestGroupSelection:
    ROBOTS = (
        "User-agent: *\n"
        "Disallow: /\n"
        "Crawl-delay: 30\n"
        "\n"
        "User-agent: facetmark\n"
        "Disallow: /admin\n"
        "Crawl-delay: 2\n"
    )

    def test_a_group_naming_us_beats_the_wildcard_group(self):
        r = parse_robots(self.ROBOTS, DEFAULT_ROBOTS_TOKEN)
        assert r.allows("/articles/1")
        assert not r.allows("/admin")
        assert r.crawl_delay == 2

    def test_a_stranger_gets_the_wildcard_group(self):
        r = parse_robots(self.ROBOTS, "SomeOtherBot")
        assert not r.allows("/articles/1")
        assert r.crawl_delay == 30

    def test_agent_tokens_match_case_insensitively(self):
        r = parse_robots("User-agent: FaceTMark\nDisallow: /x", DEFAULT_ROBOTS_TOKEN)
        assert not r.allows("/x")

    def test_consecutive_user_agent_lines_share_one_group(self):
        r = parse_robots(
            "User-agent: alpha\nUser-agent: facetmark\nDisallow: /shared\n", DEFAULT_ROBOTS_TOKEN
        )
        assert not r.allows("/shared")

    def test_records_before_any_user_agent_line_are_ignored(self):
        r = parse_robots("Disallow: /orphan\nUser-agent: *\nDisallow: /real\n", "x")
        assert r.allows("/orphan")
        assert not r.allows("/real")

    def test_a_non_numeric_crawl_delay_is_dropped_not_fatal(self):
        r = parse_robots("User-agent: *\nCrawl-delay: soon\nDisallow: /x", "x")
        assert r.crawl_delay is None
        assert not r.allows("/x")

    def test_the_browser_user_agent_string_is_not_used_for_matching(self):
        """Channel A sends a browser ``User-agent`` header with "Chrome" and
        "Safari" in it. Matching groups on that string would silently attach us
        to any group naming any of those tokens."""
        from facetmark.fetch.client import DEFAULT_UA

        robots = "User-agent: Chrome\nDisallow: /\n"
        assert parse_robots(robots, DEFAULT_UA).allows("/x") is False
        assert parse_robots(robots, DEFAULT_ROBOTS_TOKEN).allows("/x") is True


# ---------------------------------------------------------------------------
# The cache: one read per host, and what a failed read means.
# ---------------------------------------------------------------------------

class TestRobotsCache:
    @respx.mock
    async def test_robots_is_read_once_per_host(self):
        hits = 0

        def handler(request):
            nonlocal hits
            hits += 1
            return httpx.Response(200, text="User-agent: *\nDisallow: /admin\n")

        respx.get("https://a.example/robots.txt").mock(side_effect=handler)
        cache = RobotsCache()
        async with httpx.AsyncClient() as cl:
            for path in ("/1", "/2", "/admin", "/3"):
                await cache.allows(cl, f"https://a.example{path}")
        assert hits == 1

    @respx.mock
    async def test_concurrent_first_reads_collapse_into_one_request(self):
        import asyncio

        hits = 0

        async def handler(request):
            nonlocal hits
            hits += 1
            await asyncio.sleep(0.02)
            return httpx.Response(200, text="User-agent: *\nDisallow: /admin\n")

        respx.get("https://race.example/robots.txt").mock(side_effect=handler)
        cache = RobotsCache()
        async with httpx.AsyncClient() as cl:
            out = await asyncio.gather(
                *(cache.allows(cl, f"https://race.example/{i}") for i in range(10))
            )
        assert hits == 1
        assert all(allowed for allowed, _ in out)

    @respx.mock
    async def test_http_and_https_are_separate_origins(self):
        respx.get("https://b.example/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        )
        respx.get("http://b.example/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow:\n")
        )
        cache = RobotsCache()
        async with httpx.AsyncClient() as cl:
            https_allowed, _ = await cache.allows(cl, "https://b.example/x")
            http_allowed, _ = await cache.allows(cl, "http://b.example/x")
        assert https_allowed is False
        assert http_allowed is True

    @respx.mock
    async def test_a_missing_robots_allows_everything(self):
        respx.get("https://c.example/robots.txt").mock(return_value=httpx.Response(404))
        cache = RobotsCache()
        async with httpx.AsyncClient() as cl:
            allowed, _ = await cache.allows(cl, "https://c.example/anything")
        assert allowed

    @pytest.mark.parametrize("status", [500, 502, 503])
    @respx.mock
    async def test_an_unreachable_robots_defaults_to_allow(self, status):
        respx.get("https://d.example/robots.txt").mock(return_value=httpx.Response(status))
        cache = RobotsCache(on_error="allow")
        async with httpx.AsyncClient() as cl:
            allowed, _ = await cache.allows(cl, "https://d.example/x")
        assert allowed

    @respx.mock
    async def test_deny_on_error_restores_the_letter_of_the_rfc(self):
        respx.get("https://e.example/robots.txt").mock(return_value=httpx.Response(503))
        cache = RobotsCache(on_error="deny")
        async with httpx.AsyncClient() as cl:
            allowed, _ = await cache.allows(cl, "https://e.example/x")
        assert not allowed

    @respx.mock
    async def test_a_transport_failure_is_unreachable_not_a_crash(self):
        respx.get("https://f.example/robots.txt").mock(
            side_effect=httpx.ConnectTimeout("too slow")
        )
        cache = RobotsCache(on_error="deny")
        async with httpx.AsyncClient() as cl:
            allowed, _ = await cache.allows(cl, "https://f.example/x")
        assert not allowed

    @respx.mock
    async def test_a_403_on_robots_is_unreachable_not_a_site_wide_refusal(self):
        """A host that hides its own robots.txt behind auth has not said no --
        it has said nothing, which under the default reading means yes."""
        respx.get("https://g.example/robots.txt").mock(return_value=httpx.Response(403))
        async with httpx.AsyncClient() as cl:
            allowed_default, _ = await RobotsCache().allows(cl, "https://g.example/x")
            allowed_strict, _ = await RobotsCache(on_error="deny").allows(
                cl, "https://g.example/x"
            )
        assert allowed_default is True
        assert allowed_strict is False

    @respx.mock
    async def test_an_absurdly_large_robots_is_ignored(self):
        body = "User-agent: *\nDisallow: /\n" + ("#" + "x" * 99 + "\n") * 6000
        assert len(body.encode()) > MAX_ROBOTS_BYTES
        respx.get("https://h.example/robots.txt").mock(
            return_value=httpx.Response(200, text=body)
        )
        cache = RobotsCache()
        async with httpx.AsyncClient() as cl:
            allowed, _ = await cache.allows(cl, "https://h.example/x")
        assert allowed

    @respx.mock
    async def test_html_served_in_place_of_robots_parses_to_no_rules(self):
        """Soft-404s that return the site's homepage are common. There is no
        ``Disallow`` in a homepage, so it reads as permission."""
        respx.get("https://i.example/robots.txt").mock(
            return_value=httpx.Response(200, html=ARTICLE)
        )
        cache = RobotsCache()
        async with httpx.AsyncClient() as cl:
            allowed, _ = await cache.allows(cl, "https://i.example/x")
        assert allowed

    @respx.mock
    async def test_the_query_string_is_part_of_the_matched_path(self):
        respx.get("https://j.example/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /*?share=\n")
        )
        cache = RobotsCache()
        async with httpx.AsyncClient() as cl:
            plain, _ = await cache.allows(cl, "https://j.example/post")
            shared, _ = await cache.allows(cl, "https://j.example/post?share=1")
        assert plain is True
        assert shared is False


# ---------------------------------------------------------------------------
# Channel A honours it.
# ---------------------------------------------------------------------------

class TestFetchHonoursRobots:
    @respx.mock
    async def test_a_disallowed_url_is_never_requested(self):
        page = respx.get("https://k.example/admin/secret").mock(
            return_value=httpx.Response(200, html=ARTICLE)
        )
        respx.get("https://k.example/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /admin/\n")
        )
        batch = await fetch_many(["https://k.example/admin/secret"])
        assert batch.results[0].verdict is Verdict.ROBOTS_DENIED
        assert page.call_count == 0

    @respx.mock
    async def test_an_allowed_url_on_a_restricted_host_still_fetches(self):
        respx.get("https://l.example/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /admin/\n")
        )
        respx.get("https://l.example/article").mock(
            return_value=httpx.Response(200, html=ARTICLE)
        )
        batch = await fetch_many(["https://l.example/article"])
        assert batch.results[0].verdict is Verdict.OK

    @respx.mock
    async def test_a_refusal_is_not_routed_round_through_the_browser(self):
        """Channel B would succeed -- it is the user's own logged-in browser --
        and that is exactly the manoeuvre robots.txt exists to prevent."""
        respx.get("https://m.example/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        )
        batch = await fetch_many(["https://m.example/x"])
        assert Verdict.ROBOTS_DENIED not in DEFER_TO_BROWSER
        assert batch.deferred == []

    @respx.mock
    async def test_opting_out_makes_no_robots_request_at_all(self):
        robots = respx.get("https://n.example/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        )
        respx.get("https://n.example/x").mock(return_value=httpx.Response(200, html=ARTICLE))
        batch = await fetch_many(["https://n.example/x"],
                                 policy=FetchPolicy(respect_robots=False))
        assert robots.call_count == 0
        assert batch.results[0].verdict is Verdict.OK

    @respx.mock
    async def test_one_host_refusing_does_not_stop_the_others(self):
        respx.get("https://blocked.example/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        )
        respx.get("https://open.example/robots.txt").mock(return_value=httpx.Response(404))
        respx.get("https://open.example/x").mock(
            return_value=httpx.Response(200, html=ARTICLE)
        )
        batch = await fetch_many(["https://blocked.example/x", "https://open.example/x"])
        assert batch.by_verdict() == {"ok": 1, "robots_denied": 1}


class TestCrawlDelay:
    def test_a_published_delay_raises_the_host_interval(self):
        lim = _HostLimiter(FetchPolicy(per_host_min_interval_s=0.5))
        lim.note_crawl_delay("slow.example", 3.0)
        assert lim.interval_for("slow.example") == 3.0
        assert lim.interval_for("other.example") == 0.5

    def test_a_delay_below_our_own_floor_does_not_lower_it(self):
        """A host cannot talk us into being ruder than we already decided to be."""
        lim = _HostLimiter(FetchPolicy(per_host_min_interval_s=0.5))
        lim.note_crawl_delay("fast.example", 0.01)
        assert lim.interval_for("fast.example") == 0.5

    def test_an_extreme_delay_is_capped(self):
        lim = _HostLimiter(FetchPolicy(per_host_min_interval_s=0.5, max_crawl_delay_s=5.0))
        lim.note_crawl_delay("glacial.example", 3600.0)
        assert lim.interval_for("glacial.example") == 5.0

    def test_missing_or_zero_delay_changes_nothing(self):
        lim = _HostLimiter(FetchPolicy(per_host_min_interval_s=0.5))
        lim.note_crawl_delay("x.example", None)
        lim.note_crawl_delay("x.example", 0.0)
        assert lim.interval_for("x.example") == 0.5

    @respx.mock
    async def test_the_delay_is_applied_to_the_sweep(self):
        stamps: list[float] = []

        def handler(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nCrawl-delay: 0.2\n")
            stamps.append(time.monotonic())
            return httpx.Response(200, html=ARTICLE)

        respx.get(url__startswith="https://polite.example/").mock(side_effect=handler)
        await fetch_many(
            [f"https://polite.example/{i}" for i in range(3)],
            policy=FetchPolicy(per_host_min_interval_s=0.01, per_host_concurrency=1,
                               max_crawl_delay_s=5.0),
        )
        gaps = [b - a for a, b in zip(stamps, stamps[1:], strict=False)]
        assert gaps and all(g >= 0.15 for g in gaps), gaps


# ---------------------------------------------------------------------------
# The health probe honours it too. A liveness check is still automated access,
# and the drift check reads the body.
# ---------------------------------------------------------------------------

class TestHealthProbeHonoursRobots:
    @respx.mock
    async def test_a_disallowed_url_is_skipped_by_the_probe(self):
        head = respx.head("https://o.example/admin/x").mock(
            return_value=httpx.Response(200)
        )
        respx.get("https://o.example/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /admin/\n")
        )
        [probe] = await probe_many([{"url": "https://o.example/admin/x"}])
        assert probe.verdict.value == "skipped"
        assert any(e.signal == "robots_denied" for e in probe.evidence)
        assert head.call_count == 0

    @respx.mock
    async def test_an_allowed_url_is_probed_normally(self):
        respx.get("https://p.example/robots.txt").mock(return_value=httpx.Response(404))
        respx.head("https://p.example/x").mock(return_value=httpx.Response(200))
        [probe] = await probe_many([{"url": "https://p.example/x"}])
        assert probe.verdict.value != "skipped"
