"""Enrichment, the intent self-consistency filter, and vectorisation.

No network. Model calls go through the deterministic offline provider, or
through a stub that returns a scripted reply; the OpenAI-compatible transport is
exercised with respx.
"""

from __future__ import annotations

import math

import httpx
import pytest
import respx

from facetmark.config import Settings
from facetmark.db import count_vectors, ensure_vec_tables, jload, knn_content, open_db
from facetmark.enrich import (
    coerce,
    embed_content,
    embed_intents,
    enrich_all,
    filter_intents,
    probe,
)
from facetmark.enrich.pipeline import targets, title_only_hash
from facetmark.enrich.schema import SUMMARY_MAX, EnrichmentInvalid
from facetmark.enrich.vectors import content_text
from facetmark.fetch import store_body
from facetmark.importers import import_bookmarks
from facetmark.providers import (
    MockProvider,
    OpenAICompatibleProvider,
    Provider,
    ProviderError,
    get_provider,
    parse_json_object,
)
from facetmark.search import lexical_lists, rrf

PAGES = {
    "kube": ("Deploying a Python service on Kubernetes",
             "This guide walks through packaging a Flask application into a container image, "
             "writing a Deployment and a Service manifest, and rolling it out to a cluster "
             "without downtime. It covers readiness probes, resource requests and the "
             "rollback command you will want at three in the morning."),
    "vec": ("Vector databases compared",
            "A side by side look at pgvector, Qdrant, Milvus and sqlite-vec for small "
            "collections. Brute force scan is fine below one hundred thousand vectors, and "
            "the index build time of the graph based engines is rarely worth paying for a "
            "personal dataset."),
    "cjk": ("中文分词与检索",
            "本文讨论中文全文检索中的分词问题。三元组索引无法匹配长度小于三个字符的查询，"
            "而两字词恰恰是中文查询里最常见的形式。用结巴分词把正文切开之后再交给 unicode61 "
            "分词器，就能补上这个盲区。文章最后比较了几种召回策略的差异。"),
}


async def _big_library(settings, n: int = 80):
    """A synthetic library large enough for the intent probe to discriminate."""
    from facetmark.db import now as _now
    from facetmark.db import open_db

    db = open_db(":memory:")
    ts = _now()
    for i in range(n):
        db.execute(
            "INSERT INTO bookmark(id, url, url_norm, url_hash, title, date_added, "
            "created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (i + 1, f"https://e{i}.example/p", f"https://e{i}.example/p", f"h{i}",
             f"topic {i} filler subject {i}", ts, ts, ts),
        )
        store_body(db, i + 1,
                   body=f"topic {i} filler subject {i}. " * 12 + f"unique{i} marker{i}.")
    db.commit()
    await embed_content(db, settings=settings)
    return db


@pytest.fixture
def loaded(conn, mock_settings):
    """A small library with bodies, ready to enrich."""
    from tests.conftest import NETSCAPE_SAMPLE

    import_bookmarks(conn, content=NETSCAPE_SAMPLE)
    rows = conn.execute("SELECT id FROM bookmark WHERE indexable=1 ORDER BY id").fetchall()
    for row, (title, body) in zip(rows, PAGES.values(), strict=False):
        conn.execute("UPDATE bookmark SET title=? WHERE id=?", (title, row["id"]))
        store_body(conn, row["id"], body=body, title=title, extractor="trafilatura")
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# providers
# ---------------------------------------------------------------------------


