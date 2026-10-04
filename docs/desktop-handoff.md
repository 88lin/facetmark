# Facetmark 桌面化与体验升级：新对话接续提示词

你正在接续已获授权的实现任务。请先核对工作区和远端现状，然后继续完成实现、GitHub Actions 验证和可审阅交付，不要重新从规划开始。本文记录于 2026-10-03，后续代码和 Actions 状态可能变化，应以现场核对为准。

## 1. 用户目标与不可违反的约束

- 项目目录：`C:\Users\Computer\Desktop\web\facetmark`。
- GitHub：`https://github.com/88lin/facetmark`，远端为 `origin`。
- 当前测试分支：`desktop/facetmark-experience`。复用此分支，不改 main，不自动合并或发布正式 Release。
- 用户已授权在测试分支进行提交、推送和 GitHub Actions 测试。继续推进这些操作，无需反复请求确认。
- **所有桌面打包、大文件下载、大型程序运行和安装测试必须在 GitHub Actions 上完成，不能在用户电脑进行。** 不在本机安装 Rust/MSVC/PyInstaller，不下载或运行安装包、WebView2、大模型，不运行会修改系统环境的安装测试脚本。只做源码编辑与轻量检查；前端构建和浏览器验证优先安排在 Actions。
- 保护真实浏览器配置和书签；导入只能读取，不能写回、修改、删除原始浏览器资料。不使用真实书签做截图演示。
- 不覆盖或回滚已有未提交工作。当前未提交改动来自上一对话的实现草稿，需要阅读、完善和测试。
- GithubStarsManager 仅用于拓宽知识和吸取工程经验，**不是 UI 参考，不仿制其界面或复制功能清单**。Facetmark 应独立设计，把更好落实到安装可靠性、配置效率、检索效率和视觉品质。
- 任务是完整实现，用户重视页面好看。不要只交付壳、静态演示或重复输出方案。

## 2. 已确认的实现方向

首发 Windows 10/11 x64，采用 Tauri 2 + Python 后端 sidecar；React + TypeScript + Vite + Tailwind CSS，共享 Web/桌面界面，shadcn/ui 或 Radix 作为基础组件，Lucide 图标。

安装包采用 NSIS 当前用户安装，携带 PyInstaller 目录模式的 Python 后端和 WebView2 离线安装器。不包含 PyTorch 或大型本地模型。本地 AI 优先连接用户已有 Ollama 等兼容服务。继续支持 Python 包、CLI、Docker，前端构建结果随 Python 包交付，用户无需 Node 构建步骤。

桌面管理启动、就绪检测、异常恢复、重复启动聚焦、托盘、快捷键；关闭主窗口默认驻留托盘，首次提示，开机启动默认关闭。每个数据目录只有一个受管实例；优先 8787，冲突自动换端口；复用已有服务需要验证版本、认证、数据库身份。升级前备份，卸载默认保留用户数据。首版有检查更新/下载安装入口。缺少签名时明确是未签名测试包，不承诺消除 SmartScreen 提示。

界面采用三栏检索工作台：

- 左栏：搜索、全部书签、浏览批次，文件夹/标签/站点筛选；任务和设置在底部。
- 中栏：固定搜索区、筛选条件、紧凑结果列表；标题、摘要、命中片段优先，技术解释按需展开。
- 右栏：正文、AI 摘要、标签、相关书签；切换预览保持搜索条件和列表位置；原网页在系统浏览器打开。
- 全部书签是真实分页列表，不再只是统计看板；索引统计进入任务/诊断。
- 纸白、石墨灰基础，紫色仅作为品牌与选中/主操作强调。去掉手绘虚线、奶油大底、糖果大色块，形成精致、一致、信息密度合适的工作界面。
- 中英文、明暗主题、中文本地字体栈、离线资源、键盘导航、Ctrl+K、可关闭桌面快捷键、窄窗口预览抽屉和 Web 小屏适配。
- 保留现有中文输入法保护、请求取消/过期响应隔离、稳定分页、快捷键行为。加载/空库/无结果/部分索引/模型失败/断线都有真实状态和恢复操作。

