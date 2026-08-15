"""``/admin/*``: the write routes the web UI needs, and the three gates on them.

The gate tests come first and are the reason this file exists. These are the
only routes that change the library or write an API key to disk, and the whole
argument for shipping them is that a caller has to be on this machine *and*
hold the pairing token *and* not have turned the group off. Each of those is
asserted separately, because a gate that is only ever tested in combination
with the other two is a gate nobody has tested.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from facetmark import service
from facetmark.admin import INDEX_STAGES, TUPLE_FIELDS, WRITABLE, mask, settings_view
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.configfile import config_path, read_config

NETSCAPE = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
    <DT><A HREF="https://a.example/one" ADD_DATE="1700000000">Vector search notes</A>
    <DT><A HREF="https://b.example/two" ADD_DATE="1700000100">Sqlite internals</A>
</DL><p>
"""

CHROME_JSON = """{"roots": {"bookmark_bar": {"children": [
  {"type": "url", "name": "Rust ownership", "url": "https://c.example/three",
   "date_added": "13350000000000000"}
], "name": "Bookmarks bar", "type": "folder"}}, "version": 1}"""


@pytest.fixture()
def st(tmp_path, monkeypatch) -> Settings:
    # Relocate the config file too: these tests write one.
    monkeypatch.delenv("FACETMARK_DATA_DIR", raising=False)
    monkeypatch.setattr("facetmark.config.default_data_dir", lambda **kw: tmp_path / "fm")
    return Settings(data_dir=tmp_path / "fm", use_mock_provider=True)


@pytest.fixture()
def client(st):
    """A client whose TCP peer looks local.

    ``TestClient`` reports ``testclient`` as the peer by default, which the
    loopback gate correctly refuses. Overriding it here means every test below
    exercises the real gate rather than a bypass.
    """
    with TestClient(create_app(st), client=("127.0.0.1", 40404)) as c:
        yield c


@pytest.fixture()
def auth(client) -> dict:
    return {"Authorization": f"Bearer {client.app.state.fm.token}"}


def slow_index(stages=INDEX_STAGES[1:], *, step: float = 0.05):
    """A stand-in for ``index_all`` that takes a knowable amount of time.

    Single-flight and cancellation are properties of the runner, not of the
    indexer, and against the mock provider a two-bookmark library indexes
    faster than the next HTTP request arrives -- so a test written against the
    real call would assert "already running" on a job that had already
    finished, and pass or fail with the machine's mood.
    """

    async def fake(conn, *, progress=None, **kw):
        import asyncio

        for name in stages:
            await asyncio.sleep(step)
            if progress:
                progress(name, {"done": 1})
        return service.IndexReport()

    return fake


