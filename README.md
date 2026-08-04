# Facetmark

Search your own bookmarks by **what the page was about**, **why you saved it**, and **when you were saving things like it**.

Most bookmark tools index the wrong object. They fetch the page, ask a model for a summary and some tags, push one vector into a store, and call it semantic search. That works when you remember roughly what the page said. It fails on the two ways people actually remember their own bookmarks: *"the thing I read when I was trying to make embeddings fit in SQLite"* (a purpose, not a topic) and *"the stuff I saved the same evening as that Docker post"* (an episode, not a topic).

Facetmark indexes four things per bookmark and fuses them:

| Facet | What it holds | What it rescues |
|---|---|---|
| **F1 content** | embedding of the extracted body | ordinary topical recall |
| **F2 intent** | embeddings of generated *questions the page answers* (doc2query) | vague, purpose-shaped queries |
| **F3 lexical** | two FTS5 indexes: jieba-segmented + trigram | exact identifiers, CJK, substrings |
| **F4 episodic** | save-time sessions, folders, link graph | "around the same time as..." |

F1 and F3 are table stakes. **F2 and F4 are the point** - they are what the existing tools do not have.

### Then we measured it, and the fusion lost

2,376 real web pages, 479 evaluation queries, real models, three preregistered pass criteria. **All three failed.** More usefully, the ablation found that fusing was itself the problem: F1 alone gets **95.9%** Recall@5 on content queries, and equal-weight RRF with any weaker facet added drops that by 5.4pp (McNemar p<0.01). A leave-one-out probe ruled out the obvious suspect - dropping the lexical facets and fusing only F2 costs exactly the same 5.43pp.

So the shipped default is **F1 + graph expansion + time decay**, not the full fusion. The other facets are still built, still stored, still addressable as `--config C`, `--config D`, `--config E`. Graph expansion stays on because it is bit-identical on ranking and adds 2.09pp of neighbours for 9ms (10 wins, 0 losses). The F4 context multiplier is off pending a query-type gate: it is +8.14pp on episodic queries and −9.94pp on content queries, and shipping it ungated is a net loss.

A deployment with no API key still falls back to the full fusion, because the mock provider's feature-hash "embeddings" make F1 noise. The response reports which rung actually ran.

The whole thing - ladder, bootstrap CIs, per-query McNemar decisions, the leave-one-out probe, and the reasoning for each default flag - is in [`docs/gate-w1.md`](docs/gate-w1.md). The negative result is the deliverable.

Three follow-ups took the losing step apart. [`docs/query-set-lexical-audit.md`](docs/query-set-lexical-audit.md) asked how much of the query set never needed a vector: 80.1% of content queries and 46.3% of vague ones are solvable by word matching alone, and 6.05% of all queries are found *only* by the lexical facet - so F3 is not contributing nothing, the fusion is losing what it contributes. [`docs/w2-fusion-anatomy.md`](docs/w2-fusion-anatomy.md) then measured the operator itself. Two results worth stating up front: F3's trigram half had never worked on Chinese queries at all (an unsegmented sentence reached the index as one quoted phrase - 25 of 211 Chinese queries got any candidate; the repair takes it to 202, and overall Recall@5 does not move), and RRF's arithmetic gives no protection to a sole-facet hit - with the shipped constants, any document two full-weight facets both recall beats any document a single facet ranks first, at every rank inside the candidate depth. [`docs/w3-criterion-medium.md`](docs/w3-criterion-medium.md) then asked whether the W1 criterion could have measured the context multiplier at all: the shipped `MAX_BOOST = 1.60` spans 79.7% of rung A's score range but only 20.9% of the fused rung's, so testing the same mechanism there would need a cap of 6.03 - and separately, 66.3% of candidates never receive any boost, which is a different failure from a boost being too small.

Everything runs locally: Python + SQLite (`sqlite-vec`) + a browser extension. No server, no account, no upload of your library. Your bookmarks are never modified - Facetmark only reads them.

---

## Install

