"""Link health: the three layers, and the rules that stop them lying.

Every HTTP call is stubbed with respx. Two of the tests here exist specifically
to prove the suite cannot reach the network: one asserts that a host on the
privacy exclusion list produces zero outbound requests, and one asserts that
the health package contains no DELETE statement at all.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from facetmark.config import Settings
from facetmark.fetch.client import FetchPolicy
from facetmark.health import (
    CheckReport,
    Status,
    check_bookmarks,
    gather_external,
    probe_many,
    probe_one,
)
from facetmark.health.external import (
    ExternalReport,
    doh_query,
    reader_fetch,
    wayback_lookup,
)
from facetmark.health.local import RANGE_BYTES, LocalProbe, body_similarity
from facetmark.health.store import (
    HealthState,
    consecutive_failures,
    due_for_check,
    first_failed_at,
    history,
    is_confirmed_gone,
    latest,
    record_check,
    retry_after_seconds,
    state_of,
    summary,
)
from facetmark.health.synth import synthesize
from facetmark.health.verdicts import (
    HIGH_CONFIDENCE,
    LOCAL_ONLY_CAP,
    Evidence,
    LocalVerdict,
    placeholder_hit,
)
from facetmark.importers import import_bookmarks

DAY = 86_400
FAST = FetchPolicy(per_host_min_interval_s=0.0, timeout_s=5.0)


def article(title: str, paragraphs: int = 8, word: str = "retrieval") -> str:
    body = "".join(
        f"<p>{word} paragraph {i} discussing indexing and ranking at some length "
        f"so the extractor has real text to work with.</p>"
        for i in range(paragraphs)
    )
    return f"<html><head><title>{title}</title></head><body><article>{body}</article></body></html>"


async def _probe(url: str, **kw) -> LocalProbe:
    async with httpx.AsyncClient(follow_redirects=True) as cl:
        return await probe_one(cl, url, policy=FAST, **kw)


# ---------------------------------------------------------------------------
# layer 1
# ---------------------------------------------------------------------------


class TestLocalProbe:
    @respx.mock
    async def test_a_head_200_with_nothing_indexed_is_simply_alive(self):
        route = respx.head("https://example.com/a").mock(return_value=httpx.Response(200))
        p = await _probe("https://example.com/a")
        assert p.verdict is LocalVerdict.ALIVE
        assert p.method == "HEAD"
        assert p.http_status == 200
        assert route.call_count == 1
        assert not p.needs_external

    @respx.mock
    async def test_a_404_is_gone_and_escalates(self):
        respx.head("https://example.com/x").mock(return_value=httpx.Response(404))
        p = await _probe("https://example.com/x")
        assert p.verdict is LocalVerdict.GONE
        assert p.needs_external

    @respx.mock
    async def test_a_410_is_also_gone(self):
        respx.head("https://example.com/x").mock(return_value=httpx.Response(410))
        p = await _probe("https://example.com/x")
        assert p.verdict is LocalVerdict.GONE

    @respx.mock
    async def test_a_451_is_blocked_not_gone(self):
        respx.head("https://example.com/x").mock(return_value=httpx.Response(451))
        p = await _probe("https://example.com/x")
        assert p.verdict is LocalVerdict.BLOCKED

    @respx.mock
    async def test_a_server_that_refuses_head_gets_one_ranged_get(self):
        """The CDN case: 403 to HEAD, 200 to GET. Filing that as blocked would
        be a false positive we inflicted on ourselves."""
        respx.head("https://example.com/cdn").mock(return_value=httpx.Response(403))
        get = respx.get("https://example.com/cdn").mock(return_value=httpx.Response(206))
        p = await _probe("https://example.com/cdn")
        assert p.verdict is LocalVerdict.ALIVE
        assert p.method == "GET(range)"
        assert get.calls[0].request.headers["Range"] == f"bytes=0-{RANGE_BYTES - 1}"

    @respx.mock
    async def test_the_retry_still_reports_a_real_404(self):
        respx.head("https://example.com/y").mock(return_value=httpx.Response(405))
        respx.get("https://example.com/y").mock(return_value=httpx.Response(404))
        p = await _probe("https://example.com/y")
        assert p.verdict is LocalVerdict.GONE

    @respx.mock
    async def test_a_429_is_not_retried_because_that_would_be_rude(self):
        head = respx.head("https://example.com/z").mock(return_value=httpx.Response(429))
        get = respx.get("https://example.com/z").mock(return_value=httpx.Response(200))
        p = await _probe("https://example.com/z")
        assert p.verdict is LocalVerdict.BLOCKED
        assert head.call_count == 1
        assert get.call_count == 0

    @respx.mock
    async def test_a_5xx_is_unreachable_not_gone(self):
        respx.head("https://example.com/z").mock(return_value=httpx.Response(503))
        p = await _probe("https://example.com/z")
        assert p.verdict is LocalVerdict.UNREACHABLE_LOCAL

    @respx.mock
    async def test_a_name_resolution_failure_is_dns_fail(self):
        respx.head("https://nowhere.invalid/x").mock(
            side_effect=httpx.ConnectError("[Errno -2] Name or service not known")
        )
        p = await _probe("https://nowhere.invalid/x")
        assert p.verdict is LocalVerdict.DNS_FAIL
        assert any(e.signal == "dns_failure" for e in p.evidence)

    @respx.mock
    async def test_a_timeout_is_unreachable_local(self):
        respx.head("https://slow.example/x").mock(side_effect=httpx.ConnectTimeout("timed out"))
        p = await _probe("https://slow.example/x")
        assert p.verdict is LocalVerdict.UNREACHABLE_LOCAL

    async def test_a_non_http_url_is_skipped_not_failed(self):
        p = await _probe("data:text/html,hello")
        assert p.verdict is LocalVerdict.SKIPPED
        assert not p.failed
        assert not p.needs_external

    @respx.mock
    async def test_a_redirect_is_recorded_as_evidence(self):
        respx.head("https://example.com/old").mock(
            return_value=httpx.Response(301, headers={"Location": "https://example.com/new"})
        )
        respx.head("https://example.com/new").mock(return_value=httpx.Response(200))
        p = await _probe("https://example.com/old")
        assert p.verdict is LocalVerdict.ALIVE
        assert any(e.signal == "redirected" for e in p.evidence)


class TestContentComparison:
    """Drift and soft-404 only exist when there is an indexed body to compare
    against, which is why a title-only library gets liveness and nothing else."""

    @respx.mock
    async def test_the_body_request_is_not_ranged(self):
        """The trap this module is built around: comparing an indexed body
        against the first 2 KB of the page would mark the whole library as
        drifted."""
        old = article("On Retrieval")
        respx.head("https://example.com/p").mock(return_value=httpx.Response(200))
        get = respx.get("https://example.com/p").mock(
            return_value=httpx.Response(200, html=old)
        )
        await _probe("https://example.com/p", known_chars=900, known_body="x" * 900)
        assert "Range" not in get.calls[0].request.headers

    @respx.mock
    async def test_an_unchanged_page_is_alive_by_hash_without_a_similarity_pass(self):
        from facetmark.fetch.extract import extract
        from facetmark.normalize import body_hash

        html = article("On Retrieval")
        text = extract(html, url="https://example.com/p").text
        respx.head("https://example.com/p").mock(return_value=httpx.Response(200))
        respx.get("https://example.com/p").mock(return_value=httpx.Response(200, html=html))
        p = await _probe("https://example.com/p", known_chars=len(text),
                         known_body=text, known_hash=body_hash(text))
        assert p.verdict is LocalVerdict.ALIVE
        assert p.similarity == 1.0

    @respx.mock
    async def test_a_rewritten_page_is_drifted(self):
        old = (
            "Sparse retrieval scores a document by term overlap with the query, "
            "which makes BM25 fast, explainable and blind to paraphrase. Dense "
            "retrieval embeds both sides into one space and inherits whatever the "
            "encoder learned about meaning."
        ) * 4
        respx.head("https://example.com/p").mock(return_value=httpx.Response(200))
        respx.get("https://example.com/p").mock(return_value=httpx.Response(
            200,
            html="<html><head><title>Sourdough</title></head><body><article>"
                 + "<p>Feed the starter twice daily until it doubles reliably. "
                   "Autolyse the flour and water for an hour before adding salt, "
                   "then stretch and fold every thirty minutes through bulk "
                   "fermentation. Shape cold, bake covered.</p>" * 4
                 + "</article></body></html>",
        ))
        p = await _probe("https://example.com/p", known_chars=len(old), known_body=old)
        assert p.verdict is LocalVerdict.DRIFTED
        assert p.similarity is not None and p.similarity < 0.6

    @respx.mock
    async def test_a_page_that_only_gained_a_paragraph_is_not_drifted(self):
        """Drift feeds the metabolism layer, so the threshold is set to
        under-report: an edit is not a rewrite."""
        base = (
            "Sparse retrieval scores a document by term overlap with the query, "
            "which makes BM25 fast, explainable and blind to paraphrase. Dense "
            "retrieval embeds both sides into one space and inherits whatever the "
            "encoder learned about meaning."
        ) * 4
        respx.head("https://example.com/p").mock(return_value=httpx.Response(200))
        respx.get("https://example.com/p").mock(return_value=httpx.Response(
            200,
            html="<html><head><title>Retrieval</title></head><body><article><p>"
                 + base + " Update: reciprocal rank fusion combines both lists "
                          "without tuning any weights.</p></article></body></html>",
        ))
        p = await _probe("https://example.com/p", known_chars=len(base), known_body=base)
        assert p.verdict is LocalVerdict.ALIVE

    @respx.mock
    async def test_a_placeholder_plus_a_length_collapse_is_soft_gone(self):
        respx.head("https://example.com/p").mock(return_value=httpx.Response(200))
        respx.get("https://example.com/p").mock(return_value=httpx.Response(
            200,
            html="<html><head><title>404 页面不存在</title></head>"
                 "<body><p>抱歉，您访问的页面已删除或从未存在过。</p></body></html>",
        ))
        p = await _probe("https://example.com/p", known_chars=4000, known_body="x" * 4000)
        assert p.verdict is LocalVerdict.SOFT_GONE
        assert p.length_ratio is not None and p.length_ratio < 0.30
        assert any(e.signal == "soft_404" for e in p.evidence)

    @respx.mock
    async def test_a_length_collapse_alone_is_not_soft_gone(self):
        """Some pages just get shorter. Without the placeholder wording this is
        drift at most."""
        respx.head("https://example.com/p").mock(return_value=httpx.Response(200))
        respx.get("https://example.com/p").mock(
            return_value=httpx.Response(200, html=article("Trimmed", paragraphs=1))
        )
        p = await _probe("https://example.com/p", known_chars=6000, known_body="y" * 6000)
        assert p.verdict is not LocalVerdict.SOFT_GONE

    @respx.mock
    async def test_a_page_about_http_404_is_not_soft_gone(self):
        """The placeholder list matches "404"; a full-length article about
        error handling must survive it."""
        from facetmark.fetch.extract import extract

        html = article("Handling 404 responses", paragraphs=8, word="retrieval")
        text = extract(html, url="https://example.com/p").text
        respx.head("https://example.com/p").mock(return_value=httpx.Response(200))
        respx.get("https://example.com/p").mock(return_value=httpx.Response(200, html=html))
        p = await _probe("https://example.com/p", known_chars=len(text), known_body=text)
        assert p.verdict is LocalVerdict.ALIVE

    async def test_placeholder_hit_only_scans_the_head_of_the_body(self):
        assert placeholder_hit("", "x" * 600 + "page does not exist") == ""
        assert placeholder_hit("", "page does not exist" + "x" * 600)

    def test_body_similarity_handles_cjk_and_empties(self):
        assert body_similarity("", "") == 1.0
        assert body_similarity("abc", "") == 0.0
        assert body_similarity("向量数据库选型笔记", "向量数据库选型笔记") == 1.0
        assert body_similarity("向量数据库选型笔记", "今天中午吃什么好呢") < 0.6

    @respx.mock
    async def test_a_body_fetch_failure_leaves_the_liveness_answer_standing(self):
        respx.head("https://example.com/p").mock(return_value=httpx.Response(200))
        respx.get("https://example.com/p").mock(side_effect=httpx.ReadTimeout("nope"))
        p = await _probe("https://example.com/p", known_chars=900, known_body="z" * 900)
        assert p.verdict is LocalVerdict.ALIVE
        assert any(e.signal == "body_fetch_failed" for e in p.evidence)


class TestProbeMany:
    @respx.mock
    async def test_results_come_back_in_input_order(self):
        for i in range(4):
            respx.head(f"https://h{i}.example/p").mock(
                return_value=httpx.Response(200 if i % 2 == 0 else 404)
            )
        out = await probe_many(
            [{"url": f"https://h{i}.example/p"} for i in range(4)], policy=FAST
        )
        assert [p.url for p in out] == [f"https://h{i}.example/p" for i in range(4)]
        assert [p.verdict for p in out] == [
            LocalVerdict.ALIVE, LocalVerdict.GONE, LocalVerdict.ALIVE, LocalVerdict.GONE
        ]


# ---------------------------------------------------------------------------
# layer 2
# ---------------------------------------------------------------------------


def ext_settings(tmp_path, **kw) -> Settings:
    base = {
        "data_dir": tmp_path,
        "use_mock_provider": True,
        "embed_dim": 32,
        "health_enable_external": True,
        "health_doh_endpoints": ("https://doh-one.example/dns-query",
                                 "https://doh-two.example/resolve"),
        "health_wayback_api": "https://wayback.example/available",
        "health_reader_proxy": "https://reader.example/",
    }
    base.update(kw)
    return Settings(**base)


def doh_ok(*addrs: str) -> httpx.Response:
    return httpx.Response(200, json={
        "Status": 0,
        "Answer": [{"name": "x", "type": 1, "TTL": 60, "data": a} for a in addrs],
    })


def doh_nxdomain() -> httpx.Response:
    return httpx.Response(200, json={"Status": 3})


def stub_external(*, one=None, two=None, wayback=None, reader=None) -> None:
    respx.get(url__startswith="https://doh-one.example/dns-query").mock(
        return_value=one if one is not None else doh_nxdomain())
    respx.get(url__startswith="https://doh-two.example/resolve").mock(
        return_value=two if two is not None else doh_nxdomain())
    respx.get(url__startswith="https://wayback.example/available").mock(
        return_value=wayback if wayback is not None
        else httpx.Response(200, json={"archived_snapshots": {}}))
    respx.get(url__startswith="https://reader.example/").mock(
        return_value=reader if reader is not None else httpx.Response(502))


async def _gather(url: str, st: Settings, **kw) -> ExternalReport:
    async with httpx.AsyncClient() as cl:
        return await gather_external(cl, url, settings=st, **kw)


class TestExternalSources:
    @respx.mock
    async def test_doh_parses_a_records_and_rcode(self):
        respx.get(url__startswith="https://doh-one.example").mock(
            return_value=doh_ok("93.184.216.34"))
        async with httpx.AsyncClient() as cl:
            a = await doh_query(cl, "example.com", "https://doh-one.example/dns-query")
        assert a.resolved and a.rcode == 0 and a.usable
        assert a.addresses == ("93.184.216.34",)

    @respx.mock
    async def test_a_resolver_that_errors_is_not_counted_as_a_no(self):
        respx.get(url__startswith="https://doh-one.example").mock(
            side_effect=httpx.ConnectTimeout("x"))
        async with httpx.AsyncClient() as cl:
            a = await doh_query(cl, "example.com", "https://doh-one.example/dns-query")
        assert not a.usable and not a.resolved and not a.nxdomain

    @respx.mock
    async def test_wayback_returns_the_snapshot_epoch(self):
        respx.get(url__startswith="https://wayback.example").mock(
            return_value=httpx.Response(200, json={"archived_snapshots": {"closest": {
                "available": True, "url": "http://web.archive.org/web/20260728/x",
                "timestamp": "20260728120000", "status": "200"}}}))
        async with httpx.AsyncClient() as cl:
            url, ts, err = await wayback_lookup(
                cl, "https://example.com/x", "https://wayback.example/available")
        assert not err and ts is not None and "web.archive.org" in url

    @respx.mock
    async def test_wayback_with_no_snapshot_is_silence_not_a_verdict(self):
        respx.get(url__startswith="https://wayback.example").mock(
            return_value=httpx.Response(200, json={"archived_snapshots": {}}))
        async with httpx.AsyncClient() as cl:
            url, ts, err = await wayback_lookup(
                cl, "https://example.com/x", "https://wayback.example/available")
        assert (url, ts, err) == ("", None, "")

    @respx.mock
    async def test_the_reader_proxy_hands_back_the_body(self):
        respx.get(url__startswith="https://reader.example/").mock(
            return_value=httpx.Response(200, text="Title Line\n\nrecovered article text"))
        async with httpx.AsyncClient() as cl:
            ok, text, err = await reader_fetch(
                cl, "https://example.com/x", "https://reader.example/")
        assert ok and not err and "recovered article text" in text

    async def test_no_reader_proxy_configured_is_a_clean_no(self):
        async with httpx.AsyncClient() as cl:
            ok, text, err = await reader_fetch(cl, "https://example.com/x", "")
        assert not ok and err


class TestGatherExternal:
    @respx.mock
    async def test_disagreeing_resolvers_are_recorded_as_divergence(self, tmp_path):
        stub_external(one=doh_ok("1.2.3.4"), two=doh_nxdomain())
        rep = await _gather("https://example.com/x", ext_settings(tmp_path))
        assert rep.checked and rep.resolver_divergence and rep.any_resolved
        assert any(e.signal == "resolver_divergence" for e in rep.evidence)

    @respx.mock
    async def test_agreeing_nxdomain_is_recorded_separately(self, tmp_path):
        stub_external()
        rep = await _gather("https://example.com/x", ext_settings(tmp_path))
        assert rep.resolvers_agree_nxdomain and not rep.resolver_divergence

    @respx.mock
    async def test_a_snapshot_after_the_failure_is_the_signal_that_matters(self, tmp_path):
        stub_external(wayback=httpx.Response(200, json={"archived_snapshots": {"closest": {
            "available": True, "url": "http://web.archive.org/web/20260728/x",
            "timestamp": "20260728120000"}}}))
        after = await _gather("https://example.com/x", ext_settings(tmp_path),
                              first_failed_ts=1_700_000_000)
        assert after.snapshot_after_failure
        before = await _gather("https://example.com/x", ext_settings(tmp_path),
                               first_failed_ts=2_000_000_000)
        assert not before.snapshot_after_failure
        assert before.snapshot_url

    @respx.mock
    async def test_a_reader_success_carries_the_recovered_body(self, tmp_path):
        stub_external(reader=httpx.Response(200, text="Recovered\n\nbody text here"))
        rep = await _gather("https://example.com/x", ext_settings(tmp_path))
        assert rep.reader_ok and rep.reachable_elsewhere
        assert rep.recovered_title == "Recovered"
        assert "body text here" in rep.recovered_body

    @respx.mock
    async def test_the_master_switch_stops_the_layer_entirely(self, tmp_path):
        stub_external(one=doh_ok("1.2.3.4"))
        rep = await _gather("https://example.com/x",
                            ext_settings(tmp_path, health_enable_external=False))
        assert not rep.checked and "disabled" in rep.skipped_reason
        assert not respx.calls

    @respx.mock
    async def test_a_privacy_excluded_host_makes_zero_outbound_requests(self, tmp_path):
        """The hard privacy guarantee: excluded domains are never named to a
        third party, not even to a DNS resolver."""
        stub_external(one=doh_ok("1.2.3.4"))
        st = ext_settings(tmp_path, privacy_excluded_domains=("internal.example",))
        rep = await _gather("https://wiki.internal.example/page", st)
        assert not rep.checked
        assert "privacy" in rep.skipped_reason or "exclusion" in rep.skipped_reason
        assert len(respx.calls) == 0

    @respx.mock
    async def test_each_source_is_switchable_on_its_own(self, tmp_path):
        stub_external(one=doh_ok("1.2.3.4"),
                      reader=httpx.Response(200, text="t\n\nbody"))
        st = ext_settings(tmp_path, health_enable_wayback=False,
                          health_enable_reader=False)
        rep = await _gather("https://example.com/x", st)
        assert rep.checked and rep.any_resolved
        assert not rep.reader_ok and not rep.snapshot_url
        hosts = {c.request.url.host for c in respx.calls}
        assert hosts == {"doh-one.example", "doh-two.example"}

    @respx.mock
    async def test_turning_everything_off_reports_no_source_rather_than_success(
        self, tmp_path
    ):
        stub_external()
        st = ext_settings(tmp_path, health_enable_doh=False,
                          health_enable_wayback=False, health_enable_reader=False)
        rep = await _gather("https://example.com/x", st)
        assert not rep.checked and "no external source" in rep.skipped_reason


# ---------------------------------------------------------------------------
# synthesis
# ---------------------------------------------------------------------------


def local(verdict: LocalVerdict, **kw) -> LocalProbe:
    return LocalProbe(url="https://example.com/x", verdict=verdict, **kw)


def ext(**kw) -> ExternalReport:
    return ExternalReport(checked=True, **kw)


class TestSynthesis:
    def test_one_positive_elsewhere_outvotes_a_local_404(self):
        """The headline rule. A reader proxy that rendered the page beats any
        amount of local failure."""
        c = synthesize(local(LocalVerdict.GONE, http_status=404),
                       ext(reader_ok=True, recovered_body="text"))
        assert c.status is Status.RESTRICTED
        assert c.confidence > HIGH_CONFIDENCE

    def test_resolver_divergence_turns_a_timeout_into_restricted(self):
        c = synthesize(local(LocalVerdict.UNREACHABLE_LOCAL),
                       ext(resolver_divergence=True, any_resolved=True))
        assert c.status is Status.RESTRICTED

    def test_a_local_dns_failure_that_public_resolvers_contradict_is_restricted(self):
        c = synthesize(local(LocalVerdict.DNS_FAIL), ext(any_resolved=True))
        assert c.status is Status.RESTRICTED
        assert any(e.signal == "local_resolver_diverges" for e in c.evidence)

    def test_a_snapshot_taken_after_we_started_failing_is_restricted(self):
        c = synthesize(local(LocalVerdict.UNREACHABLE_LOCAL),
                       ext(snapshot_after_failure=True,
                           snapshot_url="http://web.archive.org/web/x"))
        assert c.status is Status.RESTRICTED
        assert c.archive_url

    def test_a_404_that_nothing_contradicts_is_gone_above_the_confirmation_bar(self):
        c = synthesize(local(LocalVerdict.GONE, http_status=404), ext())
        assert c.status is Status.GONE
        assert c.confidence >= HIGH_CONFIDENCE

    def test_a_404_without_the_external_layer_can_never_confirm(self):
        """Graceful degradation: the check still runs and is still recorded, it
        just cannot reach the bar that declaring a death requires."""
        c = synthesize(local(LocalVerdict.GONE, http_status=404), None)
        assert c.status is Status.GONE
        assert c.confidence == LOCAL_ONLY_CAP
        assert c.confidence < HIGH_CONFIDENCE

    def test_a_dead_domain_is_still_only_unreachable(self):
        """Deliberately stricter than the evidence: both public resolvers say
        NXDOMAIN, and the answer is still not `gone`, because only the server
        itself gets to declare a URL dead."""
        c = synthesize(local(LocalVerdict.DNS_FAIL), ext(resolvers_agree_nxdomain=True))
        assert c.status is Status.UNREACHABLE
        assert c.status is not Status.GONE

    def test_a_403_is_restricted_because_the_server_refused_us_specifically(self):
        c = synthesize(local(LocalVerdict.BLOCKED, http_status=403), ext())
        assert c.status is Status.RESTRICTED

    def test_a_200_never_consults_the_second_layer(self):
        c = synthesize(local(LocalVerdict.ALIVE, http_status=200))
        assert c.status is Status.ALIVE
        assert c.external is None
        assert not c.is_dead_signal

    def test_drift_and_soft_gone_pass_straight_through(self):
        assert synthesize(local(LocalVerdict.DRIFTED)).status is Status.DRIFTED
        assert synthesize(local(LocalVerdict.SOFT_GONE)).status is Status.SOFT_GONE
        assert synthesize(local(LocalVerdict.DRIFTED)).is_dead_signal

    def test_a_skipped_url_is_unknown_not_a_failure(self):
        assert synthesize(local(LocalVerdict.SKIPPED)).status is Status.UNKNOWN

    def test_evidence_from_both_layers_is_kept_for_the_user_to_read(self):
        p = local(LocalVerdict.GONE, evidence=[Evidence("local", "http_404", "", 1)])
        c = synthesize(p, ext(evidence=[Evidence("doh", "resolves", "", 1)]))
        layers = {e.layer for e in c.evidence}
        assert layers == {"local", "doh"}
        assert c.as_dict()["evidence"]

    def test_every_dead_verdict_string_matches_what_decay_looks_for(self):
        from facetmark.search.decay import DEAD_VERDICTS

        assert set(DEAD_VERDICTS) <= {s.value for s in Status}


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------


@pytest.fixture()
def hdb(conn, netscape_sample, settings):
    import_bookmarks(conn, content=netscape_sample, settings=settings)
    return conn


def bid_of(conn, needle: str) -> int:
    return int(conn.execute(
        "SELECT id FROM bookmark WHERE url LIKE ? LIMIT 1", (f"%{needle}%",)
    ).fetchone()["id"])


def put(conn, bid: int, status: Status, at: int, conf: float = 0.9) -> None:
    record_check(conn, bid, synthesize(
        local(LocalVerdict.ALIVE) if status is Status.ALIVE else local(LocalVerdict.GONE),
        None, now_ts=at,
    ))
    conn.execute("UPDATE health SET verdict=?, confidence=? WHERE id=(SELECT MAX(id) FROM health)",
                 (status.value, conf))


class TestStore:
    def test_a_check_round_trips_with_its_evidence(self, hdb):
        bid = bid_of(hdb, "crdt-guide")
        c = synthesize(local(LocalVerdict.GONE, http_status=404,
                             evidence=[Evidence("local", "http_404", "", 1)]),
                       ext(snapshot_url="http://web.archive.org/web/x"), now_ts=1000)
        record_check(hdb, bid, c)
        row = latest(hdb, bid)
        assert row["verdict"] == "gone" and row["http_status"] == 404
        assert row["archive_url"] == "http://web.archive.org/web/x"
        assert "http_404" in row["local_evidence"]
        assert row["external_evidence"]

    def test_history_is_append_only(self, hdb):
        bid = bid_of(hdb, "crdt-guide")
        put(hdb, bid, Status.ALIVE, 1000)
        put(hdb, bid, Status.GONE, 2000)
        assert len(history(hdb, bid)) == 2
        assert latest(hdb, bid)["verdict"] == "gone"

    def test_first_failed_tracks_the_current_run_not_the_first_ever(self, hdb):
        """A page that broke, was fixed, and broke again has been failing since
        the second break -- which is what the Wayback comparison hinges on."""
        bid = bid_of(hdb, "crdt-guide")
        put(hdb, bid, Status.GONE, 1_000_000)
        put(hdb, bid, Status.ALIVE, 2_000_000)
        put(hdb, bid, Status.UNREACHABLE, 3_000_000)
        put(hdb, bid, Status.UNREACHABLE, 4_000_000)
        assert first_failed_at(hdb, bid) == 3_000_000

    def test_no_failures_means_no_failure_start(self, hdb):
        bid = bid_of(hdb, "crdt-guide")
        put(hdb, bid, Status.ALIVE, 1000)
        assert first_failed_at(hdb, bid) is None

    def test_two_gone_checks_a_day_apart_do_not_confirm(self, hdb):
        bid = bid_of(hdb, "crdt-guide")
        put(hdb, bid, Status.GONE, 1_000_000)
        put(hdb, bid, Status.GONE, 1_000_000 + DAY)
        assert not is_confirmed_gone(hdb, bid, confirm_days=7)

    def test_two_gone_checks_eight_days_apart_confirm(self, hdb):
        bid = bid_of(hdb, "crdt-guide")
        put(hdb, bid, Status.GONE, 1_000_000)
        put(hdb, bid, Status.GONE, 1_000_000 + 8 * DAY)
        assert is_confirmed_gone(hdb, bid, confirm_days=7)

    def test_low_confidence_checks_never_count_as_confirmations(self, hdb):
        bid = bid_of(hdb, "crdt-guide")
        put(hdb, bid, Status.GONE, 1_000_000, conf=LOCAL_ONLY_CAP)
        put(hdb, bid, Status.GONE, 1_000_000 + 30 * DAY, conf=LOCAL_ONLY_CAP)
        assert not is_confirmed_gone(hdb, bid, confirm_days=7)

    def test_backoff_doubles_and_then_stops(self):
        assert retry_after_seconds(0) == DAY
        assert retry_after_seconds(1) == DAY
        assert retry_after_seconds(3) == 4 * DAY
        assert retry_after_seconds(50) == 30 * DAY

    def test_consecutive_failures_resets_after_a_recovery(self, hdb):
        bid = bid_of(hdb, "crdt-guide")
        put(hdb, bid, Status.UNREACHABLE, 1000)
        put(hdb, bid, Status.UNREACHABLE, 2000)
        assert consecutive_failures(hdb, bid) == 2
        put(hdb, bid, Status.ALIVE, 3000)
        assert consecutive_failures(hdb, bid) == 0

    def test_state_is_unknown_before_any_check(self, hdb):
        st = state_of(hdb, bid_of(hdb, "crdt-guide"))
        assert st.status is Status.UNKNOWN and st.checked_at is None
        assert not st.show_in_graveyard and st.badge == ""

    def test_the_graveyard_needs_a_confirmation_not_just_a_verdict(self, hdb, settings):
        bid = bid_of(hdb, "crdt-guide")
        put(hdb, bid, Status.GONE, 1_000_000)
        assert not state_of(hdb, bid, settings=settings).show_in_graveyard
        put(hdb, bid, Status.GONE, 1_000_000 + 8 * DAY)
        state = state_of(hdb, bid, settings=settings)
        assert state.show_in_graveyard
        assert state.badge == "link appears dead"

    def test_restricted_gets_a_badge_and_stays_out_of_the_graveyard(self, hdb, settings):
        bid = bid_of(hdb, "crdt-guide")
        put(hdb, bid, Status.RESTRICTED, 1_000_000)
        state = state_of(hdb, bid, settings=settings)
        assert not state.show_in_graveyard
        assert "region" in state.badge

    def test_summary_reports_unchecked_rather_than_omitting_it(self, hdb):
        bid = bid_of(hdb, "crdt-guide")
        put(hdb, bid, Status.ALIVE, 1000)
        s = summary(hdb)
        assert s["alive"] == 1
        assert s["unchecked"] >= 1

    def test_due_for_check_prefers_never_checked_and_respects_backoff(self, hdb):
        first = due_for_check(hdb, limit=100, now_ts=10_000_000)
        assert len(first) >= 4
        bid = int(first[0]["id"])
        put(hdb, bid, Status.ALIVE, 10_000_000)
        again = [int(r["id"]) for r in due_for_check(hdb, limit=100, now_ts=10_000_100)]
        assert bid not in again

    def test_due_for_check_carries_the_indexed_body_so_drift_can_be_measured(self, hdb):
        from facetmark.fetch.store import store_body

        bid = bid_of(hdb, "crdt-guide")
        store_body(hdb, bid, body="indexed body text", title="t", extractor="x")
        row = next(r for r in due_for_check(hdb, limit=100) if int(r["id"]) == bid)
        assert row["known_chars"] == len("indexed body text")
        assert row["known_hash"]

    def test_the_package_contains_no_delete_statement(self):
        """Structural guarantee rather than a promise in a docstring: nothing in
        the health package can remove a bookmark or a check."""
        import pathlib

        import facetmark.health as pkg

        for p in pathlib.Path(pkg.__file__).parent.glob("*.py"):
            src = p.read_text(encoding="utf-8").lower()
            assert "delete from" not in src, p.name
            assert "drop table" not in src, p.name


# ---------------------------------------------------------------------------
# end to end
# ---------------------------------------------------------------------------


class TestCheckBookmarks:
    @respx.mock
    async def test_a_batch_writes_one_row_per_bookmark(self, hdb, tmp_path):
        respx.head(url__regex=r".*").mock(return_value=httpx.Response(200))
        rep = await check_bookmarks(hdb, settings=ext_settings(tmp_path),
                                    policy=FAST, now_ts=10_000_000)
        assert isinstance(rep, CheckReport)
        assert rep.probed == rep.considered > 0
        assert rep.by_status["alive"] == rep.probed
        assert rep.escalated == 0
        # The data: URL never reaches the probe -- the importer already marked
        # it non-indexable, and due_for_check only looks at indexable rows.
        assert not any(str(c.request.url).startswith("data:") for c in respx.calls)
        rows = hdb.execute("SELECT COUNT(*) FROM health").fetchone()[0]
        assert rows == rep.probed

    @respx.mock
    async def test_a_dead_link_escalates_and_lands_as_gone(self, hdb, tmp_path):
        respx.head(url__regex=r".*").mock(return_value=httpx.Response(404))
        stub_external()
        rep = await check_bookmarks(hdb, settings=ext_settings(tmp_path),
                                    policy=FAST, now_ts=10_000_000)
        assert rep.escalated > 0
        assert rep.by_status.get("gone", 0) > 0
        assert not rep.confirmed_gone  # one observation is not a confirmation

    @respx.mock
    async def test_two_runs_a_week_apart_are_what_confirms_a_death(self, hdb, tmp_path):
        respx.head(url__regex=r".*").mock(return_value=httpx.Response(404))
        stub_external()
        st = ext_settings(tmp_path)
        await check_bookmarks(hdb, settings=st, policy=FAST, now_ts=10_000_000)
        rep2 = await check_bookmarks(hdb, settings=st, policy=FAST,
                                     now_ts=10_000_000 + 8 * DAY)
        assert rep2.confirmed_gone
        bid = rep2.confirmed_gone[0]
        assert state_of(hdb, bid, settings=st).show_in_graveyard

    @respx.mock
    async def test_the_reader_proxy_recovers_a_body_channel_a_could_not_reach(
        self, hdb, tmp_path
    ):
        # Anchored: an unanchored pattern also matches the reader-proxy URL,
        # which embeds the target URL in its path.
        respx.head(url__regex=r"^https://example\.com/.*").mock(
            return_value=httpx.Response(403))
        respx.get(url__regex=r"^https://example\.com/.*").mock(
            return_value=httpx.Response(403))
        respx.head(url__regex=r".*").mock(return_value=httpx.Response(200))
        stub_external(reader=httpx.Response(
            200, text="Recovered Title\n\n" + "recovered article body. " * 20))
        rep = await check_bookmarks(hdb, settings=ext_settings(tmp_path),
                                    policy=FAST, now_ts=10_000_000)
        assert rep.recovered_bodies > 0
        assert rep.by_status.get("restricted", 0) > 0
        stored = hdb.execute(
            "SELECT body_text, fetch_channel FROM content WHERE fetch_channel='reader'"
        ).fetchall()
        assert stored and "recovered article body" in stored[0]["body_text"]

    @respx.mock
    async def test_an_explicit_id_list_bypasses_the_backoff(self, hdb, tmp_path):
        respx.head(url__regex=r".*").mock(return_value=httpx.Response(200))
        st = ext_settings(tmp_path)
        bid = bid_of(hdb, "crdt-guide")
        await check_bookmarks(hdb, ids=[bid], settings=st, policy=FAST, now_ts=1000)
        rep = await check_bookmarks(hdb, ids=[bid], settings=st, policy=FAST, now_ts=1100)
        assert rep.probed == 1
        assert len(history(hdb, bid)) == 2

    @respx.mock
    async def test_an_empty_selection_is_a_no_op_not_an_error(self, hdb, tmp_path):
        rep = await check_bookmarks(hdb, ids=[999_999], settings=ext_settings(tmp_path),
                                    policy=FAST)
        assert rep.considered == 0 and rep.probed == 0
        assert not respx.calls

    def test_health_state_is_json_serialisable_for_the_api(self):
        d = HealthState(bookmark_id=1, status=Status.RESTRICTED, confidence=0.8).as_dict()
        assert d["status"] == "restricted" and "badge" in d
