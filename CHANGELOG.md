# 变更记录

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

## [未发布]

只有文档、脚本与评测数据，代码行为没有任何改动。

### 新增（W4 续：那条「标题修复」假设的分层复核）

- **`docs/w4-intent-strata.md` + `scripts/intent_strata.py` + `eval/intent-strata.json`。**
  W4 判读留下的假设是「意图抽取的价值集中在标题退化的页面上，应当当标题修复用」，原
  计划要等 W2 的新查询集，实际上用已有数据就能判。**协议是单独一次提交推送的**，结果
  在之后追加，先后顺序可以从 `git log` 外部核对，不再只能凭作者自述（W4 那一页只能）。

  判定：**不支持**。标题退化层（≤3 词，n=213）的 C_nolex − A 是 −3.76pp，CI95
  [−8.45, +0.94]；交互项 +3.01pp，CI95 [−3.38, +9.40]。把「退化」收紧到单词标题时反而
  负得最狠（−7.87pp，n=89），与假设要求的单调关系相反。意图面本该擅长的 `q_vague` 在
  两层上完全一样（−7.81 对 −8.33）。

  两条全库证据（覆盖 730 篇查询集碰不到的短正文页面）：意图面与内容面的邻域重合度在
  贫瘠页面上是 28.3%，跟全库的 26.9% 没区别——它没说出内容面缺的东西；而这些页面上
  **62.4% 的意图用词在页面上根本不存在**（正常正文只有 21.3%，词面比对，是上界）。
  **页面自述充分时意图面稀释内容面，页面自述贫瘠时它编造。**

- **发现 W1 查询集有一个 30% 的覆盖盲区。** 479 条查询的 gold 页面正文最小 802 字符、
  中位数 5,651，而库里 30.7%（730/2,376）的页面正文不足 500 字符，**一条查询都没覆盖
  到**。这是查询生成方式的必然结果（查询从正文生成），后果是 W1 的全部结论只在「有充分
  正文的页面」这个子集上成立。已写进 `ROADMAP.md`，作为 W2 新查询集的硬性要求。

### 修正

- **`docs/w4-intent-read.md` §1.5 的事实错误。** 原文写「W1 的 479 条查询里有一部分就是
  从 `intent_query` 派生的」，这是错的：`scripts/corpus/gen_queries.py` 只读 `bookmark`、
  `content.body_text` 与 `bookmark_session`，`finalize_queries.py` 只读 `bookmark` 的 id
  与 `url_norm`，两者都不碰意图表。真实关系是 `q_vague` 与 `intent_query` 同为一个 3B
  模型对同一页正文的两次生成——这是**利好意图面**的相似性偏差，不是泄漏，方向与原文
  暗示的相反。

## [1.1.0] - 2026-08-03

W2 的三个开关默认全部关闭，那部分行为与 1.0.0 逐位一致；**发版是因为另外两件事不是**：
`edges.SEMANTIC_MAX_DISTANCE` 从 0.60 改成了报告实际测过的 0.93（重建图的人会得到
一张不同的图），`EdgeStats` 从报「提交了多少条」改成报「表里有多少条」。这两条都在
下面「变更（行为改动）」里。W4 的判读是文档，不改代码。

Chrome 扩展这一版没有改动，仍是 1.0.0。

### 变更（行为改动）

- **`edges.SEMANTIC_MAX_DISTANCE` 从 `0.60` 改为 `0.93`：让代码跑的是报告测过的那套配置。**
  W1 评测按**事先固定**的规则（随机文档对距离分布的第 1 百分位，两位小数；2,821,500
  个采样对上得 0.9342）把语义边距离上限重算为 0.93，语义边 80 → 7,014 条，覆盖率
  1.4% → 79.4%，§5 与 §9.1 的每一个数字都是在那张图上测的。**但源码里的常量一直停在
  0.60**——装上这个包能复现报告的文字，复现不了报告的配置，而 §9.1 唯一被认定为严格
  帕累托改进的机制（图扩展，+2.09pp）正好是靠这张图测出来的。

  这个数是**嵌入模型的属性**，不是本包的属性：它标的是「无关文档在 bge-m3 上从哪里
  开始」。换嵌入模型要按同一条规则重新推，不要沿用 0.93。

- **`build_semantic_edges(max_distance=...)` 现在在调用时解析默认值。** 它原先写成默认
  参数，在 import 时就把常量绑死了，于是设 `edges.SEMANTIC_MAX_DISTANCE` 完全无效、
  且不报任何错——一个不能转的旋钮。

