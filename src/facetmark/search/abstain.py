"""Let a facet decline to vote when it has no opinion.

The W1 ablation found that fusing any weaker facet into a strong content vector
costs 5-6pp of Recall@5, and costs the same amount whichever facet you add
(``docs/gate-w1.md`` §4.1). The arithmetic behind it is short. With flat weights
and ``rrf_k = 60``, a wrong document ranked first by both lexical facets scores

    1/61 + 0.7/61 = 0.0279

while the right document, ranked first by the content facet, scores

    1/61 = 0.0164

and loses. Note where the coincidence sits: at the *top* of the weak facets, not
deep in their lists. Truncating each facet's candidate list therefore does
nothing at all -- the offending entries are at rank 1 and survive any cap. Only
two things can help. Down-weighting the weak facet is one, and
:attr:`Config.weight_overrides` exposes it. The other is letting the facet
abstain, which is this module.

The measurement problem is that facet scores are not comparable. bm25 is an
unbounded log-odds-ish quantity; sqlite-vec reports L2 distance between unit
vectors. Any threshold stated in absolute units would have to be recalibrated
per facet, per corpus, and probably per language.

So confidence is measured *within* a facet, against that facet's own returned
scores, using a statistic that is invariant to affine rescaling:

    confidence = (best - median) / (best - worst)

A facet whose top result towers over a flat mass of near-ties reports ~1.0. A
facet whose top result is one of many indistinguishable near-ties reports ~0.0 --
it has retrieved fifty things it cannot tell apart, which is exactly the state
in which its rank-1 nomination should not outvote a confident facet. A linear
decline sits at 0.5.

Nothing here is switched on by default, and no threshold in this file has been
fitted. The evidence motivating the mechanism came out of the 479 queries in
``eval/queries/w1-real-library.jsonl``; choosing a threshold on those and then
reporting the gain would be fitting to the test set. See ``docs/gate-w1.md``
§9.5.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from statistics import median

#: Facets with fewer than this many results are never silenced. Confidence is a
#: statement about a score *distribution*, and three points is already a
#: generous reading of the word.
MIN_SAMPLE = 3


def confidence(scores: Sequence[float]) -> float:
    """How far a facet's best score stands above its own middle, in [0, 1].

    Scores must be ordered best first and follow the higher-is-better
    convention every facet in this package now uses.
    """
    if len(scores) < MIN_SAMPLE:
        # Too few results to describe a distribution. A facet that returned one
        # match may well be right; silence it and the query it was the only
        # answer to returns nothing.
        return 1.0
    best, worst = scores[0], scores[-1]
    spread = best - worst
    if spread <= 0.0:
        # Every result scored the same. The facet is not ranking, it is
        # enumerating.
        return 0.0
    return (best - median(scores)) / spread


def apply(
    scored: Mapping[str, Sequence[tuple[int, float]]], margin: float
) -> tuple[dict[str, list[int]], dict[str, float]]:
    """Drop facets below ``margin``; return the surviving lists and all scores.

    Abstention never empties the query. If every facet falls below the
    threshold the most confident one is kept anyway -- a weak answer beats no
    answer, and the alternative is a search box that silently returns nothing
    on hard queries, which is the worst failure mode this system has.
    """
    conf = {name: confidence([s for _, s in rows]) for name, rows in scored.items()}
    keep = {n: [i for i, _ in scored[n]] for n, c in conf.items() if c >= margin}
    if not keep and conf:
        best = max(conf, key=lambda n: (conf[n], n))
        keep = {best: [i for i, _ in scored[best]]}
    return keep, conf