class TestMockProvider:
    async def test_it_is_deterministic(self, mock_settings):
        a = await MockProvider(mock_settings).embed(["hello world"])
        b = await MockProvider(mock_settings).embed(["hello world"])
        assert a == b

    async def test_vectors_are_unit_length_at_the_configured_dimension(self, mock_settings):
        vecs = await MockProvider(mock_settings).embed(["alpha beta", "中文 检索"])
        for v in vecs:
            assert len(v) == mock_settings.embed_dim
            assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, rel_tol=1e-6)

    async def test_shared_vocabulary_scores_closer_than_disjoint_vocabulary(self, mock_settings):
        p = MockProvider(mock_settings)
        a, b, c = await p.embed([
            "kubernetes deployment rollout strategy",
            "kubernetes deployment rolling update",
            "sourdough bread proofing schedule",
        ])
        dot = lambda x, y: sum(i * j for i, j in zip(x, y, strict=True))  # noqa: E731
        assert dot(a, b) > dot(a, c)

    async def test_it_is_lexical_not_semantic_and_the_docstring_says_so(self, mock_settings):
        # Guard against anyone later reading demo numbers as quality evidence.
        p = MockProvider(mock_settings)
        dog, canine, unrelated = await p.embed(["dog", "canine", "xylophone"])
        dot = lambda x, y: sum(i * j for i, j in zip(x, y, strict=True))  # noqa: E731
        assert dot(dog, canine) <= max(dot(dog, unrelated), 0.05)
        assert "feature hashing over lexical tokens" in MockProvider.__doc__

    async def test_an_empty_string_still_produces_a_usable_vector(self, mock_settings):
        v = (await MockProvider(mock_settings).embed([""]))[0]
        assert len(v) == mock_settings.embed_dim
        assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, rel_tol=1e-6)

    async def test_chat_returns_every_contracted_key(self, mock_settings):
        out = await MockProvider(mock_settings).chat_json("sys", "<<<PAGE>>>" + PAGES["kube"][1])
        assert set(out) >= {"summary", "key_points", "entities", "topics", "utility",
                            "content_type", "intent_queries"}
        assert len(out["intent_queries"]) == mock_settings.intent_generate_n

    async def test_usage_is_accumulated_so_cost_can_be_reported(self, mock_settings):
        p = MockProvider(mock_settings)
        await p.chat_json("s", "u" * 400)
        await p.embed(["x" * 400])
        u = p.usage.as_dict()
        assert u["calls"] == 2 and u["prompt_tokens"] > 0 and u["embed_tokens"] > 0


class TestProviderSelection:
    def test_mock_is_chosen_when_asked_for(self, mock_settings):
        assert isinstance(get_provider(mock_settings), MockProvider)

    def test_mock_is_chosen_when_there_is_no_key_rather_than_crashing(self, tmp_path):
        s = Settings(data_dir=tmp_path, use_mock_provider=False, api_key="")
        assert isinstance(get_provider(s), MockProvider)

    def test_a_key_selects_the_real_transport(self, tmp_path):
        s = Settings(data_dir=tmp_path, api_key="sk-test")
        assert isinstance(get_provider(s), OpenAICompatibleProvider)

    def test_constructing_the_real_provider_without_a_key_says_what_to_do(self, tmp_path):
        with pytest.raises(ProviderError, match="FACETMARK_API_KEY"):
            OpenAICompatibleProvider(Settings(data_dir=tmp_path, api_key=""))


