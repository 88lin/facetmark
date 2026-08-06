# 变更记录

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

## [Unreleased]

## [1.6.1] - 2026-08-06

**1.6.0 的文档里留了一个「没查清」的问题。查完了：那个被吞掉的异常是一台自动生产死判定
的机器，而且它一次都没走火。**

1.6.0 跑全库健康检查时，stderr 反复打出 `readability` 的
`ValueError: All strings must be XML compatible`，而报告的 `errors` 是空列表。当时把它
记进局限就放过去了。

追下去发现的链条比预想的长。两条提取层各自 `except Exception: return ""`，于是「解析器
崩了」和「页面真的空了」到下游是同一个值；`probe_one` 拿它跟索引里的正文比，0 对 900
的相似度是 0.0，低于 `DRIFT_SIMILARITY`，返回 `DRIFTED`；`DRIFTED` 在 `DEAD_VERDICTS`
里，于是进冷层，于是在检索里被降权。**一次解析器崩溃会一路变成一次「这页死了」的判定，
而且长得和真实测量一模一样。** 写测试时又发现第二条路径：两层都崩之后 `extract()` 退到
metadata 层把 `<title>` 当正文返回，9 个字符的标题不是空值，连「什么都没提取到」这个信号
都被抹掉了。

**但它没有污染任何已发布的数字。** 把 2,376 行健康记录的 `local_evidence` 解开按判定分桶
数 `body_chars`：58 条 `drifted` 里 `body_chars == 0` 的有 **0 条**。`gone` 那 60 条的 0
来自 `_verdict_for_status()` 提前返回，提取层没被调用。73 条冷层、8 个受损目标、
`ΔRecall@5 = −1.4610pp` 全部成立。上了膛，没走火。

触发输入仍然没查清——控制字符本身不触发（`\x01\x0b\x0c` 两层都正常返回）。不再追：修法
钉的是策略，不是某个 lxml 版本的崩溃输入。

### 修正

- **提取层不再自己吞异常。** `_try_trafilatura` / `_try_readability` 里的
  `except Exception: return ""` 删掉，错误策略上移到编排层：`extract()` 用新的
  `_guard()` 包住每一层，把崩溃记成具名字符串。各层负责提取，编排层负责错误政策。
- **`probe_one` 拒绝从解析器崩溃推出死判定。** 见到 `parse_failed` 就记一条
  `extraction_failed` 证据并返回 `ALIVE`。这跟同一个函数里早就写着的
  「HEAD 说 200，正文重读失败不是页面死了的证据」是同一条原则，之前漏了这一处。

### 新增

- `Extraction.failures: tuple[str, ...]`——崩过的层，记成 `"层: 异常名: 消息"`，不崩就是
  空元组。默认值保证既有构造点不用改。
- `Extraction.parse_failed`——当且仅当有层崩过、且最终 `extractor` 只剩 `none` 或
  `metadata`。**metadata 算「什么都没恢复出来」**：那一层返回的是标题和 meta 描述，把 9
  个字符的标题放到 900 字符的索引正文旁边，相似度和一页被掏空没有区别。崩溃经 metadata
  层洗一遍仍然是崩溃。
- `tests/test_extraction_failure.py`，9 条。其中两条是**对照组**：真的空页、和只有
  metadata 的薄页，必须照旧产生正常判定——没有它们，上面那个修法可以简单地把 drift 检测
  关掉而全部测试仍然是绿的。

### 变更

- 测试 1166 → 1175。

## [1.6.0] - 2026-08-05

**1.5.0 花了一整节论证「默认档里那层死代码的代价是精确的零」。那次测量是在一台从来没有
开机的仪器上做的。这一轮把仪器打开，同一个实验重做一遍，结论翻转。**

`docs/decay-reach.md` §7 的最后一条边界是自己写下的：「健康检查的覆盖率没有量。」这一轮
去查了那一条，发现的不是「覆盖率低」，是 `health` 表**一行都没有**——健康检查器从来没在
那个库上跑过。冷层三条件里靠健康判定的那一半从来没有可能触发。

于是 1.5.0 那个「冷层只有 8 页、0 个目标是冷页、所以代价是零」的结论，测的是一个被静默
禁用了一半的检测器。

跑完健康检查再测：**修那个阈值要付 `−1.4610pp` 的 Recall@5，CI95 `[−2.5974, −0.4870]`，
区间不含零。**那个「缺陷」一直在帮忙。

