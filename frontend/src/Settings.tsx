import { useEffect, useState } from "react";
import {
  Check,
  Copy,
  ExternalLink,
  FlaskConical,
  LoaderCircle,
  MessageCircle,
  Network,
  Save,
} from "lucide-react";
import { api, getToken, post, type Probe, type Setting, type Setup } from "./api";
import { useText } from "./locale";

export function Models({ setup, refresh }: { setup: Setup | null; refresh: () => Promise<void> }) {
  const t = useText();
  const [rows, setRows] = useState<Setting[]>([]);
  const [draft, setDraft] = useState<Record<string, unknown>>({});
  const [results, setResults] = useState<Record<string, Probe>>({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [consent, setConsent] = useState(false);
  const hasDraft = Object.keys(draft).length > 0;
  const channelStatus = (channel: string) => {
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
  async function load() {
    const data = await api<{ settings: Setting[] }>("/admin/settings");
    setRows(data.settings);
  }
  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, []);
  const row = (key: string) => rows.find((r) => r.key === key);
  const value = (key: string) =>
    key in draft ? draft[key] : row(key)?.secret ? "" : (row(key)?.value ?? "");
  const change = (key: string, next: unknown) => {
    setDraft((d) => ({
      ...d,
      [key]: next,
      ...(key.endsWith("_allow_no_key") && next
        ? { [key.replace("_allow_no_key", "_api_key")]: "" }
        : {}),
    }));
    setNotice("");
    setResults({});
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
  async function test(channel: string) {
    await run(channel, async () => {
      const payload = Object.fromEntries(
        Object.entries(draft).filter(
          ([key]) => key.startsWith(`${channel}_`) || key === "local_embed_path",
        ),
      );
      const data = await post<Record<string, Probe>>("/admin/settings/test", {
        ...payload,
        channel,
      });
      setResults((r) => ({ ...r, [channel]: data[channel] }));
      await refresh();
    });
  }
  async function save() {
    await run("save", async () => {
      await api("/admin/settings", { method: "PUT", body: JSON.stringify({ values: draft }) });
      setDraft({});
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
        disabled={!!busy || row(key)?.locked}
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
  return (
    <section className="models">
      <div className="section-heading">
        <h2>{t("让两个模型各司其职", "Two models, two clear roles")}</h2>
        <p>
          {t(
            "聊天负责理解与摘要，向量负责语义检索。可以使用不同服务。",
            "Chat understands and summarizes. Embeddings power semantic search. Each can use a different service.",
          )}
        </p>
      </div>
      <div className="model-columns">
        {["chat", "embed"].map((channel) => (
          <section className="model-panel" key={channel}>
            <div className="model-fields">
              <header>
                <h3>
                  {channel === "chat" ? <MessageCircle size={20} /> : <Network size={20} />}
                  {channel === "chat"
                    ? t("聊天模型", "Chat model")
                    : t("向量模型", "Embedding model")}
                </h3>
                <span className="quiet">{channelStatus(channel)}</span>
              </header>
              {field(
                `${channel}_base_url`,
                t("服务地址", "Base URL"),
                "url",
                "https://api.openai.com/v1",
              )}
              {field(`${channel}_api_key`, "API Key", "password")}
              {field(`${channel}_model`, t("模型名称", "Model name"))}
              {channel === "embed" && field("embed_dim", t("向量维度", "Dimensions"), "number")}
            </div>
            <div className="model-test">
              <button className="secondary" disabled={!!busy} onClick={() => test(channel)}>
                {busy === channel ? <LoaderCircle className="spin" /> : <FlaskConical />}
                {t("测试连接", "Test connection")}
              </button>
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
            </div>
            <div className="model-options">
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
            </div>
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
