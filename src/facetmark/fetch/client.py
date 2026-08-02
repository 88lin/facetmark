"""Channel A: fetch pages directly from the service.

Politeness is not optional here. This runs against a few thousand hosts that
never asked to be crawled, from a home IP, on behalf of one person. The limits
below are deliberately conservative: a global concurrency cap, at most two
in-flight requests to any one host, and a minimum interval between requests to
the same host regardless of concurrency.

What this module will *not* do is retry its way past a refusal. A 401, 403 or
429 means channel A is the wrong tool, and the job is handed to channel B (the
browser extension), where the user's own session and cookies apply and where
the request is indistinguishable from the user visiting the page -- because
that is what it is.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum

import httpx

from .extract import Extraction, extract, looks_like_wall

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36 facetmark/0.1 (personal bookmark indexer)"
)

#: Hosts that render everything client-side. Sending channel A at these wastes a
#: request and a rate-limit slot to receive an empty shell.
SPA_HOSTS: frozenset[str] = frozenset({
    "twitter.com", "x.com", "www.instagram.com", "instagram.com",
    "www.facebook.com", "facebook.com", "www.linkedin.com", "linkedin.com",
    "www.xiaohongshu.com", "xiaohongshu.com", "www.zhihu.com", "zhihu.com",
    "weibo.com", "www.weibo.com", "www.douyin.com", "douyin.com",
    "docs.google.com", "drive.google.com", "mail.google.com",
    "www.notion.so", "notion.so", "www.figma.com", "figma.com",
    "mp.weixin.qq.com", "docs.qq.com", "www.yuque.com", "yuque.com",
})

MAX_BYTES = 3_000_000  # 3 MB: past this it is a download, not an article.

#: Documents smaller than this are taken at face value. A 2 KB page that yields
#: 130 characters is not a failed extraction -- it is a short page, and sending
#: it round the browser channel would produce the same 130 characters after
#: spending one of the user's tabs. Above this, a thin result means the text is
#: probably somewhere we could not reach, which is what channel B is for.
#: (Found by the P2 smoke test: example.com kept being deferred forever.)
SMALL_DOC_BYTES = 8_000


class Verdict(str, Enum):
    OK = "ok"
    EMPTY = "empty"                # 200, but nothing worth indexing
    WALL = "wall"                  # 200, but a bot check or login gate
    REFUSED = "refused"            # 401 / 403 / 429
    NOT_FOUND = "not_found"        # 404 / 410
    SERVER_ERROR = "server_error"  # 5xx
    DNS_FAIL = "dns_fail"
    UNREACHABLE = "unreachable"    # timeout, reset, TLS failure
    SKIPPED = "skipped"            # non-http(s), or a known SPA host
    TOO_LARGE = "too_large"
    NOT_HTML = "not_html"


#: Verdicts where the browser channel has a real chance of doing better.
DEFER_TO_BROWSER: frozenset[Verdict] = frozenset({
    Verdict.REFUSED, Verdict.WALL, Verdict.EMPTY, Verdict.SKIPPED,
})


@dataclass(slots=True)
class FetchResult:
    url: str
    verdict: Verdict
    http_status: int | None = None
    final_url: str = ""
    body: str = ""
    title: str = ""
    extractor: str = "none"
    error: str = ""
    elapsed_ms: int = 0

    @property
    def should_defer_to_browser(self) -> bool:
        return self.verdict in DEFER_TO_BROWSER


@dataclass(slots=True)
class FetchPolicy:
    concurrency: int = 30
    per_host_concurrency: int = 2
    per_host_min_interval_s: float = 0.5
    timeout_s: float = 15.0
    max_redirects: int = 5
    user_agent: str = DEFAULT_UA
    skip_spa_hosts: bool = True
    max_bytes: int = MAX_BYTES


class _HostLimiter:
    """Per-host concurrency *and* spacing. Concurrency alone is not politeness:
    two slots can still fire back-to-back forever."""

    def __init__(self, policy: FetchPolicy) -> None:
        self._policy = policy
        self._sems: dict[str, asyncio.Semaphore] = {}
        self._next_ok: dict[str, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def acquire(self, host: str) -> asyncio.Semaphore:
        async with self._lock:
            sem = self._sems.get(host)
            if sem is None:
                sem = self._sems[host] = asyncio.Semaphore(self._policy.per_host_concurrency)
        await sem.acquire()
        async with self._lock:
            wait = self._next_ok[host] - time.monotonic()
            self._next_ok[host] = max(
                time.monotonic(), self._next_ok[host]
            ) + self._policy.per_host_min_interval_s
        if wait > 0:
            await asyncio.sleep(wait)
        return sem


def _classify_exception(exc: Exception) -> tuple[Verdict, str]:
    if isinstance(exc, httpx.ConnectError):
        msg = str(exc).lower()
        if "name or service not known" in msg or "nodename nor servname" in msg \
           or "temporary failure in name resolution" in msg or "getaddrinfo" in msg:
            return Verdict.DNS_FAIL, str(exc)
        return Verdict.UNREACHABLE, str(exc)
    if isinstance(exc, httpx.TimeoutException):
        return Verdict.UNREACHABLE, f"timeout: {exc}"
    if isinstance(exc, httpx.TooManyRedirects):
        return Verdict.UNREACHABLE, "redirect loop"
    if isinstance(exc, httpx.HTTPError):
        return Verdict.UNREACHABLE, str(exc)
    return Verdict.UNREACHABLE, f"{type(exc).__name__}: {exc}"


def _verdict_for_status(status: int) -> Verdict | None:
    if status in (401, 403, 429):
        return Verdict.REFUSED
    if status in (404, 410):
        return Verdict.NOT_FOUND
    if status >= 500:
        return Verdict.SERVER_ERROR
    if status >= 400:
        return Verdict.REFUSED
    return None


async def fetch_one(
    client: httpx.AsyncClient,
    url: str,
    *,
    policy: FetchPolicy | None = None,
    limiter: _HostLimiter | None = None,
    title_hint: str = "",
) -> FetchResult:
    pol = policy or FetchPolicy()
    started = time.monotonic()

    def done(**kw) -> FetchResult:
        return FetchResult(url=url, elapsed_ms=int((time.monotonic() - started) * 1000), **kw)

    if not url.lower().startswith(("http://", "https://")):
        return done(verdict=Verdict.SKIPPED, error="not an http(s) url")
    host = httpx.URL(url).host or ""
    if pol.skip_spa_hosts and host in SPA_HOSTS:
        return done(verdict=Verdict.SKIPPED, error=f"{host} renders client-side")

    sem = await limiter.acquire(host) if limiter else None
    try:
        try:
            resp = await client.get(url, headers={"User-Agent": pol.user_agent},
                                    follow_redirects=True)
        except Exception as exc:  # noqa: BLE001 - mapped to a verdict below
            v, msg = _classify_exception(exc)
            return done(verdict=v, error=msg)

        bad = _verdict_for_status(resp.status_code)
        if bad is not None:
            return done(verdict=bad, http_status=resp.status_code,
                        final_url=str(resp.url), error=f"HTTP {resp.status_code}")

        ctype = resp.headers.get("content-type", "")
        if ctype and "html" not in ctype.lower() and "xml" not in ctype.lower():
            return done(verdict=Verdict.NOT_HTML, http_status=resp.status_code,
                        final_url=str(resp.url), error=ctype)
        raw = resp.content
        if len(raw) > pol.max_bytes:
            return done(verdict=Verdict.TOO_LARGE, http_status=resp.status_code,
                        final_url=str(resp.url), error=f"{len(raw)} bytes")

        html = resp.text
        ex: Extraction = extract(html, url=str(resp.url), title_hint=title_hint)
        if looks_like_wall(html, ex.text):
            return done(verdict=Verdict.WALL, http_status=resp.status_code,
                        final_url=str(resp.url), title=ex.title,
                        extractor=ex.extractor, body=ex.text)
        if not ex.ok:
            # A short body from a short document is the whole document.
            if ex.text and len(html) < SMALL_DOC_BYTES:
                return done(verdict=Verdict.OK, http_status=resp.status_code,
                            final_url=str(resp.url), title=ex.title,
                            extractor=ex.extractor, body=ex.text)
            return done(verdict=Verdict.EMPTY, http_status=resp.status_code,
                        final_url=str(resp.url), title=ex.title,
                        extractor=ex.extractor, body=ex.text)
        return done(verdict=Verdict.OK, http_status=resp.status_code,
                    final_url=str(resp.url), body=ex.text, title=ex.title,
                    extractor=ex.extractor)
    finally:
        if sem is not None:
            sem.release()


@dataclass(slots=True)
class BatchResult:
    results: list[FetchResult] = field(default_factory=list)

    @property
    def ok(self) -> list[FetchResult]:
        return [r for r in self.results if r.verdict is Verdict.OK]

    @property
    def deferred(self) -> list[FetchResult]:
        return [r for r in self.results if r.should_defer_to_browser]

    def by_verdict(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.results:
            out[r.verdict.value] = out.get(r.verdict.value, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))


async def fetch_many(
    urls: Sequence[str] | Iterable[str],
    *,
    policy: FetchPolicy | None = None,
    client: httpx.AsyncClient | None = None,
    on_result=None,
) -> BatchResult:
    """Fetch a batch under the global and per-host limits.

    Results come back in input order regardless of completion order, so a caller
    can zip them against bookmark ids without bookkeeping.
    """
    pol = policy or FetchPolicy()
    urls = list(urls)
    limiter = _HostLimiter(pol)
    gate = asyncio.Semaphore(pol.concurrency)
    owned = client is None
    cl = client or httpx.AsyncClient(
        timeout=pol.timeout_s,
        max_redirects=pol.max_redirects,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=pol.concurrency,
                            max_keepalive_connections=pol.concurrency),
    )

    async def one(u: str) -> FetchResult:
        async with gate:
            r = await fetch_one(cl, u, policy=pol, limiter=limiter)
            if on_result is not None:
                on_result(r)
            return r

    try:
        results = await asyncio.gather(*(one(u) for u in urls))
    finally:
        if owned:
            await cl.aclose()
    return BatchResult(list(results))