结论（不改阈值）没变，理由全变了。这个区别不是文字游戏：1.5.0 说的是「这段代码是死的，
删了无所谓」，1.6.0 说的是「这段代码在意外地做对事，而且现在有东西压在上面」。

### 修正

- **`docs/decay-reach.md` 的主结论作废**（全文一字未改，顶部加更正横幅）。作废的是 §5
  「救援阀守着一个不存在的风险」和 §6「收益是零」两处。方法、A/B 干净性论证、配对
  bootstrap 那一节仍然成立——被推翻的是它跑在什么上面，不是它怎么跑的。

- **`ROADMAP.md` 的衰减层条目**从「已量，代价是零」改成「已量，这个意外在做对的事，
  而且它承重」，并新增第三个待测问题（c）：窄化条件 3。

### 新增

- **`docs/decay-instrumented.md`**——完整过程、机制拆解、根因、局限。数据落在
  `eval/decay-reach-checked.json` 与 `eval/cold-census.json`。

  **两个恒真的条件。** 冷层要求「从未打开 + 老于一年 + 有取代证据」三条全中。在这个库上
  `open_count = 0` 对**全部 2,376 条**成立——浏览器书签的 HTML 导出格式里根本不带使用
  遥测，条件 1 不筛掉任何东西。条件 3 的健康判定那一半因为 `health` 表为空同样不可能
  触发。实际工作的只有条件 2 加 supersession 边：全库 14 条有 supersession 出边、其中
  8 条同时够老，这就是 1.5.0 那 8 页的全部来历。

  **把仪器打开。** 库复制一份，`health_enable_external=False`、`save_recovered=False`
  跑一遍全库健康检查，2.1 分钟、2,336 条探测。`save_recovered=False` 是 A/B 干净性的
  关键：它保证只写 `health` 表。逐层验证过——`content`、`edge`、`bookmark` 三张表的深度
  指纹和向量、FTS 全部逐位一致，只有 `health` 从 0 行变成 2,376 行。

  判定分布：alive 1,899 / restricted 200 / unreachable 85 / unknown 74 / gone 60 /
  drifted 58。

  **冷层 8 → 73**（0.34% → 3.07%），构成 `gone 37 + drifted 28 + supersession 8`。
  更要紧的是它第一次碰到了答案：**冷层 ∩ 230 个目标从 0 变成 8**，涉及 19 条查询。

  **ΔRecall@5 = `−1.4610pp`，CI95 `[−2.5974, −0.4870]`**（10,000 次配对 bootstrap，
  seed 20260805）。shipped `0.5860` → reachable `0.5714`。分层三档全跌：q_content
  0.9061→0.8840、q_vague 0.6540→0.6445、q_episodic 0.2634→0.2500。ΔRecall@1
  `−0.4870pp`，CI95 `[−1.2987, +0.3247]`（探索性，跨零）。救援阀打开的查询数从
  113 涨到 **417/616**。

  **机制能逐条数出来，不需要统计。** 37 条目标名次变化拆开：**12 条跌出 20 名列表，
  其中 10 条原本在前 5、5 条原本排第 1**；24 条名次上升（21 条只升一名、3 条升两名），
  但**只有 1 条因此跨进前 5**；1 条从列表外进到第 20 名；0 条下降但留在列表内。
  前 5 净损失 `−10 + 1 = −9`，`−9/616 = −1.4610pp`——和 bootstrap 点估计完全一致。
  收益全落在桶内位移（把第 7 名推到第 6 名不改变对错），损失全落在桶边界。这个不对称
  是结构性的，不是运气。

  **根因：条件 3 把「URL 死了」当成了「存下来的副本没用了」。** facetmark 存正文，一个
  404 页面的那段文字仍然是问题的正确答案。`drifted` 更反——它的意思是远端正文和本地
  快照对不上，这恰恰说明本地这份是唯一还留着原内容的地方，降权它是反的。

  一个显然的补救（只在没有可服务正文时降权）**只救得回一半**：8 个受损目标里 4 个的
  `char_count` 就是 0，完全没有正文却仍然被检索到、并且是查询集认定的正确答案，靠的是
  标题和两个词面面。所以这不是干净的修法。

  **局限三条**：(1) 73 是**上界**——按 `synth.py` 的规则顺序，「任何外部正面观察都压过
  本地失败」排在「本地 404 → gone」之前，关掉外部证据就是最偏向判死的配置；开了外部
  证据冷层只会更小，Δ 的绝对值只会更小，但方向不会翻。(2) `drifted` 那 28 条是拿约
  3 天前的快照比出来的，噪声大，没有独立核验。(3) 只跑了一次，没有第二次观察去满足
  `health_gone_confirm_days = 7` 的设计意图。另记一条**没查清的**：全库健康检查时
  stderr 反复打出 `readability` 的 `ValueError: All strings must be XML compatible`，
  但报告的 `errors` 是空列表——异常在上层被吞掉了，可能让一部分页的 drift 检测静默失效。