def wait_for_job(client, auth, *, timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get("/admin/job", headers=auth).json()
        if body.get("state") not in ("running",):
            return body
        time.sleep(0.05)
    raise AssertionError(f"index job did not finish in {timeout}s: {body}")


# ---------------------------------------------------------------------------
# the three gates
# ---------------------------------------------------------------------------


class TestTheGates:
    ROUTES = [
        ("POST", "/admin/import"),
        ("POST", "/admin/index"),
        ("GET", "/admin/job"),
        ("POST", "/admin/job/cancel"),
        ("GET", "/admin/settings"),
        ("PUT", "/admin/settings"),
        ("POST", "/admin/settings/test"),
    ]

    @pytest.mark.parametrize(("method", "path"), ROUTES)
    def test_no_token_is_401(self, client, method, path):
        assert client.request(method, path, json={}).status_code == 401

    @pytest.mark.parametrize(("method", "path"), ROUTES)
    def test_a_remote_peer_is_403_even_with_a_valid_token(self, st, method, path):
        """A LAN-bound service does not offer administration to the LAN."""
        with TestClient(create_app(st), client=("10.0.0.9", 40404)) as remote:
            headers = {"Authorization": f"Bearer {remote.app.state.fm.token}"}
            r = remote.request(method, path, json={}, headers=headers)
            assert r.status_code == 403
            assert "loopback" in r.json()["detail"]

    @pytest.mark.parametrize(("method", "path"), ROUTES)
    def test_the_off_switch_is_403(self, tmp_path, method, path):
        st = Settings(data_dir=tmp_path / "fm", use_mock_provider=True, admin_api=False)
        with TestClient(create_app(st), client=("127.0.0.1", 1)) as c:
            headers = {"Authorization": f"Bearer {c.app.state.fm.token}"}
            r = c.request(method, path, json={}, headers=headers)
            assert r.status_code == 403
            assert "disabled" in r.json()["detail"]

    def test_the_admin_routes_are_not_public(self):
        from facetmark.api import PUBLIC_PATHS

        assert not any(p.startswith("/admin") for p in PUBLIC_PATHS)

    def test_ipv6_loopback_is_accepted(self, st):
        with TestClient(create_app(st), client=("::1", 40404)) as c:
            headers = {"Authorization": f"Bearer {c.app.state.fm.token}"}
            assert c.get("/admin/settings", headers=headers).status_code == 200


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------


class TestImport:
    def test_a_netscape_export_lands_in_the_library(self, client, auth):
        r = client.post("/admin/import", content=NETSCAPE.encode(),
                        headers={**auth, "X-Filename": "bookmarks.html"})
        assert r.status_code == 200
        body = r.json()
        assert body["parsed"] == 2
        assert body["inserted"] == 2
        assert body["filename"] == "bookmarks.html"
        assert body["bytes"] == len(NETSCAPE.encode())
        assert client.get("/stats", headers=auth).json()["bookmarks"] == 2

    def test_chrome_json_is_sniffed_without_being_told(self, client, auth):
        """One endpoint, no format parameter: the importer already detects it."""
        r = client.post("/admin/import", content=CHROME_JSON.encode(), headers=auth)
        assert r.status_code == 200
        assert r.json()["inserted"] == 1

    def test_a_second_import_updates_rather_than_duplicates(self, client, auth):
        client.post("/admin/import", content=NETSCAPE.encode(), headers=auth)
        body = client.post("/admin/import", content=NETSCAPE.encode(), headers=auth).json()
        assert body["inserted"] == 0
        assert client.get("/stats", headers=auth).json()["bookmarks"] == 2

    def test_an_empty_body_is_400(self, client, auth):
        assert client.post("/admin/import", content=b"", headers=auth).status_code == 400

    def test_an_oversized_body_is_413(self, client, auth, monkeypatch):
        monkeypatch.setattr("facetmark.admin.MAX_UPLOAD_BYTES", 16)
        r = client.post("/admin/import", content=b"x" * 64, headers=auth)
        assert r.status_code == 413

    def test_a_legacy_encoding_keeps_its_title(self, client, auth):
        """The upload path decodes like the file path, or it damages titles.

        "Does not crash" was the whole of this assertion once, and it passed
        while the endpoint stored ``Caf\ufffd``: the body was decoded as UTF-8
        with ``errors="replace"``, so a cp1252 or GBK export imported with a
        200 and a broken title -- which then went into the lexical index, the
        summary and the embedding.
        """
        for enc, was, title, url in (
            ("cp1252", "Vector search notes", "Caf\xe9 notes", "https://a.example/one"),
            ("gb18030", "Sqlite internals", "\u4e2d\u6587\u6807\u9898", "https://b.example/two"),
        ):
            body = NETSCAPE.replace(was, title).encode(enc)
            r = client.post("/admin/import", content=body, headers=auth)
            assert r.status_code == 200
            titles = [
                t for (t,) in client.app.state.fm.conn.execute(
                    "select title from bookmark where url = ?", (url,)
                )
            ]
            assert titles == [title], f"{enc} title did not survive the upload"

    def test_an_ambiguous_legacy_byte_pair_still_imports(self, client, auth):
        """``\\xe4l`` is a legal GB18030 pair *and* a legal cp1252 one.

        ``intern\\xe4ls`` decodes to a CJK character under GB18030 and to
        ``internäls`` under cp1252, and nothing in the bytes says which was
        meant. The ladder prefers GB18030 because reordering it to rescue this
        case would turn every real Chinese export into mojibake -- a much
        larger population than accented Latin next to an ASCII letter. So the
        URL is asserted and the title is not: this is a known ambiguity, not a
        regression to fix by swapping two entries.
        """
        raw = NETSCAPE.replace("Sqlite internals", "Sqlite intern\xe4ls").encode("cp1252")
        r = client.post("/admin/import", content=raw, headers=auth)
        assert r.status_code == 200
        assert r.json()["inserted"] == 2


# ---------------------------------------------------------------------------
# index job
# ---------------------------------------------------------------------------


class TestIndexJob:
    def test_the_published_stage_list_matches_what_index_all_emits(self, client, auth):
        """``INDEX_STAGES`` drives a progress bar, so it cannot drift silently."""
        client.post("/admin/import", content=NETSCAPE.encode(), headers=auth)
        client.post("/admin/index", json={"fetch": False}, headers=auth)
        body = wait_for_job(client, auth)
        assert body["state"] == "done", body["error"]
        assert [s["name"] for s in body["stages"]] == list(INDEX_STAGES[1:])

    def test_idle_before_anything_has_run(self, client, auth):
        assert client.get("/admin/job", headers=auth).json()["state"] == "idle"

    def test_a_job_reports_progress_and_a_log(self, client, auth):
        client.post("/admin/import", content=NETSCAPE.encode(), headers=auth)
        started = client.post("/admin/index", json={"fetch": False}, headers=auth).json()
        assert started["state"] == "running"
        assert started["planned"] == list(INDEX_STAGES[1:])
        body = wait_for_job(client, auth)
        assert body["progress"] == 1.0
        assert body["current"] is None
        assert body["elapsed"] >= 0
        assert any("enrich" in line for line in body["log"])

    def test_fetch_true_plans_the_crawl_stage(self, client, auth):
        started = client.post("/admin/index", json={"fetch": True}, headers=auth).json()
        assert started["planned"][0] == "fetch"
        wait_for_job(client, auth)

    def test_a_second_start_is_409_not_a_second_job(self, client, auth, monkeypatch):
        monkeypatch.setattr("facetmark.service.index_all", slow_index())
        first = client.post("/admin/index", json={"fetch": False}, headers=auth).json()
        second = client.post("/admin/index", json={"fetch": False}, headers=auth)
        assert second.status_code == 409
        assert "already running" in second.json()["detail"]
        wait_for_job(client, auth)
        assert client.get("/admin/job", headers=auth).json()["id"] == first["id"]

    def test_a_new_job_may_start_once_the_last_one_ended(self, client, auth, monkeypatch):
        monkeypatch.setattr("facetmark.service.index_all", slow_index(step=0.01))
        first = client.post("/admin/index", json={"fetch": False}, headers=auth).json()
        wait_for_job(client, auth)
        second = client.post("/admin/index", json={"fetch": False}, headers=auth)
        assert second.status_code == 200
        assert second.json()["id"] != first["id"]
        wait_for_job(client, auth)

    def test_cancel_on_an_idle_runner_says_so_rather_than_erroring(self, client, auth):
        body = client.post("/admin/job/cancel", headers=auth).json()
        assert body["cancel_requested"] is False

    def test_a_cancelled_job_stops_and_keeps_the_stages_it_finished(
        self, client, auth, monkeypatch
    ):
        monkeypatch.setattr("facetmark.service.index_all", slow_index(step=0.15))
        client.post("/admin/index", json={"fetch": False}, headers=auth)
        assert client.post("/admin/job/cancel", headers=auth).json()["cancel_requested"] is True
        body = wait_for_job(client, auth)
        # Cancellation lands at a stage boundary, so *which* stage it stops
        # after is a race. What must hold: it stopped, and it stopped early.
        assert body["state"] == "cancelled"
        assert len(body["stages"]) < len(INDEX_STAGES[1:])
        assert "cancelled" in body["log"][-1]

    def test_cancelling_is_advertised_as_taking_effect_at_a_boundary(
        self, client, auth, monkeypatch
    ):
        """The UI repeats this wording; if it changes, the UI is lying."""
        monkeypatch.setattr("facetmark.service.index_all", slow_index(step=0.15))
        client.post("/admin/index", json={"fetch": False}, headers=auth)
        client.post("/admin/job/cancel", headers=auth)
        log = client.get("/admin/job", headers=auth).json()["log"]
        assert any("after the current stage" in line for line in log)
        wait_for_job(client, auth)

    def test_a_failing_stage_is_reported_not_swallowed(self, client, auth, monkeypatch):
        async def boom(*a, **kw):
            raise RuntimeError("endpoint refused the embedding request")

        monkeypatch.setattr("facetmark.service.index_all", boom)
        client.post("/admin/index", json={"fetch": False}, headers=auth)
        body = wait_for_job(client, auth)
        assert body["state"] == "failed"
        assert "endpoint refused" in body["error"]

    def test_search_still_answers_while_a_job_runs(self, client, auth):
        """The job holds its own connection, not the one every search takes."""
        client.post("/admin/import", content=NETSCAPE.encode(), headers=auth)
        client.post("/admin/index", json={"fetch": False}, headers=auth)
        assert client.get("/quick", params={"q": "sqlite"}, headers=auth).status_code == 200
        wait_for_job(client, auth)


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------


class TestSettings:
    def test_the_key_is_never_returned_in_full(self, tmp_path, monkeypatch):
        monkeypatch.setattr("facetmark.config.default_data_dir", lambda **kw: tmp_path / "fm")
        st = Settings(data_dir=tmp_path / "fm", use_mock_provider=True,
                      api_key="sk-abcdefghijklmnop")
        with TestClient(create_app(st), client=("127.0.0.1", 1)) as c:
            headers = {"Authorization": f"Bearer {c.app.state.fm.token}"}
            rows = {r["key"]: r for r in c.get("/admin/settings", headers=headers).json()["settings"]}
        assert rows["api_key"]["value"] == "sk-...mnop"
        assert "abcdefghij" not in str(rows)
        assert rows["api_key"]["secret"] is True
        assert rows["api_key"]["set"] is True

    def test_mask_keeps_short_values_intact_rather_than_lying(self):
        assert mask("") == ""
        assert mask("short") == "short"
        assert mask("sk-abcdefghij") == "sk-...ghij"

    def test_the_source_column_names_the_winner(self, client, auth, monkeypatch):
        client.put("/admin/settings", json={"values": {"chat_model": "from-file"}},
                   headers=auth)
        monkeypatch.setenv("FACETMARK_BASE_URL", "https://env.example/v1")
        rows = {r["key"]: r for r in client.get("/admin/settings", headers=auth).json()["settings"]}
        assert rows["chat_model"]["source"] == "file"
        assert rows["base_url"]["source"] == "env"
        assert rows["base_url"]["locked"] is True
        assert rows["embed_model"]["source"] == "default"

    def test_a_write_lands_in_the_config_file(self, client, auth):
        r = client.put("/admin/settings",
                       json={"values": {"chat_model": "deepseek-chat", "embed_dim": 1024}},
                       headers=auth)
        assert r.status_code == 200
        assert read_config()["chat_model"] == "deepseek-chat"
        assert read_config()["embed_dim"] == 1024

    def test_a_write_says_which_keys_need_a_restart(self, client, auth):
        body = client.put("/admin/settings",
                          json={"values": {"chat_model": "x", "embed_dim": 1024}},
                          headers=auth).json()
        assert body["restart_required"] == ["embed_dim"]
        assert "chat_model" in body["applied"]

    def test_an_applied_key_takes_effect_immediately(self, client, auth):
        client.put("/admin/settings", json={"values": {"chat_model": "live-now"}}, headers=auth)
        assert client.app.state.fm.settings.chat_model == "live-now"

    def test_an_empty_api_key_clears_rather_than_pins_it(self, client, auth):
        client.put("/admin/settings", json={"values": {"api_key": "sk-one"}}, headers=auth)
        client.put("/admin/settings", json={"values": {"api_key": ""}}, headers=auth)
        assert "api_key" not in read_config()

    @pytest.mark.parametrize(
        "sent,want",
        [
            ("private.example, mail.example", ["private.example", "mail.example"]),
            ("  a.example ,, b.example ,", ["a.example", "b.example"]),
            ("dup.example, dup.example", ["dup.example"]),
            ("one.example two.example", ["one.example", "two.example"]),
            (["x.example", "y.example"], ["x.example", "y.example"]),
            ("", []),
        ],
    )
    def test_a_list_setting_can_be_written_from_one_text_box(self, client, auth, sent, want):
        """The settings page renders this field as a single comma-separated box.

        It used to send that box as a string, and the string hit a
        ``tuple[str, ...]`` field: every attempt to save a privacy exclusion
        returned ``400 Input should be a valid tuple``, which is both the only
        list-valued setting the UI offers and a message nobody can act on.
        """
        r = client.put(
            "/admin/settings",
            json={"values": {"privacy_excluded_domains": sent}},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        row = next(x for x in r.json()["settings"] if x["key"] == "privacy_excluded_domains")
        assert row["value"] == want
        assert list(read_config().get("privacy_excluded_domains", [])) == want
        live = client.app.state.fm.settings.privacy_excluded_domains
        # A tuple, not the list that was written to TOML: `host_excluded` takes
        # a sequence, so a stray `str` here would iterate characters and match
        # hosts by their last letter.
        assert isinstance(live, tuple)
        assert list(live) == want

    def test_the_list_fields_are_read_off_the_model(self):
        """So that the next tuple-valued setting does not have to be remembered."""
        assert set(TUPLE_FIELDS) == {"privacy_excluded_domains"}

    def test_an_env_locked_field_is_refused_rather_than_half_applied(
        self, client, auth, monkeypatch
    ):
        """The read-only box in the UI is not the gate; this is.

        A localhost HTTP API has callers other than its own page. Writing a
        field the environment owns used to return 200, drop the key from the
        config file, and overwrite the live value -- while the same response
        still reported ``source: env``, because that part was right.
        """
        monkeypatch.setenv("FACETMARK_BASE_URL", "https://from-env.example/v1")
        live = client.app.state.fm.settings
        live.base_url = "https://from-env.example/v1"
        r = client.put(
            "/admin/settings",
            json={"values": {"base_url": "https://typed-in-the-box.example/v1"}},
            headers=auth,
        )
        assert r.status_code == 409
        assert "base_url" in r.json()["detail"]
        assert live.base_url == "https://from-env.example/v1"
        assert "base_url" not in read_config()

    def test_an_env_locked_key_cannot_be_cleared_by_an_empty_string(
        self, client, auth, monkeypatch
    ):
        """``api_key: ""`` means "clear it", which is still a write."""
        monkeypatch.setenv("FACETMARK_API_KEY", "sk-from-env-do-not-touch")
        live = client.app.state.fm.settings
        live.api_key = "sk-from-env-do-not-touch"
        r = client.put("/admin/settings", json={"values": {"api_key": ""}}, headers=auth)
        assert r.status_code == 409
        assert live.api_key == "sk-from-env-do-not-touch"
        row = next(x for x in settings_view(live)["settings"] if x["key"] == "api_key")
        assert row["locked"] is True
        assert row["source"] == "env"
        assert row["value"] == mask("sk-from-env-do-not-touch")

    def test_a_non_writable_key_is_refused_by_name(self, client, auth):
        r = client.put("/admin/settings", json={"values": {"rrf_k": 5}}, headers=auth)
        assert r.status_code == 400
        assert "rrf_k" in r.json()["detail"]

    def test_retrieval_constants_are_not_writable_from_a_text_box(self):
        """They are load-bearing for numbers the README publishes."""
        for key in ("rrf_k", "candidates_per_facet", "rerank_depth", "decay_factor",
                    "max_page_size", "max_candidate_depth", "graph_expand_hops"):
            assert key not in WRITABLE

    def test_an_invalid_value_is_400_and_is_not_written(self, client, auth):
        r = client.put("/admin/settings", json={"values": {"embed_backend": "telepathy"}},
                       headers=auth)
        assert r.status_code == 400
        assert "embed_backend" not in read_config()

    def test_a_rejected_write_leaves_the_live_settings_alone(self, client, auth):
        before = client.app.state.fm.settings.embed_backend
        client.put("/admin/settings", json={"values": {"embed_backend": "telepathy"}},
                   headers=auth)
        assert client.app.state.fm.settings.embed_backend == before


class TestTheConfigFilePath:
    """Which ``config.toml`` the settings page is looking at.

    Worth its own class because the obvious reading of ``serve --db`` is wrong
    in a way that is expensive: the page reports a path outside the data
    directory it was started with, which looks like a bug and is the only
    correct answer.
    """

    @pytest.fixture()
    def two_dirs(self, tmp_path, monkeypatch):
        """The per-OS default directory, and the one ``--db`` would select."""
        default, instance = tmp_path / "default", tmp_path / "instance"
        default.mkdir()
        instance.mkdir()
        monkeypatch.delenv("FACETMARK_DATA_DIR", raising=False)
        monkeypatch.setattr("facetmark.config.default_data_dir", lambda **kw: default)
        return default, instance

    def test_the_page_names_the_file_the_next_boot_will_read(self, two_dirs):
        """Not ``settings.data_dir``, on purpose.

        ``facetmark serve --db /elsewhere/x.db`` moves the database and leaves
        the config file where it was, because :class:`ConfigFileSource` resolves
        its own path from the environment -- a file cannot choose its own
        location without the resolution becoming circular. So the loader reads
        the default directory, and the settings page has to name the same file
        it does. Reporting ``/elsewhere/config.toml`` would look tidier and
        would write settings that nothing ever reads.
        """
        default, instance = two_dirs
        (default / "config.toml").write_text('chat_model = "from-default-dir"\n', encoding="utf-8")
        (instance / "config.toml").write_text('chat_model = "from-instance-dir"\n', encoding="utf-8")
        st = Settings(data_dir=instance, use_mock_provider=True)
        assert st.data_dir == instance
        assert st.chat_model == "from-default-dir"
        assert settings_view(st)["path"] == str(config_path())
        assert settings_view(st)["path"] == str(default / "config.toml")

    def test_a_write_goes_to_that_same_file(self, two_dirs):
        default, instance = two_dirs
        st = Settings(data_dir=instance, use_mock_provider=True)
        with TestClient(create_app(st), client=("127.0.0.1", 40404)) as c:
            headers = {"Authorization": f"Bearer {c.app.state.fm.token}"}
            r = c.put("/admin/settings", json={"values": {"chat_model": "written"}},
                      headers=headers)
            assert r.status_code == 200
            assert r.json()["path"] == str(default / "config.toml")
        assert (default / "config.toml").exists()
        assert not (instance / "config.toml").exists()
        # And the value comes back on the next boot of the same instance.
        assert Settings(data_dir=instance, use_mock_provider=True).chat_model == "written"


class TestConnectionProbe:
    def test_the_probe_reports_chat_and_embed_separately(self, client, auth):
        """They fail independently on aggregated endpoints, constantly."""
        body = client.post("/admin/settings/test", json={}, headers=auth).json()
        assert set(body) == {"chat", "embed", "ok"}
        assert body["chat"]["ok"] is True
        assert body["embed"]["ok"] is True
        assert body["ok"] is True

    def test_a_dimension_mismatch_fails_the_probe_before_it_corrupts_an_index(
        self, client, auth
    ):
        """The meta table pins the dimension on first build; a mismatch found
        later means an index of incompatible vectors, so it has to fail here."""

        async def short(self, texts):
            return [[0.0] * 8 for _ in texts]

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("facetmark.providers.MockProvider.embed", short)
            body = client.post("/admin/settings/test", json={}, headers=auth).json()
        assert body["embed"]["ok"] is True
        assert body["embed"]["dim"] == 8
        assert body["embed"]["dim_matches"] is False
        assert body["embed"]["expected_dim"] == 1536
        assert body["ok"] is False

    def test_a_broken_endpoint_returns_a_readable_reason_not_a_500(self, client, auth):
        async def boom(self, texts):
            raise RuntimeError("404 page not found: /v1/embeddings")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("facetmark.providers.MockProvider.embed", boom)
            body = client.post("/admin/settings/test", json={}, headers=auth).json()
        assert body["embed"]["ok"] is False
        assert "/v1/embeddings" in body["embed"]["error"]
        assert body["chat"]["ok"] is True

    def test_the_probe_does_not_persist_what_it_was_given(self, client, auth):
        client.post("/admin/settings/test",
                    json={"chat_model": "throwaway", "api_key": "sk-throwaway"}, headers=auth)
        assert read_config() == {}
        assert client.app.state.fm.settings.chat_model != "throwaway"


# ---------------------------------------------------------------------------
# the loop this whole module exists for
# ---------------------------------------------------------------------------


def test_a_browser_can_go_from_empty_library_to_search_results(client, auth):
    """Import, index, search -- no terminal anywhere in it."""
    assert client.get("/stats", headers=auth).json()["bookmarks"] == 0
    assert client.post("/admin/import", content=NETSCAPE.encode(), headers=auth).status_code == 200
    assert client.post("/admin/index", json={"fetch": False}, headers=auth).status_code == 200
    assert wait_for_job(client, auth)["state"] == "done"
    hits = client.post("/search", json={"q": "sqlite", "limit": 5}, headers=auth).json()
    assert hits["total"] >= 1
    assert service  # imported for the fixture's sake; keeps the import honest
