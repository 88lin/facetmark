# Contributing

The unusual thing about this repository is that its headline feature lost its
own evaluation. `docs/gate-w1.md` is the report; the shipped default
configuration is the one the data selected, not the one the design document
proposed. That history sets the bar for changes: **a retrieval change is not
accepted because it is plausible, it is accepted because it moved a number on
queries that did not suggest it.**

Everything else is ordinary.

## Getting set up

```bash
git clone https://github.com/88lin/facetmark
cd facetmark
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q            # 800+ tests, no network access required
ruff check src tests scripts
```

No API key is needed to develop or to run the suite. `FACETMARK_USE_MOCK_PROVIDER=true`
gives you a deterministic offline provider, and it is what the tests use.

One consequence worth knowing before you are surprised by it: the mock
provider's embeddings are a word-level feature hash, so content vectors are
noise on a mock library. `default_config()` therefore falls back to the full
lexical fusion whenever there is no real embedding model, and
`SearchResponse.config` reports the rung that *actually ran*. If you see
`"fused"` where you asked for `"full"`, that is the fallback, not a bug.

## Running things

```bash
facetmark import bookmarks.html     # parse a browser export
facetmark crawl                     # fetch bodies, respecting robots.txt
facetmark enrich                    # summaries, topics, intent queries
facetmark index                     # embeddings, sessions, graph edges
facetmark search "那篇讲 raft 的"
facetmark serve                     # HTTP API
facetmark mcp                       # MCP server over stdio
```

`scripts/mcp_e2e.py` drives the MCP server through a real stdio subprocess and
asserts 22 behaviours. CI runs it on one shard. If you touch `mcp_server.py`,
run it locally — the unit tests deliberately do not cover that file, because
the failure mode being guarded against is the protocol wiring, not the logic.

## What a good pull request looks like

**Bug fixes and plumbing.** Normal rules. A test that fails before and passes
after. `ruff check` clean. Commit message says what was wrong, not what you
typed.

**Retrieval changes.** These need evidence, and the evidence has a specific
shape:

1. Add your variant as a named configuration in `search/pipeline.py`. Do not
   change a default in the same commit that introduces the mechanism.
2. Run it against a query set. `facetmark eval --config <name>` takes a JSONL
   query file; `eval/queries/w1-real-library.jsonl` is the W1 set (479 queries,
   2,376 real pages).
3. Report paired statistics, not means. The harness gives you McNemar plus a
   bootstrap CI because a 2pp difference on 479 queries is frequently nothing.
   `n=171` per query type buys you roughly ±4pp of interval width; plan for it.
4. **Do not fit on the query set that suggested the change.** This is the one
   rule that gets pull requests closed. Two knobs currently ship switched off
   — `Config.weight_overrides` and `Config.context_gate` — precisely because
   the numbers arguing for them came out of the only query set available. See
   `docs/gate-w1.md` §9.5.

A retrieval change that makes the numbers worse but explains *why* is more
useful here than one that makes them better and cannot say why. The largest
single finding in the W1 report is of exactly that kind: fusing any weaker
facet into a strong content vector costs 5-6pp of Recall@5, and it costs the
same amount whichever facet you add.

## Things that are open

`docs/gate-w1.md` §9.4 lists the three follow-ups in priority order:
fusion weights and candidate gating, query-type gating for the contextual
multiplier, and a manual read of 50 intent-extraction outputs to decide whether
the idea itself holds up on a 3B model. All three need a query set that has not
seen the hypothesis. Building that set is the most valuable thing anyone could
contribute right now, and it does not require touching retrieval code at all.

## Style

`ruff` decides formatting arguments; line length is 100. Tests are named as
sentences describing the behaviour, not `test_func_1`. Comments explain why a
constant has the value it has, ideally with the measurement attached — several
of them cite p-values, and that is deliberate.

## Reporting problems

Open an issue. If it is a retrieval quality complaint, the query text and what
you expected to find are worth more than a description of the symptom, because
the first question will be whether the classifier read your query as episodic.

Security issues: see `SECURITY.md`. Do not open a public issue for those.