- **`EdgeStats` 报的是表里的行数，不再是提交上去的行数。** `_insert()` 原先返回
  `len(pairs)`，而 `ON CONFLICT DO UPDATE` 会把重复提交的同一条悄悄合并，所以统计值
  可以声称一些表里并不存在的边，而且这种计数永远不可能和写入结果打架。随报告发布的
  库快照就卡在这个缝里：日志记 19,763，快照里 19,648，谁也说不清哪个对（重建之后确认
  日志对、快照短）。现在改成查表计数，并加了「统计值必须逐类等于表内行数」的不变量测试。
  发布的那份快照也已经换成重建之后的（26,697 条，就是评测跑过的那张图）。

### 变更

- **修正包元数据里的项目简介。** `pyproject.toml` 的 `description` 还在写「四个正交
  检索面用 RRF 融合」——这正是 W1 闸门否决掉的那套说法，而且它是 PyPI 页面和
  `pip show` 会展示的第一句话。README 里的负面结论如果只写在 README 里，安装包的人
  看不到。同时把 `Development Status` 从 `3 - Alpha` 改成 `4 - Beta`：声称 1.0.0
  又标 Alpha 是自相矛盾的。

- **补齐开源项目的社区文件**：`CONTRIBUTING.md`、`SECURITY.md`、三个 issue 模板
  （检索质量 / bug / 检索改动提案）与 PR 模板。检索类模板里写进了这个项目特有的
  收敛条件：变更要带配对统计（McNemar + bootstrap CI）而不是均值，而且**不能在提出
  该假说的那一批查询上拟合**。PR 模板留了一行——把数字变差但能解释原因的改动是欢迎的，
  照实写，不用包装成胜利。

  `SECURITY.md` 明确了三处与常规 web 应用不同的信任边界：`serve` 无鉴权且只绑
  loopback（按设计，不是漏洞）；`crawl` 是刻意保留的 SSRF 形状能力，URL 来自你自己的
  导出文件，所以不要拿别人给的书签文件去抓；抓回来的正文会进模型 prompt，构造页面可以
  尝试提示注入，影响面限于污染你自己库里的摘要与候选查询字段。

### 新增（W4：意图面到底成不成立——做完了，答案是不成立）

- **`docs/w4-intent-read.md` 与 `eval/w4-intent-read.jsonl`：协议先行的 50 条意图判读。**
  抽样种子、三档标准、判定阈值全部在看数据之前写死并落盘，结果才追加进同一份文件。
  结果是**会 38% / 勉强 42% / 不会 20%**，按预注册规则（「会」< 50%）判为**理念问题，
  不是 3B 模型不够大**。

  值钱的不是那个百分比，是失败的形态。彻底错的只有 20%——编造使用场景、与页面内容
  不符、把发文域名当产品名——这一档换更大的模型能修。占最多的 42% 是**在已知答案的
  前提下反推**：逐字复制标题、产品名加泛后缀、抄页面里的专有名词。更大的模型只会写出
  措辞更漂亮的标题改写，因为它能看到的只有这一页，写不出「这个人当时为什么存它」。
  判读者是本系统的 LLM 助手而不是这个库的主人，所以 38% 是**上界**。

  **没有据此改任何默认值**（默认档本来就只开内容面），也没有删掉意图抽取：19 条
  「会」里有 11 条的标题是「Demo」「维基百科」「介绍文章」这类零信息量标题，所以留下
  一条待测的小假设——意图抽取的价值可能集中在标题退化的页面上，即把它当**标题修复**
  而不是当一个检索面。

- **新增 `scripts/facet_overlap.py`：量一量第二个面到底看见了第一个面看不见的什么。**
  用同一个向量（每篇书签自己的内容向量）同时探内容面与意图面，去掉探针文档自身，
  比两个 top-10 邻域。全库 2,376 个探针：意图面与内容面重叠 **26.9%**，一个真正不同
  的面（`lex_seg`，用标题探）只有 10.6%，随机是 0.4%；2,367 个探针（99.6%）离自己
  内容向量最近的意图向量，就是它自己生成的那几条。意图面不是内容面的复制品，但它与
  内容面的相关性是别的面的 2.5 倍，而 W1 里把它加到内容面上是 −5.43pp——交回来的是
  「四分之一重复 + 四分之三不更好」。脚本只读库，不需要模型，也不碰查询集。

### 新增（W2 的三个开关，默认全部关闭）

