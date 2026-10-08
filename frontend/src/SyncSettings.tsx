import { useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowDownToLine, ArrowUpFromLine, Check, LoaderCircle, Pause, RefreshCw, Save } from "lucide-react";
import { api, ApiError, post } from "./api";
import { useText } from "./locale";
import "./sync-settings.css";

type SyncConfig = { folder: string; enabled: boolean; auto_sync: boolean; poll_seconds: number };
type SyncStatus = SyncConfig & {
  configured: boolean;
  last_sync_at: number | null;
  last_error: string;
  pending_conflicts: number;
  needs_review: boolean;
};
type Metadata = { url: string; title: string; folder: string; tags: string[]; date_added: number | null };
type Counts = {
  upload_new: number; upload_update: number; upload_delete: number;
  download_new: number; download_update: number; download_delete: number;
  unchanged: number; conflicts: number;
};
type Conflict = {
  id: string;
  reason: string;
  can_delete?: boolean;
  local: Metadata | null;
  remote: Metadata | null;
  remote_versions: { choice: string; record: Metadata | null }[];
};
type Change = {
  id: string;
  local: Metadata | null;
  remote: Metadata | null;
  target: Metadata | null;
  directions: ("upload" | "download")[];
};
type Preview = {
  preview_id: string;
  expires_at: number;
  counts: Counts;
  conflicts: Conflict[];
  changes: Change[];
  excluded_karakeep: number;
  excluded_unsupported: number;
};
type Applied = { counts: Counts; backup_path: string | null; status: SyncStatus };
type Draft = Omit<SyncConfig, "poll_seconds"> & { poll_seconds: string };

const endpoint = "/admin/library/sync";
const draftOf = (status: SyncConfig): Draft => ({
  folder: status.folder, enabled: status.enabled, auto_sync: status.auto_sync,
  poll_seconds: String(status.poll_seconds),
});
const configOf = (status: SyncConfig): SyncConfig => ({
  folder: status.folder, enabled: status.enabled, auto_sync: status.auto_sync,
  poll_seconds: status.poll_seconds,
});

