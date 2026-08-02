"""robots.txt, fetched once per host and honoured by channel A.

A personal bookmark indexer still crawls: a few thousand hosts that never asked
for the traffic. Reading ``/robots.txt`` first is the difference between a tool
and a nuisance, and it costs one request per host for a whole library.

Follows RFC 9309 where it matters:

* the most **specific** rule wins -- longest matching pattern, ``Allow`` breaks
  a tie with an equally long ``Disallow``;
* ``*`` matches any run of characters and ``$`` anchors the end of the path;
* an empty ``Disallow:`` means "allow everything", which is not the same as no
  rule at all;
* the ``User-agent`` group for our own token beats the ``*`` group, and groups
  are matched case-insensitively on a substring of the product token.

One deliberate deviation, exposed as a setting rather than hidden. RFC 9309 says
an *unreachable* robots.txt (5xx, timeout, connection reset) should be read as
"disallow everything", while a *missing* one (404) means "allow everything".
Applied literally, one flaky CDN silently drops a chunk of the user's own
library from their own index, and the user is not a search engine competing for
crawl budget -- they are re-reading pages they already visited in a browser.
So the default for unreachable is ``allow``; ``FACETMARK_ROBOTS_ON_ERROR=deny``
restores the letter of the RFC. A 401/403 on robots.txt itself is treated as
unreachable, not as a refusal of the whole site.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

import httpx

#: The product token robots.txt groups are matched against. RFC 9309 matches on
#: the token, not on the whole ``User-agent`` header, and channel A's header is a
#: browser string with half a dozen incidental tokens in it ("Chrome", "Safari",
#: "Gecko"). Matching that whole string would attach us to any group naming any
#: of them. We answer to one name.
DEFAULT_ROBOTS_TOKEN = "facetmark"

#: robots.txt bodies are small; anything past this is a misconfiguration.
MAX_ROBOTS_BYTES = 512_000
ROBOTS_TIMEOUT_S = 8.0
#: Re-read robots.txt after this long. One sweep of a library never runs long
#: enough to hit it; a long-lived service will.
CACHE_TTL_S = 24 * 3600


def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """``/admin/*.php$`` -> a compiled anchored regex. Everything except ``*``
    and a trailing ``$`` is literal."""
    anchored = pattern.endswith("$")
    if anchored:
        pattern = pattern[:-1]
    parts = [re.escape(p) for p in pattern.split("*")]
    return re.compile("^" + ".*".join(parts) + ("$" if anchored else ""))


@dataclass(slots=True)
class _Rule:
    allow: bool
    pattern: str
    regex: re.Pattern[str]

    @property
    def length(self) -> int:
        return len(self.pattern)


@dataclass(slots=True)
class RobotsFile:
    """Parsed rules for one host, already narrowed to our user agent."""

    rules: list[_Rule] = field(default_factory=list)
    crawl_delay: float | None = None
    fetched_at: float = 0.0
    #: Set when robots.txt could not be read; the caller decides what it means.
    unreachable: bool = False

    def allows(self, path: str) -> bool:
        best: _Rule | None = None
        for rule in self.rules:
            if not rule.regex.match(path):
                continue
            # Longest match wins; Allow wins a tie (RFC 9309 s2.2.2).
            if best is None or rule.length > best.length or (
                rule.length == best.length and rule.allow and not best.allow
            ):
                best = rule
        return True if best is None else best.allow


def _agent_matches(token: str, user_agent: str) -> bool:
    token = token.strip().lower()
    if token == "*":
        return True
    return token in user_agent.lower()


def parse_robots(text: str, user_agent: str) -> RobotsFile:
    """Pick the group that applies to ``user_agent``, preferring a named group
    over ``*``. Records in a group are order-independent; groups are not."""
    named: list[_Rule] = []
    wildcard: list[_Rule] = []
    named_delay: float | None = None
    wildcard_delay: float | None = None
    saw_named = False

    agents: list[str] = []
    collecting_agents = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field_name, _, value = line.partition(":")
        field_name = field_name.strip().lower()
        value = value.strip()

        if field_name == "user-agent":
            if not collecting_agents:
                agents = []
                collecting_agents = True
            agents.append(value)
            continue
        collecting_agents = False
        if not agents:
            continue  # a record outside any group

        exact = [a for a in agents if a.strip() != "*" and _agent_matches(a, user_agent)]
        wild = any(a.strip() == "*" for a in agents)
        if exact:
            saw_named = True
        if not exact and not wild:
            continue

        if field_name in ("allow", "disallow"):
            if field_name == "disallow" and value == "":
                continue  # "Disallow:" with no path allows everything
            if not value:
                continue
            path = value if value.startswith("/") else "/" + value
            rule = _Rule(field_name == "allow", path, _pattern_to_regex(path))
            if exact:
                named.append(rule)
            if wild:
                wildcard.append(rule)
        elif field_name == "crawl-delay":
            try:
                delay = float(value)
            except ValueError:
                continue
            if exact:
                named_delay = delay
            if wild:
                wildcard_delay = delay

    if saw_named:
        return RobotsFile(rules=named, crawl_delay=named_delay, fetched_at=time.time())
    return RobotsFile(rules=wildcard, crawl_delay=wildcard_delay, fetched_at=time.time())


class RobotsCache:
    """One robots.txt per host, fetched at most once, shared across a sweep."""

    def __init__(
        self,
        user_agent: str = DEFAULT_ROBOTS_TOKEN,
        *,
        on_error: str = "allow",
        fetch_user_agent: str | None = None,
    ) -> None:
        #: Matched against ``User-agent:`` groups.
        self.user_agent = user_agent
        #: Sent as the header when reading robots.txt itself, so the request
        #: looks exactly like the page request that follows it.
        self.fetch_user_agent = fetch_user_agent or user_agent
        self.on_error = on_error
        self._files: dict[str, RobotsFile] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def _load(self, client: httpx.AsyncClient, scheme: str, host: str) -> RobotsFile:
        url = f"{scheme}://{host}/robots.txt"
        try:
            resp = await client.get(
                url,
                headers={"User-Agent": self.fetch_user_agent},
                timeout=ROBOTS_TIMEOUT_S,
                follow_redirects=True,
            )
        except Exception:  # noqa: BLE001 - any transport problem is "unreachable"
            return RobotsFile(fetched_at=time.time(), unreachable=True)
        if resp.status_code in (404, 410):
            return RobotsFile(fetched_at=time.time())  # missing means allow all
        if resp.status_code >= 400:
            return RobotsFile(fetched_at=time.time(), unreachable=True)
        if len(resp.content) > MAX_ROBOTS_BYTES:
            return RobotsFile(fetched_at=time.time())
        return parse_robots(resp.text, self.user_agent)

    async def get(self, client: httpx.AsyncClient, url: str) -> RobotsFile:
        parts = urlsplit(url)
        host = parts.netloc
        key = f"{parts.scheme}://{host}"
        cached = self._files.get(key)
        if cached is not None and time.time() - cached.fetched_at < CACHE_TTL_S:
            return cached
        async with self._guard:
            lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self._files.get(key)
            if cached is not None and time.time() - cached.fetched_at < CACHE_TTL_S:
                return cached
            robots = await self._load(client, parts.scheme or "https", host)
            self._files[key] = robots
            return robots

    async def allows(self, client: httpx.AsyncClient, url: str) -> tuple[bool, float | None]:
        """``(allowed, crawl_delay)``. Never raises: a robots failure must not
        take down the sweep."""
        robots = await self.get(client, url)
        if robots.unreachable:
            return self.on_error != "deny", robots.crawl_delay
        parts = urlsplit(url)
        path = unquote(parts.path or "/")
        if parts.query:
            path = f"{path}?{parts.query}"
        return robots.allows(path), robots.crawl_delay