- **`cold_census()`**（`src/facetmark/search/decay.py`）——把冷层三个条件**分开**报，
  并给两处静默失效起名字。这次翻转能发生是因为有人手动去查了 `health` 表有几行；这个
  函数的存在意义是让下一次不必靠运气。

  返回的 `degenerate_conditions` 目前会报两种：`never_opened_selects_everything`
  （`open_count` 全库为 0，条件 1 恒真）、`health_never_checked`（`health` 表为空，
  条件 3 的死判定那一半不可能触发）。在 1.5.0 用的那个库上跑，两条都会亮。

  同时分开报 `servable_cold` / `unservable_cold`（按 `min_body_chars` 切），因为
  「URL 死了」和「没有正文可服务」是两件不同的事，而现在的判定把它们混为一谈。

  `tests/test_cold_census.py`（17 条）钉住这些字段的语义，包括「治愈」的情形：一页先被
  判 `gone`、后被判 `alive`，只看最新判定所以不算冷。

- **`fm health --check` 新增 `--no-save-recovered`**。原先健康检查会把重新抓到的正文
  写回 `content`，这在做 A/B 时会污染实验——正文变了，向量和 FTS 都得跟着变，两次运行
  的差异就不再只归因于被测的那一个设置。这个开关就是为了让上面那个实验能干净地做。

- **冷层普查接到两个可观测面上**：`fm stats` 的 payload 里多了 `cold_layer`，
  `fm health --check` 结尾多打一行普查摘要加退化警告。

### 变更

- `service.library_stats()` 签名从 `(conn)` 变成 `(conn, settings=None)`，为的是让普查
  用调用方的 `decay_age_days` 和 `min_body_chars`，而不是重新读一遍全局配置。不传
  settings 时行为不变。

## [1.5.0] - 2026-08-05

**这一轮没有加功能，只是回头查了 1.4.0 亲手写下的两句话，两句都不成立。**

一句是「没有任何东西验证一边发出的 JSON 就是另一边解析的 JSON，而这需要同时起 karakeep
和 facetmark，本仓库做不到」——做得到，只要让两边各自把自己那半边的字节落成文件。另一句
是把「默认档里有一层死代码」当成了一个待修的缺陷——它是真的，但它的代价被量出来是精确的
零，于是待办事项从「要修」变成了「不修，这是理由」。

一个缺口被补上，一个缺口被证明不必补。剩下的缺口仍然在 ROADMAP 上写着。

### 新增

- **跨语言线格式契约**（`integrations/karakeep/contract/`）。1.4.0 的 CHANGELOG 和
  插件源码头注释里都写着同一个缺口：Python 路由由 Python 测试钉住，TypeScript 签名由
  `tsc` 钉住，**没有任何东西验证一边发出的 JSON 就是另一边解析的 JSON**。1.4.0 里还
  顺带断言了这个缺口「需要同时起 karakeep 和 facetmark，本仓库做不到」——**这后半句是
  错的，本条把它撤回**。

  做法是让每一边把自己那半边的字节落成一个提交进仓库的文件，另一边对着文件断言：

  - `capture.ts` 用 karakeep 驱动插件的方式驱动真插件（环境变量 → `getClient()` →
    四个方法），只把 `globalThis.fetch` 换成记录器，请求体写进 `wire.json`。插件源码
    一行没改。
  - `tests/test_karakeep_contract.py`（25 条）把这 6 条请求**原样重放**进真实的 FastAPI
    应用，断言全部 200，并把响应写回 `replies.json`；`capture.ts` 再把这些响应喂回插件的
    `search()`，检查 TypeScript 这边解析得动。
  - CI 两个 job 各跑一半：`python` 那个不需要 Node，`karakeep-plugin` 那个跑
    `npm run contract:check`，不需要 Python。任一侧漂移都是一个已提交文件里的 diff。

  钉住的边界情形：TypeScript 的 `Date` 经 `JSON.stringify` 只以 ISO 字符串到达 Python
  （`z.date()` 描述的是一个 Python 永远见不到的类型）；只有两个必填字段的文档；显式
  `null` 与字段缺失的区别；`FilterQuery` 的 `eq`/`in` 两种变体；`/karakeep/clear` 是一个
  声明了 JSON content-type 却没有 body 的 POST；两个空批次早退不产生 HTTP 请求；以及
  Pydantic 默认会静默丢弃的「插件发了模型不认识的键」。

  **发现的语义陷阱**：请求「唯一一条匹配结果的 offset 1」时，真实响应是 `hits: []` 但
  `totalHits: 1`。空的 `hits` 是一个分页结果，不是空结果集。两边任何把二者混为一谈的
  代码都是错的。这条哪一种语言单独测都测不出来。

  **边界**：这是格式契约，不是集成测试。插件注册、真实 HTTP 栈、并发、活的 karakeep
  实例，一样都不覆盖。

