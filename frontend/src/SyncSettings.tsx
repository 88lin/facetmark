import { CapsuleButton } from "./ui/controls";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowDownToLine, ArrowUpFromLine, Check, LoaderCircle, Pause, RefreshCw, Save } from "lucide-react";
import { api, ApiError } from "./api";
import { useText } from "./locale";
import { loadSyncWorkspace, saveSyncWorkspace, validSyncPreview, validSyncStatus, type SyncChangeRequest, type SyncWorkspace } from "./sync-local-state";
import type { SyncApplied as Applied, SyncConfig, SyncCounts as Counts, SyncDraft as Draft, SyncMetadata as Metadata,
  SyncPreview as Preview, SyncReceipt, SyncStatus } from "./sync-types";
import { useSyncOperations } from "./useSyncOperations";
import "./sync-settings.css";

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
  const [restored] = useState(loadSyncWorkspace);
  const [workspace, setWorkspace] = useState<SyncWorkspace>(() => restored ?? {
    version: 1, draft: { folder: "", enabled: false, auto_sync: false, poll_seconds: "60" }, resolutions: {}, confirmed: false,
  });
  const { draft, resolutions, confirmed } = workspace;
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [expired, setExpired] = useState(false);
  const [applied, setApplied] = useState<Applied | null>(null);
  const statusRef = useRef<SyncStatus | null>(null);
  const workspaceRef = useRef(workspace), previewRef = useRef<Preview | null>(null), live = useRef(true);
  const workController = useRef<AbortController | null>(null);
  const busyRef = useRef(false);
  const statusGeneration = useRef(0);
  const changedRef = useRef(onChanged);
  changedRef.current = onChanged;

  function remember(values: Partial<SyncWorkspace>) {
    const next = { ...workspaceRef.current, ...values };
    workspaceRef.current = next;
    setWorkspace(next);
    if (!saveSyncWorkspace(next)) setError(t("无法保存本机同步草稿。请检查本机存储；离开前先保留草稿内容。", "The local sync draft could not be saved. Check local storage and keep a copy before leaving."));
  }
  function acceptPreview(next: Preview | null) { previewRef.current = next; setPreview(next); }
  function clearPreview() {
    acceptPreview(null);
    remember({ previewId: undefined, resolutions: {}, confirmed: false });
  }
  async function readStatus(signal?: AbortSignal) {
    const next = await api<unknown>(`${endpoint}/status`, { signal });
    if (!validSyncStatus(next)) throw new Error(t("同步状态不完整，请重新读取。原操作与草稿已保留。", "Sync status is incomplete. Read again; the original operation and draft are retained."));
    return next;
  }
  async function readPreview(previewId: string, signal?: AbortSignal) {
    const next = await api<unknown>(`${endpoint}/previews/${encodeURIComponent(previewId)}`, { signal });
    if (!validSyncPreview(next, previewId)) throw new Error(t("无法核对原预览内容，请重新读取。", "The original preview could not be verified. Read it again."));
    return next;
  }
  const recovery = useSyncOperations(async (receipt: SyncReceipt, change?: SyncChangeRequest) => {
    statusGeneration.current += 1;
    setError("");
    acceptStatus(receipt.current_status);
    if (receipt.action === "apply") {
      const result = receipt.result as Applied;
      setApplied(result);
      if (!change || (change.kind === "apply" && workspaceRef.current.previewId === change.previewId)) clearPreview();
      setNotice(result.complete ? t("同步完成。", "Synchronization complete.")
        : t("本机变更已保存。共享文件夹发送尚未完成，可继续原同步。", "Local changes are saved. Shared-folder delivery is unfinished; continue the original sync."));
    }
    const fresh = await readStatus();
    if (!live.current) return;
    acceptStatus(fresh);
    if (change?.kind === "configure" && JSON.stringify(workspaceRef.current.draft) === JSON.stringify(draftOf(change.values))) {
      remember({ draft: draftOf(fresh), configRevision: fresh.config_revision });
      clearPreview(); setApplied(null);
    } else if (change?.kind === "configure" && !change.values.enabled) {
      remember({ draft: { ...workspaceRef.current.draft, enabled: false, auto_sync: false }, configRevision: fresh.config_revision });
    }
    if (receipt.action === "configure") setNotice(fresh.enabled ? fresh.needs_review
      ? t("配置已保存。先预览并确认一次同步。", "Settings saved. Preview and confirm a sync first.")
      : t("同步设置已保存。", "Sync settings saved.")
      : t("同步已停用。书签、共享数据与未完成的原同步均保留。", "Sync is disabled. Bookmarks, shared data and unfinished original syncs are retained."));
    if (receipt.action === "apply") await changedRef.current();
  });

  function acceptStatus(next: SyncStatus) {
    statusRef.current = next;
    setStatus(next);
  }

  useEffect(() => {
    live.current = true;
    const controller = new AbortController();
    async function refresh(initial = false) {
      if (!initial && (busyRef.current || recovery.isBusy())) return;
      // Claim a generation before the request, not after: a slow poll that
      // resolves after an apply must not overwrite the post-apply state.
      const generation = ++statusGeneration.current;
      try {
        const next = await readStatus(controller.signal);
        if (controller.signal.aborted || generation !== statusGeneration.current) return;
        const previous = statusRef.current;
        acceptStatus(next);
        if (!previous && !restored) remember({ draft: draftOf(next), configRevision: next.config_revision });
        if (initial && workspaceRef.current.previewId) {
          const original = await readPreview(workspaceRef.current.previewId, controller.signal);
          if (controller.signal.aborted || generation !== statusGeneration.current) return;
          acceptPreview(original);
          if (original.stale) remember({ confirmed: false });
        }
        if (previous && (next.last_sync_id !== previous.last_sync_id || next.last_sync_at !== previous.last_sync_at)) {
          if (previewRef.current) acceptPreview({ ...previewRef.current, stale: true });
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
    return () => { live.current = false; controller.abort(); workController.current?.abort(); window.clearInterval(timer); };
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
  const displayError = error || recovery.error || status?.last_error || status?.pending_operations?.find(value => value.error)?.error;
  const locked = !!busy || recovery.busy;
  const hasOriginal = recovery.operations.length > 0 || !!status?.pending_operations?.length;
  const canDisable = recovery.operations.every(value => value.confirmed);
  const stale = !!preview?.stale;
  const configChanged = !!status && !!workspace.configRevision && workspace.configRevision !== status.config_revision;

  async function run(action: string, work: (signal: AbortSignal) => Promise<void>) {
    if (busyRef.current || recovery.isBusy()) return;
    statusGeneration.current += 1;
    busyRef.current = true;
    setBusy(action);
    setError("");
    setNotice("");
    const controller = new AbortController(); workController.current = controller;
    try { await work(controller.signal); }
    catch (e) {
      if (!live.current || controller.signal.aborted) return;
      if (e instanceof ApiError && e.status === 409 && previewRef.current) acceptPreview({ ...previewRef.current, stale: true });
      setError(e instanceof Error ? e.message : String(e));
    } finally { busyRef.current = false; if (live.current) setBusy(""); }
  }

  function change(values: Partial<Draft>) {
    remember({ draft: { ...workspaceRef.current.draft, ...values } });
    clearPreview();
    setNotice("");
  }

  async function saveConfig() {
    await run("save", async () => {
      const current = workspaceRef.current.draft;
      const seconds = Number(current.poll_seconds);
      if (!Number.isInteger(seconds) || seconds < 30 || seconds > 3600) {
        throw new Error(t("检查间隔须为 30–3600 秒的整数。", "Choose a whole-number interval from 30 to 3600 seconds."));
      }
      if (current.enabled && !current.folder.trim()) throw new Error(t("请填写已有共享文件夹的完整路径。", "Enter the full path to an existing shared folder."));
      const values = { ...current, folder: current.folder.trim(), poll_seconds: seconds, auto_sync: current.enabled && current.auto_sync,
        expected_revision: workspaceRef.current.configRevision ?? statusRef.current?.config_revision };
      remember({ draft: draftOf(values) });
      await recovery.run({ kind: "configure", values });
    });
  }

  async function disableSync() {
    if (!statusRef.current) return;
    await run("disable", async () => {
      await recovery.run({ kind: "configure", values: { ...configOf(statusRef.current!), enabled: false, auto_sync: false,
        expected_revision: statusRef.current!.config_revision } });
    });
  }

  async function loadPreview() {
    if (hasOriginal) return;
    await run("preview", async signal => {
      const next = await api<unknown>(`${endpoint}/preview`, { method: "POST", body: "{}", signal, timeoutMs: 20000 });
      if (!validSyncPreview(next)) throw new Error(t("预览内容不完整。原预览与选择已保留，请重试。", "The preview is incomplete. The original preview and choices are retained; retry."));
      if (signal.aborted) return;
      const previous = previewRef.current, choices = workspaceRef.current.resolutions;
      const retained: Record<string, string> = {};
      for (const conflict of next.conflicts) {
        const original = previous?.conflicts.find(item => item.id === conflict.id);
        if (original && JSON.stringify(original) === JSON.stringify(conflict) && choices[conflict.id]) retained[conflict.id] = choices[conflict.id];
      }
      acceptPreview(next); remember({ previewId: next.preview_id, resolutions: retained, confirmed: false }); setApplied(null);
      const fresh = await readStatus(signal);
      if (signal.aborted) return;
      acceptStatus(fresh);
    });
  }

  async function applyPreview() {
    if (!previewRef.current || !workspaceRef.current.confirmed || !allResolved || expired || dirty || stale || hasOriginal) return;
    await run("apply", async () => {
      const accepted = await recovery.run({ kind: "apply", previewId: previewRef.current!.preview_id, resolutions: { ...workspaceRef.current.resolutions } });
      if (!accepted && previewRef.current) acceptPreview({ ...previewRef.current, stale: true });
    });
  }

  async function returnToEdit(requestId: string) {
    await run("return", async signal => {
      const original = await recovery.abandon(requestId);
      if (!original || signal.aborted) return;
      if (original.kind === "configure") {
        remember({ draft: draftOf(original.values), configRevision: original.values.expected_revision });
        clearPreview();
      } else {
        remember({ previewId: original.previewId, resolutions: { ...original.resolutions }, confirmed: false });
        if (previewRef.current?.preview_id === original.previewId) acceptPreview({ ...previewRef.current, stale: true });
        else acceptPreview(null);
      }
      const fresh = await readStatus(signal);
      if (signal.aborted) return;
      acceptStatus(fresh);
      if (original.kind === "configure" && !original.values.expected_revision) remember({ configRevision: fresh.config_revision });
      setNotice(t("原操作未被接受。内容已保留，可以核对后修改并重新预览。", "The original operation was not accepted. Its content is retained; review and edit before a new preview."));
    });
  }
  function setConfirmed(value: boolean) { remember({ confirmed: value }); }
  function choose(id: string, value: string) {
    remember({ resolutions: { ...workspaceRef.current.resolutions, [id]: value }, confirmed: false });
  }

  const stateLabel = !status?.enabled ? t("未启用", "Disabled")
    : status.pending_operations?.length ? t("原同步待完成", "Original sync unfinished")
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
    {!loading && !status && <CapsuleButton className="secondary" disabled={locked} onClick={() => run("load", async signal => {
      const next = await readStatus(signal);
      if (signal.aborted) return;
      acceptStatus(next); if (!restored) remember({ draft: draftOf(next), configRevision: next.config_revision });
    })}><RefreshCw size={16} />{t("重试读取设置", "Retry loading settings")}</CapsuleButton>}

    {recovery.showRecovery && recovery.operations.length > 0 && <aside className="sync-recovery" aria-label={t("同步操作恢复", "Sync operation recovery")} aria-busy={locked}>
      {recovery.operations.map(value => <div className="sync-recovery-item" key={value.requestId}>
        <div className="sync-recovery-copy"><strong>{value.confirmed ? <Check size={17} /> : <RefreshCw size={17} />}{value.change.kind === "configure" ? t("原同步设置保存", "Original sync settings save") : t("原同步变更", "Original sync changes")}</strong>
          <p>{value.confirmed ? t("操作已接受。再次读取可以确认当前状态；继续原同步只完成尚未发送的内容。", "The operation was accepted. Read its current status; continuing only delivers unfinished original content.")
            : value.rejected ? t("原请求未被接受。可以返回修改，原内容仍会保留。", "The original request was not accepted. Return to edit; its content is retained.")
              : value.refused ? t("请求已被拒绝，仍需核对保存结果。先读取确认，再返回修改。", "The request was refused, but its saved result still needs checking. Read before returning to edit.")
                : t("暂时无法确定原请求是否已接受。重开页面仅查询结果；重试会保留原内容。", "The original request's acceptance is uncertain. Reopening only reads its result; retry retains the original content.")}</p>
          {value.change.kind === "configure" ? <details className="sync-original"><summary>{t("查看原设置内容", "View original settings")}</summary><dl className="sync-metadata">
            <div><dt>{t("共享文件夹", "Shared folder")}</dt><dd>{value.change.values.folder || t("未设置", "Not set")}</dd></div>
            <div><dt>{t("同步方式", "Sync mode")}</dt><dd>{!value.change.values.enabled ? t("停用", "Disabled") : value.change.values.auto_sync ? t("自动同步", "Automatic sync") : t("手动同步", "Manual sync")} · {value.change.values.poll_seconds} {t("秒", "seconds")}</dd></div>
          </dl></details> : <p className="hint">{value.change.kind === "apply" ? <>{Object.keys(value.change.resolutions).length} {t("条原冲突选择已保留", "original conflict choices retained")}</>
            : t("原同步结果已保存，读取不会重新改写书签。", "The original sync result is saved. Reading never rewrites bookmarks.")}</p>}
        </div>
        <div className="sync-recovery-actions">
          <CapsuleButton className="secondary" disabled={locked} onClick={() => recovery.check(value.requestId)}><RefreshCw size={16} />{t("读取原操作结果", "Read original result")}</CapsuleButton>
          {!value.refused && (!value.confirmed || value.change.kind === "apply" || (value.change.kind === "receipt" && value.change.action === "apply")) && <CapsuleButton className="secondary" disabled={locked} onClick={() => recovery.check(value.requestId, true)}>
            <ArrowUpFromLine size={16} />{value.confirmed ? t("继续原同步", "Continue original sync") : t("重试原请求", "Retry original request")}</CapsuleButton>}
          {value.rejected && !value.confirmed && <CapsuleButton className="secondary" disabled={locked} onClick={() => returnToEdit(value.requestId)}>{t("返回修改同步", "Return to edit sync")}</CapsuleButton>}
        </div>
      </div>)}
    </aside>}

    {!!status?.pending_operations?.length && status.pending_operations.filter(value => !recovery.operations.some(local => local.requestId === value.request_id)).map(value =>
      <aside className="sync-recovery" aria-label={t("未完成的共享发送", "Unfinished shared delivery")} key={value.request_id} aria-busy={locked}>
        <div className="sync-recovery-copy"><strong><ArrowUpFromLine size={17} />{t("本机已保存，共享发送待完成", "Saved locally; shared delivery unfinished")}</strong>
          <p>{t("继续原同步使用已保存的发送内容，不会再次改写本机书签。停用同步仍保留这次原操作。", "Continue using the saved delivery content without rewriting local bookmarks. Disabling sync retains this original operation.")}</p>
          <details className="sync-original"><summary>{t("查看原发送内容", "View original delivery")}</summary><p className="sync-path">{value.folder}</p><CountTable counts={value.counts} />{value.backup_path && <p className="sync-path">{value.backup_path}</p>}</details>
        </div>
        <div className="sync-recovery-actions"><CapsuleButton className="secondary" disabled={locked} onClick={() => recovery.check(value.request_id)}><RefreshCw size={16} />{t("读取原操作结果", "Read original result")}</CapsuleButton>
          <CapsuleButton className="secondary" disabled={locked} onClick={() => recovery.check(value.request_id, true)}><ArrowUpFromLine size={16} />{t("继续原同步", "Continue original sync")}</CapsuleButton></div>
      </aside>)}

    {status && <>
      {configChanged && <div className="sync-current" role="status"><p>{t("同步设置已在另一窗口修改。你的草稿已保留，请核对当前设置后继续。", "Sync settings changed in another window. Your draft is retained; review the current settings before continuing.")}</p>
        <details className="sync-original"><summary>{t("查看当前已保存设置", "View currently saved settings")}</summary><p className="sync-path">{status.folder || t("未设置路径", "No path set")}</p><p>{!status.enabled ? t("已停用", "Disabled") : status.auto_sync ? t("自动同步", "Automatic sync") : t("手动同步", "Manual sync")} · {status.poll_seconds} {t("秒", "seconds")}</p></details>
        <div className="sync-actions form-actions"><CapsuleButton className="secondary" disabled={locked || hasOriginal} onClick={() => { remember({ draft: draftOf(status), configRevision: status.config_revision }); clearPreview(); }}>{t("采用当前设置", "Use current settings")}</CapsuleButton>
          <CapsuleButton className="secondary" disabled={locked || hasOriginal} onClick={() => remember({ configRevision: status.config_revision })}>{t("保留草稿并继续", "Keep draft and continue")}</CapsuleButton></div>
      </div>}
      <form className="sync-config" onSubmit={(event) => { event.preventDefault(); void saveConfig(); }}>
        <label className="field"><span>{t("共享文件夹完整路径", "Full shared-folder path")}</span>
          <input name="sync_folder" autoComplete="off" spellCheck={false} maxLength={4096} value={draft.folder}
            placeholder={t("填写本机上已有的共享文件夹", "An existing shared folder on this device")}
            disabled={locked || hasOriginal} onChange={(event) => change({ folder: event.target.value })} aria-describedby="sync-folder-hint" /></label>
        <p className="hint" id="sync-folder-hint">{t("先用 OneDrive、iCloud Drive 或其他工具同步该文件夹，再在每台设备上填写对应的本地路径。Facetmark 会在其中创建自己的同步子目录。", "Share the folder with OneDrive, iCloud Drive or another tool, then enter its local path on each device. Facetmark creates its own sync subfolder inside it.")}</p>
        <div className="sync-options">
          <div className="sync-switches">
            <label className="check"><input type="checkbox" checked={draft.enabled} disabled={locked || hasOriginal} onChange={(event) => change({ enabled: event.target.checked })} />{t("启用共享文件夹同步", "Enable shared-folder sync")}</label>
            <label className="check"><input type="checkbox" checked={draft.auto_sync} disabled={locked || hasOriginal || !draft.enabled} onChange={(event) => change({ auto_sync: event.target.checked })} />{t("首次确认后自动同步", "Sync automatically after the first review")}</label>
          </div>
          <label className="field sync-interval"><span>{t("检查间隔（秒）", "Check interval (seconds)")}</span><input name="sync_poll_seconds" type="number" min={30} max={3600} step={1} required value={draft.poll_seconds} disabled={locked || hasOriginal || !draft.enabled} onChange={(event) => change({ poll_seconds: event.target.value })} /></label>
        </div>
        <p className="hint">{t("自动同步仅在应用运行时执行。出现冲突会暂停，等待你选择版本。", "Automatic sync runs while the app is open. Conflicts pause it until you choose a version.")}</p>
        <div className="form-actions sync-actions">
          <CapsuleButton type="submit" className="secondary" disabled={locked || hasOriginal || !dirty || configChanged}>{busy === "save" ? <LoaderCircle className="spin" /> : <Save />}{t("保存同步设置", "Save sync settings")}</CapsuleButton>
          {status.enabled && <CapsuleButton type="button" className="secondary" disabled={locked || !canDisable} onClick={disableSync}>{busy === "disable" ? <LoaderCircle className="spin" /> : <Pause />}{t("停用同步", "Disable sync")}</CapsuleButton>}
          {dirty && <span className="hint">{t("有未保存的设置", "Unsaved settings")}</span>}
        </div>
      </form>

      <div className="sync-review-heading">
        <div><h3>{t("先看变更，再同步", "Review changes before syncing")}</h3><p className="hint">{status.last_sync_at ? <>{t("最近同步", "Last synced")} · {new Date(status.last_sync_at * 1000).toLocaleString(t("zh-CN", "en-US"))}</> : t("尚未完成过同步", "No completed sync yet")}</p></div>
        <CapsuleButton type="button" className={preview ? "secondary" : "primary"} disabled={locked || hasOriginal || !status.enabled || dirty} onClick={loadPreview}>{busy === "preview" ? <LoaderCircle className="spin" /> : <RefreshCw />}{preview ? t("重新预览", "Refresh preview") : t("预览同步变更", "Preview sync changes")}</CapsuleButton>
      </div>
      {workspace.previewId && !preview && <p className="sync-preview-read">{t("原预览仍已保留。重新读取只查看内容，不会应用同步。", "The original preview is retained. Reading it only inspects content and never applies a sync.")}
        <CapsuleButton className="secondary" disabled={locked} onClick={() => run("read-preview", async signal => {
          const next = await readPreview(workspaceRef.current.previewId!, signal); if (signal.aborted) return;
          acceptPreview(next); if (next.stale) remember({ confirmed: false });
        })}><RefreshCw size={16} />{t("重新读取原预览", "Read original preview again")}</CapsuleButton></p>}
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
                  <label className="sync-choice"><input type="radio" name={`sync-resolution-${conflict.id}`} value={version.choice} checked={resolutions[conflict.id] === version.choice} disabled={locked || hasOriginal || expired || stale} onChange={() => choose(conflict.id, version.choice)} /><span>{label}{version.record === null && <> · {t("无此书签", "Absent")}</>}</span></label>
                  <MetadataView record={version.record} />
                </div>;
              })}
            </div>
          </fieldset>)}
        </div>}

        {(expired || stale) && <p className="notice" role="status">{expired ? t("这次预览已过期，内容仍可查看。请重新预览后再应用。", "This preview expired, but its content remains viewable. Refresh it before applying.")
          : t("本机、共享内容或设置已变化。原预览与选择保留供核对，请重新预览后再应用。", "Local, shared content or settings changed. The original preview and choices are retained for review; refresh before applying.")}</p>}
        <div className="sync-apply">
          <p className="hint">{t("接收新增、修改或删除前，Facetmark 会先在本机备份当前书签库。共享文件夹只保存书签信息。", "Before receiving additions, edits or deletions, Facetmark backs up the current library locally. The shared folder contains bookmark metadata only.")}</p>
          <label className="check"><input type="checkbox" checked={confirmed} disabled={locked || hasOriginal || !allResolved || expired || stale} onChange={(event) => setConfirmed(event.target.checked)} />{t("我已核对以上变更，并确认应用", "I reviewed these changes and confirm applying them")}</label>
          <div className="form-actions sync-actions"><CapsuleButton type="button" className="primary" disabled={locked || hasOriginal || !allResolved || !confirmed || dirty || expired || stale} onClick={applyPreview}>{busy === "apply" ? <LoaderCircle className="spin" /> : <Check />}{t("应用本次同步", "Apply this sync")}</CapsuleButton>{!allResolved && <span className="hint">{t("请先为每条冲突选择版本。", "Choose a version for every conflict first.")}</span>}</div>
        </div>
      </div>}
    </>}

    {displayError && <div className="error sync-error" role="alert"><span>{displayError}</span><p>{hasOriginal ? t("原操作已保留。先读取原结果，再继续发送或返回修改。", "The original operation is retained. Read its result before continuing delivery or returning to edit.")
      : t("检查共享文件夹是否可用；若两端内容发生变化，请重新预览。", "Check that the shared folder is available. If either side changed, refresh the preview.")}</p>{status && <CapsuleButton type="button" className="secondary" disabled={locked} onClick={() => run("status", async signal => {
        const next = await readStatus(signal); if (!signal.aborted) acceptStatus(next);
      })}><RefreshCw size={16} />{t("重试读取状态", "Retry status")}</CapsuleButton>}</div>}
    {notice && <p className="notice" role="status">{notice}</p>}
    {applied && <div className="sync-applied"><CountTable counts={applied.counts} />{applied.backup_path && <p className="sync-backup"><span>{t("本次本机备份", "Local backup for this sync")}</span><code>{applied.backup_path}</code></p>}</div>}
  </section>;
}
