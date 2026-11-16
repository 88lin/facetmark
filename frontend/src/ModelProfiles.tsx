import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown, LoaderCircle, Pencil, Plus, RotateCcw, Save, Trash2, X } from "lucide-react";
import { api, ApiError, post, type Setting } from "./api";
import { useText } from "./locale";
import { CapsuleButton } from "./ui/controls";
import "./model-profiles.css";

export type ModelProfile = {
  id: string; name: string; channel: "chat" | "embed"; backend: string; model: string; agent: string;
  base_url: string; key_set: boolean; configured: boolean; tested: boolean; current: boolean; updated_at: number;
};
export type AppliedProfile = { profile: ModelProfile; settings: Setting[]; restart_required: string[] };

export function ModelProfiles({ channel, values, revision, hasDraft, disabled, run, onApplied }: {
  channel: "chat" | "embed"; values: Record<string, unknown>; revision: string; hasDraft: boolean; disabled: boolean;
  run: (name: string, work: () => Promise<void>) => Promise<void>;
  onApplied: (result: AppliedProfile) => Promise<void>;
}) {
  const t = useText(), id = useId();
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [removing, setRemoving] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const pending = useRef<{ signature: string; id: string } | null>(null);
  const mounted = useRef(true);
  const requestVersion = useRef(0);
  const [action, setAction] = useState("");
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const request = new AbortController(), version = ++requestVersion.current;
    setLoading(true); setError("");
    api<{ profiles: ModelProfile[] }>("/admin/model-profiles?channel=" + channel, { signal: request.signal })
      .then(result => {
        if (!Array.isArray(result.profiles)) throw new Error(t("未收到有效的已保存连接列表。", "Saved connections returned an invalid list."));
        if (!request.signal.aborted && version === requestVersion.current) setProfiles(result.profiles);
      })
      .catch(failure => { if (!request.signal.aborted && version === requestVersion.current) setError(String(failure)); })
      .finally(() => { if (!request.signal.aborted && version === requestVersion.current) setLoading(false); });
    return () => request.abort();
  }, [channel, revision, reload]);

  const locked = disabled || loading || Boolean(action);
  async function act(operation: string, work: () => Promise<void>) {
    await run(`profile-${channel}-${operation}`, async () => {
      setAction(operation); setError(""); setNotice("");
      try { await work(); }
      catch (failure) { if (mounted.current) setError(String(failure)); }
      finally { if (mounted.current) setAction(""); }
    });
  }
  const keep = (profile: ModelProfile) => {
    requestVersion.current++;
    setLoading(false);
    setProfiles(previous => [...previous.filter(item => item.id !== profile.id), profile]);
  };
  async function create() {
    const label = name.trim();
    if (!label) return;
    const signature = JSON.stringify([label, values]);
    if (pending.current?.signature !== signature) pending.current = { signature, id: crypto.randomUUID() };
    const identity = pending.current.id;
    await act("create", async () => {
      const result = await post<{ profile: ModelProfile }>("/admin/model-profiles", { id: identity, name: label, channel, values });
      if (!mounted.current) return;
      keep(result.profile); setName(""); pending.current = null;
      setNotice(t(`已保存“${result.profile.name}”。当前使用的连接保持不变。`, `“${result.profile.name}” saved. Your current connection is unchanged.`));
    });
  }
  async function apply(profile: ModelProfile) {
    await act("apply-" + profile.id, async () => {
      const result = await post<AppliedProfile>(`/admin/model-profiles/${profile.id}/apply`, {});
      if (!mounted.current) return;
      setProfiles(previous => previous.map(item => item.id === profile.id ? result.profile : { ...item, current: false }));
      setNotice(result.profile.tested
        ? t(`已使用“${profile.name}”，无需重复测试。`, `Using “${profile.name}”; no repeat test is needed.`)
        : t(`已使用“${profile.name}”。此连接还需测试。`, `Using “${profile.name}”. This connection still needs a test.`));
      await onApplied(result);
    });
  }
  async function rename(profile: ModelProfile) {
    const label = editName.trim();
    if (!label) return;
    await act("rename-" + profile.id, async () => {
      const result = await api<{ profile: ModelProfile }>(`/admin/model-profiles/${profile.id}`, {
        method: "PUT", body: JSON.stringify({ name: label }),
      });
      if (!mounted.current) return;
      keep(result.profile); setEditing(null);
      setNotice(t("连接名称已更新。", "Connection renamed."));
    });
  }
  async function remove(profile: ModelProfile) {
    await act("remove-" + profile.id, async () => {
      try { await api(`/admin/model-profiles/${profile.id}`, { method: "DELETE" }); }
      catch (failure) { if (!(failure instanceof ApiError && failure.status === 404)) throw failure; }
      if (!mounted.current) return;
      requestVersion.current++;
      setLoading(false);
      setProfiles(previous => previous.filter(item => item.id !== profile.id)); setRemoving(null);
      setNotice(t("命名连接已移除。当前使用的配置和收藏仍保留。", "Named connection removed. Your current settings and bookmarks are retained."));
    });
  }

  return <details className="model-profiles">
    <summary><span>{t("已保存连接", "Saved connections")}</span><span className="model-profile-count">{profiles.length}</span><ChevronDown size={16} aria-hidden="true"/></summary>
    <p className="model-profile-intro">{t("为不同模型或服务保存名称，之后直接切换。密钥只保存在本机，不会随书签导出或同步。", "Name connections for different models or services, then switch directly. Keys stay on this machine and are excluded from bookmark exports and sync.")}</p>
    <form className="model-profile-create" onSubmit={event => { event.preventDefault(); void create(); }}>
      <label htmlFor={`${id}-name`}>{t("连接名称", "Connection name")}</label>
      <input id={`${id}-name`} value={name} maxLength={80} required disabled={locked} autoComplete="off"
        placeholder={t("例如：日常摘要、本地模型", "For example: Daily summaries, Local model")}
        onChange={event => setName(event.currentTarget.value)}/>
      <CapsuleButton type="submit" className="secondary" disabled={locked || !name.trim()}>
        {action === "create" ? <LoaderCircle size={16} className="spin"/> : <Plus size={16}/>}{t("保存当前连接", "Save current connection")}
      </CapsuleButton>
    </form>
    {hasDraft && <p className="model-profile-draft" role="status">{t("将保存上方正在编辑的连接。使用已有连接会替换此通道未保存的修改。", "The connection edited above will be saved. Using a saved connection replaces unsaved edits in this channel.")}</p>}
    {loading && <p className="model-profile-loading" role="status"><LoaderCircle size={16} className="spin"/>{t("正在读取已保存连接…", "Loading saved connections…")}</p>}
    {!loading && !error && !profiles.length && <p className="model-profile-empty">{t("还没有命名连接。当前配置仍可直接使用。", "No named connections yet. Your current settings remain available.")}</p>}
    <ul className="model-profile-list" aria-label={t("已保存的模型连接", "Saved model connections")}>
      {profiles.map(profile => <li key={profile.id} className={profile.current ? "is-current" : ""}>
        {editing === profile.id ? <form className="model-profile-edit" onSubmit={event => { event.preventDefault(); void rename(profile); }}>
          <label className="sr-only" htmlFor={`${id}-${profile.id}`}>{t("新连接名称", "New connection name")}</label>
          <input id={`${id}-${profile.id}`} value={editName} maxLength={80} required autoFocus disabled={locked}
            onChange={event => setEditName(event.currentTarget.value)}
            onKeyDown={event => { if (event.key === "Escape" && !locked) { event.preventDefault(); setEditing(null); } }}/>
          <CapsuleButton type="submit" className="secondary" disabled={locked || !editName.trim()} aria-label={t("保存连接名称", "Save connection name")}><Save size={16}/></CapsuleButton>
          <CapsuleButton type="button" className="text-button" disabled={locked} onClick={() => setEditing(null)} aria-label={t("取消重命名", "Cancel rename")}><X size={16}/></CapsuleButton>
        </form> : <>
          <div className="model-profile-info"><strong>{profile.name}</strong><span>{profile.model || t("Agent 默认模型", "Agent default model")}
            {profile.backend === "agent" ? ` · ${profile.agent}` : profile.backend === "local" ? t(" · 本地模型", " · Local model") : ""}</span>
            {profile.base_url && <span className="model-profile-endpoint">{profile.base_url}</span>}
            <span className="model-profile-status">{profile.current && <span><Check size={13} aria-hidden="true"/>{t("当前配置", "Current settings")}</span>}
              {profile.tested ? t("已验证", "Verified") : t("未验证", "Needs test")}</span>
          </div>
          <div className="model-profile-actions">
            <CapsuleButton type="button" className="secondary" disabled={locked || (profile.current && !hasDraft)} onClick={() => void apply(profile)} aria-label={t(`使用连接：${profile.name}`, `Use connection: ${profile.name}`)}>
              {action === "apply-" + profile.id ? <LoaderCircle size={15} className="spin"/> : <Check size={15}/>}<span>{t("使用", "Use")}</span>
            </CapsuleButton>
            <CapsuleButton type="button" className="text-button" disabled={locked} onClick={() => { setEditName(profile.name); setEditing(profile.id); setRemoving(null); }} aria-label={t(`重命名连接：${profile.name}`, `Rename connection: ${profile.name}`)}><Pencil size={15}/></CapsuleButton>
            <CapsuleButton type="button" className="text-button" disabled={locked} onClick={() => { setRemoving(profile.id); setEditing(null); }} aria-label={t(`移除连接：${profile.name}`, `Remove connection: ${profile.name}`)}><Trash2 size={15}/></CapsuleButton>
          </div>
        </>}
        {removing === profile.id && <div className="model-profile-confirm"><p>{t(`移除“${profile.name}”的命名记录？当前配置和收藏不会删除。`, `Remove the named record “${profile.name}”? Your current settings and bookmarks will be retained.`)}</p>
          <CapsuleButton type="button" className="danger" disabled={locked} onClick={() => void remove(profile)}>{t("确认移除连接", "Remove saved connection")}</CapsuleButton>
          <CapsuleButton type="button" className="secondary" disabled={locked} onClick={() => setRemoving(null)}>{t("取消", "Cancel")}</CapsuleButton>
        </div>}
      </li>)}
    </ul>
    {notice && <p className="model-profile-notice" role="status">{notice}</p>}
    {error && <div className="model-profile-error"><p role="alert">{error}</p>
      <CapsuleButton type="button" className="text-button" disabled={disabled || Boolean(action)} onClick={() => setReload(value => value + 1)}><RotateCcw size={15}/>{t("重新读取连接", "Reload connections")}</CapsuleButton>
    </div>}
  </details>;
}