- **`Config.weight_overrides` 与 `Config.context_gate`。** W1 报告 §9.4 列的前两条待办
  各需要一处结构改动，现已落地并有测试守卫，但**默认值一律保持关闭**：验证它们的
  证据只能来自没有提出过这两个假说的查询集，而现有 479 条已经用掉了。

  `weight_overrides` 是 `tuple[tuple[str, float], ...]` 而不是字典——`Config` 是
  `frozen=True` 的 dataclass，字典字段会让 `hash()` 抛异常。属性 `facet_weights`
  把覆盖值叠在 `DEFAULT_FACET_WEIGHTS` 上；`search()` 的融合调用改读它，未设覆盖时
  与原来逐位相同。`context_gate` 走 `Config.wants_context(understanding)`，只有在
  `context=True` 且查询被判为情景型时才应用上下文乘子。

- **三个探索性档位**：`A_gatedctx`（A_ctx + 门控）、`D_gated`（D + 门控）、
  `C_lowlex`（C，`lex_seg` 0.3 / `lex_tri` 0.2）。可用 `--config` 直接调用。
  **本版本不给这三档的任何实测结论**，权重值是拍的不是拟合的。

- **`Config.abstain_margin`：让没有意见的面弃权。** W1 报告 §9.4 第 1 条把「候选门控」
  和「修融合权重」并列。动手前先把 §4.1 记的失效场景照原样算了一遍，结果**否掉了
  「候选门控」的字面读法**：肇事的错误文档站在两个弱面的第 1 名，弱面砍到只剩 3 条
  它都还在，融合结果一位不变。深度上限砍的是第 11 到 50 名，压根不是出事的地方。
  详见 `docs/gate-w1.md` §9.6 的对照表。能修的只剩降权和弃权两条。

  弃权的判据必须是**面内**的：bm25 是无界对数量纲，sqlite-vec 报的是 L2 距离，
  面间分数不可比，任何绝对阈值都要按面、按语料、按语言重标定。所以用一个对仿射
  变换不变的量：`confidence = (best − median) / (best − worst)`。顶端孤峰立于平地
  → ≈1.0；顶端只是一堆并列之一 → ≈0.0（这个面在枚举，不在排序）。两个安全阀：
  少于 3 条结果的面永不静音；弃权**绝不清空结果**，全员低于阈值时保留置信度最高者。
  `0.25` 是拍的，不是拟合的，本版本不给它任何实测结论。

- **响应体新增 `facet_confidence`。** `SearchResponse` 与其 `as_dict()` 现在带每个面的
  置信度，无论该面是否被静音都记录，便于事后审计到底静音了谁。

- **新增 `*_scored` 系列检索函数**：`lexical_lists_scored`、`vector_lists_scored`、
  `content_list_scored`、`intent_list_scored`（均从 `facetmark.search` 导出，另有
  `vector_lists_from_vec_scored`）。原先四个面在返回前就把分数丢了，因为 `rrf()`
  只吃 id 列表；弃权需要分数才能判。原函数改成剥分数的薄包装，有测试守卫两者名次
  逐位一致。`abstain_margin = 0.0` 时管线走的仍是原来那条逐字未改的分支。

- **探索性档位 `C_abstain`**（= C + `abstain_margin=0.25`）。

- `Config.as_dict()` 现在带上 `weight_overrides`、`context_gate` 与 `abstain_margin`
  三个字段。


## [1.0.0] - 2026-08-03

### 变更（行为改动，影响调用方）

- **默认检索配置从「四面融合 + 上下文 + 图 + 重排」改为「内容面 + 图扩展 + 时间衰减」。**
  W1 决策闸门（`docs/gate-w1.md`，2376 篇真实网页 / 479 条查询 / 真实 3B 模型与
  bge-m3）三条预注册判据全部未通过，且发现融合本身在损害检索：纯内容面在内容型查询
  上的 Recall@5 是 95.9%，加上任意一个更弱的面就掉 5.4pp（McNemar p<0.01）。
  留一法探针进一步排除了「词面特别坏」这个归因——只加意图面、不加词面，损失完全相同
  （均为 −5.43pp）。成因是平权 RRF 加每面无条件 50 条候选，让弱面上的巧合
  （`1/61 + 0.7/61`）盖过强面上的确信（`1/61`）。

  `graph` 与 `decay` 留在默认里：图扩展对排序指标**逐位不变**，只在 `recall@5+exp`
  上 +2.09pp（10 赢 0 输，p=0.0019），代价 9 毫秒，是全研究里唯一的严格帕累托改进。
  上下文乘子被关掉：单独打开时情景型查询 +8.14pp（14 赢 0 输）但内容型 −9.94pp
  （1 赢 18 输），必须先按查询类型门控才能开。重排被关掉：p50 从 148 毫秒涨到
  45.4 秒，换回来的 R@1 只是融合自己造成的损失的 45%，而那份损失现在已经不存在了。

