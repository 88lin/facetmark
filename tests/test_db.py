"""Storage layer: schema, meta pinning and the sqlite-vec adapter."""

from __future__ import annotations

import math
import sqlite3

import pytest

from facetmark.db import (
    SchemaMismatch,
    count_vectors,
    ensure_vec_tables,
    get_meta,
    jdump,
    jload,
    knn_content,
    knn_intent,
    open_db,
    set_meta,
    upsert_content_vector,
    upsert_intent_vector,
    vec_tables_exist,
)

DIM = 8


def _unit(*vals: float) -> list[float]:
    v = list(vals) + [0.0] * (DIM - len(vals))
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _add_bookmarks(conn, n):
    for i in range(1, n + 1):
        conn.execute(
            "INSERT INTO bookmark(id, url, url_norm, url_hash, created_at, updated_at)"
            " VALUES(?,?,?,?,0,0)",
            (i, f"https://e.com/{i}", f"https://e.com/{i}", f"h{i}"),
        )


class TestSchema:
    def test_all_expected_tables_exist(self, conn):
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        for t in (
            "meta", "bookmark", "content", "enrichment", "intent_query",
            "session", "bookmark_session", "edge", "health", "interaction",
            "fts_tri", "fts_seg",
        ):
            assert t in names, f"missing table {t}"

    def test_schema_version_is_recorded(self, conn):
        assert get_meta(conn, "schema_version") == "1"

    def test_init_is_idempotent(self, tmp_path):
        p = tmp_path / "a.db"
        open_db(p).close()
        c = open_db(p)  # second call must not raise
        assert get_meta(c, "schema_version") == "1"
        c.close()

    def test_foreign_keys_cascade(self, conn):
        _add_bookmarks(conn, 1)
        conn.execute(
            "INSERT INTO content(bookmark_id, body_text) VALUES(1,'x')"
        )
        conn.execute("DELETE FROM bookmark WHERE id=1")
        assert conn.execute("SELECT count(*) FROM content").fetchone()[0] == 0

    def test_url_hash_is_unique(self, conn):
        _add_bookmarks(conn, 1)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO bookmark(url, url_norm, url_hash, created_at, updated_at)"
                " VALUES('x','x','h1',0,0)"
            )


class TestMeta:
    def test_set_and_get(self, conn):
        set_meta(conn, "k", "v")
        assert get_meta(conn, "k") == "v"

    def test_upsert_overwrites(self, conn):
        set_meta(conn, "k", "a")
        set_meta(conn, "k", "b")
        assert get_meta(conn, "k") == "b"

    def test_missing_key_returns_none(self, conn):
        assert get_meta(conn, "nope") is None


class TestVectorAdapter:
    def test_tables_are_created_lazily(self, conn):
        assert not vec_tables_exist(conn)
        ensure_vec_tables(conn, DIM, "m")
        assert vec_tables_exist(conn)

    def test_dimension_and_model_are_pinned(self, conn):
        ensure_vec_tables(conn, DIM, "model-a")
        assert get_meta(conn, "embed_dim") == str(DIM)
        assert get_meta(conn, "embed_model") == "model-a"

    def test_dimension_change_is_a_hard_error(self, conn):
        ensure_vec_tables(conn, DIM, "model-a")
        with pytest.raises(SchemaMismatch, match="embed_dim"):
            ensure_vec_tables(conn, DIM + 1, "model-a")

    def test_model_change_is_a_hard_error(self, conn):
        ensure_vec_tables(conn, DIM, "model-a")
        with pytest.raises(SchemaMismatch, match="embed_model"):
            ensure_vec_tables(conn, DIM, "model-b")

    def test_repeated_ensure_with_same_params_is_fine(self, conn):
        ensure_vec_tables(conn, DIM, "m")
        ensure_vec_tables(conn, DIM, "m")
        assert vec_tables_exist(conn)

    def test_knn_orders_by_similarity(self, conn):
        _add_bookmarks(conn, 3)
        ensure_vec_tables(conn, DIM, "m")
        upsert_content_vector(conn, 1, _unit(1, 0, 0))
        upsert_content_vector(conn, 2, _unit(0, 1, 0))
        upsert_content_vector(conn, 3, _unit(0.9, 0.1, 0))
        hits = knn_content(conn, _unit(1, 0, 0), 3)
        assert [h[0] for h in hits[:2]] == [1, 3]
        assert hits[0][1] < hits[1][1] < hits[2][1]

    def test_vectors_are_normalised_on_write(self, conn):
        """Ranking must not depend on the caller's vector magnitude."""
        _add_bookmarks(conn, 2)
        ensure_vec_tables(conn, DIM, "m")
        upsert_content_vector(conn, 1, [3.0, 0, 0, 0, 0, 0, 0, 0])
        upsert_content_vector(conn, 2, [0.01, 0, 0, 0, 0, 0, 0, 0])
        hits = dict(knn_content(conn, _unit(1, 0, 0), 2))
        assert math.isclose(hits[1], hits[2], abs_tol=1e-5)

    def test_zero_vector_does_not_raise(self, conn):
        _add_bookmarks(conn, 1)
        ensure_vec_tables(conn, DIM, "m")
        upsert_content_vector(conn, 1, [0.0] * DIM)
        assert knn_content(conn, _unit(1, 0, 0), 1)

    def test_upsert_replaces_rather_than_duplicates(self, conn):
        _add_bookmarks(conn, 1)
        ensure_vec_tables(conn, DIM, "m")
        upsert_content_vector(conn, 1, _unit(1, 0))
        upsert_content_vector(conn, 1, _unit(0, 1))
        assert count_vectors(conn)[0] == 1
        assert knn_content(conn, _unit(0, 1), 1)[0][1] < 1e-5

    def test_intent_vectors_are_a_separate_space(self, conn):
        _add_bookmarks(conn, 1)
        ensure_vec_tables(conn, DIM, "m")
        conn.execute(
            "INSERT INTO intent_query(id, bookmark_id, text, kept) VALUES(10,1,'q',1)"
        )
        upsert_intent_vector(conn, 10, _unit(1, 0))
        assert count_vectors(conn) == (0, 1)
        assert knn_intent(conn, _unit(1, 0), 1)[0][0] == 10

    def test_counts_are_zero_before_tables_exist(self, conn):
        assert count_vectors(conn) == (0, 0)

    def test_k_larger_than_corpus(self, conn):
        _add_bookmarks(conn, 2)
        ensure_vec_tables(conn, DIM, "m")
        upsert_content_vector(conn, 1, _unit(1, 0))
        upsert_content_vector(conn, 2, _unit(0, 1))
        assert len(knn_content(conn, _unit(1, 0), 50)) == 2


class TestJsonHelpers:
    def test_round_trip_preserves_cjk(self):
        assert jload(jdump(["中文", "a"])) == ["中文", "a"]

    def test_dump_does_not_escape_cjk(self):
        assert "中文" in jdump({"k": "中文"})

    def test_load_handles_none_and_garbage(self):
        assert jload(None) == []
        assert jload("") == []
        assert jload("{not json") == []
        assert jload("{not json", default={}) == {}
