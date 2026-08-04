#!/usr/bin/env python3
"""Measure the medium the contextual multiplier is tested in.

``docs/gate-w1.md`` §9.2 records a methodology problem the W1 numbers cannot
resolve on their own: the *same* contextual multiplier measures +8.14pp when it
is layered on config A (one facet) and +3.49pp when it is layered on config D
(four facets fused). The stated explanation is that D's fused scores are spread
further apart, so a bounded multiplier capped at ``MAX_BOOST = 1.60`` cannot
move a document as many positions. That explanation has never been measured. It
is the reason W3 exists, and W2's criteria are blocked behind it.

This script measures it, in two parts, neither of which needs a model or a new
query set:

1. **Arithmetic.** RRF scores are a closed-form function of rank and facet
   membership, so the *dynamic range* of each rung -- the ratio between the best
   and worst score a document can hold -- is computable exactly. A multiplier is
   multiplicative, so its reach is naturally measured in log units of that
   range. This is a property of the operator, not of any data.

2. **Measurement on real fused lists.** The two lexical facets need no vectors,
   so the real 479 queries can be replayed through a one-facet medium
   (``seg_only``) and a two-facet medium (``lex_only``) and the displacement a
   1.60x boost actually buys can be counted. Two facets is the *mildest*
   multi-facet case -- D fuses four -- so the gap measured here is a lower bound
   on the gap between A and D.

   The same replay also records what boosts the contextual facet actually
   *emits* on this library, using lexical hits as anchors. If most candidates
   receive 1.0, the cap is not the binding constraint and the medium is only
   half the story.

3. **The media the criterion actually straddled**, once an embedding model is
   available. ``--media A,C_nolex,C`` replays the same queries through the one
   vector facet A really uses, the two vector facets, and the four fused facets
   C and D share. C and D fuse the same facet set, so their fusion arithmetic is
   identical and A-vs-C measures the medium gap A-vs-D was tested across without
   needing D's graph pass. This turns part 2's lower bound into the measurement.

What this does not do: it does not re-run any W1 comparison, does not restate
+8.14pp or +3.49pp, and does not decide whether the contextual multiplier works.
It sizes the instrument. The verdict still belongs to a query set that has not
been generated yet.

    python scripts/boost_medium.py --db library.db --eval eval_loo.json \
        --out eval/boost-medium.json

    python scripts/boost_medium.py --db library.db --eval eval_loo.json \
        --media A,C_nolex,C --boost-anchor C --vec-cache qvec.jsonl \
        --out eval/boost-medium-vectors.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sqlite3
from collections import Counter
from pathlib import Path
from statistics import median

from facetmark.config import Settings
from facetmark.db import connect
from facetmark.providers import get_provider
from facetmark.search.context import MAX_BOOST, build_context
from facetmark.search.lexical import lexical_lists
from facetmark.search.pipeline import (
    CONFIGS,
    DEFAULT_FACET_WEIGHTS,
    EXPLORATORY,
    LEXICAL_FACETS,
    VECTOR_FACETS,
    Config,
)
from facetmark.search.rrf import rrf
from facetmark.search.understand import classify
from facetmark.search.vectors import vector_lists_from_vec

#: The media compared when ``--media`` is not given. Both are lexical, so both
#: run without a model; they stand in for "one facet" and "more than one facet".
MEDIA = ("seg_only", "lex_only")
#: Ranks a boost is asked to lift a document from.
PROBE_RANKS = (3, 5, 10, 20)
#: Every rung a ``--media`` name may refer to. ``EXPLORATORY`` first so that a
#: name defined in both dictionaries resolves the way the ablation ladder reads
#: it; there is currently no such name, and this makes it stay that way.
RUNGS: dict[str, Config] = {**CONFIGS, **EXPLORATORY}


def rung(name: str) -> Config:
    try:
        return RUNGS[name]
    except KeyError:
        known = ", ".join(sorted(RUNGS))
        raise SystemExit(f"unknown medium {name!r}; known rungs: {known}") from None


# ---------------------------------------------------------------------------
# 1. arithmetic
# ---------------------------------------------------------------------------


def dynamic_range(k: int, depth: int, weights: dict[str, float]) -> dict:
    """Best-to-worst score ratio for each rung, and what 1.60x covers of it.

    Best case is a document every facet ranks first: ``W / (k + 1)``. Worst is
    one that a single, least-weighted facet ranks last: ``w_min / (k + depth)``.
    A single-facet rung collapses to ``(k + depth) / (k + 1)`` -- rank is the
    only thing that can vary, so the range is narrow by construction.

    Reach is reported in log units because the multiplier is multiplicative:
    ``log(m) / log(range)`` is the fraction of the rung's span a boost of ``m``
    can cross, and it is the quantity that has to be held constant if the same
    mechanism is to be compared across two rungs.
    """
    rows = []
    for name in ("A", "B", "C", "D"):
        ws = {f: weights.get(f, 1.0) for f in sorted(CONFIGS[name].facets)}
        best = sum(ws.values()) / (k + 1)
        worst = min(ws.values()) / (k + depth)
        rng = best / worst
        reach = math.log(MAX_BOOST) / math.log(rng)
        rows.append({
            "config": name,
            "facets": ws,
            "best_possible_score": round(best, 6),
            "worst_possible_score": round(worst, 6),
            "dynamic_range": round(rng, 3),
            "reach_of_max_boost_in_log_units": round(reach, 4),
            # the multiplier that would give this rung the same reach A gets
            "equivalent_multiplier_to_match_A": None,
        })
    a_reach = rows[0]["reach_of_max_boost_in_log_units"]
    for r in rows:
        r["equivalent_multiplier_to_match_A"] = round(
            r["dynamic_range"] ** a_reach, 3
        )
    return {
        "rrf_k": k,
        "candidates_per_facet": depth,
        "max_boost": MAX_BOOST,
        "note": (
            "reach = log(MAX_BOOST)/log(dynamic_range); "
            "equivalent multiplier = dynamic_range ** reach_A"
        ),
        "per_config": rows,
    }


def single_facet_displacement(k: int, depth: int, m: float) -> dict:
    """Where a boost of ``m`` lands a document in a one-facet rung.

    Exact, because a single facet's score depends on nothing but rank:
    ``m / (k + r) >= 1 / (k + r')`` gives ``r' >= (k + r) / m - k``.
    """
    def lands(r: int) -> int:
        return max(1, math.ceil((k + r) / m - k))

    deepest_to_first = max(
        (r for r in range(1, depth + 1) if lands(r) == 1), default=0
    )
    return {
        "multiplier": m,
        "lands_from": {str(r): lands(r) for r in (*PROBE_RANKS, depth)},
        "deepest_rank_that_reaches_first": deepest_to_first,
    }


# ---------------------------------------------------------------------------
# 2. measurement
# ---------------------------------------------------------------------------


def fused_scores(conn: sqlite3.Connection, text: str, medium: str,
                 settings: Settings,
                 vec: list[float] | None = None) -> list[tuple[int, float]]:
    """Fused (id, score) for one query in one medium.

    ``vec`` is the query's embedding. Rungs made only of lexical facets ignore
    it; rungs that carry a vector facet refuse to run without it rather than
    quietly reporting a narrower medium than the one that was asked for. The
    embedding is passed in, not computed here, because a three-media replay
    would otherwise pay for the same query vector once per medium.
    """
    cfg = rung(medium)
    lists: dict[str, list[int]] = {}
    if cfg.facets & LEXICAL_FACETS:
        lists.update(lexical_lists(conn, text, limit=settings.candidates_per_facet))
    if cfg.facets & VECTOR_FACETS:
        if vec is None:
            raise SystemExit(f"medium {medium!r} needs a query vector; see --vec-cache")
        lists.update(vector_lists_from_vec(
            conn, vec,
            limit=settings.candidates_per_facet,
            want_content="content" in cfg.facets,
            want_intent="intent" in cfg.facets,
        ))
    lists = {f: ids for f, ids in lists.items() if f in cfg.facets}
    return [(f.doc_id, f.score) for f in rrf(lists, k=settings.rrf_k,
                                             weights=cfg.facet_weights)]


def index_clock(db: str) -> int | None:
    """The moment the relative time windows are read against.

    Re-running the published lexical replay a day later moved
    ``share_receiving_no_boost`` from 0.6627 to 0.6628: ``classify`` resolves
    "last week" against ``time.time()``, so an overnight rerun slides the window
    off a handful of bookmarks. Pinning the clock to the index's own
    ``created_at`` makes the census a property of the library instead of a
    property of the day the script ran.
    """
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='created_at'").fetchone()
    finally:
        conn.close()
    return int(row[0]) if row else None


def query_vectors(queries: list[dict], settings: Settings,
                  cache: Path | None) -> dict[str, list[float]]:
    """Embed every distinct query text once, reusing ``cache`` when it exists.

    The cache is keyed by the text itself, not by position, so a query set that
    grows can reuse the vectors of the rows it already had. It is JSONL because
    the file is written once and read once and a 479x1024 float matrix is not
    worth a binary format.
    """
    texts = list(dict.fromkeys(q["text"] for q in queries))
    have: dict[str, list[float]] = {}
    if cache and cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            have[row["text"]] = row["vec"]
        print(f"vector cache: {len(have)} texts from {cache}", flush=True)
    missing = [t for t in texts if t not in have]
    if missing:
        print(f"embedding {len(missing)} query texts ...", flush=True)
        prov = get_provider(settings)

        async def go() -> list[list[float]]:
            try:
                return await prov.embed(missing)
            finally:
                await prov.aclose()

        for text, vec in zip(missing, asyncio.run(go()), strict=True):
            have[text] = list(vec)
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(
                "".join(
                    json.dumps({"text": t, "vec": have[t]}, ensure_ascii=False) + "\n"
                    for t in texts
                ),
                encoding="utf-8",
            )
            print(f"wrote {cache}", flush=True)
    return have


def displacement(scores: list[tuple[int, float]], r: int, m: float) -> int | None:
    """Rank the document at 1-based rank ``r`` reaches when boosted by ``m``.

    Only the probed document is boosted. That is the honest question for a
    contextual signal that fires on some candidates and not others; boosting
    every candidate by the same factor is a no-op on the ordering.
    """
    if len(scores) < r:
        return None
    target = scores[r - 1][1] * m
    ahead = sum(1 for i, (_, s) in enumerate(scores) if i != r - 1 and s > target)
    return ahead + 1


def replay(db: str, queries: list[dict], settings: Settings, *,
           media: tuple[str, ...] = MEDIA, boost_anchor: str = "lex_only",
           vecs: dict[str, list[float]] | None = None,
           now_ts: int | None = None) -> dict:
    vecs = vecs or {}
    if any(rung(m).facets & VECTOR_FACETS for m in (*media, boost_anchor)):
        conn = connect(db, read_only=True)
    else:
        # The published lexical run predates sqlite-vec being loaded here; keep
        # its connection exactly as it was so the numbers stay comparable.
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    per_medium: dict[str, dict] = {}
    boosts: Counter = Counter()
    boost_values: list[float] = []
    try:
        for medium in media:
            landing: dict[int, list[int]] = {r: [] for r in PROBE_RANKS}
            ratios: dict[int, list[float]] = {r: [] for r in PROBE_RANKS}
            reached_top5 = dict.fromkeys(PROBE_RANKS, 0)
            reached_first = dict.fromkeys(PROBE_RANKS, 0)
            probed = dict.fromkeys(PROBE_RANKS, 0)
            ranges: list[float] = []
            ranges10: list[float] = []
            for q in queries:
                scores = fused_scores(conn, q["text"], medium, settings,
                                      vecs.get(q["text"]))
                if len(scores) < 2:
                    continue
                ranges.append(scores[0][1] / scores[-1][1])
                if len(scores) >= 10:
                    ranges10.append(scores[0][1] / scores[9][1])
                for r in PROBE_RANKS:
                    landed = displacement(scores, r, MAX_BOOST)
                    if landed is None:
                        continue
                    probed[r] += 1
                    landing[r].append(landed)
                    # what multiplier would this document have needed to reach #1
                    ratios[r].append(scores[0][1] / scores[r - 1][1])
                    if landed <= 5:
                        reached_top5[r] += 1
                    if landed == 1:
                        reached_first[r] += 1
            per_medium[medium] = {
                "facets": sorted(rung(medium).facets),
                "n_queries_with_a_list": len(ranges),
                "median_observed_dynamic_range": round(median(ranges), 3) if ranges else 0.0,
                "median_observed_range_over_top10": (round(median(ranges10), 3)
                                                     if ranges10 else 0.0),
                "from_rank": {
                    str(r): {
                        "n": probed[r],
                        "median_landing_rank": median(landing[r]) if landing[r] else 0,
                        "share_reaching_rank1": (round(reached_first[r] / probed[r], 4)
                                                 if probed[r] else 0.0),
                        "share_reaching_top5": (round(reached_top5[r] / probed[r], 4)
                                                if probed[r] else 0.0),
                        "median_multiplier_needed_for_rank1": (
                            round(median(ratios[r]), 3) if ratios[r] else 0.0),
                        "p90_multiplier_needed_for_rank1": (
                            round(sorted(ratios[r])[int(0.9 * len(ratios[r]))], 3)
                            if ratios[r] else 0.0),
                        "share_needing_more_than_max_boost": (
                            round(sum(1 for x in ratios[r] if x > MAX_BOOST) / len(ratios[r]), 4)
                            if ratios[r] else 0.0),
                    }
                    for r in PROBE_RANKS
                },
            }

        # 3. what the contextual facet actually emits on this library
        by_type: dict[str, list[float]] = {}
        for q in queries:
            scores = fused_scores(conn, q["text"], boost_anchor, settings,
                                  vecs.get(q["text"]))
            if not scores:
                continue
            u = classify(q["text"], now_ts=now_ts)
            ids = [d for d, _ in scores]
            ctx = build_context(
                conn, anchors=ids, candidates=ids[:200],
                query_window=u.time_window,
                episodic_confidence=u.episodic_confidence,
            )
            for group in ("all", q["qtype"]):
                bucket = by_type.setdefault(group, [])
                for d in ids[:200]:
                    bucket.append(ctx.boost(d))
            for d in ids[:200]:
                b = ctx.boost(d)
                boosts["n"] += 1
                if b <= 1.0:
                    boosts["neutral"] += 1
                else:
                    boost_values.append(b)
                    if b >= MAX_BOOST - 1e-9:
                        boosts["at_cap"] += 1
    finally:
        conn.close()

    n = boosts["n"] or 1
    return {
        "media_compared": list(media),
        "clock": now_ts,
        "media": per_medium,
        "observed_boosts": {
            "candidates_scored": boosts["n"],
            "share_receiving_no_boost": round(boosts["neutral"] / n, 4),
            "share_at_the_cap": round(boosts["at_cap"] / n, 4),
            "median_boost_when_boosted": (round(median(boost_values), 4)
                                          if boost_values else 1.0),
            "max_boost_observed": round(max(boost_values), 4) if boost_values else 1.0,
            "anchors": f"{boost_anchor} fused hits",
            "by_query_type": {
                g: {
                    "candidates": len(v),
                    "share_receiving_no_boost": round(
                        sum(1 for x in v if x <= 1.0) / len(v), 4),
                    "median_boost_when_boosted": (
                        round(median([x for x in v if x > 1.0]), 4)
                        if any(x > 1.0 for x in v) else 1.0),
                }
                for g, v in sorted(by_type.items())
            },
        },
    }


LEXICAL_CAVEAT = (
    "The empirical media are lexical (1 facet vs 2). A is 1 vector facet "
    "and D is 4 fused facets, so the measured gap is a lower bound on the "
    "gap the W1 criterion actually straddled."
)
VECTOR_CAVEAT = (
    "The media include the vector facets, so the A-vs-C gap is the gap the W1 "
    "criterion straddled rather than a lower bound on it. C and D fuse the same "
    "four facets and therefore share this fusion arithmetic; D's extra work is "
    "graph expansion and the contextual multiplier, neither of which changes "
    "what a bounded multiplier can reach. Ranks come from the same 479 queries "
    "W1 used, so nothing here is a verdict on any switch."
)


def run(args) -> None:
    media = tuple(m.strip() for m in args.media.split(",") if m.strip())
    for name in (*media, args.boost_anchor):
        rung(name)
    needs_vectors = any(rung(m).facets & VECTOR_FACETS
                        for m in (*media, args.boost_anchor))
    settings = Settings(db_path=args.db, use_mock_provider=not needs_vectors)
    now_ts: int | None = args.now or index_clock(args.db)
    rep = json.loads(Path(args.eval).read_text(encoding="utf-8"))
    queries = rep["queries"]
    vecs = (query_vectors(queries, settings,
                          Path(args.vec_cache) if args.vec_cache else None)
            if needs_vectors else {})
    print(f"replaying {len(queries)} queries through {len(media)} media ...", flush=True)

    result = {
        "arithmetic": dynamic_range(
            settings.rrf_k, settings.candidates_per_facet, dict(DEFAULT_FACET_WEIGHTS)
        ),
        "single_facet_displacement": [
            single_facet_displacement(settings.rrf_k, settings.candidates_per_facet, m)
            for m in (1.15, 1.30, MAX_BOOST)
        ],
        "replay": replay(args.db, queries, settings, media=media,
                         boost_anchor=args.boost_anchor, vecs=vecs, now_ts=now_ts),
        "caveat": VECTOR_CAVEAT if needs_vectors else LEXICAL_CAVEAT,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result["arithmetic"], ensure_ascii=False, indent=2))
    print(json.dumps(result["single_facet_displacement"], ensure_ascii=False, indent=2))
    print(json.dumps(result["replay"], ensure_ascii=False, indent=2))
    print(f"\nwrote {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--media", default=",".join(MEDIA),
                    help="comma-separated rungs to compare (default: the two "
                         "lexical media, which need no model)")
    ap.add_argument("--boost-anchor", default="lex_only",
                    help="rung whose fused list anchors the contextual-boost census")
    ap.add_argument("--vec-cache", default="",
                    help="JSONL of {text, vec} reused across runs; written if absent")
    ap.add_argument("--now", type=int, default=0,
                    help="epoch seconds the relative time windows are read against "
                         "(default: the index's own created_at, so the census does "
                         "not drift with the wall clock)")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
