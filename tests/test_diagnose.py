"""``facetmark doctor``: the checks, and the promise that it only reads.

The scenarios here are the ones that actually happen and that nothing else in
the product explains: a library that was never indexed, vectors built at a
dimension the settings no longer name, a database a newer build wrote. Each
assertion is on the *finding*, not on the wording -- the message is prose and
should stay free to improve.
"""

from __future__ import annotations

import json

import pytest

from facetmark.config import Settings
from facetmark.db import ensure_vec_tables, open_db, set_meta
from facetmark.diagnose import Check, run_checks, worst
from facetmark.text import sync_fts

BASE = {
    "use_mock_provider": False,
    "embed_model": "text-embedding-3-small",
    "chat_model": "gpt-4o-mini",
    "health_enable_external": False,
    "api_key": "sk-test",
}


def st_for(tmp_path, **over) -> Settings:
    return Settings(data_dir=tmp_path, **{**BASE, "embed_dim": 1536, **over})


def named(checks: list[Check], name: str) -> Check | None:
    return next((c for c in checks if c.name == name), None)


def add_bookmark(conn, i: int, *, index: bool = True) -> None:
    conn.execute(
        "INSERT INTO bookmark(id,url,url_norm,url_hash,title,date_added,source,"
        "indexable,created_at,updated_at) VALUES(?,?,?,?,?,?,'api',1,1,1)",
        (i, f"https://e{i}.test/", f"https://e{i}.test/", f"h{i}", f"page {i}", 1),
    )
    if index:
        sync_fts(conn, i, title=f"page {i}", body="some body text")


class TestAFreshInstall:
    def test_nothing_is_an_error(self, tmp_path):
        """An empty library is incomplete, not broken, and must not read as
        broken -- a doctor that cries error on a first run teaches people to
        ignore it."""
        st = st_for(tmp_path)
        conn = open_db(st.db_path)
        try:
            checks = run_checks(conn, st)
        finally:
            conn.close()
        assert worst(checks) != "error", [c for c in checks if c.status == "error"]
        assert named(checks, "library").status == "warn"
        assert named(checks, "schema").status == "ok"

    def test_it_says_where_the_config_file_is(self, tmp_path):
        st = st_for(tmp_path)
        conn = open_db(st.db_path)
        try:
            checks = run_checks(conn, st)
        finally:
            conn.close()
        assert "config.toml" in named(checks, "config.file").message


class TestTheFailuresNothingElseExplains:
    def test_vectors_built_at_another_dimension(self, tmp_path):
        """The README warns that changing `embed_dim` invalidates every stored
        vector. Until now the only thing that said so was a `SchemaMismatch`
        raised on the next write, an hour into an index run."""
        st = st_for(tmp_path, embed_dim=64)
        conn = open_db(st.db_path)
        ensure_vec_tables(conn, 64, "text-embedding-3-small")
        add_bookmark(conn, 1)
        conn.commit()
        try:
            checks = run_checks(conn, st_for(tmp_path, embed_dim=1536))
        finally:
            conn.close()
        c = named(checks, "vectors.dim")
        assert c is not None and c.status == "error"
        assert "reindex" in c.message

    def test_vectors_built_with_another_model(self, tmp_path):
        st = st_for(tmp_path)
        conn = open_db(st.db_path)
        ensure_vec_tables(conn, 1536, "bge-m3")
        conn.commit()
        try:
            checks = run_checks(conn, st)
        finally:
            conn.close()
        assert named(checks, "vectors.model").status == "error"

    def test_a_library_that_was_never_indexed(self, tmp_path):
        st = st_for(tmp_path)
        conn = open_db(st.db_path)
        for i in range(1, 11):
            add_bookmark(conn, i, index=False)
        conn.commit()
        try:
            checks = run_checks(conn, st)
        finally:
            conn.close()
        assert named(checks, "lexical.fts_seg").status == "error"
        assert named(checks, "lexical.fts_tri").status == "error"
        assert "reindex" in named(checks, "lexical.fts_seg").message

    def test_an_indexed_library_is_quiet_about_its_indexes(self, tmp_path):
        st = st_for(tmp_path)
        conn = open_db(st.db_path)
        for i in range(1, 11):
            add_bookmark(conn, i)
        conn.commit()
        try:
            checks = run_checks(conn, st)
        finally:
            conn.close()
        assert named(checks, "lexical.fts_seg").status == "ok"

    def test_a_database_behind_this_build(self, tmp_path):
        st = st_for(tmp_path)
        conn = open_db(st.db_path)
        set_meta(conn, "schema_version", "3")
        conn.commit()
        try:
            checks = run_checks(conn, st)
        finally:
            conn.close()
        c = named(checks, "schema")
        assert c.status == "error" and "migrate" in c.message

    def test_a_database_from_the_future(self, tmp_path):
        st = st_for(tmp_path)
        conn = open_db(st.db_path)
        set_meta(conn, "schema_version", "999")
        conn.commit()
        try:
            checks = run_checks(conn, st)
        finally:
            conn.close()
        assert named(checks, "schema").status == "error"

    def test_an_empty_vector_table_is_called_out(self, tmp_path):
        """What a chat-only endpoint looks like: the tables exist because the
        settings promised vectors, and nothing ever landed in them."""
        st = st_for(tmp_path)
        conn = open_db(st.db_path)
        ensure_vec_tables(conn, 1536, "text-embedding-3-small")
        add_bookmark(conn, 1)
        conn.commit()
        try:
            checks = run_checks(conn, st)
        finally:
            conn.close()
        assert named(checks, "vectors").status == "warn"
        assert "/embeddings" in named(checks, "vectors").message

    def test_no_key_and_no_local_backend(self, tmp_path):
        st = st_for(tmp_path, api_key="")
        conn = open_db(st.db_path)
        try:
            checks = run_checks(conn, st)
        finally:
            conn.close()
        assert named(checks, "provider.embed").status == "warn"

    def test_the_mock_provider_is_flagged(self, tmp_path):
        st = Settings(data_dir=tmp_path, use_mock_provider=True,
                      health_enable_external=False)
        conn = open_db(st.db_path)
        try:
            checks = run_checks(conn, st)
        finally:
            conn.close()
        assert named(checks, "provider").status == "warn"