- **新增 `default_config(settings=None, provider=None)`**（`facetmark.search`）。
  `search()` 的 `config` 参数默认值由 `FULL` 改为 `None`，在 provider 解析之后才决定
  跑哪一档。原因是 mock provider 的 embed 是词级特征哈希，内容向量在这种库上就是
  噪声——**没有配 API key 的部署如果直接用新默认会得到空结果**。因此在「注入了
  MockProvider」或「settings 里 `use_mock_provider` 为真 / 没有 `api_key`」时回退到
  全融合档 `FUSED`，与 `get_reranker()` 无 key 时回退 `OverlapReranker` 的逻辑同构。
  显式传入 `config=` 的调用方不受影响。

- **`SearchResponse.config`（以及 HTTP `/search` 响应里的 `config` 字段）现在报的是
  实际跑了哪一档，不是调用方点了哪一档。** 请求 `config: "full"` 的 mock 部署会收到
  `"fused"`。依赖这个字段回显请求值的客户端需要改。

- CLI / HTTP API / MCP 里 `config` 为空或 `"full"` 时走 `default_config(...)`；
  `"A"`–`"E"` 等具名档位仍按名字精确取，不受默认变更影响。

### 新增

- **探索性档位** `EXPLORATORY`（`A_graph` / `A_ctx` / `C_nolex` / `D_nolex`）与档位表
  `ALL_CONFIGS`、`PROFILES`。预注册的 A–E 阶梯是**加法**的，因此只能回答「加 X 有没有
  用」，回答不了「拆掉 X 会怎样」；这四个档位是补这个盲区的留一法探针，结论记在
  `docs/gate-w1.md` §9（明确标注为探索性、非预注册）。`CONFIGS`（A–E）本身一个字节
  都没动，测试里有专门的守卫断言防止它被事后改写。

- `scripts/mcp_e2e.py`：把 MCP 服务端当成助手那样驱动一遍——真的 fork 一个子进程、
  走 stdio 上的 JSON-RPC 握手、把九个工具全调一遍、把三个资源全读一遍，共 22 项检查。
  进程内的 `create_server()` 测试查不出两类故障：导入链上任何一处 `print` 都会污染
  协议流，以及 FastMCP 无法为某个返回标注生成 schema。两者都只在真管道上暴露。
  用的是临时目录里的 mock 库，不联网、不需要模型。

- `fetch/robots.py`：抓取前按 host 取一次 `robots.txt` 并遵守，命中 `Disallow` 记为
  `robots_disallowed` 并跳过，理由写进抓取存储；支持 `Crawl-delay`。默认开启
  （`respect_robots = True`）。开源的爬取组件缺这个不合格。
- 评测报告落**逐条判决**：`report["queries"]`（每条查询的 `qtype` / `target_id` /
  `note` / `text`）与 `report["outcomes"][rung]`（每条的 `rank` / `expanded` / `ms`，
  与查询列表同序）。只有汇总的报告没法按事后才想到的切片重算，而这里最要紧的切片
  （情景查询按时间表达方式分层）恰好是这样一个切片。
- 评测新增辅助指标 `recall@5+exp`：命中主列表或出现在一跳扩展组即算找到。
  `SearchResponse.ids` 只含 `hits`，扩展组单独渲染、刻意不与主列表交织，因此按主
  指标口径图扩展对 Recall@k 的贡献恒为 0；不并列这个数字就看不出 D−C 的差值到底来自
  上下文乘子还是图扩展。**闸门判据仍只看 `recall@5`。**
- `facetmark eval --concurrency N`：rung E 每条查询要付一次 LLM 重排，几百条查询打
  本地 CPU 端点是数小时的套接字等待。结果按下标写回，因此配对 bootstrap 依赖的顺序
  不受完成次序影响；并发 >1 时报告里带 `latency_caveat`，说明 `p50_ms/p95_ms` 是排队
  时间而不是用户可感延迟。
- `enrich_concurrency` 配置项（默认 4）。
- `scripts/corpus/`：W1 评测语料与查询集的完整脚手架（采集、抽样、抓取、索引、查询
  生成、候选池探针、闸门分析）以及 2376 条语料的 `manifest.jsonl`。正文不入库，任何
  人可按 manifest 重抓复现。
- `docs/eval-w1.md`：W1 评测报告（装置、语料、语料与真实库的五处偏离、查询集构造、
  泄漏探针、闸门判定）。
