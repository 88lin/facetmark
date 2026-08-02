"""Layer 2: ask somebody else.

The premise of this layer is that the local machine is a biased observer. Its
DNS may be poisoned, its egress may be geoblocked, its IP may be on a
reputation list. Every one of those produces the same symptoms as a deleted
page, and no amount of retrying from the same socket will separate them. So the
question stops being "is this page alive" and becomes "does anyone else see it",
which is answerable.

Three independent sources, chosen because they fail differently:

* **DoH, two resolvers.** Cheapest, and the only one that sees just a hostname
  rather than a full URL. Disagreement between resolvers is direct evidence of
  DNS-layer partition -- one of them is being lied to.
* **Wayback availability.** The useful signal is not "a snapshot exists" (any
  page that ever existed has one) but "a snapshot was taken *after* the moment
  we started failing". Somebody's crawler reached it when we could not.
* **A public reader proxy.** Dual purpose, and the reason it earns its keep: a
  200 proves the page renders from a different egress, *and* it hands back the
  text, which can be filed straight into ``content`` for a page channel A could
  never reach.

Absence of evidence is not evidence here. "No snapshot" and "the resolver timed
out" contribute nothing in either direction; only positive observations move
the conclusion. That asymmetry is what keeps the layer from manufacturing
``gone`` verdicts out of a flaky network.

Privacy boundary: DoH sees the hostname, Wayback and the reader proxy see the
whole URL. Each is separately switchable, and any host on
``privacy_excluded_domains`` skips this layer entirely and degrades to
local-only, low-confidence checking.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from ..config import Settings, get_settings
from ..normalize import host_excluded
from .verdicts import Evidence

#: Reader proxies return whole articles; this bounds one page's cost.
READER_MAX_CHARS = 40_000

DNS_RCODE_NXDOMAIN = 3
DNS_RCODE_SERVFAIL = 2


@dataclass(slots=True)
class DohAnswer:
    endpoint: str
    rcode: int | None = None
    addresses: tuple[str, ...] = ()
    error: str = ""

    @property
    def resolved(self) -> bool:
        return bool(self.addresses)

    @property
    def nxdomain(self) -> bool:
        return self.rcode == DNS_RCODE_NXDOMAIN

    @property
    def usable(self) -> bool:
        """Did this resolver actually answer? A timeout is not a 'no'."""
        return not self.error and self.rcode is not None

    def as_dict(self) -> dict:
        return {"endpoint": self.endpoint, "rcode": self.rcode,
                "addresses": list(self.addresses), "error": self.error}


@dataclass(slots=True)
class ExternalReport:
    checked: bool = False
    skipped_reason: str = ""
    doh: list[DohAnswer] = field(default_factory=list)
    resolver_divergence: bool = False
    resolvers_agree_nxdomain: bool = False
    any_resolved: bool = False
    snapshot_url: str = ""
    snapshot_ts: int | None = None
    snapshot_after_failure: bool = False
    reader_ok: bool = False
    recovered_body: str = ""
    recovered_title: str = ""
    proxy_ok: bool = False
    evidence: list[Evidence] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def reachable_elsewhere(self) -> bool:
        """A positive observation from another egress. This is the single
        signal that overrides everything the local layer concluded."""
        return self.reader_ok or self.proxy_ok

    def as_dict(self) -> dict:
        return {
            "checked": self.checked,
            "skipped_reason": self.skipped_reason,
            "doh": [d.as_dict() for d in self.doh],
            "resolver_divergence": self.resolver_divergence,
            "resolvers_agree_nxdomain": self.resolvers_agree_nxdomain,
            "any_resolved": self.any_resolved,
            "snapshot_url": self.snapshot_url,
            "snapshot_ts": self.snapshot_ts,
            "snapshot_after_failure": self.snapshot_after_failure,
            "reader_ok": self.reader_ok,
            "recovered_chars": len(self.recovered_body),
            "proxy_ok": self.proxy_ok,
            "evidence": [e.as_dict() for e in self.evidence],
            "errors": self.errors,
        }


def _doh_url(endpoint: str, host: str) -> tuple[str, dict[str, str]]:
    """Both Cloudflare and Google speak the same JSON dialect; they disagree
    only on the path and on whether the JSON content type must be requested."""
    sep = "&" if "?" in endpoint else "?"
    return f"{endpoint}{sep}name={host}&type=A", {"accept": "application/dns-json"}


async def doh_query(client: httpx.AsyncClient, host: str, endpoint: str,
                    *, timeout: float = 8.0) -> DohAnswer:
    url, headers = _doh_url(endpoint, host)
    try:
        r = await client.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return DohAnswer(endpoint, error=f"HTTP {r.status_code}")
        data = r.json()
    except Exception as exc:  # noqa: BLE001 - a broken resolver is just no answer
        return DohAnswer(endpoint, error=f"{type(exc).__name__}: {exc}"[:160])
    rcode = data.get("Status")
    addrs = tuple(
        str(a.get("data", ""))
        for a in (data.get("Answer") or [])
        if a.get("type") == 1 and a.get("data")
    )
    return DohAnswer(endpoint, rcode=rcode if isinstance(rcode, int) else None,
                     addresses=addrs)


def _parse_wayback_ts(ts: str) -> int | None:
    try:
        dt = datetime.strptime(ts[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    return int(dt.timestamp())


async def wayback_lookup(client: httpx.AsyncClient, url: str, api: str,
                         *, timeout: float = 10.0) -> tuple[str, int | None, str]:
    """Return ``(snapshot_url, snapshot_epoch, error)``."""
    sep = "&" if "?" in api else "?"
    try:
        r = await client.get(f"{api}{sep}url={httpx.URL(url)}", timeout=timeout)
        if r.status_code != 200:
            return "", None, f"HTTP {r.status_code}"
        data = r.json()
    except Exception as exc:  # noqa: BLE001
        return "", None, f"{type(exc).__name__}: {exc}"[:160]
    closest = ((data.get("archived_snapshots") or {}).get("closest") or {})
    if not closest.get("available"):
        return "", None, ""
    return str(closest.get("url", "")), _parse_wayback_ts(str(closest.get("timestamp", ""))), ""


async def reader_fetch(client: httpx.AsyncClient, url: str, proxy: str,
                       *, timeout: float = 25.0) -> tuple[bool, str, str]:
    """Return ``(ok, text, error)``. Reader proxies answer plain text."""
    if not proxy:
        return False, "", "no reader proxy configured"
    target = proxy if proxy.endswith(("/", "=")) else proxy + "/"
    try:
        r = await client.get(target + url, timeout=timeout,
                             headers={"accept": "text/plain"})
    except Exception as exc:  # noqa: BLE001
        return False, "", f"{type(exc).__name__}: {exc}"[:160]
    if r.status_code != 200:
        return False, "", f"HTTP {r.status_code}"
    return True, r.text[:READER_MAX_CHARS], ""


async def proxy_probe(url: str, proxy_url: str, *, timeout: float = 20.0,
                      user_agent: str = "") -> tuple[bool, int | None, str]:
    """Layer 3. A second egress the user controls. Off unless configured.

    A separate client is unavoidable: the proxy is the entire point, and
    reusing the caller's (unproxied) client would silently answer the wrong
    question.
    """
    headers = {"User-Agent": user_agent} if user_agent else {}
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=timeout,
                                     follow_redirects=True) as cl:
            r = await cl.get(url, headers=headers)
    except Exception as exc:  # noqa: BLE001
        return False, None, f"{type(exc).__name__}: {exc}"[:160]
    return (200 <= r.status_code < 400), r.status_code, ""


async def gather_external(
    client: httpx.AsyncClient,
    url: str,
    *,
    settings: Settings | None = None,
    first_failed_ts: int | None = None,
    now_ts: int | None = None,
) -> ExternalReport:
    """Run every enabled layer-2 source concurrently and report observations.

    This function decides nothing. It records what each source said; the
    synthesis step weighs it.
    """
    st = settings or get_settings()
    now = int(time.time()) if now_ts is None else int(now_ts)
    rep = ExternalReport()

    host = httpx.URL(url).host or ""
    if not st.health_enable_external:
        rep.skipped_reason = "external checks disabled"
        rep.evidence.append(Evidence("policy", "external_disabled", "", now))
        return rep
    if host_excluded(host, st.privacy_excluded_domains):
        rep.skipped_reason = f"{host} is on the privacy exclusion list"
        rep.evidence.append(Evidence("policy", "privacy_excluded", host, now))
        return rep

    tasks: dict[str, asyncio.Task] = {}
    if st.health_enable_doh and host:
        for ep in st.health_doh_endpoints:
            tasks[f"doh:{ep}"] = asyncio.ensure_future(doh_query(client, host, ep))
    if st.health_enable_wayback:
        tasks["wayback"] = asyncio.ensure_future(
            wayback_lookup(client, url, st.health_wayback_api))
    if st.health_enable_reader:
        tasks["reader"] = asyncio.ensure_future(
            reader_fetch(client, url, st.health_reader_proxy))
    if st.health_proxy_url:
        tasks["proxy"] = asyncio.ensure_future(
            proxy_probe(url, st.health_proxy_url, user_agent=st.user_agent))

    if not tasks:
        rep.skipped_reason = "no external source enabled"
        rep.evidence.append(Evidence("policy", "no_external_source", "", now))
        return rep

    rep.checked = True
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for key, res in zip(tasks.keys(), results, strict=True):
        if isinstance(res, BaseException):
            rep.errors.append(f"{key}: {type(res).__name__}: {res}"[:200])
            continue
        if key.startswith("doh:"):
            rep.doh.append(res)
        elif key == "wayback":
            rep.snapshot_url, rep.snapshot_ts, err = res
            if err:
                rep.errors.append(f"wayback: {err}")
        elif key == "reader":
            rep.reader_ok, text, err = res
            if err:
                rep.errors.append(f"reader: {err}")
            if rep.reader_ok:
                rep.recovered_body = text
                rep.recovered_title = text.splitlines()[0].strip()[:200] if text else ""
        elif key == "proxy":
            rep.proxy_ok, status, err = res
            if err:
                rep.errors.append(f"proxy: {err}")
            if rep.proxy_ok:
                rep.evidence.append(Evidence("proxy", "http_ok", str(status), now))

    usable = [d for d in rep.doh if d.usable]
    rep.any_resolved = any(d.resolved for d in usable)
    rep.resolver_divergence = (
        len(usable) >= 2
        and any(d.resolved for d in usable)
        and any(d.nxdomain or (not d.resolved and d.rcode in (0, DNS_RCODE_SERVFAIL))
                for d in usable)
    )
    rep.resolvers_agree_nxdomain = bool(usable) and all(d.nxdomain for d in usable)
    if rep.resolver_divergence:
        detail = "; ".join(
            f"{httpx.URL(d.endpoint).host}={'A' if d.resolved else f'rcode {d.rcode}'}"
            for d in usable
        )
        rep.evidence.append(Evidence("doh", "resolver_divergence", detail, now))
    elif rep.resolvers_agree_nxdomain:
        rep.evidence.append(Evidence("doh", "all_resolvers_nxdomain",
                                     f"{len(usable)} resolvers", now))
    elif rep.any_resolved:
        rep.evidence.append(Evidence("doh", "resolves", host, now))

    if rep.snapshot_ts is not None:
        rep.snapshot_after_failure = (
            first_failed_ts is not None and rep.snapshot_ts >= first_failed_ts
        )
        stamp = datetime.fromtimestamp(rep.snapshot_ts, tz=timezone.utc).date().isoformat()
        rep.evidence.append(Evidence(
            "wayback",
            "snapshot_after_failure" if rep.snapshot_after_failure else "snapshot_exists",
            stamp, now,
        ))
    if rep.reader_ok:
        rep.evidence.append(Evidence("reader", "http_200",
                                     f"body {len(rep.recovered_body)} chars", now))
    return rep
