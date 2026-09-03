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
from urllib.parse import urldefrag, urljoin

import httpx

from .config import Settings, get_settings
from .fetch.client import DEFAULT_UA, FetchPolicy, RobotsCache, _HostLimiter
from .fetch.extract import extract
from .fetch.store import store_body
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
) -> CrawlReport:
    """Breadth-first crawl from ``start_url``, saving every page as a bookmark.

    Politeness is delegated wholesale to the fetch layer's own policy: the
    crawler creates one :class:`FetchPolicy` and one robots cache and lets the
    per-host limiter space every request. A crawl of one site is therefore
    exactly as polite as an index run over the same site's bookmarks.
    """
    st = settings or get_settings()
    report = CrawlReport(start_url=start_url)

    start = normalize_url(start_url)
    if not start.indexable:
        report.notes.append("start url is not http(s) and cannot be crawled")
        return report
    base_domain = registrable_domain(start.host)

    policy = FetchPolicy(
        concurrency=min(st.fetch_concurrency, 8),
        timeout_s=st.request_timeout,
        user_agent=DEFAULT_UA,
    )
    limiter = _HostLimiter(policy)
    robots = RobotsCache(
        "facetmark-crawl",
        on_error=policy.robots_on_error,
        fetch_user_agent=policy.user_agent,
    )

    frontier: deque[str] = deque([start_url])
    queued: set[str] = {start.normalized}
    known_hashes = {
        row[0] for row in conn.execute("SELECT url_hash FROM bookmark").fetchall()
    }

    async with httpx.AsyncClient(
        timeout=policy.timeout_s,
        follow_redirects=True,
        max_redirects=policy.max_redirects,
    ) as client:
        while frontier and report.pages_fetched < max_pages:
            # The batch is capped by what is left of the budget as well as by
            # the per-host concurrency: a batch sized only by concurrency can
            # fetch past `--max-pages`, and the budget is the whole point of
            # the flag.
            room = max_pages - report.pages_fetched
            batch = []
            while frontier and len(batch) < min(max(1, policy.per_host_concurrency), room):
                batch.append(frontier.popleft())

            results = await asyncio.gather(
                *(_fetch_and_save(conn, client, url, limiter, robots, policy, report,
                                  queued, known_hashes, settings=st, on_page=on_page)
                  for url in batch)
            )
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
    known_hashes: set[str],
    *,
    settings: Settings | None = None,
    on_page=None,
) -> tuple[str, bool, list[str]]:
    """Fetch one page, store it, and return the links to follow.

    Returns ``(url, fetched_ok, links)``. The crawl continues on failure by
    design: one dead page on a site is normal, and stopping the walk because
    page 3 of the docs 404s would strand the other 20.
    """
    st = settings or get_settings()
    host = httpx.URL(url).host or ""
    # The exclusion list is a promise about egress, so it is checked before the
    # first request rather than at save time: `save_bookmark` would mark the row
    # `privacy_skipped`, but by then the crawl has already fetched the page and
    # `store_body` has already written its text into the library. Checked ahead
    # of robots.txt too, because fetching robots.txt is itself a request to the
    # host.
    if host_excluded(host, st.privacy_excluded_domains):
        report.privacy_skipped += 1
        report.notes.append(f"{url}: host is on privacy_excluded_domains")
        return url, False, []

    allowed, delay = await robots.allows(client, url)
    limiter.note_crawl_delay(host, delay)
    if not allowed:
        report.robots_denied += 1
        report.notes.append(f"robots.txt disallows {url}")
        return url, False, []

    sem = await limiter.acquire(host)
    try:
        try:
            resp = await client.get(url, headers={"User-Agent": policy.user_agent})
        except Exception as exc:  # noqa: BLE001 - one page, not the crawl
            report.errors += 1
            report.notes.append(f"{url}: {type(exc).__name__}")
            return url, False, []

        if resp.status_code >= 400:
            report.errors += 1
            report.notes.append(f"{url}: HTTP {resp.status_code}")
            return url, False, []
        ctype = resp.headers.get("content-type", "")
        if ctype and "html" not in ctype.lower() and "xml" not in ctype.lower():
            report.skipped += 1
            return url, False, []
        if len(resp.content) > policy.max_bytes:
            report.skipped += 1
            return url, False, []

        report.pages_fetched += 1
        html = resp.text
        final_url = str(resp.url)
        ex = extract(html, url=final_url)
        links = extract_links(html, final_url)

        nu = normalize_url(final_url)
        # A redirect lands somewhere the frontier has not seen. Record the
        # destination, or every other link to it spends another page of the
        # budget re-fetching this same page.
        queued.add(nu.normalized)
        rec = None
        if nu.hash in known_hashes:
            report.already_known += 1
            row = conn.execute(
                "SELECT id FROM bookmark WHERE url_hash=?", (nu.hash,)
            ).fetchone()
            if row is not None:
                rec = {"bookmark_id": int(row[0])}
        if rec is None:
            rec = save_bookmark(conn, final_url, title=ex.title or "", settings=st)
            known_hashes.add(nu.hash)
            if rec.get("created", True):
                report.inserted += 1
                # Provenance: `api` is the save path's default and a crawl is
                # not that. The one UPDATE a crawl performs, and it is on a row
                # the crawl itself just created.
                conn.execute(
                    "UPDATE bookmark SET source='crawl' WHERE id=?",
                    (rec["bookmark_id"],),
                )
            else:
                report.already_known += 1

        if ex.text:
            out = store_body(
                conn, rec["bookmark_id"], body=ex.text, title=ex.title or "",
                extractor=ex.extractor, channel="a",
                http_status=resp.status_code, final_url=final_url,
            )
            if out.stored:
                report.bodies_stored += 1
        if on_page is not None:
            on_page(final_url, ex.title or "", bool(ex.text))
        # Follow links from every fetched page regardless of storage: a page
        # with no extractable text is still a page with links worth walking.
        return url, True, links
    finally:
        sem.release()
