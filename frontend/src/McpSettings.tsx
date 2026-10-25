import { useEffect, useId, useRef, useState } from "react";
import { Check, Copy, KeyRound, Link2, LoaderCircle, RefreshCw, ShieldCheck } from "lucide-react";
import { api, getToken, post } from "./api";
import { useText } from "./locale";
import { CapsuleButton } from "./ui/controls";
import "./mcp-settings.css";

type McpStatus = {
  enabled: boolean; configured: boolean; running: boolean; transport_ready: boolean;
  status: "disabled" | "ready" | "starting" | "unconfigured"; error: string;
  endpoint: string; token: string; client_config: Record<string, unknown>; codex_config?: string;
  locked: { enabled: boolean; token: boolean }; last_request_at: number | null;
  probe?: { ok: boolean; server?: string; tools?: number; resources?: number; templates?: number; error?: string } | null;
};
type KarakeepStats = { documents: number; users: number; with_body: number };

export function McpSettings({ active = true }: { active?: boolean }) {
  const t = useText(), id = useId();
  const [status, setStatus] = useState<McpStatus | null>(null);
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false);
  const [error, setError] = useState(""), [copied, setCopied] = useState("");
  const [showToken, setShowToken] = useState(false), [resetting, setResetting] = useState(false);
  const [karakeep, setKarakeep] = useState<KarakeepStats | null>(null), [karakeepError, setKarakeepError] = useState("");
  const revision = useRef(0), gate = useRef(false), abort = useRef<AbortController | null>(null);

  async function load(signal?: AbortSignal) {
    if (gate.current) return;
    const current = ++revision.current;
    try {
      const next = await api<McpStatus>("/admin/mcp", { signal });
      if (current === revision.current && !signal?.aborted) { setStatus(next); setError(""); }
    } catch (failure) {
      if (current === revision.current && !signal?.aborted) setError(String(failure));
    } finally {
      if (current === revision.current && !signal?.aborted) setLoading(false);
    }
  }
  async function loadKarakeep(signal?: AbortSignal) {
    try {
      const next = await api<KarakeepStats>("/karakeep/stats", { signal });
      if (!signal?.aborted) { setKarakeep(next); setKarakeepError(""); }
    } catch (failure) {
      if (!signal?.aborted) setKarakeepError(String(failure));
    }
  }
  useEffect(() => {
    if (!active) return;
    const request = new AbortController(); abort.current = request;
    void load(request.signal); void loadKarakeep(request.signal);
    const timer = setInterval(() => { void load(request.signal); }, 5000);
    return () => { request.abort(); clearInterval(timer); };
  }, [active]);
  useEffect(() => () => abort.current?.abort(), []);

  async function change(values: { enabled?: boolean; rotate_token?: boolean; probe?: boolean }) {
    if (gate.current) return;
    gate.current = true; const current = ++revision.current;
    setBusy(true); setError(""); setCopied("");
    try {
      const next = await post<McpStatus>("/admin/mcp", values);
      if (current === revision.current) { setStatus(next); setResetting(false); }
    } catch (failure) {
      if (current === revision.current) setError(String(failure));
    } finally { gate.current = false; setBusy(false); }
  }
  async function copy(value: string, message: string) {
    try { await navigator.clipboard.writeText(value); setCopied(message); }
    catch { setCopied(t("无法复制，请在文本框中选择并复制。", "Copy unavailable. Select and copy the text in its field.")); }
  }
  let serviceOrigin = location.origin;
  try { if (status?.endpoint) serviceOrigin = new URL(status.endpoint).origin; } catch { /* Keep the actual page origin while loading. */ }
  const config = status ? JSON.stringify(status.client_config, null, 2) : "";
  const running = Boolean(status?.enabled && status.running && status.transport_ready);
  const lastRequest = status?.last_request_at ? new Date(status.last_request_at * 1000).toLocaleString(t("zh-CN", "en-US")) : "";

  return <div className="mcp-integrations">
    <section className="mcp-settings" aria-labelledby="mcp-settings-heading">
      <header className="mcp-heading">
        <div><h2 id="mcp-settings-heading"><Link2 size={22}/>{t("让 AI 使用你的收藏", "Connect your collection to AI")}</h2>
          <p>{t("通过 MCP，在支持的 AI 客户端中检索、阅读和保存收藏。桌面应用运行时即可使用，无需另装 Python。",
            "Use MCP to search, read and save bookmarks in a compatible AI client. Keep the desktop app running; no separate Python installation is needed.")}</p></div>
        <span className={`mcp-service-status ${running ? "is-ready" : ""}`} role="status">
          {loading ? t("正在读取状态…", "Loading status…") : !status ? t("状态无法读取", "Status unavailable")
            : !status.enabled ? t("MCP 已停用", "MCP disabled") : running ? t("MCP 服务已启动", "MCP service running")
              : status.status === "unconfigured" ? t("尚未配置令牌", "Token not configured") : t("服务尚未就绪", "Service not ready")}
        </span>
      </header>
      <div className="mcp-actions">
        <CapsuleButton type="button" className={status?.enabled ? "secondary" : "primary"}
          disabled={!status || busy || status.locked.enabled} onClick={() => change({ enabled: !status?.enabled })}>
          {busy ? <LoaderCircle size={16} className="spin"/> : <Link2 size={16}/>}
          {status?.enabled ? t("停用 MCP", "Disable MCP") : t("开启 MCP", "Enable MCP")}
        </CapsuleButton>
        <CapsuleButton type="button" className="secondary" disabled={!running || busy} onClick={() => change({ probe: true })}>
          <ShieldCheck size={16}/>{t("检查接入", "Test connection")}
        </CapsuleButton>
        <CapsuleButton type="button" className="text-button" disabled={busy} onClick={() => load()}>
          <RefreshCw size={15}/>{t("刷新状态", "Refresh status")}
        </CapsuleButton>
      </div>
      {status?.locked.enabled && <p className="mcp-note">{t("MCP 开关由运行环境配置控制。", "The MCP switch is controlled by environment configuration.")}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {status?.error && <p className="error" role="alert">{status.error}</p>}
      {status?.probe && <div className={`mcp-probe ${status.probe.ok ? "is-ready" : "has-error"}`} role={status.probe.ok ? "status" : "alert"}>
        {status.probe.ok ? <><Check size={17}/><span>{t("协议自检通过", "Protocol self-check passed")}
          {` · ${status.probe.tools ?? 0} `}{t("个工具", "tools")}{` · ${status.probe.resources ?? 0} `}{t("个资源", "resources")}
          {Boolean(status.probe.templates) && <>{` · ${status.probe.templates} `}{t("个资源模板", "resource templates")}</>}</span></>
          : <span>{status.probe.error || t("协议自检未通过，请刷新状态后重试。", "Protocol self-check failed. Refresh status and try again.")}</span>}
      </div>}
      <p className="mcp-note">{t("服务状态与协议自检不代表外部 AI 已连接。", "Service status and a protocol self-check do not establish an external AI connection.")}
        {lastRequest ? t("最近 MCP 请求：", " Last MCP request: ") + lastRequest : t("尚无 MCP 请求记录。", " No MCP requests recorded.")}</p>
      {status && <div className="mcp-connection-fields">
        <div className="mcp-field"><label htmlFor={id + "-url"}>{t("MCP 地址", "MCP URL")}</label>
          <div className="mcp-copy-field"><input id={id + "-url"} value={status.endpoint} readOnly aria-label={t("MCP 地址", "MCP URL")}/>
            <CapsuleButton type="button" className="secondary" onClick={() => copy(status.endpoint, t("MCP 地址已复制", "MCP URL copied"))}>
              <Copy size={15}/>{t("复制地址", "Copy URL")}</CapsuleButton></div>
        </div>
        <div className="mcp-field"><label htmlFor={id + "-token"}>{t("独立访问令牌", "Separate access token")}</label>
          <div className="mcp-copy-field"><input id={id + "-token"} type={showToken ? "text" : "password"} value={status.token} readOnly autoComplete="off"
            aria-label={t("MCP 访问令牌", "MCP access token")}/>
            <CapsuleButton type="button" className="secondary" disabled={!status.configured} onClick={() => copy(status.token, t("MCP 令牌已复制", "MCP token copied"))}>
              <Copy size={15}/>{t("复制令牌", "Copy token")}</CapsuleButton></div>
        </div>
        <div className="mcp-token-actions">
          <CapsuleButton type="button" className="text-button" disabled={!status.configured} aria-pressed={showToken} onClick={() => setShowToken(!showToken)}>
            {showToken ? t("隐藏令牌", "Hide token") : t("显示令牌", "Show token")}</CapsuleButton>
          <CapsuleButton type="button" className="text-button" disabled={busy || status.locked.token} onClick={() => setResetting(!resetting)}>
            <KeyRound size={15}/>{t("重置令牌", "Reset token")}</CapsuleButton>
        </div>
        {resetting && <div className="mcp-token-reset" role="group" aria-label={t("重置 MCP 令牌", "Reset MCP token")}>
          <p>{t("重置后，已连接的客户端需要更新令牌。", "Connected clients must update their token after a reset.")}</p>
          <CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => change({ rotate_token: true })}>{t("确认重置", "Confirm reset")}</CapsuleButton>
          <CapsuleButton type="button" className="text-button" disabled={busy} onClick={() => setResetting(false)}>{t("取消", "Cancel")}</CapsuleButton>
        </div>}
        <label className="mcp-field"><span>{t("AI 客户端配置", "AI client configuration")}</span>
          <textarea value={config} readOnly rows={7} aria-label={t("MCP 客户端配置", "MCP client configuration")} spellCheck={false}/>
        </label>
        <CapsuleButton type="button" className="secondary mcp-copy-config" disabled={!status.configured} onClick={() => copy(config, t("客户端配置已复制", "Client configuration copied"))}>
          <Copy size={16}/>{t("复制客户端配置", "Copy client configuration")}</CapsuleButton>
        {status.codex_config && <details className="mcp-codex-config">
          <summary>{t("Codex 配置", "Codex configuration")}</summary>
          <label className="mcp-field"><span>{t("添加到 Codex config.toml", "Add to Codex config.toml")}</span>
            <textarea value={status.codex_config} readOnly rows={4} aria-label={t("Codex MCP 配置", "Codex MCP configuration")} spellCheck={false}/>
          </label>
          <CapsuleButton type="button" className="secondary" disabled={!status.configured}
            onClick={() => copy(status.codex_config || "", t("Codex 配置已复制", "Codex configuration copied"))}>
            <Copy size={16}/>{t("复制 Codex 配置", "Copy Codex configuration")}</CapsuleButton>
        </details>}
      </div>}
      <p className="mcp-note">{t("将地址、令牌或完整配置加入 AI 客户端的 MCP 设置，再在客户端连接。命令行的 facetmark mcp 仍支持 stdio。",
        "Add the URL and token, or the full configuration, to your AI client's MCP settings and connect there. The facetmark mcp command continues to support stdio.")}</p>
      <p className="mcp-copy-status" role="status">{copied}</p>
    </section>
    <section className="mcp-karakeep" aria-labelledby="karakeep-settings-heading">
      <h3 id="karakeep-settings-heading">{t("Karakeep 搜索接入", "Karakeep search integration")}</h3>
      <p>{t("原有 Karakeep 搜索接口随桌面服务保留。插件配置使用这台设备的服务地址与普通配对令牌。",
        "The existing Karakeep search API runs with the desktop service. Configure its plugin with this device's service URL and regular pairing token.")}</p>
      {karakeep && <p className="mcp-karakeep-stats" role="status">{t(`已接收 ${karakeep.documents} 条收藏 · ${karakeep.with_body} 条有正文`,
        `${karakeep.documents} bookmarks received · ${karakeep.with_body} with page text`)}</p>}
      {karakeepError && <p className="error" role="alert">{karakeepError}</p>}
      <div className="mcp-field"><label htmlFor={id + "-karakeep"}>{t("服务地址 · FACETMARK_URL", "Service URL · FACETMARK_URL")}</label>
        <div className="mcp-copy-field"><input id={id + "-karakeep"} readOnly value={serviceOrigin} aria-label={t("Karakeep 服务地址", "Karakeep service URL")}/>
          <CapsuleButton type="button" className="secondary" onClick={() => copy(serviceOrigin, t("服务地址已复制", "Service URL copied"))}><Copy size={15}/>{t("复制地址", "Copy URL")}</CapsuleButton></div>
      </div>
      <div className="mcp-actions">
        <CapsuleButton type="button" className="secondary" onClick={() => copy(getToken(), t("配对令牌已复制", "Pairing token copied"))}><Copy size={15}/>{t("复制配对令牌", "Copy pairing token")}</CapsuleButton>
        <CapsuleButton type="button" className="text-button" onClick={() => loadKarakeep()}><RefreshCw size={15}/>{t("刷新接入统计", "Refresh integration stats")}</CapsuleButton>
        <a href="https://github.com/88lin/facetmark/blob/main/docs/karakeep.md" target="_blank" rel="noreferrer">{t("插件配置说明", "Plugin setup instructions")}</a>
      </div>
    </section>
  </div>;
}
