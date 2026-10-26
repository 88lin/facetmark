import { useEffect, useId, useState } from "react";
import type { Catalog } from "./ModelPicker";
import { useText } from "./locale";
import { CapsuleButton } from "./ui/controls";
import { effortLevels, inferReasoningMethod, parseChatOptions, readEndpointReasoning,
  writeEndpointReasoning, type ReasoningMethod } from "./reasoning";
import "./reasoning-settings.css";

export function ReasoningSettings({ agent, model, baseUrl = "", value, extraBody, catalog, disabled, onChange }: {
  agent?: string; model: string; baseUrl?: string; value: string; extraBody: string;
  catalog: Catalog | null; disabled: boolean; onChange: (value: string) => void;
}) {
  const t = useText(), id = useId();
  const [manual, setManual] = useState(false);
  const [methodOverride, setMethodOverride] = useState<ReasoningMethod>();
  useEffect(() => { setMethodOverride(undefined); setManual(false); }, [agent, model, baseUrl]);
  const body = parseChatOptions(extraBody);
  const current = readEndpointReasoning(body || {});
  const method = methodOverride || current.method || inferReasoningMethod(model, baseUrl);
  const selectedModel = model || catalog?.default_model || "";
  const choice = catalog?.models.find(item => item.id === selectedModel);
  const inherited = model ? agent === "claude"
    ? choice?.default_reasoning_effort || catalog?.configured_reasoning_effort
    : catalog?.configured_reasoning_effort || choice?.default_reasoning_effort
    : catalog?.default_reasoning_effort;
  const catalogLevels = agent || method === "reasoning_effort"
    ? choice?.reasoning_levels?.map(level => level.id) || [] : [];
  const defaults = agent === "opencode" ? [] : agent === "claude"
    ? ["low", "medium", "high", "xhigh", "max"] : agent === "codex" ? [...effortLevels, "ultra"]
      : method === "reasoning_effort" ? effortLevels : ["none", "enabled"];
  // A cache is a suggestion, not a restriction on a custom service or a newer
  // CLI. Known effort names stay selectable even with an incomplete catalog.
  const levels = [...new Set([...catalogLevels, ...defaults])];
  // These documented models cannot disable reasoning. Relays still need a test.
  const offered = !agent ? levels.filter(level =>
    !(level === "none" && /gpt-6\.1-sol|gpt-6-astra/i.test(model))
    && !(level === "minimal" && /gpt-6\.1-sol/i.test(model))) : levels;
  const selected = agent ? value : current.value;
  const label = (level: string) => ({
    none: t("关闭思考", "Thinking off"), enabled: t("开启思考", "Thinking on"),
    minimal: t("最少 · minimal", "Minimal · minimal"), low: t("低 · low", "Low · low"),
    medium: t("中 · medium", "Medium · medium"), high: t("高 · high", "High · high"),
    xhigh: t("更高 · xhigh", "Extra high · xhigh"), max: t("最高 · max", "Maximum · max"),
    ultra: t("ultra", "Ultra"), custom: t("高级参数自定义", "Custom advanced parameters"),
  } as Record<string, string>)[level] || level;
  const choose = (next: string) => agent ? onChange(next) : onChange(writeEndpointReasoning(extraBody, method, next));
  const unavailable = !agent && !body;
  const customAllowed = Boolean(agent || method === "reasoning_effort");
  return <div className="reasoning-settings">
    <label className="field" htmlFor={id}>
      {agent === "opencode" ? t("思考模式 / 模型变体", "Thinking / model variant") : t("思考模式", "Thinking mode")}
      <select id={id} name={agent ? "chat_agent_reasoning_effort" : "chat_reasoning"}
        aria-label={t("思考模式", "Thinking mode")} value={selected}
        disabled={disabled || unavailable} onChange={event =>
          event.target.value === "__custom_level__" ? setManual(true) : choose(event.target.value)}>
        <option value="">{agent ? t("沿用默认", "Use default")
          : t("沿用服务默认", "Use service default")}{agent && inherited ? " · " + label(inherited) : ""}</option>
        {offered.map(level => <option key={level} value={level}>{label(level)}</option>)}
        {selected && !offered.includes(selected) && <option value={selected} disabled={selected === "custom"}>
          {selected === "custom" ? label(selected) : t("当前 · ", "Current · ") + label(selected)}
        </option>}
        {customAllowed && <option value="__custom_level__">{t("自定义档位 / 变体…", "Custom level / variant…")}</option>}
      </select>
    </label>
    <p className="reasoning-note" role={unavailable ? "alert" : "status"}>
      {unavailable ? t("额外参数不是有效的 JSON 对象，请先在高级参数中修正。", "Fix the extra parameter JSON object before changing thinking mode.")
        : agent && inherited ? t("已读取默认档位；模型支持和实际访问权限以连接测试为准。", "Default level read from configuration or catalog. Test model support and access.")
        : agent === "opencode" ? t("档位来自当前模型的变体。目录未提供时，可手动填写已有变体名称。", "Levels come from this model's variants. Enter a known variant if the catalog provides none.")
        : agent && choice?.reasoning_levels ? t("可自行选择档位；目录未列出的档位也可以尝试，是否支持由连接测试确认。", "Choose your effort level. You can also try levels absent from the catalog; the connection test checks support.")
        : t("默认值由服务或客户端决定。选择的档位需经过测试；更高档位通常耗时更长。", "The service or client decides its default. Test the selected level; higher effort usually takes longer.")}
    </p>
    {(agent === "codex" || agent === "claude" || (!agent && method === "reasoning_effort")) && <div className="reasoning-shortcuts" role="group" aria-label={t("常用思考档位", "Common thinking levels")}>
      {["high", "xhigh", "max"].map(level => <CapsuleButton key={level} type="button"
        className="reasoning-shortcut" aria-pressed={selected === level} disabled={disabled || unavailable}
        onClick={() => { setManual(false); choose(level); }}>{level}</CapsuleButton>)}
    </div>}
    {customAllowed && manual && <div className="reasoning-manual">
      <CapsuleButton className="text-button" type="button" disabled={disabled} onClick={() => setManual(!manual)}>
        {t("收起自定义档位", "Hide custom level")}
      </CapsuleButton>
      <label className="field">{t("自定义档位 / 变体名称", "Custom level / variant name")}
        <input value={selected === "custom" ? "" : selected} disabled={disabled || unavailable} aria-label={t("自定义思考档位", "Custom thinking level")}
          maxLength={80} spellCheck={false} autoComplete="off" onChange={event => choose(event.target.value.trim())}/>
      </label>
    </div>}
    {!agent && method !== "reasoning_effort" && <p className="reasoning-note">{t("当前接口格式只区分开启 / 关闭思考。如果服务支持 high、xhigh 或 max，请在下方切换为 reasoning_effort 格式。", "This parameter format switches thinking on or off. For a service supporting high, xhigh or max, select reasoning_effort below.")}</p>}
    {!agent && <details className="reasoning-compatibility">
      <summary>{t("服务兼容设置", "Service compatibility")}</summary>
      <label className="field">{t("思考参数格式", "Thinking parameter format")}
        <select value={method} disabled={disabled || unavailable} aria-label={t("思考参数格式", "Thinking parameter format")}
          onChange={event => {
            const next = event.target.value as ReasoningMethod;
            setMethodOverride(next);
            if (selected && selected !== "custom")
              onChange(writeEndpointReasoning(extraBody, next, next === "reasoning_effort"
                ? selected === "enabled" ? "medium" : selected : selected === "none" ? "none" : "enabled"));
          }}>
          <option value="reasoning_effort">OpenAI / Kimi / Ollama · reasoning_effort</option>
          <option value="thinking">DeepSeek / GLM · thinking</option>
          <option value="enable_thinking">Qwen / SiliconFlow · enable_thinking</option>
          <option value="chat_template_kwargs">vLLM · chat_template_kwargs</option>
        </select>
      </label>
      <p className="reasoning-note">{t("按模型和服务选择格式；自定义服务仍需测试确认。高级 JSON 中的其他参数会保留。",
        "Choose the format your model and service support, then test it. Other advanced JSON parameters are preserved.")}</p>
    </details>}
  </div>;
}
