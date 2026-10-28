# 可用性修复交接 · 2026-10-28

## 当前状态与授权

用户要求接着上轮，对照 GithubStarsManager 全面查漏，修复思考档位、连接重复配置、
全选、浏览批次和鼠标横向操作。用户已经授权必要检查后直接提交、推送、创建或更新 PR
以及运行 Actions；无需逐次确认。合并 PR、正式发行仍需明确指令。

- 分支：`fix/usability-connections-sessions-2026-10-26`；[PR #54](https://github.com/88lin/facetmark/pull/54) 仍开放。
- 当前已验证的应用源码：`dad2966b32f680073380d254d24ebf5a629565c9`，版本仍为 2.1.0。
- 本文后的收尾提交只更新记录，不改变已验证的应用、测试和工作流。
- 本地仅源码编辑、静态检查和隔离小型证据检查；没有安装依赖、运行浏览器或操作真实浏览器资料。
- 完整源码对照与参考项目最新差异见 [功能审计](githubstarsmanager-gap-audit-2026-10-26.md)。

## 本次接续完成

| 内容 | 代码与回归入口 |
| --- | --- |
| 测试成功后直接保存，保存失败只重试保存，已保存状态可见 | `frontend/src/Settings.tsx`、`frontend/tests/usability-repair.spec.ts` |
| 保存模型与验证记录一致；重开、试用其他草稿不破坏当前连接 | `src/facetmark/admin.py`、`local_agents.py`、`chat.py`、`tests/test_connection_reuse.py` |
| high/xhigh/max 和自定义档位，保持测试/保存/实际请求一致 | `ReasoningSettings.tsx`、`reasoning.ts`、`tests/test_model_connection.py`、`frontend/tests/reasoning.spec.ts` |
| 思考块中的示例 JSON 不会被当作最终摘要；不完整思考输出报错 | `src/facetmark/providers.py`、`tests/test_enrich.py::TestJsonRecovery` |
| 聊天临时消息编号不再与时钟碰撞，避免问题重复显示 | `frontend/src/ChatWorkspace.tsx`、`frontend/tests/chat.spec.ts` |
| 窄屏批次标题占满下一行；分页失败重试原页，整理失败重试原动作 | `SavingSessions.tsx`、`saving-sessions.css`、`usability-repair.spec.ts` |
| 月份卡片显示简洁月日范围，320px 下自动收窄以保留完整日期和数量；鼠标滚轮、箭头和键盘 | `ActivityTimeline.tsx`、`activity-timeline.spec.ts` |
| 全选的可见边界、勾选/半选、数量与键盘，保留现有工具栏 | `LibraryTools.tsx`、`library-tools.css`、`usability-repair.spec.ts` |
| 元数据整理批次、事务回滚，无需配置 AI | `POST /admin/sessions/rebuild`、`sessions.py`、`tests/test_sessions_workflow.py` |
| 阅读字号保存、专注模式保持位置、批次直达/刷新/返回 | `Reader.tsx`、`reader-shell.css`、`App.tsx`、`redesign.spec.ts` |

接续提交为 `a536660`、`bf44001`、`f35b950`、`c285d31`、`dad2966`。最初工作区已有未提交修正，
本次核查后保留并补齐测试；没有覆盖或删除已有取证资料。`artifacts/` 未加入版本库。
Git HTTPS 连接失败后，通过 Git Data API 传输同一批 Git 对象；逐个核对 blob、tree 和
commit SHA，以非强制更新分支完成推送，未改动 Git 代理或全局配置。

## 验证结果

以下四条运行均核对到应用源码 `dad2966`：

| 工作流 | 运行 | 结果 |
| --- | --- | --- |
| CI | [40664895634](https://github.com/88lin/facetmark/actions/runs/40664895634) | 通过 |
| 收藏界面取证 | [40665508196](https://github.com/88lin/facetmark/actions/runs/40665508196) | 通过 |
| 完整体验与 20 万收藏 | [40665514020](https://github.com/88lin/facetmark/actions/runs/40665514020) | 通过 |
| Windows 打包与安装 | [40665519203](https://github.com/88lin/facetmark/actions/runs/40665519203) | 通过 |

CI 浏览器与完整体验矩阵均为 159 项通过、2 项按场景跳过；收藏专项 93 项通过，
另有 1 项 20 万条收藏浏览器回归通过。
CI 包含四组 Windows/Linux Python 回归、完整 TypeScript/Vite 构建、扩展、镜像、wheel、
插件契约和浏览器回归。收藏专项覆盖设置、摘要、聊天、导入、全选、批次、阅读、窄屏、
中英、明暗、键盘及减少动效，并生成同提交截图。完整体验另验证实际 OpenCode CLI、
20 万条合成收藏 API、目标快照、浏览器分页/选择及分发包。Windows 流程包含冻结服务、
原生几何/启动回归、离线安装、实际启动和托盘取证。

本地用已有 `.venv`：连接复用与批次事务 8 项通过；新增 JSON 合成场景先复现 6 项失败，
修正后 JSON、请求档位和连接复用 22 项通过，两组去重共 24 项。Ruff、73 份 TS/TSX、
27 份 CSS 语法解析、UI 静态检测和 diff 检查通过。语法解析不代替完整类型检查。

收藏取证共 121 张截图，163 份源码指纹与 `dad2966` 完全一致；本次下载复核的 8 张截图
哈希全部吻合，包含 320/390px 时间线、320/1280px 长标题批次、全选、保存 max、中英明暗
收藏页。320px 月份卡片的日期和数量均可见。体验动画证据另核对 69 份前端源码，
18 组交互无页面错误、无非预期写入；首个转场为 12 组 opacity/blur 中间值，最大采样
间隔 83ms，结束时 transform/opacity/filter/willChange 已清除。
Windows 小型证据已下载，核对安装后的收藏、阅读空态和托盘画面；托盘外框及客户区均为
312×374，明暗内部无溢出。启动失败后的真实 Enter 重试等待旧服务退出，再恢复新服务，
后续 12 次健康检查通过。这里只核对云端安装，未替换用户本机现有安装。

取证只使用隔离合成数据。已检查代表性收藏、全选、批次长标题、模型状态/菜单和聊天画面；
当前功能与排版问题的检查不等于用户已认可整体视觉。真实模型接受的 effort、实际服务
质量和总结效果不能从合成测试推断；Hosted Windows Server 也不是所有 Windows 10/11
环境的认证。

## 仍存在的功能差距

| 优先级 | 缺口 | 接续要求 |
| --- | --- | --- |
| P1 | 多套命名模型配置及聊天独立选择 | 持久保存档案与当前选择；迁移现有单套设置，保留密钥和验证记录语义 |
| P1 | 原生 Responses/Anthropic/Gemini 端点协议 | 当前直接端点为 Chat Completions 兼容协议；CLI 连接不等于原生端点适配 |
| P1 | 批量粘贴 URL 导入与统一导入历史 | 复用去重和 URL 校验，增加候选预览、逐项结果与重试 |
| P2 | 实时相似内容召回、独立远程 BGE 重排 | 当前 Related 是已存关系图；不等于参考项目新加的资料画像与多路实时召回 |
| P2 | 正文翻译和双语阅读 | 摘要语言不等于正文翻译，需原文/译文缓存及取消重试 |
| P2 | 原生 WebDAV | 共享目录同步不等价于 WebDAV，需独立连接、冲突和失败处理 |
| P2 | 文件夹颜色/图标/排序、独立笔记与部分显示定制 | 仍未实现，不应对外称完整对齐参考应用 |
| 待用户评价 | 整体视觉 | 已修排版并核对代表画面，仍不能将测试通过写成用户审美认可 |

GitHub 专属 Stars/Lists 双向连接、Release/Fork/Gist/Discover 和插件市场属于产品扩展；
不要把它们变成普通收藏的前置条件。站点分类继续遵从用户要求保持移除。

## 历史失败与接续方式

`7098cc2` 的失败已由 `cb062b3` 修正批次 hash、专注阅读位置和测试清理竞态。
`cb062b3` 的 CI/安装通过，收藏专项暴露聊天重复问题，完整体验超时；本次已分别修复
唯一临时编号和工作流时限。`a536660` 的唯一浏览器失败是测试模拟模型设置却未同步
验证状态，由 `f35b950` 修正；`f35b950` 四条运行全部通过后，截图复查发现月份日期
断行，由 `c285d31` 修正；随后 `dad2966` 修正 320px 月份卡片固定宽度导致的数量裁切。
`c285d31` 的 CI、收藏和安装通过，完整体验为 158 通过、2 跳过、1 失败：
首个页面转场记录了两帧 opacity/blur 中间值，随后出现 275ms rAF 采样间隔，再到达终态，
未达到同节点至少三帧中间值的断言。没有页面错误，动画最终清除了全部自有 inline 样式；
该记录不能进一步区分浏览器渲染停顿与运行器调度来源。`f35b950` 同一转场有 11 组中间值。
保留动画实现及原有严格断言，`dad2966` 完整体验再次通过，实际帧记录也满足原要求。
这证明当前运行的交互正常，不能据此宣称所有设备都不存在掉帧。
被新提交取代而取消的运行不是通过结果。

继续时先检查 `git status`、PR 和运行 `headSha`。CI 随 PR 更新触发，另外三条在该
分支须手动 dispatch：`collection-review.yml`、`experience.yml`、`desktop.yml`。
新问题先看实际日志和失败截图；下载证据先核对 `provenance.json` 的提交和源文件。
项目记录只写本仓库，不更新通用设计手册或长期记忆。
