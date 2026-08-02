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

Everything runs locally: Python + SQLite (`sqlite-vec`) + a browser extension. No server, no account, no upload of your library. Your bookmarks are never modified - Facetmark only reads them.

---

## Install

```bash
pip install facetmark          # or: uv pip install facetmark
facetmark import bookmarks.html
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

For ~1,700 bookmarks the one-off indexing cost lands around 8.5M input + 0.9M output chat tokens and ~3.4M embedding tokens. Vectors for that library are ~35 MB at float32/1024-dim; brute-force scan in `sqlite-vec` is well inside its comfortable range, so there is no ANN index to tune.

---

## The browser extension

```bash
cd extension && npm install && npm run build
```

Load `extension/dist` as an unpacked MV3 extension (Chrome/Edge: `chrome://extensions` -> Developer mode -> Load unpacked). Paste the pairing token from `facetmark serve` into the options page.

The extension does three jobs:

- **Search** - popup and the `fm` omnibox keyword. It renders in two stages: the FTS5 result goes on screen in single-digit milliseconds, the fused four-facet ranking replaces it a few hundred milliseconds later. Waiting for stage two before drawing anything is what makes fast search feel slow.
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
facetmark import PATH         Netscape HTML or Chrome JSON
facetmark index [--no-fetch]  fetch, enrich, embed, filter intents, sessions, edges
facetmark search QUERY        four-facet search from the terminal
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
  search/      query understanding, four-facet RRF, context, graph, decay, rerank
  health/      local probe, external cross-check, synthesis, append-only store
  eval/        synthetic corpus + A-E ablation bench
  service.py api.py mcp_server.py cli.py
extension/     MV3, TypeScript, esbuild
```

599 tests, no network access required to run them.

---

## 中文说明

书签搜不到，通常不是模型不行，是**索引的对象错了**。只对正文做一个向量，就只能接住“我记得它讲什么”这一种回忆方式；接不住“我当时是为了解决什么问题才存的”和“跟那批东西一起存的”。

Facetmark 给每条书签建四个面并做 RRF 融合：内容面（正文向量）、**意图面**（让模型反向生成“这个页面能回答哪些问题”，再用自洽性过滤掉幻觉出来的问题）、词面（jieba 分词 + trigram 两条 FTS5 路径，中文短词和英文子串盲区互不重叠，缺一不可）、**情境面**（保存时间聚类出的 session、文件夹、链接图）。后两个是现有工具都没有的。

全部本地运行，不改你的浏览器书签，不上传书签库。想先看效果又不想配 key：`facetmark demo`。

链接健康检查遵守一条硬规则：**任何情况下不自动删除、不自动隐藏**。本地探测失败永远不足以判定“页面已死”——从一个 socket 看过去，被墙和被删长得一模一样。

## License

MIT