- **量了「够不着的衰减层」到底值多少钱**（`scripts/decay_reach_probe.py`、
  `eval/decay-reach.json`、`docs/decay-reach.md`）。1.4.0 记下的缺陷是：默认档 `full`
  是单面配置，RRF 单面封顶 `1/61 = 0.0164` 低于 `decay_rescue_threshold = 0.02`，救援阀
  每次都开，冷层降权一次也没执行过。那是一个关于算术的证明，它不说后果。

  确定性 A/B，同一个检索器只改这一个设置（`0.02` 对 `0.0`，后者让阀门朝另一个方向够
  不着，于是降权总是执行），同一个 2,376 篇的库、同一批 616 条留出查询、同一个本地
  bge-m3、时钟冻结在 `1785649110`：

  - **ΔRecall@5 = `0.0000pp`，CI95 `[0.0000, 0.0000]`**（10,000 次 bootstrap）。
    shipped 与 reachable 都是 `0.5860`；分层 Recall@5 一位没动（q_content 0.9061 /
    q_vague 0.6540 / q_episodic 0.2634）。
  - **不是功效不足。** 46 条查询的完整列表变了、15 条的前 5 变了、3 条的目标名次移动了
    一格（14→13、9→8、2→1），而 `0 < rank <= 5` 这个布尔值一条都没翻转。CI 是 `[0,0]`
    因为每一次重抽都在重抽一堆完全相同的配对。
  - **冷层普查**是解释：全库 2,376 页，满足「老且从未打开」的 1,071 页，三条件全满足
    的**只有 8 页**，而 616 条查询的 230 个目标里**一个冷页都没有**。条件 3（需要取代
    证据）挡掉 99.25%，而它正是拦着这一层退化成年龄过滤器的那道墙。
  - 救援阀在 **113/616** 条查询上开启，每一次守的都是一个不存在的风险。

  **处置：不改阈值。** 理由从「改默认排序需要先有协议」升级成「量过了，收益是零」。
  `tests/test_decay_reach.py` 继续钉住现状。ROADMAP 里 (a) 标记为已测，(b)（阈值该不该
  按面数归一化）仍未测但优先级下调——归一化能让阀门正确工作，而由 (a) 可知正确工作的
  收益在这个库上是零。

  **两条标注**：Recall@1 的 `+0.1623pp`（CI95 `[0, +0.4870]`，就是那 1/616 条）是**看到
  数字之后才算的探索性指标**，不作证据用；`cold_targets` 为空是查询集的性质而不是库的
  性质——查询从有正文的页生成，冷页大多是死链，一批「找回那个已经打不开的页面」的查询
  可以推翻上面每一个数字。这是这份实验最需要被质疑的一点。

### 变更

- `tsc --noEmit` 的 `include` 现在也覆盖契约脚本（`allowImportingTsExtensions`），所以
  捕获脚本本身也被类型检查。
- 契约脚本必须用 `node --experimental-transform-types` 而非 `--strip-types`：插件的构造
  函数用了参数属性，strip-only 模式擦不掉。这里选择动运行参数而不是动插件源码。
