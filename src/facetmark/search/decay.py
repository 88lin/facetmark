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

#: Health verdicts that count as evidence of supersession for condition 3.
DEAD_VERDICTS = ("gone", "drifted", "soft_gone")


def cold_bookmark_ids(
    conn: sqlite3.Connection,
    *,
    age_days: int = 365,
    ids: Sequence[int] | None = None,
    now_ts: int | None = None,
) -> set[int]:
    """Bookmarks meeting all three demotion conditions."""
    now_ts = int(time.time()) if now_ts is None else int(now_ts)
    cutoff = now_ts - age_days * 86400
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
