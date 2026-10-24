# Facetmark 桌面化与体验升级交接

## 当前状态：2026-10-19，视觉方向已拒绝，重设计继续

**2026-10-19，用户看截图后再次拒绝 `bed41ee` 的整个视觉方向：纯色处理、配色、
构图和视觉元素仍显古板。重设计继续，运行结果仅作为技术证据，不能记录完成交付、
视觉 `ship` 或用户认可。** 随后三张样机整体也全部被拒绝。用户最新明确要求：
**“现在这种图标布局样式颜色等都不要。”** 此要求覆盖此前文件夹图标的局部认可；
当前整套视觉均不作为新方案保留要求，整体新 UI 实施未完成。

当前通过验证的应用／测试源码为 `f1454704f15d89f9fd6aa74889e984280410e425`，工作分支为
`desktop/facetmark-experience`，对应 [PR #44](https://github.com/88lin/facetmark/pull/44)。
`2e56a7c9ee0b7aa09753f9afdaae9cc24aaa1198` 仅添加 A／B／C 视觉样机和云端渲染，
不是应用的新 UI。样机使用合成内容，三张的构图、配色和其余组件均已被用户拒绝。

当前只把立体文件夹接入真实目录和文件夹选择器：整行悬停／键盘焦点展开前盖、
抬起纸张，选择后有短促反馈，移开后回到选中／收起状态。文件夹路径决定稳定配色，
两处一致；减少动画偏好实时生效。实际 28px、深浅色与选择器截图已独立复核；
Web 快速打断／动画中途减少动态测试、安装版真实文件夹操作均通过。这是历史组件
技术证据；最新要求已取消其视觉保留地位。

[方向契约](../.impeccable/workbench-direction.md)与
[前端 surface brief](../.impeccable/surfaces/frontend.md)记录设计与验收上下文；
[DESIGN.md](../DESIGN.md)与[设计 sidecar](../.impeccable/design.json)标记替代设计待实现，
旧 token 与组件样例已移至[历史归档](../.impeccable/history/2026-10-19-rejected-ui/README.md)；
[UI motion tools](ui-motion-tools.md)记录动画责任。HeroUI、GithubStarsManager 与
FlClash 提供组件、组织和交互参考。以下实现细节只用于回归排查，不约束新方案的
图标、布局、字体、配色、材质或动效。规则修正并未修改应用外观。

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
| [Experience 39214088010](https://github.com/88lin/facetmark/actions/runs/39214088010) | 全部 5 作业成功；后端 2050 通过／1 跳过，浏览器 76 通过／1 跳过，独立 20 万条浏览器测试通过。 |
| [Windows 39214088011](https://github.com/88lin/facetmark/actions/runs/39214088011) | 成功；实际安装版记录 17 个动作，包括文件夹动效与选择，0 页面错误、0 非预期写入。 |
| [CI 39214092925](https://github.com/88lin/facetmark/actions/runs/39214092925) | 全部 10 作业成功。手机 390×844 完整显示 2 张卡；标题 18px、摘要 16px 与触达尺寸保留。 |
| Web 与安装证据 | 主线程核对 89 张 Web PNG、3 个 MP4 哈希；主交互 18 个动作，文件夹专项 9 个动作，包含快速打断和中途减少动态。安装证据源码一致。 |
| [样机渲染 39206868180](https://github.com/88lin/facetmark/actions/runs/39206868180) | 成功；6 张 PNG 哈希已核对。仅证明 A／B／C 合成样机被渲染，不证明应用新 UI 已实现或获得认可。 |

小型安装证据为 [12170105241](https://github.com/88lin/facetmark/actions/runs/39214088011/artifacts/12170105241)
（492,731 bytes）；[安装器 12169053783](https://github.com/88lin/facetmark/actions/runs/39214088011/artifacts/12169053783)
为 287,596,770 bytes，未下载，未替换用户本机安装。文件夹 GIF／MP4 来自
[组件预览 39212823994](https://github.com/88lin/facetmark/actions/runs/39212823994)，使用实际组件。
三张整体方向仍均被拒绝，不能沿用；当前通过不代表整体设计完成。

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
