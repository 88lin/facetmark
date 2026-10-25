# 原有功能与桌面覆盖记录

日期：2026-10-25。Facetmark 应用与取证版本：`81f310a8251191804ffbf9cfd5e94decabe69ab9`。此记录复用先前只读 artifacts 审计，沿原 `src/facetmark/cli.py`/`api.py` 用户操作契约追踪 frontend → API → service/任务 → 持久化，不将按钮或路由存在本身当作运行证明。

参考仓库固定 SHA 为 `2f41b01c79d9e4ed11752592fa4c6cbb837e342a`；完整 48 项功能、15 条并发/重试路径和 9 项风险取舍见 [githubstarsmanager-comparison-2026-10-25.md](githubstarsmanager-comparison-2026-10-25.md)。参考源码与 Facetmark 原功能覆盖是两份证据，不能相互替代。

本轮新能力标注 **“本轮实现”**。`81f310a` 的 CI、收藏、体验和 Windows 安装均已通过，同版本结果见文末和 [桌面补齐记录](desktop-completion-2026-10-25.md)。模型回复、库与浏览器来源为合成数据；真实模型账号权限、生成质量及用户视觉评价另行判断。内部源码定位相对于仓库根，函数名用于避免行号移动。

日常 CRUD、目录/标签、关键词/语义搜索、阅读、保存会话、完整索引、扩展与 Karakeep 原入口已保留。新增 Timeline/Health/Chat/HTTP MCP/网站导入和恢复备份已纳入本轮回归；重依赖 ST 与低频 CLI/CI 运维能力明确保留边界，不宣称桌面包装等同完整 Python 环境。

## 原 CLI 命令与选项覆盖