class TestOpenAICompatibleTransport:
    @respx.mock
    async def test_a_chat_reply_is_parsed_and_usage_recorded(self, tmp_path):
        respx.post("https://api.example/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{"message": {"content": '{"summary":"s","intent_queries":["q1"]}'}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            })
        )
        p = OpenAICompatibleProvider(
            Settings(data_dir=tmp_path, api_key="sk-x", base_url="https://api.example/v1"))
        got = await p.chat_json("sys", "user")
        await p.aclose()
        assert got["summary"] == "s"
        assert p.usage.prompt_tokens == 100

    @respx.mock
    async def test_embeddings_are_returned_in_request_order(self, tmp_path):
        respx.post("https://api.example/v1/embeddings").mock(
            return_value=httpx.Response(200, json={
                "data": [{"index": 1, "embedding": [0.0, 1.0]},
                         {"index": 0, "embedding": [1.0, 0.0]}],
                "usage": {"total_tokens": 4},
            })
        )
        p = OpenAICompatibleProvider(
            Settings(data_dir=tmp_path, api_key="sk-x", base_url="https://api.example/v1",
                     embed_dim=2))
        got = await p.embed(["a", "b"])
        await p.aclose()
        assert got == [[1.0, 0.0], [0.0, 1.0]]

    @respx.mock
    async def test_a_dimension_mismatch_names_the_setting_to_change(self, tmp_path):
        respx.post("https://api.example/v1/embeddings").mock(
            return_value=httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0] * 8}]})
        )
        p = OpenAICompatibleProvider(
            Settings(data_dir=tmp_path, api_key="sk-x", base_url="https://api.example/v1",
                     embed_dim=1536))
        with pytest.raises(ProviderError, match="FACETMARK_EMBED_DIM=8"):
            await p.embed(["a"])
        await p.aclose()

    @respx.mock
    async def test_a_rate_limit_is_retried_and_a_bad_request_is_not(self, tmp_path):
        s = Settings(data_dir=tmp_path, api_key="sk-x", base_url="https://api.example/v1",
                     max_retries=3)
        route = respx.post("https://api.example/v1/chat/completions").mock(
            side_effect=[httpx.Response(429),
                         httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})]
        )
        p = OpenAICompatibleProvider(s)
        with pytest.raises(EnrichmentInvalid):
            coerce(await p.chat_json("s", "u"))   # retried, then returned {}
        assert route.call_count == 2

        respx.post("https://api.example/v1/embeddings").mock(return_value=httpx.Response(400))
        with pytest.raises(ProviderError, match="HTTP 400"):
            await p.embed(["a"])
        await p.aclose()

    @respx.mock
    async def test_exhausted_retries_raise_rather_than_return_garbage(self, tmp_path):
        respx.post("https://api.example/v1/chat/completions").mock(
            return_value=httpx.Response(503))
        p = OpenAICompatibleProvider(
            Settings(data_dir=tmp_path, api_key="sk-x", base_url="https://api.example/v1",
                     max_retries=2))
        with pytest.raises(ProviderError, match="failed after 2"):
            await p.chat_json("s", "u")
        await p.aclose()


class TestJsonRecovery:
    @pytest.mark.parametrize("text", [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        '```\n{"a": 1}\n```',
        'Sure! Here you go:\n{"a": 1}\nHope that helps.',
    ])
    def test_common_model_wrappers_are_unwrapped(self, text):
        assert parse_json_object(text) == {"a": 1}

    @pytest.mark.parametrize("text", ["", "no json here", "[1, 2, 3]"])
    def test_a_reply_with_no_object_is_an_error(self, text):
        with pytest.raises(ProviderError):
            parse_json_object(text)


# ---------------------------------------------------------------------------
# output coercion
# ---------------------------------------------------------------------------