- 测试数 1090 → 1149（+25 条线格式契约，+19 条衰减探针的测量装置，+15 条版本一致性）。
  衰减那批里最要紧的一条是「相互抵消的差异不会把区间压成 `[0,0]`」——整份
  `docs/decay-reach.md` 的读法都靠它成立。

### 修正

- **`facetmark.__version__` 从 1.3.0 补到 1.5.0。** 它在整个 1.4.0 期间都停在 1.3.0，
  于是 `facetmark version`、`GET /health` 和 OpenAPI 文档一起报了一个落后两版的版本号。
  没有任何东西报错，这正是问题所在——一个只有人会读的版本号会悄悄漂走。
  `tests/test_version.py` 现在把五处（包内常量、`pyproject.toml`、
  `extension/package.json`、`CITATION.cff`、`CHANGELOG.md` 最新的已发布标题）钉在一起，
  顺带钉住 CITATION 的日期和 CHANGELOG 的版本顺序。
- **浏览器扩展的 manifest 版本改为构建时注入。** 它自己写死着 `1.0.0`，而
  `package.json` 已经爬到 1.4.0——装出来的扩展报着一个从没发布过的版本。现在
  `src/manifest.json` 里没有 `version` 字段，`build.mjs` 从 `package.json` 盖上去，
  单一事实来源，不会再漂。

## [1.4.0] - 2026-08-04

**这一轮的主题是停止造轮子。** karakeep 已经把检索周边的东西全做完了——浏览器扩展、
手机 App、无头 Chrome 抓取、多用户、Web UI、Docker 部署——而它的排序是一个只有四个方法
的插件接口。所以 facetmark 实现那个接口，然后放弃自己那三样。

### 新增

- **`facetmark.bridges.karakeep`**：karakeep `SearchIndexClient` 契约的 Python 侧实现，
  `addDocuments` / `deleteDocuments` / `search` / `clearIndex` 四个方法各对应一个函数。
  按需建一张 `karakeep_doc(karakeep_id, user_id, bookmark_id, updated_at)` 映射表，卸载
  就是 `DROP TABLE karakeep_doc`。
- **五条 HTTP 路由**：`POST /karakeep/documents`、`POST /karakeep/documents/delete`、
  `POST /karakeep/search`、`POST /karakeep/clear`、`GET /karakeep/stats`。写路径全部在
  服务的全局锁内。
- **`POST /karakeep/search` 接受 `config` 参数**（`full`、`A`–`E`、任意消融档名）。
  ~~消融可以在一个真实 karakeep 库上跑了~~ —— **这条在同一个版本里被自己的实验证伪并
  撤回**，见下面的往返实验。读取路径没问题，指标级结论搬得过去，名次级结论搬不过去。
- **`integrations/karakeep/search-facetmark/`**：karakeep 侧的 TypeScript 插件
  （`FacetmarkClient implements SearchIndexClient` + provider 注册）。~~它不在本仓库的
  CI 里构建、也没有测试~~ —— 这个缺口在本版本内被补上了一半：
  `integrations/karakeep/typecheck/` 里放着上游两个接口模块的类型声明，blob SHA 钉在
  `upstream-pins.json`，CI 的 `karakeep-plugin` job 每次 push 跑 `tsc --noEmit`。
  仍然没有的是对着一个活的 karakeep 实例的集成测试。
- **`docs/karakeep.md`**：分工表、三步装法、五条路由、逐字段映射表，以及三处不保真的
  地方。
- **`README.zh-CN.md`**，并把 `README.md` 整篇重写成英文版，两边互相链接。旧 README
  里那段 `## 中文说明` 的内容并入中文版并按 1.3.0 的实际默认值更正。

### 修正

- **README 与 `docs/karakeep.md` 里的服务端口从 8765 改回 8787**，与
  `config.py` 的 `port: int = 8787` 一致。
- **README 里两处数字张冠李戴已更正**：`0.5860 / 0.5065` 是 W2/W3 那 616 条留出集上的
  数字，不是 W1 的；W1 的主表是 A 0.643 / B 0.589 / C 0.635 / D 0.639（n=479）。另外
  出厂默认档 `FULL` 是 `content + graph + decay`，**不含词面**，之前写成了
  「lexical + content + graph + decay」。

### 已知短板（写在这里而不是藏起来）

- **多用户是最弱的一环。** facetmark 的索引没有用户分区，`userId` 过滤发生在**排序
  之后**，所以书签多的用户会被系统性地偏向。`OVERFETCH = 5` 是补偿，不是保证。诚实的
  配置是一个用户一个库。