| 原命令及契约 | 当前桌面入口/执行链 | 覆盖事实和保留边界 | 源码落点 |
| --- | --- | --- | --- |
| `version`、根命令 `--version` | 设置桌面与更新展示当前版本；CLI 保留脚本输出。 | 现有入口保留。版本展示不表示本轮云端安装已通过。 | `src/facetmark/cli.py:version`; `frontend/src/Settings.tsx:UpdateSettings`; `src/facetmark/workbench.py:check_updates` |
| `import <path>`：HTML、Chromium JSON、Facetmark JSON，读取来源、写入本地库 | Setup 上传/拖放 → /admin/import → import_content/import_bookmarks。 | 元数据入口保留；v2 full 正文/AI 派生/聊天恢复 本轮实现。来源文件读取后写 Facetmark 本地库；详细导入报告仍需按最终 UI 核对。 | `frontend/src/Setup.tsx`; `src/facetmark/admin.py:register`; `src/facetmark/service.py:import_content`; `src/facetmark/importers/__init__.py`; `src/facetmark/backup.py` |
| `import` 不带路径：发现真实 Chromium 来源，多来源不猜测 | Setup 明确发现来源 → 用户选择 source_id → /admin/import/source。 | 现有入口保留，多来源不猜测。只读选定原浏览器书签来源，再写本地库；HMAC 来源 ID 不提供任意路径读取。 | `frontend/src/Setup.tsx`; `src/facetmark/workbench.py:import_sources`; `src/facetmark/workbench.py:import_source`; `src/facetmark/importers/discovery.py` |
| `browsers`：列出可导入来源，不接触库 | 相同来源发现界面 → /admin/import/sources。 | 现有用户操作对等。完整路径/JSON 仍作为 CLI 调试信息，不要求桌面暴露任意文件路径。 | `src/facetmark/cli.py:browsers`; `frontend/src/Setup.tsx`; `src/facetmark/workbench.py` |
| `migrate`、`migrate --check` | 服务正常连接数据库执行迁移；设置显示兼容状态。 | 手动 migrate/check 和非零退出码保留 CLI/CI；当前任务日志/stats 不是完整迁移检查 UI。 | `src/facetmark/cli.py:migrate`; `src/facetmark/db.py`; `src/facetmark/migrations.py`; `frontend/src/Settings.tsx` |
| `index`：fetch → enrich → embed_content → filter_intents → embed_intents → sessions → edges | 任务页“建立完整索引” → /admin/index → JobRunner 独立连接 → index_all。 | 原完整七阶段管道保留。阶段式取消，重跑按指纹跳过；与独立 fetch/summary 逐项快照恢复不同。 | `frontend/src/Tasks.tsx`; `src/facetmark/admin.py:JobRunner`; `src/facetmark/service.py:index_all` |
| `index --no-fetch`、`--limit`、`--force`、`--mock`、`--json` | 完整 index 可选先抓正文；独立处理任务有选择/范围。 | no-fetch 有用户入口；limit/force/mock/JSON 的完整 CLI 契约保留。当前 Tasks 不提供所有研究/强制整库参数，不能把选中摘要重做说成全库 reindex。 | `src/facetmark/cli.py:index`; `frontend/src/Tasks.tsx`; `src/facetmark/admin.py:IndexRequest` |
| `reindex`：强制整库重新抓取与处理 | 设置应用向量变更：备份并清不兼容向量 → 再执行完整 index。 | 有模型/维度变化恢复路径。直接强制整库重新抓取/处理保留 CLI；doctor 已改为真实设置重建后 index 路径，本轮实现。 | `src/facetmark/cli.py:reindex`; `src/facetmark/workbench.py:apply_settings`; `src/facetmark/diagnose.py:check_vectors`; `frontend/src/Settings.tsx` |
| `search`、`search --quick`：关键词/完整检索、offset、固定 depth、查询语言 | 顶部共享搜索 → /quick 或 /search；offset/depth 分页；/suggest/query 补语法。 | 现有入口保留；语义受模型已测试/向量兼容/pending_apply 约束。A–E/JSON/mock/完整原始解释保留 CLI/API；失败状态与新查询身份需本轮回归。 | `src/facetmark/cli.py:search`; `frontend/src/App.tsx`; `frontend/src/SearchTools.tsx`; `src/facetmark/api.py:full_search` |
| `show <id> --body` | 统一 Reader → /bookmark/{id}?body=true；AI 概览/要点与原文同页。 | 本轮统一阅读、AI 标题、目录/进度/字号 本轮实现；原始标题/链接保留。目标语言摘要不表示原正文已经翻译。 | `src/facetmark/cli.py:show`; `frontend/src/App.tsx`; `frontend/src/Reader.tsx`; `src/facetmark/service.py:bookmark_record` |
| `sessions`：保存会话聚类 | 活动页保存会话列表分页 → session 过滤成员；API/MCP 提供 session 详情。 | 现有成员浏览保留。原始关系/边权详情没有专用 UI，可留接口，不把聊天会话与保存会话聚类混为一类。 | `src/facetmark/cli.py:sessions`; `frontend/src/App.tsx`; `src/facetmark/service.py:session_list`; `src/facetmark/service.py:session_record` |
| `health`、`health --check` | 任务页 HealthTools → summary/graveyard/check；可读保存内容、原链接/存档。 | 本轮桌面健康入口与短持锁落库 本轮实现；check 可联网并写判定/恢复正文，不自动删除收藏。no-external/no-save-recovered/cold census 保留 CLI 运维选项。 | `src/facetmark/cli.py:health`; `frontend/src/HealthTools.tsx`; `src/facetmark/api.py:AppState.check_links`; `src/facetmark/health/__init__.py` |
| `export`：全量或 query 范围、JSON/HTML、`--full` 派生数据 | LibraryTools → /admin/library/export；CLI full 同样读取 reading/chat 数据。 | 本轮可恢复 JSON v2 full 本轮实现，兼容 v1。HTML/元数据 JSON 与 full 范围不同；full 不含模型密钥/向量，不是完整 SQLite/任务日志备份。 | `src/facetmark/cli.py:export`; `frontend/src/LibraryTools.tsx`; `src/facetmark/library.py:export_library`; `src/facetmark/service.py:export_bookmarks`; `src/facetmark/backup.py` |
| `doctor`：本机配置/数据库/索引诊断，不调用模型、不修复库 | 任务高级区保留日志/stats；设置有模型连接测试。 | 完整 doctor 留 CLI/CI；它不调用模型、不修库，存在临时可写性探针。不能称 UI 日志等价 doctor，不能以 doctor 通过证明凭据/端点/编码器可用。修复提示 本轮实现。 | `src/facetmark/cli.py:doctor`; `src/facetmark/diagnose.py`; `frontend/src/Tasks.tsx`; `src/facetmark/admin.py:probe` |
| `stats`：索引统计与模型/图层信息 | Setup/任务/设置与 /stats 显示库计数、状态和兼容信息。 | 现有核心计数入口保留；原始图层与 JSON 信息仍 API/CLI。 | `src/facetmark/cli.py:stats`; `src/facetmark/service.py:library_stats`; `frontend/src/Tasks.tsx`; `src/facetmark/workbench.py:setup_status` |
| `token`、`token --rotate`：普通配对凭据读取/轮换 | 扩展设置复制当前普通 pairing token；MCP 设置管理独立 token。 | 获取普通 token 已对等。普通轮换 CLI 保留，MCP token 轮换不等于普通 token 轮换；凭据不放启动 argv/URL。 | `src/facetmark/cli.py:token`; `frontend/src/Settings.tsx:ExtensionSettings`; `frontend/src/McpSettings.tsx`; `src/facetmark/mcp_http.py` |
| `config path` | 模型设置管理可见配置，路径/来源诊断仍 CLI。 | 合理保留运维命令；frozen sidecar 不是 CLI binary，不能建议直接给 facetmark-service.exe 传 config path。 | `src/facetmark/cli.py:config_path_cmd`; `src/facetmark/configfile.py`; `src/facetmark/desktop.py:main` |
| `config show [--json]`：有效值与来源 | Settings 管理可编辑值，完整 env/file/default 来源仍 CLI。 | 本轮 api_key/chat_api_key/embed_api_key/mcp_token 均遮盖，本轮实现；表格与 --json 需要合成凭据回归。没有读取真实密钥进行审计。 | `src/facetmark/cli.py:config_show_cmd`; `src/facetmark/config.py`; `frontend/src/Settings.tsx` |
| `serve`：host/port/deployment/admin | Tauri 启动 sidecar；同 create_app、动态端口、同数据路径认证后复用。 | 现有生命周期保留；host/port/deployment flags 留 CLI。设置/扩展/MCP 使用实际 origin，不将 8787 写死。 | `src/facetmark/cli.py:serve`; `src/facetmark/desktop.py:compatible_service`; `desktop/src-tauri/src/backend_state.rs`; `src/facetmark/api.py:create_app` |
| `mcp`：stdio 服务给外部 AI 访问收藏 | 原 stdio 保留；sidecar 新 HTTP MCP 与设置复制配置。 | HTTP FastMCP/独立 token/协议自检 本轮实现。原 9 工具含 save_bookmark 和主动健康检查，不是全只读；这是对外服务端，不代表桌面 Chat 是第三方 MCP 客户端。 | `src/facetmark/cli.py:mcp`; `src/facetmark/mcp_server.py:create_server`; `src/facetmark/mcp_http.py`; `frontend/src/McpSettings.tsx` |
| `crawl <url>`：BFS 导入链接，默认同站、25 页预算、robots/隐私策略 | Setup 中 SiteImport → /admin/crawl → CrawlRunner/crawl_site；状态与取消独立路由。 | 原缺口已补，本轮实现。页数 1–500，默认 25；尊重同站/robots/隐私，独立连接并等待取消退出；上次参数/进度持久，重跑去重复用正文，不是精确 frontier resume。 | `src/facetmark/cli.py:crawl`; `frontend/src/SiteImport.tsx`; `frontend/src/Setup.tsx`; `src/facetmark/crawl_jobs.py`; `src/facetmark/crawl.py` |
| `update`：查询 PyPI 的 Python 分发版本 | 桌面设置 /admin/updates/check 查询 GitHub 安装包 release；CLI 查询 PyPI。 | 现有正确分发渠道保留；检查/打开下载不等于静默安装或自动升级，本轮不发布正式版本。 | `src/facetmark/cli.py:update`; `src/facetmark/workbench.py:check_updates`; `frontend/src/Settings.tsx:UpdateSettings` |
| `demo`：隔离合成数据、offline mock | 开发/CI 使用隔离合成数据。 | 合理留 CLI/CI；mock 不表示真实模型/真实用户库已成功。 | `src/facetmark/cli.py:demo` |
| `eval`：corpus/queries、A–E ablation、bootstrap、并发/延迟与质量评估 | CLI/CI corpus/queries、ablation、bootstrap、并发/延迟/质量研究。 | 合理留 CLI/CI，不增加桌面研究面板；mock 只验证管道。 | `src/facetmark/cli.py:eval_cmd`; `src/facetmark/eval/harness.py` |