class TestCoerce:
    def test_a_clean_reply_survives_intact(self):
        e = coerce({
            "summary": "A guide.", "key_points": ["p1", "p2"], "entities": ["Kubernetes"],
            "topics": ["devops"], "utility": "tutorial", "content_type": "docs",
            "intent_queries": ["how do i deploy", "rollback a bad release"],
        })
        assert e.utility == "tutorial" and e.content_type == "docs"
        assert e.entities == ["Kubernetes"]
        assert len(e.intent_queries) == 2

    def test_the_summary_is_capped_not_rejected(self):
        assert len(coerce({"summary": "x" * 500}).summary) == SUMMARY_MAX

    def test_a_string_where_a_list_was_asked_for_is_split(self):
        e = coerce({"summary": "s", "topics": "python; kubernetes; devops"})
        assert e.topics == ["python", "kubernetes", "devops"]

    def test_objects_inside_a_list_are_reduced_to_their_name(self):
        e = coerce({"summary": "s",
                    "entities": [{"name": "Qdrant", "type": "product"}, {"text": "Milvus"}]})
        assert e.entities == ["Qdrant", "Milvus"]

    def test_a_freeform_enum_is_snapped_to_the_allowed_set(self):
        assert coerce({"summary": "s", "utility": "Tutorial/guide"}).utility == "tutorial"
        assert coerce({"summary": "s", "utility": "vibes"}).utility == "other"

    def test_alternative_key_names_are_accepted(self):
        e = coerce({"abstract": "s", "tags": ["a"], "questions": ["how do i do the thing"]})
        assert e.summary == "s" and e.topics == ["a"]
        assert e.intent_queries == ["how do i do the thing"]

    def test_duplicate_entities_are_collapsed_case_insensitively(self):
        e = coerce({"summary": "s", "entities": ["Redis", "redis", "REDIS", "Valkey"]})
        assert e.entities == ["Redis", "Valkey"]

    def test_entity_casing_is_preserved_because_the_user_will_type_it(self):
        e = coerce({"summary": "s", "entities": ["sqlite-vec", "FastAPI", "gRPC"]})
        assert e.entities == ["sqlite-vec", "FastAPI", "gRPC"]

    def test_query_count_is_capped_at_the_configured_budget(self):
        e = coerce({"summary": "s", "intent_queries": [f"query number {i}" for i in range(30)]},
                   max_queries=8)
        assert len(e.intent_queries) == 8

    def test_a_reply_with_neither_summary_nor_queries_is_a_failure(self):
        with pytest.raises(EnrichmentInvalid):
            coerce({"topics": ["a"]})

    def test_a_non_object_is_a_failure(self):
        with pytest.raises(EnrichmentInvalid):
            coerce(["not", "an", "object"])


# ---------------------------------------------------------------------------
# pipeline
# ---------------------------------------------------------------------------


