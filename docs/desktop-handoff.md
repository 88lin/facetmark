# Facetmark 桌面化与体验升级交接

## 当前状态：2026-10-19，视觉方向已拒绝，重设计继续

**2026-10-19，用户看截图后再次拒绝 `bed41ee` 的整个视觉方向：纯色处理、配色、
构图和视觉元素仍显古板。重设计继续，运行结果仅作为技术证据，不能记录完成交付、
视觉 `ship` 或用户认可。** 随后三张样机整体也全部被拒绝，只保留 Orbit 的立体
文件夹图标，且以真实动画效果为条件；整体新 UI 实施未完成。

已构建应用／测试的技术基线为 `bed41ee497e52f5b70b6426683640e2532520995`，工作分支为
`desktop/facetmark-experience`，对应 [PR #44](https://github.com/88lin/facetmark/pull/44)。
`2e56a7c9ee0b7aa09753f9afdaae9cc24aaa1198` 仅添加 A／B／C 视觉样机和云端渲染，
不是应用的新 UI。样机使用合成内容，三张的构图、配色和其余组件均已被用户拒绝。

当前只把立体文件夹接入真实目录和文件夹选择器：整行悬停／键盘焦点展开前盖、
抬起纸张，选择后有短促反馈，移开后回到选中／收起状态。文件夹路径决定稳定配色，
两处一致；减少动画偏好实时生效。该组件的云端录像与交互结果待验证。

[方向契约](../.impeccable/workbench-direction.md)与
[前端 surface brief](../.impeccable/surfaces/frontend.md)记录设计与验收上下文；
[DESIGN.md](../DESIGN.md)与[设计 sidecar](../.impeccable/design.json)记录实现规范；
[UI motion tools](ui-motion-tools.md)记录动画责任。HeroUI、GithubStarsManager 与
FlClash 提供组件、组织和交互参考。这些记录及既有截图均不构成用户批准的视觉方向。

## 已构建应用的技术基线（视觉已拒绝）

以下描述 `bed41ee` 中已有的 HeroUI 3.2.6、GSAP 与胶囊工作区实现，供继续重设计时
核对功能和回归范围，不是新视觉方向或验收结论。

- **统一侧栏**：244px 侧栏同时容纳应用入口、分类模式、目录搜索和目录列表；
  紧凑／宽桌面为 224／260px，外层间距为 12px。应用入口使用整行胶囊，工具使用
  40px 圆形按钮并保留可访问名称；分类模式保留文字。960px 以下改为 56px 顶栏和
  管理焦点的目录抽屉，手机标题与搜索分行。短窗口的分类间距、导航宽度和图标
  边距已统一修正；后续布局仍需按新设计验证。
- **字体与形状**：Inter／Noto Sans SC 随应用提供，系统字体兜底。收藏标题 18px、
  摘要 16px、主要控件 15px、元信息 13px；页面标题 28px，并有响应式例外。
  控件为完整胶囊，卡片 22px、侧栏和支持面板 28px、菜单／对话框 24px。
  手机主要动作保持 44px 目标；卡片与列表共享内容层级，展开以实际裁切测量为准。
- **实际 HeroUI 控件**：共享 `CapsuleButton` 包装 HeroUI Button，文件夹／模型搜索
  使用 HeroUI Input。HeroUI 负责按压和焦点；包装层保留原生按钮、真实点击目标、
  表单提交与 Enter／Space 行为。调用方键盘处理先执行，阻止默认行为后不再交给
  HeroUI 重复处理。HeroUI 阻止 Enter／Space 默认点击时，普通按钮才补一次真实
  DOM 点击；原生提交按钮保留表单语义。禁用／等待状态禁止激活。Agent 模型选择
  不再套方形外框。
- **完整动效分工**：GSAP 在现有容器中分别编排页面、设置章节、分类、分页和筛选，
  标题与正文分层进入，快速反向从当前画面继续。Motion 负责选中胶囊、卡片重排和
  浮层进出；HeroUI 负责控件状态；有界墨迹与主题圆形切换提供点击反馈。状态和
  焦点立即更新，关闭浮层立即 inert。动态减少动画偏好取消空间反馈，包括 portal
  中的按压效果。墨迹在原控件隐藏、inert、移除或移位后清除，并有 600ms 上限；
  导航遮罩不套胶囊、缩放或墨迹。靛蓝 `#5c4ddb` 与选中背景的定义色值对比度约
  4.84:1。当前技术证据确认先前墨迹残留已修复，不代表整体视觉方向获认可。
- **阅读与工作流保留**：阅读区的真实标题导航、正文进度、玻璃位置胶囊和纸飞机
  大纲继续存在。原网页、勾选、编辑和预览相互独立。Agent 发现、模型选择、测试、
  保存和摘要使用保持分离；恢复任务复用原目标快照，保留完成项。HTML／JSON 导入、
  只读来源发现、共享文件夹同步、冻结后端及离线 WebView2 安装流程继续保留。

## 技术证据与样机状态

完整记录见[当前验证条目](desktop-validation.md#2026-10-19-visual-direction-rejected-redesign-continues)。

| 证据 | 当前结论 |
| --- | --- |
| [Experience 39204645206](https://github.com/88lin/facetmark/actions/runs/39204645206) | web 作业失败，其余 4 个作业成功；准确测试计数尚未提取。 |
| [Windows 39204645205](https://github.com/88lin/facetmark/actions/runs/39204645205) | 成功；安装版记录 13 个动作、0 页面错误、0 非预期写入。 |
| [CI 39204650822](https://github.com/88lin/facetmark/actions/runs/39204650822) | 浏览器 74 通过／1 跳过／1 失败：手机收藏期望完整显示 2 张卡，实际 1 张；其余 CI 作业通过。 |
| Web 与安装证据 | 主线程核对 82 张 Web PNG、2 个 MP4 的哈希；Web 录制含 18 个动作。小型安装证据已下载并核对源码，墨迹残留已修复。 |
| [样机渲染 39206868180](https://github.com/88lin/facetmark/actions/runs/39206868180) | 成功；6 张 PNG 哈希已核对。仅证明 A／B／C 合成样机被渲染，不证明应用新 UI 已实现或获得认可。 |

小型安装证据为 [12165886859](https://github.com/88lin/facetmark/actions/runs/39204645205/artifacts/12165886859)
（362,483 bytes）；[安装器 12165414259](https://github.com/88lin/facetmark/actions/runs/39204645205/artifacts/12165414259)
为 287,498,248 bytes，未下载。样机[产物 12166290878](https://github.com/88lin/facetmark/actions/runs/39206868180/artifacts/12166290878)
为 2,888,243 bytes。手机密度失败仍是未通过项；三张整体方向均被拒绝，不能沿用。

## 使用与工程边界

用户使用步骤见[桌面预览](desktop-preview.md)、[本机 Agent](local-agents.md)和
[收藏管理](library-management.md)。端用户无需安装 Node、Python 或 Rust。

本次任务本地仅允许源码编辑、轻量静态检查及小型证据检查；**不在本机运行构建、
浏览器、包安装、桌面打包或安装，也不下载大型产物**。运行验证放在 GitHub Actions。
只使用合成书签和隔离 fixture，不修改或自动操作真实浏览器资料，不使用个人收藏。
模型 fixture 不证明个人账号权限、额度或真实摘要质量。

Windows 是用户的主要环境。托管 Windows Server 的通过结果不等于覆盖所有
Windows 10/11 机器、跨版本升级或普通非管理员使用；预览安装器仍未签名。
变更交付到既有 PR；不自动合并 main、正式发布或部署 Pages。

工程入口为 `.github/workflows/experience.yml` 与 `desktop.yml`。优先取回
`facetmark-visual-evidence` 和 `desktop-install-evidence` 小型证据；
`facetmark-experience-review` 与 `facetmark-windows-x64-preview` 含大型构建产物，
不要为取截图下载整包。保留 `.desktop-build/preserved-inputs` 中的初始素材备份。
