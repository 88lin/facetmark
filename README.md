# facetmark

**Bookmark search that indexes why you saved a page, not just what it says.**

[![CI](https://github.com/88lin/facetmark/actions/workflows/ci.yml/badge.svg)](https://github.com/88lin/facetmark/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1081-brightgreen)](tests/)

[English](README.md) · [简体中文](README.zh-CN.md)

Everything runs on your machine against a single SQLite file. Nothing is uploaded, nothing
is deleted, and your browser's own bookmark store is never written to.

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
| **Episodic** | Saving sessions reconstructed from timestamp gaps, plus a folder/domain graph | "the batch I saved while researching X" |

Candidates are fused with reciprocal rank fusion, expanded one hop through the graph, and
decayed by age.

Then the project measured whether fusing all four is better than using one, and it is not —
see [What is actually measured](#what-is-actually-measured). The shipped default searches
the **content** facet with graph expansion and time decay; the other three are still built,
still stored, and reachable with `--config`. A deployment with no API key falls back to the
full fusion instead, because without real embeddings the content facet is the one that
returns noise.

## Quickstart

```bash
uv pip install facetmark        # or: pip install facetmark

facetmark import                # reads the live browser profile, or pass a path
facetmark index                 # crawl, enrich, embed, sessions, graph
facetmark search "网盘直链解析"
```

Export first if you prefer a file: Chrome/Edge → Bookmark manager → Export, or Firefox →
Manage bookmarks → Export to HTML. Netscape HTML and Chrome's `Bookmarks` JSON both work.

Real output from a 1,701-bookmark library ([full run](docs/real-library-demo.md)):

```
$ facetmark import favorites.html --json
{"parsed": 1710, "inserted": 1701, "merged_duplicates": 9, "non_indexable": 1,
 "folders": 96, "max_depth": 4, "timestamp_unit": "unix_s", "warnings": []}

$ facetmark search "chrome 插件下载" -n 3
1. Chrome插件下载器          收藏夹栏/工具/插件搜索工具
2. 插件小屋 Chrome插件        收藏夹栏/工具/插件搜索工具
3. Chrome 离线安装包          收藏夹栏/工具
```

### Try it with no API key and no library

```bash
facetmark demo                   # synthetic library, indexed and searched, fully offline
facetmark eval --ablation        # A-E ablation with bootstrap CIs and McNemar tests
facetmark eval --rungs C,C_notri # or any two rungs, judged head to head
```

Both use a mock provider whose "embeddings" are feature hashes over lexical tokens. They
prove the pipeline is wired correctly. They are **not** a quality measurement, and every
command that uses them says so in its output.

## Install from source

```bash
git clone https://github.com/88lin/facetmark
cd facetmark
uv venv && uv pip install -e ".[dev]"
pytest -q                       # 1081 tests, no network needed
ruff check src tests scripts
```

Python 3.10+. The only unusual dependency is [`sqlite-vec`](https://github.com/asg017/sqlite-vec),
which provides vector KNN inside SQLite — there is no separate vector database to run.

## Model access

facetmark needs an embedding model and, for the intent facet, a chat model. Any
OpenAI-compatible endpoint works.

```bash
export FACETMARK_API_KEY=sk-...
export FACETMARK_BASE_URL=https://api.openai.com/v1      # must include /v1
export FACETMARK_CHAT_MODEL=gpt-4o-mini
export FACETMARK_EMBED_MODEL=text-embedding-3-small
export FACETMARK_EMBED_DIM=1536
```

**Local embeddings**, if your endpoint has no embedding route or you would rather not send
page text anywhere:

```bash
export FACETMARK_EMBED_BACKEND=local
export FACETMARK_LOCAL_EMBED_PATH=/path/to/bge-m3
export FACETMARK_EMBED_MODEL=bge-m3
export FACETMARK_EMBED_DIM=1024
```

`FACETMARK_CHAT_MODEL_FALLBACKS` takes a comma-separated list tried in order when the
primary model returns an error — useful with free or rate-limited gateways.

The embedding dimension and model name are written into the database on first index. They
cannot be changed later without a rebuild, and facetmark refuses to mix them rather than
silently returning garbage neighbours.

### Configuration

All settings are `FACETMARK_`-prefixed environment variables or a `.env` file. The ones
worth knowing:

| Variable | Default | Notes |
|---|---|---|
| `FACETMARK_DATA_DIR` | platform data dir | Everything lives here: DB, token, logs |
| `FACETMARK_DB_NAME` | `facetmark.db` | One library per file |
| `FACETMARK_FETCH_CONCURRENCY` | `30` | Global crawl concurrency |
| `FACETMARK_FETCH_PER_HOST_CONCURRENCY` | `2` | Per-host cap, plus a 0.5 s minimum interval |
| `FACETMARK_RESPECT_ROBOTS` | `true` | See "Crawling other people's servers" below |
| `FACETMARK_INTENT_GENERATE_N` / `_KEEP_N` | `8` / `4` | Intent queries generated, then kept after filtering |
| `FACETMARK_DECAY_FACTOR` / `_AGE_DAYS` | `0.5` / `365` | Age decay half-life |
| `FACETMARK_HEALTH_ENABLE_EXTERNAL` | `true` | Third-party link checks (DoH, Wayback, reader) |
| `FACETMARK_HOST` / `FACETMARK_PORT` | `127.0.0.1` / `8787` | Where `facetmark serve` listens |

## What is actually measured

This project's distinguishing feature is not its architecture, it is that every default was
chosen by a pre-registered experiment and two of them were **changed because the numbers
came back wrong**.

**The full fusion lost, and it lost to the simplest rung on the ladder.** W1 ran five rungs
(A content-only, B +lexical, C +intent, D +context and graph, E +LLM rerank) over 479
queries against 2,376 real crawled pages. Three pre-registered criteria, all three failed —
and not by being underwhelming. Adding facets made retrieval *worse*: A scored Recall@5
**0.643** / Recall@1 0.505 / MRR@10 0.564 against B 0.589, C 0.635, D 0.639, and ran 3.5x
faster. On a later, independent 616-query set the gap is wider still: **0.5860** for content
alone against **0.5065** for all four fused.

So the shipped default is **content + graph expansion + time decay**, not the full fusion.
Graph expansion stays because it is free — expansion never touches the ranked page, so every
ranked metric is bit-identical, and the second group finds the target in 2.09pp more queries
for 9 ms. Details in [`docs/gate-w1.md`](docs/gate-w1.md); the autopsy of *why* fusion loses,
including that RRF with flat weights lets a coincidence on a weak facet outvote confidence on
a strong one, and that the trigram half of the lexical facet had never worked on Chinese
queries at all, is in [`docs/w2-fusion-anatomy.md`](docs/w2-fusion-anatomy.md).

**The context multiplier changed the default twice.** Ungated it is +8.14pp on episodic
queries and −9.94pp on content queries, so W1 shipped it off. Gating it on "the query looks
episodic" won on 616 held-out queries — **+3.09pp Recall@5, CI95 [+1.79, +4.55], 19 better
and 0 worse** — and 1.2.0 shipped it on ([`docs/gate-w2w3.md`](docs/gate-w2w3.md)).

Then 1.3.0 took it back off. That run had only measured the gate where it *should* fire: its
0.55% false-positive rate came from 181 content queries a generator had been told not to put
dates into. Asked instead for **361 topical queries whose time expression belongs to the
subject matter** — a page filed in 2026 searched for as `2015年国际空间站咖啡机为什么那么贵` —
the gate fires on **361 of 361** and costs **−18.83pp Recall@5, CI95 [−23.27, −14.68], 3
better and 71 worse**, with Recall@1 falling 0.801 → 0.363. On the 304 probes whose resolved
window cannot contain the answer it is −22.37pp; on the 57 where the window happens to be
right it is exactly +0.00pp, which locates the damage in the window being wrong rather than
the multiplier being heavy. The pre-registered remedy fixed the bare-year clause completely
and still lost −10.52pp to relative time words, so it cleared one of its two frozen bars and
did not ship either. Protocol written before the data:
[`docs/gate-precision-protocol.md`](docs/gate-precision-protocol.md); report:
[`docs/gate-precision.md`](docs/gate-precision.md).

The same 616 queries judged five other candidate repairs. Three genuinely fix part of what
fusion broke (`C_notri` +4.54pp, `C_max` +4.22pp, `C_lowlex` +4.22pp) and none of them
catches up to the content facet alone — they stay 3.4–3.7pp behind it — so none shipped.
Two did nothing at all: `C_abstain` changed exactly 1 result out of 616.

**The intent facet is an idea problem, not a model-size problem.** W4 read 50 sampled
doc2query outputs by hand, with the rubric and the pass threshold frozen beforehand. Only
**38% (19/50)** were queries a real user might plausibly type — below the 50% bar, so the
verdict is the premise, not "the 3B model was too small". The corroborating measurement is
sharper: of the intents kept for each page, the fraction whose content words appear nowhere
on that page is 21.3% for pages with normal body text and **62.4% for pages with thin body
text** ([`docs/w4-intent-strata.md`](docs/w4-intent-strata.md)). The story was "when a page
cannot describe itself, the intents supply what is missing". The table says the opposite:
when a page cannot describe itself, the model is not supplying, it is inventing. The code
was not deleted — what was rejected is using it as an independent equal-weight facet.

**One run on a real export rather than a generated corpus**: 1,701 bookmarks, 96 folders,
1,513 hosts, titles only and no crawl ([`docs/real-library-demo.md`](docs/real-library-demo.md)).
Nothing there is scored — someone else's bookmarks have no ground truth — but the revert is
visible in it. Searching `2025 日历` in a library containing a bookmark literally titled
中国2025日历, the 1.2.0 default reads the year as a filing date and drops that bookmark from
rank 1 to rank 3, promoting an unrelated sunset-time tool to the top.

Reproduce any of it: `facetmark eval --rungs A,A_gatedctx` and the frozen query sets in
`eval/queries/`.

## Use it as karakeep's search engine

[karakeep](https://github.com/karakeep-app/karakeep) already has the browser extension, the
mobile app, the headless-Chrome crawler, multi-user accounts, tagging and a UI — everything
around retrieval. Its ranking is a plugin behind a four-method interface. facetmark
implements that interface, so the division of labour is: karakeep does the product,
facetmark does the ranking.

```bash
facetmark serve && facetmark token                      # prints the pairing token
cp -r integrations/karakeep/search-facetmark <karakeep>/packages/plugins/
export FACETMARK_URL=http://127.0.0.1:8787 FACETMARK_TOKEN=<token>
```

Then trigger a reindex in karakeep; it pushes every bookmark through `addDocuments`. No
schema coupling, no database reading. karakeep's crawled article text comes with it, which
skips the slowest part of a first index.

`POST /karakeep/search` accepts a `config` parameter, so ablations can be run **on a real
karakeep library** instead of only on generated corpora. Every number above comes from a
generated query set; this is the first path to checking them against real use. Setup,
field-by-field mapping, and the honest limits (post-ranking multi-user filtering, and the
TypeScript side not being built in this repo's CI) are in
[`docs/karakeep.md`](docs/karakeep.md).

This also means the project stops building its own extension, crawler and UI. karakeep
already does those better, and a ranking engine that also insists on shipping a browser
extension is a ranking engine with less time to spend on ranking.

## Commands

```
facetmark import [PATH]       Netscape HTML or Chrome JSON; no PATH reads the live profile
facetmark browsers            live browser profiles that can be imported
facetmark index [--no-fetch]  fetch, enrich, embed, filter intents, sessions, edges
facetmark reindex             rebuild everything, keeping the bookmarks
facetmark search QUERY        search from the terminal (--config to pick a rung, --explain)
facetmark show ID             one bookmark with its facets and health
facetmark sessions            reconstructed saving episodes, newest first
facetmark health [--check]    link health summary, or run a round of probes
facetmark stats               index size and coverage
facetmark serve               local HTTP service for the extension and integrations
facetmark mcp                 MCP server over stdio, for Claude Desktop and other clients
facetmark token [--rotate]    the pairing token the extension needs
facetmark demo / eval         offline synthetic corpus and the A-E ablation bench
```

## Boundaries this project keeps

**Your bookmarks are never modified.** facetmark reads the browser's export or profile and
writes only to its own SQLite file. A tool that rewrites your bookmarks is a tool you cannot
safely uninstall.

**Nothing is ever deleted.** Link health reports; it does not clean up. Dead links stay in
the library and stay searchable, and the "graveyard" endpoint exists so a UI can *offer* a
cleanup view, never so one happens automatically.

**Crawling is polite by default.** `robots.txt` is respected, two concurrent requests per
host with a 0.5 s floor between them, a real User-Agent that identifies the tool, and crawl
delays honoured up to 5 s. Fetching pages you bookmarked is still traffic to someone else's
server; the defaults assume you would rather be slow than rude.

**The intent facet is the only thing that sends page text anywhere**, and only to the
endpoint you configured. Set `FACETMARK_EMBED_BACKEND=local` and skip `index`'s enrichment
step to keep everything on the machine.

**The local service is token-paired.** `facetmark serve` binds 127.0.0.1 and mints a pairing
token; every route except `/` and `/health` requires it. `facetmark token --rotate`
invalidates the old one.

## Layout

```
src/facetmark/
  db.py normalize.py text.py sessions.py edges.py providers.py config.py
  importers/   Netscape HTML + Chrome JSON, timestamp unit detection
  fetch/       two-channel crawl, three-tier extraction, browser fallback queue
  enrich/      summaries, doc2query intents, self-consistency filter, vectors
  search/      query understanding, per-facet retrieval, RRF, context, graph, decay, rerank
  health/      local probe, external cross-check, synthesis, append-only store
  bridges/     other applications' plugin contracts (karakeep)
  eval/        synthetic corpus + A-E ablation bench with bootstrap CIs
  service.py api.py mcp_server.py cli.py
integrations/  karakeep search plugin (TypeScript, not built in this repo's CI)
extension/     MV3, TypeScript, esbuild
eval/queries/  frozen query sets: W1 real-library, W2/W3 holdout, gate-precision probes
docs/          one file per experiment, including the ones that failed
scripts/       corpus generation, verdict scripts, disposition tables
```

## Status

Read [`ROADMAP.md`](ROADMAP.md) for what is *not* done and why. Short version: W1 and W4 are
complete and both returned negative results; the six W2/W3 switches have been judged on a
fresh 616-query set; the one that changed a default was then overturned by an adversarial
probe set and the default reverted. Fusion itself is still not fixed.

Contribution rules: [`CONTRIBUTING.md`](CONTRIBUTING.md). Trust boundaries:
[`SECURITY.md`](SECURITY.md). Version history, including why each default changed:
[`CHANGELOG.md`](CHANGELOG.md).

## License

MIT.