class TestEnrichPipeline:
    async def test_a_first_pass_enriches_everything_indexable(self, loaded, mock_settings):
        rep = await enrich_all(loaded, settings=mock_settings)
        n = loaded.execute("SELECT COUNT(*) c FROM bookmark WHERE indexable=1").fetchone()["c"]
        assert rep.enriched == n and rep.failed == 0
        assert rep.queries_generated == n * mock_settings.intent_generate_n
        row = loaded.execute("SELECT * FROM enrichment LIMIT 1").fetchone()
        assert row["summary"] and row["source_hash"] and row["model"] == "mock-chat"
        assert isinstance(jload(row["topics"], []), list)

    async def test_a_second_pass_costs_nothing(self, loaded, mock_settings):
        await enrich_all(loaded, settings=mock_settings)
        prov = MockProvider(mock_settings)
        rep = await enrich_all(loaded, provider=prov, settings=mock_settings)
        assert rep.considered == 0 and rep.enriched == 0
        assert prov.usage.calls == 0
        assert rep.skipped_unchanged > 0

    async def test_a_changed_body_re_enriches_only_that_page(self, loaded, mock_settings):
        await enrich_all(loaded, settings=mock_settings)
        bid = loaded.execute("SELECT id FROM bookmark ORDER BY id LIMIT 1").fetchone()["id"]
        store_body(loaded, bid, body="Something completely different now. " * 20)
        assert [t.bookmark_id for t in targets(loaded)] == [bid]
        prov = MockProvider(mock_settings)
        rep = await enrich_all(loaded, provider=prov, settings=mock_settings)
        assert rep.enriched == 1 and prov.usage.calls == 1

    async def test_force_re_enriches_regardless(self, loaded, mock_settings):
        await enrich_all(loaded, settings=mock_settings)
        rep = await enrich_all(loaded, settings=mock_settings, force=True)
        assert rep.enriched > 0

    async def test_a_privacy_excluded_page_never_reaches_a_model(self, loaded, mock_settings):
        bid = loaded.execute("SELECT id FROM bookmark ORDER BY id LIMIT 1").fetchone()["id"]
        loaded.execute("UPDATE bookmark SET privacy_skipped=1 WHERE id=?", (bid,))
        await enrich_all(loaded, settings=mock_settings)
        assert loaded.execute(
            "SELECT COUNT(*) c FROM enrichment WHERE bookmark_id=?", (bid,)
        ).fetchone()["c"] == 0

    async def test_a_page_with_no_body_is_still_enriched_from_its_title(
        self, conn, mock_settings
    ):
        from tests.conftest import NETSCAPE_SAMPLE

        import_bookmarks(conn, content=NETSCAPE_SAMPLE)
        rep = await enrich_all(conn, settings=mock_settings)
        assert rep.enriched > 0
        # ...and the title-only hash keeps it from being redone every run.
        prov = MockProvider(mock_settings)
        assert (await enrich_all(conn, provider=prov, settings=mock_settings)).enriched == 0
        assert prov.usage.calls == 0

    async def test_enrichment_text_reaches_both_lexical_indexes(self, loaded, mock_settings):
        await enrich_all(loaded, settings=mock_settings)
        row = loaded.execute("SELECT bookmark_id, summary FROM enrichment "
                             "WHERE summary != '' LIMIT 1").fetchone()
        word = next(w for w in row["summary"].split() if len(w) > 4)
        hits = loaded.execute("SELECT rowid FROM fts_seg WHERE fts_seg MATCH ?",
                              (f'"{word}"',)).fetchall()
        assert row["bookmark_id"] in {r["rowid"] for r in hits}

    async def test_a_failing_model_is_counted_not_raised(self, loaded, mock_settings):
        class Broken(Provider):
            name = "broken"

            async def chat_json(self, system, user):
                raise ProviderError("upstream is on fire")

            async def embed(self, texts):
                return []

        rep = await enrich_all(loaded, provider=Broken(mock_settings), settings=mock_settings)
        assert rep.failed == rep.considered and rep.enriched == 0
        assert rep.errors and "on fire" in rep.errors[0]

    async def test_re_enriching_replaces_candidate_queries_wholesale(self, loaded, mock_settings):
        await enrich_all(loaded, settings=mock_settings)
        before = loaded.execute("SELECT COUNT(*) c FROM intent_query").fetchone()["c"]
        await enrich_all(loaded, settings=mock_settings, force=True)
        after = loaded.execute("SELECT COUNT(*) c FROM intent_query").fetchone()["c"]
        assert before == after > 0

    def test_the_title_only_hash_is_stable_and_distinct(self):
        assert title_only_hash("a", "u") == title_only_hash("a", "u")
        assert title_only_hash("a", "u") != title_only_hash("b", "u")


# ---------------------------------------------------------------------------
# vectors
# ---------------------------------------------------------------------------


