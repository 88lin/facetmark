# Facetmark 桌面化与体验升级交接

## 当前交接：2026-10-17，完整模型与摘要流程

已验证应用／测试源码为 `4c6383ad0537bccb85ce32f76fc11fe3f9e139e8`。
Experience `39002142092`、CI `39002144664`、Windows `39002142193` 均通过；
独立视觉复核为 **ship**，原八项发现全部解决。

工作分支为 `desktop/facetmark-experience`，对应 PR #44。用户要求完整改进
Agent 发现、模型选择、测试保存、摘要使用与失败恢复，并拒绝继续堆叠孤立补丁。
保留纯白／湖蓝、18px/700 收藏标题与 15px 描述；共享控件圆角改为 7px，
导航与支持页采用无外框的紧凑结构。用户尚未确认当前审美效果。

当前交互契约集中在[方向说明](../.impeccable/workbench-direction.md)和
[前端 surface brief](../.impeccable/surfaces/frontend.md)；[DESIGN.md](../DESIGN.md)
与[设计 sidecar](../.impeccable/design.json)记录相同系统的 token 和组件示例。
历史验证保留在[桌面验证记录](desktop-validation.md)，不再作为当前完成依据。

## 当前实现

- **模型选择到使用**：支持 Codex、Claude Code、OpenCode 与 API 服务。显示实际
  Agent，模型选择器提供搜索、沿用默认、手动输入、刷新以及目录来源提示。发现目录
  不代表权限或登录成功；选择后测试，成功保存后再进入摘要。修改模型或连接身份会
  使旧测试失效；Agent 草稿与摘要／向量通道状态分别保留。
- **设置布局**：摘要和可选向量采用全宽独立章节；桌面字段两列，手机一列。
  模型选择、测试／保存及反馈靠近；超时和安装路径放在后续展开项。四个设置分类
  使用下划线标签，切换时保留草稿。模型样式集中在 `frontend/src/support.css`。
- **收藏工作台**：新增／管理／生成摘要为一组；状态／排序／显示为一组。
  “显示”仅切换摘要与原文摘录，处理范围、重处理数量与发送确认在处理对话框。
  原网页、勾选、编辑和预览保持独立；预览仍是辅助入口。
- **精确恢复**：部分完成、失败或中断任务以原任务 ID 恢复其持久化目标快照，
  保留完成项，仅重试该快照中的失败／未完成项。不会把局部重试扩大为全库失败项。
  当前范围、状态、进度和恢复动作排在新任务入口之前。
- **保留的桌面能力**：HTML／JSON 导入、同文件重试、原网页系统浏览器打开、
  只读来源发现、共享文件夹元数据同步、冻结后端及离线 WebView2 安装流程。

## 验证状态：云端、安装与独立视觉复核通过

完整证据以[当前验证条目](desktop-validation.md#2026-10-17-complete-model-choice-summary-use-and-exact-recovery)为准：

- Experience **2049 项 Python 通过／1 项跳过**；普通 Playwright **63 项通过／
  1 项大矩阵场景跳过**，独立 **20 万条浏览器检查通过**。构建、wheel/sdist、
  Docker、扩展及 Linux／Windows 真实 OpenCode 隔离 HTTP 模型流程均通过。
- CI **10 个作业全部通过**。Windows 离线安装、后端隔离、实际安装版的合成导入／
  搜索／Edge 原网页打开／预览返回、重装、卸载保留数据及父进程清理通过。
- 最终源码的 **80 张 Web PNG 哈希全部匹配**。桌面／390px 手机列表顶部为
  **208.39／256.08px**，与首卡 **211.39／259.08px**分别记录；五种宽度均无横向溢出，
  手机完整显示两张卡。安装版查询保留且没有页面错误。
- 独立视觉复核为 **ship**，原 **8 项发现全部 resolved**，复核范围内无剩余实质问题。
  实际检查 **17 张指定画面**：五种收藏尺寸、六种模型／连接状态、英文深色设置、
  暂停／部分完成任务、导入，以及安装版收藏／预览。
- 通用 reviewer 代替不可用的专门角色。它核对最终源码／manifest，但没有逐张查看
  全部 80 张 Web 截图，也没有运行浏览器；运行结果来自云端。源码复核五项 resolved
  与单次机械扫描 `[]` 保留为独立证据。当前没有待补验收字段。

中间失败运行与修复保留在验证文档的历史段；不再作为当前状态。视觉 verdict 支持本次
完整复核范围，不等于用户审美认可。部分任务画面的通用阶段列表是 fixture 内容，
精确恢复由真实后端的范围恢复测试支持。未使用个人模型账号，不证明额度或真实摘要质量。
安装器仍未签名，大安装包未下载到本机，托管 Windows Server 不等于所有 Windows 环境认证。

## 使用与工程边界

用户使用步骤见[桌面预览](desktop-preview.md)、[本机 Agent](local-agents.md)和
[收藏管理](library-management.md)。端用户无需安装 Node、Python 或 Rust。

大型下载、构建、浏览器、打包及安装检查在 GitHub Actions 运行。本地只做轻量检查
和小型产物检查；不得使用真实浏览器资料或个人收藏作为测试数据。预览安装器未签名，
托管 Windows Server 测试不等同于覆盖所有 Windows 10/11 环境。模型 fixture 证明
集成协议和指定模型传递，不证明个人账号、额度或模型内容质量。

保留既有授权边界：不自动合并 main，不自动发布正式版本，不替换原始浏览器资料。
过去的布局、run ID 和安装验收以验证文档中的历史章节为准。

工程入口为 `.github/workflows/experience.yml` 与 `desktop.yml`。优先取回
`facetmark-visual-evidence` 和 `desktop-install-evidence` 小型证据；
`facetmark-experience-review` 与 `facetmark-windows-x64-preview` 含大型构建产物，
不要为取截图下载整包。保留 `.desktop-build/preserved-inputs` 中的初始素材备份。
