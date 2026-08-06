"""Offline evaluation bench: A-E ablation over a synthetic library.

Why a synthetic corpus and not the user's own bookmarks: the ablation needs
labelled targets for three *different kinds* of query, and nobody is going to
hand-label 360 of those. The generator builds pages whose rare signature term,
purpose paraphrase and session neighbours are known by construction, so every
query has exactly one correct answer that was decided before any retrieval ran.

The honest caveat is printed with every run: under the mock provider the
embeddings are feature hashes over lexical tokens, so rungs that depend on
semantics (A, C) measure plumbing, not quality. The numbers are still useful as
a regression guard - a change that breaks RRF fusion or the context multiplier
shows up immediately - but they are not a claim about retrieval quality.
"""

from __future__ import annotations

import asyncio
import contextlib
import math
import random
import shutil
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import Settings, get_settings
from ..db import open_db
from ..providers import get_provider
from ..search.pipeline import ALL_CONFIGS, default_config, search
from ..service import index_all
from .corpus import Corpus, EvalQuery, generate_corpus, load_corpus, load_query_file

#: Rungs in the order the report argues them, each adding one mechanism.
RUNGS = ("A", "B", "C", "D", "E")


def resolve_rungs(rungs: Sequence[str] | None, *, ablation: bool) -> list[str]:
    """Which rungs this run evaluates, and in what order.

    The A-E ladder is the pre-registered one; every other rung in
    :data:`~facetmark.search.pipeline.ALL_CONFIGS` is a candidate switch that
    has to be judged on a query set it did not help produce. Naming them
    explicitly is how that judgement gets run, so the names are validated here
    rather than failing with a ``KeyError`` several minutes into a replay.

    Order is the caller's, because ``deltas`` compares adjacent entries: asking
    for ``C,C_notri`` and asking for ``C_notri,C`` are the same comparison with
    the sign flipped, and the caller is the one who knows which direction the
    hypothesis was written in.
    """
    if not rungs:
        return list(RUNGS) if ablation else ["full"]
    keys = [r.strip() for r in rungs if r.strip()]
    if not keys:
        raise ValueError("--rungs was given but named nothing")
    unknown = [k for k in keys if k != "full" and k not in ALL_CONFIGS]
    if unknown:
        raise ValueError(
            f"unknown rung(s) {', '.join(sorted(unknown))}; known: "
            f"full, {', '.join(sorted(ALL_CONFIGS))}"
        )
    if len(set(keys)) != len(keys):
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        raise ValueError(
            f"rung(s) {', '.join(dupes)} named twice: the second run would be "
            "compared against itself and the paired bootstrap would report a "
            "zero-width interval"
        )
    return keys

#: The bar the design doc set for the whole stack over the single-vector
#: baseline, in absolute percentage points of Recall@5.
PASS_MARGIN_PP = 10.0

QUERY_TYPES = ("q_content", "q_vague", "q_episodic", "q_save_action")


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Outcome:
    """One query under one rung: where the correct answer landed."""

    qtype: str
    rank: int  #: 1-based rank of the target, 0 when it never appeared
    #: Wall time of the one search call, milliseconds. Only interpretable as
    #: user-facing latency when the rung ran at concurrency 1; a concurrent
    #: run reports queueing, not response time, which is why the report
    #: records the concurrency next to the percentiles.
    ms: float = 0.0
    #: The target appeared in the one-hop expansion group. Expansion is
    #: rendered under its own heading and is deliberately not interleaved with
    #: ``hits``, so it cannot count towards Recall@k -- but rung D's graph
    #: mechanism can *only* surface a target there, never in the main list.
    #: Without this flag the ladder credits D with nothing for the one thing
    #: graph expansion does, and the D-C reading is silently wrong about which
    #: mechanism it measured.
    expanded: bool = False

    @property
    def found_with_expansion(self) -> int:
        return 1 if (self.hit5 or self.expanded) else 0

    @property
    def hit1(self) -> int:
        return 1 if self.rank == 1 else 0

    @property
    def hit5(self) -> int:
        return 1 if 0 < self.rank <= 5 else 0

    @property
    def hit10(self) -> int:
        return 1 if 0 < self.rank <= 10 else 0

    @property
    def rr(self) -> float:
        return 1.0 / self.rank if 0 < self.rank <= 10 else 0.0


def percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile. No interpolation: with a few hundred samples
    the interpolated value is a fiction the data does not support."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return ordered[idx]


def summarise(outcomes: list[Outcome]) -> dict[str, float]:
    n = len(outcomes)
    if not n:
        return {"n": 0, "recall@1": 0.0, "recall@5": 0.0, "recall@10": 0.0, "mrr@10": 0.0,
                "recall@5+exp": 0.0, "p50_ms": 0.0, "p95_ms": 0.0}
    lat = [o.ms for o in outcomes]
    return {
        "n": n,
        "recall@1": round(sum(o.hit1 for o in outcomes) / n, 4),
        "recall@5": round(sum(o.hit5 for o in outcomes) / n, 4),
        "recall@10": round(sum(o.hit10 for o in outcomes) / n, 4),
        "mrr@10": round(sum(o.rr for o in outcomes) / n, 4),
        "recall@5+exp": round(sum(o.found_with_expansion for o in outcomes) / n, 4),
        "p50_ms": round(percentile(lat, 0.50), 1),
        "p95_ms": round(percentile(lat, 0.95), 1),
    }


def bootstrap_ci(
    a: list[Outcome], b: list[Outcome], *, resamples: int = 1000, seed: int = 11
) -> tuple[float, float]:
    """Percentile CI for the paired Recall@5 difference (b minus a).

    Paired on purpose: both rungs answered the same query list in the same
    order, so resampling query *indices* keeps the pairing and removes the
    between-query variance that dominates a corpus this small.
    """
    n = min(len(a), len(b))
    if n == 0 or resamples <= 0:
        return (0.0, 0.0)
    diffs = [b[i].hit5 - a[i].hit5 for i in range(n)]
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(resamples):
        s = sum(diffs[rng.randrange(n)] for _ in range(n))
        means.append(s / n)
    means.sort()
    lo = means[max(0, int(0.025 * resamples) - 1)]
    hi = means[min(resamples - 1, int(0.975 * resamples))]
    return (round(lo * 100, 2), round(hi * 100, 2))


def mcnemar(a: list[Outcome], b: list[Outcome]) -> dict[str, float]:
    """Exact two-sided McNemar on hit@5 disagreements.

    Exact rather than chi-square because the discordant counts here are small
    (often under 25), which is exactly where the chi-square approximation is
    known to be wrong.
    """
    n = min(len(a), len(b))
    b_only = sum(1 for i in range(n) if b[i].hit5 and not a[i].hit5)
    a_only = sum(1 for i in range(n) if a[i].hit5 and not b[i].hit5)
    disc = a_only + b_only
    if disc == 0:
        return {"gained": 0, "lost": 0, "p": 1.0}
    k = min(a_only, b_only)
    tail = sum(math.comb(disc, i) for i in range(k + 1)) / (2**disc)
    return {"gained": b_only, "lost": a_only, "p": round(min(1.0, 2 * tail), 5)}


# ---------------------------------------------------------------------------
# building a library to measure
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Bench:
    corpus: Corpus
    conn: Any
    settings: Settings
    index: dict = field(default_factory=dict)
    db_path: Path | None = None
    tmp_dir: str = ""

    def close(self, *, keep: bool = False) -> None:
        with contextlib.suppress(Exception):  # pragma: no cover - defensive
            self.conn.close()
        if self.tmp_dir and not keep:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)


async def build_bench(
    *, size: int, db: Path | None, seed: int = 7, settings: Settings | None = None
) -> Bench:
    """Generate, load and fully index a synthetic library."""
    tmp = ""
    if db is None:
        tmp = tempfile.mkdtemp(prefix="facetmark-eval-")
        db = Path(tmp) / "eval.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()

    st = settings or get_settings(use_mock_provider=True, data_dir=str(db.parent))
    conn = open_db(db)
    corpus = generate_corpus(size=size, seed=seed)
    load_corpus(conn, corpus, settings=st)
    prov = get_provider(st)
    rep = await index_all(conn, provider=prov, settings=st, fetch=False)
    await prov.aclose()
    conn.commit()
    return Bench(corpus=corpus, conn=conn, settings=st, index=rep.as_dict(),
                 db_path=db, tmp_dir=tmp)