- **schema 迁移机制**：`migrations.py` 里一条有序 `MIGRATIONS` 列表，第 N 项把库从
  N−1 迁到 N；每项独立事务、最后一句写 `meta.schema_version`，中断只会停在最后一个
  完整应用的版本上。`open_db()` 自动应用（可 `migrate=False` 关掉改为报错），首次迁移
  前用 `VACUUM INTO` 留一份 `*.bak-v<旧版本>` 快照。库版本高于代码时拒绝打开而不是
  猜——降级数据没法保证不丢行。新增 `facetmark migrate [--check] [--no-backup]`。
  `SCHEMA_VERSION` 由迁移列表推导而非另行声明，且有一条测试逐列比对「全新库」与
  「迁移后的库」，这两处漂移正是该机制要防的那类缺陷。
- 浏览器队列退避重试：`fetch_queue.next_attempt_at`（本仓库第一条真实迁移，v1→v2）。
  失败后按 5 分钟 → 30 分钟 → 2 小时递增等待，期间不再派发。新增
  `queue_waiting()` 并在 `/queue/next`、`/queue/stats`、`facetmark stats` 中单列，
  免得「pending 40 但租不到任何东西」看起来像 bug。
- enrich 在回复被上下文窗口截断时用半长正文重试一次，次数记为
  `EnrichReport.rescued_by_shorter_body`。

### 新增

- **`facetmark import` 不带参数时自动定位浏览器实时配置文件**，新增 `facetmark browsers`
  列出找到的配置。`discover_bookmark_files()` 此前写好了、注释里写着「Windows 是首要
  目标平台」，但全仓库没有任何调用点——Windows 用户的第一条命令是手敲
  `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Bookmarks`。找到多个配置时**不猜**：
  列出候选并以退出码 2 要求明确指定，导入错人的收藏夹比多敲一条命令糟糕得多；一个都
  没找到时打印**搜过哪些目录**，而不是一句「not found」。
- 平台表拆到 `importers/discovery.py` 并补齐 Opera（Windows 上在漫游
  `%APPDATA%` 而不是 `%LOCALAPPDATA%`，且 `Bookmarks` 直接放在渠道目录里、没有
  `Default/` 一层——解析器的文档字符串一直声称支持 Opera，发现表里却没有它）。
- **`facetmark index` 现在整条链路都是增量的，并有端到端测试钉住这条保证**
  （`TestIndexingTwiceIsNotPayingTwice`）：同一个库跑第二遍，模型调用数为 **0**——
  不重新 enrich、不重算内容向量、不重打意图探针、不重嵌意图向量。计的是**文本条数**
  而不是请求数，因为嵌入是批的，一次请求六十四条就是付了六十四条的钱。逐个阶段各自
  增量与「整条命令增量」不是同一个命题：只要有一个阶段全量重扫，整条命令就退化成全量
  重跑。原计划里的 `facetmark index --since` 因此**不做**——它要解决的问题已经不存在，
  多一个标志只会多一个会和 `force` 语义打架的旋钮。（会话与边每次都整体重建，但那是
  纯本地 SQL，不花模型调用。）
- **扩展有测试了**（`extension/test/`，`npm test`，已进 CI）。不引入任何新依赖：
  用 node 22 自带的 `--test` 跑，用 `--experimental-strip-types` 直接加载**出厂的
  那份源码**而不是编译副本。代价是源码必须是「删掉类型就能跑」的子集，所以
  `tsconfig.json` 打开 `erasableSyntaxOnly`（构造器参数属性、`enum`、`namespace`
  这些 node 会当场拒绝的写法编译期就报错），`ApiError` 相应改写。`test/stub.ts` 是
  一份手写的浏览器替身，只覆盖 service worker 真正调用的那几个 API——用不到的一律
  不写，这样将来多出一处对浏览器的依赖会在测试里变成 `TypeError`，而不是在真机上
  变成沉默。16 条测试覆盖队列算术与整条 channel B 抓取循环的失败路径。

### 修复

- **索引驱动脚本会在一个永远失败的页面上空转到天荒地老。** `scripts/corpus/run_index.py`
  分块调用 `enrich_all` 直到「这一轮什么都没处理」为止，而它把「什么都没处理」写成了
  `enriched + failed == 0`。失败**也算数**。于是一个确定性失败的页面——提示词长度就是
  塞不进上下文的那种——每一轮都会被重新选中、重新失败、重新把计数器顶到 1，循环
  永不退出。实测在第 12 轮之后空转了 16,761 轮、十四个小时，后面的向量、意图、会话、
  边四个阶段一个都没跑。改为按 `enriched == 0` 判定停滞，连续 `--stall-rounds`（默认 3）
  轮没有任何一页成功就停下，并把卡住的页面逐条打印出来。瞬时故障仍有重试余地，
  确定性故障不再绑架整条流水线。

