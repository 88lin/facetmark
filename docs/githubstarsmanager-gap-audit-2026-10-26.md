# GithubStarsManager 功能对照与可用性修复 · 2026-10-26

用户本次反馈：当前仍有大量问题，思考档位不能顺畅自行选择，保存过的 AI 连接又被要求测试，
全选控件不清楚，浏览批次外观、长文本和鼠标横向浏览不可用。用户对当前整体体验未认可。
这份记录取代“功能已经补齐”作为本轮完成度依据；旧云端通过仅证明旧提交的检查范围。

## 2026-10-28 源码复核与接续修复

参考项目更新到 [`22fecdf`](https://github.com/AmintaCCCP/GithubStarsManager/tree/22fecdfd957919636f02a20f934bce6b92364b1d)。
与下表原对照版本 `aa1e3c7` 相比，共 19 个提交、27 个文件变化。本次使用 Git tree/blob
核对已有资料：含 README 在内的 85 份资料中 79 份未变，6 份功能源码变化；另读取
11 份当前生产源码，覆盖新增流水线及调用它们的搜索和列表入口。没有运行参考
应用，也没有使用个人账号数据；以下新增结论来自源码，而非 README 的功能描述。

| 新增或变化 | 参考实现 | Facetmark 的实际边界 |
| --- | --- | --- |
| 多路搜索与阶段回退 | [vectorSearchPipeline.ts](https://github.com/AmintaCCCP/GithubStarsManager/blob/22fecdfd957919636f02a20f934bce6b92364b1d/src/services/vectorSearchPipeline.ts)：原始查询、HyDE、关键词、结构化信号融合，各阶段预算、取消和回退诊断。 | 已有词法/向量融合、意图理解、上下文、可选重排、图扩展与无向量退化；算法和召回质量不是相同实现，仍需独立语料评测。 |
| 交叉编码器重排 | [crossEncoderReranker.ts](https://github.com/AmintaCCCP/GithubStarsManager/blob/22fecdfd957919636f02a20f934bce6b92364b1d/src/services/crossEncoderReranker.ts)：仅在配置 SiliconFlow 时使用固定 BGE 模型；校验索引和分数，失败回退。 | 不能把“有重排”写成已支持参考项目的远程 BGE 协议；此远程协议尚未提供独立连接入口。 |
| 相似内容专用召回 | [similarRepositoryPipeline.ts](https://github.com/AmintaCCCP/GithubStarsManager/blob/22fecdfd957919636f02a20f934bce6b92364b1d/src/services/similarRepositoryPipeline.ts)：源仓库资料、可选 README、本地/AI 画像、语义与关键词召回及重排。修复返回与自定义排序下的相似视图。 | 本项目 `/bookmark/{id}/related` 读取已保存的关系图；它不等价于实时双路相似内容搜索。这是新增明确差距。 |
| 思考输出中的 JSON | [aiService.ts](https://github.com/AmintaCCCP/GithubStarsManager/blob/22fecdfd957919636f02a20f934bce6b92364b1d/src/services/aiService.ts)：处理模型内容中的思考标签，避免其中括号干扰 JSON 解析。 | 发现本项目同类问题并修复：仅移除开头完整的 `<think>` 块，保留最终 JSON 字符串中的字面标签；只有思考或思考被截断时仍报错，不保存其中的草稿。API 与 Agent 共用此解析入口。 |

本轮完成的具体修正：

1. 测试成功后主操作是“保存连接”，已保存显示“已保存”；保存失败保留测试结果，
   重试只发送保存请求。更换模型、凭据、思考参数仍需重新测试，未变配置可直接使用。
2. 聊天临时问题/回答使用不重复的本地编号，消除时间戳跨毫秒导致的 React key 碰撞。
3. 320/390px 批次行的标题使用整行宽度；加载更多失败后重试原页且保留已加载行，
   整理失败重试整理操作。截图复查后进一步缩短月份卡片内重复年份的日期范围，
   避免日期末位挤到下一行；月份卡片宽度随窄屏收缩，避免右侧数量被裁掉。
   完整日期保留在无障碍名称和提示中。
   日期滚轮、箭头和键盘延续上轮实现并参与回归。
4. JSON 思考块问题先用合成输出复现 6 项失败，修正后 JSON、请求档位传递和连接复用
   22 项通过；批次事务另有 2 项通过。语法、Ruff 与 UI 静态检查通过。
5. 完整体验超时从 25 调整到 40 分钟，覆盖原本来不及执行的视频和发行包内容验证。

当前 Actions、截图复核与遗留项目统一见 [交接记录](handoff-usability-2026-10-26.md)。
下表保留原固定版本的完整功能对照，以上补充覆盖这两天的生产代码差异。

## 源码依据和核对方法

- Facetmark 基线：`main@9eeefd0`，发行版本 2.1.0。本轮为其上的未发布修复。
- 参考项目：[AmintaCCCP/GithubStarsManager](https://github.com/AmintaCCCP/GithubStarsManager)，
  本次查询 HEAD 为 `aa1e3c7473511132758c94a0b2365db6288c1eba`。
- 与上次检查的 `2f41b01c79d9e4ed11752592fa4c6cbb837e342a` 对比，变更仅在依赖清单和锁文件。
  对照当前 Git tree 校验了已取得的 84 份组件、hooks、服务和桌面源码：77 份 Git blob 完全一致；
  7 份转换 CRLF 为 LF 后一致。不存在功能源码版本差异。
- 重点重新读取模型配置、连接测试、思考请求、设置持久化、阅读器、选择工具栏和列表实现，
  再与本项目设置、任务、批次、阅读和导出源码对照。没有运行参考项目或使用真实账号。
- 下表的“现有”指当前源码有完整入口和实现，并不代替本次运行验证。参考项目也有边界，
  例如部分协议未发送 effort、部分队列只保存在内存、更新检查不负责自动安装。

## 完整功能对照

参考源码链接统一固定到上述 HEAD；同组的配套 hook/service 见目录内源码。

| 功能组 | GithubStarsManager 的实际功能 | Facetmark 对照、缺口与本轮处理 |
| --- | --- | --- |
| Stars 与 Lists | [GitHub API](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/services/githubApi.ts) 全量分页同步 Stars；Lists 拉取和回写；保留手工字段。 | 本项目是普通收藏库，现有 HTML/JSON/浏览器导出导入、来源去重与原数据保留。没有 GitHub 账户 Stars/Lists 双向连接器；不会把 GitHub 登录变成普通收藏的前置条件。 |
| 批量粘贴导入 | [useBatchStarImport](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/features/repositories/hooks/useBatchStarImport.ts) 候选预览、去重、逐项失败、输入历史。 | 有文件导入报告和受限网站爬取；缺少通用“粘贴多个 URL → 预览 → 导入”的工作流和统一导入历史。保留为明确功能缺口。 |
| 目录管理 | [CategorySidebar](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/components/CategorySidebar.tsx) 分类图标、颜色、隐藏、排序；分类锁。 | 有精确文件夹路径、子文件夹展开、标签、重命名/合并/移动；AI 不改写手工文件夹。缺少用户自定义目录颜色/图标及拖动排序。按用户要求继续不提供站点分类。 |
| 手工编辑优先 | [RepositoryCard](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/components/RepositoryCard.tsx) 手工描述、标签、清空语义与原始内容分开。 | 现有原标题与 AI 标题分开；修改影响内容的字段会撤销相关派生索引，失败再生成保留旧内容。没有独立手工批注/笔记字段。 |
| 批量选择与动作 | [BulkActionToolbar](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/components/BulkActionToolbar.tsx) 计数、全选、分类、锁定、订阅、Unstar。 | 有跨页摘要选择、移动、标签、导出、删除。本轮把全选做成有完整边界、勾选/半选图形和明确数量的胶囊控件，仍位于现有工具栏；不复制参考项目新增底部选择栏的做法。 |
| 关键词搜索 | [repoSearch](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/utils/repoSearch.ts) 多字段、分词、筛选、排序。 | 已有原标题/AI 标题/摘要/标签/文件夹搜索，日期语法、处理状态、排序与服务端分页。无需 AI。 |
| AI 搜索和相似内容 | [useSearchActions](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/features/repositories/hooks/useSearchActions.ts) 向量、HyDE、重排、关键词回退；相似仓库。 | 已有关键词/语义模式、检索解释、相关收藏、可选向量；不是必须配置两个模型才能使用收藏和摘要。 |
| 向量维护 | [vectorSearchService](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/services/vectorSearchService.ts) 增量版本、批次、缩短重试、索引状态。 | 已有向量空间指纹、备份重建、状态和 HTTP embedding；冻结桌面包仍不含进程内 Sentence Transformers。这一限制未改变。 |
| 模型连接管理 | [configurationSlice](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/store/slices/configurationSlice.ts) 多套命名 AI/embedding 配置、切换当前连接。 | 本项目有单套当前聊天/向量连接与 Codex/Claude/OpenCode 自动检测。**仍缺多套命名连接档案**；不能把 Agent 之间的临时草稿称为配置档案。 |
| API 协议 | [aiService](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/services/aiService.ts) Chat、Responses、Anthropic、Gemini 与兼容提供商分支。 | 当前直接端点仍是 OpenAI Chat Completions 兼容协议；Codex/Claude/OpenCode 通过 CLI 使用。没有原生 Responses/Anthropic/Gemini 端点适配；这是协议覆盖差距。 |
| 思考档位 | [AIConfigPanel](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/components/settings/AIConfigPanel.tsx#L575) 固定档位选择；部分请求分支使用 effort，部分没有使用。 | 本轮补出 high/xhigh/max 快捷选择；目录不再限制用户尝试标准 effort。OpenCode 使用实际变体，并保留自定义入口；API effort 支持自定义。开关格式仍明确只有开/关，不能假装 max 已生效。实际支持由连接测试确定。 |
| 连接测试与重开 | [useAIConfigActions](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/features/settings/hooks/useAIConfigActions.ts) 保存的配置与一次测试操作分开。 | 本轮修复草稿测试覆盖旧验证、无关默认配置使显式选择失效、重复模型目录加载、相同选择制造脏状态，以及保存后仍提示重复选择。重新打开显示“已保存，可以直接使用”。 |
| 生成语言与提示词 | [aiLanguage](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/i18n/aiLanguage.ts)、AIConfigPanel：目标语言、自定义/内置/恢复提示词。 | 现有 AI 标题、摘要、要点同语言生成，提示词独立保存/恢复；固定 JSON 结构单独维护。显式语言目前仍是中文/英文。 |
| AI 队列 | [useRepositoryAnalysisJob](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/features/repositories/hooks/useRepositoryAnalysisJob.ts)、aiAnalysisOptimizer：并发、暂停、重试、逐项结果。 | 已有持久任务快照、语言/提示词快照、并发/频率约束、暂停恢复、精确失败重试。保留跨重启恢复；参考的内存队列不是替换依据。 |
| 阅读 | [ReadmeModal](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/components/ReadmeModal.tsx) 阅读目录、进度、字号、来源、缓存。 | 已有统一摘要+要点+正文、来源、章节、进度、上/下篇。本轮增加局部阅读字号、重置和保存偏好；相关收藏改为普通列表按钮，避免大胶囊包住内容。 |
| 正文翻译 | [translateService](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/services/translateService.ts) Microsoft/Google/AI，原文/译文/双语、取消和重试。 | **仍缺正文翻译和双语阅读。** 摘要目标语言不等于正文翻译；原文仍保留采集时语言。 |
| 单条/多条聊天 | [repositoryChatRunner](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/services/repositoryChatRunner.ts)、RepositoryChatSheet：单仓库问答、有限工具轮次、停止/重试/重生成。 | 已有整库、单收藏、最多 12 条所选收藏聊天、引用和停止/重生成。聊天使用当前连接；仍缺聊天独立选择另一套连接的入口。 |
| 聊天历史与引用 | [repositoryChatStorage](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/services/repositoryChatStorage.ts)、GlobalChatHistorySheet：消息/证据存储与历史。 | 已有数据库持久历史、受范围限制的来源引用、完整 JSON 恢复。本轮验证记录修复也接入聊天，避免设置页和聊天可用状态不一致。 |
| MCP | [server MCP](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/server/src/mcp/http.ts)、electron/mcpLocalServer.js：HTTP/SSE、独立 Token、检索/证据/分类工具。 | 已有 stdio 和桌面 HTTP、独立 Token、真实协议自检与客户端配置。不同入口的权限和工具范围按本项目合约保留，不扩成任意桌面控制。 |
| 收藏时间线 | 参考的主要时间线面向 Release 与 Fork，普通收藏活动并非完全对等功能。 | 本轮重做日期区和批次列表：可点左右按钮、普通鼠标滚轮、键盘；保留触控板。独立整理只使用收藏元数据，不再要求先运行 AI 索引。 |
| 列表密度和字段 | [RepositoryList](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/components/RepositoryList.tsx)、ThemeSettingsCard：网格/列表、渐进渲染、字段和快捷动作。 | 有网格/列表、内容显示偏好、分页和稳定选择。没有完整卡片字段/动作拖动编排；本轮修复长文本、全选辨识和批次翻页闪空。 |
| 外观与快捷键 | [ThemeSettingsCard](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/components/settings/ThemeSettingsCard.tsx)、useSearchShortcuts：主题、缩放、减少动效、搜索快捷键。 | 有明暗、中英、减少动效、原生键盘行为；本轮增加阅读字号。整体视觉仍待用户评价，未把技术通过写成审美认可。 |
| JSON/HTML 备份 | [DataManagementPanel](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/components/settings/DataManagementPanel.tsx) 选择数据类型，merge/replace，敏感值选项。 | 已有 JSON/HTML、正文/摘要/范围内聊天恢复，排除密钥及向量。本轮删除“只能恢复书签元数据”的过期说明。 |
| WebDAV / 后端同步 | [webdavService](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/services/webdavService.ts)、autoSync：WebDAV 备份、多设备后端交换和竞争处理。 | 有共享目录同步、冲突预览/选择、备份与周期检查；**没有原生 WebDAV 连接配置**。两者不能宣称完全等价。 |
| 桌面与网络 | [electron/main.js](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/electron/main.js)、useNetworkActions：单实例、托盘、自启动、代理/路由测试。 | 有 Tauri 启动/恢复/托盘/快捷键/自启动；没有同等完整的独立代理管理页面。本轮未改托盘几何，安装效果仍需同版本 Windows 检查。 |
| 更新 | [updateService](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/services/updateService.ts) 检查版本、通知、打开下载地址。 | 有检查与发布页入口，双方都不应据此称“自动下载安装”。本轮不发布新正式版本。 |
| Release 订阅 / 下载 | [useReleaseTimelineActions](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/features/releases/hooks/useReleaseTimelineActions.ts)、useReleaseArtifactActions：订阅、已读、平台资产过滤、aria2。 | 未实现 GitHub 专属 Release 订阅/下载器；可选软件收藏扩展，属于新增产品功能，不伪装成已经存在。 |
| Discover / 代码搜索 | [useDiscoveryActions](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/features/discovery/hooks/useDiscoveryActions.ts)、CodeSearchView：Trending、热门发布、Topics、grep.app。 | 未实现 GitHub 榜单和公共代码搜索。普通个人收藏检索保留自身语义，不能用外部热门结果冒充已保存收藏。 |
| 外部发现来源 | [externalDiscoveryFeed](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/services/externalDiscoveryFeed.ts)、telegramService、xTweetService、weeklyIssuesService：JSON/RSS/Atom、公开 Telegram、X、周刊抽取。 | 有有界网站导入；没有这些专属订阅连接器，也没有通用 RSS 阅读器。不会借参考研究去访问真实浏览器 Cookie。 |
| Fork / Gist | [useForkTimelineActions](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/src/features/forks/hooks/useForkTimelineActions.ts)、useGistActions：上游合并、Actions、片段读写与 Star。 | 未实现 GitHub 代码托管写操作；与“保存并找回个人收藏”不同。未用本轮修复指令执行任何远程合并或仓库操作。 |
| 插件市场 | [pluginManager](https://github.com/AmintaCCCP/GithubStarsManager/blob/aa1e3c7473511132758c94a0b2365db6288c1eba/electron/plugins/pluginManager.js) 本地目录、固定来源安装、权限、页面/导出/动作扩展。 | 未实现第三方运行时代码市场。参考的 Node worker 也不是系统沙箱；本轮不为补功能数量引入这套执行面。 |

## 本轮修复的具体原因

### 连接保存与思考模式

原来 `model-probes.json` 每个通道只记最后一次测试。测试另一个未保存模型，无论成功还是失败，
都会覆盖或清除原来保存连接的证明。现在证明按完整连接指纹匹配，保存有限历史并保留当前连接；
失败只影响所测连接。最多保留最新记录和 8 条历史，不保存 API Key 明文。

指纹只覆盖实际使用的后端。端点连接不受未启用的 Agent 草稿影响；JSON 空白/键顺序不影响结果。
显式 Codex 模型和 effort 不再被日常客户端默认模型/effort 的变化作废；真正继承默认值时仍会失效。
旧版本证明通过原指纹比对兼容，不在升级时无条件要求重测。聊天、摘要、向量应用和设置共用判断。

设置页会说明“已保存，可以直接使用”。选择相同值不创建修改草稿，改回已保存值会清掉脏状态。
密钥输入保持遮蔽；“清除已保存的密钥”仍算一次明确修改，不被空值去重逻辑吞掉。
模型目录自动读取不再因测试按钮禁用/恢复而再次执行。`high / xhigh / max` 有直接入口；
开发模式重建组件副作用时会重新读取被取消的目录，不会被“已读取”标记阻止。
不把缓存目录当作用户不能尝试其他档位的硬限制，也不把显式选择等同于服务实际支持。
开关式思考参数只展示开启/关闭，不混入目录中的 effort 档位，避免把 high/max 悄悄转换成布尔值。
Codex 使用 managed 默认模型时，单独选择 effort 会保留目录里显示的默认模型，
避免因忽略客户端配置而退回另一个内置模型。

### 批次、日期与阅读

旧批次内容行直接使用胶囊控件，缺少内容布局归属。现在 `SavingSessions` 独立拥有列表、
数据读取、刷新/分页和样式；内容行使用原生 button 的点击、Enter/Space、焦点语义。
长标题可以换行，数量单独排列；下一页读取期间已有行不消失，旧响应不能覆盖新页面。
进入某批次时清除遗留摘要状态和语义查询，避免看见空结果后误以为批次坏了。

日期条保留横向浏览，并增加可见左右按钮及局部滚轮处理。到达边缘时交还纵向滚动；
Ctrl+滚轮缩放不拦截，触控板横向输入仍按浏览器原生处理。周期格用内容卡片尺寸，不使用大胶囊。

`POST /admin/sessions/rebuild` 使用固定 20 分钟间隔和既有批量导入规则，只处理本地收藏元数据。
单独连接和线程完成事务，同时更新批次关系边；失败回滚，任务/模型使用期间不能抢写。
忽略无效的零时间戳，不运行模型、不抓取网页、不需要先建立向量索引。

阅读正文、摘要与章节提供 5 档字号和一键恢复，偏好保存在当前应用浏览器存储中。
它不改变收藏列表字体；受限或清空的浏览器存储会恢复默认。相关收藏使用普通列表行，
长文本不被强制套入胶囊。导出提示与现有 JSON v2 恢复能力保持一致。

## 当前验证和下一步

最终应用源码 `dad2966` 的 CI、收藏专项、完整体验和 Windows 安装四条 Actions 全部通过。
CI 和完整体验浏览器矩阵均为 159 项通过、2 项按场景跳过；收藏专项 93 项通过，另有
1 项 20 万条收藏浏览器回归通过。完整 TypeScript/Vite 构建、Windows/Linux Python、
实际 OpenCode CLI、冻结服务、离线安装、原生托盘和启动恢复也已通过。

本地只使用已有隔离环境做小型测试和静态检查：24 项不同的连接、effort、JSON 解析与
批次流程检查通过；其中批次覆盖无 AI 整理、收藏保留、关系更新、失败回滚和并发写入保护。
Ruff、73 份 TS/TSX 和 27 份 CSS 语法检查通过。曾因本地缺少 HeroUI 依赖而不能完成
完整类型检查；没有为此安装依赖，完整类型结论来自上述 Actions。

已增加浏览器回归覆盖保存后重开、目录外 max、重复选值、鼠标滚轮/箭头、长批次标题、
密钥清除、开关/effort 格式区分、带旧筛选进入批次、分页保持、全选混合状态与键盘、
强制颜色，以及阅读字号保存。收藏 Actions 已纳入新 suite。
首轮 `7098cc2` 及中间版本有过浏览器失败、超时和转场采样不足；这些历史结果不能被
写成通过。后续补齐批次路由、阅读位置、聊天编号及 fixture 验证状态；动画保留原实现
和严格断言，最终同版本矩阵通过。详细运行与失败处置见
[交接文档](handoff-usability-2026-10-26.md)。

本次收藏证据共 121 张截图，163 份源码指纹与 `dad2966` 吻合，已下载并核对 8 张代表性
截图的哈希及画面。320px 月份的日期和数量完整显示，长批次标题占满可用行宽。另核对
安装后的收藏、阅读和托盘画面。以上是当前功能与排版证据，不是用户对整体视觉的认可；
真实模型对 effort 的支持及生成质量仍不能从合成服务验证推断。

后续产品差距最值得优先处理的是：多套命名模型连接和聊天独立选择、原生 API 协议覆盖、
批量 URL 导入、正文翻译/双语阅读，以及可选 WebDAV。它们仍是明确缺口，未写成已完成。
GitHub 专属 Fork/Gist/Actions/Release 和插件市场另属扩展方向；本轮交付优先修复基本可用性。

用户随后明确取消逐次提交确认限制：检查无误后直接提交、推送、创建或更新 PR，
并运行必要的 GitHub Actions。本轮按此最新约定继续云端验证；自动合并和正式发布
仍依用户明确指令执行。本轮已推送至 PR #54，没有自动合并或发布正式版本。
