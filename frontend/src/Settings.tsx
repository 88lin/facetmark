import { useEffect, useRef, useState } from "react";
import {
  Check,
  Copy,
  ExternalLink,
  FlaskConical,
  LoaderCircle,
  MessageCircle,
  Network,
  RefreshCw,
  Save,
} from "lucide-react";
import { api, getToken, post, type Probe, type Setting, type Setup } from "./api";
import { useText } from "./locale";
import { ModelPicker } from "./ModelPicker";

type LocalAgent = { id: string; name: string; installed: boolean; path?: string | null };

export function Models({ setup, refresh, showHeading = true, onSummarize }: { setup: Setup | null; refresh: () => Promise<void>; showHeading?: boolean; onSummarize?: () => void }) {
  const t = useText();
  const [agents, setAgents] = useState<LocalAgent[]>([]);
  const [detecting, setDetecting] = useState(true);
  const [detectionError, setDetectionError] = useState("");
  const [rows, setRows] = useState<Setting[]>([]);
  const [draft, setDraft] = useState<Record<string, unknown>>({});
  const [results, setResults] = useState<Record<string, Probe>>({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [consent, setConsent] = useState(false);
  const [loadingSettings, setLoadingSettings] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [channelFeedback, setChannelFeedback] = useState<Record<string, { text: string; saved: boolean }>>({});
  const [testingAndSaving, setTestingAndSaving] = useState(false);
  const agentModels = useRef<Record<string, string>>({});
  const lastAgent = useRef<{ preference: string; id: string } | null>(null);
  const hasDraft = Object.keys(draft).length > 0;
  const channelStatus = (channel: string) => {
    if (busy === channel) return t("正在测试…", "Testing…");
    if (results[channel] && (!results[channel].ok || results[channel].dim_matches === false))
      return t("测试未通过", "Test failed");
    const dirty = Object.keys(draft).some(
      (key) => key.startsWith(`${channel}_`) || (channel === "embed" && key === "local_embed_path"),
    );
    if (dirty)
      return results[channel]?.ok && results[channel]?.dim_matches !== false
        ? t("草稿已测试 · 尚未保存", "Draft tested · not saved")
        : t("尚未保存 · 需测试", "Unsaved · needs test");
    return setup?.channels[channel]?.tested
      ? t("已测试", "Tested")
      : setup?.channels[channel]?.configured
        ? t("待测试", "Needs test")
        : t("未配置", "Not configured");
  };
  async function detect() {
    setDetecting(true);
    setDetectionError("");
    try {
      const found = await api<{ agents: LocalAgent[] }>("/admin/agents");
      setAgents(found.agents);
      return found.agents;
    } catch {
      setAgents([]);
      setDetectionError(t("暂时无法检测本机 Agent，请重新检测。", "Agent detection failed. Please retry."));
      return [];
    } finally {
      setDetecting(false);
    }
  }
  async function load(suggestAgent = false) {
    setLoadingSettings(true); setLoadError("");
    try {
      const data = await api<{ settings: Setting[]; channels: { chat: { configured: boolean } } }>("/admin/settings");
      setRows(data.settings);
      if (suggestAgent) {
        const found = await detect();
        if (!data.channels.chat.configured && found.some(a => a.installed)
          && data.settings.find(r => r.key === "chat_backend")?.value !== "agent"
          && !data.settings.find(r => r.key === "chat_backend")?.locked)
          setDraft(current => ({ chat_backend: "agent", ...current }));
      }
    } catch {
      setLoadError(t("未能读取已保存的设置，请重试。", "Saved settings could not be loaded. Please retry."));
    } finally { setLoadingSettings(false); }
  }
  useEffect(() => {
    load(true).catch((e) => { setError(String(e)); setDetecting(false); });
  }, []);
  const row = (key: string) => rows.find((r) => r.key === key);
  const value = (key: string) =>
    key in draft ? draft[key] : row(key)?.secret ? "" : (row(key)?.value ?? "");
  const agentPreference = String(value("chat_agent") || "auto");
  const selectedAgent = agentPreference === "auto" ? agents.find(a => a.installed) : agents.find(a => a.id === agentPreference && a.installed);
  const agentUnavailable = value("chat_backend") === "agent" && (detecting || !selectedAgent || !!detectionError);
  useEffect(() => {
    // A failed discovery has not established a new agent identity. Keep the
    // last known identity and any manual draft until detection succeeds.
    if (detecting || detectionError || !selectedAgent) return;
    const id = selectedAgent.id;
    const previous = lastAgent.current;
    lastAgent.current = { preference: agentPreference, id };
    if (previous?.preference === "auto" && agentPreference === "auto" && previous.id !== id) {
      if (previous.id) agentModels.current[previous.id] = String(value("chat_agent_model"));
      if (!row("chat_agent_model")?.locked) setDraft(current => ({ ...current, chat_agent_model: agentModels.current[id] || "" }));
      setResults(current => Object.fromEntries(Object.entries(current).filter(([key]) => key !== "chat")));
      setChannelFeedback(current => Object.fromEntries(Object.entries(current).filter(([key]) => key !== "chat")));
    }
  }, [selectedAgent?.id, agentPreference, detecting, detectionError]);
  const change = (key: string, next: unknown) => {
    if (key === "chat_agent") agentModels.current[selectedAgent?.id || agentPreference] = String(value("chat_agent_model"));
    const nextAgent = next === "auto" ? agents.find(agent => agent.installed)?.id || "auto" : String(next);
    setDraft((d) => ({
      ...d,
      [key]: next,
      ...(key === "chat_agent" && !row("chat_agent_model")?.locked
        ? { chat_agent_model: agentModels.current[nextAgent] || "" } : {}),
      ...(key.endsWith("_allow_no_key") && next
        ? { [key.replace("_allow_no_key", "_api_key")]: "" }
        : {}),
    }));
    setNotice("");
    setChannelFeedback(current => Object.fromEntries(Object.entries(current).filter(([channel]) => !key.startsWith(`${channel}_`))));
    setResults(current => Object.fromEntries(Object.entries(current).filter(([channel]) =>
      !key.startsWith(`${channel}_`) && !(channel === "embed" && key === "local_embed_path"))));
    setConsent(false);
  };
  async function run(name: string, work: () => Promise<void>) {
    setBusy(name);
    setError("");
    setNotice("");
    try {
      await work();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy("");
    }
  }
  async function test(channel: string, saveAfter = false) {
    setTestingAndSaving(saveAfter);
    setChannelFeedback(current => Object.fromEntries(Object.entries(current).filter(([key]) => key !== channel)));
    await run(channel, async () => {
      const payload = Object.fromEntries(
        Object.entries(draft).filter(
          ([key]) => key.startsWith(`${channel}_`) || (channel === "embed" && key === "local_embed_path"),
        ),
      );
      setResults(current => Object.fromEntries(Object.entries(current).filter(([key]) => key !== channel)));
      let data: Record<string, Probe>;
      try {
        if (channel === "chat" && value("chat_backend") === "agent") {
          const found = await detect();
          const actual = agentPreference === "auto" ? found.find(agent => agent.installed) : found.find(agent => agent.id === agentPreference && agent.installed);
          if (!actual || actual.id !== selectedAgent?.id || actual.path !== selectedAgent?.path)
            throw new Error(t("本机 Agent 已变化，请确认当前 Agent 和模型后重新测试。", "The detected agent changed. Check the current agent and model, then test again."));
        }
        data = await post<Record<string, Probe>>("/admin/settings/test", { ...payload, channel });
        if (!data[channel]) throw new Error(t("没有收到测试结果，请重试。", "No test result received. Please retry."));
      } catch (e) {
        setResults(current => ({ ...current, [channel]: { ok: false, model: "", error: String(e) } }));
        return;
      }
      setResults((r) => ({ ...r, [channel]: data[channel] }));
      if (saveAfter && data[channel]?.ok && data[channel]?.dim_matches !== false) {
        try {
          await api("/admin/settings", { method: "PUT", body: JSON.stringify({ values: payload }) });
        } catch (e) {
          setChannelFeedback(current => ({ ...current, [channel]: { saved: false, text: t("连接测试成功，但配置未保存。请重试。", "Connection passed, but settings were not saved. Please retry.") + " " + String(e) } }));
          return;
        }
        acknowledgeSaved(payload);
        await load();
        setChannelFeedback(current => ({ ...current, [channel]: { saved: true, text: channel === "chat"
          ? t("连接已验证并保存，可以开始生成摘要。", "Connection verified and saved. Ready to generate summaries.")
          : t("向量连接已验证并保存；如有配置变更，请继续应用向量配置。", "Embedding connection verified and saved. Apply any embedding configuration changes below.") } }));
      }
      await refresh();
    });
  }
  async function save() {
    await run("save", async () => {
      await api("/admin/settings", { method: "PUT", body: JSON.stringify({ values: draft }) });
      acknowledgeSaved(draft);
      await load();
      await refresh();
      setNotice(
        t(
          "已保存。连接测试与当前配置匹配后即可应用。",
          "Saved. Apply after the connection test matches these settings.",
        ),
      );
    });
  }
  function acknowledgeSaved(values: Record<string, unknown>) {
    setRows(current => current.map(item => item.key in values ? { ...item,
      value: item.secret ? "" : values[item.key], set: Boolean(values[item.key]), source: "file" } : item));
    setDraft(current => Object.fromEntries(Object.entries(current).filter(([key]) => !(key in values))));
  }
  const field = (key: string, label: string, type = "text", hint?: string) => (
    <label className="field" key={key}>
      <span>
        {label}
        {row(key)?.locked && <small>{t("环境变量控制", "Environment controlled")}</small>}
      </span>
      <input
        name={key}
        type={type}
        value={String(value(key))}
        disabled={!!busy || loadingSettings || !rows.length || row(key)?.locked}
        autoComplete={type === "password" ? "new-password" : "off"}
        spellCheck={false}
        placeholder={
          row(key)?.secret && row(key)?.set
            ? t("已保存 · 留空保留，输入替换", "Saved · leave untouched to keep")
            : hint
        }
        onChange={(e) => change(key, type === "number" ? Number(e.target.value) : e.target.value)}
      />
      {type === "password" && row(key)?.set && !row(key)?.locked && (
        <button
          className="text-button"
          disabled={!!busy}
          onClick={() => change(key, "")}
          type="button"
        >
          {t("清除已保存的密钥", "Clear saved key")}
        </button>
      )}
    </label>
  );
  const modelPicker = (channel: string, local = false) => {
    const key = local ? "chat_agent_model" : `${channel}_model`;
    const payload = { channel, ...Object.fromEntries(Object.entries(draft).filter(([key]) => key.startsWith(`${channel}_`))), ...(local ? { chat_agent: selectedAgent?.id || agentPreference } : {}) };
    const identity = local ? JSON.stringify([agentPreference, selectedAgent?.path, selectedAgent?.id, detecting])
      : JSON.stringify([value(`${channel}_base_url`), value(`${channel}_api_key`), value(`${channel}_allow_no_key`)]);
    return <ModelPicker key={local ? "agent" : channel} name={key} value={String(value(key))}
      onChange={next => change(key, next)} payload={payload} identity={identity}
      agent={local ? selectedAgent?.id || agentPreference : undefined} autoLoad={local && !agentUnavailable}
      disabled={!!busy || loadingSettings || !!row(key)?.locked}/>;
  };
  if (!rows.length) return <section className="models settings-loading" aria-busy={loadingSettings}>
    {loadingSettings ? <p role="status"><LoaderCircle className="spin" size={18}/>{t("正在读取连接设置…", "Loading connection settings…")}</p>
      : <><p className="error" role="alert">{loadError}</p><button className="secondary" onClick={() => load(true)}><RefreshCw size={16}/>{t("重新读取设置", "Reload settings")}</button></>}
  </section>;
  return (
    <section className="models">
      {showHeading && <div className="section-heading">
        <h2>{t("连接你已经在用的 AI", "Connect the AI you already use")}</h2>
        <p>
          {t(
            "摘要可直接使用本机已登录的 Agent，也可连接 API。向量模型仅用于可选的语义检索。",
            "Use an installed, signed-in agent or a chat API for summaries. Embeddings are optional and only needed for semantic search.",
          )}
        </p>
      </div>}
      {loadError && <div className="error" role="alert">{loadError}<button className="text-button" onClick={() => load()}>{t("重新读取设置", "Reload settings")}</button></div>}
      <div className="model-columns">
        {["chat", "embed"].map((channel) => (
          <section className={`model-panel model-${channel}`} key={channel}>
            <div className="model-intro">
              <header>
                <h3>
                  {channel === "chat" ? <MessageCircle size={20} /> : <Network size={20} />}
                  {channel === "chat"
                    ? t("阅读摘要", "Reading summaries")
                    : t("向量模型", "Embedding model")}
                </h3>
                <span className="quiet">{channelStatus(channel)}</span>
              </header>
              <p className="model-purpose">{channel === "chat"
                ? t("用于生成摘要与检索意图，选择一种接入方式即可。", "Generates summaries and search intents. Choose one provider below.")
                : t("可选 · 用于按含义查找。普通关键词搜索和摘要不需要向量模型。", "Optional · Find pages by meaning. Keyword search and summaries do not require embeddings.")}</p>
            </div>
            <div className="model-fields">
              {channel === "chat" && <label className="field">{t("摘要来源", "Summary provider")}
                <select aria-label={t("摘要来源", "Summary provider")} value={String(value("chat_backend") || "endpoint")}
                  disabled={!!busy || row("chat_backend")?.locked} onChange={e => change("chat_backend", e.target.value)}>
                  <option value="agent">{t("本机 Agent · 使用已有登录", "Local agent · existing sign-in")}</option>
                  <option value="endpoint">{t("API 服务", "API endpoint")}</option>
                </select>
              </label>}
              {channel === "chat" && value("chat_backend") === "agent" ? <>
                <label className="field">{t("选择 Agent", "Agent")}
                  <select aria-label={t("选择 Agent", "Agent")} value={String(value("chat_agent") || "auto")}
                    disabled={!!busy || row("chat_agent")?.locked} onChange={e => change("chat_agent", e.target.value)}>
                    <option value="auto">{selectedAgent && agentPreference === "auto" ? t(`自动选择 · ${selectedAgent.name}`, `Automatic · ${selectedAgent.name}`) : t("自动选择已检测到的 Agent", "Automatically select a detected agent")}</option>
                    {agents.map(a => <option key={a.id} value={a.id}>{a.name}{a.installed ? t(" · 已检测到", " · detected") : t(" · 未检测到", " · not detected")}</option>)}
                    {agentPreference !== "auto" && !agents.some(a => a.id === agentPreference) && <option value={agentPreference}>{agentPreference}</option>}
                  </select>
                </label>
                <div className="agent-discovery">
                  <p className="agent-detection" role="status">{detecting ? t("正在检测本机 Agent…", "Detecting local agents…") : detectionError || (selectedAgent
                    ? t(`将使用 ${selectedAgent.name}，连接状态以测试结果为准。`, `Will use ${selectedAgent.name}. Test the connection to verify access.`)
                    : agentPreference === "auto" ? t("未检测到 CLI。支持 Codex、Claude Code 和 OpenCode。安装并登录后重新检测。", "No CLI detected. Codex, Claude Code and OpenCode are supported. Install, sign in and retry detection.")
                    : t("未检测到所选 Agent，请安装后重试，或选择其他 Agent。", "Selected agent not detected. Install it or choose another agent."))}</p>
                  <button className="text-button" disabled={!!busy || detecting} onClick={async () => {
                    setResults(current => Object.fromEntries(Object.entries(current).filter(([key]) => key !== "chat")));
                    setChannelFeedback(current => Object.fromEntries(Object.entries(current).filter(([key]) => key !== "chat")));
                    await detect(); await refresh();
                  }}><RefreshCw size={14} className={detecting ? "spin" : ""}/>{t("重新检测", "Detect again")}</button>
                </div>
                {modelPicker("chat", true)}
              </> : <>
                {field(`${channel}_base_url`, t("服务地址", "Base URL"), "url", "https://api.openai.com/v1")}
                {field(`${channel}_api_key`, "API Key", "password")}
                {modelPicker(channel)}
                {channel === "embed" && field("embed_dim", t("向量维度", "Dimensions"), "number")}
              </>}
            </div>
            <div className="model-test">
              <button className="secondary" disabled={!!busy || !rows.length || (channel === "chat" && agentUnavailable)} onClick={() => test(channel)}>
                {busy === channel && !testingAndSaving ? <LoaderCircle className="spin" /> : <FlaskConical />}
                {t("测试连接", "Test connection")}
              </button>
              <button className="primary" disabled={!!busy || !rows.length || (channel === "chat" && agentUnavailable)} onClick={() => test(channel, true)}>{busy === channel && testingAndSaving ? <LoaderCircle size={16} className="spin"/> : <Check size={16}/>} {t("测试并保存", "Test and save")}</button>
              {results[channel] && (
                <div
                  role="status"
                  className={
                    results[channel].ok && results[channel].dim_matches !== false
                      ? "test-result"
                      : "error"
                  }
                >
                  {results[channel].ok ? (
                    <>
                      <Check size={16} />
                      {t("连接成功", "Connected")} · {results[channel].ms} ms
                      {channel === "chat" && <span className="tested-model">{results[channel].model}</span>}
                      {channel === "embed" && (
                        <>
                          {" "}
                          · {results[channel].dim} {t("维", "dimensions")}
                        </>
                      )}
                    </>
                  ) : (
                    results[channel].error
                  )}
                  {results[channel].dim_matches === false && !!results[channel].dim && (
                    <p>
                      {t(
                        "实测维度与配置不一致，请修改后重新测试。",
                        "Measured dimensions differ. Update the value and test again.",
                      )}{" "}
                      <button
                        className="text-button"
                        onClick={() => change("embed_dim", results[channel].dim)}
                      >
                        {t("采用实测维度", "Use measured dimensions")}
                      </button>
                    </p>
                  )}
                </div>
              )}
              {channelFeedback[channel] && <div className={channelFeedback[channel].saved ? "notice connection-feedback" : "error connection-feedback"} role={channelFeedback[channel].saved ? "status" : "alert"}>
                <p>{channelFeedback[channel].text}</p>
                {channel === "chat" && channelFeedback[channel].saved && onSummarize && <button type="button" className="text-button" onClick={onSummarize}>{t("前往生成摘要", "Start generating summaries")}</button>}
              </div>}
            </div>
            {channel === "chat" && value("chat_backend") === "agent" && <div className="model-options">
              <p className="hint">{t("使用已有登录，无需再填 Key。摘要会发送到所选 Agent 的模型服务。", "Uses your existing sign-in. Summaries are sent to the selected agent's model service.")}</p>
              <details className="agent-details">
                <summary>{t("超时与安装位置", "Timeout and installation paths")}</summary>
                {field("chat_agent_timeout", t("单次超时（秒）", "Request timeout (seconds)"), "number", "180")}
                <ul className="agent-paths">{agents.map(agent => <li key={agent.id}><strong>{agent.name}</strong><span>{agent.path || (agent.installed ? t("已检测到", "Detected") : t("未检测到", "Not detected"))}</span></li>)}</ul>
              </details>
            </div>}
            {!(channel === "chat" && value("chat_backend") === "agent") && <div className="model-options">
              <label className="check">
                <input
                  type="checkbox"
                  checked={Boolean(value(`${channel}_allow_no_key`))}
                  disabled={!!busy || row(`${channel}_allow_no_key`)?.locked}
                  onChange={(e) => change(`${channel}_allow_no_key`, e.target.checked)}
                />
                {t("连接本机服务，不使用 Key", "Use a local service without a key")}
              </label>
              <p className="hint">
                {t(
                  "免 Key 仅接受 localhost、127.0.0.1 或 ::1。Ollama 可用 http://127.0.0.1:11434/v1。",
                  "Keyless access only accepts localhost, 127.0.0.1 or ::1. Ollama: http://127.0.0.1:11434/v1.",
                )}
              </p>
              {channel === "embed" && (
                <label className="check">
                  <input
                    type="checkbox"
                    checked={Boolean(value("embed_send_dimensions"))}
                    disabled={!!busy || row("embed_send_dimensions")?.locked}
                    onChange={(e) => change("embed_send_dimensions", e.target.checked)}
                  />
                  {t("在请求中指定维度", "Send dimensions in requests")}
                </label>
              )}
            </div>}
          </section>
        ))}
      </div>
      <details className="advanced">
        <summary>
          {t("高级聊天参数与隐私排除", "Advanced chat options and privacy exclusions")}
        </summary>
        {field(
          "chat_extra_body",
          t("额外参数（JSON 对象）", "Extra chat parameters (JSON object)"),
        )}
        {field(
          "chat_model_fallbacks",
          t("备用聊天模型（逗号分隔）", "Fallback chat models (comma separated)"),
        )}
        {field(
          "privacy_excluded_domains",
          t(
            "不抓取、不发送给模型的站点（逗号分隔）",
            "Domains excluded from fetching and models (comma separated)",
          ),
        )}
      </details>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      <div className="form-actions">
        <button className="primary" disabled={!!busy || !Object.keys(draft).length} onClick={save}>
          <Save />
          {t("保存配置", "Save settings")}
        </button>
        {hasDraft && <button className="secondary" disabled={!!busy} onClick={() => { setDraft({}); setResults({}); setChannelFeedback({}); setError(""); setNotice(""); setConsent(false); agentModels.current = {}; }}>{t("放弃修改", "Discard changes")}</button>}
        <span className="hint">
          {t(
            "测试只发送固定测试句，不发送书签。",
            "Tests send fixed sample text, never your bookmarks.",
          )}
        </span>
      </div>
      {(setup?.pending_apply || setup?.vector_compatible === false) && (
        <section className="apply-panel">
          <h3>{t("应用向量配置", "Apply embedding settings")}</h3>
          {hasDraft && (
            <p className="hint">
              {t(
                "请先保存可见草稿，再测试并应用。",
                "Save the visible draft before testing and applying it.",
              )}
            </p>
          )}
          <p>
            {t(
              "如果向量空间发生变化，会先备份数据库，再清理旧向量。书签和原文会保留，之后需重新索引。",
              "If the vector space changes, the database is backed up before old vectors are cleared. Bookmarks and page text stay; indexing must run again.",
            )}
          </p>
          <label className="check">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            {t("我确认备份并在需要时重建向量", "I confirm backup and vector rebuild when needed")}
          </label>
          <button
            className="secondary"
            disabled={!!busy || hasDraft || !consent || !setup.channels.embed.tested}
            onClick={() =>
              run("apply", async () => {
                const result = await post<{ backup: string | null }>("/admin/settings/apply", {
                  confirm_rebuild: consent,
                });
                await refresh();
                await load();
                setNotice(
                  result.backup
                    ? `${t("备份已保存：", "Backup saved: ")}${result.backup}`
                    : t("配置已应用", "Settings applied"),
                );
              })
            }
          >
            {t("应用已测试的配置", "Apply tested settings")}
          </button>
        </section>
      )}
    </section>
  );
}

export function ExtensionSettings() {
  const t = useText();
  const [copied, setCopied] = useState("");
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    const refresh = () =>
      api<{ recently_connected: boolean }>("/admin/extension-status")
        .then((data) => setConnected(data.recently_connected))
        .catch(() => setConnected(false));
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, []);
  async function copy(value: string, name: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(name);
    } catch {
      setCopied(t("无法复制，请手动选择。", "Copy unavailable; select the text manually."));
    }
  }
  return (
    <section className="extension-settings">
      <h2>{t("连接浏览器扩展", "Connect the browser extension")}</h2>
      <p role="status">
        {connected
          ? t("扩展最近已连接此书库", "Extension recently connected to this library")
          : t(
              "尚未收到扩展连接。安装并配对后，在扩展中执行一次操作。",
              "No extension connection received. After installing and pairing, perform an action in the extension.",
            )}
      </p>
      <p>
        {t(
          "扩展帮助保存页面，并在你启用后读取需要浏览器的页面。请从测试产物下载扩展，在浏览器扩展管理页开启开发者模式并加载解压后的文件夹。",
          "The extension saves pages and, when enabled, reads pages that need a browser. Download it from the preview artifacts, enable developer mode in your browser and load the extracted folder.",
        )}
      </p>
      <a href="https://github.com/88lin/facetmark/actions" target="_blank" rel="noreferrer">
        {t("查看扩展下载与构建", "Extension downloads and builds")}
        <ExternalLink size={14} />
      </a>
      <div className="pairing-row">
        <code>{location.origin}</code>
        <button
          className="secondary"
          onClick={() => copy(location.origin, t("地址已复制", "URL copied"))}
        >
          <Copy />
          {t("复制地址", "Copy URL")}
        </button>
        <button
          className="secondary"
          onClick={() => copy(getToken(), t("配对令牌已复制", "Pairing token copied"))}
        >
          <Copy />
          {t("复制配对令牌", "Copy pairing token")}
        </button>
      </div>
      <p className="hint">
        {t(
          "将地址和令牌粘贴到扩展设置中，再点击连接。扩展需要手动安装；端口以这里显示的地址为准。",
          "Paste the URL and token into extension settings and connect. Installation is manual; use the current port shown here.",
        )}
      </p>
      <p role="status">{copied}</p>
    </section>
  );
}

