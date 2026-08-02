# 变更记录

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

## [未发布]

### 新增

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

### 修复

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
