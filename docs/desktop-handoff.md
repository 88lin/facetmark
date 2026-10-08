# Facetmark 桌面化与体验升级交接

## 2026-10-08 收藏管理、独立阅读任务与共享文件夹同步（当前）

已完成用户“继续全部完善吧”及明确选择的共享文件夹同步方案。沿用纯白／湖蓝、
胶囊控件与收藏优先布局；本轮扩展功能，不替换已选定的视觉方向。

- 收藏页可新增、编辑、删除，批量移动或增删标签，按完整名称合并／移除分类，
  并按书库、分类、当前页或所选范围导出 JSON／HTML。
- 正文提取不要求模型；独立摘要只要求已测试的聊天模型和本次发送确认。
  支持任务进度、停止、重新处理，以及完成后列表和阅读缓存刷新。
- 共享文件夹同步提供变更预览、过期预览保护、多版本及重复网址冲突处理、
  首次人工确认、可选自动模式、接收变更前的本机 SQLite 备份。
- 新增／修改网址拒绝嵌入式凭据，正文请求使用受控抓取；Karakeep 关联记录保持受保护。

应用源码：`33ff0df5340b31061434deb7e341c612e22feae1`。
最终浏览器测试源码：`f757f33e00a0a3582e4b656865bddd51d3d4f445`，仅调整原生禁用选项的
测试断言。已确认两个提交的 `frontend/src`、`src`、`desktop` 和 `pyproject.toml` 一致；
后续文档及截图来源提交不改变应用代码。