class TestVectors:
    def test_the_embedded_text_leads_with_the_title(self):
        t = content_text(title="T", summary="S", topics=["a"], entities=["B"], body="body text")
        assert t.startswith("T\nS\n")
        assert "a · B" in t

    async def test_content_vectors_are_written_once_per_bookmark(self, loaded, mock_settings):
        await enrich_all(loaded, settings=mock_settings)
        rep = await embed_content(loaded, settings=mock_settings)
        n = loaded.execute(
            "SELECT COUNT(*) c FROM bookmark WHERE indexable=1 AND privacy_skipped=0"
        ).fetchone()["c"]
        assert rep.content_written == n
        assert count_vectors(loaded)[0] == n

    async def test_a_second_embedding_pass_skips_what_exists(self, loaded, mock_settings):
        await enrich_all(loaded, settings=mock_settings)
        await embed_content(loaded, settings=mock_settings)
        prov = MockProvider(mock_settings)
        rep = await embed_content(loaded, provider=prov, settings=mock_settings)
        assert rep.content_written == 0 and prov.usage.calls == 0

    async def test_knn_finds_the_page_its_own_text_came_from(self, loaded, mock_settings):
        await enrich_all(loaded, settings=mock_settings)
        await embed_content(loaded, settings=mock_settings)
        prov = MockProvider(mock_settings)
        bid, title = loaded.execute(
            "SELECT b.id, b.title FROM bookmark b JOIN vec_content v ON v.bookmark_id=b.id LIMIT 1"
        ).fetchone()
        vec = (await prov.embed([title]))[0]
        assert knn_content(loaded, vec, 3)[0][0] == bid

    async def test_a_privacy_excluded_page_is_never_embedded(self, loaded, mock_settings):
        bid = loaded.execute("SELECT id FROM bookmark ORDER BY id LIMIT 1").fetchone()["id"]
        loaded.execute("UPDATE bookmark SET privacy_skipped=1 WHERE id=?", (bid,))
        await enrich_all(loaded, settings=mock_settings)
        await embed_content(loaded, settings=mock_settings)
        assert loaded.execute(
            "SELECT COUNT(*) c FROM vec_content WHERE bookmark_id=?", (bid,)
        ).fetchone()["c"] == 0

    async def test_a_model_or_dimension_change_is_refused_not_silently_mixed(
        self, loaded, mock_settings
    ):
        from facetmark.db import SchemaMismatch

        await embed_content(loaded, settings=mock_settings)
        with pytest.raises(SchemaMismatch):
            ensure_vec_tables(loaded, mock_settings.embed_dim, "some-other-model")
        with pytest.raises(SchemaMismatch):
            ensure_vec_tables(loaded, 999, mock_settings.embed_model)


# ---------------------------------------------------------------------------
# the intent filter
# ---------------------------------------------------------------------------


