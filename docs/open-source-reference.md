# 书签工作流参考与实现边界

本轮响应 2026-10-11 的产品反馈：原网页应直接打开、摘要在集合内浏览、20 万条书签可按范围批量处理，并复用本机 Agent 的登录。

- [GithubStarsManager](https://github.com/AmintaCCCP/GithubStarsManager/tree/3dc524bb9a85890118618af27fe6e86c0e585f1c)，MIT。参考 RepositoryCard、RepositoryList、BulkActionToolbar、CategorySidebar 和 AIConfigPanel 的职责拆分：外链与详情分开；列表展示摘要；集合工具栏提供未分析、失败重试和批量操作。Facetmark 保留白色、湖蓝与清晰的控件层级，使用 SQLite 分页和服务端选择范围，避免将整个大库载入前端。
- [open-design](https://github.com/nexu-io/open-design/tree/17e255959703a3fad7c8eb7f7b70dcafccc5629a)，Apache-2.0。参考 daemon 的运行时发现、Windows npm 启动器处理、stdin 提示词与 JSON 事件适配。Facetmark 的 Python 实现支持 Codex、Claude Code 与 OpenCode，复用 CLI 身份与模型配置，限制摘要调用的工具权限。没有搬入设计代理的宽权限执行方式。
- [OpenCode 1.19.0](https://github.com/anomalyco/opencode/tree/v1.19.0)，MIT。核对 `run` 的 stdin／JSON 事件、`--pure`、JSONC 配置合并、认证路径与 `OPENCODE_DB` 隔离行为后实现独立 Python 适配；使用真实 CLI 和模拟 HTTP 模型服务做 Windows／Linux 回归。支持范围见[本机 Agent 连接](local-agents.md)。

以上为独立实现的工作流与接口参考，未直接复制上游组件源码。具体入口是 `frontend/src/BookmarkCard.tsx`、`CollectionTools.tsx`、`src/facetmark/local_agents.py`、`processing.py`。

## 连接约定

API 服务仍可使用。测试与保存使用同一份聊天配置（包括备用模型），成功测试的指纹随本地配置持久化；配置改变后旧测试失效。只在端点明确拒绝 `response_format` 时回退普通 JSON 文本模式。摘要与向量测试相互独立。

本机 Agent 使用已有 CLI 登录，不读取浏览器资料。Codex 需要支持 `exec --json --ephemeral --ignore-user-config --ignore-rules` 的版本，保留原认证存储，只复用模型与服务白名单设置；provider 中的凭据经子进程专用环境变量传递，不放进命令行或日志，也不改写原配置。Claude Code 使用 print JSON、空工具集、严格空 MCP 配置和禁用 hooks。真实账号连通性由用户在设置页执行测试确认；CI 覆盖独立子进程夹具，并额外在 Windows／Linux 安装真实 OpenCode 1.19.0，对接隔离的模拟模型服务；不声称测试过用户的账号。

## 大库处理约定

范围包含关键词、分类、站点、标签、批次、摘要状态和有限排除列表。启动时将目标存入数据库；摘要按有界并发分批读取，正文在 SQL 读取时限长。暂停等待当前已派发批次落盘，续跑只读取原快照中的 pending 项。单条摘要、派生索引失效与完成标记在同一事务提交。任务元数据按 ID 保留，开启新任务不会抹去旧任务恢复记录。

## 桌面外链与 sidecar

[tauri-plugin-shell 2.4.0](https://github.com/tauri-apps/plugins-workspace/tree/shell-v2.4.0/plugins/shell)
默认向 WebView 注入旧的 `_blank` 点击拦截，先阻止默认导航再调用 shell IPC。
工作台没有该权限时，实际点击会报 `shell|open not allowed by ACL`，无法抵达原生外链回调。
`desktop/src-tauri/src/native_shell.rs` 用公开的 Tauri Plugin 接口委托官方 shell 插件的
Rust 初始化和事件生命周期，保留 sidecar API，省去网页初始化脚本与 IPC 接口。
sidecar 的进程创建、编码、事件读取仍由原库负责。

[tauri-plugin-opener 2.7.0](https://github.com/tauri-apps/plugins-workspace/tree/opener-v2.7.0/plugins/opener)
也会默认拦截网页链接，因此显式关闭 `open_js_links_on_click`。HTTP／HTTPS 外链统一由
原生 `on_navigation`／`on_new_window` 回调交给系统浏览器；没有为工作台扩大 shell 权限。
安装验收观察一次性回环网页的实际请求，若失败才运行独立 OS 对照；对照成功不能代替应用点击通过。

所有构建、浏览器、20 万条规模与安装验证在 GitHub Actions 执行。验证结果另记录在 `desktop-handoff.md`，未执行的项目不得标成通过。
