"""Storage layer: schema, meta pinning and the sqlite-vec adapter."""

from __future__ import annotations

import json
import math
import sqlite3

import pytest

from facetmark.db import (
    SCHEMA_VERSION,
    SchemaMismatch,
    SchemaTooNew,
    apply_pending,
    connect,
    count_vectors,
    ensure_vec_tables,
    get_meta,
    jdump,
    jload,
    knn_content,
    knn_intent,
    open_db,
    schema_status,
    set_meta,
    upsert_content_vector,
    upsert_intent_vector,
    vec_tables_exist,
)
from facetmark.migrations import MIGRATIONS, backup_database

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
        assert get_meta(conn, "schema_version") == str(SCHEMA_VERSION)

    def test_init_is_idempotent(self, tmp_path):
        p = tmp_path / "a.db"
        open_db(p).close()
        c = open_db(p)  # second call must not raise
        assert get_meta(c, "schema_version") == str(SCHEMA_VERSION)
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


# ---------------------------------------------------------------------------
# migrations
# ---------------------------------------------------------------------------


def _write_v1(path) -> None:
    """A database as v1 wrote it, stamped ``1``.

    Built by reversing the later migrations rather than by keeping a paste of
    the old SCHEMA_SQL around, which would rot the first time anything
    unrelated changed. What has to be true is only that what v2 onwards add is
    genuinely absent.
    """
    c = open_db(path)
    c.execute("DROP INDEX IF EXISTS ix_fetch_queue_ready")
    c.execute("ALTER TABLE fetch_queue DROP COLUMN next_attempt_at")
    c.execute("DROP TABLE IF EXISTS vec_content_meta")
    c.execute("DROP INDEX IF EXISTS ix_intent_unscored")   # indexed columns cannot be dropped
    c.execute("ALTER TABLE intent_query DROP COLUMN scored_at")
    c.execute("ALTER TABLE enrichment DROP COLUMN basis")
    c.execute("ALTER TABLE bookmark DROP COLUMN tags")
    _add_bookmarks(c, 3)
    c.execute(
        "INSERT INTO fetch_queue(bookmark_id, reason, state, attempts, queued_at)"
        " VALUES(1,'wall','pending',1,100)"
    )
    # The three cases v4 has to tell apart, written the way v1 wrote them.
    c.executemany(
        "INSERT INTO intent_query(bookmark_id, text, kept, probe_rank, created_at)"
        " VALUES(?,?,?,?,500)",
        [(1, "kept, so certainly probed", 1, 2),
         (1, "rejected, but it recorded a rank", 0, 7),
         (2, "no rank, no flag, no evidence", 0, None)],
    )
    # The three cases v5 has to tell apart: a summary written from a fetched
    # body (hash is the body hash), one written from the title alone (the
    # t:-prefixed fingerprint), and one the karakeep bridge claimed.
    c.executemany(
        "INSERT INTO enrichment(bookmark_id, summary, source_hash, model, created_at)"
        " VALUES(?,?,?,?,400)",
        [(1, "written from the body", "body-hash-1", "old",),
         (2, "inferred from the title", "t:abc123", "old"),
         (3, "imported by the bridge", "karakeep", "karakeep")],
    )
    set_meta(c, "schema_version", "1")
    c.close()


def _shape(conn) -> dict:
    """Every table's columns and indexes, as a comparable structure."""
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    out = {}
    for t in tables:
        cols = [(r[1], r[2], r[3], r[4], r[5]) for r in conn.execute(f"PRAGMA table_info({t})")]
        idx = sorted(
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? "
                "AND name NOT LIKE 'sqlite_%'", (t,)
            )
        )
        out[t] = {"columns": cols, "indexes": idx}
    return out