连续首次向导：导入书签 -> 分别配置聊天与向量 -> 独立测试两条连接和实际向量维度 -> 明确确认后索引 -> 开始检索。支持拖放 HTML/JSON 和用户主动选择发现的 Chromium 来源；不自动读取所有个人配置。云端索引前说明发送内容并确认，不偷偷启动全库处理。不填 Key 可跳过 AI 使用关键词检索。真实工作流不能静默降级为 mock，mock 只保留显式 demo/test。

任务状态统一管理，页面切换不丢失；取消在安全阶段边界生效；重启提示中断并利用指纹机制跳过已完成部分。没有细粒度进度时用不确定进度，不伪造百分比。扩展提供安装说明、连接状态、UI 复制配对信息入口，不能声称自动安装浏览器扩展。

## 3. 已提交且已推送的工作

当前远端分支 HEAD：`2aefc60b3358987531a08bd931d45539a4cc4027`。

提交：

1. `d97a832 feat(desktop): 建立 Tauri 外壳与云端离线安装验证`
2. `3f1c6b1 fix(desktop): 包含启动页 HTML 资源`
3. `2aefc60 fix(build): 修正 PyInstaller spec 相对路径`

已创建的关键文件：

- `.github/workflows/desktop.yml`：`desktop/**` 分支 push / workflow_dispatch，Windows hosted runner 构建并验证，上传预览包/证据和依赖锁文件，不发布正式 Release。
- `desktop/package.json`、`desktop/src-tauri/Cargo.toml`、`build.rs`、`tauri.conf.json`、`capabilities/default.json`、`src/main.rs`。
- `desktop/splash/index.html`、`loading.js`：本地启动/失败重试页面。
- `desktop/freeze.py`、`desktop/facetmark.spec`：PyInstaller 目录模式打包，不包含大型模型栈。
- `scripts/desktop_assets.py`：CI 内生成小型应用图标并 staging sidecar。
- `scripts/desktop_smoke.py`：冻结程序自检、清理子进程 PATH 排除 Python、中文/空格路径、8787 冲突、authenticated runtime、重复实例、优雅停止、保留 DB。
- `scripts/desktop_install_smoke.ps1`：**仅 GitHub-hosted runner 可运行**，卸载已有 WebView2、验证缺失、针对安装程序/应用配置出站防火墙阻断、静默安装、启动桌面与后端、检查 WebView2 进程。绝对不能在用户机器执行。
- `src/facetmark/desktop.py`：数据目录锁、端口保留、已有服务认证验证、备份、JSON stdout readiness、stdin stop、父进程监控、原生扩展/分词/抽取/静态资源自检。
- `src/facetmark/admin.py` 的已提交部分增加受保护 `/admin/runtime`，返回 service/version/database_identity，不暴露完整路径。
- `.gitignore`：忽略 Tauri target/binaries/icons、临时构建目录，允许 splash/frontend HTML。

## 4. 云端验证的真实结果

最新 Actions run：`37124179483`，链接：
`https://github.com/88lin/facetmark/actions/runs/37124179483`

2026-10-03 本次交接已实时查询：run completed / success；冻结后端、Tauri 离线 Windows 安装包构建、冻结程序隔离验证、安装和启动 smoke、artifact 上传全部 success。

云端冻结服务日志显示 startup_seconds 为 `0.94`；这是该 runner 一次结果，不是对普通机器的性能承诺。

Artifacts（14 天保留，后续需重新确认未过期）：

- `facetmark-windows-x64-preview`，id `11274404619`，zip size `276577455` bytes（约 276.6 MB / 263.8 MiB）。这是整个 artifact 的 ZIP 大小，**不能直接当作安装 EXE 文件大小**。
- `desktop-dependency-locks`，id `11274790575`，size `31972` bytes。包含 CI 生成的 desktop/package-lock.json 与 Cargo.lock。目前尚未下载并提交这些锁文件；可只取这个小 artifact，不下载大安装包。

