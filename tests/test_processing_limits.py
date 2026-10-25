"""Cloud-only checks of actual request budgets and local-client backpressure."""
from __future__ import annotations

import asyncio
from email.utils import formatdate
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from facetmark import admin, local_agents, providers, service
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.db import open_db
from facetmark.providers import MockProvider, OpenAICompatibleProvider, ProviderError, _retry_after


@pytest.mark.parametrize("key,default,minimum,maximum", [
    ("enrich_concurrency", 4, 1, 64), ("agent_concurrency", 2, 1, 8),
    ("chat_concurrency", 2, 1, 8), ("fetch_concurrency", 30, 1, 64),
    ("fetch_per_host_concurrency", 2, 1, 16),
    ("fetch_per_host_min_interval", 0.5, 0, 60),
    ("max_retries", 3, 1, 10), ("model_requests_per_minute", 0, 0, 6000),
])
def test_processing_limits_have_defaults_and_reject_out_of_range_values(tmp_path, key, default, minimum, maximum):
    assert getattr(Settings(data_dir=tmp_path), key) == default
    for value in (minimum, maximum):
        assert getattr(Settings(data_dir=tmp_path, **{key: value}), key) == value
    for value in (minimum - 1, maximum + 1):
        with pytest.raises(ValidationError):
            Settings(data_dir=tmp_path, **{key: value})


def test_saved_limits_are_used_by_the_next_provider_without_invalidating_model_tests(tmp_path, monkeypatch):
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))
    settings = Settings(data_dir=tmp_path, api_key="synthetic-key", base_url="https://synthetic.test/v1")
    before = {channel: admin.probe_fingerprint(settings, channel) for channel in ("chat", "embed")}
    with TestClient(create_app(settings), client=("127.0.0.1", 40000)) as client:
        state = client.app.state.fm
        client.headers["Authorization"] = "Bearer " + state.token
        old = state.provider
        for channel, fingerprint in before.items():
            state.probe_results[channel] = {"fingerprint": fingerprint, "result": {"ok": True}}
        values = {"enrich_concurrency": 7, "agent_concurrency": 3, "chat_concurrency": 3,
                  "fetch_concurrency": 8, "fetch_per_host_concurrency": 4,
                  "fetch_per_host_min_interval": 0, "max_retries": 5, "model_requests_per_minute": 40}
        response = client.put("/admin/settings", json={"values": values})
        assert response.status_code == 200, response.text
        assert response.json()["restart_required"] == []
        new = state.provider
        assert new is not old
        assert all(getattr(new.settings, key) == value for key, value in values.items())
        assert {channel: admin.probe_fingerprint(state.settings, channel) for channel in before} == before
        assert all(state.probe_results[channel]["fingerprint"] == fingerprint for channel, fingerprint in before.items())
    reloaded = Settings(data_dir=tmp_path)
    assert all(getattr(reloaded, key) == value for key, value in values.items())


@pytest.mark.parametrize("key,value", [("enrich_concurrency", 65), ("agent_concurrency", 9),
    ("chat_concurrency", 0), ("fetch_per_host_concurrency", 17),
    ("fetch_per_host_min_interval", -0.1), ("max_retries", 0), ("model_requests_per_minute", -1)])
def test_invalid_limit_patches_leave_the_saved_settings_unchanged(tmp_path, monkeypatch, key, value):
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))
    with TestClient(create_app(Settings(data_dir=tmp_path)), client=("127.0.0.1", 40000)) as client:
        state = client.app.state.fm
        client.headers["Authorization"] = "Bearer " + state.token
        before = getattr(state.settings, key)
        response = client.put("/admin/settings", json={"values": {key: value}})
        assert response.status_code == 400
        assert getattr(state.settings, key) == before


class Clock:
    def __init__(self):
        self.current = 0.0
        self.delays = []

    async def sleep(self, delay):
        self.delays.append(delay)
        self.current += delay