- **意图面不由桥接填充**，karakeep 推过来的文档需要事后单独跑一次 `facetmark index`
  才有意图向量。
- `tags` 映射到 `bookmark.folder` 时用 `" / "` 拼接，`folder_depth = len(tags)`。**这不
  是等价物**：五个平级标签在 facetmark 眼里长得像五层嵌套目录。

### 实验：karakeep 往返保真度（判定 `roundtrip_unfaithful`）

- **协议先冻结再搬数据**：`docs/karakeep-roundtrip-protocol.md`（149 行），三条判据在
  测量之前写死。结果报告 `docs/karakeep-roundtrip.md`。
- 2,376 条真实书签推进 karakeep 形态的库再拉回来，616 条留出查询，bootstrap 10,000 次。
  判据 a（指标保真）**通过**：ΔRecall@5 = −0.81pp，CI95 [−2.44, +0.81]。
  判据 c（读取路径）**通过**：616 × 2 档 HTTP 与原生逐条比对，0 处不一致。
  判据 b（名次保真）**差 0.94pp 未通过**：overlap@5 中位数 4.0 达标，top-1 一致率
  79.06% 未达 80%。
- **归因是完全的**：正文 1876/1876 逐字节相同，摘要 2375/2375 逐字相同，但 `topics`
  一致率 0%、`entities` 1.18%——karakeep 的 tag 是浏览器**文件夹**标签。嵌入文本里那行
  关键词的词汇量从 19,016 塌缩到 13，人均 10.32 → 0.76，最高频词是出现在 1,124 页上的
  `未分类`。向量中位余弦 0.9846。把源库富集移植回去后 2376/2376 条嵌入文本逐字符相同，
  残差 0。
- **补救路径已实测有效**：在桥接库上跑 `facetmark index`，karakeep 给过的正文 0 条被
  重抓，2376/2376 条桥接写入的富集行被重新拾起，重建的图与源库逐位相同，只差 212 条
  语义边（26,485 对 26,697）。
- 按协议第 7 节，`docs/karakeep.md` 里那句「可以在真实 karakeep 库上跑消融」已撤回并
  限定，未通过的判据 b 写进了两份 README。

### 修复

- **桥接会静默降级已有的富集。** 旧的 `_upsert_one` 在 `ON CONFLICT` 分支里改
  `summary` / `topics` / `model`，却**不动 `source_hash`**。后果链：某页本来被真实模型
  富集过（`source_hash = <body_hash>`）→ karakeep 同步把摘要换成标签列表 → `source_hash`
  仍等于 body_hash → `enrich.targets()` 认为这行没变过而**永久跳过**；而 `content_work()`
  的指纹已经变了，向量会按**更差的文本**重建。不报错、不可逆（除非 `--force`）、报告里
  也看不出来。现在改成与 `bookmark.source`、`delete_documents` 一致的**认领而非覆盖**：
  只有该行不存在、或本来就是 `source_hash='karakeep'` 时才写；否则原样保留并在返回里
  计入新字段 `kept_enrichment`。保留外来富集时，FTS 按**库里已存的**富集同步，不索引
  karakeep 的词。UPDATE 分支现在显式写 `source_hash='karakeep'`。四条新测试钉住。

### 已知缺陷（记录，未修）

- **衰减层在默认档里够不着。** RRF 分数是 `sum_f w_f / (k + rank_f)`，`rrf_k = 60` 时
  单个单位权重的面最高 `1/61 = 0.016393`，而 `decay_rescue_threshold` 出厂值 `0.02`。
  默认档 `FULL` 是单面配置，于是救援阀恒开，它守着的降权从未执行过。`FUSED` 不受影响。
  `tests/test_decay_reach.py` 五条测试钉住现状，**故意不改默认值**——动阈值会改变每条
  查询的默认排序，按项目规矩需要先有查询集和预注册判据。已列入 `ROADMAP.md`。
- 同时更正一条旧笔记：「只有 8/2,376 页够得上冷却线且从未进入前 20」的后半句是错的，
  冷页确实进过前 5（源库侧 15/616 条查询）。它们只是从来没有被降过权。

### 工具

- **`scripts/karakeep_roundtrip_diff.py`**：两个库的逐层差异，一直挖到关键词行的词汇量
  统计。