## 原 API 与集成操作覆盖

路由“仍挂载”与“桌面有用户入口”分别判断。桌面使用相同 create_app，但冻结的 facetmark-service.exe 只运行 desktop.main，不是完整 CLI。

| 原操作 | 当前桌面/集成入口 | 覆盖事实、副作用和源码 |
| --- | --- | --- |
| `/`、`/health`、`/app`、`/app/boot`、`/admin/runtime` | 本地启动/配对、sidecar 就绪与兼容身份检查。 | 生命周期入口保留；需安装版启动/退出/端口冲突/复用。`src/facetmark/api.py:create_app`; `src/facetmark/desktop.py` |
| `GET /stats` | Setup、任务和设置读取统计。 | 核心统计保留；完整原始输出仍 API/CLI。`src/facetmark/service.py:library_stats`; `src/facetmark/workbench.py:setup_status` |
| `GET /quick`、`POST /search` | App 顶部关键词/语义搜索与固定 depth 分页。 | 原入口保留；本轮模型操作独立连接/短 metadata 锁 本轮实现。`frontend/src/App.tsx`; `src/facetmark/api.py:full_search`; `src/facetmark/api.py:AppState.model_operation` |
| `POST /suggest` | 外部编辑器/Agent 文本上下文推荐；MCP suggest_from_context。 | frontend 无单独调用，合理作为原集成接口保留；它按句本地词法检索、无模型调用，不等于查询语法补全。`src/facetmark/service.py:suggest_from_context`; `src/facetmark/mcp_server.py` |
| `POST /suggest/query` | SearchTools 字段/值/排序补全。 | 原入口保留。`frontend/src/SearchTools.tsx`; `src/facetmark/service.py:suggest_query_syntax` |
| `POST /synthesize` | SearchTools 对检索结果生成带引用的一次回答。 | 原问答保留；持久 Chat 为本轮另一链路，不能用 /synthesize 证明聊天历史。`frontend/src/SearchTools.tsx`; `src/facetmark/service.py:synthesize`; `src/facetmark/chat.py` |
| `GET /bookmark/{id}`、`GET /bookmark/{id}/related` | Reader 阅读、AI 概览/要点/原文与 related。 | 统一阅读 本轮实现；与图关系返回分别核对，不混入原始来源翻译。`frontend/src/Reader.tsx`; `src/facetmark/service.py:bookmark_record`; `src/facetmark/service.py:related_records` |
| `GET /sessions`、`GET /session/{id}` | App 保存会话列表/成员过滤；原 API/MCP 详情。 | 用户成员浏览保留，细节接口仍可用。`frontend/src/App.tsx`; `src/facetmark/service.py:session_record` |
| `GET /timeline` | ActivityTimeline、日期桶返回收藏过滤。 | 新桌面入口 本轮实现，有 AbortController、刷新/重试与旧数据保留；不是 Release 或聊天时间线。`frontend/src/ActivityTimeline.tsx`; `frontend/src/App.tsx`; `src/facetmark/service.py:timeline` |
| `POST /bookmark` | 扩展/外部保存；桌面手工新增走 /admin/library/bookmarks。 | 用户保存结果对等，写入本地库；不回写原浏览器。`frontend/src/LibraryTools.tsx`; `src/facetmark/service.py:save_bookmark`; `extension/src/background.ts` |
| `POST /open` | BookmarkCard/Reader 打开原链接并记录交互。 | 原契约保留；打开动作会写 interaction，不称纯读取。`frontend/src/BookmarkCard.tsx`; `frontend/src/Reader.tsx`; `src/facetmark/service.py:record_open` |
| `GET /queue/next`、`POST /queue/complete`、`GET /queue/stats` | 扩展 Channel B 正文队列；扩展设置显示连接/origin/token。 | 原协议保留。next 会租约队列，complete 写正文/抓取状态，扩展会打开 tabs；不能笼统说全只读。`src/facetmark/api.py:queue_next`; `src/facetmark/fetch/store.py`; `extension/src/background.ts`; `frontend/src/Settings.tsx` |
| `GET /link-health/summary`、`GET /link-health/{id}`、`POST /link-health/check`、`GET /graveyard` | HealthTools 汇总/检查/已确认失效与保存内容打开。 | 桌面入口和短持锁写判定/恢复 本轮实现；最多 50 条列表明示，不自动删收藏。`frontend/src/HealthTools.tsx`; `src/facetmark/api.py:AppState.check_links`; `src/facetmark/health/__init__.py` |
| `/karakeep/documents`、`/karakeep/documents/delete`、`/karakeep/search`、`/karakeep/clear`、`/karakeep/stats` | 原 Karakeep plugin API 随 sidecar 保留；集成设置展示统计/普通 token/实际 origin。 | 外部 add/delete/clear 是写操作，managed bookmark 保护保留；add/search 网络改独立连接 本轮实现。`src/facetmark/api.py:karakeep_add`; `src/facetmark/bridges/karakeep.py`; `src/facetmark/library.py:_rows`; `frontend/src/McpSettings.tsx` |
| `/bookmarks`、`/bookmarks/facets*`、`/bookmarks/folders/tree`、`/bookmarks/folders/path` | App 收藏分页、FacetBrowser 标签、FolderTree 目录。 | 原入口保留；移除站点分类 本轮实现，domain/host 查询仍保留有效过滤，不把浏览分类移除扩大为删 API 契约。`src/facetmark/workbench.py`; `frontend/src/FolderTree.tsx`; `frontend/src/FacetBrowser.tsx` |
| `/admin/library/bookmarks` CRUD、`bulk`、`taxonomy`、`export` | LibraryTools 新增/编辑/删除/批量移动和标签/目录标签管理/范围导出。 | 原管理保留；v2 full、相关不变量与任务互锁 本轮实现，待合成数据回归。`frontend/src/LibraryTools.tsx`; `src/facetmark/library.py` |
| `/admin/import`、`/admin/import/sources`、`/admin/import/source` | Setup 文件导入、发现选择来源；SiteImport 为另一路由。 | 元数据入口保留；v2 full 恢复与详细反馈 UI 本轮实现。显示真实主计数、四类恢复计数和警告，区分零新增、部分结果和恢复，不沿用旧统一“导入完成”判定。`frontend/src/Setup.tsx`; `src/facetmark/importers/__init__.py`; `src/facetmark/backup.py` |
| `/admin/index`、`/admin/jobs/start`、`resume`、`pause`、`current`、历史与 `cancel` | Tasks、收藏工具栏生成/抓正文、Reader 重做、ProcessingPreferences。 | 原任务管理保留；选择直接重做、无选择处理当前范围和语言/提示词快照 本轮实现。分别核对 index 阶段取消与独立任务持久目标恢复。`src/facetmark/admin.py`; `frontend/src/Tasks.tsx`; `frontend/src/App.tsx` |
| `/admin/settings`、`test`、`models`、`apply`、`/admin/agents` | Settings 独立 chat/embed、目录/Agent 自动检测、测试/保存/应用和思考/提示词。 | 思考模式和默认/指纹、ST runtime 服务描述与桌面 endpoint 迁移 UI 本轮实现。迁移区分实际运行值、草稿与待应用设置；测试默认未知不能伪称 medium。`src/facetmark/admin.py`; `src/facetmark/embedding_runtime.py`; `frontend/src/Settings.tsx`; `frontend/src/ReasoningSettings.tsx` |
| 原 stdio MCP 工具与 resources | 原 stdio 保留，新 HTTP /mcp/ 使用相同 9 工具/资源。 | HTTP/独立 token/SDK 协议探测 本轮实现；save_bookmark、probe=true 和模型合成的副作用按工具说明，非全只读。`src/facetmark/mcp_server.py`; `src/facetmark/mcp_http.py`; `frontend/src/McpSettings.tsx` |
| `/admin/updates/check`、`/admin/extension-status` | 设置中的更新检查、扩展近期连接状态。 | 原入口保留，不自动安装；使用本服务实际端口。`src/facetmark/workbench.py`; `frontend/src/Settings.tsx` |
| LibrarySync 增量同步 | SyncSettings → 用户共享目录 metadata DAG 的预览、冲突选择与应用前备份。 | 现有同步入口保留；可新增/修改/删除本地元数据，正文/聊天/向量/密钥不在同步范围。`src/facetmark/library_sync.py`; `frontend/src/SyncSettings.tsx` |

