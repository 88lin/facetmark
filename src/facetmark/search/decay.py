"""Metabolism: demote the cold layer, never delete it.

A bookmark library rots in a specific way -- the stuff you saved three years
ago and never opened crowds out the stuff you saved last month and will open
tomorrow. The obvious fix, deleting or archiving, is the wrong one: the whole
premise of this project is that the user cannot judge from a title whether they
will want a page again, so neither can a heuristic built on the same titles.

The rule is therefore conservative to the point of being boring. **All three**
conditions must hold:

1. never opened (``open_count = 0``), and
2. saved more than ``decay_age_days`` ago, and
3. there is positive evidence it has been superseded -- either an outgoing
   ``supersession`` edge, or a health verdict of ``gone`` / ``drifted``.

Condition 3 is what stops this from being an age filter. Age alone demotes
exactly the reference material that ages well: a 2019 paper, a language spec, a
recipe.

The rescue valve
----------------
Demotion is multiplicative and applied after fusion, so it cannot remove
anything -- but it can bury the only good answer if the only good answer
happens to be cold. So: if the best *non-cold* hit scores below
``decay_rescue_threshold``, the hot layer had nothing to offer, the demotion is
lifted, and the page is re-ranked once undecayed. The user sees the cold result
rather than an empty-feeling page.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace

from ..db import in_chunks

#: Health verdicts that count as evidence of supersession for condition 3.
DEAD_VERDICTS = ("gone", "drifted", "soft_gone")


def cold_bookmark_ids(
    conn: sqlite3.Connection,
    *,
    age_days: int = 365,
    ids: Sequence[int] | None = None,
    now_ts: int | None = None,
) -> set[int]:
    """Bookmarks meeting all three demotion conditions.

    ``ids`` restricts the scan to a candidate set, and is chunked: it is the
    fused pool, whose size follows the paging depth rather than a fixed 50, so
    one placeholder per id is no longer a bounded number of them. An empty
    sequence still means "no restriction", as before -- it is ``None`` and
    ``[]`` alike that scan the whole table.
    """
    now_ts = int(time.time()) if now_ts is None else int(now_ts)
    cutoff = now_ts - age_days * 86400
    if ids:
        out: set[int] = set()
        for batch in in_chunks([int(i) for i in ids]):
            out |= _cold_ids(conn, cutoff, batch)
        return out
    return _cold_ids(conn, cutoff, None)


def _cold_ids(
    conn: sqlite3.Connection, cutoff: int, ids: Sequence[int] | None
) -> set[int]:
    where = [
        "b.open_count = 0",
        "b.date_added IS NOT NULL",
        "b.date_added < ?",
    ]
    params: list[object] = [cutoff]
    if ids:
        where.append(f"b.id IN ({','.join('?' * len(ids))})")
        params.extend(int(i) for i in ids)
    marks = ",".join("?" * len(DEAD_VERDICTS))
    params.extend(DEAD_VERDICTS)
    sql = (
        "SELECT b.id FROM bookmark b WHERE "
        + " AND ".join(where)
        + " AND ("
        "  EXISTS (SELECT 1 FROM edge e WHERE e.src = b.id AND e.kind = 'supersession')"
        "  OR EXISTS (SELECT 1 FROM health h WHERE h.bookmark_id = b.id"
        f"             AND h.verdict IN ({marks})"
        "             AND h.checked_at = (SELECT max(checked_at) FROM health h2"
        "                                 WHERE h2.bookmark_id = b.id))"
        ")"
    )
    return {int(r["id"]) for r in conn.execute(sql, params)}


def cold_census(
    conn: sqlite3.Connection,
    *,
    age_days: int = 365,
    now_ts: int | None = None,
    min_body_chars: int = 200,
) -> dict:
    """Which of the three conditions is actually selecting anything, and why.

    The conditions are an ``AND``, so the layer is only as selective as its
    least degenerate term -- and two of the three fail quietly on a library
    that was just imported:

    * **Condition 1 is degenerate on any browser export.** ``open_count = 0``
      is true of *every* bookmark, because the Netscape bookmark HTML format
      carries no usage telemetry. Nothing is wrong; there is simply no data.
      Until facetmark has observed opens itself, condition 1 selects the whole
      library and contributes nothing.
    * **Condition 3's health half needs the health table populated**, and
      ``fm health --check`` is opt-in network I/O. Nobody runs it by accident.
      With zero rows in ``health``, that disjunct can never fire, so condition
      3 collapses to "has an outgoing supersession edge".

    A library where both hold has a cold layer built from supersession edges
    alone. That is a different feature from the three-condition one the
    docstring above describes, and the difference is large: on the 2,376-page
    evaluation library it is 8 pages versus 73. Measuring the decay layer
    without checking this first measures the instrument, not the layer.

    ``servable`` is the count of cold pages whose text is still in the index.
    It matters because demotion is a statement about *the answer*, not about
    the URL: facetmark stores bodies, so a page the server now 404s can still
    be the correct answer to the query, retrievable and readable, with a
    Wayback link attached. Cold pages that are still servable are the ones
    demotion can actually cost the user something.
    """
    now_ts = int(time.time()) if now_ts is None else int(now_ts)
    cutoff = now_ts - age_days * 86400

    def one(sql: str, *p: object) -> int:
        row = conn.execute(sql, p).fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    marks = ",".join("?" * len(DEAD_VERDICTS))
    latest_dead = (
        "EXISTS (SELECT 1 FROM health h WHERE h.bookmark_id = b.id"
        f"        AND h.verdict IN ({marks})"
        "        AND h.checked_at = (SELECT max(checked_at) FROM health h2"
        "                            WHERE h2.bookmark_id = b.id))"
    )
    has_sup = (
        "EXISTS (SELECT 1 FROM edge e WHERE e.src = b.id AND e.kind = 'supersession')"
    )
    both = "b.open_count = 0 AND b.date_added IS NOT NULL AND b.date_added < ?"

    total = one("SELECT count(*) FROM bookmark")
    never_opened = one("SELECT count(*) FROM bookmark WHERE open_count = 0")
    older = one(
        "SELECT count(*) FROM bookmark WHERE date_added IS NOT NULL AND date_added < ?", cutoff
    )
    old_unopened = one(f"SELECT count(*) FROM bookmark b WHERE {both}", cutoff)
    by_sup = one(f"SELECT count(*) FROM bookmark b WHERE {both} AND {has_sup}", cutoff)
    by_dead = one(
        f"SELECT count(*) FROM bookmark b WHERE {both} AND {latest_dead}",
        cutoff,
        *DEAD_VERDICTS,
    )
    cold = cold_bookmark_ids(conn, age_days=age_days, now_ts=now_ts)
    checked = one("SELECT count(DISTINCT bookmark_id) FROM health")
    servable = 0
    if cold:
        ids = ",".join("?" * len(cold))
        servable = one(
            f"SELECT count(*) FROM content WHERE bookmark_id IN ({ids})"
            " AND COALESCE(char_count, 0) >= ?",
            *sorted(cold),
            min_body_chars,
        )

    degenerate: list[str] = []
    if total and never_opened == total:
        degenerate.append("never_opened_selects_everything")
    if checked == 0:
        degenerate.append("health_never_checked")

    return {
        "bookmarks": total,
        "age_days": age_days,
        "cutoff_ts": cutoff,
        # ---- the three conditions, separately
        "never_opened": never_opened,
        "older_than_cutoff": older,
        "old_and_never_opened": old_unopened,
        "condition3_by_supersession": by_sup,
        "condition3_by_dead_verdict": by_dead,
        "cold": len(cold),
        # ---- can the third condition even fire?
        "health_checked": checked,
        "health_unchecked": max(0, total - checked),
        # ---- of the cold pages, how many can we still serve?
        "servable_cold": servable,
        "unservable_cold": len(cold) - servable,
        "degenerate_conditions": degenerate,
    }


@dataclass(slots=True)
class DecayOutcome:
    #: True when the demotion was lifted because the hot layer was empty-handed.
    rescued: bool = False
    demoted: int = 0
    hot_top_score: float = 0.0


def apply_decay(
    scored: Sequence[tuple[int, float]],
    cold: set[int],
    *,
    factor: float = 0.5,
    rescue_threshold: float = 0.02,
) -> tuple[list[tuple[int, float]], DecayOutcome]:
    """Demote cold ids, then rescue if that left nothing worth showing.

    Input and output are ``(bookmark_id, score)`` ordered best first.
    """
    out = DecayOutcome()
    if not cold:
        if scored:
            out.hot_top_score = max(s for _, s in scored)
        return list(scored), out

    hot_scores = [s for i, s in scored if i not in cold]
    out.hot_top_score = max(hot_scores) if hot_scores else 0.0
    if out.hot_top_score < rescue_threshold:
        out.rescued = True
        return list(scored), out

    adjusted: list[tuple[int, float]] = []
    for bid, score in scored:
        if bid in cold:
            adjusted.append((bid, score * factor))
            out.demoted += 1
        else:
            adjusted.append((bid, score))
    adjusted.sort(key=lambda t: (-t[1], t[0]))
    return adjusted, out


def decay_hits(hits, cold: set[int], *, factor: float = 0.5, rescue_threshold: float = 0.02):
    """``apply_decay`` over objects carrying ``.doc_id`` and ``.score``."""
    pairs = [(h.doc_id, h.score) for h in hits]
    adjusted, outcome = apply_decay(
        pairs, cold, factor=factor, rescue_threshold=rescue_threshold
    )
    by_id = {h.doc_id: h for h in hits}
    return [replace(by_id[i], score=s) for i, s in adjusted], outcome