- **图扩展从来没有出过一行。** `search()` 把「已经展示过、不要重复」的排除表设成了
  **整个融合候选池**（`exclude=[f.doc_id for f in fused]`），而不是**真正展示给用户的
  那几条**。这两个集合差着一个数量级：每个向量面无论相不相关都会交回
  `candidates_per_facet`（默认 50）个近邻，于是候选池是 50–150 篇，`hits` 只有 10 条。
  更要命的是方向：一篇文档之所以是某条命中的图邻居（同一次会话存的、语义互为近邻），
  恰恰意味着向量面也会把它捞进候选池——排除池和图通道几乎完全重合。小库上
  `expanded` 恒为空集，大库上只剩下「没有任何面检索到」的那些，也就是最没有资格
  被展示的那些。改为 `exclude=[h.bookmark_id for h in hits]`：要挡的是用户**看见**的，
  不是检索器**掂量过**的。
- **这个缺陷带着三条常绿测试活了下来。** `test_only_configs_d_and_up_produce_an_expansion_group`
  断言的是 `isinstance(d.expanded, list)`（空表也是 list）；
  `test_the_expansion_group_never_overlaps_the_main_results` 断言 `isdisjoint`
  （空表与谁都不交）；`test_an_expanded_row_says_which_bookmark_it_came_from`
  外面裹着 `if exp:`（空表就整段跳过）。而它们共用的 `indexed` fixture 是三篇分属三个
  不同域名、彼此无关的页面，构建的 `same_domain` / `anchor_sibling` / `supersession`
  三种边一条都建不出来——`edge` 表是空的。三条测试从来没有真正执行过这个功能。
  现在新增 `graphed` fixture（显式插入 session 与 semantic 边），三条断言全部改成
  会失败的形式，并补上 `test_a_neighbour_the_retriever_also_considered_is_still_expandable`
  与 API 层的 `test_a_graph_neighbour_actually_reaches_the_client`，把回归钉死。
- `expand()` 的 `max_seeds` 只限制**走哪几条命中**，不负责**挡住哪几条命中**。当
  `limit > DEFAULT_SEEDS` 时，第 11 条以后的命中不在种子里、也就不会被自动屏蔽，
  可能在「相关」分组里紧挨着自己再出现一次。新增
  `test_a_hit_past_the_seed_cap_still_has_to_be_excluded_by_name` 说明为什么管线必须
  显式传 `exclude`，而不能依赖种子屏蔽。

- **扩展把队列里「等浏览器」的条数报错了。** 弹窗和选项页都把 `/queue/stats` 的
  `pending` 直接印成「waiting for the browser」。服务端的 `waiting` 是 `pending` 的
  **子集**（在退避窗口里、当下租不出去的那些），两个数分开报的理由就写在
  `fetch/store.py` 的 docstring 里：免得「pending 40 却租不到任何东西」看起来像 bug。
  扩展把这个区分丢掉，等于把服务端特意防住的困惑又装了回去——用户点「fetch queued
  pages」，得到「processed 0 page(s)」，旁边的数字纹丝不动，而实际上什么都没坏。
  改为 `summarizeQueue()` / `describeQueue()` 一对纯函数，把 `ready`（现在就能取）、
  `waiting`（在等时钟）、`leased`（已派出去）、`failed`（不再重试）分开说。
- **选项页那句「processed N page(s)」没有人看得见**：写完立刻 `await refresh()`，
  下一行就把它覆盖掉了。`refresh(note)` 现在接住这句话并与状态行拼在一起；channel B
  关着或暂停时不再发消息，直接说明是哪一种。
- **一个打不开的标签页会把整条 channel B 卡死到 service worker 重启为止。**
  `chrome.tabs.create` 失败时给回调传的是 `undefined` 并置 `chrome.runtime.lastError`，
  而 `renderInTab` 上来就读 `tab.id`——`TypeError` 抛在一个 Promise 看不见的回调里，
  于是那个 Promise 永远不 settle，`drainQueue` 的 `await` 永远不返回，`draining`
  永远是 `true`。现在先查 `lastError`，并且把 20 秒的超时**在请求标签页之前**就装上
  （原来装在回调里，恰好漏掉了「回调根本不来」这一种）。竞态输给超时时创建出来的
  标签页也会被关掉。
- **抓取失败时扩展不区分「服务端没开」和「配对令牌被拒」**，两者都被同一个空
  `catch` 吞掉。前者下一次闹钟会自己好，不值得打扰；后者永远不会自己好，而没有任何
  信号的 channel B 和「没活可干的 channel B」在屏幕上长得一模一样。令牌被拒现在会亮
  角标。
