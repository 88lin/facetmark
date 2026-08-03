"""Facet 4, part two: the typed relation graph used for 1-hop expansion.

Five kinds, deliberately unequal
--------------------------------
``session``        Saved in the same reconstructed episode. The strongest
                   non-content signal, and the one no other tool has.
``semantic``       Mutual-ish k-NN over content vectors. Requires P3 vectors;
                   skipped silently when the vector tables do not exist yet.
``supersession``   A later bookmark that looks like a replacement for an earlier
                   one. **The only directed kind**: ``src`` is superseded *by*
                   ``dst``, so "what replaced this?" is a single-row lookup, and
                   the metabolism rule can ask "is anything pointing away from
                   me?" without a self-join.
``anchor_sibling`` Different fragments of the same page, or different pages of
                   the same repository/document. Cheap, exact, and surprisingly
                   informative: it reconstructs "the other half of that thing".
``same_domain``    Weakest by a wide margin, and measured to be so: on a real
                   1697-entry library there are 1504 distinct domains and 95% of
                   them appear exactly once. Sharing a domain almost never means
                   sharing a topic. Hub domains are excluded outright -- 78
                   bookmarks on github.com would otherwise generate 3003 edges
                   that all say nothing.

Expansion is capped at one hop everywhere. Two hops through ``same_domain``
would connect essentially unrelated bookmarks through a hub, and two hops
through ``session`` chains days apart.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field

from .db import knn_content, unpack_vector, vec_tables_exist
from .normalize import normalize_url
from .text import segment

#: Default edge weights. Tuned by argument, not by data -- the ablation harness
#: in P7 is where these get earned.
WEIGHTS: dict[str, float] = {
    "session": 1.00,
    "semantic": 0.80,
    "supersession": 0.70,
    "anchor_sibling": 0.50,
    "same_domain": 0.15,
}

#: A session bigger than this is treated as a hub too: pairs grow quadratically
#: and a 60-bookmark "episode" is a research binge, not a coherent sitting.
MAX_SESSION_FANOUT = 30

#: Domains with more members than this are hubs and get no same_domain edges.
MAX_DOMAIN_FANOUT = 25

#: Title-token Jaccard above which two same-domain bookmarks are candidates for
#: supersession. High on purpose: a false supersession demotes a live bookmark.
SUPERSESSION_MIN_JACCARD = 0.80

#: ...and they must be at least this far apart in time to be versions rather
#: than the same page saved twice in one sitting.
SUPERSESSION_MIN_GAP_S = 86_400

#: Neighbours per bookmark for the semantic kind.
SEMANTIC_K = 8

#: Distance ceiling for the semantic kind, L2 between unit vectors.
#:
#: This was 0.60 (~cosine 0.82), a number nobody measured, and on bge-m3 it gave
#: semantic edges to 1.4% of the library -- the graph was effectively session and
#: same-domain edges only. The W1 evaluation replaced it under a rule fixed
#: *before* looking at the result -- the 1st percentile of the random
#: document-pair distance distribution, two decimals -- which on 2,821,500
#: sampled pairs came out at 0.9342, so 0.93. Coverage went 1.4% -> 79.4% and
#: semantic edges 80 -> 7,014 (``post_index.json`` ships the calibration).
#:
#: The number is a property of the embedding model, not of this package: it is
#: where *unrelated* documents start on bge-m3. Swap the model and re-derive it
#: with the same rule rather than keeping this value.
SEMANTIC_MAX_DISTANCE = 0.93


@dataclass(slots=True)
class EdgeStats:
    counts: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def _rows(conn: sqlite3.Connection, kind: str) -> int:
    return int(conn.execute("SELECT count(*) FROM edge WHERE kind = ?", (kind,)).fetchone()[0])


def _insert(conn: sqlite3.Connection, kind: str, pairs: list[tuple[int, int, float]]) -> int:
    """Write ``pairs`` and return how many rows that actually *added*.

    Not ``len(pairs)``. ``ON CONFLICT DO UPDATE`` silently collapses a pair
    offered twice into one row, so the two numbers can differ, and reporting
    the offered count means the stats can claim edges the table does not hold.
    That is not hypothetical: the W1 index log reported 19,763 edges, and the
    published snapshot of that library holds 19,648. A rebuild reproduces
    19,763, so the log was right about the graph and wrong about what it had
    verified -- it had counted its own intentions. Count the table instead.
    """
    if not pairs:
        return 0
    before = _rows(conn, kind)
    conn.executemany(
        "INSERT INTO edge(src, dst, kind, weight) VALUES(?,?,?,?)"
        " ON CONFLICT(src, dst, kind) DO UPDATE SET weight=excluded.weight",
        [(s, d, kind, w) for s, d, w in pairs],
    )
    return _rows(conn, kind) - before


def _both_ways(a: int, b: int, w: float) -> list[tuple[int, int, float]]:
    return [(a, b, w), (b, a, w)]


# ---------------------------------------------------------------------------
# session
# ---------------------------------------------------------------------------
def build_session_edges(conn: sqlite3.Connection, *, weight: float | None = None) -> int:
    w = WEIGHTS["session"] if weight is None else weight
    rows = conn.execute(
        "SELECT session_id, bookmark_id FROM bookmark_session ORDER BY session_id, bookmark_id"
    ).fetchall()
    groups: dict[int, list[int]] = defaultdict(list)
    for r in rows:
        groups[int(r["session_id"])].append(int(r["bookmark_id"]))

    pairs: list[tuple[int, int, float]] = []
    for members in groups.values():
        if len(members) < 2 or len(members) > MAX_SESSION_FANOUT:
            continue
        # Smaller episodes are more meaningful: three links saved together say
        # more about each other than thirty do.
        scale = w * (2.0 / len(members)) ** 0.5
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                pairs += _both_ways(a, b, round(min(w, scale), 4))
    return _insert(conn, "session", pairs)


# ---------------------------------------------------------------------------
# same_domain
# ---------------------------------------------------------------------------
def build_same_domain_edges(conn: sqlite3.Connection, *, weight: float | None = None) -> int:
    w = WEIGHTS["same_domain"] if weight is None else weight
    rows = conn.execute(
        "SELECT id, domain FROM bookmark WHERE domain != '' AND indexable = 1"
    ).fetchall()
    groups: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        groups[r["domain"]].append(int(r["id"]))

    pairs: list[tuple[int, int, float]] = []
    for members in groups.values():
        if not 2 <= len(members) <= MAX_DOMAIN_FANOUT:
            continue
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                pairs += _both_ways(a, b, w)
    return _insert(conn, "same_domain", pairs)


# ---------------------------------------------------------------------------
# anchor_sibling
# ---------------------------------------------------------------------------
def _anchor_key(url: str, host: str) -> str | None:
    """A key shared by bookmarks that are parts of one larger thing."""
    nu = normalize_url(url)
    if not nu.indexable:
        return None
    base = nu.normalized.split("#", 1)[0]
    path = base.split("://", 1)[-1].split("/", 1)
    if len(path) < 2:
        return None
    segs = [s for s in path[1].split("?", 1)[0].split("/") if s]
    # Code-forge and doc hosts: the project, not the file, is the unit.
    if host.endswith(("github.com", "gitlab.com")) and len(segs) >= 2:
        return f"repo:{host}/{segs[0]}/{segs[1]}"
    if nu.kept_fragment:
        return f"page:{base}"
    return None


def build_anchor_sibling_edges(conn: sqlite3.Connection, *, weight: float | None = None) -> int:
    w = WEIGHTS["anchor_sibling"] if weight is None else weight
    rows = conn.execute(
        "SELECT id, url, host FROM bookmark WHERE indexable = 1"
    ).fetchall()
    groups: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        key = _anchor_key(r["url"], r["host"] or "")
        if key:
            groups[key].append(int(r["id"]))

    pairs: list[tuple[int, int, float]] = []
    for members in groups.values():
        if not 2 <= len(members) <= MAX_DOMAIN_FANOUT:
            continue
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                pairs += _both_ways(a, b, w)
    return _insert(conn, "anchor_sibling", pairs)


# ---------------------------------------------------------------------------
# supersession
# ---------------------------------------------------------------------------
def _title_tokens(title: str) -> frozenset[str]:
    return frozenset(t for t in segment(title).split() if len(t) > 1)


def build_supersession_edges(
    conn: sqlite3.Connection,
    *,
    weight: float | None = None,
    min_jaccard: float = SUPERSESSION_MIN_JACCARD,
    min_gap_s: int = SUPERSESSION_MIN_GAP_S,
) -> int:
    """Directed: ``src`` was superseded by ``dst``.

    Restricted to same-domain candidates. Cross-domain "versions" exist (a blog
    post reposted elsewhere) but detecting them from titles alone produces false
    positives, and a false supersession silently demotes a live bookmark in the
    cold layer -- the one failure mode this system must not have.
    """
    w = WEIGHTS["supersession"] if weight is None else weight
    rows = conn.execute(
        "SELECT id, domain, title, date_added FROM bookmark"
        " WHERE indexable = 1 AND date_added IS NOT NULL AND title != ''"
        " ORDER BY domain, date_added"
    ).fetchall()
    groups: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        if r["domain"]:
            groups[r["domain"]].append(r)

    pairs: list[tuple[int, int, float]] = []
    for members in groups.values():
        if not 2 <= len(members) <= MAX_DOMAIN_FANOUT:
            continue
        toks = [_title_tokens(m["title"]) for m in members]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                if not toks[i] or not toks[j]:
                    continue
                gap = abs(int(members[j]["date_added"]) - int(members[i]["date_added"]))
                if gap < min_gap_s:
                    continue
                inter = len(toks[i] & toks[j])
                if not inter:
                    continue
                jac = inter / len(toks[i] | toks[j])
                if jac < min_jaccard:
                    continue
                older, newer = members[i], members[j]  # rows are date-ordered
                pairs.append((int(older["id"]), int(newer["id"]), round(w * jac, 4)))
    return _insert(conn, "supersession", pairs)


# ---------------------------------------------------------------------------
# semantic
# ---------------------------------------------------------------------------
def build_semantic_edges(
    conn: sqlite3.Connection,
    *,
    weight: float | None = None,
    k: int = SEMANTIC_K,
    max_distance: float | None = None,
) -> int:
    """k-NN over content vectors, kept only where both directions agree.

    Mutual k-NN rather than plain k-NN: without it, a bookmark whose vector sits
    in a dense region collects inbound edges from the whole neighbourhood and
    becomes a semantic hub that pollutes every expansion.

    ``max_distance`` defaults to :data:`SEMANTIC_MAX_DISTANCE` *at call time*.
    It used to be a default argument, which bound the constant at import and
    made the module-level knob unturnable -- setting
    ``edges.SEMANTIC_MAX_DISTANCE`` had no effect whatsoever, silently.
    """
    w = WEIGHTS["semantic"] if weight is None else weight
    max_distance = SEMANTIC_MAX_DISTANCE if max_distance is None else max_distance
    if not vec_tables_exist(conn):
        return 0
    rows = conn.execute(
        "SELECT bookmark_id, embedding FROM vec_content ORDER BY bookmark_id"
    ).fetchall()
    if len(rows) < 2:
        return 0

    neighbours: dict[int, dict[int, float]] = {}
    for row in rows:
        bid = int(row["bookmark_id"])
        hits = knn_content(conn, unpack_vector(row["embedding"]), k + 1)
        neighbours[bid] = {
            int(h_id): float(dist)
            for h_id, dist in hits
            if int(h_id) != bid and float(dist) <= max_distance
        }

    pairs: list[tuple[int, int, float]] = []
    for a, nbrs in neighbours.items():
        for b, dist in nbrs.items():
            if a < b and a in neighbours.get(b, {}):
                sim = max(0.0, 1.0 - dist / 2.0)  # L2 on unit vectors -> [0,1]
                pairs += _both_ways(a, b, round(w * sim, 4))
    return _insert(conn, "semantic", pairs)


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
def build_edges(conn: sqlite3.Connection, *, kinds: list[str] | None = None) -> EdgeStats:
    """Rebuild the graph. Cheap enough to redo wholesale after any import."""
    wanted = kinds or list(WEIGHTS)
    stats = EdgeStats()
    builders = {
        "session": build_session_edges,
        "same_domain": build_same_domain_edges,
        "anchor_sibling": build_anchor_sibling_edges,
        "supersession": build_supersession_edges,
        "semantic": build_semantic_edges,
    }
    for kind in wanted:
        conn.execute("DELETE FROM edge WHERE kind = ?", (kind,))
        n = builders[kind](conn)
        stats.counts[kind] = n
        if kind == "semantic" and n == 0 and not vec_tables_exist(conn):
            stats.skipped.append("semantic (no vectors yet -- run `facetmark index`)")
    conn.commit()
    return stats


def neighbours(
    conn: sqlite3.Connection, bookmark_id: int, *, kinds: list[str] | None = None, limit: int = 50
) -> list[tuple[int, str, float]]:
    """One hop out. Returns ``(bookmark_id, kind, weight)`` best first."""
    sql = "SELECT dst, kind, weight FROM edge WHERE src = ?"
    params: list[object] = [bookmark_id]
    if kinds:
        sql += f" AND kind IN ({','.join('?' * len(kinds))})"
        params += kinds
    sql += " ORDER BY weight DESC, dst LIMIT ?"
    params.append(limit)
    return [(int(r[0]), str(r[1]), float(r[2])) for r in conn.execute(sql, params).fetchall()]