async def run_rung(
    bench: Bench, config_key: str, queries: list[EvalQuery], *, concurrency: int = 1
) -> tuple[list[Outcome], str]:
    """Answer every query under one rung.

    ``concurrency`` exists because stage E calls the chat model once per query,
    and a few hundred queries against a local CPU endpoint is hours of wall
    time spent waiting on a socket. Results are written back by index, so the
    outcome list is in query order regardless of completion order and the
    pairing the bootstrap depends on survives.
    """
    prov = get_provider(bench.settings)
    # "full" means *what ships here*, which on a mock provider is not what
    # ships on a real one -- see search.pipeline.default_config.
    cfg = default_config(bench.settings, prov) if config_key == "full" else ALL_CONFIGS[config_key]
    outcomes: list[Outcome | None] = [None] * len(queries)
    reranker = ""
    gate = asyncio.Semaphore(max(1, concurrency))

    async def one(i: int, q: EvalQuery) -> None:
        nonlocal reranker
        async with gate:
            t0 = time.perf_counter()
            resp = await search(bench.conn, q.text, limit=10, config=cfg,
                                provider=prov, settings=bench.settings)
            ms = (time.perf_counter() - t0) * 1000.0
        reranker = resp.reranker or reranker
        ids = resp.ids
        rank = ids.index(q.target_id) + 1 if q.target_id in ids else 0
        expanded = any(h.bookmark_id == q.target_id for h in resp.expanded)
        outcomes[i] = Outcome(qtype=q.qtype, rank=rank, ms=ms, expanded=expanded)

    if concurrency <= 1:
        for i, q in enumerate(queries):
            await one(i, q)
    else:
        await asyncio.gather(*(one(i, q) for i, q in enumerate(queries)))
    await prov.aclose()
    done = [o for o in outcomes if o is not None]
    if len(done) != len(queries):
        # Unreachable while ``one`` propagates its exceptions, and that is the
        # point: a silently shorter list would shrink the recall denominator
        # instead of failing, which is the failure mode an eval must not have.
        raise RuntimeError(f"rung {config_key}: {len(queries) - len(done)} queries produced "
                           "no outcome; the report would be computed on a different "
                           "denominator than it claims")
    return done, reranker


# ---------------------------------------------------------------------------
# entry points used by the CLI
# ---------------------------------------------------------------------------


