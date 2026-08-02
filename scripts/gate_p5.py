"""P5 gate: calibrate the link-health layer against the real library.

Privacy contract, enforced by construction:
  * ``:memory:`` database -- nothing touches disk;
  * every httpx transport used here raises on any outbound request, so a
    network call would crash the script rather than leak a URL;
  * the real bookmark file is read, measured, and discarded.

What this can prove: how many probes a full sweep costs, how long politeness
makes it take, whether the soft-404 patterns fire on real titles, and whether
the privacy gate actually stops the external layer.

What this CANNOT prove: verdict accuracy. Nothing is fetched, so every verdict
distribution stays hypothetical.
"""

from __future__ import annotations

import asyncio
import collections
import statistics
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx  # noqa: E402

from facetmark.config import Settings  # noqa: E402
from facetmark.db import open_db  # noqa: E402
from facetmark.health import gather_external  # noqa: E402
from facetmark.health.store import due_for_check, retry_after_seconds  # noqa: E402
from facetmark.health.verdicts import (  # noqa: E402
    SOFT_404_PATTERNS,
    placeholder_hit,
)
from facetmark.importers import import_bookmarks  # noqa: E402

SRC = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0


def rule(title: str) -> None:
    print(f"\n=== {title} " + "=" * max(0, 62 - len(title)))


def no_network_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"outbound request attempted: {request.url}")

    return httpx.MockTransport(handler)


def main() -> None:
    st = Settings(data_dir=Path("/tmp/facetmark-gate-p5"), use_mock_provider=True,
                  embed_dim=64)
    conn = open_db(":memory:")
    stats = import_bookmarks(conn, SRC, settings=st)
    print(f"imported: parsed={stats.total_parsed} inserted={stats.inserted} "
          f"merged={stats.merged_duplicates} non_indexable={stats.non_indexable}")

    # ---------------------------------------------------------------- queue
    rule("1. probe queue")
    rows = due_for_check(conn, limit=LIMIT or 10_000)
    print(f"due for a first check     : {len(rows)}")
    with_body = sum(1 for r in rows if (r["known_chars"] or 0) > 0)
    print(f"with an indexed body      : {with_body} "
          f"({with_body / max(1, len(rows)):.1%})")
    print("  -> drift and soft-404 detection need a stored body to compare")
    print("     against. On a title-only index the health layer can only")
    print("     answer liveness; the other two verdicts are unreachable.")

    # ------------------------------------------------------------ politeness
    rule("2. politeness cost of one full sweep")
    hosts = collections.Counter(urlsplit(r["url"]).hostname or "" for r in rows)
    print(f"distinct hosts            : {len(hosts)}")
    print(f"single-URL hosts          : {sum(1 for h, n in hosts.items() if n == 1)}")
    busiest = hosts.most_common(5)
    print(f"busiest                   : {busiest}")
    interval = st.fetch_per_host_min_interval
    # Two bounds. Per-host serialisation dominates when one host is deep;
    # global concurrency dominates when the queue is wide and flat.
    per_host_bound = max(n for _, n in hosts.items()) * interval
    # Each probe is 1 request when HEAD succeeds; assume 1.15 to allow for the
    # retry path measured in the unit tests (only non-2xx HEADs retry).
    global_bound = len(rows) * 1.15 * 0.35 / st.fetch_concurrency
    print(f"per-host lower bound      : {per_host_bound:.0f}s "
          f"(busiest host x {interval}s)")
    print(f"global-concurrency bound  : {global_bound:.0f}s "
          f"(concurrency {st.fetch_concurrency}, ~350ms/probe)")
    print(f"=> full sweep is bounded below by ~{max(per_host_bound, global_bound):.0f}s")

    # -------------------------------------------------------------- soft 404
    rule("3. soft-404 pattern false positives on real titles")
    titles = [r["title"] or "" for r in conn.execute(
        "SELECT title FROM bookmark WHERE indexable=1")]
    hit_by_pattern: collections.Counter[str] = collections.Counter()
    hits: list[tuple[str, str]] = []
    for t in titles:
        pat = placeholder_hit(t, "")
        if pat:
            hit_by_pattern[pat] += 1
            hits.append((pat, t))
    print(f"titles scanned            : {len(titles)}")
    print(f"titles matching a pattern : {len(hits)} "
          f"({len(hits) / max(1, len(titles)):.2%})")
    for pat, n in hit_by_pattern.most_common():
        print(f"  {pat!r:<28} {n}")
    for pat, t in hits[:10]:
        print(f"    [{pat}] {t[:70]}")
    print(f"patterns in the list      : {len(SOFT_404_PATTERNS)}")
    print("  -> a title match alone never produces soft_gone: the body must")
    print("     also have collapsed below 30% of its indexed length. These")
    print("     rows are the population that guard protects.")

    # -------------------------------------------------------------- backoff
    rule("4. retry backoff schedule")
    for n in (1, 2, 3, 4, 5, 6, 10):
        print(f"  after {n:>2} consecutive failures -> next check in "
              f"{retry_after_seconds(n) / 86400:.0f} d")

    # --------------------------------------------------------------- privacy
    rule("5. privacy gate against the real top domains")
    top = [h for h, _ in hosts.most_common(12)]
    guarded = Settings(data_dir=st.data_dir, use_mock_provider=True, embed_dim=64,
                       health_enable_external=True,
                       privacy_excluded_domains=tuple(top))
    sample = [r["url"] for r in rows
              if (urlsplit(r["url"]).hostname or "") in set(top)][:200]
    print(f"excluded domains          : {len(top)}")
    print(f"real URLs under them      : {len(sample)}")

    async def probe_all() -> list[bool]:
        # A transport that raises on any request: reaching the network here is
        # a crash, not a warning.
        async with httpx.AsyncClient(transport=no_network_transport()) as cl:
            return [(await gather_external(cl, u, settings=guarded)).checked
                    for u in sample]

    checked = asyncio.run(probe_all())
    print(f"external layer engaged    : {sum(checked)} / {len(checked)}")
    assert not any(checked), "privacy gate leaked"

    off = Settings(data_dir=st.data_dir, use_mock_provider=True, embed_dim=64,
                   health_enable_external=False)
    others = [r["url"] for r in rows
              if (urlsplit(r["url"]).hostname or "") not in set(top)][:200]

    async def probe_off() -> list[bool]:
        async with httpx.AsyncClient(transport=no_network_transport()) as cl:
            return [(await gather_external(cl, u, settings=off)).checked
                    for u in others]

    checked_off = asyncio.run(probe_off())
    print(f"master switch off, engaged: {sum(checked_off)} / {len(checked_off)}")
    assert not any(checked_off), "master switch leaked"
    print("no outbound request was attempted (the transport would have raised)")

    # ------------------------------------------------------------- age model
    rule("6. how much of the library is old enough to be worth checking")
    ages = [r[0] for r in conn.execute(
        "SELECT (strftime('%s','now') - date_added) / 86400.0 FROM bookmark "
        "WHERE indexable=1 AND date_added IS NOT NULL")]
    if ages:
        ages.sort()
        print(f"age days p50/p90/max      : {statistics.median(ages):.0f} / "
              f"{ages[int(0.9 * len(ages))]:.0f} / {max(ages):.0f}")
        for cut in (365, 730, 1095):
            n = sum(1 for a in ages if a >= cut)
            print(f"  older than {cut:>4} days     : {n} ({n / len(ages):.1%})")

    conn.close()
    print("\nP5 gate finished. Nothing was written to disk and nothing left the machine.")


if __name__ == "__main__":
    main()