```bash
pip install facetmark          # or: uv pip install facetmark
facetmark import               # reads the live browser profile; or pass a file
facetmark index                # fetch + enrich + embed + session + graph
facetmark serve                # http://127.0.0.1:8787, prints a pairing token
```

From source:

```bash
git clone https://github.com/88lin/facetmark
cd facetmark
uv venv && uv pip install -e ".[dev]"
pytest -q
```

Export your bookmarks first: Chrome/Edge -> Bookmark manager -> Export, or Firefox -> Manage bookmarks -> Export to HTML. Both the Netscape HTML format and Chrome's `Bookmarks` JSON file are accepted.

### Try it without a library or an API key

```bash
facetmark demo            # builds a synthetic library, indexes it, runs three searches
facetmark eval --ablation # A-E ablation with bootstrap CIs and McNemar tests
```

Both run entirely offline on a mock provider. The mock's "embeddings" are feature hashes over lexical tokens, so the numbers check that the pipeline is wired correctly - they are **not** a quality measurement, and every command that uses them says so.

### Model access

One OpenAI-compatible endpoint drives both enrichment and embeddings, so any provider that speaks that API works:

```bash
export FACETMARK_API_KEY=sk-...
export FACETMARK_BASE_URL=https://api.openai.com/v1   # or your own gateway
export FACETMARK_CHAT_MODEL=gpt-4o-mini
export FACETMARK_EMBED_MODEL=text-embedding-3-small
```

Shared and free gateways list models they cannot always serve, so the chat side takes an
ordered fallback chain. It is empty by default - on a paid endpoint an error is information
and hiding it behind three more attempts turns a typo into a latency mystery.

```bash
export FACETMARK_CHAT_MODEL_FALLBACKS="DeepSeek-V4-Pro,grok-4.3-fast,deepseek-v4-flash"
```

Failover is forward-only and sticky: the first model that answers with a JSON object serves
the rest of the run, and models already ruled out are never re-probed - on a 3,000-page
index that would be thousands of known-dead timeouts. A model that returns HTTP 200 and
prose counts as a failure, because for a JSON call it is indistinguishable from absence.
The provider records answers and failures per model (`chat_model_mix()`), and any number
reported from a chained run has to publish that mix - otherwise the run's `chat_model`
field is a lie.

For ~1,700 bookmarks the one-off indexing cost lands around 8.5M input + 0.9M output chat tokens and ~3.4M embedding tokens. Vectors for that library are ~35 MB at float32/1024-dim; brute-force scan in `sqlite-vec` is well inside its comfortable range, so there is no ANN index to tune.

---

## The browser extension

```bash
cd extension && npm install && npm run build
```

Load `extension/dist` as an unpacked MV3 extension (Chrome/Edge: `chrome://extensions` -> Developer mode -> Load unpacked). Paste the pairing token from `facetmark serve` into the options page.

The extension does three jobs:

- **Search** - popup and the `fm` omnibox keyword. It renders in two stages: the FTS5 result goes on screen in single-digit milliseconds, the ranked result replaces it a few hundred milliseconds later. Waiting for stage two before drawing anything is what makes fast search feel slow.
- **Save** - the current page or any link, straight into the index.
- **Channel B** - pages the server cannot fetch (login walls, client-rendered shells, hosts that refuse unknown agents) are rendered in a background tab by the browser you are already logged into, three at a time, with a visible counter and a pause switch. About one page in fifty needs this; without it those pages stay title-only forever.

All requests originate in the service worker, never in a content script. Chrome 142 tightened Local Network Access, and an extension worker holding an explicit `host_permissions` entry for `127.0.0.1` is the path that keeps working.

---

## Crawling other people's servers

Indexing a bookmark library means touching a few thousand hosts that never asked for the traffic. Channel A reads `/robots.txt` once per host and obeys it (RFC 9309: longest match wins, `Allow` breaks a tie, `*` and `$` supported, a group naming `facetmark` beats the `*` group), on top of a global concurrency cap, at most two in-flight requests per host, and a minimum interval between them. A published `Crawl-delay` raises that interval, capped so one host asking for 30 seconds cannot stall the sweep.