class TestMigrations:
    def test_a_new_database_is_born_at_the_current_version(self, tmp_path):
        c = open_db(tmp_path / "new.db")
        st = schema_status(c)
        assert st.found == SCHEMA_VERSION
        assert st.current and not st.pending
        c.close()

    def test_an_old_database_reports_what_it_is_missing(self, tmp_path):
        p = tmp_path / "old.db"
        _write_v1(p)
        c = connect(p)
        st = schema_status(c)
        assert st.found == 1
        assert [m.version for m in st.pending] == [
            m.version for m in MIGRATIONS if m.version > 1
        ]
        assert not st.current
        c.close()

    def test_opening_an_old_database_upgrades_it(self, tmp_path):
        p = tmp_path / "old.db"
        _write_v1(p)
        c = open_db(p)
        assert get_meta(c, "schema_version") == str(SCHEMA_VERSION)
        cols = {r[1] for r in c.execute("PRAGMA table_info(fetch_queue)")}
        assert "next_attempt_at" in cols
        c.close()

    def test_the_upgrade_keeps_the_rows_it_found(self, tmp_path):
        p = tmp_path / "old.db"
        _write_v1(p)
        c = open_db(p)
        assert c.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 3
        row = c.execute("SELECT state, attempts, next_attempt_at FROM fetch_queue").fetchone()
        assert (row[0], row[1], row[2]) == ("pending", 1, None)
        c.close()

    def test_the_backfill_only_claims_what_it_can_prove(self, tmp_path):
        """A rejection and an omission look identical, so only evidence counts."""
        p = tmp_path / "old.db"
        _write_v1(p)
        c = open_db(p)
        got = {
            r["text"]: r["scored_at"]
            for r in c.execute("SELECT text, scored_at FROM intent_query")
        }
        assert got["kept, so certainly probed"] == 500
        assert got["rejected, but it recorded a rank"] == 500
        assert got["no rank, no flag, no evidence"] is None
        c.close()

    def test_v5_backfills_the_summary_basis_from_the_fingerprint(self, tmp_path):
        """The t: prefix is the only honest record of a title-only enrichment."""
        p = tmp_path / "old.db"
        _write_v1(p)
        c = open_db(p)
        got = {
            r["bookmark_id"]: r["basis"]
            for r in c.execute("SELECT bookmark_id, basis FROM enrichment")
        }
        assert got == {1: "body", 2: "title", 3: "body"}
        c.close()

    def test_a_migrated_database_is_shaped_like_a_fresh_one(self, tmp_path):
        """The guard against SCHEMA_SQL and the migration list drifting apart."""
        old = tmp_path / "old.db"
        _write_v1(old)
        migrated = open_db(old)
        fresh = open_db(tmp_path / "fresh.db")
        assert _shape(migrated) == _shape(fresh)
        migrated.close()
        fresh.close()

    def test_the_upgrade_leaves_the_old_file_behind(self, tmp_path):
        p = tmp_path / "old.db"
        _write_v1(p)
        open_db(p).close()
        saved = tmp_path / "old.db.bak-v1"
        assert saved.exists()
        c = connect(saved)
        assert schema_status(c).found == 1
        assert c.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0] == 3
        c.close()

    def test_the_backup_can_be_declined(self, tmp_path):
        p = tmp_path / "old.db"
        _write_v1(p)
        c = connect(p)
        apply_pending(c, backup=False)
        c.close()
        assert not (tmp_path / "old.db.bak-v1").exists()

    def test_a_database_from_the_future_is_refused(self, tmp_path):
        p = tmp_path / "future.db"
        c = open_db(p)
        set_meta(c, "schema_version", str(SCHEMA_VERSION + 5))
        c.close()
        with pytest.raises(SchemaTooNew, match="Upgrade facetmark"):
            open_db(p)

    def test_migrating_can_be_refused_so_a_caller_can_decide(self, tmp_path):
        p = tmp_path / "old.db"
        _write_v1(p)
        with pytest.raises(RuntimeError, match="facetmark migrate"):
            open_db(p, migrate=False)
        c = connect(p)
        assert schema_status(c).found == 1  # untouched
        c.close()

    def test_applying_twice_is_a_no_op(self, tmp_path):
        p = tmp_path / "old.db"
        _write_v1(p)
        c = open_db(p)
        done, saved = apply_pending(c)
        assert done == [] and saved is None
        c.close()

    def test_every_migration_lands_on_the_version_after_the_last(self):
        seen = 1
        for m in MIGRATIONS:
            assert m.version == seen + 1, f"gap or reorder at v{m.version}"
            assert m.note, "a migration with no note is unreviewable"
            seen = m.version
        assert seen == SCHEMA_VERSION

    def test_an_in_memory_database_has_nothing_to_back_up(self, conn):
        assert backup_database(conn, suffix="bak") is None


class TestMigrateCommand:
    def _run(self, *args):
        from typer.testing import CliRunner

        from facetmark.cli import app

        return CliRunner().invoke(app, ["migrate", *args])

    def test_check_reports_pending_and_exits_non_zero(self, tmp_path):
        p = tmp_path / "old.db"
        _write_v1(p)
        r = self._run("--db", str(p), "--check")
        assert r.exit_code == 1
        assert "pending" in r.stdout
        c = connect(p)
        assert schema_status(c).found == 1  # --check changed nothing
        c.close()

    def test_check_on_a_current_database_exits_zero(self, tmp_path):
        p = tmp_path / "new.db"
        open_db(p).close()
        r = self._run("--db", str(p), "--check")
        assert r.exit_code == 0
        assert "up to date" in r.stdout

    def test_check_does_not_create_a_database(self, tmp_path):
        p = tmp_path / "nothing-here.db"
        r = self._run("--db", str(p), "--check")
        assert r.exit_code == 0
        assert not p.exists()

    def test_it_upgrades_and_says_what_it_did(self, tmp_path):
        p = tmp_path / "old.db"
        _write_v1(p)
        r = self._run("--db", str(p), "--no-backup", "--json")
        assert r.exit_code == 0
        payload = json.loads(r.stdout)
        assert payload["from"] == 1
        assert payload["to"] == SCHEMA_VERSION
        assert [a["version"] for a in payload["applied"]] == [
            m.version for m in MIGRATIONS if m.version > 1
        ]
        assert payload["backup"] is None


class TestV6Tags:
    """v6 gives bookmarks a tags column; the importer fills it, migration just
    makes the column exist so the INSERT does not explode on an old file."""

    def test_v6_adds_the_column_to_an_old_database(self, tmp_path):
        p = tmp_path / "old.db"
        _write_v1(p)
        c = open_db(p)
        cols = {r[1] for r in c.execute("PRAGMA table_info(bookmark)")}
        assert "tags" in cols
        # Born empty, and readable as JSON the moment a row exists.
        val = c.execute("SELECT tags FROM bookmark WHERE id=1").fetchone()[0]
        assert val == "[]"
        c.close()

    def test_the_migration_is_repairable_by_hand(self, tmp_path):
        """A migration that checks before it acts can be re-run safely."""
        p = tmp_path / "old.db"
        _write_v1(p)
        c = open_db(p)
        c.close()
        # Opening again finds the version already current; no error, no change.
        c2 = open_db(p)
        assert schema_status(c2).current
        c2.close()
