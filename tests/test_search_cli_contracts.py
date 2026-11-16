"""Local retrieval and command output keep their own library and resources."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client
from typer.testing import CliRunner

from facetmark import service
from facetmark.api import create_app
from facetmark.cli import _settings, app
from facetmark.config import Settings, reset_settings
from facetmark.db import ensure_vec_tables, open_db, upsert_content_vector
from facetmark.mcp_server import create_server
from facetmark.providers import MockProvider, ProviderError
from facetmark.search import pipeline


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    for key in list(os.environ):
        if key.lower().startswith("facetmark_"):
            monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path / "default-local"))
    reset_settings()
    try:
        yield
    finally:
        reset_settings()


@pytest.mark.parametrize("entry", ["settings", "cli-directory", "cli-file"])
def test_explicit_library_reads_its_own_config_instead_of_another_directory(
    tmp_path, monkeypatch, entry
):
    first, target = tmp_path / "first", tmp_path / "second"
    for path, model, host in (
        (first, "model-first", "first.invalid"),
        (target, "model-second", "second.invalid"),
    ):
        path.mkdir()
        (path / "config.toml").write_text(
            f'chat_model = "{model}"\nchat_base_url = "https://{host}/v1"\nchat_api_key = "synthetic-{host}"\n',
            encoding="utf-8",
        )
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(first))
    if entry == "settings":
        value = Settings(data_dir=target)
    else:
        value = _settings(target / "selected.db" if entry == "cli-file" else target)
    assert value.data_dir == target
    assert value.chat_model == "model-second"
    assert value.chat_base_url == "https://second.invalid/v1"
    assert value.chat_api_key == "synthetic-second.invalid"
    if entry == "cli-file":
        assert value.db_path == target / "selected.db"


def test_selecting_a_library_does_not_read_a_broken_config_from_the_default_library(
    tmp_path, monkeypatch
):
    broken = tmp_path / "broken-default"
    broken.mkdir()
    (broken / "config.toml").write_text('chat_model = "unfinished\n', encoding="utf-8")
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(broken))
    selected = tmp_path / "selected"
    selected.mkdir()
    (selected / "config.toml").write_text('chat_model = "selected-model"\n', encoding="utf-8")
    assert _settings(selected).chat_model == "selected-model"


@pytest.mark.parametrize(
    "query,config",
    [
        ("keyword", None),
        ("keyword", pipeline.Config("lexical", pipeline.LEXICAL_FACETS)),
        ("folder:Research", pipeline.FULL),
        ("keyword", pipeline.Config("content-only", frozenset({"content"}))),
    ],
)
@pytest.mark.asyncio
async def test_model_free_retrieval_survives_an_unusable_local_embedding_configuration(
    tmp_path, query, config
):
    settings = Settings(
        data_dir=tmp_path / "model-free", embed_backend="local", local_embed_path=""
    )
    with open_db(settings.db_path) as conn:
        saved = service.save_bookmark(
            conn,
            "https://saved.invalid/keyword",
            title="keyword research",
            folder="Research",
            settings=settings,
        )
        conn.commit()
        result = await pipeline.search(conn, query, settings=settings, config=config)
        assert [hit.bookmark_id for hit in result.hits] == [saved["bookmark_id"]]
        if config is not None and config.name == "content-only":
            assert result.degraded_from == "content-only"


@pytest.mark.parametrize("query,config", [("keyword", "lex_only"), ("folder:Research", "full")])
def test_http_model_free_retrieval_does_not_initialize_the_unusable_encoder(
    tmp_path, query, config
):
    settings = Settings(
        data_dir=tmp_path / "http-model-free", embed_backend="local", local_embed_path=""
    )
    with TestClient(create_app(settings)) as client:
        state = client.app.state.fm
        saved = service.save_bookmark(
            state.conn,
            "https://saved.invalid/keyword",
            title="keyword research",
            folder="Research",
            settings=settings,
        )
        state.conn.commit()
        response = client.post(
            "/search",
            headers={"Authorization": "Bearer " + state.token},
            json={"q": query, "config": config},
        )
        assert response.status_code == 200
        assert [hit["bookmark_id"] for hit in response.json()["hits"]] == [saved["bookmark_id"]]
        assert state._provider is None


@pytest.mark.asyncio
async def test_stdio_mcp_can_browse_without_initializing_an_unusable_encoder(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "stdio-model-free", embed_backend="local", local_embed_path=""
    )
    with open_db(settings.db_path) as conn:
        saved = service.save_bookmark(
            conn,
            "https://saved.invalid/keyword",
            title="keyword research",
            folder="Research",
            settings=settings,
        )
        conn.commit()
        async with Client(create_server(settings, conn)) as client:
            result = await client.call_tool("search_bookmarks", {"query": "folder:Research"})
            assert [hit["bookmark_id"] for hit in result.data["hits"]] == [saved["bookmark_id"]]


def test_synthesis_without_indexed_text_keeps_the_explanation_without_initializing_an_encoder(
    tmp_path,
):
    settings = Settings(
        data_dir=tmp_path / "http-no-text", embed_backend="local", local_embed_path=""
    )
    with TestClient(create_app(settings)) as client:
        state = client.app.state.fm
        service.save_bookmark(
            state.conn, "https://saved.invalid/keyword", title="keyword research", settings=settings
        )
        state.conn.commit()
        response = client.post(
            "/synthesize", headers={"Authorization": "Bearer " + state.token}, json={"q": "keyword"}
        )
        assert response.status_code == 200
        assert response.json()["model"] == "none"
        assert response.json()["sources"]
        assert state._provider is None


class TrackedProvider(MockProvider):
    def __init__(self, settings):
        super().__init__(settings)
        self.closed = 0

    async def aclose(self):
        self.closed += 1


@pytest.mark.parametrize("fails", [False, True])
@pytest.mark.asyncio
async def test_a_search_owned_provider_closes_after_success_or_a_failed_database_read(
    tmp_path, monkeypatch, fails
):
    settings = Settings(data_dir=tmp_path / "owned-provider", use_mock_provider=True)
    provider = TrackedProvider(settings)
    monkeypatch.setattr(pipeline, "get_chat_provider", lambda _settings: provider)
    with open_db(settings.db_path) as conn:
        service.save_bookmark(
            conn, "https://saved.invalid/keyword", title="keyword", settings=settings
        )
        conn.commit()
        if fails:

            def failure(*_args, **_kwargs):
                raise OSError("synthetic candidate read failure")

            monkeypatch.setattr(pipeline, "lexical_lists", failure)
            with pytest.raises(OSError, match="candidate read failure"):
                await pipeline.search(
                    conn,
                    "keyword",
                    config=pipeline.Config("lexical", pipeline.LEXICAL_FACETS),
                    settings=settings,
                    assist=True,
                )
        else:
            result = await pipeline.search(
                conn,
                "keyword",
                config=pipeline.Config("lexical", pipeline.LEXICAL_FACETS),
                settings=settings,
                assist=True,
            )
            assert result.hits
    assert provider.closed == 1


@pytest.mark.asyncio
async def test_a_shared_api_provider_remains_open_after_search(tmp_path):
    settings = Settings(data_dir=tmp_path / "shared-provider", use_mock_provider=True)
    provider = TrackedProvider(settings)
    with open_db(settings.db_path) as conn:
        service.save_bookmark(
            conn, "https://saved.invalid/keyword", title="keyword", settings=settings
        )
        conn.commit()
        result = await pipeline.search(
            conn,
            "keyword",
            provider=provider,
            config=pipeline.Config("lexical", pipeline.LEXICAL_FACETS),
            settings=settings,
        )
        assert result.hits
    assert provider.closed == 0


@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled"])
@pytest.mark.asyncio
async def test_owned_embedding_resources_close_after_the_actual_vector_query(
    tmp_path, monkeypatch, outcome
):
    settings = Settings(data_dir=tmp_path / "vector-owner", use_mock_provider=True, embed_dim=4)

    class Embeddings(TrackedProvider):
        async def embed(self, texts):
            if outcome == "failure":
                raise ProviderError("synthetic embedding failure")
            if outcome == "cancelled":
                raise asyncio.CancelledError()
            return await super().embed(texts)

    provider = Embeddings(settings)
    monkeypatch.setattr(pipeline, "get_embed_provider", lambda _settings: provider)
    with open_db(settings.db_path) as conn:
        saved = service.save_bookmark(
            conn, "https://saved.invalid/vector", title="keyword", settings=settings
        )
        conn.commit()
        ensure_vec_tables(conn, settings.embed_dim, settings.embed_model)
        upsert_content_vector(conn, saved["bookmark_id"], [1.0, 0.0, 0.0, 0.0])
        if outcome == "success":
            result = await pipeline.search(
                conn, "keyword", config=pipeline.CONFIGS["A"], settings=settings
            )
            assert [hit.bookmark_id for hit in result.hits] == [saved["bookmark_id"]]
        else:
            expected = ProviderError if outcome == "failure" else asyncio.CancelledError
            with pytest.raises(expected):
                await pipeline.search(
                    conn, "keyword", config=pipeline.CONFIGS["A"], settings=settings
                )
    assert provider.closed == 1


@pytest.mark.asyncio
async def test_a_chat_only_reranker_uses_the_saved_channel_without_loading_local_embeddings(
    tmp_path, monkeypatch
):
    settings = Settings(
        data_dir=tmp_path / "chat-only-rerank",
        embed_backend="local",
        local_embed_path="",
        api_key="",
        chat_base_url="https://chat.invalid/v1",
        chat_api_key="synthetic-chat-only",
    )

    class Reranking(TrackedProvider):
        async def chat_json(self, system, user):
            self.usage.calls += 1
            return {}

    provider = Reranking(settings)
    monkeypatch.setattr(pipeline, "get_chat_provider", lambda _settings: provider)
    with open_db(settings.db_path) as conn:
        service.save_bookmark(
            conn, "https://saved.invalid/keyword", title="keyword", settings=settings
        )
        conn.commit()
        config = pipeline.Config("lexical-rerank", pipeline.LEXICAL_FACETS, rerank=True)
        result = await pipeline.search(conn, "keyword", config=config, settings=settings)
        assert result.hits
        assert result.reranker.startswith("llm-listwise")
    assert provider.usage.calls == 1
    assert provider.closed == 1


def test_a_partial_export_write_preserves_the_previous_backup(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path / "export-library")
    with open_db(settings.db_path) as conn:
        service.save_bookmark(
            conn, "https://saved.invalid/backup", title="A saved page", settings=settings
        )
        conn.commit()
    directory = tmp_path / "exports"
    directory.mkdir()
    target = directory / "previous-backup.json"
    original = b'{"previous":"complete synthetic backup"}\n'
    target.write_bytes(original)
    real_open = Path.open
    interrupted_paths = []

    class PartialWrite:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def write(self, text):
            self.stream.write(text[:20])
            self.stream.flush()
            raise OSError("synthetic disk write interrupted")

    def interrupted(file, mode="r", *args, **kwargs):
        stream = real_open(file, mode, *args, **kwargs)
        if file.parent == directory and "w" in mode:
            interrupted_paths.append(file)
            return PartialWrite(stream)
        return stream

    # Python 3.10's Path accessor captures io.open at import time. Inject at
    # the public file-opening boundary so every supported runtime interrupts
    # the actual export write instead of silently missing the failure.
    monkeypatch.setattr(Path, "open", interrupted)
    result = CliRunner().invoke(app, ["export", str(target), "--db", str(settings.db_path)])
    assert len(interrupted_paths) == 1 and interrupted_paths[0] != target
    assert result.exit_code == 1
    assert target.read_bytes() == original
    assert list(directory.iterdir()) == [target]
