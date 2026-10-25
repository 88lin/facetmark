import { useId, useState, type FormEvent } from "react";
import { Gauge, LoaderCircle, RotateCcw, Save } from "lucide-react";
import type { Setting } from "./api";
import { useText } from "./locale";
import { CapsuleButton } from "./ui/controls";
import "./processing-preferences.css";

type ProcessingKey = "enrich_concurrency" | "agent_concurrency" | "chat_concurrency"
  | "fetch_concurrency" | "fetch_per_host_concurrency" | "fetch_per_host_min_interval"
  | "max_retries" | "model_requests_per_minute";
export type ProcessingValues = Partial<Record<ProcessingKey, number>>;
type ProcessingField = {
  key: ProcessingKey;
  group: "models" | "fetch" | "reliability";
  label: [string, string];
  hint: [string, string];
  minimum: number;
  maximum: number;
  defaultValue: number;
  integer: boolean;
};

const fields: ProcessingField[] = [
  { key: "enrich_concurrency", group: "models", label: ["摘要请求上限", "Summary request limit"],
    hint: ["生成摘要时可同时发送的模型请求数。", "Model requests that can run together when generating summaries."],
    minimum: 1, maximum: 64, defaultValue: 4, integer: true },
  { key: "chat_concurrency", group: "models", label: ["同时对话数量", "Concurrent conversations"],
    hint: ["可同时运行的 AI 对话数量，同一对话按顺序处理。", "AI conversations that can run together. Each conversation processes messages in order."],
    minimum: 1, maximum: 8, defaultValue: 2, integer: true },
  { key: "agent_concurrency", group: "models", label: ["Agent 进程上限", "Agent process limit"],
    hint: ["同一本机 Agent 的共享进程上限，摘要和对话合计遵守。", "Shared process cap for the same local agent, across summaries and conversations."],
    minimum: 1, maximum: 8, defaultValue: 2, integer: true },
  { key: "fetch_concurrency", group: "fetch", label: ["抓取请求上限", "Fetch request limit"],
    hint: ["采集网页正文时，所有站点合计的请求上限。", "Total requests across all sites when collecting page text."],
    minimum: 1, maximum: 64, defaultValue: 30, integer: true },
  { key: "fetch_per_host_concurrency", group: "fetch", label: ["同站点请求上限", "Requests per host"],
    hint: ["一个站点可同时收到的请求数，也受抓取总上限约束。", "Requests that can run together for one host, within the total fetch limit."],
    minimum: 1, maximum: 16, defaultValue: 2, integer: true },
  { key: "fetch_per_host_min_interval", group: "fetch", label: ["同站点请求间隔（秒）", "Host request interval (seconds)"],
    hint: ["同一站点连续发起请求的最短间隔。", "Minimum interval between starting requests to the same host."],
    minimum: 0, maximum: 60, defaultValue: 0.5, integer: false },
  { key: "model_requests_per_minute", group: "reliability", label: ["每分钟请求上限", "HTTP requests per minute"],
    hint: ["仅 HTTP 模型接口，0 表示不限；同一接口与账号的请求共享限速，重试也计入。", "HTTP model APIs only. Zero means unlimited; the same endpoint and account share this limit, including retries."],
    minimum: 0, maximum: 6000, defaultValue: 0, integer: true },
  { key: "max_retries", group: "reliability", label: ["最大尝试次数", "Maximum attempts"],
    hint: ["HTTP 模型请求的总尝试次数，包含首次请求。设为 1 时只尝试一次。", "Total attempts for an HTTP model request, including the first. Set to 1 for a single attempt."],
    minimum: 1, maximum: 10, defaultValue: 3, integer: true },
];

