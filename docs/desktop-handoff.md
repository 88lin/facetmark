# Facetmark 桌面化与体验升级交接

## 2026-10-06 用户否定后的重建

用户明确否定上一版：**“整体太普通，像后台管理工具”**。下面 `d618c52` 的测试和
七项修正 ship 仅是历史记录，不是新视觉的验收。新的独立全量复审给出 rebuild。

`33bee64` 重建共享前端骨架：取消常驻分类侧栏，改为顶部导航和按需筛选；未选中时
双列收藏索引，选中后索引退为辅助、文章成为主要画面；合并阅读工具，收藏信息折叠；
窄窗口改为全宽阅读。新增布局源为 `frontend/src/workbench.css`。
首批 [37407299839](https://github.com/88lin/facetmark/actions/runs/37407299839)
正在生成真实渲染。待看图集中修正后，更新设计规范、最终截图和下面的交付状态。

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
- 三栏检索、书签浏览／批次、筛选、分页、正文／AI 摘要／相关书签。
- IME、AbortController、过期响应隔离、Ctrl+K、列表上下键、Escape 保留查询。
- 手机导航 inert、焦点进入／陷阱／还原，Radix 阅读抽屉，预览 tabs 键盘操作。
- 连续导入 → 双模型 → 独立测试 → 确认索引 → 搜索向导，可跳过 AI。
- 查询语法建议、综合回答发送确认／编号引用、按需搜索解释。
- 中英、明暗、离线资源、reduced motion、真实 loading/error/retry。
- 区分未保存 draft 与 tested；有未保存 draft 时禁止 apply。
- 当前方向“索引与阅读同桌”：208px 轻导航、72px 共享搜索栏、424px 来源优先索引，
  余下空间连续阅读；28px 阅读标题、16px/1.95 正文、固定 tabs 与滚动位置页脚。
- 桌面专注阅读可展开／反向恢复；窄窗口采用可打断阅读抽屉，关闭回到选中项。
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

## 当前交付收尾

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