class TestIntentFilter:
    @pytest.fixture
    async def enriched(self, loaded, mock_settings):
        await enrich_all(loaded, settings=mock_settings)
        await embed_content(loaded, settings=mock_settings)
        return loaded

    async def test_the_probe_uses_content_and_lexical_only(self, enriched, mock_settings):
        # If the probe consulted the intent facet it would be scoring a query
        # against itself. Assert it works before any intent vector exists.
        assert count_vectors(enriched)[1] == 0
        prov = MockProvider(mock_settings)
        bid, title = enriched.execute(
            "SELECT id, title FROM bookmark WHERE title!='' LIMIT 1").fetchone()
        vec = (await prov.embed([title]))[0]
        assert bid in probe(enriched, title, vec, top_k=10)

    async def test_no_more_than_keep_n_survive_per_bookmark(self, enriched, mock_settings):
        rep = await filter_intents(enriched, settings=mock_settings)
        assert rep.candidates > 0
        per = enriched.execute(
            "SELECT bookmark_id, SUM(kept) k FROM intent_query GROUP BY bookmark_id").fetchall()
        assert all(r["k"] <= mock_settings.intent_keep_n for r in per)
        assert rep.kept + rep.dropped == rep.candidates

    async def test_every_candidate_gets_a_recorded_probe_rank_or_an_honest_null(
        self, enriched, mock_settings
    ):
        await filter_intents(enriched, settings=mock_settings)
        rows = enriched.execute("SELECT kept, probe_rank FROM intent_query").fetchall()
        assert rows
        for r in rows:
            if r["kept"]:
                assert r["probe_rank"] is not None
                assert r["probe_rank"] <= mock_settings.intent_probe_top_k

    async def test_a_query_that_cannot_find_its_own_page_is_dropped(
        self, mock_settings
    ):
        # Needs a library larger than the probe depth; see the next test for
        # why, and for what the filter does when that is not true.
        db = await _big_library(mock_settings, n=80)
        bid = db.execute("SELECT id FROM bookmark ORDER BY id LIMIT 1").fetchone()["id"]
        db.executemany(
            "INSERT INTO intent_query(bookmark_id, text, kept, created_at) VALUES(?,?,0,0)",
            [(bid, "zzzz qqqq unrelated gibberish token"),
             (bid, "xxxx wwww nothing here at all"),
             (bid, "topic 0 filler subject 0")],       # this one should survive
        )
        await filter_intents(db, settings=mock_settings, ids=[bid])
        rows = db.execute(
            "SELECT text, kept, probe_rank FROM intent_query WHERE bookmark_id=?", (bid,)
        ).fetchall()
        kept = {r["text"] for r in rows if r["kept"]}
        assert "zzzz qqqq unrelated gibberish token" not in kept
        assert "xxxx wwww nothing here at all" not in kept
        assert "topic 0 filler subject 0" in kept

    async def test_on_a_library_smaller_than_the_probe_depth_nothing_can_be_rejected(
        self, enriched, mock_settings
    ):
        # Documented degeneracy, asserted so it cannot regress into a surprise:
        # a KNN index has no distance floor, so in a three-document library
        # every query "finds" every document.
        n_docs = enriched.execute("SELECT COUNT(*) c FROM vec_content").fetchone()["c"]
        assert n_docs < mock_settings.intent_probe_top_k * 3
        bid = enriched.execute("SELECT id FROM bookmark LIMIT 1").fetchone()["id"]
        enriched.execute("DELETE FROM intent_query WHERE bookmark_id=?", (bid,))
        enriched.execute(
            "INSERT INTO intent_query(bookmark_id, text, kept, created_at) VALUES(?,?,0,0)",
            (bid, "zzzz qqqq unrelated gibberish token"))
        await filter_intents(enriched, settings=mock_settings, ids=[bid])
        assert enriched.execute(
            "SELECT kept FROM intent_query WHERE bookmark_id=?", (bid,)).fetchone()["kept"] == 1

    async def test_keep_n_is_a_hyperparameter_the_ablation_can_sweep(
        self, enriched, mock_settings
    ):
        counts = {}
        for n in (2, 4, 6):
            rep = await filter_intents(enriched, settings=mock_settings, keep_n=n)
            counts[n] = rep.kept
        assert counts[2] <= counts[4] <= counts[6]
        assert counts[2] < counts[6]

    async def test_only_survivors_get_vectors(self, enriched, mock_settings):
        await filter_intents(enriched, settings=mock_settings)
        await embed_intents(enriched, settings=mock_settings)
        kept = enriched.execute("SELECT COUNT(*) c FROM intent_query WHERE kept=1").fetchone()["c"]
        assert count_vectors(enriched)[1] == kept

    async def test_re_filtering_more_strictly_removes_the_now_rejected_vectors(
        self, enriched, mock_settings
    ):
        await filter_intents(enriched, settings=mock_settings, keep_n=6)
        await embed_intents(enriched, settings=mock_settings)
        wide = count_vectors(enriched)[1]
        await filter_intents(enriched, settings=mock_settings, keep_n=2)
        narrow = count_vectors(enriched)[1]
        assert narrow < wide
        assert narrow == enriched.execute(
            "SELECT COUNT(*) c FROM intent_query WHERE kept=1").fetchone()["c"]

    async def test_the_report_explains_where_the_candidates_went(
        self, enriched, mock_settings
    ):
        rep = (await filter_intents(enriched, settings=mock_settings)).as_dict()
        assert sum(rep["rank_histogram"].values()) == rep["candidates"]
        assert 0.0 <= rep["keep_rate"] <= 1.0

    async def test_filtering_an_empty_table_is_not_an_error(self, conn, mock_settings):
        rep = await filter_intents(conn, settings=mock_settings)
        assert rep.candidates == 0 and rep.kept == 0


# ---------------------------------------------------------------------------
# lexical facet + fusion (used by the probe, exercised again in P4)
# ---------------------------------------------------------------------------


