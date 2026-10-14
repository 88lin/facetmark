"""Exercise the real OpenCode CLI against a disposable, credential-free model server."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from facetmark.config import Settings
from facetmark.local_agents import LocalAgentProvider, resolve_command


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Real CLI validation runs in GitHub Actions only")
    command = resolve_command("opencode")
    assert command, "Installed OpenCode was not detected"
    requests = []
    reply = json.dumps({"summary": "中文摘要链路通过"}, ensure_ascii=False)

    class Model(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(payload)
            chunk = {"id": "fixture", "object": "chat.completion.chunk", "created": 1,
                     "model": "fixture-model", "choices": [{"index": 0,
                     "delta": {"role": "assistant", "content": reply}, "finish_reason": None}]}
            if payload.get("stream"):
                final = {**chunk, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}}
                body = ("data: " + json.dumps(chunk) + "\n\ndata: " + json.dumps(final) + "\n\ndata: [DONE]\n\n").encode()
                content_type = "text/event-stream"
            else:
                body = json.dumps({**chunk, "object": "chat.completion", "choices": [{"index": 0,
                    "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}]}).encode()
                content_type = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Model)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="facetmark-opencode-check-") as temporary:
            root = Path(temporary)
            config = root / "config/opencode"
            config.mkdir(parents=True)
            settings_file = config / "opencode.json"
            settings_file.write_text(json.dumps({
                "model": "fixture/fixture-model",
                "small_model": "fixture/fixture-model",
                "provider": {"fixture": {"npm": "@ai-sdk/openai-compatible", "name": "Fixture",
                    "options": {"baseURL": f"http://127.0.0.1:{server.server_port}/v1", "apiKey": "synthetic-only"},
                    "models": {"fixture-model": {"name": "Fixture", "limit": {"context": 32000, "output": 1000}}}}},
                "permission": {"bash": "allow", "read": "allow"},
                "plugin": ["file:///must-not-load-facetmark-plugin.js"],
                "mcp": {"inherited": {"type": "local", "command": ["must-not-start-facetmark-mcp"]}},
            }), encoding="utf-8")
            before = settings_file.read_bytes()
            environment = {"XDG_CONFIG_HOME": str(root / "config"), "XDG_DATA_HOME": str(root / "data"),
                           "XDG_STATE_HOME": str(root / "state"), "XDG_CACHE_HOME": str(root / "cache"),
                           "OPENCODE_DISABLE_MODELS_FETCH": "1"}

            async def generate():
                provider = LocalAgentProvider(Settings(data_dir=root / "facetmark", chat_backend="agent",
                    chat_agent="opencode", chat_agent_timeout=120))
                try:
                    result = await provider.chat_json("Return a JSON summary.", "测试中文和 $(do-not-execute)")
                    assert result == {"summary": "中文摘要链路通过"}, result
                finally:
                    await provider.aclose()

            with patch.dict(os.environ, environment), patch("facetmark.local_agents.Path.home", return_value=root):
                asyncio.run(generate())
            assert requests, "The real CLI never reached the model service"
            summary_requests = [item for item in requests if "do-not-execute" in json.dumps(item)]
            assert summary_requests, "The bookmark prompt was not delivered"
            assert all(not item.get("tools") for item in summary_requests), "Summary request exposed tools"
            assert settings_file.read_bytes() == before, "Original agent configuration changed"
            assert not list((root / "data").rglob("opencode.db")), "Session database escaped the temporary invocation"
            print(json.dumps({"cli": "OpenCode 1.19.0", "platform": os.name,
                              "model": "isolated synthetic HTTP fixture", "requests": len(requests),
                              "stdin_unicode": True, "tools": False, "source_config_unchanged": True}))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