def endpoint(tmp_path, monkeypatch, replies, *, rpm=0, attempts=3):
    clock = Clock()
    monkeypatch.setattr(providers, "monotonic", lambda: clock.current)
    monkeypatch.setattr(providers.asyncio, "sleep", clock.sleep)
    client = AsyncMock(spec=httpx.AsyncClient)
    sent = []

    async def post(path, json):
        sent.append((path, clock.current))
        return replies.pop(0)

    client.post.side_effect = post
    settings = Settings(data_dir=tmp_path, api_key="synthetic-key", max_retries=attempts,
                        model_requests_per_minute=rpm)
    return OpenAICompatibleProvider(settings, client=client), clock, sent


async def test_each_http_attempt_uses_the_shared_rolling_minute_budget(tmp_path, monkeypatch):
    provider, clock, sent = endpoint(tmp_path, monkeypatch, [
        httpx.Response(500), httpx.Response(200, json={"first": True}),
        httpx.Response(200, json={"second": True})], rpm=2)
    assert await provider._post("/chat/completions", {}) == {"first": True}
    assert await provider._post("/embeddings", {}) == {"second": True}
    assert [timestamp for _, timestamp in sent] == [0, 1, 60]
    assert sum(clock.delays) == 60


async def test_distinct_provider_instances_share_http_budget_and_server_cooldown(tmp_path, monkeypatch):
    first, clock, sent = endpoint(tmp_path, monkeypatch, [
        httpx.Response(200, json={"first": True}),
        httpx.Response(429, headers={"Retry-After": "120"}),
        httpx.Response(200, json={"third": True})], rpm=1, attempts=1)
    second = OpenAICompatibleProvider(first.settings, client=first._client)
    assert await first._post("/chat/completions", {}) == {"first": True}
    with pytest.raises(ProviderError, match="failed after 1"):
        await second._post("/embeddings", {})
    assert await first._post("/chat/completions", {}) == {"third": True}
    assert [timestamp for _, timestamp in sent] == [0, 60, 180]
    assert sum(clock.delays) == 180


async def test_retry_after_is_not_shortened_and_exhausted_429_cools_down_the_next_call(tmp_path, monkeypatch):
    provider, clock, sent = endpoint(tmp_path, monkeypatch, [
        httpx.Response(429, headers={"Retry-After": "120"}),
        httpx.Response(200, json={"ok": True})], attempts=1)
    with pytest.raises(ProviderError, match="failed after 1"):
        await provider._post("/chat/completions", {})
    assert await provider._post("/embeddings", {}) == {"ok": True}
    assert [timestamp for _, timestamp in sent] == [0, 120]
    assert clock.delays == [60, 60]


def test_retry_after_seconds_and_http_dates_handle_invalid_values(monkeypatch):
    monkeypatch.setattr(providers, "time", lambda: 1_700_000_000)
    assert _retry_after("120") == 120
    assert _retry_after(formatdate(1_700_000_090, usegmt=True)) == 90
    for value in (None, "bad-date", "NaN", "Infinity", "-30", formatdate(1_699_999_000, usegmt=True)):
        assert _retry_after(value) == 0


async def test_long_server_cooldowns_fail_without_premature_resubmission(tmp_path, monkeypatch):
    provider, clock, sent = endpoint(tmp_path, monkeypatch, [httpx.Response(429, headers={"Retry-After": "3600"})])
    with pytest.raises(ProviderError, match="long cooldown"):
        await provider._post("/chat/completions", {})
    with pytest.raises(ProviderError, match="long cooldown"):
        await provider._post("/embeddings", {})
    assert len(sent) == 1 and clock.delays == []


async def test_transient_failures_respect_total_attempts_and_auth_failures_do_not_retry(tmp_path, monkeypatch):
    provider, clock, sent = endpoint(tmp_path, monkeypatch, [httpx.Response(500), httpx.Response(502)], attempts=2)
    with pytest.raises(ProviderError, match="failed after 2"):
        await provider._post("/chat/completions", {})
    assert len(sent) == 2 and clock.delays == [1]
    provider, clock, sent = endpoint(tmp_path, monkeypatch, [httpx.Response(401)], attempts=10)
    with pytest.raises(ProviderError, match="HTTP 401"):
        await provider._post("/chat/completions", {})
    assert len(sent) == 1 and clock.delays == []


