export type ReasoningMethod = "reasoning_effort" | "thinking" | "enable_thinking" | "chat_template_kwargs";
export const effortLevels = ["none", "minimal", "low", "medium", "high", "xhigh", "max"];

export function parseChatOptions(text: string): Record<string, unknown> | null {
  try {
    const value: unknown = JSON.parse(text.trim() || "{}");
    return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
  } catch { return null; }
}

const object = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};

export function readEndpointReasoning(body: Record<string, unknown>) {
  const entries: { method: ReasoningMethod; value: string }[] = [];
  if ("reasoning_effort" in body)
    entries.push({ method: "reasoning_effort", value: typeof body.reasoning_effort === "string" ? body.reasoning_effort : "custom" });
  if ("thinking" in body) {
    const type = object(body.thinking).type;
    entries.push({ method: "thinking", value: type === "disabled" ? "none" : type === "enabled" ? "enabled" : "custom" });
  }
  if ("enable_thinking" in body)
    entries.push({ method: "enable_thinking", value: body.enable_thinking === false ? "none" : body.enable_thinking === true ? "enabled" : "custom" });
  const template = object(body.chat_template_kwargs);
  if ("enable_thinking" in template)
    entries.push({ method: "chat_template_kwargs", value: template.enable_thinking === false ? "none" : template.enable_thinking === true ? "enabled" : "custom" });
  return { method: entries[0]?.method, value: entries.length > 1 ? "custom" : entries[0]?.value || "" };
}

export function inferReasoningMethod(model: string, baseUrl: string): ReasoningMethod {
  let host = "";
  try { host = new URL(baseUrl).hostname.toLowerCase(); } catch { /* A URL draft may be incomplete. */ }
  if (/deepseek|^glm-/i.test(model) || /(^|\.)deepseek\.com$|(^|\.)bigmodel\.cn$/.test(host)) return "thinking";
  if (/dashscope|siliconflow/.test(host)) return "enable_thinking";
  return "reasoning_effort";
}

export function writeEndpointReasoning(text: string, method: ReasoningMethod, value: string): string {
  const original = parseChatOptions(text);
  if (!original) throw new Error("Invalid chat parameter JSON");
  const body = { ...original };
  const template = { ...object(body.chat_template_kwargs) };
  const thinking = { ...object(body.thinking) };
  delete body.reasoning_effort;
  delete body.thinking;
  delete body.enable_thinking;
  delete template.enable_thinking;
  if (Object.keys(template).length) body.chat_template_kwargs = template;
  else delete body.chat_template_kwargs;
  if (value) {
    if (method === "reasoning_effort") body.reasoning_effort = value;
    else if (method === "thinking") body.thinking = value === "none" ? { type: "disabled" } : { ...thinking, type: "enabled" };
    else if (method === "enable_thinking") body.enable_thinking = value !== "none";
    else body.chat_template_kwargs = { ...template, enable_thinking: value !== "none" };
  }
  return Object.keys(body).length ? JSON.stringify(body) : "";
}
