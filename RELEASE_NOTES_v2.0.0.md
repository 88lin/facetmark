# v2.0.0 — 本地搜索页面、全栈分页与全量界面重构

> 自 v1.6.1 以来 **108 个提交**、**152 个文件变更**（+34,563 / −2,702），合并 **8 个 PR**（#7–#11、#15–#18）。

**facetmark 2.0 是一个"装完就能用"的版本。** 1.x 最大的缺口是：`facetmark serve` 起来之后没有任何页面可以打开——扩展要先 `npm run build` 再手动加载，`docs/landing/` 只能读不能用，`/docs` 是 Swagger。对一个不写代码的人来说，这个项目装完之后没有入口。2.0 补上了这个入口，同时把检索分页、配置管理和后台操作全部搬到了 HTTP 上。

---

## ✨ 新增功能

### 1. 本地搜索页面 `GET /app`

`facetmark serve` 现在自带一个完整的搜索界面——一个 HTML 外壳、一张样式表、若干 ES 模块，**没有打包器、没有 Node 构建产物、没有新的 Python 依赖**。

- **两个视图**：搜索（沿用 #11 的 `offset`/`depth` 分页，`depth` 从第一页钉住）与书签库总览（`/stats`，回答"我建好索引了吗"）。
- **中英双语 + 深浅色主题**：两套文案集中在 `static/strings.json`，主题跟随系统可手动切换，写入 `localStorage`。
- **`GET /app/boot`**：配对令牌的唯一出口。只有在 TCP 对端是回环地址**并且** `Host` 头也是回环字面量时才返回令牌——第二个条件防 DNS 重绑定攻击。不满足时退回手工粘贴令牌。
- **`GET /app/static/*`**：Starlette `StaticFiles` 挂载，ETag 与 304 白送。
- 启动横幅多一行 `open the search page: .../app`。

### 2. 全栈分页（`offset` + `depth`）

"只能搜出 20 条"不是一个上限，是**四个**天花板叠在一起：页大小、缺失的 offset、把"检索多深"和"一页给几条"绑成同一个数的候选池，以及开销随页大小线性增长的重排。2.0 把四层全部拆开。

- **`offset` 和 `depth` 贯穿全栈**：`search()` / `quick_search()` / HTTP `/search` `/quick` / MCP `search_bookmarks` / CLI（`-o/--offset`、`--depth`）/ 浏览器扩展 / karakeep 桥。
- **响应新增六个字段**：`limit`、`offset`、`depth`、`total`、`has_more`、`depth_capped`——全部是**实际给出的值**而非请求的回显。
- **`depth` 是显式参数**：RRF 只在单面时对深度稳定，靠加深池子去够第二页会让第二页对第一页改口。解法是把深度钉住：响应回报 `depth`，客户端原样送回，每一页都是同一版排名上的一刀。
- **浏览器扩展**从写死 `api.search(q, 20)` 改为"加载更多"。
- **`db.in_chunks()`**：按 900 一批切开 `IN (...)`，避免发行版 SQLite 的 999 变量上限在深翻页时炸掉。

### 3. HTTP 管理 API

导入、索引、配置全部可通过 HTTP 完成（新增 `src/facetmark/admin.py`）。不再需要 CLI 才能操作——从浏览器设置页就能导入书签、触发索引、改配置。

### 4. 文件配置系统

- 从 `<data_dir>/config.toml` **读写设置**（新增 `src/facetmark/configfile.py`），安全回写。
- 检索上限——`MAX_PAGE_SIZE`（200）、`MAX_CANDIDATE_DEPTH`（2000）、`RERANK_DEPTH`（20）——从散落在各个接口签名里的 `le=` 搬到了配置里。**超限是截断不是拒绝**，且截断结果写在响应里。

### 5. 面贡献报告

搜索响应现在报告**每个面对融合分数的贡献**，让"为什么是这个排名"可解释。

---

## 🎨 界面与文档

### Web UI 全量重构

- **苹果系统字体 + 紫藤色板**，把棕、咖啡、浓绿和近黑全部请出去。
- **手绘虚线视觉语言**，8 个视图全部重画——白卡阵列换成分层、色相与虚线框。
- 新增**初始化页**与**设置页**，每条排名都附"为什么是这个结果"。
- 排版音阶推进应用界面，胶囊导航，macOS 代码窗口。
- `color-scheme` 与手动主题同步（`light`/`dark` 成对），修掉系统深色 + 手动浅色时 UA 部件仍按深色渲染的问题。

