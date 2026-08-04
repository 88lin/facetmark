# karakeep round-trip: result

Protocol: [`karakeep-roundtrip-protocol.md`](karakeep-roundtrip-protocol.md), frozen
and pushed before the library was pushed. Nothing below changes it.

**Verdict: `roundtrip_unfaithful`.** Two of three criteria pass. The one that
fails, fails by 0.94 percentage points on a single sub-clause, and the mechanism
behind it is completely explained and completely repairable. Both facts matter
and neither cancels the other.

| | criterion | measured | |
|---|---|---|---|
| a | metric fidelity: \|ΔRecall@5\| ≤ 3.00pp and CI95 inside ±5pp | **−0.81pp**, CI95 **[−2.44, +0.81]** | pass |
| b | list fidelity: median overlap@5 ≥ 4 **and** top-1 agreement ≥ 80% | median **4.0** (pass); top-1 **79.06%** (fail by 0.94pp) | **fail** |
| c | read path: 616 × 2 configs, HTTP vs native, zero disagreements | mismatches **0**, tie reorders **0** | pass |

616 held-out queries, clock pinned at 1785649110, 10,000 bootstrap resamples,
seed 20260803. Raw: `roundtrip.json`, `runs.json`, `roundtrip-diff.json`,
`remedy-bridged.json`, `remedy-source-graph.json`, `remedy-attribution.json`.

## 1. What the numbers are

Identical in config `A` and config `full` — see §4 for why that is not a bug.

| | source | bridged | Δ |
|---|---|---|---|
| Recall@5 | 0.5860 | 0.5779 | −0.81pp |
| Recall@1 | 0.4237 | 0.4075 | −1.62pp |
| overlap@5 mean | | | 3.971 / 5 |
| top-1 same | | | 0.7906 |

McNemar on the 25 discordant queries: 10 won, 15 lost, p = 0.4244. The
difference in *retrieval quality* is not distinguishable from noise. The
difference in *which documents come back* is real: `overlap5_hist` is
`{1: 1, 2: 25, 3: 113, 4: 329, 5: 148}` — only 148 of 616 queries return the
same five documents.

By query type:

| stratum | n | source R@5 | bridged R@5 | Δ |
|---|---|---|---|---|
| `q_content` | 181 | 0.9061 | 0.9061 | 0.00pp |
| `q_episodic` | 224 | 0.2634 | 0.2545 | −0.89pp |
| `q_vague` | 211 | 0.6540 | 0.6398 | −1.42pp |

Content queries are *bit-for-bit unharmed* — 0.00pp, not "small". The loss is
entirely in the two strata that lean on something other than the page's own
words.

## 2. Why criterion b failed — the whole chain

Each link below is measured, not inferred.

**Bodies survive perfectly.** 1,876 pages have a body on both sides.
Byte-identical: **1,876 / 1,876**. Zero differ. The push→pull path does not
corrupt text.

**Vectors do not survive at all.** 2,376 shared bookmarks, byte-identical
vectors: **0**. Cosine between the source vector and the bridged vector:

| | n | min | p05 | median | p95 | max |
|---|---|---|---|---|---|---|
| with body | 1876 | 0.9115 | 0.9642 | **0.9846** | 0.9924 | 0.9967 |
| no body | 500 | 0.8624 | 0.9238 | **0.9690** | 0.9884 | 0.9949 |

0.9846 is a large cosine and a *small* one. It is large enough that the
retrieved sets mostly agree, which is criterion a passing. It is small enough
to reshuffle the top of the list, which is criterion b failing.

**The drift is in one field, and it is not the summary.** Of 2,375 enrichment
rows present on both sides:

| field | identical | |
|---|---|---|
| `summary` | 2375 / 2375 | **100%** |
| `topics` | 0 / 2375 | **0%** |
| `entities` | 28 / 2375 | **1.18%** |

**Which lands on the keyword line.** `content_text()` builds the embedded text
as title → summary → `" · ".join([*topics, *entities][:12])` → truncated body.
The third line is the only one that changed:

| | source | bridged |
|---|---|---|
| pages | 2375 | 2376 |
| distinct terms | **19,016** | **13** |
| mean terms / page | **10.32** | **0.76** |
| pages with no topics | 0 | **847** |
| pages with no entities | 28 | **2,376** |
| most common | AI 94, ChatGPT 66, Anthropic 59, OpenAI 56, Google 53 | 未分类 1124, AI 175, 模型 175, 编程 111, 前端 39 |