- 扩展判定「页面没读到正文」的口径与服务端不一致：客户端只看 `!text`，服务端看
  `text.strip()`。整页空白会白跑一个来回，并且把扩展本来知道的原因（页面没渲染出
  东西）换成服务端的泛化原因。客户端改为同样先 `trim()`。 `SearchResponse.took_ms`
  在服务端是分阶段耗时的字典（`understand` / `facets` / `total` …），扩展里却声明成
  `number` 直接插进模板字符串。`request<T>` 是 `await res.json() as T`——一次不做
  检查的强制转换，TypeScript 会相信任何写在那里的形状，所以 `tsc` 和 CI 的
  `--noEmit` 全都是绿的。同一处强制转换还藏了两个字段谎报：`Hit.via` 声明为必有的
  `string`，服务端只在**扩展组**的行上给 `via`，而且它是 `number`（来源书签 id）；
  `Hit.badge` 服务端从不下发。结果条目下面那行「为什么命中」永远只有域名和文件夹，
  RRF 特意保留的 `facets` 归属信息在最后一步被丢掉了。现在类型按服务端实际形状改写，
  弹窗渲染 `took_ms.total` 与 `facets`（`content`→about、`intent`→asked as …）。
- **一跳图扩展在扩展里根本没有渲染。** 服务端一直在返回 `expanded`（刻意与 `hits`
  分开、不交织），弹窗只读 `hits`——图这一面在真实 UI 里完全不可见，与它在评测主
  指标上恒为 0 是同一个形状的问题。现在扩展组以「saved around these」为标题单列，
  每行用 `via_kind` 说明是靠哪种边到达的。
- **Windows 上把搜索结果重定向到文件必崩。** Windows 控制台与 Python 之间说的是
  UTF-8，但**重定向**后的 stdout 用的是 ANSI 代码页；一条中文标题就让
  `facetmark search > hits.txt` 抛 `UnicodeEncodeError`，退出码 1，什么也拿不到。
  一个专门用来找中文收藏的工具，在中文标题上崩溃，这个缺陷的严重性高于它的修复难度。
  现在 `facetmark.cli` 导入时会加固 stdout/stderr：非 UTF-8 的流升到 UTF-8（重定向的
  目标是文件，文件本来就该是 UTF-8），显式设了 `PYTHONIOENCODING` 的按用户的选择保留、
  只把错误处理从 raise 降级为 replace——标题糊了还能看出命中的是哪一条，堆栈什么都看不出。
  同一缺陷在**没有 locale 的 POSIX 进程**（cron、systemd、容器）里一模一样，所以回归
  测试在 Linux CI 上就能跑：子进程用 `LC_ALL=C` 起一个 ASCII stdout，先断言裸解释器
  确实会崩，再断言只要 `import facetmark.cli` 就不崩。
- **中文写法的绝对年份完全解析不出时间窗。** `understand._ABS_YEAR` 原为
  `\b(19[89]\d|20[0-4]\d)\s*年?\b`；Python 把 CJK 算作 `\w`，所以「2023年那会儿」
  末尾的 `\b` 永不成立。改用前后向断言，允许 CJK 邻接，仍拒绝 `es2015` / `2024px` /
  `vue 2` 这类标识符。既有测试用的是「2023 年的会议记录」（数字与「年」之间有空格），
  恰好绕开了这个缺陷，这是它长期未被发现的原因。
- 相对时间支持中文数字与英文拼写数字：「三个月前」「十天前」「a couple of weeks ago」
  此前都解析不出。
- `run_rung()` 原先用 `[o for o in outcomes if o is not None]` 静默过滤缺失结果，
  会缩小召回率的**分母**，把一次失败变成一个好看的数字。改为硬失败。
- **静默的 schema 漂移。** `SCHEMA_SQL` 全是 `CREATE TABLE IF NOT EXISTS`，
  `init_db()` 只在没有版本号时写一次、之后从不校验；旧版本写的库能干净地打开，直到
  第一条用到新列的查询才炸，而那时报错点离原因已经很远。现在开库即校验。
- `providers._post()` 重试耗尽时只打印 `failed after 3 attempts:`——httpx 的多个超时
  异常 `str()` 为空。改为带上异常类名。
- **一页把提取器搞崩会连坐整批抓取。** `fetch_many` 用的是不带 `return_exceptions`
  的 `asyncio.gather`，而 `extract()` 的异常在 `fetch_one` 里没有被接住——一个畸形
  页面足以让同批已经抓好的结果全部丢掉，并且破坏调用方用来对齐 bookmark id 的
  「结果按输入顺序返回」契约。现在提取失败记为 `empty`（请求是成功的，是我们的解析
  器没解析出来，真浏览器有机会做得更好），批内任何未预料到的异常记为 `unreachable`
  并留在原位。