### 官网与 README

- 官网重建为**三页中英双语站点**（首页 / 快速上手 / 指南），滚动叙事首页，配色对齐参考站。
- **README 全面重写**（中英文）：居中 hero 区、树形目录、GitHub Admonitions、Mermaid 横向流程图、Star History 图表。
- 新增 **Web 界面**与**分页**两节指南，首页新增八张截图（搜索 / 书签库 × 中英 × 深浅）。
- `docs/` 新增 `config.html`、`guide.html`、`quickstart.html`、`webui.html`、`integrations.html`、`measured.html`（中英各一）。

---

## 🐛 修复

- **chat-only 库空结果**：没有向量库时（`/embeddings` 404 的端点），搜索不再对所有查询返回空页。`search()` 按库自动降级到词法面，响应新增 `degraded_from` 记下被换掉的名字。
- **`synthesize` 空答案**：excerpt 全空时（导入了但还没索引的页）不再调用模型——这次调用注定失败还花钱——返回明确 gap："none of the sources have any indexed text; run `facetmark index`"。
- **纯标题摘要无标注**：正文没抓到的页从标题+网址推断摘要，此前和真实摘要无法区分。新增 `basis` 列（`body` / `title` / `karakeep`），推断摘要带「摘要由标题推断」徽章，`/synthesize` 的提示词和 gap 里都加注。
- **`.gitignore` 吞掉 wheel 内容**：第 23 行 `*.html` 会把 `src/facetmark/web/index.html` 一起吃掉，导致构建成功、启动成功、`/app` 404。加了 `!src/facetmark/web/*.html` 反选，并由 wheel job 兜底。
- **对比度**：新增 `--ink-mute` token，排名序号、页脚等小字在所有背景色上 ≥ 4.5:1，且这条承诺是被测出来的。
- **设置页**：能存下域名列表，上传不再吃掉标题，环境变量锁住的字段不再被改。
- **手机端**：第五个视图够不着、Escape 关弹窗不清空搜索等问题修复。

---

## ⚠️ 行为变更

- **重排深度不再等于页大小**：受 `RERANK_DEPTH`（20）约束，一页的重排成本与页大小无关。会重排的档位（`E`、`fused`）上超过 20 条的页尾巴保持融合顺序。**这是一处可能影响相关性的变更，尚未测量其对检索质量的影响。**
- **`CANDIDATES_PER_FACET` 从"池子大小"变成"池子下界"**：每次检索至少这么深，一个 5 行的请求也能报出诚实的 `total`。
- **首屏深度**从 `max(3 × limit, 30)` 变成 `max(candidates_per_facet, 3 × 窗口)`。
- **MCP `search_bookmarks`** 去掉了 `limit` 上的静态 `le`（默认仍为 10——那是上下文窗口预算，不是召回上限）。
- **karakeep 桥**检索窗口上限从字面量 `500` 换成 `MAX_CANDIDATE_DEPTH`，`truncated` 改为直接取流水线的 `has_more`。

---

## 🔒 安全

- 从 `HEAD` 移除误传的个人书签导出文件 `favorites_2026_8_4.html`（1,710 条 `HREF=`，带目录和时间戳），并在 `.gitignore` 补上具名条目。**移除只改变 HEAD，不改写历史**——文件在旧提交里仍可取。
- `/app/boot` 的 DNS 重绑定防护（回环地址 + 回环 Host 双重校验）。

---

## 🧪 测试与 CI

- **Python 测试 1188 → 1514**（+326），**扩展测试 16 → 28**。
- CI 新增 `webui` job（`node --test` 跑纯函数模块）与 `wheel` job（构建 wheel 并断言 `web/index.html` 等四个文件在里面）。
- **`scripts/browser_check.py`**：CI 真的打开页面看一眼——7 个 bug 逐个放回，全被抓住。
- 新增 `star-history` workflow（每周一更新 Star History 图表）。
- 官网新增中英两套内容的**结构对等测试**，以及"已提交的 HTML 等于重新渲染的结果"。

---

## 📦 安装与升级

```bash
pip install facetmark==2.0.0
```

或从源码：

```bash
pip install -e '.[dev]'
facetmark import BOOKMARKS.html
facetmark index
facetmark serve          # 然后打开浏览器访问 .../app
```

**Full Changelog**: https://github.com/88lin/facetmark/compare/v1.6.1...v2.0.0