async def run_eval(
    *,
    db: Path | None = None,
    ablation: bool = False,
    size: int = 120,
    build: bool = True,
    bootstrap: int = 1000,
    console=None,
    seed: int = 7,
    queries_path: Path | None = None,
    concurrency: int = 1,
    rungs: Sequence[str] | None = None,
) -> dict:
    """Run the bench and return a JSON-serialisable report."""
    if not build and db is None:
        raise ValueError("--no-build needs --db pointing at an indexed library")
    if not build and queries_path is None:
        raise ValueError(
            "--no-build needs --queries: an existing library carries no relevance "
            "judgements, so the (query, correct answer) pairs have to come from a file"
        )

    keys = resolve_rungs(rungs, ablation=ablation)
    t0 = time.perf_counter()
    bench = (await build_bench(size=size, db=db, seed=seed) if build
             else _attach(db, queries_path))
    queries = bench.corpus.queries
    if not queries:
        raise ValueError("no evaluation queries: nothing to measure")

    report: dict[str, Any] = {
        "provider": "mock" if bench.settings.use_mock_provider else bench.settings.chat_model,
        "embed_model": "mock-hash" if bench.settings.use_mock_provider
        else bench.settings.embed_model,
        "reranker": "",
        "queries_from": str(queries_path) if queries_path else "generated",
        "corpus": bench.corpus.counts,
        "index": bench.index,
        "concurrency": concurrency,
        "rungs_run": list(keys),
        "rungs": [],
        "deltas": [],
        "pass_margin_pp": PASS_MARGIN_PP,
        # The raw judgements behind every aggregate below. A report that only
        # ships means cannot be re-cut by any slice its author did not think
        # of -- and the slice that matters most here (episodic queries split by
        # how the time phrase was written) is exactly such a slice. ``note``
        # carries whatever label the query file attached.
        "queries": [
            {"i": i, "qtype": q.qtype, "target_id": q.target_id, "note": q.note,
             "text": q.text}
            for i, q in enumerate(queries)
        ],
        "outcomes": {},
    }
    if concurrency > 1:
        report["latency_caveat"] = (
            f"queries ran {concurrency}-at-a-time: p50_ms/p95_ms include queueing "
            "against a shared endpoint and are not user-facing latency. Re-run with "
            "concurrency 1 on a subsample for that number."
        )
    if bench.settings.use_mock_provider:
        report["caveat"] = (
            "mock provider: embeddings are feature hashes over lexical tokens, so these "
            "numbers check that the pipeline is wired correctly, not retrieval quality"
        )

    by_rung: dict[str, list[Outcome]] = {}
    try:
        for key in keys:
            outs, reranker = await run_rung(bench, key, queries, concurrency=concurrency)
            by_rung[key] = outs
            report["reranker"] = reranker or report["reranker"]
            row = {
                "config": key,
                "overall": summarise(outs),
                "by_type": {t: summarise([o for o in outs if o.qtype == t])
                            for t in QUERY_TYPES},
            }
            report["rungs"].append(row)
            report["outcomes"][key] = [
                {"rank": o.rank, "expanded": o.expanded, "ms": round(o.ms, 1)}
                for o in outs
            ]
            if console:
                _print_rung(console, row)

        for prev, cur in zip(keys, keys[1:], strict=False):
            a, b = by_rung[prev], by_rung[cur]
            delta = {
                "from": prev,
                "to": cur,
                "recall@5_pp": round(
                    (summarise(b)["recall@5"] - summarise(a)["recall@5"]) * 100, 2),
                "ci95_pp": list(bootstrap_ci(a, b, resamples=bootstrap)),
                "mcnemar": mcnemar(a, b),
            }
            report["deltas"].append(delta)

        if len(keys) > 1:
            first, last = by_rung[keys[0]], by_rung[keys[-1]]
            gain = (summarise(last)["recall@5"] - summarise(first)["recall@5"]) * 100
            end: dict[str, Any] = {
                "from": keys[0],
                "to": keys[-1],
                "recall@5_pp": round(gain, 2),
                "ci95_pp": list(bootstrap_ci(first, last, resamples=bootstrap)),
                "mcnemar": mcnemar(first, last),
            }
            if keys == list(RUNGS):
                end["meets_bar"] = bool(gain >= PASS_MARGIN_PP)
            else:
                # PASS_MARGIN_PP was pre-registered for the whole stack over the
                # single-vector baseline. Printing it next to an arbitrary pair
                # of rungs would let any comparison inherit a bar it was never
                # set against.
                end["bar_not_applicable"] = (
                    f"the {PASS_MARGIN_PP}pp bar was pre-registered for "
                    f"{'->'.join(RUNGS)}, not for {keys[0]}->{keys[-1]}"
                )
            report["end_to_end"] = end
    finally:
        bench.close(keep=db is not None)

    report["seconds"] = round(time.perf_counter() - t0, 2)
    if console:
        _print_tail(console, report)
    return report


async def run_demo(
    *,
    db: Path | None = None,
    size: int = 60,
    keep: bool = False,
    console=None,
    quiet: bool = False,
) -> dict:
    """Build a small synthetic library and run a few searches over it."""
    bench = await build_bench(size=size, db=db, seed=3)
    picks = [bench.corpus.by_type(t)[0] for t in QUERY_TYPES if bench.corpus.by_type(t)]
    prov = get_provider(bench.settings)
    samples = []
    for q in picks:
        resp = await search(bench.conn, q.text, limit=5, provider=prov,
                            settings=bench.settings)
        ids = resp.ids
        samples.append({
            "type": q.qtype,
            "query": q.text,
            "target_rank": ids.index(q.target_id) + 1 if q.target_id in ids else 0,
            "hits": [{"rank": i + 1, "title": h.title, "url": h.url,
                      "score": round(h.score, 4), "via": h.via}
                     for i, h in enumerate(resp.hits[:5])],
            "took_ms": resp.took_ms,
        })
    await prov.aclose()

    payload = {
        "db": str(bench.db_path),
        "kept": bool(keep or db is not None),
        "corpus": bench.corpus.counts,
        "index": bench.index,
        "samples": samples,
        "provider": "mock" if bench.settings.use_mock_provider else bench.settings.chat_model,
    }
    if console and not quiet:
        _print_demo(console, payload)
    bench.close(keep=keep or db is not None)
    return payload


