"""Layer 1: probe from this machine.

Cheap first. ``HEAD`` costs one round trip and no body, which is all that is
needed to separate "the server says this URL is gone" from "the server answered
fine". Servers that refuse ``HEAD`` (and there are many -- some CDNs answer 403
or 405 to any method they were not configured for) get one ranged ``GET`` as a
second chance, because filing a working page as blocked on the strength of a
method restriction would be a self-inflicted false positive.

The ranged-GET trap
-------------------
A ranged ``GET`` is the right tool for a *status* and the wrong tool for a
*content comparison*. ``Range: bytes=0-2047`` returns the first two kilobytes,
which for almost any real page is the ``<head>`` and a nav bar -- extract text
from that and every page in the library looks like it has been gutted since
indexing. So the two cases take different paths: liveness checks use the ranged
request, and drift/soft-404 checks (which only run when there is an indexed
body to compare against) use a full, size-capped ``GET``. This distinction was
worth writing down because getting it wrong produces a library-wide false
``drifted``, which looks like a working feature.

Nothing here concludes anything final. A 403 becomes ``blocked_or_forbidden``,
not ``restricted``; a timeout becomes ``unreachable_local``, not ``gone``. The
naming keeps the layer honest about what it can actually see.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

import httpx

from ..fetch.client import (
    DEFAULT_UA,
    MAX_BYTES,
    FetchPolicy,
    Verdict,
    _classify_exception,
    _HostLimiter,
)
from ..fetch.extract import extract
from ..normalize import body_hash, body_normalize_for_hash
from ..text import CJK_RE
from .verdicts import (
    DRIFT_SIMILARITY,
    NEEDS_EXTERNAL,
    Evidence,
    LocalVerdict,
    placeholder_hit,
)

#: Enough bytes for a status and a title, not enough to pretend it is the page.
RANGE_BYTES = 2048

#: HEAD failed in a way that says more about method support than about the
#: resource. 429 is absent on purpose: retrying immediately after being told to
#: slow down is the opposite of the politeness the fetch layer promises.
RETRY_WITH_GET: frozenset[int] = frozenset({400, 401, 403, 405, 406, 501})

#: Cap for the similarity comparison. Beyond this the ratio has converged and
#: the extra characters only cost time.
COMPARE_CHARS = 20_000


@dataclass(slots=True)
class LocalProbe:
    url: str
    verdict: LocalVerdict
    http_status: int | None = None
    final_url: str = ""
    method: str = ""
    elapsed_ms: int = 0
    body_chars: int = 0
    body_hash: str = ""
    length_ratio: float | None = None
    similarity: float | None = None
    error: str = ""
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def needs_external(self) -> bool:
        return self.verdict in NEEDS_EXTERNAL

    @property
    def failed(self) -> bool:
        return self.verdict not in (LocalVerdict.ALIVE, LocalVerdict.SKIPPED)

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "http_status": self.http_status,
            "final_url": self.final_url,
            "method": self.method,
            "elapsed_ms": self.elapsed_ms,
            "body_chars": self.body_chars,
            "length_ratio": self.length_ratio,
            "similarity": self.similarity,
            "error": self.error,
            "evidence": [e.as_dict() for e in self.evidence],
        }


def _verdict_for_status(status: int) -> LocalVerdict | None:
    if status in (404, 410):
        return LocalVerdict.GONE
    if status in (401, 403, 429, 451):
        return LocalVerdict.BLOCKED
    if status >= 500:
        # A 502 means the origin is having a bad day, not that the page is
        # gone. Transient failures share a bucket with timeouts on purpose.
        return LocalVerdict.UNREACHABLE_LOCAL
    if status >= 400:
        return LocalVerdict.BLOCKED
    return None


_LATIN_TOKEN = re.compile(r"[a-z0-9]+")


def _shingles(text: str) -> set[str]:
    """Vocabulary of a document: latin word tokens plus CJK character bigrams.

    Bigrams rather than jieba tokens for the CJK half, because this comparison
    runs on every re-probe and does not need segmentation quality -- it needs a
    stable, cheap set with comparable granularity to the latin side.
    """
    t = body_normalize_for_hash(text or "").lower()[:COMPARE_CHARS]
    if not t:
        return set()
    toks = set(_LATIN_TOKEN.findall(t))
    runs = "".join(ch if CJK_RE.match(ch) else " " for ch in t).split()
    for run in runs:
        if len(run) == 1:
            toks.add(run)
        else:
            toks.update(run[i:i + 2] for i in range(len(run) - 1))
    return toks


def body_similarity(a: str, b: str) -> float:
    """Jaccard overlap of two documents' vocabularies.

    Character-level similarity was the first attempt and it does not work: two
    unrelated English articles of similar length score ~0.9 on a character
    multiset, because English letter frequencies are English letter
    frequencies. Vocabulary overlap has an actual dynamic range.

    The threshold this feeds (``DRIFT_SIMILARITY``) is a judgement call, not a
    measurement -- calibrating it honestly would need the same pages fetched
    months apart, which this project has no dataset for. It is set low, so the
    system under-reports drift rather than demoting pages that merely gained a
    comment section.
    """
    sa, sb = _shingles(a), _shingles(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    return round(inter / (len(sa) + len(sb) - inter), 4)


async def probe_one(
    client: httpx.AsyncClient,
    url: str,
    *,
    policy: FetchPolicy | None = None,
    limiter: _HostLimiter | None = None,
    known_chars: int = 0,
    known_body: str = "",
    known_hash: str = "",
    soft_gone_ratio: float = 0.30,
    title_hint: str = "",
) -> LocalProbe:
    """One URL, one layer-1 conclusion.

    ``known_chars`` / ``known_body`` / ``known_hash`` come from the ``content``
    row captured at index time. Without them the probe can only answer "did the
    server respond", which is why a title-only library gets liveness checking
    but not drift detection.
    """
    pol = policy or FetchPolicy()
    started = time.monotonic()
    ev: list[Evidence] = []
    now = int(time.time())

    def done(verdict: LocalVerdict, **kw) -> LocalProbe:
        return LocalProbe(
            url=url, verdict=verdict,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            evidence=ev, **kw,
        )

    if not url.lower().startswith(("http://", "https://")):
        ev.append(Evidence("local", "not_http", url[:40], now))
        return done(LocalVerdict.SKIPPED, error="not an http(s) url")

    host = httpx.URL(url).host or ""
    headers = {"User-Agent": pol.user_agent or DEFAULT_UA}
    sem = await limiter.acquire(host) if limiter else None
    try:
        try:
            resp = await client.head(url, headers=headers, follow_redirects=True)
            method = "HEAD"
        except Exception as exc:  # noqa: BLE001 - every failure maps to a verdict
            v, msg = _classify_exception(exc)
            sig = "dns_failure" if v is Verdict.DNS_FAIL else "transport_failure"
            ev.append(Evidence("local", sig, msg[:200], now))
            lv = (LocalVerdict.DNS_FAIL if v is Verdict.DNS_FAIL
                  else LocalVerdict.UNREACHABLE_LOCAL)
            return done(lv, method="HEAD", error=msg[:200])

        # Second chance for servers that only dislike the method.
        if resp.status_code in RETRY_WITH_GET:
            ev.append(Evidence("local", "head_refused",
                               f"HTTP {resp.status_code}; retrying with GET", now))
            try:
                resp = await client.get(
                    url, headers={**headers, "Range": f"bytes=0-{RANGE_BYTES - 1}"},
                    follow_redirects=True,
                )
                method = "GET(range)"
            except Exception as exc:  # noqa: BLE001
                v, msg = _classify_exception(exc)
                sig = "dns_failure" if v is Verdict.DNS_FAIL else "transport_failure"
                ev.append(Evidence("local", sig, msg[:200], now))
                lv = (LocalVerdict.DNS_FAIL if v is Verdict.DNS_FAIL
                      else LocalVerdict.UNREACHABLE_LOCAL)
                return done(lv, method="GET(range)", error=msg[:200])

        status = resp.status_code
        final_url = str(resp.url)
        bad = _verdict_for_status(status)
        if bad is not None:
            ev.append(Evidence("local", f"http_{status}", final_url[:200], now))
            return done(bad, http_status=status, final_url=final_url,
                        method=method, error=f"HTTP {status}")

        ev.append(Evidence("local", f"http_{status}", final_url[:200], now))
        if final_url.rstrip("/") != url.rstrip("/"):
            ev.append(Evidence("local", "redirected", final_url[:200], now))

        # 200 with nothing indexed to compare against: liveness is the whole
        # answer available, and claiming more would be invention.
        if known_chars <= 0 and not known_body:
            return done(LocalVerdict.ALIVE, http_status=status,
                        final_url=final_url, method=method)

        try:
            body_resp = await client.get(url, headers=headers, follow_redirects=True)
        except Exception as exc:  # noqa: BLE001
            _v, msg = _classify_exception(exc)
            ev.append(Evidence("local", "body_fetch_failed", msg[:200], now))
            # HEAD said 200; a failure to re-read the body is not evidence the
            # page died, so the liveness answer stands.
            return done(LocalVerdict.ALIVE, http_status=status,
                        final_url=final_url, method=method, error=msg[:200])

        raw = body_resp.content[:MAX_BYTES]
        ex = extract(body_resp.text if raw else "", url=final_url, title_hint=title_hint)
        new_chars = len(ex.text)
        ratio = (new_chars / known_chars) if known_chars > 0 else None
        pat = placeholder_hit(ex.title, ex.text)

        if ratio is not None and ratio < soft_gone_ratio and pat:
            ev.append(Evidence("local", "soft_404",
                               f"length {new_chars}/{known_chars} "
                               f"({ratio:.0%}), matched {pat!r}", now))
            return done(LocalVerdict.SOFT_GONE, http_status=status,
                        final_url=final_url, method="GET", body_chars=new_chars,
                        body_hash=body_hash(ex.text), length_ratio=round(ratio, 4))

        new_hash = body_hash(ex.text)
        if known_hash and new_hash == known_hash:
            return done(LocalVerdict.ALIVE, http_status=status, final_url=final_url,
                        method="GET", body_chars=new_chars, body_hash=new_hash,
                        length_ratio=None if ratio is None else round(ratio, 4),
                        similarity=1.0)

        sim = body_similarity(known_body, ex.text) if known_body else None
        if sim is not None and sim < DRIFT_SIMILARITY:
            ev.append(Evidence("local", "content_drift",
                               f"similarity {sim:.2f} < {DRIFT_SIMILARITY}", now))
            return done(LocalVerdict.DRIFTED, http_status=status, final_url=final_url,
                        method="GET", body_chars=new_chars, body_hash=new_hash,
                        length_ratio=None if ratio is None else round(ratio, 4),
                        similarity=sim)

        return done(LocalVerdict.ALIVE, http_status=status, final_url=final_url,
                    method="GET", body_chars=new_chars, body_hash=new_hash,
                    length_ratio=None if ratio is None else round(ratio, 4),
                    similarity=sim)
    finally:
        if sem is not None:
            sem.release()


async def probe_many(
    targets: Sequence[dict] | Iterable[dict],
    *,
    policy: FetchPolicy | None = None,
    client: httpx.AsyncClient | None = None,
    soft_gone_ratio: float = 0.30,
) -> list[LocalProbe]:
    """Probe a batch under the same global and per-host limits as crawling.

    Each target is a dict with at least ``url`` and optionally ``known_chars``,
    ``known_body``, ``known_hash``, ``title_hint``. Results come back in input
    order so callers can zip them against bookmark ids.
    """
    pol = policy or FetchPolicy()
    items = list(targets)
    limiter = _HostLimiter(pol)
    gate = asyncio.Semaphore(pol.concurrency)
    owned = client is None
    cl = client or httpx.AsyncClient(
        timeout=pol.timeout_s,
        follow_redirects=True,
        max_redirects=pol.max_redirects,
    )
    out: list[LocalProbe | None] = [None] * len(items)

    async def run(i: int, t: dict) -> None:
        async with gate:
            out[i] = await probe_one(
                cl, t["url"], policy=pol, limiter=limiter,
                known_chars=int(t.get("known_chars") or 0),
                known_body=t.get("known_body") or "",
                known_hash=t.get("known_hash") or "",
                soft_gone_ratio=soft_gone_ratio,
                title_hint=t.get("title_hint") or "",
            )

    try:
        await asyncio.gather(*(run(i, t) for i, t in enumerate(items)))
    finally:
        if owned:
            await cl.aclose()
    return [p for p in out if p is not None]