A vocabulary of 19,016 terms collapses to 13. The single most common bridged
term is `未分类` — "uncategorised" — on 1,124 pages.

The reason is structural, not a mapping bug. The protocol maps
`tags = folder.split("/")`, and karakeep tags are the browser's *folder* labels.
A folder label describes a shelf; a topic describes a page. One example from
`roundtrip-diff.json`:

```
https://chrome.google.com/webstore/detail/gptanywhere/...
  source  topics ["AI","Text Generation","GPT-3","Chrome Extensions"]
          entities ["GPT-3","Chrome"]
  bridged topics ["AI","模型"]  entities []
```

Two other sampled pages — an English Medium article and a Chinese WeChat
article — carry the *same* `["AI","模型"]`. That is the shelf, not the page.

**So**: identical bodies, identical summaries, folder labels where per-page
topics used to be, a 12-term keyword line reduced to 0.76 terms, vectors that
move by a median cosine of 0.0154, and 20.94% of queries returning a different
first result. Criterion b measures exactly this and correctly says no.

## 3. Attribution, and the repair

**Attribution is total.** Grafting the source library's enrichment rows into the
bridged library and rebuilding the embed text:

| | |
|---|---|
| shared bookmarks | 2376 |
| identical embed text *before* the graft | **0** |
| identical embed text *after* the graft | **2376** |
| residual differences | **0** |

Every byte of drift is the enrichment field. No other column contributes
anything — not the body, not the title, not the URL, not the timestamp.

**The repair is `facetmark index` on the bridged library.** Measured, not
assumed (`remedy-bridged.json`):

| stage | measured |
|---|---|
| fetch | 500 pages would be requested (exactly the ones with no body); **0** karakeep-supplied bodies would be re-fetched |
| enrich | 2,376 would be re-enriched; bridge-written rows picked up **2376 / 2376**, skipped **0** |
| embed, as-is | pending **0** / current **2376** — the trap: the vectors exist and are wrong |
| embed, once enrichment changes | pending **2376** / current 0 |
| graph rebuild | 240 sessions, 1,990 assigned, coverage 0.8375, eps 14400 |

Compared against the source library rebuilt the same way
(`remedy-source-graph.json`): sessions **240 / 1990 / 0.8375 / 14400** — digit
for digit identical. Edges:

| kind | source | bridged | Δ |
|---|---|---|---|
| session | 16930 | 16930 | 0 |
| semantic | 7014 | 6802 | **−212** |
| supersession | 45 | 45 | 0 |
| same_domain | 2708 | 2708 | 0 |
| anchor_sibling | 0 | 0 | 0 |
| **total** | **26697** | **26485** | **−212** |

The entire graph deficit is semantic edges — the ones built from the vectors
that drifted. Everything derived from time, domain, and structure round-trips
exactly.

Note the middle row of that table. Before re-enrichment the embed layer reports
**0 pending, 2,376 current**: a maintenance command run in this state does
nothing and reports success. `content_work()`'s docstring already says "a vector
can exist and be wrong"; this is the first time it has been measured on a real
library.

## 4. Why `A` and `full` produce identical numbers

Both configs returned the same 616 lists on both sides. Two independent reasons,
both structural:

**Graph expansion never enters `hits`.** `pipeline.py` §6 is commented "one hop
out, as its own group": expansions go to `SearchResponse.expanded`, a separate
field. Recall@5 is computed over `hits`. A `graph=True` config therefore cannot
differ from its `graph=False` twin *on this metric* — by construction, not by
measurement.

**Decay could not fire, in either library, for different reasons.**

On the bridged side it is trivial: 0 edges and 0 health rows means the cold set
is empty, so `apply_decay` returns early.

On the source side the cold set is *not* empty — 8 of 2,376 bookmarks meet all
three conditions at the pinned clock, and cold pages do reach the top 5 (15 of
616 queries on the source side, 25 of 616 on the bridged side). Chasing that
turned up a separate defect, which is the honest finding of this section:

> **The rescue valve is above the score ceiling, so the demotion it guards is
> unreachable in the default profile.**

