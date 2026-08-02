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

import contextlib
import math
import random
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import Settings, get_settings
from ..db import open_db
from ..providers import get_provider
from ..search.pipeline import CONFIGS, FULL, search
from ..service import index_all
from .corpus import Corpus, EvalQuery, generate_corpus, load_corpus

#: Rungs in the order the report argues them, each adding one mechanism.
RUNGS = ("A", "B", "C", "D", "E")

#: The bar the design doc set for the whole stack over the single-vector
#: baseline, in absolute percentage points of Recall@5.
PASS_MARGIN_PP = 10.0

QUERY_TYPES = ("q_content", "q_vague", "q_episodic")


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Outcome:
    """One query under one rung: where the correct answer landed."""

    qtype: str
    rank: int  #: 1-based rank of the target, 0 when it never appeared

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


def summarise(outcomes: list[Outcome]) -> dict[str, float]:
    n = len(outcomes)
    if not n:
        return {"n": 0, "recall@1": 0.0, "recall@5": 0.0, "recall@10": 0.0, "mrr@10": 0.0}
    return {
        "n": n,
        "recall@1": round(sum(o.hit1 for o in outcomes) / n, 4),
        "recall@5": round(sum(o.hit5 for o in outcomes) / n, 4),
        "recall@10": round(sum(o.hit10 for o in outcomes) / n, 4),
        "mrr@10": round(sum(o.rr for o in outcomes) / n, 4),
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
    bench: Bench, config_key: str, queries: list[EvalQuery]
) -> tuple[list[Outcome], str]:
    cfg = FULL if config_key == "full" else CONFIGS[config_key]
    prov = get_provider(bench.settings)
    outcomes: list[Outcome] = []
    reranker = ""
    for q in queries:
        resp = await search(bench.conn, q.text, limit=10, config=cfg,
                            provider=prov, settings=bench.settings)
        reranker = resp.reranker or reranker
        ids = resp.ids
        rank = ids.index(q.target_id) + 1 if q.target_id in ids else 0
        outcomes.append(Outcome(qtype=q.qtype, rank=rank))
    await prov.aclose()
    return outcomes, reranker


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
) -> dict:
    """Run the bench and return a JSON-serialisable report."""
    if not build and db is None:
        raise ValueError("--no-build needs --db pointing at an indexed library")

    t0 = time.perf_counter()
    bench = await build_bench(size=size, db=db, seed=seed) if build else _attach(db)
    keys = list(RUNGS) if ablation else ["full"]
    queries = bench.corpus.queries

    report: dict[str, Any] = {
        "provider": "mock" if bench.settings.use_mock_provider else bench.settings.chat_model,
        "embed_model": "mock-hash" if bench.settings.use_mock_provider
        else bench.settings.embed_model,
        "reranker": "",
        "corpus": bench.corpus.counts,
        "index": bench.index,
        "rungs": [],
        "deltas": [],
        "pass_margin_pp": PASS_MARGIN_PP,
    }
    if bench.settings.use_mock_provider:
        report["caveat"] = (
            "mock provider: embeddings are feature hashes over lexical tokens, so these "
            "numbers check that the pipeline is wired correctly, not retrieval quality"
        )

    by_rung: dict[str, list[Outcome]] = {}
    try:
        for key in keys:
            outs, reranker = await run_rung(bench, key, queries)
            by_rung[key] = outs
            report["reranker"] = reranker or report["reranker"]
            row = {
                "config": key,
                "overall": summarise(outs),
                "by_type": {t: summarise([o for o in outs if o.qtype == t])
                            for t in QUERY_TYPES},
            }
            report["rungs"].append(row)
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
            report["end_to_end"] = {
                "from": keys[0],
                "to": keys[-1],
                "recall@5_pp": round(gain, 2),
                "ci95_pp": list(bootstrap_ci(first, last, resamples=bootstrap)),
                "mcnemar": mcnemar(first, last),
                "meets_bar": bool(gain >= PASS_MARGIN_PP),
            }
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


def _attach(db: Path | None) -> Bench:  # pragma: no cover - exercised by CLI only
    st = get_settings(use_mock_provider=True)
    conn = open_db(db)
    corpus = Corpus()
    return Bench(corpus=corpus, conn=conn, settings=st, db_path=db)


# ---------------------------------------------------------------------------
# printing
# ---------------------------------------------------------------------------


def _print_rung(console, row: dict) -> None:
    o = row["overall"]
    console.print(
        f"[bold]{row['config']}[/bold]  n={o['n']:<4} "
        f"R@1 {o['recall@1']:.3f}  R@5 {o['recall@5']:.3f}  "
        f"R@10 {o['recall@10']:.3f}  MRR {o['mrr@10']:.3f}"
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
        verdict = "meets" if e["meets_bar"] else "below"
        console.print(f"[bold]{e['from']} -> {e['to']}[/bold] {e['recall@5_pp']:+.2f} pp "
                      f"({verdict} the {report['pass_margin_pp']} pp bar)")
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
