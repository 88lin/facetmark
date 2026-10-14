# 本机 Agent 摘要连接

在 **设置 → AI 连接 → 摘要来源** 选择 **本机 Agent**。支持 Codex、Claude Code 和 OpenCode；
界面显示自动模式实际选中的程序，也可以指定其中一个。自动模式按 Codex、Claude Code、OpenCode
的顺序选择已找到的程序，不会在连接失败后偷偷换成另一个账号或服务。

**已检测到**只表示找到了可启动的文件，不表示已经登录。点击 **测试并保存**后，
Facetmark 用固定测试文本验证连接，成功才保存这一通道；测试不发送收藏内容。
成功结果显示使用的 Agent／模型。摘要和向量配置、草稿与测试结果相互独立。

## 安装与重新检测

| Agent | 运行方式 | 版本要求 |
| --- | --- | --- |
| Codex | `codex exec`，stdin 输入、JSON 事件 | 需支持 `--ephemeral --ignore-user-config --ignore-rules` |
| Claude Code | `claude --print`，stdin 输入、JSON 结果 | 需支持空工具集、严格 MCP 配置和禁用 hooks |
| OpenCode | `opencode run --format json --pure`，stdin 输入 | 以 1.19.0 验证，需支持这些非交互参数 |

探测会检查进程 PATH、常用的用户安装目录及 npm、Bun、pnpm、Volta、Scoop、Homebrew 位置。
Windows 还会只读读取注册表中当前的用户和系统 PATH，减少桌面程序启动后新安装 CLI 却查不到的情况。
不会扫描整个磁盘或启动交互式 shell。Windows npm 包装器被解析为对应的 Node 入口或原生程序，
OpenCode 新版的 `opencode.exe` 不依赖额外的 Node 启动步骤。

安装或更新后点击 **重新检测**。该操作保留正在填写的模型草稿；读取失败和未检测到是不同状态，
所选 Agent 未找到时不能测试。展开 **模型、超时与安装位置**可查看探测到的路径、指定模型及单次超时。
如果在自定义目录安装，将目录加入 PATH 后重新检测。CLI 参数不兼容时，连接错误会提示更新版本。

## OpenCode 配置复用

支持 `opencode.json`、`opencode.jsonc`、`OPENCODE_CONFIG`、`OPENCODE_CONFIG_DIR` 和
`OPENCODE_CONFIG_CONTENT` 中的模型／provider 配置；JSONC 注释、尾逗号和相对凭据文件引用会保留语义。
模型留空时沿用配置或 OpenCode 记住的默认值；覆盖模型时填写 `provider/model`。

仅复用模型相关配置。摘要运行使用临时工作目录、临时会话数据库、禁止工具的独立 agent，
关闭项目指令、外部插件、MCP 和会话分享。内置认证适配器保留，CLI 使用正常的认证存储，
可以按自身流程更新 OAuth 凭据；Facetmark 不改写原有配置文件，也不把凭据放进命令行。
依赖外部认证插件或 `wellknown` 组织远程配置的服务请使用 API 接入。

Agent 是模型服务的客户端，摘要仍会发送到该模型服务，并不代表在本机离线推理。
每个 Agent 最多并发两次调用，超时和取消会终止子进程树。自动模式解析到不同程序时，
旧连接测试失效，需要重新测试实际程序。

## 验证范围

`tests/test_local_agents.py` 覆盖探测、包装器、配置隔离、输出格式、超时／取消与错误信息。
`frontend/tests/local-agents.spec.ts` 覆盖设置页的探测、选择、重试、测试／保存和独立通道状态。
Actions 中的 `scripts/check_opencode.py` 安装真实 OpenCode 1.19.0，在 Windows 和 Linux 上
连接隔离的模拟 HTTP 模型服务，验证中文 stdin、结果解析、请求不带工具和原配置保持不变。
这些测试验证集成协议；没有调用个人模型账号，也不证明真实模型的摘要质量或额度。