## 新接入与修复的真实范围

| 能力 | 本轮源码和入口 | 限制与待验证 |
| --- | --- | --- |
| 目标语言阅读与摘要 | `src/facetmark/enrich/prompts.py`、`schema.py`、`pipeline.py`；`frontend/src/Settings.tsx` 与 `Reader.tsx`；标题/摘要/要点同页，内置提示词可编辑恢复；本轮实现 | 原始标题/正文保留；AI topics 不自动覆盖用户 tags；未实现全文翻译。摘要/语言/提示词变化与失败保留旧结果须回归。 |
| 选择与范围处理 | `frontend/src/App.tsx`/`LibraryTools.tsx` → `src/facetmark/admin.py`；工具栏全选/生成、选中重做、无选择当前范围待生成/已变化；本轮实现 | 不新增长选择行，不重复要求同意/重做勾选；跨页 allMatching/排除、空结果和 stale preview 需回归。 |
| 持久聊天与范围 | `src/facetmark/chat.py`、`frontend/src/ChatWorkspace.tsx`、`App.chatWithSelection`；单篇/1–12 所选/整库、`/chat/scopes/resolve` 用同 CollectionScope 与排除；本轮实现 | 固定来源最多 12 个，来源预算 24k 字符；整库问题先检索保存内容，不把全部正文无限送模型。后台 JSON 生成/状态轮询，不是逐 token streaming。 |
| 聊天证据、Stop、重试、重新回答 | `chat._evidence/_answer/_history`、`MessageRequest.regenerate`、cancel/messages；来源 hash/时间/摘录/引用，任务取消/请求幂等；本轮实现 | Stop 要等真实 task 退出；重试失败/停止答案，重新回答追加答案并保留旧完整回答；前端最终按钮与快速交互需要本轮回归。网页与历史是数据，不成为工具授权。 |
| HTTP MCP 与诊断 | `src/facetmark/mcp_http.py` 和 `frontend/src/McpSettings.tsx`；默认关闭/独立 token/客户端配置/SDK lifespan/initialize+列表自检；本轮实现 | 原工具包含本地保存与主动健康写入，不称全只读；ASGI 协议自检不是外部 socket 客户端已连通，Windows frozen 依赖闭包待回归。 |
| 网站导入 | `src/facetmark/crawl_jobs.py`/`crawl.py`、`frontend/src/SiteImport.tsx`；seed HTTP(S)，同站/1–500 页（默认25），robots/隐私、进度/取消；本轮实现 | 保存上次任务参数/统计，重跑按 URL 去重且复用已有正文；没有持久化精确 BFS frontier，不能称精确断点续爬。 |
| 模型额度与恢复 | `src/facetmark/providers.py:_request_budget/_retry_after/_post`、`local_agents._agent_quota`、`ProcessingPreferences.tsx`；固定用户上限、逐 HTTP 尝试 RPM 与 Retry-After、Agent quota；本轮实现 | 同一服务进程内、同目录/端点/账号/RPM 配置共享；不是跨独立 OS 进程全局限速，也不是所有模型通道一个并发门限。等待过长返回可重试状态，不截短服务端截止。 |
| 长网络操作与服务响应 | `api.AppState.model_operation/check_links`、`health.persist_lock`；search/synthesize/Karakeep 使用独立连接，健康短事务锁；本轮实现 | 保留处理/配置/导入互锁；不因移锁宣称所有组合无数据竞争。慢服务时取消、普通读取、外部桥接须回归。 |
| 可恢复 JSON v2 full | `service.export_reading_data/export_bookmarks`、`library.export_library`、`importers`、`backup.prepare/restore/export_conversations`；本轮实现 | 补齐缺失正文/AI 派生与聊天，已有本地副本不覆盖；来源 hash 校验，按 URL 重映射聊天引用、缺 pin 保留范围限制。范围导出仅纳入完整位于范围内的会话。普通备份无密钥/向量。 |
| CLI 输出与有效诊断提示 | `cli.config_show_cmd` 遮盖四类凭据；`diagnose` 提示设置测试/应用备份重建后 index；本轮实现 | 不运行真实 config show 读取密钥；需合成设置验证表格/JSON 及实际恢复路径。 |
| 可选本地 ST runtime | `embedding_runtime.local_embedding_runtime/local_embedding_error`、`admin.settings_view`/`providers` 与 `frontend/src/Settings.tsx`；支持描述和迁移 UI 本轮实现 | frozen 桌面明确不含 ST；Python extra 可用性检测不等于模型已加载/向量兼容。endpoint 迁移需测试、保存、应用；向量变化仍用既有备份重建确认。 |