- **`scripts/karakeep_remedy_probe.py`**：干跑 `facetmark index` 每一段会做什么，带
  `--graph-only` 与 `--attribute` 两种模式。所有写操作都包在显式的
  `BEGIN` / `ROLLBACK` 里并事后断言行数——因为 `facetmark.db.connect()` 是 autocommit，
  `conn.rollback()` 在那里是空操作。

### 开源工程

- **两份 README 全面重写**（`README.md` / `README.zh-CN.md`）：加目录、流水线示意、
  数据模型表、完整配置表、命令表、检索档位表、排错、FAQ、贡献指引，并把上面所有负面结果
  平铺在正文里。
- 新增 `CODE_OF_CONDUCT.md`（Contributor Covenant 2.1）、`CITATION.cff`、`.editorconfig`。
- 浏览器扩展版本从 `1.0.0` 对齐到主包版本。

## [1.3.0] - 2026-08-04

**发版是因为默认检索行为又变了，而且是往回变**：1.2.0 把带门控的上下文乘子设成默认，
1.3.0 把它撤掉。`FULL` 退回 `content + graph + decay`——也就是 1.1.0 的排序行为。

撤掉的理由是一次预注册的实验（协议 `docs/gate-precision-protocol.md` 先落盘，报告
`docs/gate-precision.md`）。1.2.0 那 +3.09pp 的依据只测了门控**该响的时候**响不响：
它的假阳性率 0.55% 是在 181 条"生成时被明确要求不要写日期"的内容型查询上量的。换成
**361 条时间词属于正文主题而非保存时间**的查询——比如一篇 2026 年存的页面配上
"2015年国际空间站咖啡机为什么那么贵"——门控 **361/361 全响**，代价是
**Recall@5 −18.83pp，CI95 [−23.27, −14.68]，3 胜 71 负**，Recall@1 从 0.801 掉到 0.363。

其中一个次要分层值得单独说：`p_relative` 子类有 57 条的时间窗恰好包含目标自己的保存
时间，那 57 条上 ΔR@5 恰好 **+0.00pp**（1 胜 1 负）；窗口不可能包含答案的 304 条上是
**−22.37pp**。所以这 22 个点是"窗口错了"，不是"乘子太重"。

预注册的补救 `gate_v2`（`context_gate_version=2`，裸年份不再单独构成保存时间信号）
也实现了、也跑了两关，结果是一关过一关不过：探针集上残余 **−10.52pp CI95
[−13.85, −7.48]**（第一关不过，残余全部来自协议明确不动的 `time:relative`），616 条
holdout 上仍有 **+1.79pp CI95 [+0.81, +2.92]**（第二关过）。协议要求两关都过，所以
默认值按预注册规则退回无门控行为，`gate_v2` 留在树里但不上线。

### 改动

- **`FULL` 从 `content + context(gated) + graph + decay` 退回 `content + graph + decay`。**
  装上这个版本的人，同一个库、同一条查询，情景型查询上会比 1.2.0 差（放弃了那
  +8.48pp），带日期的内容型查询上会比 1.2.0 好很多（避开了那 −18.83pp）。
- **新增 `Config.context_gate_version` 与 `episodic_beyond_a_bare_year()`**，以及档位
  `A_gatedctx_v2`。实现了、有测试、默认关闭、有一个不合格的数字挂在上面。
- **新增 `scripts/corpus/gen_gate_probe.py`**（探针生成器）、`scripts/gate_precision.py`
  （按预注册规则判定）、`scripts/gate_v2_disposition.py`（两关合取的处置表）。
- **新增评测数据**：`eval/queries/gate-precision.jsonl`（361 条，跑任何一档之前冻结）、
  `eval/gate-precision-eval.json`、`eval/gate-precision.json`、`eval/gate-v2-probe.json`、
  `eval/gate-v2-holdout.json`、`eval/gate-v2-disposition.json`、`eval/gate-precision-gen.json`。
- **新增文档** `docs/gate-precision-protocol.md`、`docs/gate-precision.md`。

### 没有做的事

没有顺着数字继续收窄 `time:relative`。它看起来很可能管用（v2 已经把 `p_year` 压到
−0.50pp 并保住 +1.79pp），但这 361 条查询已经被用来**在两个门控之间做选择**，再用它们
去检验第三个门控就是重演这次实验要纠正的那种循环。`gate_v3` 需要自己的预注册和自己的
探针集，记在 W4 里。