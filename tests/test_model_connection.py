import asyncio
import json

import httpx

from facetmark.config import Settings
from facetmark.providers import OpenAICompatibleProvider


def test_compatible_chat_retries_explicit_json_mode_rejection_once(tmp_path):
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if "response_format" in body:
            return httpx.Response(400, json={"error": "response_format is not supported"})
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":true}'}}]})

    async def run():
        settings = Settings(data_dir=tmp_path, api_key="synthetic", chat_model="compatible")
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond), base_url="https://synthetic.invalid/v1/") as client:
            provider = OpenAICompatibleProvider(settings, client=client)
            assert await provider.chat_json("Return JSON", "Test") == {"ok": True}
            assert await provider.chat_json("Return JSON", "Test again") == {"ok": True}

    asyncio.run(run())
    assert len(requests) == 3
    assert "response_format" not in requests[-1]


def test_effort_request_reads_final_json_after_inline_thinking(tmp_path):
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {
            "content": '<think>```json\n{"summary":"draft"}\n```</think>{"summary":"final"}',
        }, "finish_reason": "stop"}]})

    async def run():
        settings = Settings(data_dir=tmp_path, api_key="synthetic", chat_model="thinking-model",
                            chat_extra_body='{"reasoning_effort":"max"}')
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond), base_url="https://synthetic.invalid/v1/") as client:
            provider = OpenAICompatibleProvider(settings, client=client)
            assert await provider.chat_json("Return JSON", "Test") == {"summary": "final"}

    asyncio.run(run())
    assert len(requests) == 1
    assert requests[0]["reasoning_effort"] == "max"
