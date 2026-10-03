"""Current model options at the HTTP boundary, without credentials or network."""

import importlib.util
import json
from pathlib import Path

import httpx
import pytest
import respx
from pydantic import ValidationError

from facetmark.config import Settings
from facetmark.configfile import read_config, to_toml, write_config
from facetmark.providers import OpenAICompatibleProvider, ProviderError


def provider(tmp_path, **options):
    return OpenAICompatibleProvider(Settings(
        data_dir=tmp_path, api_key="test", base_url="https://model.example/v1", **options,
    ))


@respx.mock
@pytest.mark.parametrize("options", [
    {},
    {"reasoning_effort": "none", "max_completion_tokens": 4096},
    {"reasoning_effort": "low", "max_completion_tokens": 8192},
    {"thinking": {"type": "disabled"}, "max_tokens": 4096},
    {"enable_thinking": False},
    {"chat_template_kwargs": {"enable_thinking": False}},
    {"temperature": 0.2},
])
async def test_options_reach_the_top_level_without_forced_sampling(tmp_path, options):
    route = respx.post("https://model.example/v1/chat/completions").respond(
        200, json={"choices": [{"message": {"content": '{"ok":true}'}}]},
    )
    p = provider(tmp_path, chat_extra_body=json.dumps(options))
    try:
        assert await p.chat_json("Return JSON", "test") == {"ok": True}
        body = json.loads(route.calls[0].request.content)
        assert body == {
            **options,
            "model": p.settings.chat_model,
            "messages": [{"role": "system", "content": "Return JSON"},
                         {"role": "user", "content": "test"}],
            "response_format": {"type": "json_object"},
        }
    finally:
        await p.aclose()


@pytest.mark.parametrize("value", [
    "[]", "null", "broken", '{"temperature":NaN}', '{"stream":false}',
    '{"model":"other"}', '{"messages":[]}', '{"response_format":null}', '{"n":2}',
])
def test_options_reject_invalid_json_and_protocol_overrides(tmp_path, value):
    with pytest.raises(ValidationError):
        Settings(data_dir=tmp_path, chat_extra_body=value)


@respx.mock
@pytest.mark.parametrize("response", [
    httpx.Response(200, text="<html>gateway failure</html>"),
    httpx.Response(200, json=[]),
    httpx.Response(200, json={"choices": [{"message": {"content": []}}]}),
    httpx.Response(200, json={"choices": [{"message": {"content": None}}]}),
    httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]}),
    httpx.Response(200, json={"choices": [{"message": {"refusal": "no", "content": "{}"}}]}),
])
async def test_invalid_or_incomplete_answers_use_the_fallback(tmp_path, response):
    route = respx.post("https://model.example/v1/chat/completions").mock(side_effect=[
        response, httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":true}'}}]}),
    ])
    p = provider(tmp_path, chat_model="first", chat_model_fallbacks="second")
    try:
        assert await p.chat_json("Return JSON", "test") == {"ok": True}
        assert route.call_count == 2
        assert p.chat_model_in_use == "second"
        assert p.chat_model_mix() == {"failed": {"first": 1}, "answered": {"second": 1}}
    finally:
        await p.aclose()


@respx.mock
@pytest.mark.parametrize("send_dimensions", [False, True])
async def test_embedding_batches_keep_order_and_count_each_request(tmp_path, send_dimensions):
    batches = []

    def reply(request):
        body = json.loads(request.content)
        batches.append(body["input"])
        assert body.get("dimensions") == (2 if send_dimensions else None)
        return httpx.Response(200, json={
            "data": [{"index": i, "embedding": [float(t), 1.0]}
                     for i, t in reversed(list(enumerate(body["input"])))],
            "usage": {"total_tokens": len(body["input"])},
        })

    respx.post("https://model.example/v1/embeddings").mock(side_effect=reply)
    p = provider(tmp_path, embed_dim=2, embed_batch_size=2, embed_send_dimensions=send_dimensions)
    try:
        assert await p.embed(["0", "1", "2", "3", "4"]) == [[float(i), 1.0] for i in range(5)]
        assert batches == [["0", "1"], ["2", "3"], ["4"]]
        assert p.usage.calls == 3
        assert p.usage.embed_tokens == 5
    finally:
        await p.aclose()


@respx.mock
@pytest.mark.parametrize("rows", [
    [{"index": 0, "embedding": [1, 2]}, {"index": 1, "embedding": [1]}],
    [{"index": 0, "embedding": [1, 2]}, {"index": 0, "embedding": [1, 2]}],
    [{"index": 0, "embedding": [1, 2]}, {"index": 1, "embedding": ["NaN", 2]}],
])
async def test_every_vector_is_validated_before_return(tmp_path, rows):
    respx.post("https://model.example/v1/embeddings").respond(200, json={"data": rows})
    p = provider(tmp_path, embed_dim=2)
    try:
        with pytest.raises(ProviderError):
            await p.embed(["a", "b"])
    finally:
        await p.aclose()


def test_copyable_provider_examples_roundtrip_through_real_config(tmp_path):
    path = Path(__file__).resolve().parents[1] / "docs/landing/model_presets.py"
    spec = importlib.util.spec_from_file_location("model_presets", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for _, config, *_ in module.PRESETS:
        cfg = tmp_path / "config.toml"
        cfg.write_text(module.config_text(config), encoding="utf-8")
        values = read_config(cfg)
        settings = Settings(**values)
        assert set(values) <= set(Settings.model_fields)
        assert json.loads(settings.chat_extra_body)
        write_config(values, cfg)
        assert read_config(cfg) == values
        assert to_toml(values)
        if settings.embed_backend == "local":
            assert settings.local_embed_path == settings.embed_model