测试边界：当前 runner 是 windows-latest Windows Server 2025，不等价于 Windows 10/11 全覆盖；防火墙只按已列程序阻断，不是整机物理断网；目前没有视觉截图证明工作台/WebView 内容正确，也未验证全套升级卸载/普通非管理员用户行为。报告时必须明确这些边界，不把 smoke 说成完整验收。

先前 run `37123912149` 因 PyInstaller spec 把脚本路径解析为 desktop/desktop/freeze.py 失败，已在 2aefc60 修好；更早 run 被新 push 取消。这些不是当前阻塞。

## 5. 当前本地未提交草稿：必须继续完善

`git status --short` 当前有且只有以下 4 个源码修改（交接文档加入后会多一个未跟踪文件）：

- `src/facetmark/config.py`
- `src/facetmark/providers.py`
- `src/facetmark/cli.py`
- `src/facetmark/admin.py`

草稿共约 156 additions / 26 deletions，尚未 lint、单测或 push，不能把它当作完成能力。

已写入的草稿内容：

- config：新增 chat_base_url/chat_api_key/chat_allow_no_key、embed_base_url/embed_api_key/embed_allow_no_key；重写 settings sources 合并，尝试在每个来源内部展开 legacy 统一配置，保持来源优先级；channel_settings/channel_ready；免 Key 只允许显式 loopback。
- providers：get_provider 使用两个通道，可复用相同服务，复用 SplitProvider；新增 UnconfiguredProvider；缺少 Key 不静默用 mock；免 Key 不发 Authorization。
- cli：index 未配置真实聊天/向量时明确退出，不再 silently mock。
- admin：新增可写双通道字段和 ProbeRequest 字段，短 Key 脱敏，尝试锁住环境变量派生通道；settings_view 返回 channels；JobRunner 新增历史任务持久化/恢复草稿与 shutdown。

必须重点检查：

- 来源合并、model_dump 后重新构建 Settings、legacy/channel 字段冲突及跨来源密钥继承是否严格满足计划。不能把不同服务 Key 意外转发。
- 新增双通道字段的 env_locked 过于粗糙可能阻止合法编辑；settings_view 对无效 URL 的异常处理和旧 UI 兼容尚未验证。
- get_provider 构造 local embed 失败时聊天 HTTP client 是否泄漏，显式 mock + local 行为和旧测试预期需要审查。
- probe 实现还基本是旧逻辑，需要分别测试通道，确保无 Key 本地接口、维度探测、未保存草稿及错误脱敏正确。
- JobRunner.persist 尚未在任务最终状态写入，api.AppState 尚未传 data_dir，lifespan 尚未接 shutdown，所以任务恢复未打通。
- 所有新行为要写有意义的兼容/安全回归测试，不能只修改旧测试让它们通过。

## 6. 上一轮失败的 patch：没有落地，别误判为已经完成

最后一次 apply_patch 同时两次更新 api.py，工具报错：
`invalid patch: multiple operations target .../src/facetmark/api.py`

2026-10-03 已核对：`src/facetmark/workbench.py` 不存在，该整批 patch 未应用。以下功能仍未实现：

- JobRunner 最终状态持久化、shutdown interruption、api 生命周期接入。
- `/admin/index` 对未配置模型和 pending settings 的检查；`/admin/job` 读取 previous。
- 保存/测试模型时 endpoint 更换不继承旧 Key；运行任务期间修改设置保护；完整错误脱敏与 probe fingerprint。
- `/admin/import/sources` 和 `/admin/import/source`：建议用 server HMAC source ID 映射重新发现的来源，不接受任意客户端路径，保留 admin gate，文件限制 64 MB。
- `/admin/setup-status`：配置、真实测试、有效索引、mock/demo、pending apply 分开表达。
- 受控向量模型变更/重建：不能混用旧空间，先备份、确认后应用并重建，保持书签正文。上轮草稿想增加 `/admin/settings/apply`，但实现需重新审查设计与事务正确性。
- `/bookmarks` 分页和筛选以及 `/bookmarks/facets` 统计接口：全部书签浏览的后端基础，需参数化 SQL、权限、稳定排序、分页和大库测试。

## 7. 尚未开始的主要交付