RRF scores are `sum_f w_f / (k + rank_f)`. With `rrf_k = 60`, a single
unit-weight facet tops out at `1 / 61 = 0.016393`. `FULL` is a one-facet config
(`frozenset({"content"})`). `decay_rescue_threshold` ships at `0.02`. So
`hot_top_score < rescue_threshold` is *always* true, `rescued` is always `True`,
and `apply_decay` always returns its input unchanged.

`FULL` is the profile `default_config()` selects whenever a real API key is
configured — i.e. the shipped default. The four-facet `FUSED` profile is not
affected: two facets already clear the threshold (`1.7 / 61 = 0.0279`).

Pinned by `tests/test_decay_reach.py`, five tests, all asserting the *current*
behaviour. Not fixed here: raising the threshold or lowering `rrf_k` changes the
default ranking for every query, and this project does not do that without a
query set and a pre-registered criterion. It is on `ROADMAP.md`.

The previous note in this repository — "only 8 of 2,376 pages reach the cold
line and none entered the top 20" — was wrong in its second clause. Cold pages
do reach the top 5. They are simply never demoted when they do.

## 5. What the protocol said would happen if this failed

§7: on `roundtrip_unfaithful`, the value claim in `docs/karakeep.md` — that the
`config` parameter on `/karakeep/search` lets ablations run against a real
karakeep library — must be withdrawn or qualified, and the failing criterion
must appear in both READMEs. Done in the same commit as this document.

The qualification, precisely: the read path is sound (criterion c, 1,232
comparisons, zero disagreements), and metric-level conclusions transfer
(criterion a). What does not transfer is **list-level** comparison on a library
karakeep enriched, because the enrichment is different data. An ablation whose
outcome depends on which document ranks first is not valid there until the
library has been re-indexed by facetmark's own enrichment.

## 6. Protocol §8, revisited

§8 listed five things the experiment could not measure. Four still stand:
karakeep's own body extraction, multi-user isolation, the intent facet, and
incremental drift over repeated syncs.

§8.1 — "nothing checks the TypeScript plugin against karakeep's real
interfaces" — was overtaken twice, both recorded here rather than by editing the
frozen protocol.

First by commit `a4c4a95`, which added a `tsc --noEmit` check against upstream
type stubs, blob SHAs pinned in
`integrations/karakeep/typecheck/upstream-pins.json`, and a CI job that runs it.

Then by the wire contract in `integrations/karakeep/contract/`, which closes the
half this report named as still open: *whether the JSON the TypeScript plugin
emits parses the way the Python route expects*. It turns out that needs neither
a running karakeep nor two processes at once — each side writes its own bytes to
a committed file and asserts against the file the other side wrote. The capture
drives the real `FacetmarkProvider` with a recording `fetch`;
`tests/test_karakeep_contract.py` replays the captured bodies through the real
app. Six requests, both directions, checked in CI by two jobs that do not share
a runtime.

Two findings from building it, neither of which either language could have
produced alone. TypeScript `Date` values reach Python only as ISO strings, so
the `z.date()` half of the schema describes a type the Python side never sees.
And a search for offset 1 of a single match legitimately returns `hits: []` with
`totalHits: 1` — an empty hit list is a pagination result, not an empty result
set, and code on either side that conflates them is wrong.

Still untested: an actual running karakeep instance. A format contract is not an
integration test, and the four items above are unaffected by it.

## 7. Reproducing

`scripts/karakeep_roundtrip_run.sh` drives the whole thing. It needs a local
embedding model, because the point is a deterministic embedder:

```
FACETMARK_EMBED_BACKEND=local
FACETMARK_EMBED_MODEL=bge-m3
FACETMARK_EMBED_DIM=1024
FACETMARK_LOCAL_EMBED_PATH=/path/to/bge-m3
FACETMARK_LOCAL_EMBED_MAX_SEQ=1024
```

Push throughput on 8 cores was 1.2–1.4 documents/second; 2,376 documents took
1,700 seconds, all 2,376 created, 0 skipped, 0 updated, 0 missing timestamps.

The two probes are reusable on any library:

* `scripts/karakeep_roundtrip_diff.py` — layer-by-layer diff of two libraries,
  down to keyword-line vocabulary.
* `scripts/karakeep_remedy_probe.py` — dry-runs what `facetmark index` would do,
  with `--graph-only` and `--attribute` modes. Every mutation runs inside an
  explicit `BEGIN`/`ROLLBACK` and asserts row counts afterwards, because
  `facetmark.db.connect()` is autocommit and `conn.rollback()` is a no-op there.
