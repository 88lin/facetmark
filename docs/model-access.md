# Current model configuration / 当前模型配置

Official documentation checked / 官方文档核对日期：**2026-10-03**.

Copyable TOML examples are in the [English configuration guide](landing/config.html#presets) and [中文配置指南](landing/config.zh.html#presets). Their shared source is [`landing/model_presets.py`](landing/model_presets.py). This update checks documented API compatibility; it does not claim live account access or new retrieval benchmarks.

本次更新核对公开官方文档与接口参数，未使用付费 Key 做真实模型调用，也未重新测量检索质量。新默认仅影响没有显式指定型号的配置；现有 `.env`、环境变量、`config.toml` 和历史评测记录保留原值。

| Provider / 服务商 | Chat / 对话 | Embeddings / 向量 | Notes / 说明 |
| --- | --- | --- | --- |
| OpenAI | `gpt-6-luna` | `text-embedding-3-small` · 1536 | 批量提取使用 `reasoning_effort: "none"`；更强的 `gpt-6.1-sol` 用 `low`，不支持 `none` |
| DeepSeek | `deepseek-flash` | 本地 / local `BAAI/bge-m3` · 1024 | 对应 V4.1-Flash；`thinking: {"type":"disabled"}`；官方没有可直接搭配的向量配置 |
| Kimi | `kimi-k3` | 本地 / local `BAAI/bge-m3` · 1024 | K3 始终思考，用 `reasoning_effort: "low"`；不传温度；`moonshot-v1` 已下线 |
| Zhipu / 智谱 | `glm-5.3-flash` | `embedding-3` · 2048 | 最新 Flash 为付费，思考设 `low`；免费对话可选 `glm-4.7-flash`，允许关闭思考 |
| SiliconFlow / 硅基流动 | `Qwen/Qwen3.6-27B` | `Qwen/Qwen3-Embedding-0.6B` · 1024 | 官方当前 Qwen 示例；未确认该平台上架 Qwen3.8。顶层 `enable_thinking: false` |
| Bailian / 百炼 | `qwen3.8-flash` | `qwen3.7-text-embedding` · 1024 | 顶层 `enable_thinking: false`；向量批次最多 20 条 |
| Ollama | `qwen3.8:27b` | `qwen3-embedding:0.6b` · 1024 | 最新 27B 下载约 18 GB；较小选项 `qwen3.5:4b` / `qwen3.5:9b`；兼容接口用 `reasoning_effort: "none"` |
| vLLM | `Qwen/Qwen3.8-27B` | 本地 / local `BAAI/bge-m3` · 1024 | `chat_template_kwargs: {"enable_thinking":false}`；模型名称需与部署一致 |

## Chat parameters / 对话参数

The transport still uses `/chat/completions` with JSON Object output. `chat_extra_body` is a **JSON object encoded as a string**, merged into the top-level request. The application no longer forces `temperature=0.2`, because reasoning models may reject sampling parameters and Kimi K3 fixes its temperature. An empty value uses provider defaults; for predictable latency and output cost, set a budget appropriate to your model.

`chat_extra_body` 为 JSON 对象字符串，程序将字段合并到请求顶层。不要再套一层 `extra_body`；那是部分 SDK 的参数形式。空值采用服务商默认值。固定 `temperature=0.2` 已移除，避免新推理模型拒绝请求。

```toml
# OpenAI GPT-6 Luna: no reasoning, bounded output
chat_model = "gpt-6-luna"
chat_extra_body = '{"reasoning_effort":"none","max_completion_tokens":4096}'
```

```toml
# Kimi K3: reasoning cannot be disabled; the budget includes reasoning
chat_model = "kimi-k3"
chat_extra_body = '{"reasoning_effort":"low","max_completion_tokens":8192}'
```

DeepSeek, GLM, SiliconFlow, Bailian and local deployment examples use `max_tokens` where documented. Kimi's current API deprecates `max_tokens` in favor of `max_completion_tokens`. Budgets above are starting points, not guarantees that every page will fit. Truncated or refused responses are treated as failures and can use the configured fallback chain.

附加参数用于整个备用模型链，必须与链中所有模型兼容。`model`、`messages`、`response_format`、`stream` 和工具调用等会改变响应协议的字段不能覆盖。网页内容提取仍要求输出 JSON；模型拒绝、截断、非文本内容和非法响应均会报告错误。

## Embeddings and migration / 向量与迁移

- `embed_dim` records the actual vector width; it does not by itself ask the endpoint to shorten vectors. Set `embed_send_dimensions = true` only for models that document the `dimensions` parameter. The request then sends `embed_dim`, and every returned vector is validated.
- `embed_batch_size` limits each endpoint request. Pipeline batches are split automatically and usage is counted across all requests. The default is 64; current Bailian models need **20**. Older Bailian embedding models may require **10**.
- OpenAI `text-embedding-3-small` remains the current small model (1536 by default); `text-embedding-3-large` returns 3072 by default. Zhipu `embedding-3` remains current, with 2048 by default and documented reductions to 256/512/1024. Its API limits each input to 3072 tokens and each batch to 64.
- Qwen3 Embedding 0.6B returns 1024 dimensions; 4B returns 2560; 8B returns 4096. On SiliconFlow, 8B can request 1024 with `embed_send_dimensions = true`. Do not copy the 8B width into a 0.6B configuration.
- Local examples require `python -m pip install "facetmark[local]"`. `local_embed_path` must name a Hugging Face model ID or an existing directory; an empty path is an error, not a download instruction. Set `embed_model` to the same encoder identity you use for the index.
- **Changing the embedding model requires rebuilding vectors even when the dimension stays the same.** Back up the database first, configure the intended encoder, then use `facetmark reindex --vectors`. No existing library or user configuration is migrated by this code update.

维度相同不代表模型兼容。切换向量型号后应备份数据库并运行 `facetmark reindex --vectors`；本次只更新项目代码和示例，不改动真实书签库。`embed_send_dimensions` 默认关闭，避免把不受支持的参数发给旧模型。接口返回的每一行向量都会校验维度、序号及有限数值，防止错误结果写入索引。

## Official sources / 官方来源

- OpenAI: [model catalog](https://developers.openai.com/api/docs/models), [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [migration parameters](https://developers.openai.com/api/docs/guides/latest-model/gpt-6-astra), [embedding models and dimensions](https://developers.openai.com/api/docs/guides/embeddings).
- DeepSeek: [current models](https://api-docs.deepseek.com/quick_start/pricing), [updates and retirement notices](https://api-docs.deepseek.com/updates), [Chat API](https://api-docs.deepseek.com/api/create-chat-completion), [JSON output](https://api-docs.deepseek.com/guides/json_mode).
- Kimi: [models and retirement dates](https://platform.kimi.com/docs/models), [model parameters](https://platform.kimi.com/docs/api/models-overview), [Chat API](https://platform.kimi.com/docs/api/chat), [JSON output](https://platform.kimi.com/docs/guide/response_format).
- Zhipu: [GLM-5.3-Flash](https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash), [free GLM-4.7-Flash](https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash), [thinking modes](https://docs.bigmodel.cn/cn/guide/capabilities/thinking-mode), [embedding API](https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E6%96%87%E6%9C%AC%E5%B5%8C%E5%85%A5).
- SiliconFlow: [current text guide](https://docs.siliconflow.cn/docs/userguide/capabilities/text-generation), [embedding API](https://docs.siliconflow.cn/docs/api/embeddings-post), [retirement announcements](https://docs.siliconflow.cn/docs/release-notes/overview).
- Bailian: [current text models](https://help.aliyun.com/zh/model-studio/text-generation-model), [embedding API](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api), [JSON output](https://help.aliyun.com/zh/model-studio/json-mode), [compatible domains](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope). The old DashScope domains remain supported; workspace-specific domains must match your region and key.
- Ollama: [Qwen3.8](https://ollama.com/library/qwen3.8), [smaller Qwen3.5 models](https://ollama.com/library/qwen3.5), [Qwen3 embedding 0.6B](https://ollama.com/library/qwen3-embedding:0.6b), [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility).
- vLLM: [Qwen3.8 recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B). Embedding dimensions: [Qwen's official 0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B).
