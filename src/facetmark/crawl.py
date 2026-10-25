"""Crawl a site into the library: ``facetmark crawl https://example.com``.

Ported from hister's ``cmd/crawl`` (its crawler walks a site and indexes what
it finds). facetmark already had every piece except the walk itself: the
politeness machinery in :mod:`facetmark.fetch.client` -- robots.txt, a
per-host concurrency *and* spacing limit, a real user agent, a byte ceiling --
and the storage in :mod:`facetmark.fetch.store`. This module is only the BFS
frontier on top of them, plus link extraction, which stdlib's ``html.parser``
does without a new dependency.

The bounds are the feature, not a limitation. A personal bookmark library has
no use for a general-purpose crawler, and a tool that can accidentally walk
ten thousand pages is a tool that cannot be run casually. ``--max-pages``
defaults to 25, off-domain links are ignored by default, hosts on
``privacy_excluded_domains`` are not contacted at all, and every discovered
page goes through ``save_bookmark`` so the URL-level dedup the importer already
relies on applies to crawled pages too.

What the crawl does *not* do: enrich or embed. The crawled pages are ordinary
bookmarks with bodies; ``facetmark index`` runs the rest of the pipeline and
its fingerprints mean it will only process what the crawl actually added.
"""

from __future__ import annotations

import asyncio
import contextlib
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlsplit

import httpx

from .config import Settings, get_settings
from .fetch.client import FetchPolicy, RobotsCache, _HostLimiter
from .fetch.extract import extract
from .fetch.safety import PublicFetchTransport
from .fetch.store import policy_from_settings, store_body
from .normalize import host_excluded, normalize_url, registrable_domain
from .service import save_bookmark

#: The default page budget. 25 pages is "read the section of the docs I am
#: looking at"; 10,000 is a slurp, and slurps are not what a bookmark library
#: is for. The flag exists for the reader who wants more and knows it.
DEFAULT_MAX_PAGES = 25

#: Extensions never worth fetching even when they are linked. The fetch layer
#: would refuse them as non-HTML anyway; skipping them earlier keeps the crawl
#: budget for pages. Stored without the dot: it is compared against the
#: *suffix of the last path segment*, which is what a link actually carries.
SKIP_EXTENSIONS = frozenset((
    "png", "jpg", "jpeg", "gif", "webp", "svg", "ico", "css", "js",
    "json", "xml", "rss", "zip", "tar", "gz", "tgz", "pdf", "doc",
    "docx", "xls", "xlsx", "mp3", "mp4", "webm", "woff", "woff2",
    "ttf", "eot", "wasm",
))


