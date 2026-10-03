"""Official-documentation model examples shared by both site languages.

Reviewed 2026-10-03. These are copyable starting points, not account discovery
or claims of measured retrieval quality. Keep historical evaluation models intact.
"""

import json

CHECKED = "2026-10-03"

LOCAL = {
    "embed_backend": "local",
    "local_embed_path": "BAAI/bge-m3",
    "embed_model": "BAAI/bge-m3",
    "embed_dim": 1024,
}

PRESETS = [
    (
        "OpenAI",
        {
            "api_key": "sk-...",
            "base_url": "https://api.openai.com/v1",
            "chat_model": "gpt-6-luna",
            "chat_extra_body": {"reasoning_effort": "none", "max_completion_tokens": 4096},
            "embed_model": "text-embedding-3-small",
            "embed_dim": 1536,
        },
        "https://developers.openai.com/api/docs/models/gpt-6-luna",
        "Luna suits high-volume extraction; gpt-6.1-sol is a higher-cost option (use low reasoning, not none). The current small embedding model remains unchanged.",
        "Luna 适合批量提取；需要更强模型可选 gpt-6.1-sol（思考设为 low，不支持 none）。现有小型向量模型仍是当前型号。",
    ),
    (
        "DeepSeek",
        {
            "api_key": "sk-...",
            "base_url": "https://api.deepseek.com/v1",
            "chat_model": "deepseek-flash",
            "chat_extra_body": {"thinking": {"type": "disabled"}, "max_tokens": 4096},
            **LOCAL,
        },
        "https://api-docs.deepseek.com/quick_start/pricing",
        "DeepSeek-V4.1-Flash replaces the old deepseek-chat example. This example uses local embeddings; install facetmark[local] first.",
        "DeepSeek-V4.1-Flash 替换旧 deepseek-chat 示例。此配置搭配本地向量，先安装 facetmark[local]。",
    ),
    (
        "Moonshot / Kimi",
        {
            "api_key": "sk-...",
            "base_url": "https://api.moonshot.cn/v1",
            "chat_model": "kimi-k3",
            "chat_extra_body": {"reasoning_effort": "low", "max_completion_tokens": 8192},
            **LOCAL,
        },
        "https://platform.kimi.com/docs/models",
        "moonshot-v1 was retired on 2026-08-31. K3 always reasons: omit temperature and use max_completion_tokens. Local embeddings require facetmark[local].",
        "moonshot-v1 已于 2026-08-31 下线。K3 始终思考：不传 temperature，使用 max_completion_tokens。本地向量需要 facetmark[local]。",
    ),
    (
        "Zhipu / GLM",
        {
            "api_key": "...",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "chat_model": "glm-5.3-flash",
            "chat_extra_body": {"reasoning_effort": "low", "max_tokens": 8192},
            "embed_model": "embedding-3",
            "embed_dim": 2048,
        },
        "https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash",
        '5.3 Flash is paid and always reasons. For free chat use glm-4.7-flash with {"thinking":{"type":"disabled"},"max_tokens":4096}. embedding-3 remains current and is billed separately.',
        '5.3 Flash 是付费且始终思考的模型。免费对话可选 glm-4.7-flash，参数换成 {"thinking":{"type":"disabled"},"max_tokens":4096}。embedding-3 仍是当前向量型号，单独计费。',
    ),
    (
        "SiliconFlow",
        {
            "api_key": "sk-...",
            "base_url": "https://api.siliconflow.cn/v1",
            "chat_model": "Qwen/Qwen3.6-27B",
            "chat_extra_body": {"enable_thinking": False, "max_tokens": 4096},
            "embed_model": "Qwen/Qwen3-Embedding-0.6B",
            "embed_dim": 1024,
        },
        "https://docs.siliconflow.cn/docs/userguide/capabilities/text-generation",
        "Uses the Qwen model in the current Chinese provider guide; availability differs from Qwen's own releases. For Qwen/Qwen3-Embedding-8B at 1024 dimensions, also set embed_send_dimensions = true.",
        "采用当前中文官方指南确认的 Qwen 型号；服务商上架进度与 Qwen 官方发布不同。若用 Qwen/Qwen3-Embedding-8B 并保留 1024 维，还需设置 embed_send_dimensions = true。",
    ),
    (
        "Aliyun Bailian",
        {
            "api_key": "sk-...",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "chat_model": "qwen3.8-flash",
            "chat_extra_body": {"enable_thinking": False, "max_tokens": 4096},
            "embed_model": "qwen3.7-text-embedding",
            "embed_dim": 1024,
            "embed_batch_size": 20,
        },
        "https://help.aliyun.com/zh/model-studio/text-generation-model",
        "The existing Beijing host remains supported. You may use your workspace-specific host from the console; match the key and region. Current embedding requests allow at most 20 texts.",
        "原北京域名仍受支持，也可填写控制台提供的业务空间专属域名；Key 与地域需匹配。当前向量接口每批最多 20 条文本。",
    ),
    (
        "Ollama",
        {
            "base_url": "http://127.0.0.1:11434/v1",
            "api_key": "ollama",
            "chat_model": "qwen3.8:27b",
            "chat_extra_body": {"reasoning_effort": "none", "max_tokens": 4096},
            "embed_model": "qwen3-embedding:0.6b",
            "embed_dim": 1024,
        },
        "https://docs.ollama.com/api/openai-compatibility",
        "Pull both models first. Qwen3.8 27B downloads about 18 GB; qwen3.5:4b or qwen3.5:9b are smaller alternatives. The placeholder key selects the real local endpoint instead of mock mode.",
        "先用 ollama pull 下载两种模型。Qwen3.8 27B 约 18 GB；小内存可选 qwen3.5:4b 或 qwen3.5:9b。占位 Key 用于启用真实本地接口，避免进入演示模式。",
    ),
    (
        "vLLM",
        {
            "base_url": "http://127.0.0.1:8000/v1",
            "api_key": "not-used",
            "chat_model": "Qwen/Qwen3.8-27B",
            "chat_extra_body": {"chat_template_kwargs": {"enable_thinking": False}, "max_tokens": 4096},
            **LOCAL,
        },
        "https://recipes.vllm.ai/Qwen/Qwen3.8-27B",
        "Use the model name served by your deployment and the actual key if authentication is enabled. The chat server does not automatically serve an embedding model; this example uses facetmark[local].",
        "模型名必须与部署时的名称一致；启用鉴权时填写实际 Key。对话服务不会自动提供向量模型，本例使用 facetmark[local]。",
    ),
]