function MetadataView({ record }: { record: Metadata | null }) {
  const t = useText();
  if (!record) return <p className="sync-absent">{t("此版本没有这条书签。", "This version has no bookmark.")}</p>;
  const fields: [string, ReactNode][] = [
    [t("标题", "Title"), record.title || t("无标题", "Untitled")],
    [t("地址", "URL"), record.url],
    [t("文件夹", "Folder"), record.folder || t("未分类", "Unfiled")],
    [t("标签", "Tags"), record.tags.length ? <ul className="sync-tags">{record.tags.map((tag) => <li key={tag}>{tag}</li>)}</ul> : t("无标签", "No tags")],
    [t("收藏时间", "Saved"), record.date_added === null ? t("未记录", "Not recorded") : new Date(record.date_added * 1000).toLocaleString(t("zh-CN", "en-US"))],
  ];
  return <dl className="sync-metadata">{fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function CountTable({ counts }: { counts: Counts }) {
  const t = useText();
  return <div className="sync-counts">
    <table aria-label={t("同步预览数量", "Synchronization change counts")}>
      <thead><tr><th scope="col">{t("变更位置", "Destination")}</th><th scope="col">{t("新增", "New")}</th><th scope="col">{t("修改", "Updated")}</th><th scope="col">{t("删除", "Deleted")}</th></tr></thead>
      <tbody>
        <tr><th scope="row"><span><ArrowUpFromLine size={16} />{t("共享文件夹", "Shared folder")}</span></th><td>{counts.upload_new}</td><td>{counts.upload_update}</td><td>{counts.upload_delete}</td></tr>
        <tr><th scope="row"><span><ArrowDownToLine size={16} />{t("本机书签库", "This library")}</span></th><td>{counts.download_new}</td><td>{counts.download_update}</td><td>{counts.download_delete}</td></tr>
      </tbody>
    </table>
    <p className="hint">{counts.unchanged} {t("条保持不变", "unchanged")}{counts.conflicts > 0 && <> · {counts.conflicts} {t("条冲突尚未计入上表", "conflicts are excluded from this table")}</>}</p>
  </div>;
}

export function SyncSettings({ onChanged }: { onChanged: () => void | Promise<void> }) {
  const t = useText();
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [draft, setDraft] = useState<Draft>({ folder: "", enabled: false, auto_sync: false, poll_seconds: "60" });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [resolutions, setResolutions] = useState<Record<string, string>>({});
  const [confirmed, setConfirmed] = useState(false);
  const [expired, setExpired] = useState(false);
  const [applied, setApplied] = useState<Applied | null>(null);
  const statusRef = useRef<SyncStatus | null>(null);
  const busyRef = useRef(false);
  const statusGeneration = useRef(0);
  const changedRef = useRef(onChanged);
  changedRef.current = onChanged;

  function acceptStatus(next: SyncStatus) {
    statusRef.current = next;
    setStatus(next);
  }

  useEffect(() => {
    const controller = new AbortController();
    async function refresh(initial = false) {
      if (busyRef.current) return;
      const generation = statusGeneration.current;
      try {
        const next = await api<SyncStatus>(`${endpoint}/status`, { signal: controller.signal });
        if (controller.signal.aborted || generation !== statusGeneration.current) return;
        const previous = statusRef.current;
        acceptStatus(next);
        if (initial || !previous) setDraft(draftOf(next));
        if (previous && next.last_sync_at !== previous.last_sync_at) {
          clearPreview();
          await changedRef.current();
        }
      } catch (e) {
        if (!controller.signal.aborted && generation === statusGeneration.current) setError(String(e));
      } finally {
        if (!controller.signal.aborted && initial) setLoading(false);
      }
    }
    void refresh(true);
    const timer = window.setInterval(() => { void refresh(); }, 15000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, []);

  useEffect(() => {
    setExpired(false);
    if (!preview) return;
    const delay = Math.max(0, preview.expires_at * 1000 - Date.now());
    const timer = window.setTimeout(() => setExpired(true), delay);
    return () => window.clearTimeout(timer);
  }, [preview]);

  const dirty = !!status && JSON.stringify(draft) !== JSON.stringify(draftOf(status));
  const allResolved = !!preview && preview.conflicts.every((conflict) => !!resolutions[conflict.id]);
  const displayError = error || status?.last_error;

  function clearPreview() {
    setPreview(null);
    setResolutions({});
    setConfirmed(false);
  }

  async function run(action: string, work: () => Promise<void>) {
    if (busyRef.current) return;
    statusGeneration.current += 1;
    busyRef.current = true;
    setBusy(action);
    setError("");
    setNotice("");
    try { await work(); }
    catch (e) {
      if (e instanceof ApiError && e.status === 409) clearPreview();
      setError(e instanceof Error ? e.message : String(e));
    } finally { busyRef.current = false; setBusy(""); }
  }

  function change(values: Partial<Draft>) {
    setDraft((previous) => ({ ...previous, ...values }));
    clearPreview();
    setNotice("");
  }

  async function saveConfig() {
    await run("save", async () => {
      const seconds = Number(draft.poll_seconds);
      if (!Number.isInteger(seconds) || seconds < 30 || seconds > 3600) {
        throw new Error(t("检查间隔须为 30–3600 秒的整数。", "Choose a whole-number interval from 30 to 3600 seconds."));
      }
      if (draft.enabled && !draft.folder.trim()) throw new Error(t("请填写已有共享文件夹的完整路径。", "Enter the full path to an existing shared folder."));
      const next = await post<SyncStatus>(`${endpoint}/config`, {
        ...draft, folder: draft.folder.trim(), poll_seconds: seconds,
        auto_sync: draft.enabled && draft.auto_sync,
      });
      acceptStatus(next);
      setDraft(draftOf(next));
      clearPreview();
      setApplied(null);
      setNotice(next.enabled ? next.needs_review ? t("配置已保存。先预览并确认一次同步。", "Settings saved. Preview and confirm a sync first.") : t("同步设置已保存。", "Sync settings saved.") : t("同步已停用。书签和共享文件夹中的数据会保留。", "Sync is disabled. Bookmarks and shared-folder data are kept."));
    });
  }

  async function disableSync() {
    if (!status) return;
    await run("disable", async () => {
      const next = await post<SyncStatus>(`${endpoint}/config`, { ...configOf(status), enabled: false, auto_sync: false });
      acceptStatus(next);
      setDraft((previous) => ({ ...previous, enabled: false, auto_sync: false }));
      clearPreview();
      setNotice(t("同步已停用。书签和共享文件夹中的数据会保留。", "Sync is disabled. Bookmarks and shared-folder data are kept."));
    });
  }

  async function loadPreview() {
    await run("preview", async () => {
      clearPreview();
      setApplied(null);
      const next = await post<Preview>(`${endpoint}/preview`, {});
      setPreview(next);
      const fresh = await api<SyncStatus>(`${endpoint}/status`);
      acceptStatus(fresh);
    });
  }

  async function applyPreview() {
    if (!preview || !confirmed || !allResolved || expired || dirty) return;
    await run("apply", async () => {
      const result = await post<Applied>(`${endpoint}/apply`, { preview_id: preview.preview_id, resolutions });
      acceptStatus(result.status);
      setApplied(result);
      clearPreview();
      setNotice(t("同步完成。", "Synchronization complete."));
      try { await changedRef.current(); }
      catch { setError(t("同步已完成，但未能刷新书签列表。请刷新页面。", "Sync completed, but the bookmark list could not refresh. Reload the page.")); }
    });
  }

  const stateLabel = !status?.enabled ? t("未启用", "Disabled")
    : status.pending_conflicts ? t("有冲突待处理", "Conflicts need review")
      : status.needs_review ? t("等待首次确认", "First review needed")
        : status.auto_sync ? t("自动同步已启用", "Automatic sync enabled") : t("手动同步", "Manual sync");
  const reason = (value: string) => value === "remote_concurrent_changes"
    ? t("共享文件夹中有多个独立修改的版本，请选择要保留的一份。", "The shared folder has concurrent versions. Choose one to keep.")
    : value === "duplicate_url_keep_one"
      ? t("多条书签使用同一地址。请保留其中一条，并为另一条选择「删除重复书签」。", "Multiple bookmarks share a URL. Keep one and choose “Delete duplicate bookmark” for the other.")
      : t("本机和共享文件夹都修改了这条书签。", "This bookmark changed both locally and in the shared folder.");

  return <section className="sync-settings" aria-labelledby="sync-title">
    <header className="section-heading sync-heading">
      <div><h2 id="sync-title">{t("在设备之间同步书签", "Sync bookmarks between devices")}</h2>
        <p>{t("使用已在设备间同步的文件夹，交换地址、标题、文件夹、标签和收藏时间。正文、摘要与模型密钥保留在本机。", "Use a folder already shared between your devices for URLs, titles, folders, tags and save dates. Page text, summaries and model keys stay on this device.")}</p></div>
      {status && <span className="sync-state">{stateLabel}</span>}
    </header>

    {loading && <p className="sync-loading" role="status"><LoaderCircle className="spin" size={18} />{t("正在读取同步设置…", "Loading sync settings…")}</p>}
    {!loading && !status && <button className="secondary" disabled={!!busy} onClick={() => run("load", async () => {
      const next = await api<SyncStatus>(`${endpoint}/status`);
      acceptStatus(next); setDraft(draftOf(next));
    })}><RefreshCw size={16} />{t("重试读取设置", "Retry loading settings")}</button>}

    {status && <>
      <form className="sync-config" onSubmit={(event) => { event.preventDefault(); void saveConfig(); }}>
        <label className="field"><span>{t("共享文件夹完整路径", "Full shared-folder path")}</span>
          <input name="sync_folder" autoComplete="off" spellCheck={false} maxLength={4096} value={draft.folder}
            placeholder={t("填写本机上已有的共享文件夹", "An existing shared folder on this device")}
            disabled={!!busy} onChange={(event) => change({ folder: event.target.value })} aria-describedby="sync-folder-hint" /></label>
        <p className="hint" id="sync-folder-hint">{t("先用 OneDrive、iCloud Drive 或其他工具同步该文件夹，再在每台设备上填写对应的本地路径。Facetmark 会在其中创建自己的同步子目录。", "Share the folder with OneDrive, iCloud Drive or another tool, then enter its local path on each device. Facetmark creates its own sync subfolder inside it.")}</p>
        <div className="sync-options">
          <div className="sync-switches">
            <label className="check"><input type="checkbox" checked={draft.enabled} disabled={!!busy} onChange={(event) => change({ enabled: event.target.checked })} />{t("启用共享文件夹同步", "Enable shared-folder sync")}</label>
            <label className="check"><input type="checkbox" checked={draft.auto_sync} disabled={!!busy || !draft.enabled} onChange={(event) => change({ auto_sync: event.target.checked })} />{t("首次确认后自动同步", "Sync automatically after the first review")}</label>
          </div>
          <label className="field sync-interval"><span>{t("检查间隔（秒）", "Check interval (seconds)")}</span><input name="sync_poll_seconds" type="number" min={30} max={3600} step={1} required value={draft.poll_seconds} disabled={!!busy || !draft.enabled} onChange={(event) => change({ poll_seconds: event.target.value })} /></label>
        </div>
        <p className="hint">{t("自动同步仅在应用运行时执行。出现冲突会暂停，等待你选择版本。", "Automatic sync runs while the app is open. Conflicts pause it until you choose a version.")}</p>
        <div className="form-actions sync-actions">
          <button type="submit" className="secondary" disabled={!!busy || !dirty}>{busy === "save" ? <LoaderCircle className="spin" /> : <Save />}{t("保存同步设置", "Save sync settings")}</button>
          {status.enabled && <button type="button" className="secondary" disabled={!!busy} onClick={disableSync}>{busy === "disable" ? <LoaderCircle className="spin" /> : <Pause />}{t("停用同步", "Disable sync")}</button>}
          {dirty && <span className="hint">{t("有未保存的设置", "Unsaved settings")}</span>}
        </div>
      </form>

      <div className="sync-review-heading">
        <div><h3>{t("先看变更，再同步", "Review changes before syncing")}</h3><p className="hint">{status.last_sync_at ? <>{t("最近同步", "Last synced")} · {new Date(status.last_sync_at * 1000).toLocaleString(t("zh-CN", "en-US"))}</> : t("尚未完成过同步", "No completed sync yet")}</p></div>
        <button type="button" className={preview ? "secondary" : "primary"} disabled={!!busy || !status.enabled || dirty} onClick={loadPreview}>{busy === "preview" ? <LoaderCircle className="spin" /> : <RefreshCw />}{preview ? t("重新预览", "Refresh preview") : t("预览同步变更", "Preview sync changes")}</button>
      </div>
      {!status.enabled && <p className="hint">{t("填写路径并保存启用后，即可查看两端的变化。", "Save an enabled shared-folder configuration to inspect changes on both sides.")}</p>}

      {preview && <div className="sync-preview" aria-label={t("同步变更预览", "Sync change preview")}>
        <CountTable counts={preview.counts} />
        {(preview.excluded_karakeep > 0 || preview.excluded_unsupported > 0) && <p className="hint">{t("本次不参与同步", "Excluded from this sync")} · {preview.excluded_karakeep} {t("条 Karakeep 关联书签", "Karakeep-linked bookmarks")} · {preview.excluded_unsupported} {t("条不支持的地址或格式", "unsupported addresses or records")}</p>}

        {!!preview.changes?.length && <details className="sync-change-list">
          <summary>{t("查看可直接同步的变更", "Inspect nonconflicting changes")} ({preview.changes.length})</summary>
          {preview.changes.map((entry) => <details className="sync-change" key={entry.id}>
            <summary><span>{entry.target?.title || entry.local?.title || entry.remote?.title || t("无标题书签", "Untitled bookmark")}</span><small>{entry.directions.includes("download") ? t("更新本机", "Update this device") : t("发送到共享文件夹", "Send to shared folder")}{entry.target === null && <> · {t("删除", "Delete")}</>}</small></summary>
            <div className="sync-comparison"><div><h4>{t("本机当前版本", "Current local version")}</h4><MetadataView record={entry.local} /></div><div><h4>{t("共享当前版本", "Current shared version")}</h4><MetadataView record={entry.remote} /></div><div><h4>{t("同步后保留的版本", "Version after syncing")}</h4><MetadataView record={entry.target} /></div></div>
          </details>)}
        </details>}

        {preview.conflicts.length > 0 && <div className="sync-conflicts">
          <h3>{t("选择要保留的版本", "Choose the versions to keep")} ({preview.conflicts.length})</h3>
          <p className="hint">{t("每条冲突都需要选择。选择「无此书签」会移除另一端已有的副本；选择后再统一应用。", "Choose a version for every conflict. Choosing an absent version removes the existing copy on the other side. All choices are applied together.")}</p>
          {preview.conflicts.map((conflict, index) => <fieldset className="sync-conflict" key={conflict.id}>
            <legend>{index + 1}. {conflict.local?.title || conflict.remote?.title || conflict.remote_versions.find((v) => v.record)?.record?.title || t("无标题书签", "Untitled bookmark")}</legend>
            <p className="hint">{reason(conflict.reason)}</p>
            <div className="sync-versions">
              {[{ choice: "local", record: conflict.local }, ...conflict.remote_versions, ...(conflict.can_delete ? [{ choice: "delete", record: null }] : [])].map((version, versionIndex) => {
                const label = version.choice === "local" ? t("保留本机状态", "Keep local state")
                  : version.choice === "delete" ? t("删除重复书签", "Delete duplicate bookmark")
                    : `${t("采用共享版本", "Use shared version")} ${versionIndex}`;
                return <div className={`sync-version${resolutions[conflict.id] === version.choice ? " chosen" : ""}`} key={version.choice}>
                  <label className="sync-choice"><input type="radio" name={`sync-resolution-${conflict.id}`} value={version.choice} checked={resolutions[conflict.id] === version.choice} disabled={!!busy || expired} onChange={() => { setResolutions((previous) => ({ ...previous, [conflict.id]: version.choice })); setConfirmed(false); }} /><span>{label}{version.record === null && <> · {t("无此书签", "Absent")}</>}</span></label>
                  <MetadataView record={version.record} />
                </div>;
              })}
            </div>
          </fieldset>)}
        </div>}

        {expired ? <p className="notice" role="status">{t("这次预览已过期，请重新预览后再应用。", "This preview expired. Refresh it before applying.")}</p> : <div className="sync-apply">
          <p className="hint">{t("接收新增、修改或删除前，Facetmark 会先在本机备份当前书签库。共享文件夹只保存书签信息。", "Before receiving additions, edits or deletions, Facetmark backs up the current library locally. The shared folder contains bookmark metadata only.")}</p>
          <label className="check"><input type="checkbox" checked={confirmed} disabled={!!busy || !allResolved} onChange={(event) => setConfirmed(event.target.checked)} />{t("我已核对以上变更，并确认应用", "I reviewed these changes and confirm applying them")}</label>
          <div className="form-actions sync-actions"><button type="button" className="primary" disabled={!!busy || !allResolved || !confirmed || dirty} onClick={applyPreview}>{busy === "apply" ? <LoaderCircle className="spin" /> : <Check />}{t("应用本次同步", "Apply this sync")}</button>{!allResolved && <span className="hint">{t("请先为每条冲突选择版本。", "Choose a version for every conflict first.")}</span>}</div>
        </div>}
      </div>}
    </>}

    {displayError && <div className="error sync-error" role="alert"><span>{displayError}</span><p>{t("检查共享文件夹是否可用；若两端内容发生变化，请重新预览。", "Check that the shared folder is available. If either side changed, refresh the preview.")}</p>{status && <button type="button" className="secondary" disabled={!!busy} onClick={() => run("status", async () => acceptStatus(await api<SyncStatus>(`${endpoint}/status`)))}><RefreshCw size={16} />{t("重试读取状态", "Retry status")}</button>}</div>}
    {notice && <p className="notice" role="status">{notice}</p>}
    {applied && <div className="sync-applied"><CountTable counts={applied.counts} />{applied.backup_path && <p className="sync-backup"><span>{t("本次本机备份", "Local backup for this sync")}</span><code>{applied.backup_path}</code></p>}</div>}
  </section>;
}
