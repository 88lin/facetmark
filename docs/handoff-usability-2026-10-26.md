# 可用性修复交接 · 2026-10-26

## 当前任务与授权

用户要求对照 GithubStarsManager 全面排查，明确指出思考档位、已保存连接反复测试、
全选控件、浏览批次布局和鼠标横向操作不可用。用户随后明确：检查无误即可提交、
推送、创建或更新 PR，无需再询问；其他问题写入文档供下一位 AI 接续。

- 分支：`fix/usability-connections-sessions-2026-10-26`，基线 `9eeefd0`，版本仍为 2.1.0。
- 本地仅源码编辑、静态检查和小型隔离检查；构建、浏览器、安装依赖、打包与安装验证使用 Actions。
- 使用合成数据，不操作真实浏览器资料。PR 合并、正式发行仍依用户明确指令。
- 完整源码对照、根因和差距见 [功能审计](githubstarsmanager-gap-audit-2026-10-26.md)。
- 旧 `81f310a` 的通过结果只对应旧版本；不得当成本轮验证证据或用户视觉认可。

## 本轮实现入口

| 内容 | 代码与回归入口 |
| --- | --- |
| 保存连接的验证历史、有效配置指纹、重启复用 | `src/facetmark/admin.py`、`local_agents.py`、`chat.py`、`tests/test_connection_reuse.py` |
| high/xhigh/max 与自定义档位、模型目录、重复选值和密钥清除 | `frontend/src/ReasoningSettings.tsx`、`Settings.tsx`、`ModelPicker.tsx`；`frontend/tests/reasoning.spec.ts`、`usability-repair.spec.ts` |
| 全选胶囊、勾选/半选、键盘及强制颜色 | `frontend/src/LibraryTools.tsx`、`library-tools.css`；`usability-repair.spec.ts` |
| 批次长标题、分页、筛选重置、鼠标滚轮/箭头/键盘 | `frontend/src/SavingSessions.tsx`、`saving-sessions.css`、`ActivityTimeline.tsx`；`activity-timeline.spec.ts`、`usability-repair.spec.ts` |
| 无 AI 整理批次，事务更新分组及关系，失败回滚 | `POST /admin/sessions/rebuild`、`src/facetmark/workbench.py`、`sessions.py`；`tests/test_sessions_workflow.py` |
| 阅读字号保存、相关内容行、JSON 恢复说明 | `frontend/src/Reader.tsx`、`reader-shell.css`、`LibraryTools.tsx`；`usability-repair.spec.ts` |

## 验证状态

本地已通过：连接复用与档位传递 6 项、批次事务流程 2 项；Ruff；73 个 TS/TSX 文件和
27 个 CSS 文件的语法解析；`git diff --check`。

本地完整 TypeScript 检查因缺少 `@heroui/react` 和 `@react-aria/utils` 未通过，
没有为此本地安装依赖。旧 `artifacts/check-source-syntax.cjs` 的 transpile 步骤会异常，
本轮语法证据来自 TypeScript `createSourceFile` 和 PostCSS 解析，不能与完整类型检查混淆。

云端结果待补录，必须核对运行的 `headSha`。CI 覆盖类型、构建、Python、扩展与浏览器；
collection-review 产生本轮代表性截图；experience 包含真实 CLI 和 20 万收藏场景；
desktop 包含 Windows 打包、离线安装、启动和原生菜单取证。

## 尚未完成的事项

| 优先级 | 问题或功能差距 | 下一步 |
| --- | --- | --- |
| P0 | 本轮完整构建和运行验证未完成 | 跟进四条工作流；失败先读实际日志和失败截图，修复后验证新提交 |
| P0 | 新版界面尚未逐页视觉核对，用户未认可整体视觉 | 检查桌面/窄屏、长标题、全选、批次、模型面板与阅读截图；检查键盘、快速切换和减少动效 |
| P1 | 多套命名模型配置及聊天独立选择 | 先设计持久档案与当前选择，再迁移现有单套配置；保留连接验证及密钥语义 |
| P1 | 原生 Responses/Anthropic/Gemini API 协议 | 目前直接端点只有 Chat Completions 兼容协议；CLI 连接不等于端点协议支持 |
| P1 | 批量粘贴 URL 导入与统一导入历史 | 复用现有去重、导入报告和 URL 校验，增加候选预览及逐项结果 |
| P2 | 正文翻译和双语阅读 | 摘要目标语言不等于正文翻译；保存原文、译文缓存和取消/重试语义 |
| P2 | 原生 WebDAV | 共享目录同步不等价于 WebDAV，需要独立连接、冲突和失败处理 |
| P2 | 文件夹颜色/图标/排序、独立笔记与部分显示定制 | 属于已识别缺口，当前尚未实现 |

真实模型是否接受指定 effort 仍由连接测试决定；合成服务和 CLI 验证不代表真实摘要质量。
GitHub 专属 Release/Fork/Gist/Discover/插件市场属于产品扩展方向，不混入当前收藏基础修复。

## 接续方式

1. 先检查 `git status`、当前分支、PR 和最新 Actions，避免重复提交或使用旧运行结论。
2. 有关工作流：`ci.yml`、`collection-review.yml`、`experience.yml`、`desktop.yml`。
   后三条在本分支须手动 dispatch；普通 `fix/**` 推送不会自动触发它们。
3. `gh run list --branch fix/usability-connections-sessions-2026-10-26` 查看运行；
   `gh run view <id> --log-failed` 定位失败；下载截图后先核对 `provenance.json` 和源码版本。
4. 可提交的内容仅源码、测试、项目文档和工作流。`artifacts/` 是已有本地资料和证据，
   不要整体加入版本库。项目复盘只写本仓库，不更新通用设计手册或长期记忆。
5. 修复完成后更新本文与功能审计中的验证结果、剩余问题及 PR 入口，避免下一位 AI 重新调查。