def config_text(config: dict) -> str:
    lines = []
    for key, value in config.items():
        if isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines)


def provider_blocks(lang: str) -> list[tuple]:
    zh = lang == "zh"
    intro = (
        f"官方文档核对日期：{CHECKED}。先运行 <code>facetmark config path</code> 找到配置文件。"
        "请确认账户已开通所选模型，并先测试少量页面；以下型号更新未重新评测检索效果。"
        if zh else
        f"Official documentation checked {CHECKED}. Locate your file with <code>facetmark config path</code>. "
        "Confirm account access and test a small batch first; retrieval quality has not been re-evaluated for these model updates."
    )
    blocks = [("p", intro)]
    for name, config, source, en, cn in PRESETS:
        blocks.append(("cb", name, config_text(config)))
        label = "官方文档" if zh else "Official documentation"
        blocks.append(("p", f'{cn if zh else en} <a href="{source}">{label}</a>.'))
    blocks.append((
        "callout", "",
        "对话与在线向量共用接口地址" if zh else "Chat and online embeddings share an endpoint",
        "<p>只有一组 base_url 与 api_key。DeepSeek、Kimi 或独立 vLLM 对话服务可搭配上面的本地向量配置。"
        "更换向量模型，即使维度不变，也需要重建向量索引。对话附加参数会用于所有备用模型，必须同时兼容。</p>"
        if zh else
        "<p>There is one base_url and api_key pair. DeepSeek, Kimi and standalone vLLM chat servers can use "
        "the local embedding configuration above. Rebuild vectors after changing the embedding model, even "
        "if its dimension is unchanged. Chat parameters apply to every fallback model and must work with all of them.</p>",
    ))
    return blocks