## 不应计为已完整桌面移植的能力

- frozen sidecar 的 `desktop.main()` 只接 `--self-test`、`--parent-pid`、`--data-dir`；迁移/doctor/config 来源/serve 部署/eval/demo/stdio MCP 运维留 Python CLI/CI。不能给安装用户不存在的 facetmark-service.exe 子命令。
- 原 `POST /suggest` 为编辑器/Agent 上下文提供本地词法推荐；`/suggest/query` 是语法补全。桌面没有单独草稿编辑器，两者不互相充当覆盖证明。
- 手工来源管理和 Karakeep managed 合约保留；AI topics 与 bookmark.tags 分开。Release/GitHub Stars/Lists/Fork/Gist 写操作、公共代码检索、全文翻译、feeds、WebDAV、Node 插件均未复制，理由在参考比较中逐项说明。
- 完整 index 是阶段取消/按指纹重跑；独立 fetch/summary 是持久目标快照；Crawl 是保存统计/参数后重跑复用页面。三个恢复语义不得合并成一句“精确续传”。
- JSON full、HTML/metadata JSON、metadata sync、应用前 SQLite 备份范围不同。便携 full 保存阅读/聊天，但不包含密钥/向量/完整任务历史/健康运维日志；共享目录只同步书签元数据。

## 本轮收尾核对