A page that `robots.txt` disallows is recorded as `robots_denied` and stays title-only. It is **not** re-tried through the browser extension — channel B would succeed, because it is the user's own logged-in browser, and that is precisely the manoeuvre `robots.txt` exists to prevent. The same rule applies to link-health probes: a liveness check is still automated access, and the drift check reads the body.

```bash
FACETMARK_RESPECT_ROBOTS=false        # your servers, your call
FACETMARK_ROBOTS_ON_ERROR=deny        # RFC 9309 reads an unreachable robots.txt as "disallow all"
FACETMARK_ROBOTS_MAX_CRAWL_DELAY=5.0  # ceiling on an honoured Crawl-delay, seconds
```

The default for an *unreachable* `robots.txt` (5xx, timeout, reset) is `allow`, which deviates from the RFC on purpose. Applied literally, one flaky CDN silently drops a chunk of the user's own library out of the user's own index — and the user is not a search engine competing for crawl budget, they are re-reading pages they already opened in a browser. A *missing* `robots.txt` (404) means allow, as the RFC says. `deny` restores the strict reading.

---

## MCP server

```bash
facetmark mcp    # stdio
```

Nine tools: `search_bookmarks`, `get_bookmark`, `list_sessions`, `get_session`, `find_related`, `synthesize`, `suggest_from_context`, `check_link_health`, `save_bookmark`, plus `bookmark://<id>` and `session://<id>` resources. `synthesize` answers from your own saved pages with per-claim citations and refuses to keep a claim whose citation does not resolve; it also reports what it could **not** find, which is the part that makes the answer usable.

---

## Link health, and what it never does

Roughly a quarter of a multi-year library is older than two years, and some of it is gone. Facetmark checks in three layers:

1. **Local probe** - ranged GET for liveness; a full GET only when it needs to compare content.
2. **External cross-check** - DoH resolvers, Wayback, a reader proxy - used only to separate *"the page is gone"* from *"the page is fine and this network cannot reach it"*.
3. **Synthesis** - the two layers together produce `alive` / `drifted` / `soft_gone` / `restricted` / `unreachable` / `gone`.

The design rule is that a local failure can never, on its own, conclude `gone`: confidence from local evidence alone is capped below the threshold that a "dead" verdict requires. A blocked page and a deleted page look identical from one socket.

**Nothing is ever deleted or hidden.** A link confirmed dead twice, at least seven days apart, gets a graveyard view and a Wayback link - and stays fully searchable. `restricted` gets a badge and nothing else. Two lessons from the tools that came before, both encoded here: automation needs a deterministic fallback the user can reach, and a knowledge-graph visualisation is not that fallback.

Two switches, both honoured everywhere:

```bash
FACETMARK_HEALTH_ENABLE_EXTERNAL=false      # never leave the machine for health checks
FACETMARK_PRIVACY_EXCLUDED_DOMAINS=bank.example,internal.corp
```

Excluded domains skip the entire external layer - DNS included.

---

## Commands

```
facetmark import [PATH]       Netscape HTML or Chrome JSON; no PATH reads the live profile
facetmark browsers            live browser profiles that can be imported
facetmark index [--no-fetch]  fetch, enrich, embed, filter intents, sessions, edges
facetmark search QUERY        search from the terminal (--config to pick a rung)
facetmark show ID             one bookmark with its facets and health
facetmark sessions            saving sessions, newest first
facetmark health [--check]    link health summary, or run a round of probes
facetmark stats               library overview
facetmark serve               HTTP API for the extension
facetmark mcp                 MCP server over stdio
facetmark token --rotate      new pairing token
facetmark demo / eval         offline synthetic corpus and A-E ablation
```

## Layout

