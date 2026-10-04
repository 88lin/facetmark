# Facetmark 桌面预览

测试分支：`desktop/facetmark-experience`。首次目标为 Windows 10/11 x64。
这是未签名预览版，不是正式发布。测试分支不会自动合并 main。

## 下载与首次使用

1. 打开 [desktop-preview Actions](https://github.com/88lin/facetmark/actions/workflows/desktop.yml)，
   选择此测试分支最新成功的运行，下载 `facetmark-windows-x64-preview`。
2. 解压后运行 NSIS 安装程序。安装到当前用户目录；带 Python 后端和 WebView2
   离线安装器，不需要安装 Python、Node、Rust，也不带大模型。
3. 导入 HTML／JSON 书签副本；或主动查找本机 Chromium 来源，再选择一个来源。
   不修改浏览器原文件，不自动读取所有个人配置。
4. 分别填写聊天、向量服务地址、Key 和模型名。支持同服务，也支持不同服务。
   Ollama 等已有本机服务可填写 `http://127.0.0.1:11434/v1` 并勾选免 Key。
5. 独立测试两条连接。测试仅发送固定测试句，并报告实测向量维度。
   保存后应用已测试的向量配置。更换向量空间时，确认备份与重建。
6. 在任务页了解发送内容并确认索引。也可以跳过 AI，直接用关键词搜索。

API Key 留空且未编辑时保留；“清除已保存的密钥”才清除。更换地址不会继承
另一服务的密钥。受环境变量控制的字段显示只读。保存与应用是不同状态；向量
配置应用前旧空间仍保持一致。启动新索引前需要当前进程确认两条实际连接。

## 日常操作

- 左侧切换全部书签、浏览批次、文件夹、标签和站点；中间搜索和翻页。
- 选择结果后右侧显示正文、AI 摘要和相关书签。未读取正文与未生成摘要会明确说明。
- `Ctrl+K` 聚焦搜索，列表上下箭头选择，`Escape` 关闭预览而保留查询。
- 窄窗口与手机 Web 用预览抽屉，退出后焦点回到所选书签。
- 任务跨页面继续；取消在阶段结束后生效。退出或崩溃后显示中断，重新运行用指纹
  跳过未变化且已完成的内容。界面显示阶段，不把阶段数当作工作百分比。
- 关闭主窗口后留在托盘，首次有提示。托盘管理开机启动（默认关闭）、全局快捷键
  `Ctrl+Shift+Space` 和退出。设置中可主动检查 GitHub 正式版本与打开测试包下载页。
- 默认端口 8787 被占用时自动换端口。扩展设置使用工作台复制的当前地址和配对令牌。
  扩展需要手动加载，不会自动安装；近期已连接状态来自认证过的扩展请求。

## 数据与更新

每个数据目录最多一个受管后端。复用已有服务时核对版本、认证和数据库身份。
数据目录沿用 `FACETMARK_DATA_DIR`；默认使用系统用户数据目录。
应用升级前使用 SQLite backup API 备份；更换向量模型或端点前也先备份。
清理向量不删除书签与原文。卸载默认保留数据。

预览包尚未配置签名证书，不承诺消除 SmartScreen。下载和安装更新由用户主动完成。

## Web、Python 与 Docker

开发源位于 `frontend/`，构建产物为 `src/facetmark/web/dist/`，不提交生成的 JS/CSS。
Actions、Docker 多阶段构建和 Python 发布工作流先执行 `npm ci && npm run build`，
再构建完整发行物。Hatch 把生成资源纳入 wheel 与 sdist；云端检查实际 wheel 内容。
源码未构建 React 时仍可运行旧资源作开发兼容，预览发行物必须通过 React 资源门禁。

Python 方式仍为 `facetmark serve`，桌面也访问同一后端 `/app`。配对令牌仅自动
提供给 loopback Host + loopback peer；其他访问需主动输入令牌，管理接口仍限制
loopback。Docker 运行在非 root 用户下，只读根文件系统，数据卷独立持久化。

## 验证与边界

- 所有打包、大文件下载、安装、浏览器运行和 WebView 测试均在 GitHub Actions。
- `experience-validation`：前端类型检查／构建、Python 回归、扩展测试、浏览器
  行为和截图、wheel 内容与 Docker 实际运行。
- `desktop-preview`：冻结程序无 Python PATH 隔离、中文路径、端口冲突、认证、
  NSIS 离线安装、安装后 WebView 渲染、同版本修复安装、卸载保留数据。
- 图像只用合成书签。Actions 每项检查是否真正通过，以对应提交的日志和产物为准。
- Windows hosted runner 是 Windows Server，不能代替 Windows 10/11 真机覆盖。
  防火墙按程序阻断，不等于整机物理断网。同版本重装不是跨版本升级测试。
  普通非管理员账户、Windows 10/11 真机和签名信任链仍需额外验证。

产物保留 14 天；过期后重新运行工作流。不下载大安装包到开发者电脑。