async def test_cancellation_during_rate_wait_does_not_dispatch_or_retry(tmp_path, monkeypatch):
    provider, _, sent = endpoint(tmp_path, monkeypatch, [httpx.Response(200, json={"ok": True})], rpm=1)
    await provider._post("/chat/completions", {})
    entered = asyncio.Event()

    async def wait(delay):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(providers.asyncio, "sleep", wait)
    task = asyncio.create_task(provider._post("/embeddings", {}))
    await asyncio.wait_for(entered.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(sent) == 1


@pytest.mark.parametrize("limit", [1, 3])
@pytest.mark.parametrize("providers_count", [1, 2])
async def test_local_client_concurrency_is_a_real_cap_and_cancelled_waiters_release_it(tmp_path, monkeypatch, limit, providers_count):
    monkeypatch.setattr(local_agents, "selected_agent", lambda _: "codex")
    clients = [local_agents.LocalAgentProvider(Settings(data_dir=tmp_path, agent_concurrency=limit)) for _ in range(providers_count)]
    release, filled = asyncio.Event(), asyncio.Event()
    active, peak, calls = 0, 0, []

    async def generate(system, user):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        calls.append(user)
        if active == limit:
            filled.set()
        try:
            await release.wait()
            return {"answer": user}
        finally:
            active -= 1

    for client in clients:
        monkeypatch.setattr(client, "_generate", generate)
    tasks = [asyncio.create_task(clients[index % providers_count].chat_json("s", str(index))) for index in range(limit + 2)]
    try:
        await asyncio.wait_for(filled.wait(), 2)
        assert len(calls) == limit and peak == limit
        tasks[-1].cancel()
        with pytest.raises(asyncio.CancelledError):
            await tasks[-1]
        release.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks[:-1]), 2)
        assert len(results) == limit + 1 and str(limit + 1) not in calls
        assert active == 0 and peak == limit
    finally:
        release.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.parametrize("summary_limit,agent_limit", [(6, 4), (3, 8), (4, 1)])
async def test_desktop_summary_queue_reaches_the_configured_agent_limit(tmp_path, monkeypatch, summary_limit, agent_limit):
    settings = Settings(data_dir=tmp_path, chat_backend="agent", chat_agent="codex",
                        enrich_concurrency=summary_limit, agent_concurrency=agent_limit)
    conn = open_db(settings.db_path)
    try:
        ids = [service.save_bookmark(conn, f"https://queue.test/{index}", title=f"Saved page {index}",
                                     settings=settings)["bookmark_id"] for index in range(12)]
    finally:
        conn.close()
    monkeypatch.setattr(local_agents, "selected_agent", lambda _: "codex")
    expected = min(summary_limit, agent_limit)
    release, filled = asyncio.Event(), asyncio.Event()
    active, peak, calls = 0, 0, []
    replies = MockProvider(settings)

    async def generate(_provider, system, user):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        calls.append(user)
        if active == expected:
            filled.set()
        try:
            await release.wait()
            return await replies.chat_json(system, user)
        finally:
            active -= 1

    # Keep the shipping provider's shared quota and the real desktop queue.
    # Only the external CLI response is synthetic.
    monkeypatch.setattr(local_agents.LocalAgentProvider, "_generate", generate)
    runner = admin.JobRunner(tmp_path)
    job = runner.start(settings, mode="summarize", fetch=False, limit=None, force=False, bookmark_ids=ids)
    try:
        await asyncio.wait_for(filled.wait(), 5)
        assert peak == expected and len(calls) == expected and job.items_done == 0
        release.set()
        await asyncio.wait_for(runner._task, 10)
        assert job.state == "done", job.error
        assert job.items_done == len(ids) and job.items_failed == 0
        assert len(calls) == len(ids) and peak == expected and active == 0
    finally:
        release.set()
        await runner.shutdown()