class TestLexicalFacet:
    def test_a_two_character_cjk_query_is_answered_by_the_segmented_path_only(self, conn):
        from facetmark.text import sync_fts

        conn.execute(
            "INSERT INTO bookmark(id, url, url_norm, url_hash, title, created_at, updated_at) "
            "VALUES(1,'u','u','h','效率工具与提示词', 0, 0)")
        sync_fts(conn, 1, title="效率工具与提示词", body="一些关于效率工具的讨论")
        lists = lexical_lists(conn, "工具")
        assert lists.get("lex_seg") == [1]
        assert "lex_tri" not in lists          # trigram cannot see a 2-char query

    def test_a_three_character_cjk_query_is_answered_by_both(self, conn):
        from facetmark.text import sync_fts

        conn.execute(
            "INSERT INTO bookmark(id, url, url_norm, url_hash, title, created_at, updated_at) "
            "VALUES(1,'u','u','h','提示词工程', 0, 0)")
        sync_fts(conn, 1, title="提示词工程", body="提示词的写法")
        lists = lexical_lists(conn, "提示词")
        assert lists.get("lex_seg") == [1] and lists.get("lex_tri") == [1]

    def test_an_unmatched_query_yields_no_lists_rather_than_raising(self, conn):
        assert lexical_lists(conn, "nothingmatchesthis") == {}

    def test_punctuation_only_input_is_survivable(self, conn):
        assert lexical_lists(conn, "??? *** ^^^") == {}


class TestRRF:
    def test_a_document_ranked_by_two_facets_beats_one_ranked_higher_by_one(self):
        fused = rrf({"a": [10, 20], "b": [20, 30]})
        assert fused[0].doc_id == 20
        assert fused[0].facets == ["a", "b"]

    def test_the_score_matches_the_definition(self):
        fused = rrf({"a": [7]}, k=60)
        assert math.isclose(fused[0].score, 1 / 61)

    def test_duplicates_inside_one_list_do_not_double_count(self):
        assert math.isclose(rrf({"a": [5, 5, 5]})[0].score, 1 / 61)

    def test_a_zero_weight_facet_is_excluded_entirely(self):
        fused = rrf({"a": [1], "b": [2]}, weights={"b": 0.0})
        assert [f.doc_id for f in fused] == [1]

    def test_contributions_are_reported_so_a_result_can_explain_itself(self):
        f = rrf({"content": [3], "lex_seg": [3]})[0]
        assert set(f.contributions) == {"content", "lex_seg"}
        assert math.isclose(sum(f.contributions.values()), f.score)

    def test_empty_input_is_an_empty_ranking(self):
        assert rrf({}) == [] and rrf({"a": []}) == []


class TestFullIndexingPass:
    async def test_the_documented_order_runs_end_to_end_offline(self, loaded, mock_settings):
        e = await enrich_all(loaded, settings=mock_settings)
        c = await embed_content(loaded, settings=mock_settings)
        f = await filter_intents(loaded, settings=mock_settings)
        i = await embed_intents(loaded, settings=mock_settings)
        assert e.enriched == c.content_written > 0
        assert f.candidates == e.queries_generated
        assert i.intent_written == f.kept
        n_content, n_intent = count_vectors(loaded)
        assert n_content == c.content_written and n_intent == f.kept

    async def test_it_is_fully_idempotent(self, loaded, mock_settings):
        for _ in range(2):
            await enrich_all(loaded, settings=mock_settings)
            await embed_content(loaded, settings=mock_settings)
            await filter_intents(loaded, settings=mock_settings)
            await embed_intents(loaded, settings=mock_settings)
        prov = MockProvider(mock_settings)
        assert (await enrich_all(loaded, provider=prov, settings=mock_settings)).enriched == 0
        assert (await embed_content(loaded, provider=prov,
                                    settings=mock_settings)).content_written == 0
        assert prov.usage.calls == 0

    async def test_it_runs_on_an_empty_library_without_complaint(self, mock_settings):
        empty = open_db(":memory:")
        assert (await enrich_all(empty, settings=mock_settings)).considered == 0
        assert (await embed_content(empty, settings=mock_settings)).content_written == 0
        assert (await filter_intents(empty, settings=mock_settings)).candidates == 0
