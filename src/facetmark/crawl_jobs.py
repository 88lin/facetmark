"""Desktop site imports with durable progress and joined cancellation."""
from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from . import admin
from .config import Settings
from .crawl import DEFAULT_MAX_PAGES, CrawlReport, crawl_site
from .db import open_db
from .normalize import host_excluded


class CrawlRequest(BaseModel):
    start_url: str = Field(min_length=1, max_length=8192)
    max_pages: int = Field(default=DEFAULT_MAX_PAGES, ge=1, le=500)
    same_domain: bool = True

    @field_validator("start_url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        value = value.strip()
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError("Use an HTTP(S) URL without embedded credentials")
        # Force validation of malformed/out-of-range ports before starting.
        _ = parts.port
        return value


@dataclass
class CrawlJob:
    params: dict
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: str = "running"
    started_at: int = field(default_factory=lambda: int(time.time()))
    finished_at: int | None = None
    report: dict = field(default_factory=dict)
    current_url: str = ""
    error: str = ""
    cancel_requested: bool = False

    def as_dict(self) -> dict:
        return {"id": self.id, "state": self.state, "params": self.params,
                "started_at": self.started_at, "finished_at": self.finished_at,
                "report": self.report, "current_url": self.current_url,
                "error": self.error, "cancel_requested": self.cancel_requested,
                "retryable": self.state in {"cancelled", "interrupted", "partial", "failed"}}


class CrawlRunner:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "last-crawl-job.json"
        self.job: CrawlJob | None = None
        self.task: asyncio.Task | None = None
        self.previous: dict | None = None
        self.stopping = False
        with contextlib.suppress(OSError, ValueError, TypeError):
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(saved, dict) and isinstance(saved.get("params"), dict):
                CrawlRequest.model_validate(saved["params"])
                if saved.get("state") == "running":
                    saved.update(state="interrupted", retryable=True, finished_at=int(time.time()),
                                 error="Site import interrupted; rerun to reuse pages already saved.")
                self.previous = saved

    @property
    def running(self) -> bool:
        return self.task is not None and not self.task.done()

    def current(self) -> dict:
        return self.job.as_dict() if self.job else self.previous or {"state": "idle"}

    def persist(self) -> None:
        if self.job is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.job.as_dict(), ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)

    def start(self, request: CrawlRequest, settings: Settings) -> dict:
        if self.running:
            raise HTTPException(409, "A site import is already running")
        self.stopping = False
        self.job = CrawlJob(params=request.model_dump(), report=CrawlReport(request.start_url).as_dict())
        self.persist()
        self.task = asyncio.create_task(self._run(self.job, settings.model_copy(deep=True)))
        return self.job.as_dict()

    async def _run(self, job: CrawlJob, settings: Settings) -> None:
        conn = None
        try:
            conn = open_db(settings.db_path, same_thread=False)
            conn.isolation_level = None

            def progress(report):
                job.report = report.as_dict()
                self.persist()

            def saved_page(url, _title, _has_body):
                job.current_url = url
                conn.commit()

            result = await crawl_site(conn, **job.params, settings=settings, on_page=saved_page,
                                      on_progress=progress, keep_existing=True)
            job.report = result.as_dict()
            unsuccessful = result.errors + result.robots_denied + result.privacy_skipped + result.skipped
            job.state = "partial" if unsuccessful else "done"
        except asyncio.CancelledError:
            job.state = "interrupted" if self.stopping else "cancelled"
        except Exception as exc:  # noqa: BLE001 - durable task failure
            job.state = "failed"
            job.error = admin.safe_error(exc, settings)
        finally:
            if conn is not None:
                # crawl_site joins every child before propagating cancellation.
                conn.commit()
                conn.close()
            job.finished_at = int(time.time())
            self.persist()

    async def cancel(self, *, shutdown: bool = False) -> dict:
        task, job = self.task, self.job
        if task is not None and not task.done():
            self.stopping = shutdown
            if job:
                job.cancel_requested = True
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            # A task cancelled before its coroutine begins cannot run finally.
            if job and job.state == "running":
                job.state = "interrupted" if shutdown else "cancelled"
                job.finished_at = int(time.time())
                self.persist()
        return self.current()

    async def shutdown(self) -> None:
        await self.cancel(shutdown=True)


def register(app: FastAPI, auth: list) -> None:
    deps = [*auth, Depends(admin.admin_gate)]

    @app.get("/admin/crawl", dependencies=deps)
    async def status(request: Request):
        return request.app.state.fm.crawls.current()

    @app.post("/admin/crawl", dependencies=deps)
    async def start(body: CrawlRequest, request: Request):
        state = request.app.state.fm
        async with state.lock:
            if (state.jobs.running or state.health_running or state.model_users
                    or any(not task.done() for task in state.chat_runs.values())):
                raise HTTPException(409, "Wait for active processing, model requests or link checks before importing a site")
            if host_excluded(urlsplit(body.start_url).hostname or "", state.settings.privacy_excluded_domains):
                raise HTTPException(400, "This site is excluded in your privacy settings")
            return state.crawls.start(body, state.settings)

    @app.post("/admin/crawl/cancel", dependencies=deps)
    async def cancel(request: Request):
        # Joining network tasks does not hold the shared metadata lock.
        return await request.app.state.fm.crawls.cancel()