class _LinkParser(HTMLParser):
    """Collect ``href``/``src`` targets from anchors. Tolerant by design:
    real pages have broken markup, and a parser error must cost one link,
    not the crawl."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag not in ("a", "link"):
            return
        for name, value in attrs:
            if name == "href" and value:
                self.links.append(value)


def extract_links(html: str, base_url: str) -> list[str]:
    """Absolute, defragmented, deduplicated http(s) URLs from one page."""
    parser = _LinkParser()
    # Broken markup is the normal case, not the exception: one bad page costs
    # its links, never the crawl.
    with contextlib.suppress(Exception):
        parser.feed(html)
    out: list[str] = []
    seen: set[str] = set()
    for href in parser.links:
        try:
            url, _frag = urldefrag(urljoin(base_url, href))
        except ValueError:
            continue
        if not url.lower().startswith(("http://", "https://")):
            continue
        if "." in url.split("/")[-1] and url.split("/")[-1].rsplit(".", 1)[-1].lower() in SKIP_EXTENSIONS:
            continue
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


@dataclass(slots=True)
class CrawlReport:
    """What one crawl did, in the vocabulary the CLI prints."""
    start_url: str
    links_found: int = 0
    pages_fetched: int = 0
    pages_attempted: int = 0
    inserted: int = 0
    already_known: int = 0
    bodies_stored: int = 0
    skipped: int = 0
    errors: int = 0
    robots_denied: int = 0
    off_domain_skipped: int = 0
    privacy_skipped: int = 0
    #: The last error per distinct verdict, for the operator; not per page.
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "start_url": self.start_url, "links_found": self.links_found,
            "pages_fetched": self.pages_fetched, "inserted": self.inserted,
            "pages_attempted": self.pages_attempted,
            "already_known": self.already_known, "bodies_stored": self.bodies_stored,
            "skipped": self.skipped, "errors": self.errors,
            "robots_denied": self.robots_denied, "off_domain_skipped": self.off_domain_skipped,
            "privacy_skipped": self.privacy_skipped,
            "notes": self.notes[:8],
        }


async def crawl_site(
    conn: sqlite3.Connection,
    start_url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    same_domain: bool = True,
    settings: Settings | None = None,
    on_page=None,
    on_progress=None,
    keep_existing: bool = False,
) -> CrawlReport:
    """Breadth-first crawl from ``start_url``, saving every page as a bookmark.

    Politeness is delegated wholesale to the fetch layer's own policy: the
    crawler creates one :class:`FetchPolicy` and one robots cache and lets the
    per-host limiter space every request. A crawl of one site is therefore
    exactly as polite as an index run over the same site's bookmarks.
    """
    st = settings or get_settings()
    report = CrawlReport(start_url=start_url)
    if max_pages < 1:
        raise ValueError("max_pages must be positive")

    start = normalize_url(start_url)
    if not start.indexable:
        report.notes.append("start url is not http(s) and cannot be crawled")
        return report
    base_domain = registrable_domain(start.host)

    policy = policy_from_settings(st)
    limiter = _HostLimiter(policy)
    robots = RobotsCache(
        "facetmark-crawl",
        on_error=policy.robots_on_error,
        fetch_user_agent=policy.user_agent,
    )

    frontier: deque[str] = deque([start_url])
    queued: set[str] = {start.normalized}
    frontier_limit = min(10_000, max_pages * 50)

    async with httpx.AsyncClient(
        timeout=policy.timeout_s,
        follow_redirects=False,
        max_redirects=policy.max_redirects,
        transport=PublicFetchTransport(excluded_domains=policy.excluded_domains,
                                       max_connections=policy.concurrency),
        trust_env=False,
    ) as client:
        while frontier and report.pages_attempted < max_pages:
            # The batch is capped by what is left of the budget as well as by
            # the per-host concurrency: a batch sized only by concurrency can
            # fetch past `--max-pages`, and the budget is the whole point of
            # the flag.
            room = max_pages - report.pages_attempted
            batch = []
            while frontier and len(batch) < min(max(1, policy.per_host_concurrency), policy.concurrency, room):
                batch.append(frontier.popleft())

            tasks = [asyncio.create_task(_fetch_and_save(
                conn, client, url, limiter, robots, policy, report, queued,
                settings=st, on_page=on_page, same_domain=same_domain,
                base_domain=base_domain, keep_existing=keep_existing)) for url in batch]
            try:
                results = await asyncio.gather(*tasks)
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                if on_progress is not None:
                    on_progress(report)
            for _url, ok, links in results:
                if not ok:
                    continue
                for link in links:
                    report.links_found += 1
                    nu = normalize_url(link)
                    if not nu.indexable or nu.normalized in queued:
                        continue
                    if same_domain and registrable_domain(nu.host) != base_domain:
                        report.off_domain_skipped += 1
                        continue
                    if len(queued) >= frontier_limit:
                        report.skipped += 1
                        continue
                    queued.add(nu.normalized)
                    frontier.append(link)

    conn.commit()
    return report


async def _fetch_and_save(
    conn: sqlite3.Connection,
    client: httpx.AsyncClient,
    url: str,
    limiter: _HostLimiter,
    robots: RobotsCache,
    policy: FetchPolicy,
    report: CrawlReport,
    queued: set[str],
    *,
    settings: Settings | None = None,
    on_page=None,
    same_domain: bool = True,
    base_domain: str = "",
    keep_existing: bool = False,
) -> tuple[str, bool, list[str]]:
    """Fetch one page, store it, and return the links to follow.

    Returns ``(url, fetched_ok, links)``. The crawl continues on failure by
    design: one dead page on a site is normal, and stopping the walk because
    page 3 of the docs 404s would strand the other 20.
    """
    st = settings or get_settings()
    report.pages_attempted += 1
    try:
        fetched = await _read_html(client, url, policy, st, report, limiter, robots,
                                   same_domain=same_domain, base_domain=base_domain)
    except Exception as exc:  # noqa: BLE001 - one page, not the crawl
        report.errors += 1
        report.notes.append(f"{url}: {type(exc).__name__}")
        return url, False, []
    if fetched is None:
        return url, False, []

    report.pages_fetched += 1
    final_url, status, html = fetched
    ex = extract(html, url=final_url)
    links = extract_links(html, final_url)
    nu = normalize_url(final_url)
    queued.add(nu.normalized)
    row = conn.execute("SELECT id FROM bookmark WHERE url_hash=?", (nu.hash,)).fetchone()
    if row is not None:
        report.already_known += 1
        bid = int(row[0])
    else:
        rec = save_bookmark(conn, final_url, title=ex.title or "", settings=st)
        bid = rec["bookmark_id"]
        if rec.get("created", True):
            report.inserted += 1
            conn.execute("UPDATE bookmark SET source='crawl' WHERE id=?", (bid,))
        else:
            report.already_known += 1
    saved = conn.execute("SELECT body_text FROM content WHERE bookmark_id=?", (bid,)).fetchone()
    if ex.text and not (keep_existing and saved and saved["body_text"]):
        conn.execute("SAVEPOINT crawl_body")
        try:
            out = store_body(conn, bid, body=ex.text, title=ex.title or "",
                             extractor=ex.extractor, channel="a", http_status=status, final_url=final_url)
        except Exception:
            conn.execute("ROLLBACK TO crawl_body")
            conn.execute("RELEASE crawl_body")
            raise
        conn.execute("RELEASE crawl_body")
        if out.stored:
            report.bodies_stored += 1
    # No SQLite write transaction may remain open while another page waits on
    # the network. Each successful page also survives an interrupted batch.
    conn.commit()
    if on_page is not None:
        on_page(final_url, ex.title or "", bool(ex.text))
    # Even an empty page may contain links to useful reading material.
    return url, True, links


async def _read_html(client, url, policy: FetchPolicy, settings, report, limiter, robots, *, same_domain, base_domain):
    for _ in range(policy.max_redirects + 1):
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            report.skipped += 1
            return None
        if host_excluded(parts.hostname, settings.privacy_excluded_domains):
            report.privacy_skipped += 1
            report.notes.append("A destination is on privacy_excluded_domains")
            return None
        if same_domain and registrable_domain(parts.hostname) != base_domain:
            report.off_domain_skipped += 1
            return None
        if policy.respect_robots:
            allowed, delay = await robots.allows(client, url)
            limiter.note_crawl_delay(parts.hostname, delay)
            if not allowed:
                report.robots_denied += 1
                report.notes.append("robots.txt disallows a requested page")
                return None
        sem = await limiter.acquire(parts.hostname)
        try:
            async with client.stream("GET", url, headers={"User-Agent": policy.user_agent}, follow_redirects=False) as response:
                if response.status_code in {301, 302, 303, 307, 308} and response.headers.get("location"):
                    url = urljoin(str(response.url), response.headers["location"])
                    continue
                if response.status_code >= 400:
                    report.errors += 1
                    report.notes.append(f"{url}: HTTP {response.status_code}")
                    return None
                ctype = response.headers.get("content-type", "")
                if ctype and "html" not in ctype.lower() and "xml" not in ctype.lower():
                    report.skipped += 1
                    return None
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > policy.max_bytes:
                        report.skipped += 1
                        report.notes.append("A page exceeded the fetch size limit")
                        return None
                    body.extend(chunk)
                try:
                    text = body.decode(response.charset_encoding or "utf-8", errors="replace")
                except LookupError:
                    text = body.decode("utf-8", errors="replace")
                return str(response.url), response.status_code, text
        finally:
            sem.release()
    report.errors += 1
    report.notes.append("Too many redirects")
    return None