```
src/facetmark/
  db.py normalize.py text.py sessions.py edges.py providers.py
  importers/   Netscape HTML + Chrome JSON
  fetch/       two-channel crawl, three-tier extraction
  enrich/      summaries, doc2query, self-consistency filter, vectors
  search/      query understanding, per-facet retrieval, RRF, context, graph, decay, rerank
  health/      local probe, external cross-check, synthesis, append-only store
  eval/        synthetic corpus + A-E ablation bench
  service.py api.py mcp_server.py cli.py
extension/     MV3, TypeScript, esbuild
```

847 tests, no network access required to run them.

Project status, including what is *not* done and why, is in [`ROADMAP.md`](ROADMAP.md). Short version: the W1 evaluation gate is complete and it failed all three of its pre-registered criteria; weeks 2 through 4 of the plan are not done, and the thing blocking them is a query set, not code. Contribution rules are in [`CONTRIBUTING.md`](CONTRIBUTING.md); trust boundaries in [`SECURITY.md`](SECURITY.md).

---

## 中文说明

书签搜不到，通常不是模型不行，是**索引的对象错了**。只对正文做一个向量，就只能接住“我记得它讲什么”这一种回忆方式；接不住“我当时是为了解决什么问题才存的”和“跟那批东西一起存的”。

Facetmark 给每条书签建四个面：内容面（正文向量）、**意图面**（让模型反向生成“这个页面能回答哪些问题”，再用自洽性过滤掉幻觉出来的问题）、词面（jieba 分词 + trigram 两条 FTS5 路径，中文短词和英文子串盲区互不重叠）、**情境面**（保存时间聚类出的 session、文件夹、链接图）。后两个是现有工具都没有的。

**然后我们量了一下这四个面融合起来到底有没有用，答案是没有。** 2376 篇真实网页、
479 条评测查询、真实模型（`docs/gate-w1.md`）：只用内容面，内容型查询 Recall@5 是
95.9%；平权 RRF 融进任意一个更弱的面就掉 5.4pp。所以默认配置现在是**内容面 + 图扩展
+ 时间衰减**，另外三个面照建照存，但要显式 `--config C/D/E` 才参与排序。图扩展留在
默认里是因为它对排序逐位不变、只把邻居多送 2.09pp 上来，代价 9 毫秒。
情境面的上下文乘子被暂时关掉：它在情景型查询上 +8.14pp，在内容型上 −9.94pp，
得先按查询类型门控才能开——那是下一轮的活。

原始阶梯、置信区间、McNemar 逐条判决和留一法探针都在 `docs/gate-w1.md`，包括三条
预注册判据**全部未通过**的判定过程。

后续三份把"输掉的那一步"拆开了。`docs/query-set-lexical-audit.md` 量出这批查询里有
多少条根本不需要向量（内容型 80.1%、模糊型 46.3%），以及 6.05% 的查询**只有**词面能
找到——所以词面面不是没贡献，是融合把贡献弄丢了。`docs/w2-fusion-anatomy.md` 接着量
融合算子本身，两条值得单说：词面的 trigram 半边在中文查询上**从来没有工作过**（无空格
的整句被当成一个引号短语丢给索引，211 条中文查询只有 25 条拿得到候选；修好后 202 条，
而整体 Recall@5 一动不动），以及 RRF 的算术**给不出单面保护**——用出厂常数，任何被两个
满权重面同时召回的文档，在候选深度内的每一个名次上都赢过任何单面第一名。
`docs/w3-criterion-medium.md` 再往前问一层：W1 的判据**能不能测到**上下文乘子——出厂的
`MAX_BOOST = 1.60` 在 A 档能跨过整档分数量程的 79.7%，在融合档只有 20.9%，同一个机制
放在融合档里测需要 6.03 的上限；另外，66.3% 的候选**根本没有拿到任何加成**，那和
"加成太小推不动"是两个不同的问题。

全部本地运行，不改你的浏览器书签，不上传书签库。想先看效果又不想配 key：`facetmark demo`。

链接健康检查遵守一条硬规则：**任何情况下不自动删除、不自动隐藏**。本地探测失败永远不足以判定“页面已死”——从一个 socket 看过去，被墙和被删长得一模一样。

## License

MIT
