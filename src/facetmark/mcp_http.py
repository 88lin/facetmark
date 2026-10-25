"""Authenticated Streamable HTTP access to the same tools as the stdio server.

The desktop sidecar already serves the local workbench. This transport lives in
that process, so an AI client does not need to install or launch Python. Its
token is independent from browser pairing and is disclosed only by local admin.
"""
from __future__ import annotations

import hmac
import json
import secrets
import time
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel
from starlette.responses import JSONResponse

from .admin import admin_gate
from .configfile import config_path, external_setting_keys, update_config
from .mcp_server import Ctx, create_server

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
LOOPBACK_PEERS = LOOPBACK_HOSTS | {"::ffff:127.0.0.1"}
PROTOCOL_VERSION = "2025-03-26"


def _origin_matches(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    try:
        parsed = urlsplit(origin)
        actual = request.url
        return (parsed.scheme in {"http", "https"}
                and parsed.hostname in LOOPBACK_HOSTS
                and not parsed.username and not parsed.password
                and not parsed.path and not parsed.query and not parsed.fragment
                and parsed.scheme == actual.scheme
                and (parsed.port or (443 if parsed.scheme == "https" else 80))
                == (actual.port or (443 if actual.scheme == "https" else 80)))
    except ValueError:
        return False


class _AccessGate:
    def __init__(self, bridge):
        self.bridge = bridge

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.bridge.transport(scope, receive, send)
        state = getattr(self.bridge.app.state, "fm", None)
        if state is None:
            return await JSONResponse({"detail": "MCP service is starting"}, status_code=503)(scope, receive, send)
        if not state.settings.mcp_enabled:
            return await JSONResponse({"detail": "MCP is disabled"}, status_code=404)(scope, receive, send)
        request = Request(scope, receive)
        peer = (request.client.host if request.client else "") or ""
        if (peer not in LOOPBACK_PEERS or not request.headers.get("host")
                or request.url.hostname not in LOOPBACK_HOSTS or not _origin_matches(request)):
            return await JSONResponse({"detail": "MCP is local-only"}, status_code=403)(scope, receive, send)
        authorization = request.headers.get("authorization", "")
        supplied = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
        token = state.settings.mcp_token
        if not token or not hmac.compare_digest(supplied, token):
            return await JSONResponse({"detail": "Bad or missing MCP token"}, status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="facetmark-mcp"'})(scope, receive, send)
        self.bridge.last_request_at = int(time.time())
        return await self.bridge.transport(scope, receive, send)


class MCPBridge:
    def __init__(self, app: FastAPI):
        self.app = app
        self.server = create_server(context=Ctx(None, None, state_getter=lambda: app.state.fm))
        # Stateless HTTP still uses the SDK protocol and its lifespan. Avoid
        # cached sessions retaining authority after disabling or rotating keys.
        self.transport = self.server.http_app(path="/", transport="streamable-http",
                                             json_response=True, stateless_http=True)
        self.transport_ready = False
        self.last_request_at = None
        self.last_probe = None

    @asynccontextmanager
    async def lifespan(self):
        async with self.transport.router.lifespan_context(self.transport):
            self.transport_ready = True
            try:
                yield
            finally:
                self.transport_ready = False

    def view(self, request: Request) -> dict:
        state = self.app.state.fm
        enabled, token = state.settings.mcp_enabled, state.settings.mcp_token
        port = request.url.port or (443 if request.url.scheme == "https" else 80)
        endpoint = f"{request.url.scheme}://127.0.0.1:{port}/mcp/"
        locked = external_setting_keys({"mcp_enabled", "mcp_token"})
        status = ("disabled" if not enabled else "unconfigured" if not token
                  else "ready" if self.transport_ready else "starting")
        config = {"type": "http", "url": endpoint, "headers": {"Authorization": "Bearer " + token}}
        return {"enabled": enabled, "configured": bool(token),
                "running": enabled and bool(token) and self.transport_ready,
                "transport_ready": self.transport_ready, "status": status,
                "error": (self.last_probe or {}).get("error", ""), "endpoint": endpoint,
                "token": token, "client_config": {"mcpServers": {"facetmark": config}},
                "codex_config": "[mcp_servers.facetmark]\nurl = " + json.dumps(endpoint)
                    + "\nhttp_headers = { Authorization = " + json.dumps("Bearer " + token) + " }\n",
                "locked": {"enabled": "mcp_enabled" in locked, "token": "mcp_token" in locked},
                "last_request_at": self.last_request_at, "probe": self.last_probe}

    async def probe(self, request: Request) -> dict:
        view = self.view(request)
        if not view["running"]:
            return {"ok": False, "error": "Enable MCP before testing the protocol"}
        headers = {"Authorization": "Bearer " + view["token"],
                   "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": PROTOCOL_VERSION}
        # Exercise the mounted HTTP protocol and real FastMCP handlers without
        # claiming that an external AI client or a particular socket connected.
        transport = httpx.ASGITransport(app=self.app, client=("127.0.0.1", 0))
        try:
            async with httpx.AsyncClient(transport=transport, timeout=10) as client:
                async def call(method, request_id, params=None):
                    response = await client.post(view["endpoint"], headers=headers,
                        json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
                    response.raise_for_status()
                    payload = response.json()
                    if payload.get("error"):
                        raise ValueError("MCP protocol returned an error")
                    return payload["result"]

                initialized = await call("initialize", 1, {"protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {}, "clientInfo": {"name": "facetmark-protocol-check", "version": "1"}})
                notification = await client.post(view["endpoint"], headers=headers,
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"})
                notification.raise_for_status()
                tools = await call("tools/list", 2)
                resources = await call("resources/list", 3)
                templates = await call("resources/templates/list", 4)
            return {"ok": True, "server": initialized["serverInfo"]["name"],
                    "tools": len(tools["tools"]), "resources": len(resources["resources"]),
                    "templates": len(templates["resourceTemplates"]), "transport": "streamable-http"}
        except (httpx.HTTPError, ValueError, KeyError, TypeError, RuntimeError):
            return {"ok": False, "error": "MCP protocol check failed; restart the local service and retry"}


class MCPPatch(BaseModel):
    enabled: bool | None = None
    rotate_token: bool = False
    probe: bool = False


def register(app: FastAPI, auth: list) -> MCPBridge:
    bridge = MCPBridge(app)
    app.state.mcp_bridge = bridge
    app.mount("/mcp", _AccessGate(bridge), name="facetmark-mcp")
    deps = [*auth, Depends(admin_gate)]

    @app.get("/admin/mcp", dependencies=deps)
    async def status(request: Request):
        return JSONResponse(bridge.view(request), headers={"Cache-Control": "no-store"})

    @app.post("/admin/mcp", dependencies=deps)
    async def configure(body: MCPPatch, request: Request):
        state = app.state.fm
        changes = {}
        async with state.lock:
            if body.enabled is not None and body.enabled != state.settings.mcp_enabled:
                changes["mcp_enabled"] = body.enabled
            if body.rotate_token or (body.enabled and not state.settings.mcp_token):
                changes["mcp_token"] = secrets.token_urlsafe(32)
            locked = external_setting_keys(set(changes))
            if locked:
                raise HTTPException(409, "MCP settings are set by the environment; unset the variables to edit here")
            if changes:
                update_config(changes, config_path(state.settings.data_dir))
                state.settings = state.settings.model_copy(update=changes)
                for key in changes:
                    state.pending_settings.pop(key, None)
                bridge.last_probe = None
        if body.probe:
            bridge.last_probe = await bridge.probe(request)
        return JSONResponse(bridge.view(request), headers={"Cache-Control": "no-store"})
