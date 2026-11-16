"""CI-only HTTP transport for real link-check runs in a synthetic library.

The actual queue, probe, synthesis, persistence and API are exercised. Only
remote HTTP bytes are supplied here. No original website or external observer
is contacted; the hold switch lets a browser leave and stop an active run.
"""
from __future__ import annotations

import asyncio
import hmac
import os

import httpx
from fastapi import HTTPException, Request

from facetmark import health


def install(app) -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("The synthetic health transport is available in GitHub Actions only")
    gate = asyncio.Event()
    gate.set()
    calls: list[dict] = []

    def authorize(request: Request):
        expected = "Bearer " + request.app.state.fm.token
        if not hmac.compare_digest(request.headers.get("authorization", ""), expected):
            raise HTTPException(401, "Synthetic fixture needs the temporary pairing token")

    @app.get("/__fixture/health", include_in_schema=False)
    async def fixture_status(request: Request):
        authorize(request)
        return {"held": not gate.is_set(), "requests": calls,
                "data": "synthetic HTTP transport; no external URLs contacted"}

    @app.post("/__fixture/health", include_in_schema=False)
    async def fixture_control(request: Request, values: dict):
        authorize(request)
        if type(values.get("hold")) is not bool:
            raise HTTPException(400, "Choose the synthetic hold state")
        if values.get("reset"):
            calls.clear()
        if values["hold"]:
            gate.clear()
        else:
            gate.set()
        return {"held": not gate.is_set()}

    async def response(request: httpx.Request):
        calls.append({"method": request.method, "url": str(request.url)})
        await gate.wait()
        if not request.url.host.endswith((".example", ".invalid")):
            return httpx.Response(503, text="Synthetic fixture refuses unknown hosts")
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n", headers={"Content-Type": "text/plain"})
        text = "<html><head><title>Synthetic saved original</title></head><body><article>"
        text += "<p>这是仅用于链接检查的合成原文。Saved source text remains available for reading and comparison.</p>" * 80
        text += "</article></body></html>"
        return httpx.Response(200, text=text if request.method != "HEAD" else "", headers={"Content-Type": "text/html"})

    original = health.check_bookmarks

    async def isolated(conn, **kwargs):
        kwargs.pop("client", None)
        if kwargs.get("settings") is not None:
            kwargs["settings"] = kwargs["settings"].model_copy(update={"health_enable_external": False, "health_proxy_url": None})
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
            return await original(conn, client=client, **kwargs)

    health.check_bookmarks = isolated
