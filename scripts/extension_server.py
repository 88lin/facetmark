"""CI-only loopback server for the shipped unpacked extension, with synthetic data."""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import uvicorn
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from facetmark import service
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.db import open_db
from facetmark.fetch import store

PORT = 8793
BASE = f"http://127.0.0.1:{PORT}"


def main() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise SystemExit("Extension browser validation requires a disposable GitHub-hosted runner")
    with tempfile.TemporaryDirectory(prefix="facetmark-extension-server-") as temporary:
        settings = Settings(data_dir=Path(temporary), use_mock_provider=True, embed_dim=32,
                            chat_model="demo", embed_model="demo", host="127.0.0.1", port=PORT)
        os.environ["FACETMARK_DATA_DIR"] = temporary
        conn = open_db(settings.db_path)
        for index in range(45):
            service.save_bookmark(conn, f"{BASE}/fixture/page/{index}", title=f"Original bookmark {index:02}",
                                  folder="合成收藏 / Extension review", tags=["needle", "合成资料"], settings=settings)
        conn.close()
        app = create_app(settings)
        requests: list[dict] = []
        flags: dict = {}
        finished_quick = 0
        next_page = 100

        @app.middleware("http")
        async def record(request: Request, call_next):
            nonlocal finished_quick
            path = request.url.path
            if not path.startswith(("/_test/", "/fixture/")):
                body = await request.json() if request.method == "POST" else None
                requests.append({"path": path, "method": request.method, "body": body, "query": request.url.query})
            if path == "/quick" and request.query_params.get("q") == "slow":
                await asyncio.sleep(0.8)
                finished_quick += 1
            if path == "/search" and flags.get("delay_search"):
                await asyncio.sleep(0.8)
            if path == "/search" and flags.get("bad_search"):
                return JSONResponse({"hits": [None], "expanded": []})
            if path == "/queue/next" and flags.get("queue_failure"):
                return JSONResponse({"detail": "Synthetic queue service unavailable"}, status_code=503)
            return await call_next(request)

        @app.get("/fixture/page/{index}")
        async def page(index: int, delay: bool = False):
            if delay:
                await asyncio.sleep(8)
            return HTMLResponse("<!doctype html><html><head><title>Original browser page " + str(index)
                                + "</title></head><body><nav>Not article content</nav><article><h1>Browser article "
                                + str(index) + "</h1><p>" + "Browser extracted paragraph. 本文是隔离的合成正文。 " * 40
                                + "</p></article><script>document.querySelector('article').dataset.ready='yes'</script></body></html>")

        @app.get("/_test/state")
        async def inspect():
            state = app.state.fm
            return {"token": state.token, "requests": requests, "finished_quick": finished_quick,
                    "bookmarks": [dict(row) for row in state.conn.execute(
                        "SELECT b.id,b.url,b.title,b.tags,c.body_text,q.state AS queue_state,q.attempts,q.lease_id "
                        "FROM bookmark b LEFT JOIN content c ON c.bookmark_id=b.id "
                        "LEFT JOIN fetch_queue q ON q.bookmark_id=b.id ORDER BY b.id")], "flags": flags}

        @app.post("/_test/flags")
        async def change_flags(request: Request):
            flags.clear()
            flags.update(await request.json())
            return {"ok": True}

        @app.post("/_test/queue")
        async def enqueue(request: Request):
            nonlocal next_page
            values = await request.json()
            state = app.state.fm
            next_page += 1
            url = f"{BASE}/fixture/page/{next_page}" + ("?delay=true" if values.get("delay") else "")
            result = service.save_bookmark(state.conn, url, title=f"Queued original {next_page}", settings=settings)
            bid = result["bookmark_id"]
            store.store_body(state.conn, bid, body="Saved original text before browser reading")
            store.enqueue_for_browser(state.conn, bid, reason="synthetic browser reading")
            state.conn.commit()
            return {"bookmark_id": bid, "url": url}

        @app.post("/_test/edit")
        async def edit(request: Request):
            values = await request.json()
            state = app.state.fm
            if values.get("delete"):
                state.conn.execute("DELETE FROM bookmark WHERE id=?", (values["bookmark_id"],))
            else:
                store.store_body(state.conn, values["bookmark_id"], body=values["body"])
            state.conn.commit()
            return {"ok": True}

        uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
