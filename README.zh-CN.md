# facetmark

**书签搜索：索引你**为什么**存这个页面，而不只是它写了什么。**

[![CI](https://github.com/88lin/facetmark/actions/workflows/ci.yml/badge.svg)](https://github.com/88lin/facetmark/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1081-brightgreen)](tests/)

[English](README.md) · [简体中文](README.zh-CN.md)

全部在本机运行，全部落在一个 SQLite 文件里。不上传、不删除，也**从不写回**你浏览器自己
的书签库。

---

## 它要解决的问题

你八个月前存过一个页面。你记得**为什么**存它——「某个帖子里有人贴的那个讲 Postgres
索引类型的东西」——也大概记得是什么时候。你唯独不记得它的标题，而标题是浏览器书签
搜索唯一会看的字段。

所以 facetmark 给每条书签建四个索引：

| 面 | 是什么 | 接得住哪种回忆 |
|---|---|---|
| **词面** | 两条 FTS5 索引：字符三元组 + jieba 分词 | 精确串、ID、代码、没有空格的中文 |
| **内容面** | 页面正文抽取后的向量 | 「那篇讲消费者组重平衡的文章」 |
| **意图面** | 让模型反向生成「这页能回答哪些问题」，再用自洽性探针筛掉幻觉出来的 | 「kafka 卡住了怎么办」 |
| **情境面** | 用保存时间的间隔重建保存会话，加上文件夹 / 域名 / 语义构成的图 | 「跟那批东西一起存的」 |

候选用 RRF（倒数排名融合）合并，沿图扩展一跳，再按年龄衰减。

然后这个项目**量了一下四个面融合到底有没有用，答案是没有**——详见
[实测到了什么](#实测到了什么)。所以出厂默认只搜**内容面**，外加图扩展和时间衰减；另外
三个面照建、照存，用 `--config` 就能调出来。**没配 API key 的部署反而走全融合**，因为
没有真实嵌入时，内容面恰好是那个只返回噪声的面。

## 快速开始

```bash
uv pip install facetmark        # 或者：pip install facetmark

facetmark import                # 直接读浏览器配置目录，也可以传一个导出文件的路径
facetmark index                 # 抓正文、富集、嵌入、切会话、建图
facetmark search "网盘直链解析"
```

想先导出成文件再喂给它：Chrome / Edge → 书签管理器 → 导出，Firefox → 管理书签 → 导出
HTML。Netscape HTML 和 Chrome 的 `Bookmarks` JSON 都能读。

一个 1,701 条书签的真实库跑出来的原样输出（[完整记录](docs/real-library-demo.md)）：

```
$ facetmark import favorites.html --json
{"parsed": 1710, "inserted": 1701, "merged_duplicates": 9, "non_indexable": 1,
 "folders": 96, "max_depth": 4, "timestamp_unit": "unix_s", "warnings": []}

$ facetmark search "chrome 插件下载" -n 3
1. Chrome插件下载器          收藏夹栏/工具/插件搜索工具
2. 插件小屋 Chrome插件        收藏夹栏/工具/插件搜索工具
3. Chrome 离线安装包          收藏夹栏/工具
```

### 不配 key、也没有书签库，先看效果

```bash
facetmark demo                   # 合成库，建完索引直接搜，全程离线
facetmark eval --ablation        # A–E 消融，带 bootstrap 置信区间和 McNemar 检验
facetmark eval --rungs C,C_notri # 或者任选两档正面对打
```

这两条命令用的是 mock provider，它的「嵌入」是词面 token 的特征哈希。**它们只能证明
流水线接对了，不是质量测量**，每条用到它的命令都会在输出里自己说明这一点。

## 从源码安装

```bash
git clone https://github.com/88lin/facetmark
cd facetmark
uv venv && uv pip install -e ".[dev]"
pytest -q                       # 1081 条测试，不需要联网
ruff check src tests scripts
```

Python 3.10+。唯一一个不常见的依赖是
[`sqlite-vec`](https://github.com/asg017/sqlite-vec)，它把向量 KNN 直接做进 SQLite 里
——**没有另一个向量数据库要跑**。

## 模型接入

facetmark 需要一个嵌入模型；意图面还需要一个 chat 模型。任何 OpenAI 兼容端点都行。

```bash
export FACETMARK_API_KEY=sk-...
export FACETMARK_BASE_URL=https://api.openai.com/v1      # 必须带 /v1
export FACETMARK_CHAT_MODEL=gpt-4o-mini
export FACETMARK_EMBED_MODEL=text-embedding-3-small
export FACETMARK_EMBED_DIM=1536
```

`FACETMARK_CHAT_MODEL_FALLBACKS` 接一个逗号分隔的列表，主模型报错时按顺序往下试——用
免费网关或者有限流的网关时很有用。

### 本地嵌入

如果你的网关只有 chat、没有 `/embeddings`（免费和聚合网关非常常见，而且
`GET /v1/models` **不会告诉你**——它照样列出一串模型，但一个都不给嵌入接口用），或者
你干脆不想把正文发出去：

```bash
pip install 'facetmark[local]'                          # 装 sentence-transformers
export FACETMARK_EMBED_BACKEND=local
export FACETMARK_LOCAL_EMBED_PATH=BAAI/bge-m3           # 或者本地目录
export FACETMARK_EMBED_MODEL=bge-m3
export FACETMARK_EMBED_DIM=1024
```

`sentence-transformers` 会拉进来一个 torch，比这个项目其他所有依赖加起来都大，所以它
不在基础安装里。

**换编码器之前必须先自校验。** `sqlite-vec` 对任何宽度正确的向量都会返回近邻，哪怕
它来自另一个模型：结果照样有序、看着合理、其实无意义，代码里没有任何断言能拦住这件事。
做法是拿索引里已经存着的东西重新编码一遍，和存着的向量算余弦。`vec_intent` 存的是逐字
原文，中间没有拼接和截断，是最干净的探针。本项目自己这样测了 64 条：**最小自余弦
0.999976、中位 0.999993、64/64 全部自我匹配**，而每条对其余 63 条的**最佳错配**余弦
中位只有 0.5357、最高 0.6501。起作用的是这个**差距**，不是 0.99 这个数本身。

嵌入维度和模型名在第一次建索引时写进数据库。之后不重建就改不了，facetmark 宁可拒绝
运行也不会悄悄混着用、然后返回一堆看起来正常的垃圾近邻。

## 配置

所有配置项都是 `FACETMARK_` 前缀的环境变量，或者一个 `.env` 文件。值得知道的几个：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `FACETMARK_DATA_DIR` | 平台数据目录 | 数据库、配对令牌、日志都在这里 |
| `FACETMARK_DB_NAME` | `facetmark.db` | 一个文件一个库 |
| `FACETMARK_FETCH_CONCURRENCY` | `30` | 全局抓取并发 |
| `FACETMARK_FETCH_PER_HOST_CONCURRENCY` | `2` | 单主机并发上限，另有 0.5 秒最小间隔 |
| `FACETMARK_RESPECT_ROBOTS` | `true` | 见下面「抓的是别人的服务器」 |
| `FACETMARK_INTENT_GENERATE_N` / `_KEEP_N` | `8` / `4` | 意图查询生成条数 / 过滤后保留条数 |
| `FACETMARK_DECAY_FACTOR` / `_AGE_DAYS` | `0.5` / `365` | 时间衰减半衰期 |
| `FACETMARK_HEALTH_ENABLE_EXTERNAL` | `true` | 第三方链接检查（DoH、Wayback、reader） |
| `FACETMARK_HOST` / `FACETMARK_PORT` | `127.0.0.1` / `8787` | 本地服务监听地址 |

## 实测到了什么

这个项目真正跟别的书签工具不一样的地方不是架构，是**每一个默认值都由一次预注册实验
选出来，而其中两个是因为数字回来是反的才改掉的**。

### 融合输了，而且输给了阶梯上最简单的那一档

W1 跑了五档（A 只有内容面、B 加两个词面、C 再加意图面、D 再加上下文乘子和图扩展、
E 再加 LLM listwise 重排），语料是 2,376 个真实抓取的网页，查询集 479 条。**三条预注册
判据全部未通过**，而且不是「提升不够」——是**加了机制反而更差**：

| 档位 | Recall@1 | Recall@5 | MRR@10 | p50 延迟 |
|---|---|---|---|---|
| **A**（只有内容面） | **0.505** | **0.643** | **0.564** | **148 ms** |
| B（+ 两个词面） | 0.432 | 0.589 | 0.501 | 189 ms |
| C（+ 意图面） | 0.426 | 0.635 | 0.509 | 526 ms |
| D（+ 上下文 + 图） | 0.399 | 0.639 | 0.497 | 523 ms |

最简单的那一档在三个总体指标上全部最好，而且快 3.5 倍。后来在一批**完全独立的 616 条
查询**上重测，差距更大：**0.5860**（只有内容面）对 **0.5065**（四面全融）。

所以出厂默认是**内容面 + 图扩展 + 时间衰减**。图扩展留着是因为它免费——扩展从不动已经
排好的那一页，所以每一个排序指标都逐位不变，而第二组候选在多 2.09pp 的查询里找到了目标
（10 胜 0 负，p=0.0019），代价 9 毫秒。判据与判定过程见
[`docs/gate-w1.md`](docs/gate-w1.md)。

**为什么融合会输**，三份文档拆开讲：

- [`docs/query-set-lexical-audit.md`](docs/query-set-lexical-audit.md)：这批查询里有多少
  条根本不需要向量（内容型 80.1%、模糊型 46.3%），以及 **6.05% 的查询只有词面能找到**
  ——词面不是没贡献，是融合把贡献弄丢了。
- [`docs/w2-fusion-anatomy.md`](docs/w2-fusion-anatomy.md)：两件值得单说的事。一，词面的
  **trigram 半边在中文查询上从来没工作过**——没有空格的整句被当成一个引号短语丢给索引，
  211 条中文查询只有 25 条（11.85%）拿得到候选；修好后 202 条（95.73%），而整体 Recall@5
  一动不动。二，**RRF 的算术给不出单面保护**：用出厂常数，任何被两个满权重面同时召回的
  文档，在候选深度内的每一个名次上都赢过任何单面第一名。
- [`docs/w3-criterion-medium.md`](docs/w3-criterion-medium.md)：再往前问一层——W1 的判据
  **能不能测到**上下文乘子？出厂的 `MAX_BOOST = 1.60` 在 A 档能跨过整档分数动态范围的
  79.7%（对数尺度），在 C/D 档只有 20.9%；同一个机制放在融合档里测，上限得是 6.03。
  另外 66.3% 的候选**根本没拿到任何加成**，那和「加成太小推不动」是两个不同的问题。

### 上下文乘子：一个 flag，两次改默认

不门控时它在情景型查询上 **+8.14pp**、在内容型上 **−9.94pp**，所以 W1 把它关掉了，只留
下「按查询类型门控就该行」这个猜想。

猜想后来在 **616 条没有参与产生它的查询**上判过，判定规则先于结果落盘：门控之后相对纯
内容面是 **+3.09pp Recall@5，CI95 [+1.79, +4.55]，19 条变好、0 条变差，p=3.8e-6**，内容
型查询逐位不变（+0.00pp），情景型 +8.48pp。**1.2.0 把它默认打开了**
（[`docs/gate-w2w3.md`](docs/gate-w2w3.md)）。

**然后 1.3.0 又把它关回去了。** 那一轮只量了门控**该响的时候**响不响：0.55% 的误触发率
来自 181 条内容型查询，而那 181 条在生成时被明确禁止写日期。换一批**时间短语属于主题
本身**的查询——一个 2026 年存的页面，被问成 `2015年国际空间站咖啡机为什么那么贵`——
361 条探针，门控**响了 361 次，100%**，代价是：

```
A          Recall@5 0.9058   Recall@1 0.801
A_gatedctx Recall@5 0.7175   Recall@1 0.363

Δ Recall@5  -18.83 pp   CI95 [-23.27, -14.68]   3 胜 71 负
```

Recall@1 直接腰斩。分层看：在 304 条**解析出的时间窗口根本不可能装下答案**的探针上是
**−22.37pp**；在 57 条**窗口恰好是对的**探针上是**精确的 +0.00pp**（1 胜 1 负，p=1.0）
——这就把伤害定位在「窗口判错」，而不是「乘子太重」。

预注册的补救方案 `gate_v2` 有两道在看数据前冻死的关：**(a) 探针集上的代价必须消失
→ 未通过**（n=361 仍然 −10.52pp，CI95 [−13.85, −7.48]，1 胜 39 负；v2 保持沉默的 197 条
是 +0.00pp、0 条不一致，残余全部来自它**故意没碰**的相对时间词那一条规则）；**(b) 616
条上的收益必须还在 → 通过**（+1.79pp，CI95 [+0.81, +2.92]，11 胜 0 负，p=0.00098）。协议
要求两关都过，所以默认值**退回 1.1.0 的无门控状态**，`gate_v2` 留在树里关着。

看数据之前写好的协议：[`docs/gate-precision-protocol.md`](docs/gate-precision-protocol.md)；
报告：[`docs/gate-precision.md`](docs/gate-precision.md)。

**这里没有顺手做 `gate_v3`。** 这 361 条已经被用来在两个门控之间做选择，用完了；在同一
批探针上收窄规则再报增益，就是在测试集上拟合。v3 必须配新的预注册和全新的探针集，两笔账
都记在 [`ROADMAP.md`](ROADMAP.md) 里。

### 另外五个候选修复

同一批 616 条查询还判了五个候选修复。三个确实修好了融合坏掉的一部分（相对 C 档：
`C_notri` +4.54pp、`C_max` +4.22pp、`C_lowlex` +4.22pp），但三个都仍然**落后纯内容面
3.4–3.7pp**——融合是被解释清楚了，不是被救回来了，所以它们继续默认关闭。两个什么都没
发生：`C_abstain` 在 616 条里只改了 1 条结果，同一个门控装在融合栈上是 7 胜 8 负
（−0.16pp）。

### 意图面：理念问题，不是模型太小

W4 抽了 50 篇人工读意图抽取的输出，评分标准和判定阈值都在看数据之前写死。结果
**「会（真实用户会这么问）」只有 38%（19/50）**，低于 50% 的线，判为**理念问题**，不是
「3B 模型不够，换 32B 再试」。旁证在
[`docs/w4-intent-strata.md`](docs/w4-intent-strata.md)：每条保留下来的意图里，信息词在
页面（标题 + 正文）上完全不出现的比例，正文正常的页面是 21.3%，**正文贫瘠的页面是
62.4%**。H 的叙事是「页面说不清自己时，意图补上了缺的信息」；这张表说的是反的——
**页面说不清自己时，模型不是在补，是在编。**

意图抽取的代码**没有删**，仍在索引流程里。被否掉的是「把它当成一个独立的平权检索面」
这个用法。

### 一次真实导出上的跑通

上面每一个数字都来自生成语料。[`docs/real-library-demo.md`](docs/real-library-demo.md)
是唯一一次在**真人真实导出**上跑出厂路径：1,701 条书签、96 个文件夹、1,513 个域名、
92.8% 中文标题，只有标题、零抓取。**那里没有任何分数**——别人的书签没有标准答案——但
1.3.0 那次回退在里面看得见：库里有一条书签的标题就叫「中国2025日历」，搜 `2025 日历`，
1.2.0 的默认把这个年份读成归档日期，把它从第 1 名压到第 3 名，顶上来一个不相干的日落
时间查询工具。

想复现上面任何一个数字：`facetmark eval --rungs A,A_gatedctx`，冻结的查询集在
`eval/queries/` 下。

## 拿它当 karakeep 的搜索引擎

[karakeep](https://github.com/karakeep-app/karakeep) 已经把检索**周边**的东西全做完了：
浏览器扩展、手机 App、无头 Chrome 抓取加正文抽取、资源归档、多用户、自动打标、Web UI、
Docker / Helm 部署。而**它的排序是一个插件**，接口只有四个方法。facetmark 实现了这个
接口，于是分工就很清楚：**karakeep 做产品，facetmark 做排序。**

```bash
facetmark serve && facetmark token                      # 打印配对令牌
cp -r integrations/karakeep/search-facetmark <karakeep>/packages/plugins/
export FACETMARK_URL=http://127.0.0.1:8787 FACETMARK_TOKEN=<token>
```

然后在 karakeep 里触发一次重建索引，它会把每一条书签经 `addDocuments` 推过来。**不读它
的数据库，不耦合它的 schema。** karakeep 抓好的正文会跟着一起进来，正好跳过第一次建索引
最慢的那一步。

顺带买到的最有价值的东西：`POST /karakeep/search` 接受 `config` 参数，所以**消融可以在
一个真实 karakeep 库上跑**，而不是只能在生成语料上跑。上面每一个数字都来自生成查询集，
这是第一条能拿真实使用去校验它们的路径。

装法、逐字段映射、以及它诚实的短板（多用户过滤发生在排序**之后**，以及 TypeScript 那一
侧不在本仓库 CI 里构建）都写在 [`docs/karakeep.md`](docs/karakeep.md)。

**这条路线同时意味着这个项目不再自己造扩展、抓取器和 UI。** 那三样 karakeep 已经做得
更好了。

## 命令

```
facetmark import [PATH]       Netscape HTML 或 Chrome JSON；不给 PATH 就读浏览器配置目录
facetmark browsers            列出能导入的本机浏览器配置
facetmark index [--no-fetch]  抓取、富集、嵌入、意图过滤、切会话、建边
facetmark reindex             全部重建，保留书签本身
facetmark search QUERY        终端里搜（--config 指定档位，--explain 看每一分从哪来）
facetmark show ID             单条书签的四个面和健康状态
facetmark sessions            重建出来的保存会话，最新的在前
facetmark health [--check]    链接健康汇总，或者跑一轮探测
facetmark stats               索引规模与覆盖率
facetmark serve               本地 HTTP 服务，给扩展和集成用
facetmark mcp                 stdio 上的 MCP server，给 Claude Desktop 之类的客户端
facetmark token [--rotate]    扩展配对用的令牌
facetmark demo / eval         离线合成语料，和 A–E 消融台
```

## 这个项目守的边界

**从不修改你的书签。** facetmark 读浏览器的导出或配置目录，只写自己那个 SQLite 文件。
一个会改写你书签的工具，是一个你没法安全卸载的工具。

**从不删除任何东西。** 链接健康只报告，不清理。死链留在库里、继续可搜，「墓地」端点存在
是为了让 UI 能**提供**一个清理视图，绝不是为了让清理自动发生。本地探测失败永远不足以判定
「页面已死」——从一个 socket 看过去，**被墙和被删长得一模一样**。

**抓取默认是礼貌的。** 遵守 `robots.txt`，单主机两个并发、之间至少隔 0.5 秒，User-Agent
如实标明工具身份，`Crawl-delay` 最多认到 5 秒。抓你自己存的页面，流量仍然落在别人的服务器
上；默认值假设你宁可慢一点也不愿意做个混蛋。

**只有意图面会把正文发出去**，而且只发到你自己配的那个端点。设
`FACETMARK_EMBED_BACKEND=local` 并跳过 `index` 的富集步骤，就能让全部数据留在本机。

**本地服务是令牌配对的。** `facetmark serve` 只绑 127.0.0.1 并生成一个配对令牌，除 `/`
和 `/health` 外每一条路由都要它。`facetmark token --rotate` 让旧令牌立即失效。

## 目录结构

```
src/facetmark/
  db.py normalize.py text.py sessions.py edges.py providers.py config.py
  importers/   Netscape HTML + Chrome JSON，时间戳单位自动判定
  fetch/       双通道抓取、三级正文抽取、浏览器兜底队列
  enrich/      摘要、doc2query 意图、自洽性过滤、向量
  search/      查询理解、逐面召回、RRF、上下文、图扩展、衰减、重排
  health/      本地探测、外部交叉验证、综合判定、只追加的存储
  bridges/     别的应用的插件契约（karakeep）
  eval/        合成语料 + A–E 消融台，带 bootstrap 置信区间
  service.py api.py mcp_server.py cli.py
integrations/  karakeep 搜索插件（TypeScript，不在本仓库 CI 里构建）
extension/     MV3，TypeScript，esbuild
eval/queries/  冻结的查询集：W1 真实库、W2/W3 留出集、门控精确率探针
docs/          一次实验一份文档，包括失败的那些
scripts/       语料生成、判定脚本、处置表
```

## 项目状态

**没做完的东西和为什么没做，全部写在 [`ROADMAP.md`](ROADMAP.md) 里。** 简短版：W1 和 W4
都跑完了，两个都是负面结果；W2/W3 的六个开关在一批全新的 616 条查询上判过了；唯一改了
默认值的那一个后来又被一批对抗性探针推翻、默认值退回。**融合本身仍然没有修好。**

贡献规则见 [`CONTRIBUTING.md`](CONTRIBUTING.md)，信任边界见 [`SECURITY.md`](SECURITY.md)，
版本历史（包括每一个默认值为什么改）见 [`CHANGELOG.md`](CHANGELOG.md)。

## License

MIT。
