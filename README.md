# facetmark

**Bookmark search that indexes why you saved a page, not just what it says.**

[![CI](https://github.com/88lin/facetmark/actions/workflows/ci.yml/badge.svg)](https://github.com/88lin/facetmark/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1115-brightgreen)](tests/)
[![Code of Conduct](https://img.shields.io/badge/code%20of%20conduct-contributor%20covenant-blueviolet)](CODE_OF_CONDUCT.md)

[English](README.md) · [简体中文](README.zh-CN.md)

Everything runs on your machine against a single SQLite file. Nothing is uploaded, nothing
is deleted, and your browser's own bookmark store is never written to.

---

## Contents

- [The problem](#the-problem)
- [How it works](#how-it-works)
- [Quickstart](#quickstart)
- [Install](#install)
- [Model access](#model-access)
- [Configuration](#configuration)
- [Commands](#commands)
- [Search configurations](#search-configurations)
- [What is actually measured](#what-is-actually-measured)
- [Use it as karakeep's search engine](#use-it-as-karakeeps-search-engine)
- [Data model](#data-model)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Boundaries this project keeps](#boundaries-this-project-keeps)
- [Layout](#layout)
- [Contributing](#contributing)
- [Status](#status)
- [License](#license)

---

## The problem

You saved a page eight months ago. You remember *why* you saved it — "that thing about
Postgres index types someone linked in a thread" — and you remember roughly when. What you
do not remember is its title, and the title is the only thing your browser's bookmark
search looks at.

So facetmark builds four different indexes over each bookmark:

| Facet | What it is | What it answers |
|---|---|---|
| **Lexical** | Two FTS5 indexes: character trigrams and word segments | exact strings, IDs, code, Chinese without spaces |
| **Content** | An embedding of the page's actual extracted text | "that article about consumer group rebalancing" |
| **Intent** | LLM-generated queries you *might* have used, filtered by whether they retrieve the page back | "how do I stop kafka from stalling" |
| **Context** | Save-session clustering, domain and graph structure | "the batch I saved while debugging that outage" |

…fuses them with reciprocal rank fusion, and then — this is the unusual part — **measures
whether each of those four facets was worth adding**, publishes the numbers, and turns off
the ones that lost. Several of them lost. Section [What is actually
measured](#what-is-actually-measured) is the honest list.

## How it works

```
browser export (HTML)  ──┐
karakeep push (HTTP)   ──┼──▶  bookmark  ──▶  fetch  ──▶  content
manual import          ──┘                     │            │
                                               │            ▼
                                               │        enrich  (summary, topics,
                                               │            │    entities, key points)
                                               │            ▼
                                               │        embed_content  ──▶ vec_content
                                               │            │
                                               │            ▼
                                               │        intents ──▶ filter ──▶ vec_intent
                                               │            │
                                               ▼            ▼
                                          sessions  ──▶  edges     (session / semantic /
                                                                     same_domain /
                                                                     supersession)

query ──▶ understand ──▶ [lex_tri, lex_seg, content, intent] ──▶ RRF ──▶ context
      ──▶ decay ──▶ rerank ──▶ hits  +  one-hop graph expansion (separate group)
```

Every stage is idempotent and fingerprinted: `facetmark index` re-runs only what changed.
The fingerprint for enrichment is the body hash; for embeddings it is the reconstructed
embed text, so a vector that exists but was built from stale text is still detected.

## Quickstart

```bash
pip install facetmark            # or: uv pip install facetmark

facetmark init                                  # create ~/.facetmark/facetmark.db
facetmark import bookmarks.html                 # Chrome/Firefox/Edge/Safari export
facetmark index                                 # fetch → enrich → embed → sessions → edges
facetmark search "那个讲 Postgres 索引类型的"     # or use the web UI
facetmark serve                                 # http://127.0.0.1:8787
```

Exporting bookmarks: Chrome/Edge → `chrome://bookmarks` → ⋮ → Export. Firefox → Manage
Bookmarks → Import and Backup → Export to HTML. Safari → File → Export → Bookmarks.

### Try it with no API key and no library

```bash
facetmark demo
```

Builds a small synthetic library with a deterministic mock provider, indexes it, and runs
a handful of queries. No network, no key, no cost. It is the fastest way to see the shape
of the output and to check that your install works.

### The other two ways in

```bash
facetmark import-json bookmarks.json    # Firefox JSON backup, or any {url,title,...} list
```

Or push from karakeep — see [below](#use-it-as-karakeeps-search-engine).

## Install

From PyPI:

```bash
pip install facetmark
```

From source:

```bash
git clone https://github.com/88lin/facetmark
cd facetmark
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q               # 1115 tests, ~36 s
ruff check src tests scripts
```

Requires Python 3.10+. The only heavy optional dependency is `sentence-transformers`,
needed solely for the local embedding backend.

## Model access

facetmark talks to any OpenAI-compatible endpoint. Two things are needed: a **chat model**
(for enrichment and intent generation) and an **embedding model**.

```bash
export FACETMARK_API_KEY=sk-...
export FACETMARK_BASE_URL=https://api.openai.com/v1     # must include /v1
export FACETMARK_CHAT_MODEL=gpt-4o-mini
export FACETMARK_EMBED_MODEL=text-embedding-3-small
export FACETMARK_EMBED_DIM=1536
```

Works unchanged against Azure OpenAI, together.ai, DeepSeek, SiliconFlow, Ollama
(`http://localhost:11434/v1`), vLLM, LM Studio, or an internal gateway.

### Local embeddings

Some gateways proxy chat but not embeddings. Switch the embedding half to a local model
and leave the chat half on the endpoint:

```bash
pip install "facetmark[local]"
export FACETMARK_EMBED_BACKEND=local
export FACETMARK_EMBED_MODEL=bge-m3
export FACETMARK_EMBED_DIM=1024
export FACETMARK_LOCAL_EMBED_PATH=/path/to/bge-m3     # or leave unset to download
export FACETMARK_LOCAL_EMBED_MAX_SEQ=1024
```

`facetmark selfcheck-embed` verifies the backend before you spend an hour indexing: it
embeds a fixed 64-document probe set twice and reports self-cosine and best-mismatch
cosine. On bge-m3 at 1024 tokens the measured minimum self-cosine is **0.999976** and all
64 documents match themselves; at a 512-token budget the minimum drops to 0.9769, which is
why 1024 is the default and why the check exists.

**Changing `FACETMARK_EMBED_DIM` invalidates every stored vector.** facetmark refuses to
mix dimensions rather than silently returning nonsense; re-index with `--force`.

## Configuration

Every setting is an environment variable prefixed `FACETMARK_`, or a key in
`~/.facetmark/config.toml`.

| Variable | Default | What it does |
|---|---|---|
| `DATA_DIR` | `~/.facetmark` | Where the database and caches live |
| `DB_NAME` | `facetmark.db` | Database filename inside `DATA_DIR` |
| `API_KEY` | — | Key for the OpenAI-compatible endpoint |
| `BASE_URL` | `https://api.openai.com/v1` | Endpoint root; **must** include `/v1` |
| `CHAT_MODEL` | `gpt-4o-mini` | Enrichment and intent generation |
| `EMBED_MODEL` | `text-embedding-3-small` | Embeddings |
| `EMBED_DIM` | `1536` | Vector width; changing it invalidates the store |
| `EMBED_BACKEND` | `endpoint` | `endpoint` or `local` |
| `LOCAL_EMBED_PATH` | — | Path to a local sentence-transformers model |
| `LOCAL_EMBED_MAX_SEQ` | `1024` | Token budget per document |
| `LOCAL_EMBED_BATCH` | `8` | Local batch size |
| `REQUEST_TIMEOUT` | `60.0` | Per-request timeout, seconds |
| `FETCH_CONCURRENCY` | `30` | Parallel page fetches |
| `MIN_BODY_CHARS` | `200` | Below this, a page counts as body-less |
| `BODY_TRUNCATE_CHARS` | `6000` | Body kept for enrichment |
| `ENRICH_CONCURRENCY` | `4` | Parallel enrichment calls |
| `INTENT_GENERATE_N` | `8` | Candidate intents per page |
| `INTENT_KEEP_N` | `4` | Intents kept after the retrieve-back filter |
| `RRF_K` | `60` | Reciprocal rank fusion constant |
| `CANDIDATES_PER_FACET` | `50` | Candidate depth per facet |
| `GRAPH_EXPAND_HOPS` | `1` | Expansion radius |
| `GRAPH_EXPAND_FACTOR` | `0.6` | Score carried across an edge |
| `DECAY_FACTOR` | `0.5` | Multiplier applied to cold results |
| `DECAY_AGE_DAYS` | `365` | Age condition for the cold layer |
| `DECAY_RESCUE_THRESHOLD` | `0.02` | Below this the demotion is lifted — see the caveat in [What is actually measured](#what-is-actually-measured) |
| `HOST` / `PORT` | `127.0.0.1` / `8787` | Server bind address |

## Commands

| Command | What it does |
|---|---|
| `facetmark init` | Create the database |
| `facetmark import FILE.html` | Import a browser bookmark export |
| `facetmark import-json FILE.json` | Import Firefox JSON or a generic list |
| `facetmark index` | Run every stage, skipping what has not changed |
| `facetmark fetch` / `enrich` / `embed` / `intents` / `sessions` / `edges` | Run one stage |
| `facetmark search QUERY` | Search from the terminal |
| `facetmark serve` | Web UI + REST API |
| `facetmark health` | Re-check saved URLs, record `gone` / `drifted` verdicts |
| `facetmark stats` | Row counts per table, coverage per stage |
| `facetmark demo` | Synthetic library, mock provider, no network |
| `facetmark selfcheck-embed` | Verify the embedding backend before indexing |
| `facetmark eval` | Run a query set against one or more configurations |
| `facetmark export` | Dump the library back out as JSON |

Add `--force` to any stage to ignore fingerprints and redo the work.

## Search configurations

`facetmark search --config NAME` and the `config` field on the search API both accept
these. They exist because each one was a hypothesis that got measured.

| Name | Facets | Extras | Note |
|---|---|---|---|
| `A` | content | — | **The winner on the W1 query set.** |
| `B` | content, lex_seg, lex_tri | — | Adding lexical facets lost 5.4pp |
| `C` | all four | — | |
| `D` | all four | context, graph | |
| `E` | all four | context, graph, rerank | |
| `full` | content | graph, decay | Shipped default when an API key is set |
| `fused` | all four | context, graph, rerank, decay | Shipped default under the mock provider |

Plus roughly twenty exploratory ablations (`A_ctx`, `A_gatedctx`, `C_notri`, `C_lowlex`,
`C_abstain`, `C_max`, `D_gated`, `lex_only`, `seg_only`, `tri_only`, …) used by the
experiments below. `facetmark eval --list-configs` prints them all.

## What is actually measured

Most of this section is negative results. That is deliberate: the point of publishing
numbers is that they constrain what the project is allowed to claim.

### Fusion lost, and it lost to the simplest rung on the ladder

479 queries over a real 1,700-bookmark library ([`docs/eval-w1.md`](docs/eval-w1.md)):

| Config | Recall@5 | Recall@1 | MRR@10 | p50 latency |
|---|---|---|---|---|
| **A** — content vector only | **0.643** | **0.505** | **0.564** | **148 ms** |
| B — + two lexical facets | 0.589 | | | 189 ms |
| C — all four facets | 0.635 | | | 526 ms |
| D — + context + graph | 0.639 | | | 523 ms |

All three pre-registered criteria failed. Adding facets did not help; it cost 5.4pp and
3.5× latency. By query type, config A: content-style 0.959, vague 0.706, episodic 0.279 —
the episodic number is the one the intent and context facets were supposed to fix.

Two things did survive: graph expansion as a *separate* result group (+2.09pp, 10 wins /
0 losses, p = 0.0019, 9 ms), and the reranker on Recall@1 (+4.80pp, CI95 [+1.46, +8.35],
45 wins / 22 losses, p = 0.0067).

### The context multiplier: one flag, two default reversals

On a fresh 616-query held-out set ([`docs/gate-w2w3.md`](docs/gate-w2w3.md)), gating the
context multiplier on an explicit time expression looked like the one clean win:
`A → A_gatedctx` = **+3.09pp** [1.79, 4.55], 19 wins / 0 losses, p = 3.8e-6. It shipped.

Then a 361-query probe set built specifically to fire the gate
([`docs/gate-precision.md`](docs/gate-precision.md)) measured what happens *when it fires*:

| | Recall@5 | Recall@1 |
|---|---|---|
| A | 0.9058 | 0.801 |
| A_gatedctx | 0.7175 | 0.363 |

**−18.83pp**, CI95 [−23.27, −14.68], 3 wins / 71 losses. Stratified: when the inferred
window does not contain the target (n=304) it costs −22.37pp; when it does (n=57) it buys
exactly **+0.00pp**. The gate never helps and frequently destroys. Verdict
`gate_precision_unqualified`, and the default was reverted to no gating.

A `gate_v2` was drafted and refused: it failed the same probe set at −10.52pp even though
it passed the 616-query set at +1.79pp. Two attempts, one mechanism, one direction of
evidence — the third attempt was declined rather than tuned into passing.

### Five other candidate fixes, all measured

- **Lexical audit** — 80.1% of content-style and 46.3% of vague queries need no vector at
  all. But **6.05%** (29 of 479) are findable *only* lexically, above the pre-registered
  5% line, so the lexical facets stay in the box even though they lose in fusion.
- **Fusion anatomy** ([`docs/w2-fusion-anatomy.md`](docs/w2-fusion-anatomy.md)) — flat-weight
  RRF is why: a coincidence on two weak facets (0.0279) outvotes confidence on one strong
  facet (0.0164). That is arithmetic, not tuning.
- **The trigram facet never worked on Chinese.** Only 25 of 211 Chinese queries (11.85%)
  got any trigram candidate. Fixed → 202 of 211 (95.73%). Overall Recall@5: **unchanged**.
  A facet can be broken and repaired and still not matter.
- **Boost medium** ([`docs/w3-criterion-medium.md`](docs/w3-criterion-medium.md)) — the
  context multiplier's `MAX_BOOST = 1.60` crosses 79.7% of the score range in config A but
  only 20.9% in C/D; equal displacement power would need 6.03. 66.3% of candidates get a
  multiplier of exactly 1.0.
- **The intent facet is a conceptual problem, not a small-model problem**
  ([`docs/w4-intent-strata.md`](docs/w4-intent-strata.md)). Human read of 50 generated
  intents: 19/50 = 38% are queries a person would plausibly type, below the 50% line. And
  the information word is absent from the page entirely 34.0% of the time overall — rising
  to **62.4%** on body-poor pages, which is exactly the population the facet was built for.
  The code is still there; what was rejected is treating it as a co-equal retrieval facet.

### The karakeep round-trip: `roundtrip_unfaithful`

2,376 real bookmarks pushed into a karakeep-shaped store and pulled back, 616 held-out
queries, pre-registered protocol frozen before the data moved
([`docs/karakeep-roundtrip-protocol.md`](docs/karakeep-roundtrip-protocol.md), full result
in [`docs/karakeep-roundtrip.md`](docs/karakeep-roundtrip.md)).

| | criterion | measured | |
|---|---|---|---|
| a | \|ΔRecall@5\| ≤ 3pp, CI95 inside ±5pp | **−0.81pp**, CI95 [−2.44, +0.81] | pass |
| b | median overlap@5 ≥ 4 **and** top-1 agreement ≥ 80% | median 4.0; top-1 **79.06%** | **fail** |
| c | HTTP vs native read path identical, 616 × 2 configs | 0 mismatches | pass |

**Criterion b failed by 0.94pp**, and the cause is fully attributed. Bodies round-trip
byte-identically (1876/1876). Summaries round-trip identically (2375/2375, 100%). But
`topics` match 0% and `entities` 1.18%, because karakeep's tags are the browser's *folder*
labels — a shelf, not a page. The keyword line inside the embedded text collapses from
**19,016 distinct terms to 13**, mean 10.32 → 0.76 per page, most common term `未分类`
("uncategorised") on 1,124 pages. Vectors then move by a median cosine of 0.9846, which is
enough to reshuffle the top of the list without changing aggregate recall.

Grafting the source enrichment back in makes **2376/2376** embed texts byte-identical with
zero residual, so the attribution is total. Running `facetmark index` on the bridged
library repairs it: 0 karakeep-supplied bodies are re-fetched, 2376/2376 bridge-written
rows are picked up by re-enrichment, and the rebuilt graph matches the source library
exactly except for 212 semantic edges (26,485 vs 26,697), which are precisely the edges
built from the drifted vectors.

**Consequence for anyone reading this repo's numbers:** metric-level conclusions transfer
to a karakeep-enriched library; rank-level ones do not, until that library has been
re-indexed with facetmark's own enrichment.

### The decay layer cannot fire in the default profile

Found while explaining the round-trip result. RRF scores are `sum_f w_f / (k + rank_f)`;
with `rrf_k = 60` a single unit-weight facet tops out at `1/61 = 0.016393`.
`decay_rescue_threshold` ships at `0.02`. The default profile `full` is a **one-facet**
config, so `hot_top_score < rescue_threshold` is always true, the rescue valve always
opens, and the demotion it guards has never executed. `fused` is unaffected (two facets
already reach 0.0279).

Pinned by `tests/test_decay_reach.py`. **Deliberately not "fixed" here**: moving the
threshold or `rrf_k` changes the default ranking for every query, and this project does
not do that without a query set and a pre-registered criterion. It is on
[`ROADMAP.md`](ROADMAP.md).

### One real export, end to end

`favorites_2026_8_4.html`, 1.7 MB, 96 folders, 4 levels deep: parsed 1,710 → inserted
1,701, 9 duplicates merged, 1 non-indexable. Indexed with no page fetching: 322 sessions,
9,132 edges, 1,386 domains, 1,775 vectors. Median query latency 2,265 ms on that box.
Details in [`docs/real-library-demo.md`](docs/real-library-demo.md).

## Use it as karakeep's search engine

[karakeep](https://github.com/karakeep-app/karakeep) is a self-hosted bookmark manager
with a search-provider plugin interface. facetmark implements it, so karakeep keeps
owning storage, sync, and UI, and facetmark only answers queries.

```bash
cp -r integrations/karakeep/search-facetmark \
      /path/to/karakeep/packages/plugins/search-facetmark
# add "./search-facetmark": "./search-facetmark/index.ts" to the exports map in
#   packages/plugins/package.json
# add await import("@karakeep/plugins/search-facetmark"); to loadAllPlugins() in
#   packages/shared-server/src/plugins.ts — AFTER the meilisearch line, because
#   PluginManager hands out the last provider registered
export FACETMARK_URL=http://127.0.0.1:8787
export FACETMARK_TOKEN=...
```

Then run `facetmark serve` and karakeep's search box is facetmark.

The plugin is type-checked against karakeep's real interfaces on every push: upstream's
`packages/shared/search.ts` and `packages/shared/plugins.ts` are pinned by blob SHA in
`integrations/karakeep/typecheck/upstream-pins.json`, and CI runs `tsc --noEmit` against
them.

The bytes are pinned too. `integrations/karakeep/contract/` drives the real plugin the way
karakeep drives it, with a recording `fetch`, and commits the request bodies to `wire.json`;
`tests/test_karakeep_contract.py` replays those exact bodies through the real FastAPI app and
commits the replies for the capture to parse back. Each language asserts against a file the
other one produced, so a field the plugin starts sending that the Python model would silently
drop is a failing test rather than a bug report. It caught one thing worth repeating: a search
for offset 1 of a single match answers `hits: []` with `totalHits: 1`, so **an empty `hits` is
not the same as no results**. What is still untested is an actual running karakeep instance —
a format contract is not an integration test.

Read [`docs/karakeep.md`](docs/karakeep.md) before relying on this — it documents the
field mapping, what does not round-trip, and the enrichment ownership rule (the bridge
*claims* an enrichment row, it never overwrites one written by a real model).

## Data model

One SQLite file. The tables you are likely to query directly:

| Table | Holds |
|---|---|
| `bookmark` | url, title, folder, date_added, open_count, source |
| `content` | body_text, body_hash, char_count, lang, extractor, http_status |
| `enrichment` | summary, topics, entities, key_points, model, source_hash |
| `intent` | generated queries, kept flag, rank of the retrieve-back check |
| `vec_content` / `vec_intent` | embeddings, keyed by bookmark |
| `fts_tri` / `fts_seg` | FTS5 indexes over title, body, summary, extra |
| `session` / `bookmark_session` | save-burst clusters and their members |
| `edge` | `(src, dst, kind, weight)`; kinds: session, semantic, same_domain, supersession |
| `health` | per-URL verdicts over time: ok, gone, drifted, soft_gone |
| `karakeep_doc` | created on demand; drop it to fully uninstall the bridge |

`enrichment.source_hash` is the fingerprint that decides whether a page needs re-enriching.
The value `'karakeep'` is reserved and means "this row belongs to the bridge, overwrite it
freely"; anything else means a real model wrote it and the bridge must leave it alone.

## Troubleshooting

**`Dimension mismatch: expected 1024, received 1536`** — the stored vectors and
`FACETMARK_EMBED_DIM` disagree. Either restore the old dim, or re-embed with `--force`.

**`base_url` errors / 404 on every call** — the URL must end in `/v1`. Gateways that
present `https://host/` without it will 404 on `/chat/completions`.

**Enrichment silently does nothing** — `enrich.targets()` skips a row when
`source_hash` already equals the body hash. Use `facetmark enrich --force`.

**A page has a vector but bad results** — that is the failure mode described above.
`facetmark embed --force` rebuilds from the current text.

**`disk I/O error` opening the database** — SQLite cannot run on some network or FUSE
filesystems. Copy the file to local disk first.

**Fetching gets blocked** — facetmark honours `robots.txt` and per-domain rate limits by
design. Lower `FETCH_CONCURRENCY` or accept that some pages stay body-less; the pipeline
handles body-less pages by falling back to a title-only fingerprint.

## FAQ

**Does it upload my bookmarks?** No. The only network traffic is page fetching and the
model endpoint you configure. With `EMBED_BACKEND=local` and no `API_KEY`, there is none
at all beyond fetching.

**Does it modify my browser bookmarks?** Never. Import is one-way and read-only.

**Can I use it without any LLM?** Yes, degraded: the lexical facets and session/domain
graph work with no model at all. You lose the content and intent facets.

**How much does indexing cost?** Dominated by enrichment: roughly one small chat call per
page. On 1,700 pages with `gpt-4o-mini` that is cents, not dollars. Embeddings are cheaper
still, and free if local.

**Why is it slow on my library?** Fetching, almost always. `facetmark index` without
fetched bodies takes minutes; with fetching it is bounded by politeness, not CPU.

**Why does the default config only use one facet?** Because the four-facet fusion measured
*worse* than the single content facet on 479 real queries, and the project ships what the
numbers say rather than what the architecture diagram says.

## Boundaries this project keeps

- **Read-only on your browser.** Import never writes back.
- **Nothing is deleted.** The cold layer demotes; it does not archive or remove.
- **Local first.** One SQLite file, portable, inspectable with `sqlite3`.
- **Politeness by default.** `robots.txt`, per-domain rate limits, a real user agent.
- **No number without a protocol.** Every result in this README has a pre-registered
  criterion written before the measurement, and failures are published with the same
  prominence as successes.
- **No default change without a query set.** Including the two known defects listed above.

## Layout

```
src/facetmark/
  cli.py  api.py  service.py  config.py  db.py  text.py
  import_/     browser HTML and JSON parsers, URL normalisation
  fetch/       polite fetching, robots, extraction, storage
  enrich/      summary/topics/entities, intents, embed-text construction
  graph/       sessions, edges, supersession
  search/      lexical, vectors, rrf, context, graph expansion, decay, rerank, pipeline
  bridges/     karakeep push/pull bridge
  web/         single-page UI served by `facetmark serve`
integrations/karakeep/    TypeScript plugin, upstream type pins, cross-language wire contract
extension/                browser extension (open-count telemetry)
eval/                     query sets and evaluation harness
scripts/                  experiment drivers and probes
docs/                     one file per experiment, protocol first
tests/                    1115 tests
```

## Contributing

Issues and pull requests are welcome. Three things worth knowing first:

1. **Retrieval-quality changes need a protocol.** If a change moves default ranking, open
   a `retrieval-proposal` issue with the hypothesis, the query set, and the criterion
   *before* the measurement. Templates are in `.github/ISSUE_TEMPLATE/`.
2. **Run `pytest -q` and `ruff check src tests scripts`.** Do not run `ruff format`; the
   codebase is hand-formatted.
3. **Negative results are contributions.** A measured "this does not help" is worth more
   here than an unmeasured improvement.

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and
[SECURITY.md](SECURITY.md). To cite this work, see [CITATION.cff](CITATION.cff).

## Status

Usable and honest about what it does not do. The retrieval core, the CLI, the server, the
web UI, the karakeep bridge, and the evaluation harness all work; the numbers above are
reproducible from `scripts/` and `eval/`.

Known open items, all documented rather than hidden: the decay layer cannot fire in the
default profile; the intent facet is off by default and the reason is conceptual; the
karakeep bridge has no test against a live karakeep instance; and the largest missing
piece is a query set built by someone other than the author. See [ROADMAP.md](ROADMAP.md)
and [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).