function numeric(value: unknown): number | null {
  if (typeof value !== "number" && typeof value !== "string") return null;
  if (typeof value === "string" && !value.trim()) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function bounded(value: unknown, field: ProcessingField): number | null {
  const number = numeric(value);
  return number !== null && number >= field.minimum && number <= field.maximum
    && (!field.integer || Number.isInteger(number)) ? number : null;
}

export function ProcessingPreferences({ settings, disabled = false, onSave }: {
  settings: Setting[];
  disabled?: boolean;
  onSave: (values: ProcessingValues) => Promise<void>;
}) {
  const t = useText(), id = useId();
  const [draft, setDraft] = useState<Partial<Record<ProcessingKey, string>>>({});
  const [saving, setSaving] = useState(false), [error, setError] = useState(""), [notice, setNotice] = useState("");
  const row = (key: string) => settings.find(setting => setting.key === key);
  const saved = (key: ProcessingKey) => numeric(row(key)?.value);
  const value = (field: ProcessingField) => draft[field.key] ?? String(row(field.key)?.value ?? "");
  const dirty = fields.filter(field => field.key in draft
    && (bounded(draft[field.key], field) === null || numeric(draft[field.key]) !== saved(field.key)));
  const invalid = dirty.some(field => bounded(draft[field.key], field) === null || !row(field.key) || row(field.key)?.locked);
  const backend = row("chat_backend")?.value;
  const agent = saved("agent_concurrency"), summaries = saved("enrich_concurrency"), chats = saved("chat_concurrency");
  const fetches = saved("fetch_concurrency"), host = saved("fetch_per_host_concurrency"), interval = saved("fetch_per_host_min_interval");
  const rate = saved("model_requests_per_minute"), attempts = saved("max_retries");
  const effective = (limit: number | null) => backend === "agent"
    ? limit !== null && agent !== null ? Math.min(limit, agent) : null
    : backend === "endpoint" ? limit : null;
  const count = (number: number | null, zh: string, en: string) => number === null ? "—" : `${number} ${t(zh, en)}`;

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || disabled || !dirty.length || invalid) return;
    const values: ProcessingValues = {};
    for (const field of dirty) {
      const number = bounded(draft[field.key], field);
      if (number === null) return;
      values[field.key] = number;
    }
    setSaving(true); setError(""); setNotice("");
    try {
      await onSave(values);
      setDraft({});
      setNotice(t("处理设置已保存，用于之后启动的任务。", "Processing limits saved for tasks started from now on."));
    } catch (e) {
      setError(t("处理设置未保存，请重试。", "Processing limits were not saved. Please retry.") + " " + String(e));
    } finally { setSaving(false); }
  }

  const renderFields = (group: ProcessingField["group"]) => <div className="processing-fields">
    {fields.filter(field => field.group === group).map(field => {
      const setting = row(field.key), inputId = `${id}-${field.key}`;
      const fieldInvalid = field.key in draft && bounded(draft[field.key], field) === null;
      return <div className="processing-field" key={field.key}>
        <label htmlFor={inputId}>{t(...field.label)}
          {setting?.locked && <span className="processing-lock">{t("环境变量控制", "Environment controlled")}</span>}
        </label>
        <input id={inputId} name={field.key} type="number" min={field.minimum} max={field.maximum}
          step={field.integer ? 1 : "any"} inputMode={field.integer ? "numeric" : "decimal"}
          value={value(field)} required autoComplete="off"
          disabled={disabled || saving || !setting || setting.locked}
          aria-invalid={fieldInvalid || undefined}
          aria-describedby={`${inputId}-hint ${inputId}-range${fieldInvalid ? ` ${inputId}-error` : ""}`}
          onChange={event => {
            const next = event.currentTarget.value;
            setDraft(current => ({ ...current, [field.key]: next })); setNotice(""); setError("");
          }}/>
        <p id={`${inputId}-hint`}>{t(...field.hint)}</p>
        <span className="processing-range" id={`${inputId}-range`}>{setting
          ? t(`${field.minimum}–${field.maximum}${field.integer ? "，整数" : " 秒"} · 默认 ${field.defaultValue}`,
            `${field.minimum}–${field.maximum}${field.integer ? ", whole numbers" : " seconds"} · default ${field.defaultValue}`)
          : t("此服务版本尚未提供该设置。", "This service version does not expose this setting.")}</span>
        {fieldInvalid && <span className="processing-field-error" id={`${inputId}-error`}>{field.integer
          ? t(`请输入 ${field.minimum}–${field.maximum} 的整数。`, `Enter a whole number from ${field.minimum} to ${field.maximum}.`)
          : t(`请输入 ${field.minimum}–${field.maximum} 秒。`, `Enter a value from ${field.minimum} to ${field.maximum} seconds.`)}</span>}
      </div>;
    })}
  </div>;

  return <section className="processing-preferences" aria-labelledby={id}>
    <div className="processing-heading">
      <div>
        <h3 id={id}><Gauge size={18} aria-hidden="true"/>{t("处理速度与并发", "Processing speed and concurrency")}</h3>
        <p>{t("分别控制模型请求、对话数量和网页抓取。保存后用于之后启动的任务。",
          "Control model requests, conversations and page fetching separately. Saved limits apply to future tasks.")}</p>
      </div>
      <span className="processing-source">{backend === "agent" ? t("已保存 · 本机 Agent", "Saved · local agent")
        : backend === "endpoint" ? t("已保存 · API 接入", "Saved · API provider") : t("接入方式未读取", "Provider not loaded")}</span>
    </div>
    <div className="processing-effective">
      <p className="processing-effective-heading">{t("当前已保存的上限", "Current saved limits")}</p>
      <dl>
        <div className="processing-effective-summary"><dt>{t("摘要任务", "Summaries")}</dt><dd>{count(effective(summaries), "个并发请求", "concurrent requests")}</dd></div>
        <div className="processing-effective-chat"><dt>{t("AI 对话", "AI conversations")}</dt><dd>{count(effective(chats), "个同时对话", "concurrent conversations")}</dd></div>
        <div className="processing-effective-agent"><dt>{t("本机 Agent", "Local agent")}</dt><dd>{count(agent, "个进程", "processes")}</dd></div>
        <div className="processing-effective-fetch"><dt>{t("正文抓取", "Page fetching")}</dt><dd>{count(fetches, "个并发请求", "concurrent requests")}</dd></div>
      </dl>
      <p>{backend === "agent" ? t("本机 Agent 模式下，摘要与对话都受 Agent 进程上限约束。",
        "With a local agent, both summaries and conversations are constrained by the agent process limit.")
        : backend === "endpoint" ? t("API 接入时，摘要请求和同时对话数量分别生效；进程上限用于本机 Agent。",
          "With an API provider, summary requests and conversation limits apply separately. The process limit applies to local agents.")
          : t("读取已保存的接入方式后显示模型处理上限。", "Model limits are shown after the saved provider is loaded.")}</p>
      {fetches !== null && host !== null && interval !== null && <p className="processing-host-limit">{t(
        `单个站点最多 ${Math.min(fetches, host)} 个请求，启动间隔至少 ${interval} 秒。`,
        `Each host allows up to ${Math.min(fetches, host)} requests, with at least ${interval} seconds between starts.`)}</p>}
    </div>
    <form onSubmit={save} aria-busy={saving}>
      {(["models", "fetch"] as const).map(group => <fieldset className="processing-group" key={group}>
        <legend>{group === "models" ? t("生成与对话", "Generation and conversations") : t("正文抓取", "Page fetching")}</legend>
        {renderFields(group)}
      </fieldset>)}
      <details className="processing-reliability">
        <summary>{t("限流与重试", "Rate limits and retries")}<span>{rate === null || attempts === null
          ? t("设置尚未读取", "Settings not loaded")
          : t(`${rate === 0 ? "不限速" : `${rate} 次/分钟`} · 最多 ${attempts} 次尝试`,
            `${rate === 0 ? "No request limit" : `${rate} requests/min`} · up to ${attempts} ${attempts === 1 ? "attempt" : "attempts"}`)}</span></summary>
        <div className="processing-reliability-content">
          {renderFields("reliability")}
          <p>{t("仅影响 HTTP 模型接口；本机 Agent 使用各自客户端的网络与重试策略。",
            "Applies to HTTP model APIs. Local agents use their clients' networking and retry policies.")}</p>
        </div>
      </details>
      <p className="processing-rate-note">{t("模型服务商的请求和令牌速率限制仍然适用。",
        "Your model provider's request and token rate limits still apply.")}</p>
      {error && <p className="processing-save-error" role="alert">{error}</p>}
      <div className="processing-footer">
        <p role="status">{notice || (dirty.length ? t("尚未保存", "Unsaved changes")
          : t("保存这些参数无需测试模型连接。", "These limits can be saved without testing model connections."))}</p>
        <div className="processing-actions">
          {dirty.length > 0 && <CapsuleButton type="button" className="text-button" disabled={disabled || saving}
            onClick={() => { setDraft({}); setError(""); setNotice(""); }}><RotateCcw size={14}/>{t("放弃处理修改", "Discard limit changes")}</CapsuleButton>}
          <CapsuleButton type="submit" className="secondary" disabled={disabled || saving || !dirty.length || invalid}>
            {saving ? <LoaderCircle size={15} className="spin"/> : <Save size={15}/>} {t("保存处理设置", "Save processing limits")}
          </CapsuleButton>
        </div>
      </div>
    </form>
  </section>;
}