详细导入反馈、SiteImport 挂载、ST 前端迁移控件及重新回答按钮均已落盘；当前合成浏览器用例通过，覆盖以下收尾项目：

1. Setup 展示 parsed/新增/更新/去重/non-indexable/缺日期/隐私跳过/恢复正文摘要聊天/警告，零有效与部分成功不统一冒充完整成功。
2. Settings 明确 endpoint/local 当前 backend、packaged ST 不支持原因和切回 endpoint；测试/保存/应用不沿用不兼容向量或过期 probe，Python installed 状态不称模型加载验证。
3. Chat 选中范围最多 12 条且不静默丢隐私条目；重新回答保留旧完整答案、失败可重试；按钮、请求幂等与 Stop-before-delivery 顺序须覆盖。

## 本轮 GitHub Actions 验证清单

`81f310a` 已通过四条工作流：[CI 40161317356](https://github.com/88lin/facetmark/actions/runs/40161317356)、[收藏 40161403094](https://github.com/88lin/facetmark/actions/runs/40161403094)、[体验 40161402936](https://github.com/88lin/facetmark/actions/runs/40161402936) 与 [Windows 40161402706](https://github.com/88lin/facetmark/actions/runs/40161402706)。浏览器矩阵 150 通过 / 2 跳过、收藏专项 84/84、独立 200k 浏览器 1/1，四组 Python、真实 stdio MCP 22/22、frozen TCP MCP 与安装检查均通过。具体计数和截图范围统一见 [桌面补齐记录](desktop-completion-2026-10-25.md)。下列契约已纳入该轮回归；构建、模型模拟服务、包安装和所有运行均使用 Actions 隔离合成数据，不操作真实浏览器资料。

1. **原导入与备份**：HTML/Chromium/v1/v2、BOM/编码、重复幂等、隐私/日期/去重警告、零有效与恢复计数；正文/AI title/summary/key_points/语言/提示词/聊天引用 round-trip，已有本地内容保留，坏备份整体拒绝，密钥/向量不进入便携文件。
2. **原检索与管理**：FTS/CJK/查询语法/depth 分页、向量兼容与设置备份重建；CRUD/标签/目录/外部管理保护，原链接 interaction、session/date 回跳、快速请求防串结果。
3. **处理与额度**：完整七阶段 index、独立 fetch/summary pause/cancel/resume、选择/排除/范围快照、语言/提示词变化与失败保留；同服务 provider 实例共享 RPM/Retry-After、每次重试计数、Agent quota、Stop 取消冷却/排队/子进程。
4. **新聊天与 MCP**：单篇/多选/整库来源、超限/隐私/删除来源、消息持久/历史分页/删会话、幂等/重新回答/Stop/retry/引用恢复；MCP 默认关闭、独立 token 轮换、initialize/tool/resource、实际安装 sidecar/client transport，模型和写工具副作用分别核对。
5. **原集成与新网站导入**：合成浏览器来源发现/选择、扩展 Channel B、Karakeep managed 数据与慢网络响应；Crawl 范围/robots/隐私/页数/取消 join/重启 interrupted/重跑复用正文；本地 ST 不可用状态与 endpoint 回切。
6. **布局与桌面**：统一阅读/目录高度/字号/进度/窄屏/键盘/reduced motion、现有工具栏全选与生成、不恢复站点分类、托盘外围玻璃移除；启动/配对/退出/兼容服务复用/端口冲突、frozen import closure 与 Windows 安装 WebView smoke。

技术结果与安装运行证据对应当前提交/run/artifact；用户视觉评价仍未取得。本记录保留 CLI/CI、frozen ST、备份和取消语义的明确边界，没有因云端通过而把未移植能力改为桌面已覆盖。