export function UpdateSettings() {
  const t = useText();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  return (
    <section className="desktop-note">
      <h2>{t("桌面与更新", "Desktop and updates")}</h2>
      <p>
        {t(
          "开机启动、全局快捷键与退出位于系统托盘菜单。关闭窗口后任务继续运行。",
          "Launch at login, global shortcut and Quit are in the system tray menu. Tasks continue after the window closes.",
        )}
      </p>
      <p>
        {t(
          "预览安装包尚未签名，Windows 可能显示 SmartScreen 提示。更新由你下载和安装，不会自动替换应用。",
          "Preview installers are unsigned; Windows may show SmartScreen. You choose when to download and install an update.",
        )}
      </p>
      <div className="form-actions">
        <button
          className="secondary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              const data = await post<{
                current: string;
                latest: string | null;
                available: boolean;
              }>("/admin/updates/check", {});
              setMessage(
                data.latest
                  ? data.available
                    ? t(
                        `可用版本 ${data.latest}，当前 ${data.current}`,
                        `Version ${data.latest} available; current ${data.current}`,
                      )
                    : t(
                        `当前 ${data.current}，最新正式版本 ${data.latest}`,
                        `Current ${data.current}; latest release ${data.latest}`,
                      )
                  : t(
                      "尚无正式版本，请查看测试构建。",
                      "No stable release is available. See the preview builds.",
                    ),
              );
            } catch (e) {
              setMessage(String(e));
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? <LoaderCircle className="spin" /> : <ExternalLink />}
          {t("检查更新", "Check for updates")}
        </button>
        <a
          href="https://github.com/88lin/facetmark/actions/workflows/desktop.yml"
          target="_blank"
          rel="noreferrer"
        >
          {t("下载测试构建", "Download preview builds")}
          <ExternalLink size={14} />
        </a>
      </div>
      <p role="status">{message}</p>
    </section>
  );
}