class TestItOnlyReads:
    """hister's `doctor` promises it repairs nothing. So does this one."""

    def test_running_it_changes_nothing_in_the_database(self, tmp_path):
        st = st_for(tmp_path)
        conn = open_db(st.db_path)
        for i in range(1, 4):
            add_bookmark(conn, i)
        conn.commit()

        def snapshot():
            objects = sorted(
                (r[0], r[1]) for r in conn.execute(
                    "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")
            )
            rows = {
                t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for k, t in objects if k == "table"
            }
            meta = sorted(tuple(r) for r in conn.execute("SELECT key, value FROM meta"))
            return objects, rows, meta

        before = snapshot()
        run_checks(conn, st)
        run_checks(conn, st)
        assert snapshot() == before
        conn.close()

    def test_it_leaves_no_probe_file_behind(self, tmp_path):
        """The data-dir check writes to prove it can, then takes it back."""
        st = st_for(tmp_path)
        conn = open_db(st.db_path)
        try:
            run_checks(conn, st)
        finally:
            conn.close()
        assert not list(tmp_path.glob(".facetmark-write-probe"))


class TestTheCommand:
    def _run(self, args, tmp_path, monkeypatch):
        from typer.testing import CliRunner

        from facetmark import cli
        from facetmark.config import reset_settings

        monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("FACETMARK_USE_MOCK_PROVIDER", "1")
        # `get_settings()` is a process-wide singleton, so a sibling test that
        # built it first would otherwise hand this one that test's data dir --
        # and the command would report on a library this test never wrote.
        reset_settings()
        try:
            return CliRunner().invoke(cli.app, args)
        finally:
            reset_settings()

    def test_a_healthy_enough_install_exits_zero(self, tmp_path, monkeypatch):
        r = self._run(["doctor"], tmp_path, monkeypatch)
        assert r.exit_code == 0, r.output

    def test_an_error_exits_non_zero(self, tmp_path, monkeypatch):
        st = Settings(data_dir=tmp_path, use_mock_provider=True,
                      health_enable_external=False)
        conn = open_db(st.db_path)
        set_meta(conn, "schema_version", "3")
        conn.commit()
        conn.close()
        r = self._run(["doctor"], tmp_path, monkeypatch)
        assert r.exit_code == 1, r.output

    def test_json_is_a_status_and_a_list(self, tmp_path, monkeypatch):
        r = self._run(["doctor", "--json"], tmp_path, monkeypatch)
        payload = json.loads(r.stdout)
        assert payload["status"] in {"ok", "warn", "error"}
        assert payload["checks"] and all(
            set(c) == {"name", "status", "message"} for c in payload["checks"]
        )


@pytest.mark.parametrize("statuses,expected", [
    ([], "ok"),
    (["ok", "ok"], "ok"),
    (["ok", "warn"], "warn"),
    (["warn", "error", "ok"], "error"),
])
def test_worst_picks_the_worst(statuses, expected):
    assert worst([Check(f"c{i}", s, "") for i, s in enumerate(statuses)]) == expected