def _attach(db: Path, queries: Path | None, settings: Settings | None = None) -> Bench:
    """Evaluate a library that already exists, with the settings it was built under.

    The old behaviour here forced the mock provider, which made ``--no-build``
    useless for the only thing it is for: measuring a real index built with real
    models. Whatever provider the environment names is the provider that runs,
    and the report says which one it was.
    """
    st = settings or get_settings()
    conn = open_db(db)
    corpus = load_query_file(conn, queries) if queries else Corpus()
    return Bench(corpus=corpus, conn=conn, settings=st, db_path=db)


# ---------------------------------------------------------------------------
# printing
# ---------------------------------------------------------------------------


def _print_rung(console, row: dict) -> None:
    o = row["overall"]
    console.print(
        f"[bold]{row['config']}[/bold]  n={o['n']:<4} "
        f"R@1 {o['recall@1']:.3f}  R@5 {o['recall@5']:.3f}  "
        f"R@5+exp {o['recall@5+exp']:.3f}  "
        f"R@10 {o['recall@10']:.3f}  MRR {o['mrr@10']:.3f}  "
        f"p50 {o.get('p50_ms', 0):.0f}ms  p95 {o.get('p95_ms', 0):.0f}ms"
    )
    for t in QUERY_TYPES:
        s = row["by_type"][t]
        console.print(f"    {t:<12} R@1 {s['recall@1']:.3f}  R@5 {s['recall@5']:.3f}  "
                      f"MRR {s['mrr@10']:.3f}")


def _print_tail(console, report: dict) -> None:
    for d in report["deltas"]:
        m = d["mcnemar"]
        console.print(
            f"[dim]{d['from']} -> {d['to']}[/dim]  R@5 {d['recall@5_pp']:+.2f} pp "
            f"CI95 [{d['ci95_pp'][0]:+.2f}, {d['ci95_pp'][1]:+.2f}]  "
            f"McNemar gained {m['gained']} lost {m['lost']} p={m['p']}"
        )
    e = report.get("end_to_end")
    if e:
        # A custom rung list has no `meets_bar` on purpose: the bar was
        # pre-registered for A-E. Reading it unconditionally is how the first
        # `--rungs` run crashed *after* fifty minutes of replay, with the whole
        # report still in memory and nothing on disk.
        if "meets_bar" in e:
            verdict = "meets" if e["meets_bar"] else "below"
            tail = f" ({verdict} the {report['pass_margin_pp']} pp bar)"
        else:
            tail = f" ({e.get('bar_not_applicable', 'no pre-registered bar')})"
        console.print(f"[bold]{e['from']} -> {e['to']}[/bold] "
                      f"{e['recall@5_pp']:+.2f} pp{tail}")
    console.print(f"[dim]provider={report['provider']} reranker={report['reranker'] or 'none'} "
                  f"{report['seconds']}s[/dim]")
    if report.get("caveat"):
        console.print(f"[yellow]{report['caveat']}[/yellow]")


def _print_demo(console, payload: dict) -> None:
    c = payload["corpus"]
    console.print(f"[bold]demo library[/bold] {c['pages']} pages, "
                  f"{payload['db']}")
    for s in payload["samples"]:
        console.print(f"\n[bold]{s['type']}[/bold]  {s['query']}")
        console.print(f"[dim]target at rank {s['target_rank'] or '-'} "
                      f"in {s['took_ms']} ms[/dim]")
        for h in s["hits"]:
            console.print(f"  {h['rank']}. {h['title']}  [dim]{h['via']} {h['score']}[/dim]")