- [Experience 37774845284](https://github.com/88lin/facetmark/actions/runs/37774845284)：
  全部通过，31 项浏览器测试、1996 Python / 1 skipped、Ruff、前端构建、
  wheel/sdist 资源、Docker 和扩展检查通过。
- [CI 37774856968](https://github.com/88lin/facetmark/actions/runs/37774856968)：
  十项任务全部通过，覆盖 Linux／Windows × Python 3.10／3.12、浏览器、扩展、
  Karakeep 契约、分发和 Docker；真实 MCP stdio 检查 22/22 通过。
- [视觉证据 11549727814](https://github.com/88lin/facetmark/actions/runs/37774845284/artifacts/11549727814)：
  42 张实际截图及 13.64 秒 MP4，另含 WEBM、字体／滚动诊断和来源记录。
  已核对全部截图哈希，本机位置 `.desktop-build/library-verified`。
- [Windows 37773749998](https://github.com/88lin/facetmark/actions/runs/37773749998)：
  全部通过。运行时初始缺失、安装器网络被阻断时完成离线安装；实际 WebView
  导入／检索／阅读返回、同版本重装、卸载保留数据、父进程清理和冻结服务检查通过。
  三张 1028×749 安装后截图已检查，诊断匹配 `33ff0df`。小型证据在
  `.desktop-build/library-windows`，artifact `11549224103`；未签名 x64 安装包
  artifact `11548884372`，安装器本体 276907454 字节，未下载到本机。
- 独立视觉审阅发现的标签提示对比度问题已修复，桌面／390px 截图测得 5.21:1；
  简短占位符和换行说明保持完整。确认轮给出 ship，仅覆盖这一修正，未发现新增回归。
  使用通用独立代理执行 Impeccable 契约；未提供外部 QUALITY BAR／comp，不代表用户审美认可。
- 保留 DESIGN.md 既有 token 和 sidecar，仅补充新弹窗、危险操作和阅读器上下文操作的规则。
  四张项目展示图来自最终成功运行，保持原始像素数据并嵌入来源元数据。

使用与恢复说明已写入 [收藏管理、阅读处理与设备同步](library-management.md)。重要边界：
同步只传网址、标题、文件夹、标签和收藏时间，依赖用户已有云盘工具；JSON 可导出正文与摘要，
但重新导入只恢复书签信息。摘要任务不自动抓取正文，独立阅读任务不等于完整语义索引。
首次确认后的自动模式会传播无冲突删除；没有回收站、一键数据库恢复或同步历史自动压缩。
管理接口要求已启用、配对认证及回环调用。实际外部模型、云盘传输和 Windows 10/11 真机
未覆盖；安装包仍为未签名、手动更新的预览版。

本机只做源码编辑、轻量检查与小型证据取回；构建、浏览器、打包和安装测试均在 Actions。
未下载或运行大安装包，未接触真实浏览器资料。继续使用原测试分支和 draft PR #44；
不合并 main、不发布正式版本、不部署 Pages。下面为历史记录。

## 2026-10-07 收藏与专注阅读重设计（历史）

用户再次要求更强的前端设计与组件完成度。当前产品及测试源码：
`0aa3e849ae06d6707fb1f52356eefe6bd774ff4a`。

- 纯白／湖蓝及胶囊控件保留。收藏页改为 38px 标题、独立搜索行、真实文件夹入口，
  1440px 下三列来源优先卡片；选中后变为 312px 辅助索引及主阅读面板。
- 自托管 Manrope；cmdk 查询建议支持键盘、错误重试和带空格条件；Rare UI 目录仅使用
  真实文章标题。36／38px 文章标题、17px 正文与 1.9 行高形成新的阅读层级。
  两条模型通道的测试按钮直接跟在各自字段后面。许可证随共享前端分发。
- [Experience 37618229826](https://github.com/88lin/facetmark/actions/runs/37618229826)：
  19 浏览器测试、1882 Python / 1 skipped、构建、分发、Docker 和扩展通过。
- [CI 37618237956](https://github.com/88lin/facetmark/actions/runs/37618237956)：十项检查通过。
- 37 张网页截图、14.08 秒录屏和诊断来自同一源码，artifact `11480239215`，
  本机小型证据位于 `.desktop-build/collection-elevated`，全部截图哈希已核对。
  四张项目展示图同步该源码，嵌入来源且保持像素数据不变。
- [Windows 37618229866](https://github.com/88lin/facetmark/actions/runs/37618229866)：
  离线安装、实际 WebView 导入／检索／阅读返回、同版本重装、卸载保留数据、
  父进程清理与冻结服务验证通过。安装包 artifact `11481542111`，
  小型证据 `11481562146`；三张安装后截图已检查。本机未下载／运行安装包。
- 新的独立完整视觉复审为 **ship**，没有实质修复项。因专用角色不可用，由通用独立
  审阅代理按 Impeccable 契约执行。未提供外部 QUALITY BAR／comp，相关上限未验证；
  评审与自动检查不代表用户的审美认可。DESIGN.md 与 sidecar 已按实际画面确认。

本机只做源码编辑、轻量检查与小型证据取回；构建、浏览器和安装验证均在 Actions。
继续复用测试分支及 draft PR #44，不合并 main、不发布、不部署 Pages。
以下记录均为历史，不代表当前界面已经获得用户审美认可。

## 2026-10-07 胶囊控件与整体精修（历史）

用户认为上一版仅略有改善，明确要求按钮使用圆角胶囊并继续美化。
当前产品源码：`1d006544740e2c2965530a503393ccf333674a05`。
导航、导入、筛选、阅读标签及表单动作改为真正的胶囊；图标动作改为圆形。
顶部工具分组，收藏卡取消强制 166px／118px 空白高度，阅读来源、标题、正文重新分组；
双模型的字段、选项和测试动作按真实内容分行对齐，主要移动操作目标至少 44px。

- [Experience 37466126567](https://github.com/88lin/facetmark/actions/runs/37466126567)：
  14/14 浏览器、1882 Python / 1 skipped、前端构建与分发、Docker、扩展通过。
- [CI 37466133676](https://github.com/88lin/facetmark/actions/runs/37466133676)：十项检查通过。
- 35 张截图、13.68 秒 MP4 及来源记录在 `.desktop-build/capsule-first`；
  visual artifact `11414603412`，全部截图哈希已核对。
- [Windows 37466126767](https://github.com/88lin/facetmark/actions/runs/37466126767)
  第二次尝试通过：同一源码完成离线安装、真实 WebView 导入／检索／阅读返回、
  同版本重装、卸载保留数据、进程清理及冻结服务隔离检查。三张安装后截图已检查，
  小型证据在 `.desktop-build/capsule-windows`，artifact `11478997809`；
  未签名 x64 安装包 artifact `11479497637`，安装器 276793305 字节，未下载到本机。
  首次尝试在下载微软 WebView2 组件时出现 `Peer disconnected`，重跑后已通过。
- 新的独立完整视觉复审给出 **ship**：已检查 12 项必需视觉证据及覆盖 35 张截图的联系表，
  未列出实质界面修复项。使用通用独立审阅代理执行 Impeccable 契约，未提供 QUALITY BAR 图，
  历史 seed 原始记录亦不可用，方向文件已注明限制。结论不代表用户认可审美。
- DESIGN.md、design.json 和四张项目展示图已同步；图片像素数据未改，嵌入了本次来源。

本机只做源码编辑、轻量检查和小型证据取回；不运行构建、浏览器或安装包。
继续复用测试分支及 draft PR #44，不合并 main、不发布、不部署 Pages。

## 2026-10-06 纯白＋湖蓝后续（历史）

用户再次否定灰紫、平直的实际画面，明确选择 **纯白＋湖蓝、圆角面板与精致控件**。
共享前端现为白色收藏卡、浅蓝灰工作区、湖蓝选中态、分段导航和阅读标签；
卡片 16px、阅读面板 20px、通用控件 10px。保留此前已完成的业务及桌面能力。
当前产品与验收源码：`7a20776e6fa49bb55cab4e35bf43753477c76fef`。

- [Experience 37459945939](https://github.com/88lin/facetmark/actions/runs/37459945939)：
  14/14 浏览器、1882 Python / 1 skipped、共享前端与分发、Docker、扩展通过。
- [CI 37459952441](https://github.com/88lin/facetmark/actions/runs/37459952441)：十项检查通过。
- [Windows 37459946022](https://github.com/88lin/facetmark/actions/runs/37459946022)：
  实际安装后的导入、搜索、阅读返回、同版本重装、卸载保留数据、进程清理通过。
  安装包 artifact `11412588346`；小型安装证据 `11413073197`。
- 34 张网页截图和 13.2 秒录屏在 `.desktop-build/lake-blue-final`，
  三张安装后截图和诊断在 `.desktop-build/lake-blue-windows`。数据均为项目合成数据。
- 独立复审在确认轮将“关闭导航残余阴影”“收藏卡元信息对齐”两项判为 resolved，
  disposition 为 ship；该结论仅覆盖所列修正，不等于用户审美认可。
- DESIGN.md、design.json、四张官网工作台图及来源记录已同步；本机未运行构建、浏览器或安装包。

首次云端失败来自历史帮助页 `&amp;` 与生成源 `&` 不一致，`85cc439` 同步生成源后
相关 137 项轻量检查及全量云端复测通过。截图同时等待阅读抽屉停稳。
后续文档提交不改变产品源码。下面各节为先前版本历史，不能作为当前视觉授权或验收。

## 2026-10-06 用户否定后的重建

用户明确否定上一版：**“整体太普通，像后台管理工具”**。下面 `d618c52` 的测试和
七项修正 ship 仅是历史记录，不是新视觉的验收。新的独立全量复审给出 rebuild。

`33bee64` 重建共享前端骨架：取消常驻分类侧栏，改为顶部导航和按需筛选；未选中时
双列收藏索引，选中后索引退为辅助、文章成为主要画面；合并阅读工具，收藏信息折叠；
窄窗口改为全宽阅读。新增布局源为 `frontend/src/workbench.css`。
首批 [37407299839](https://github.com/88lin/facetmark/actions/runs/37407299839)
生成了首批真实渲染：后端、构建与分发通过，浏览器 8/14；5 项因隐藏导航仍被
辅助技术识别为重复按钮而失败，另 1 项沿用了旧正文高度的固定滚动断言。
集中修正 `90f551b` 统一集合内容轴、修复行高、提供明确的窄窗返回入口、移除专注
阅读顶部空区并完善可访问性与滚动恢复。确认运行和最终结果见验证文档。

当前共享前端源码：`90f551b38bd1ee15833d40c97cf1e2cf93c082fd`。
测试修正 `d6597e9` 的 [Experience 37410551657](https://github.com/88lin/facetmark/actions/runs/37410551657)
已通过 14/14 浏览器测试、1882 Python / 1 skipped 及构建／分发检查；
[CI 37411031139](https://github.com/88lin/facetmark/actions/runs/37411031139) 十项均通过。
33 张截图与录屏在 `.desktop-build/collection-final`，均对应 `d6597e9`；
产品源码未变，四张官网工作台图也已更新。新的独立完整视觉复审为 **ship**，
覆盖提供的构图、状态和交互分镜，不代表用户认可审美或 Windows 安装通过。

Windows 首次确认已安装并完成导入／阅读，但测试沿用旧“关闭预览”标签失败；
测试修正 `429e6e0` 改为依据布局寻找可见“返回收藏”，
[37411693696](https://github.com/88lin/facetmark/actions/runs/37411693696) 已通过安装后
导入／检索／阅读返回、同版本重装、卸载保留数据、父进程清理与冻结服务隔离检查。
最终小型证据在 `.desktop-build/collection-windows-final`，三张实际安装界面已检查。
安装包 artifact ID `11390096074`；小型安装证据 ID `11390071119`。未下载大安装包。
后续文档和测试提交不改变共享前端。初始未提交内容备份仍在
`.desktop-build/preserved-inputs`。继续工作时以本节为当前状态，下面为历史记录。

更新于 2026-10-05。本文已经替换最初的草稿交接；旧文中“React 未开始”
“仅四个后端草稿”等状态不再适用。继续前核对 git status、diff、分支和 Actions，
以实际代码与对应提交的云端证据为准，不从规划重启。

## 用户目标与授权

- 工作区：`C:\Users\Computer\Desktop\web\facetmark`。
- 远端：`https://github.com/88lin/facetmark`；复用 `desktop/facetmark-experience`。
- 已授权测试分支提交、推送、Actions；不合并 main、不正式发布、不部署 Pages。
- 桌面打包、大文件下载、大型程序／浏览器运行、安装测试全部在 GitHub Actions。
  本机只编辑源码、轻量检查、取回小型截图证据；不安装打包工具、不下载或运行
  安装包、WebView2、大模型。
- 真实浏览器资料只读。来源发现必须由用户主动触发，再选择来源；演示只用合成数据。
- 保留既有修改，不回滚四个初始后端草稿；它们已完善、验证并提交。
- Tauri 2 + Python sidecar，React/TypeScript/Vite/Tailwind/Radix/Lucide，共享
  Windows／Python Web／Docker 界面。GithubStarsManager 仅工程经验参考。
- 历史文档的“设计方向已确认”不代表用户认可实际界面；本轮明确授权重设计共享前端。
- 用户否定深石墨导航与圆角外壳后，明确选定：**通透明亮：纯白、轻导航、精密排版，
  接近 Linear 的秩序感**。这取代了上一轮深色侧栏方向；不要恢复被否定的视觉。
- 持续推进、简短中文更新，不重复问已确认的技术路线或提交权限。

## 已完成的功能

后端：
- 聊天／向量独立 endpoint、key、model 与实际维度测试；来源优先级合并不跨服务
  继承密钥；仅显式 loopback 可免 Key；真实工作流未配置时不静默 mock。
- 向量配置完整暂存，测试后确认应用，先备份、清向量保留书签正文。
  modelspace fingerprint 覆盖 CLI 与直接向量阶段，同维不同服务也拒绝混用。
- 持久化任务、取消、重启 interrupted、partial 状态，跨页面跟踪。
- 导入 64 MB 限制，显式来源发现使用 HMAC ID，不接受任意客户端路径。
- 真实分页，folder/tag/domain/session 筛选；扩展近期认证连接状态；
  显式 GitHub 更新检查。

共享 React：
- 收藏索引与正文阅读、书签浏览／批次、筛选、分页、正文／AI 摘要／相关书签。
- IME、AbortController、过期响应隔离、Ctrl+K、列表上下键、Escape 保留查询。
- 手机导航 inert、焦点进入／陷阱／还原，Radix 阅读抽屉，预览 tabs 键盘操作。
- 连续导入 → 双模型 → 独立测试 → 确认索引 → 搜索向导，可跳过 AI。
- 查询语法建议、综合回答发送确认／编号引用、按需搜索解释。
- 中英、明暗、离线资源、reduced motion、真实 loading/error/retry。
- 区分未保存 draft 与 tested；有未保存 draft 时禁止 apply。
- 当前方向以内容为中心：72px 横向导航，未选中时 1160px 双列索引与搜索共用边界；
  选中后 360px 辅助索引与正文并排，30px 阅读标题、16px/1.85 正文。
- 桌面专注阅读移除搜索行，可展开／反向恢复；窄窗口为全屏阅读，明确“返回收藏”。
  正文有 24 条缓存和过期响应防护；正文／摘要／相关视图各自恢复滚动位置。
- GSAP 控制桌面面板和 tab 指示，Motion 控制抽屉与改造后的 Rare UI ScrollProgress；
  无列表逐项入场。具体 token 以 DESIGN.md 和实际 CSS 为准。

桌面／交付：
- Tauri 每数据目录单实例，启动超时／重试、托盘、全局快捷键、
  默认不开机启动，偏好保存错误反馈。
- 冻结后端隔离就绪检测、认证复用、端口冲突避让、优雅退出、父进程清理。
- NSIS 当前用户安装，携带 Python sidecar 与 WebView2 离线安装器，不含大模型。
- React 打进 Python wheel/sdist、Docker、Tauri；npm 锁文件与 Cargo.lock 入库。
- README 双语、桌面使用文档、官网工作台说明／真实截图和来源记录。

## 提交与验证检查点

关键提交：
- `e957ffb`：双模型配置与共享 React 工作台。
- `9319e69`：配置隔离与桌面运行验证。
- `302461a`：查询建议、综合回答、搜索解释、交付文档。
- `3622848`：独立审阅四项交互修正、退出诊断。
- `cfb8d26`：云端 WebView 检查参数、源码格式化、设计文档／官网截图。
- `de661c0`：新视觉美化、初次加载态、导入定位修正、扩展截图宽度。
- `372abaf`：修正 PR CI 同时构建 wheel/sdist，取回前端格式化代码。
- `08c0b2e`：按用户明确选择，改为通透明亮、内容优先的新版界面。
- `673af75`：本轮完整重设计共享检索与阅读界面，加入真实渲染／短录屏证据。
- `3bf0c3f`：修复 Motion 锁文件的传递依赖约束。
- `d618c52`：集中修正阅读展开边界、密度与对比度、滚动锚定和抽屉反向操作；
  增加已安装 WebView 的合成 HTML 导入／检索／空正文验证。

已成功 Web：
[37203068070](https://github.com/88lin/facetmark/actions/runs/37203068070)，
`3622848`：1882 Python passed / 1 skipped，8 Playwright passed，
TypeScript/Vite、wheel/sdist、Docker、扩展均通过。

已成功 Windows：
[37204513032](https://github.com/88lin/facetmark/actions/runs/37204513032)，
`cfb8d26`：冻结程序隔离、NSIS 构建、安装后实际 WebView 的 React DOM／向导、
同版本重装、卸载保留 DB/token、父进程结束后清理均通过。
小型证据已取回 `.desktop-build/windows-success/` 并检查 JSON 和安装截图；
没有下载大安装包。

Web `37204513115` 在 `cfb8d26` 只有导入测试失败，7/8 passed：
通用“导入书签”按钮定位偶尔匹配导航与初次加载误显的空库按钮。
`de661c0` 已限定 sidebar 定位并修正初次加载态，不再把异常请求显示为永久加载。

此前美化提交 `de661c0` 的云端运行已全部成功：
- Web：[37258068972](https://github.com/88lin/facetmark/actions/runs/37258068972)
- Windows：[37258068939](https://github.com/88lin/facetmark/actions/runs/37258068939)

Web 1882 passed / 1 skipped、8 Playwright passed，22 张截图；Windows 安装后 React
渲染、重装／卸载保留数据与进程清理通过。证据在 `.desktop-build/review-polish/`
和 `.desktop-build/windows-polish/`。**用户随后否定了这一视觉，不应作为最终展示图。**

PR [#44](https://github.com/88lin/facetmark/pull/44) 已创建，保持 draft。
首次 PR CI 的 wheel-only 命令与 wheel/sdist 检查契约冲突，已在 `372abaf` 修好。
[37260520353](https://github.com/88lin/facetmark/actions/runs/37260520353) 的十项完整 CI
已全通过，覆盖 Linux/Windows × Python3.10/3.12、MCP stdio、扩展、集成、Docker。
`08c0b2e` 的 Web／Windows／CI 后续均已通过，但用户仍不满意实际画面。
它是历史功能基线，不作为本轮视觉验收。

## 上一版交付记录（外观已被用户否定）

本轮首批 `3bf0c3f` 的真实渲染已检查：12/14 浏览器测试通过。两项失败分别为
浏览器滚动锚定与测试查询误命中；首批录屏转 MP4 缺 ffmpeg。Windows 基线通过。
这些问题和独立审阅的视觉修正已集中处理，`d618c52` 已确认通过：

- Web：[37311576521](https://github.com/88lin/facetmark/actions/runs/37311576521)。
- Windows：[37311576569](https://github.com/88lin/facetmark/actions/runs/37311576569)。
- CI：[37311583781](https://github.com/88lin/facetmark/actions/runs/37311583781)。

Web：1882 Python passed / 1 skipped、14 Playwright passed、32 张真实截图，
另有 MP4/WEBM；CI 全部十项通过。Windows 冻结服务、安装后 WebView 合成导入／
检索／阅读空态、关闭保留查询、同版本重装、卸载数据保留和父进程清理均通过。

额外测试提交 `8da4e35` 只增加非零列表滚动位置断言，产品源码保持 `d618c52`。
显式 [37312860101](https://github.com/88lin/facetmark/actions/runs/37312860101)
补充运行已通过 14 项浏览器测试及全套 Experience 检查；没有为这个测试变化重复
Windows 打包。独立 reviewer 最终给出 **ship**，原七项修正全部 resolved；
这个结论只覆盖所列修正，不代表用户已经认可最终视觉。

最终 Web 证据在 `.desktop-build/redesign-confirmation`，Windows 小型证据在
`.desktop-build/redesign-windows`。DESIGN.md 和 design.json 按真实 CSS/组件更新；
官网四张截图来自 `d618c52`，带版本和来源元数据。后续文档提交不改变产品源码。
首批图位于 `.desktop-build/redesign-review`，不作为修正版本的最终截图。
初始未提交文档／资产备份在 `.desktop-build/preserved-inputs`，不得回滚丢弃。

## 验证边界

- Windows hosted runner 为 Windows Server，不等价于 Windows 10/11 真机覆盖。
- 程序防火墙规则不等于物理整机断网。
- 同版本修复安装不等于跨版本升级。
- runner 账户不证明普通非管理员行为完整通过。
- 未签名 preview，不承诺消除 SmartScreen；无签名信任链验收。
- 外部真实模型服务质量、个人浏览器资料不在 CI 验证范围。
- Actions artifacts 保留 14 天。

## 工具与工程注意

- 使用 apply_patch；同批 patch 任一匹配失败可能整批不落地，必须核对 git diff。
- 本地轻量 Python：`.venv/Scripts/python`。本机不跑 npm build、Playwright、Tauri。
- Actions：`.github/workflows/experience.yml`、`desktop.yml`。
- 小型 Web evidence：`facetmark-visual-evidence`，含 PNG provenance、字体诊断、
  全视口 contact sheets 和 MP4/WEBM。`facetmark-experience-review` 另含大构建产物，
  不为取图下载整个包；也不覆盖本地更新过的源码。
- Windows small evidence：`desktop-install-evidence`；大安装 artifact：
  `facetmark-windows-x64-preview`，只向用户提供云端链接。
- WebView CI 调试需同时满足 GITHUB_ACTIONS、github-hosted、
  FACETMARK_CI_WEBVIEW_INSPECT=1，通过 Tauri builder 显式传参。
- 适用 Impeccable 技能；context 和 detector 在本次任务已各执行一次，不重复。
  用户将设计判断交给实现者，不重复开启风格问答。集中检查、集中修复、一次确认；
  后续只处理独立 reviewer 指出的实质问题，不再无休止微调。
- 本轮未用 Oil Motion 或生成素材；未改全局技能、WorkBuddy 映射或任何个人浏览器资料。
