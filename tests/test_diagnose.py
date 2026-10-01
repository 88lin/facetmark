"""``facetmark doctor``: the checks, and the promise that it only reads.

The scenarios here are the ones that actually happen and that nothing else in
the product explains: a library that was never indexed, vectors built at a
dimension the settings no longer name, a database a newer build wrote. Each
assertion is on the *finding*, not on the wording -- the message is prose and
should stay free to improve.
"""

from __future__ import annotations

import json
from collections import namedtuple

import pytest

from facetmark.config import Settings
from facetmark.db import ensure_vec_tables, open_db, set_meta
from facetmark.diagnose import Check, check_provider, check_vectors, run_checks, worst
from facetmark.enrich.vectors import embed_content
from facetmark.providers import MockProvider, ProviderError
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


@pytest.fixture
def vector_library(tmp_path):
    st = st_for(tmp_path, embed_dim=8, use_mock_provider=True)
    conn = open_db(st.db_path)
    try:
        yield conn, st
    finally:
        conn.close()


class TestVectorCoverage:
    async def test_interrupted_embedding_is_reported_and_resumes_remaining_work(self, vector_library):
        conn, st = vector_library
        for i in range(1, 71):
            add_bookmark(conn, i)

        class FailsOnSecondBatch(MockProvider):
            batches = 0

            async def embed(self, texts):
                self.batches += 1
                if self.batches == 2:
                    raise ProviderError("simulated outage after the first batch")
                return await super().embed(texts)

        with pytest.raises(ProviderError, match="simulated outage"):
            await embed_content(conn, settings=st, provider=FailsOnSecondBatch(st))
        c = named(check_vectors(conn, st), "vectors.coverage")
        assert c.status == "warn" and "64 of 70" in c.message and "6 missing" in c.message

        report = await embed_content(conn, settings=st)
        assert report.content_written == 6 and report.content_current == 64
        c = named(check_vectors(conn, st), "vectors.coverage")
        assert c.status == "ok" and "70 of 70" in c.message

    async def test_one_vector_for_two_hundred_pages_is_incomplete(self, vector_library):
        conn, st = vector_library
        for i in range(1, 201):
            add_bookmark(conn, i)
        await embed_content(conn, settings=st, ids=[1])
        before = conn.total_changes
        checks = check_vectors(conn, st)
        c = named(checks, "vectors.coverage")
        assert c is not None and c.status == "warn"
        assert "1 of 200" in c.message and "199 missing" in c.message
        assert "facetmark index" in c.message
        assert conn.total_changes == before

    async def test_existing_vectors_can_be_stale(self, vector_library):
        conn, st = vector_library
        add_bookmark(conn, 1)
        await embed_content(conn, settings=st)
        conn.execute("UPDATE bookmark SET title='changed after indexing' WHERE id=1")
        c = named(check_vectors(conn, st), "vectors.coverage")
        assert c is not None and c.status == "warn"
        assert "0 missing" in c.message and "1 stale" in c.message

    async def test_excluded_and_empty_pages_are_not_missing_work(self, vector_library):
        conn, st = vector_library
        for i in range(1, 5):
            add_bookmark(conn, i)
        conn.execute("UPDATE bookmark SET privacy_skipped=1 WHERE id=2")
        conn.execute("UPDATE bookmark SET indexable=0 WHERE id=3")
        conn.execute("UPDATE bookmark SET title='' WHERE id=4")
        await embed_content(conn, settings=st)
        c = named(check_vectors(conn, st), "vectors.coverage")
        assert c is not None and c.status == "ok"
        assert "1 of 1" in c.message

    async def test_a_missing_fingerprint_is_not_proof_of_freshness(self, vector_library):
        conn, st = vector_library
        add_bookmark(conn, 1)
        await embed_content(conn, settings=st)
        conn.execute("DELETE FROM vec_content_meta")
        c = named(check_vectors(conn, st), "vectors.coverage")
        assert c is not None and c.status == "warn" and "1 stale" in c.message

    async def test_an_old_schema_is_reported_without_migrating_it(self, vector_library):
        conn, st = vector_library
        add_bookmark(conn, 1)
        await embed_content(conn, settings=st)
        conn.execute("DROP TABLE vec_content_meta")
        c = named(check_vectors(conn, st), "vectors.coverage")
        assert c is not None and c.status == "warn"
        assert "could not check" in c.message
        assert not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='vec_content_meta'"
        ).fetchone()


def test_a_set_key_does_not_claim_the_provider_was_verified(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("doctor must not initialize or contact a provider")

    monkeypatch.setattr("facetmark.providers.get_provider", forbidden)
    st = st_for(tmp_path, api_key="sk-invalid-example", base_url="http://127.0.0.1:9")
    c = named(check_provider(st), "provider.embed")
    assert c.status == "ok"  # The key is present; its validity is unknown.
    assert "not tested" in c.message
    assert st.api_key not in c.message


@pytest.mark.parametrize("free,status", [(0, "error"), (1024 * 1024, "ok")])
def test_doctor_reports_free_space(tmp_path, monkeypatch, free, status):
    usage = namedtuple("Usage", "total used free")
    monkeypatch.setattr("shutil.disk_usage", lambda path: usage(2000000, 2000000 - free, free))
    checks = run_checks(None, st_for(tmp_path))
    c = named(checks, "disk_space")
    assert c is not None and c.status == status
    if not free:
        assert "Free space" in c.message and "facetmark index" in c.message


def test_unavailable_free_space_is_reported_without_crashing(tmp_path, monkeypatch):
    def inaccessible(path):
        raise PermissionError("cannot inspect filesystem")

    monkeypatch.setattr("shutil.disk_usage", inaccessible)
    c = named(run_checks(None, st_for(tmp_path)), "disk_space")
    assert c.status == "warn" and "could not check" in c.message


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

    def test_a_full_disk_is_an_error_in_the_json_report(self, tmp_path, monkeypatch):
        usage = namedtuple("Usage", "total used free")
        monkeypatch.setattr("shutil.disk_usage", lambda path: usage(1, 1, 0))
        result = self._run(["doctor", "--json"], tmp_path, monkeypatch)
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["status"] == "error"
        assert any(c["name"] == "disk_space" and c["status"] == "error"
                   for c in payload["checks"])

    @pytest.mark.parametrize("status", ["ok", "warn"])
    @pytest.mark.parametrize("width", [60, 80, 120])
    def test_summary_stays_within_what_was_checked(self, tmp_path, monkeypatch, status, width):
        from rich.console import Console

        monkeypatch.setattr("facetmark.cli.console", Console(width=width))
        monkeypatch.setattr("facetmark.diagnose.run_checks", lambda *args: [
            Check("example", status, "local finding"),
        ])
        result = self._run(["doctor"], tmp_path, monkeypatch)
        assert result.exit_code == 0, result.output
        # Rich wraps prose at the terminal width; the diagnostic promise must
        # be present regardless of whether "not tested" spans two lines.
        output = " ".join(result.stdout.split())
        assert "Everything checks out" not in output
        assert "nothing is broken" not in output
        assert "not tested" in output


@pytest.mark.parametrize("statuses,expected", [
    ([], "ok"),
    (["ok", "ok"], "ok"),
    (["ok", "warn"], "warn"),
    (["warn", "error", "ok"], "error"),
])
def test_worst_picks_the_worst(statuses, expected):
    assert worst([Check(f"c{i}", s, "") for i, s in enumerate(statuses)]) == expected