`frontend/`、`PRODUCT.md`、`DESIGN.md` 都不存在。当前 Web 仍是原版原生 ES modules；Tauri 目前承载旧 `/app`，没有新 React 三栏工作台、连续向导、主题改版或新截图。

后续还需要：

1. 完善并验证上述后端草稿、新接口和兼容性。
2. 产品记录、设计方向契约、React 工作台及基础组件、搜索/全部书签/批次/预览/摘要/任务/设置/向导，迁移原功能。
3. CI 构建 React 并打进 Python wheel 和 desktop；Docker 同样交付完整静态资源。开发源码与 build output 的跟踪/发布策略要明确，不能让 pip 包依赖用户自行 npm build。
4. 扩展连接说明、复制 pairing 数据和动态端口衔接。
5. Actions 中前端 typecheck、行为测试、Playwright 中英文/明暗/桌面小屏/中文输入/竞态/分页/焦点/对比度，生成真实截图并审阅。
6. 官网下载安装文案与真实产品截图，README、配置/桌面说明，设计规范。
7. 小型依赖锁文件入库、构建版本一致、签名配置和未签名 preview 标注、更新入口完善。
8. 云端最终安装回归和 artifacts，测试分支可审阅交付；未经用户明确要求不合并 main 或正式发布。

桌面已提交代码也需工程审查：startup 失败/超时/retry、窗口关闭退出路径、single-instance 是否符合每数据目录语义、父进程清理与后台索引退出、tray Preferences 写入失败、快捷键注册失败反馈、远程页面无 IPC、更新入口是否满足检查更新。构建成功不代表这些均正确。

## 8. 已有验证与项目位置

在桌面新增代码初步写好时，轻量 lint、py_compile、源代码 self-test 通过；源代码 self-test 返回 sqlite_vec v0.1.9 和 frozen=false。没有本地构建或运行大安装包。

方案阶段（双模型草稿之前）执行过：

- `pytest -q tests/test_admin.py tests/test_settings_safety.py tests/test_configfile.py tests/test_model_access.py tests/test_discovery.py`：169 passed / 15 skipped。
- `node --test tests/web/api.test.mjs tests/web/paging.test.mjs tests/web/i18n.test.mjs`：63 passed。
- 这两项是旧状态基线，**不验证当前双模型草稿**。

源码主要位置：src/facetmark/config.py、configfile.py、providers.py、admin.py、api.py、service.py、db.py、migrations.py；原 Web 在 src/facetmark/web；扩展在 extension；官网在 docs/landing。

已有 scripts/browser_check.py 使用合成 mock corpus 和 Playwright 验证。测试 tests/test_web.py 把旧 palette、字体、tabs、sketch 等写死，需要有意识迁移成新界面契约，保留行为/安全/资源检查。CI 现有 .github/workflows/ci.yml 对 main push 与 PR 触发，测试分支 push 只触发新 desktop workflow；可创建 draft PR 或新增适当 branch validation，使后端/frontend 回归能在云端运行。

## 9. 接续执行要求

先运行轻量只读检查：git status、当前分支、git diff、最新 Actions。保留未提交草稿，核对本文现状，之后继续实现。

使用 apply_patch 编辑；不要复制本交接文本进客户端 bundle。常规维护不需要扩散改动。

用户已经确认技术路线、三栏布局、视觉基础和实施计划，不要重复问同样的方向问题。适用 Impeccable 进行独立设计；其 instructions 路径为 C:/Users/Computer/.agents/skills/impeccable/SKILL.md。上一对话已读取 context/init/new-work/craft-floor，但新对话需要自行读取适用规范。用户已明确选择的设计优先于技能的随机方向；不要再开启一个无关风格竞赛。遵守用户对大文件/本机运行的限制，必要的截图与检查放 CI。

每 30-60 秒简洁更新进展。实事求是区分已提交、未提交草稿、Actions 验证、仅检查源码、未验证的环境。遇到失败查看日志、修复并重跑，不把任务停在建议或半成品。最终给用户测试分支、Actions、安装产物和截图入口，说明实际完成项、测试结果与剩余限制。