- **内容向量一旦写入就永不刷新。** `embed_content(force=False)` 的候选集条件是
  `b.id NOT IN (SELECT bookmark_id FROM vec_content)`，只问「有没有向量」，不问
  「向量是不是当前文本算出来的」。先 `index --no-fetch` 建库、之后再 `crawl` 补正文
  的用户，内容向量会永远停在只有标题的那一版，而搜索排的正是这个向量；`reindex`
  走 `force=True` 能救，增量路径救不了，也没有任何地方会说它过期了。
  迁移 v3 新增 `vec_content_meta`，记下每条向量所嵌入文本的 sha256；`force=False`
  现在比对指纹，不一致就重算，`facetmark stats` 报 `content_vectors_stale`。
  指纹里混入 `CONTENT_RECIPE`，所以改动 `content_text()` 的拼法本身就会让全部旧向量
  作废。库里已有的向量来源不明，迁移刻意不做回填——它们记为过期，下一次 `index`
  重建，这是这个版本唯一诚实的答案。
- **抓取要等整批跑完才落库。** `crawl()` 原先 `await fetch_many(...)` 拿到全部结果
  之后才逐条 `save_result`。抓两千条书签是几十分钟别人的带宽，在 95% 处 Ctrl-C、
  OOM 或任何一个未预料到的异常，已经抓好的正文全部作废，下一次运行把这些请求重发
  一遍。现在结果一到就落库（连接是 autocommit，写下即提交），中断后 `pending_targets`
  只会给出真正还缺的那些。结果到达次序不再等于输入次序，因此 bookmark id 改为按 URL
  匹配而不是按位置 `zip`。
- **每条意图查询的向量都买了两遍。** `filter_intents` 给每个候选算一次嵌入用来做
  自查探针，算完就丢；紧接着的 `embed_intents` 又把幸存下来的那些原样重算一遍——
  同一段文本、同一个模型。2,376 页的库上这是约 9,500 次多余的嵌入调用，在计费端点
  上就是意图面嵌入账单多出一半。现在过滤器直接把探针用过的向量存下来（只保留还有
  可能被留下的候选，峰值内存由通过集而不是候选集决定），`IntentReport.vectors_written`
  报数，其后的 `embed_intents` 无事可做。`force=True` 的重算路径不变。
- **增量索引的代价按库的大小算，而不是按改动的大小算。** `filter_intents` 每次
  `facetmark index` 都把库里全部意图候选重新嵌入、重新探针一遍。2,376 页的库上加
  20 条书签，本该是 160 次候选打分，实际是约 19,000 次——本地端点上多花一个多小时，
  计费端点上就是一张不该出现的账单。原因是**库里分不出「打过分被拒」和「从没打过分」**：
  `kept` 默认 0，未命中时 `probe_rank` 为 NULL，两者字节相同，于是唯一安全的默认是
  全都重来。迁移 v4 给 `intent_query` 加 `scored_at`，回填只认证据明确的行（`kept=1`
  或 `probe_rank` 非空），其余留 NULL 再打一次分——分不清拒绝与遗漏时，重打一遍是
  无害的那个方向。同时把「探针」与「取舍」拆开：探针增量，取舍每次全跑。取舍读的是
  已经落库的 `probe_rank`，所以改 `keep_n` 重新裁定整个库不花一分钱，消融扫这个超参
  也就不必反复付费。`IntentReport` 新增 `probed` / `already_scored` 两个计数。
  被提升为保留但本轮没重新探针的候选手里没有向量，由紧随其后的 `embed_intents` 补齐。

### 变更

- `ruff` 依赖加上限 `>=0.6,<0.17`。ruff 在小版本里加 lint 规则，不钉上限意味着 CI
  可能因为一次什么都没改的提交而变红——这里已经发生过一次。抬上限要显式做，并在同一
  个提交里修掉新规则的发现。
- CI lint 范围从 `src tests` 扩到 `src tests scripts`：仓库里存在却不被检查的代码
  是一种慢性欠债。

## [0.1.0] - 2026-08-01

首个公开版本：四个检索面（内容向量、意图向量、分词索引、三元组索引）以 RRF 融合，
上下文乘子，一跳图扩展，LLM 重排，三层链接健康探测，MCP 服务，浏览器扩展，A–E 消融
评测框架。全部本地优先，数据落 SQLite。
