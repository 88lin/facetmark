"""A broken parser must not be readable as a dead page.

Both extractor tiers parse arbitrary bytes off the open internet, so both
crash: lxml rejects control characters, malformed markup blows the recursion
limit, a hostile document exhausts memory. Until 1.6.1 each tier caught its own
exception and returned a bare ``""``, which meant a crash and a genuinely blank
page arrived downstream as the same value.

That difference is load-bearing. ``probe_one`` compares the freshly extracted
text against the indexed copy; zero characters against a healthy copy scores
similarity 0.0, which is below ``DRIFT_SIMILARITY``, which returns DRIFTED,
which is in ``DEAD_VERDICTS``, which puts the bookmark in the cold layer and
demotes it in search. The whole chain would have been driven by our own
instrument breaking.

The 1.6.0 full-library health pass logged this exception repeatedly on stderr
while reporting ``errors: []``. Auditing the stored verdicts afterwards found
all 58 drifted rows carried ``body_chars > 0``, so no published number came
from this path -- it was a loaded gun that had not gone off. These tests keep
it unloaded.
"""

import httpx
import pytest
import respx

from facetmark.fetch.extract import MIN_USEFUL_CHARS, Extraction, extract
from facetmark.health.local import LocalVerdict, probe_one

pytestmark = pytest.mark.anyio


def article(topic: str) -> str:
    body = (
        f"{topic} is the subject of this page. Sparse retrieval scores a "
        "document by term overlap with the query, which makes it fast, "
        "explainable and blind to paraphrase. Dense retrieval embeds both "
        "sides into one space instead. "
    ) * 6
    return f"<html><head><title>{topic}</title></head><body><article><p>{body}</p></article></body></html>"


class TestTheExtractorNamesItsFailures:
    def test_a_crashing_tier_is_recorded_not_hidden(self, monkeypatch):
        mod = __import__("facetmark.fetch.extract", fromlist=["x"])

        def boom(html, url):
            raise ValueError("All strings must be XML compatible")

        monkeypatch.setattr(mod, "_try_trafilatura", boom)
        monkeypatch.setattr(mod, "_try_readability", lambda html: "")
        ex = extract(article("Retrieval"))
        assert any("trafilatura" in f for f in ex.failures)
        assert "ValueError" in ex.failures[0]

    def test_a_crash_in_one_tier_is_survivable_when_the_next_tier_works(self, monkeypatch):
        mod = __import__("facetmark.fetch.extract", fromlist=["x"])
        monkeypatch.setattr(mod, "_try_trafilatura",
                            lambda html, url: (_ for _ in ()).throw(RecursionError("deep")))
        monkeypatch.setattr(mod, "_try_readability", lambda html: "y" * MIN_USEFUL_CHARS)
        ex = extract(article("Retrieval"))
        assert ex.extractor == "readability"
        assert ex.failures, "the crash still happened and is still worth recording"
        assert not ex.parse_failed, "text was recovered, so the instrument is not broken"

    def test_both_tiers_crashing_is_a_broken_instrument(self, monkeypatch):
        mod = __import__("facetmark.fetch.extract", fromlist=["x"])
        monkeypatch.setattr(mod, "_try_trafilatura",
                            lambda html, url: (_ for _ in ()).throw(ValueError("bad")))
        monkeypatch.setattr(mod, "_try_readability",
                            lambda html: (_ for _ in ()).throw(ValueError("bad")))
        ex = extract("<html><body><p>whatever</p></body></html>")
        assert ex.parse_failed
        assert len(ex.failures) == 2

    def test_a_genuinely_empty_page_is_not_a_broken_instrument(self):
        # The distinction the whole change exists to preserve: nothing to
        # extract is a measurement, failing to extract is not.
        ex = extract("<html><body></body></html>")
        assert ex.text == ""
        assert not ex.parse_failed
        assert ex.failures == ()

    def test_a_crash_laundered_through_the_metadata_tier_is_still_a_crash(self, monkeypatch):
        # The metadata tier hands back the <title>, which is long enough to be
        # non-empty and far too short to be a body. Left unflagged it reads as
        # "the page lost 99% of its text".
        mod = __import__("facetmark.fetch.extract", fromlist=["x"])
        monkeypatch.setattr(mod, "_try_trafilatura",
                            lambda html, url: (_ for _ in ()).throw(ValueError("xml")))
        monkeypatch.setattr(mod, "_try_readability",
                            lambda html: (_ for _ in ()).throw(ValueError("xml")))
        ex = extract(article("Retrieval"))
        assert ex.extractor == "metadata" and ex.text
        assert ex.parse_failed, "non-empty title text must not disguise the crash"

    def test_a_thin_page_that_only_has_metadata_is_still_a_measurement(self):
        ex = extract("<html><head><title>Just A Title</title></head><body></body></html>")
        assert ex.extractor == "metadata" and ex.text
        assert not ex.parse_failed, "no crash happened, so this is real if thin"

    def test_the_field_defaults_so_existing_construction_still_works(self):
        assert Extraction("x", "t", "trafilatura").failures == ()
        assert not Extraction("", "t", "none").parse_failed


class TestTheHealthCheckerRefusesToVerdictOnACrash:
    @respx.mock
    async def test_a_parser_crash_on_a_live_page_does_not_become_drifted(self, monkeypatch):
        mod = __import__("facetmark.fetch.extract", fromlist=["x"])
        monkeypatch.setattr(mod, "_try_trafilatura",
                            lambda html, url: (_ for _ in ()).throw(ValueError("xml")))
        monkeypatch.setattr(mod, "_try_readability",
                            lambda html: (_ for _ in ()).throw(ValueError("xml")))

        html = article("Retrieval")
        respx.head("https://example.com/p").mock(return_value=httpx.Response(200))
        respx.get("https://example.com/p").mock(return_value=httpx.Response(200, html=html))

        async with httpx.AsyncClient(follow_redirects=True) as cl:
            p = await probe_one(
                cl, "https://example.com/p", known_chars=900,
                known_body="x" * 900, robots=None, limiter=None,
            )
        assert p.verdict is LocalVerdict.ALIVE, "HTTP 200 plus a broken parser is not a dead page"
        assert any(e.signal == "extraction_failed" for e in p.evidence)
        assert "ValueError" in (p.error or "")

    @respx.mock
    async def test_a_page_that_really_went_blank_still_drifts(self, monkeypatch):
        # The control. Without it the fix above could simply have switched
        # drift detection off and every test would still be green.
        mod = __import__("facetmark.fetch.extract", fromlist=["x"])
        monkeypatch.setattr(mod, "_try_trafilatura", lambda html, url: "")
        monkeypatch.setattr(mod, "_try_readability", lambda html: "")

        respx.head("https://example.com/q").mock(return_value=httpx.Response(200))
        respx.get("https://example.com/q").mock(
            return_value=httpx.Response(200, html="<html><body><p>hi</p></body></html>")
        )
        async with httpx.AsyncClient(follow_redirects=True) as cl:
            p = await probe_one(
                cl, "https://example.com/q", known_chars=900,
                known_body="x" * 900, robots=None, limiter=None,
            )
        assert p.verdict is LocalVerdict.DRIFTED
        assert not any(e.signal == "extraction_failed" for e in p.evidence)
