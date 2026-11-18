import { CapsuleButton } from "./ui/controls";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence } from "motion/react";
import { BookOpen, Check, ChevronDown, Download, Folder, ListChecks, LoaderCircle, MessageCircle, Minus, Plus, RotateCcw, Sparkles, Tag, Trash2, X } from "lucide-react";
import { api, ApiError, downloadExport, post, safeUrl, type Bookmark, type CollectionScope, type Setup } from "./api";
import { exportRequest, libraryRequest, type BookmarkValues, type ExportContext, type LibraryChange, type LibraryOperation, type LibraryReceipt } from "./library-local-state";
import { useText } from "./locale";
import type { TaskChange } from "./task-local-state";
import { FolderPicker } from "./FolderPicker";
import { OverlayMotion } from "./overlay-motion";
import "./library-tools.css";

type Facet = { value: string; count: number };
type Filters = { folder?: string; tag?: string; domain?: string; session?: number };
export type LibraryAction =
  | { kind: "create"; values?: BookmarkValues; notice?: string }
  | { kind: "edit"; record: Bookmark; values?: Partial<BookmarkValues> }
  | { kind: "delete"; ids: number[] }
  | { kind: "bulk"; ids: number[]; initial?: Extract<LibraryChange, { kind: "bulk" }> }
  | { kind: "taxonomy"; initial?: Extract<LibraryChange, { kind: "taxonomy" }> }
  | { kind: "export" }
  | { kind: "recover"; operation: LibraryOperation }
  | { kind: "process"; mode: "fetch" | "summarize"; ids?: number[]; scope?: CollectionScope; scopeLabel?: string; reprocess?: boolean };

export function LibraryToolbar({ batch, ids, pageIds, disabled, pending, onBatch, onIds, onAction, onSummarize,
  selectedCount, allSelected, total, crossPage, onAll, onClear, onChat, processingDisabled = false }: {
  batch: boolean; ids: number[]; pageIds: number[]; disabled: boolean; pending: boolean;
  onBatch: (value: boolean) => void; onIds: (ids: number[]) => void;
  onAction: (action: LibraryAction) => void;
  onSummarize: () => void;
  onChat?: () => void;
  processingDisabled?: boolean;
  selectedCount: number; allSelected: boolean; total: number; crossPage: boolean; onAll: () => void; onClear: () => void;
}) {
  const t = useText();
  const manage = useRef<HTMLDetailsElement>(null);
  const selection = useRef<HTMLInputElement>(null);
  useEffect(() => { if (selection.current) selection.current.indeterminate = selectedCount > 0 && !allSelected; }, [selectedCount, allSelected]);
  useEffect(() => {
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && manage.current && !manage.current.contains(event.target)) manage.current.open = false;
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);
  const pageSelected = pageIds.length > 0 && pageIds.every(id => ids.includes(id));
  const count = selectedCount || total;
  const countLabel = selectedCount ? t("已选 " + count.toLocaleString(), count.toLocaleString() + " selected")
    : t("共 " + count.toLocaleString(), count.toLocaleString() + " total");
  const compactCount = t(count.toLocaleString("zh-CN", { notation: "compact", maximumFractionDigits: 1 }),
    count.toLocaleString("en", { notation: "compact", maximumFractionDigits: 1 }));
  return <div className={`library-tools ${batch ? "selecting" : ""}`}>
    {batch ? <>
      <span className="selection-total" role="status">{t(`已选择 ${ids.length} 条`, `${ids.length} selected`)}</span>
      <CapsuleButton className="text-button" aria-pressed={pageSelected} disabled={!pageIds.length || pending}
        onClick={() => onIds(pageSelected ? ids.filter(id => !pageIds.includes(id)) : [...new Set([...ids, ...pageIds])].slice(0, 1000))}>
        {pageSelected ? t("取消本页选择", "Deselect this page") : t("选择本页", "Select this page")}</CapsuleButton>
      <CapsuleButton className="secondary" disabled={!ids.length || disabled || pending} onClick={() => onAction({ kind: "bulk", ids })}><ListChecks size={15}/>{t("批量操作", "Actions")}</CapsuleButton>
      <CapsuleButton className="secondary" disabled={!ids.length || pending} onClick={() => onAction({ kind: "export" })}><Download size={15}/>{t("导出所选", "Export selected")}</CapsuleButton>
      {onChat && <CapsuleButton type="button" className="secondary" disabled={!selectedCount || selectedCount > 12 || pending || disabled}
        title={t("一次最多讨论 12 篇收藏", "Discuss up to 12 saved pages at a time")} onClick={onChat}><MessageCircle size={15}/>{t("聊所选", "Discuss selected")}</CapsuleButton>}
      <CapsuleButton className="text-button" onClick={() => onBatch(false)}>{t("完成选择", "Done")}</CapsuleButton>
      {ids.length >= 1000 && <span className="selection-limit" role="status">{t("一次最多选择 1000 条", "Select up to 1,000 at a time")}</span>}
    </> : <>
      <CapsuleButton className="secondary library-add" aria-label={t("新增收藏", "Add bookmark")} disabled={disabled} onClick={() => onAction({ kind: "create" })}><Plus size={15}/><span className="action-full">{t("新增收藏", "Add bookmark")}</span><span className="action-short" aria-hidden="true">{t("新增", "Add")}</span></CapsuleButton>
      <details ref={manage} className="library-manage" onBlur={event => { if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) event.currentTarget.open = false; }} onKeyDown={event => { if (event.key === "Escape") { event.currentTarget.open = false; event.currentTarget.querySelector("summary")?.focus(); } }}>
        <summary aria-label={t("管理收藏", "Manage")} title={t("管理收藏", "Manage")}><ListChecks className="action-short" size={16}/><span className="action-full">{t("管理收藏", "Manage")}</span><ChevronDown size={14}/></summary>
        <div className="library-manage-menu" onClick={event => { if ((event.target as HTMLElement).closest("button:not(:disabled)")) event.currentTarget.closest("details")!.open = false; }}>
          <CapsuleButton type="button" disabled={!pageIds.length || disabled || pending} onClick={() => onBatch(true)}><ListChecks size={16}/>{t("批量管理", "Select")}</CapsuleButton>
          <CapsuleButton type="button" disabled={disabled} onClick={() => onAction({ kind: "taxonomy" })}><Folder size={16}/>{t("整理分类", "Organize")}</CapsuleButton>
          <CapsuleButton type="button" disabled={pending} onClick={() => onAction({ kind: "export" })}><Download size={16}/>{t("导出", "Export")}</CapsuleButton>
          {onChat && <CapsuleButton type="button" disabled={!selectedCount || selectedCount > 12 || pending || disabled}
            title={t("一次最多讨论 12 篇收藏", "Discuss up to 12 saved pages at a time")} onClick={onChat}><MessageCircle size={16}/>{t("聊所选", "Discuss selected")}</CapsuleButton>}
        </div>
      </details>
    </>}
    <label className="library-summary-selection" data-selected={selectedCount > 0} data-disabled={disabled || pending || !total} title={crossPage
      ? t("全选当前筛选结果，跨页生效", "Select all matching results across pages")
      : t("选择本页语义结果，保留已有选择", "Select this page of semantic results and keep existing selections")}>
      <input ref={selection} type="checkbox" checked={allSelected} disabled={disabled || pending || !total}
        aria-label={t("全选当前结果", "Select all results")} onChange={event => event.target.checked ? onAll() : onClear()}/>
      <span className="library-selection-mark" aria-hidden="true">{allSelected ? <Check size={14}/> : selectedCount > 0 ? <Minus size={14}/> : null}</span>
      <span><span className="action-full">{t("全选", "Select all")}</span><span className="action-short" aria-hidden="true">{t("全选", "All")}</span></span>
      <span className="library-selection-count" role="status" aria-label={countLabel} title={countLabel}>
        <span className="library-count-full">{countLabel}</span>
        <span className="library-count-compact" aria-hidden="true" data-count={compactCount}/>
      </span>
    </label>
    <CapsuleButton className="primary library-summarize" aria-label={t("生成摘要", "Summarize")} disabled={disabled || processingDisabled || pending || !pageIds.length} onClick={onSummarize}><Sparkles size={15}/><span className="action-full">{t("生成摘要", "Summarize")}</span><span className="action-short" aria-hidden="true">{t("生成", "Summarize")}</span></CapsuleButton>
  </div>;
}

function TagEditor({ tags, onChange }: { tags: string[]; onChange: (tags: string[]) => void }) {
  const t = useText();
  const [draft, setDraft] = useState("");
  const hintId = useId();
  const append = () => {
    const value = draft.trim();
    if (value && !tags.includes(value) && tags.length < 100) onChange([...tags, value]);
    setDraft("");
  };
  return <div className="tag-editor">
    <div className="tag-entry">
      <input aria-label={t("输入标签", "Enter a tag")} aria-describedby={hintId} value={draft} maxLength={128} placeholder={t("输入标签后按 Enter", "Add a tag, then Enter")} onChange={e => setDraft(e.target.value)} onBlur={append} onKeyDown={e => { if (e.key === "Enter" && !e.nativeEvent.isComposing) { e.preventDefault(); append(); } }}/>
      <CapsuleButton type="button" className="icon-button" aria-label={t("添加标签", "Add tag")} onClick={append}><Plus size={16}/></CapsuleButton>
    </div>
    <p id={hintId} className="hint tag-hint">{t("标签可包含空格或逗号。", "Tags can include spaces or commas.")}</p>
    {!!tags.length && <div className="editing-tags">{tags.map(tag => <CapsuleButton type="button" key={tag} onClick={() => onChange(tags.filter(value => value !== tag))} aria-label={t(`移除标签 ${tag}`, `Remove tag ${tag}`)}><Tag size={12}/>{tag}<X size={12}/></CapsuleButton>)}</div>}
  </div>;
}

export function LibraryRecoveryBanner({ operations, onOpen }: { operations: LibraryOperation[]; onOpen: (value: LibraryOperation) => void }) {
  const t = useText();
  if (!operations.length) return null;
  return <aside className="library-recovery-banner" role="status"><RotateCcw size={17}/>
    <span>{t(`还有 ${operations.length} 项收藏操作需要确认结果。`, `${operations.length} collection operation(s) still need their result confirmed.`)}</span>
    <CapsuleButton type="button" className="secondary" onClick={() => onOpen(operations[0])}>{t("查看操作", "Review operation")}</CapsuleButton>
  </aside>;
}

function OperationSummary({ change }: { change: LibraryChange }) {
  const t = useText();
  const values: [string, string][] = change.kind === "create" || change.kind === "edit"
    ? Object.entries(change.values).map(([key, value]) => [key === "url" ? t("网址", "URL") : key === "title" ? t("标题", "Title")
      : key === "folder" ? t("文件夹", "Folder") : t("标签", "Tags"), Array.isArray(value) ? value.join(" · ") : value])
    : change.kind === "bulk" ? [[t("操作", "Action"), change.action === "delete" ? t("删除收藏", "Delete bookmarks")
      : change.action === "move" ? t("移动收藏", "Move bookmarks") : change.action === "tag-add" ? t("添加标签", "Add tags") : t("移除标签", "Remove tags")],
      [t("原先选择", "Original selection"), t(`${change.ids.length} 条收藏`, `${change.ids.length} bookmarks`)],
      ...(change.folder !== undefined ? [[t("目标文件夹", "Destination folder"), change.folder] as [string, string]] : []),
      ...(change.tags ? [[t("标签", "Tags"), change.tags.join(" · ")] as [string, string]] : [])]
      : [[change.kindOfName === "folder" ? t("文件夹", "Folder") : t("标签", "Tag"), change.name],
        [t("操作", "Action"), change.action === "rename" ? t("重命名或合并", "Rename or merge") : t("移除分类", "Remove category")],
        ...(change.newName !== undefined ? [[t("新名称", "New name"), change.newName] as [string, string]] : [])];
  const content = (label: string, value: string) => label === t("网址", "URL") && safeUrl(value)
    ? <a href={safeUrl(value)} target="_blank" rel="noreferrer">{value}</a> : value || t("留空", "Empty");
  return <dl className="library-operation-summary">{values.map(([label, value]) => <div key={label}><dt>{label}</dt>
    <dd>{value.length > 160 ? <details className="library-operation-detail"><summary aria-label={t("查看完整", "View full ") + label}>
      <span className="library-operation-short">{value}</span><span className="library-operation-disclosure"><ChevronDown size={14}/>{t("完整内容", "Full text")}</span>
    </summary><div>{content(label, value)}</div></details> : content(label, value)}</dd></div>)}</dl>;
}

function validWriteResult(value: unknown, change: LibraryChange): value is LibraryReceipt["result"] {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const result = value as LibraryReceipt["result"], validId = (id: unknown) => typeof id === "number" && Number.isSafeInteger(id) && id > 0;
  if (change.kind === "create" || change.kind === "edit") return validId(result.bookmark_id)
    && (change.kind !== "edit" || result.bookmark_id === change.bookmarkId);
  if (!Array.isArray(result.ids) || !result.ids.every(validId) || typeof result.deleted !== "number" || result.deleted < 0) return false;
  if (change.kind === "bulk") return result.ids.length === new Set(change.ids).size && result.ids.every(id => change.ids.includes(id));
  return true;
}

export function LibraryDialog({ action, onClose, onChanged, onTask, onPending, onPreview, onRestoreDraft, facets, setup, running,
  pageIds, selectedIds, filters, searching, currentScope, allMatching, selectedCount, semantic }: {
  action: LibraryAction; onClose: () => void;
  onChanged: (deleted?: number[]) => Promise<void>; onTask: (change: TaskChange) => Promise<boolean>;
  onPending: (value: LibraryOperation | null, requestId: string) => boolean; onPreview: (id: number) => void;
  onRestoreDraft: (action: LibraryAction) => void;
  facets: Record<string, Facet[]>; setup: Setup | null; running: boolean;
  pageIds: number[]; selectedIds: number[]; filters: Filters; searching: boolean;
  currentScope: CollectionScope; allMatching: boolean; selectedCount: number; semantic: boolean;
}) {
  const t = useText();
  const [open, setOpen] = useState(true);
  const source = action.kind === "edit" ? action.record : null;
  const values = action.kind === "create" || action.kind === "edit" ? action.values : undefined;
  const bulkInitial = action.kind === "bulk" ? action.initial : undefined;
  const nameInitial = action.kind === "taxonomy" ? action.initial : undefined;
  const [url, setUrl] = useState(values?.url ?? source?.url ?? "");
  const [title, setTitle] = useState(values?.title ?? source?.title ?? "");
  const [folder, setFolder] = useState(values?.folder ?? bulkInitial?.folder ?? source?.folder ?? filters.folder ?? "");
  const [tags, setTags] = useState<string[]>(values?.tags ?? bulkInitial?.tags ?? source?.tags ?? (action.kind === "create" && filters.tag ? [filters.tag] : []));
  const [operation, setOperation] = useState<string>(bulkInitial?.action ?? "move");
  const [taxonomy, setTaxonomy] = useState<string>(nameInitial?.kindOfName ?? (filters.folder === undefined && filters.tag !== undefined ? "tag" : "folder"));
  const [taxonomyAction, setTaxonomyAction] = useState<string>(nameInitial?.action ?? "rename");
  const [name, setName] = useState(nameInitial?.name ?? filters.folder ?? filters.tag ?? "");
  const [newName, setNewName] = useState(nameInitial?.newName ?? "");
  const [format, setFormat] = useState("json");
  const exportContext = useRef<ExportContext>({ current: structuredClone(currentScope), selectedIds: [...selectedIds],
    pageIds: [...pageIds], allMatching, selectedCount, semantic });
  const frozen = exportContext.current;
  const [scope, setScope] = useState(frozen.selectedCount ? "selected" : searching && frozen.semantic ? "page" :
    searching || Object.values(filters).some(value => value !== undefined) || currentScope.status !== "all" ? "filtered" : "all");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [duplicateId, setDuplicateId] = useState<number | null>(null);
  const [pendingWrite, setPendingWrite] = useState<LibraryOperation | null>(action.kind === "recover" ? action.operation : null);
  const [rejectedWrite, setRejectedWrite] = useState(false);
  const pendingRef = useRef(pendingWrite), submitGate = useRef(false);
  const savedResult = useRef<LibraryReceipt["result"] | null>(null);
  const [storageWarning, setStorageWarning] = useState(false);
  const foldersId = useId();
  const returnFocus = useRef(document.activeElement?.closest(".library-manage")?.querySelector("summary") || document.activeElement as HTMLElement | null);
  const ids = "ids" in action ? action.ids : undefined;
  // The parent passes a fresh array each render (a 4 s poll re-renders it), so
  // the effect key is the content, not the identity, or the preview refetches
  // on every poll while the dialog is open.
  const idsKey = JSON.stringify(ids ?? null);
  const processing = action.kind === "process" || (action.kind === "bulk" && operation === "fetch");
  const mode = action.kind === "process" ? action.mode : operation;
  const force = processing && (action.kind === "process" ? action.reprocess ?? Boolean(ids?.length) : Boolean(ids?.length));
  const [processTarget, setProcessTarget] = useState("current");
  const processScope = action.kind === "process" ? processTarget === "all" ? {} : processTarget === "current" ? action.scope
    : { ...action.scope, status: processTarget as "pending" | "failed" } : undefined;
  const processScopeKey = JSON.stringify(processScope);
  const [targetCount, setTargetCount] = useState<number | null>(null);
  const [previewRevision, setPreviewRevision] = useState("");
  const [countError, setCountError] = useState("");
  useEffect(() => {
    if (!processing) return;
    const abort = new AbortController();
    setTargetCount(null); setCountError("");
    api<{ total: number; revision: string }>("/admin/jobs/preview", { method: "POST",
      body: JSON.stringify({ mode, bookmark_ids: ids, scope: processScope, force }), signal: abort.signal, timeoutMs: 20_000 })
      .then(data => { if (!abort.signal.aborted) { setTargetCount(data.total); setPreviewRevision(data.revision); } }).catch(e => { if (!abort.signal.aborted) setCountError(String(e)); });
    return () => abort.abort();
  }, [processing, mode, idsKey, processScopeKey, force]);
  const deleting = action.kind === "delete" || (action.kind === "bulk" && operation === "delete");
  const chatReady = Boolean(setup?.demo || setup?.channels.chat.tested);
  const needsConsent = deleting || action.kind === "taxonomy";
  const heading = action.kind === "create" ? t("新增收藏", "Add a bookmark")
    : action.kind === "edit" ? t("编辑收藏", "Edit bookmark")
    : action.kind === "delete" ? t("删除收藏", "Delete bookmarks")
    : action.kind === "bulk" ? t("批量管理", "Manage selected bookmarks")
    : action.kind === "taxonomy" ? t("整理文件夹与标签", "Organize folders and tags")
    : action.kind === "export" ? t("导出收藏", "Export bookmarks")
    : action.kind === "recover" ? t("恢复收藏操作", "Recover collection operation")
    : mode === "fetch" ? t("提取网页正文", "Fetch page text") : t("生成 AI 摘要", "Generate AI summaries");
  const resetConfirm = (value: string) => { setOperation(value); setConfirmed(false); };

  const keepWrite = (value: LibraryOperation | null, requestId: string) => {
    pendingRef.current = value; setPendingWrite(value);
    setStorageWarning(!onPending(value, requestId));
  };
  async function finishWrite(snapshot: LibraryOperation, result: LibraryReceipt["result"]) {
    savedResult.current = result;
    keepWrite({ ...snapshot, confirmed: true }, snapshot.requestId);
    try {
      await onChanged(result.deleted ? result.ids : undefined);
      keepWrite(null, snapshot.requestId); setOpen(false);
    } catch (failure) {
      setError(t("收藏已保存，但暂时无法更新收藏状态。", "Your changes were saved, but the collection status could not be updated.") + " " + String(failure));
    }
  }
  async function receipt(snapshot: LibraryOperation) {
    const value = await api<LibraryReceipt>("/admin/library/operations/" + encodeURIComponent(snapshot.requestId));
    if (value.request_id !== snapshot.requestId || value.action !== libraryRequest(snapshot).action || !validWriteResult(value.result, snapshot.change))
      throw new Error(t("读取到的结果与原操作不一致，请重新读取。", "This result does not match the original operation. Reload it."));
    return value.result;
  }
  async function readWrite() {
    const snapshot = pendingRef.current;
    if (!snapshot || submitGate.current) return;
    submitGate.current = true; setBusy(true); setError("");
    try { await finishWrite(snapshot, snapshot.confirmed && savedResult.current ? savedResult.current : await receipt(snapshot)); }
    catch (failure) {
      setError(failure instanceof ApiError && failure.status === 404 && !snapshot.confirmed
        ? t("暂时没有找到已保存的结果。可以重试原来的操作，内容和选择会保持一致。", "No saved result was found. Retry the original operation with the same content and selection.") : String(failure));
    } finally { submitGate.current = false; setBusy(false); }
  }
  async function write(snapshot: LibraryOperation) {
    if (submitGate.current || snapshot.confirmed) return;
    submitGate.current = true; setBusy(true); setError(""); setDuplicateId(null); setRejectedWrite(false);
    keepWrite(snapshot, snapshot.requestId);
    try {
      const request = libraryRequest(snapshot);
      let result: LibraryReceipt["result"];
      try {
        result = await api<LibraryReceipt["result"]>(request.path, { method: request.method, body: JSON.stringify(request.body) });
        if (!validWriteResult(result, snapshot.change)) throw new ApiError(200, t("暂时无法读取保存结果，请重新读取。", "The save result could not be read. Reload it."));
      }
      catch (failure) {
        setError(String(failure));
        const duplicate = failure instanceof ApiError ? failure.details?.bookmark_id : undefined;
        if (typeof duplicate === "number" && Number.isSafeInteger(duplicate) && duplicate > 0) setDuplicateId(duplicate);
        try { result = await receipt(snapshot); }
        catch (readFailure) {
          if (failure instanceof ApiError && failure.status >= 400 && failure.status < 500 && failure.status !== 408
            && readFailure instanceof ApiError && readFailure.status === 404) {
            if (action.kind === "recover") setRejectedWrite(true);
            else keepWrite(null, snapshot.requestId);
          }
          return;
        }
      }
      await finishWrite(snapshot, result);
    } finally { submitGate.current = false; setBusy(false); }
  }

  async function restoreDraft() {
    const snapshot = pendingRef.current;
    if (!snapshot || !rejectedWrite || submitGate.current) return;
    submitGate.current = true; setBusy(true); setError("");
    try {
      const change = structuredClone(snapshot.change);
      let restored: LibraryAction;
      if (change.kind === "create") restored = { kind: "create", values: change.values };
      else if (change.kind === "edit") {
        try {
          const record = await api<Bookmark>(`/bookmark/${change.bookmarkId}?body=true`);
          if (record.bookmark_id !== change.bookmarkId) throw new Error(t("无法确认这条收藏，请重新读取。", "This bookmark could not be confirmed. Reload it."));
          restored = { kind: "edit", record, values: change.values };
        } catch (failure) {
          if (!(failure instanceof ApiError && failure.status === 404)) throw failure;
          restored = { kind: "create", values: snapshot.draft ?? { url: change.values.url ?? "", title: change.values.title ?? "",
            folder: change.values.folder ?? "", tags: change.values.tags ?? [] },
          notice: t("原来的收藏已移除，你修改的内容仍保留。确认内容后可以另存为新收藏。", "The original bookmark was removed. Your edits are retained; review them before saving as a new bookmark.") };
        }
      } else if (change.kind === "bulk") restored = { kind: "bulk", ids: change.ids, initial: change };
      else restored = { kind: "taxonomy", initial: change };
      keepWrite(null, snapshot.requestId);
      onRestoreDraft(restored);
    } catch (failure) { setError(String(failure)); }
    finally { submitGate.current = false; setBusy(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!open || busy || submitGate.current || pendingRef.current || (running && action.kind !== "export") || (needsConsent && !confirmed) || (action.kind === "taxonomy" && !name.trim())) return;
    let change: LibraryChange | null = null;
    let draftValues: BookmarkValues | undefined;
    if (action.kind === "create" || action.kind === "edit") {
      const values = { url: url.trim(), title: title.trim(), folder: folder.trim(), tags: [...tags] };
      if (action.kind === "create") change = { kind: "create", values };
      else {
        draftValues = values;
        const changed = Object.fromEntries(Object.entries(values).filter(([key, value]) => JSON.stringify(value) !== JSON.stringify(action.record[key as keyof Bookmark] ?? (key === "tags" ? [] : ""))));
        if (Object.keys(changed).length) change = { kind: "edit", bookmarkId: action.record.bookmark_id, values: changed };
        else { setOpen(false); return; }
      }
    } else if (action.kind === "delete") change = { kind: "bulk", ids: [...action.ids], action: "delete" };
    else if (action.kind === "bulk" && !processing) change = { kind: "bulk", ids: [...action.ids], action: operation as "move" | "tag-add" | "tag-remove" | "delete",
      ...(operation === "move" ? { folder: folder.trim() } : ["tag-add", "tag-remove"].includes(operation) ? { tags: [...tags] } : {}) };
    else if (action.kind === "taxonomy") change = { kind: "taxonomy", kindOfName: taxonomy as "folder" | "tag", action: taxonomyAction as "rename" | "delete",
      name: name.trim(), ...(taxonomyAction === "rename" ? { newName: newName.trim() } : {}) };
    if (change) { await write({ version: 1, requestId: crypto.randomUUID(), createdAt: Date.now(), confirmed: false, change,
      ...(draftValues ? { draft: draftValues } : {}) }); return; }
    submitGate.current = true;
    setBusy(true); setError("");
    try {
      if (action.kind === "export") {
        await downloadExport(exportRequest(frozen, scope, format));
      } else if (processing) {
        await onTask({ kind: "start", values: { mode: mode as "fetch" | "summarize", ...(ids ? { bookmark_ids: [...ids] } : {}),
          confirmed: confirmed || mode === "summarize", force, scope: processScope, preview_revision: previewRevision } });
      }
      setOpen(false);
    } catch (e) { setError(String(e)); } finally { submitGate.current = false; setBusy(false); }
  }

  return <Dialog.Root open={open} onOpenChange={value => { if (!value && !busy && !submitGate.current) setOpen(false); }}><Dialog.Portal forceMount>
    <AnimatePresence onExitComplete={onClose}>
    {open && <Dialog.Overlay forceMount asChild key="overlay"><OverlayMotion kind="scrim" className="library-dialog-overlay"/></Dialog.Overlay>}
    {open && <Dialog.Content forceMount asChild key="content" onCloseAutoFocus={e => { e.preventDefault(); requestAnimationFrame(() => { const target = returnFocus.current?.isConnected && !(returnFocus.current as HTMLButtonElement).disabled ? returnFocus.current : document.querySelector<HTMLElement>(".library-tools button:not(:disabled), .app-header button:not(:disabled), .workspace-search input"); target?.focus({ preventScroll: true }); }); }} onEscapeKeyDown={e => { if (e.target instanceof Element && e.target.closest('.folder-picker[data-open="true"]')) { e.preventDefault(); return; } e.stopPropagation(); if (busy || submitGate.current) e.preventDefault(); }} onInteractOutside={e => { if (busy || submitGate.current) e.preventDefault(); }}>
      <OverlayMotion kind="dialog" className="library-dialog" aria-busy={busy}>
      <div className="library-dialog-heading"><Dialog.Title>{heading}</Dialog.Title><Dialog.Close className="icon-button" disabled={busy} aria-label={t("关闭操作窗口", "Close actions")}><X size={18}/></Dialog.Close></div>
      <Dialog.Description className="library-dialog-description">{action.kind === "export" ? t("JSON 副本保留分类、标签、正文、AI 阅读内容和所选范围内的对话，导入时补齐缺失内容；已有本地副本优先。模型密钥和向量不在副本内。", "JSON copies preserve folders, tags, page text, AI reading content and conversations wholly within the export scope. Import fills missing content and keeps existing local copies. Model keys and vectors are excluded.") : t("管理 Facetmark 中的收藏，浏览器中的原始书签保持原样。", "Manage your Facetmark collection. Original browser bookmarks stay untouched.")}</Dialog.Description>
      <form onSubmit={submit} className="library-dialog-form">
        <div className="library-dialog-body">
        <fieldset disabled={busy || Boolean(pendingWrite)}>
          {action.kind === "recover" && <OperationSummary change={action.operation.change}/>}
          {(action.kind === "create" || action.kind === "edit") && <>
            <label className="field">{t("网址", "URL")}<input aria-label={t("收藏网址", "Bookmark URL")} type="url" required value={url} maxLength={8192} onChange={e => setUrl(e.target.value)} placeholder="https://" autoComplete="url"/></label>
            <label className="field">{t("标题", "Title")}<input aria-label={t("收藏标题", "Bookmark title")} value={title} maxLength={2048} onChange={e => setTitle(e.target.value)}/></label>
            <FolderPicker label={t("收藏文件夹", "Bookmark folder")} value={folder} onChange={setFolder}/>
            <label className="field-label">{t("标签", "Tags")}</label><TagEditor tags={tags} onChange={setTags}/>
            {action.kind === "edit" && <p className="hint">{t("修改网址会清除旧网页正文与索引；修改标题后需重新生成 AI 内容。整理文件夹和标签会保留现有正文与摘要。", "Changing the URL clears old text and indexes. Title changes require generating new AI content. Folder and tag changes preserve saved text and summaries.")}</p>}
          </>}
          {action.kind === "bulk" && <>
            <p>{t(`将操作选中的 ${action.ids.length} 条收藏。`, `Applies to ${action.ids.length} selected bookmarks.`)}</p>
            <label className="field">{t("操作", "Action")}<select value={operation} onChange={e => resetConfirm(e.target.value)} aria-label={t("批量操作类型", "Bulk action")}>
              <option value="move">{t("移动到文件夹", "Move to folder")}</option><option value="tag-add">{t("添加标签", "Add tags")}</option><option value="tag-remove">{t("移除标签", "Remove tags")}</option><option value="fetch">{t("提取正文", "Fetch text")}</option><option value="delete">{t("删除收藏", "Delete bookmarks")}</option>
            </select></label>
            {operation === "move" && <FolderPicker label={t("目标文件夹", "Destination folder")} value={folder} onChange={setFolder}/>}
            {["tag-add", "tag-remove"].includes(operation) && <TagEditor tags={tags} onChange={setTags}/>}
          </>}
          {action.kind === "taxonomy" && <>
            <div className="library-form-pair"><label className="field">{t("整理对象", "Organize")}<select value={taxonomy} onChange={e => { setTaxonomy(e.target.value); setName(""); setConfirmed(false); }}><option value="folder">{t("文件夹", "Folders")}</option><option value="tag">{t("标签", "Tags")}</option></select></label>
            <label className="field">{t("操作", "Action")}<select value={taxonomyAction} onChange={e => { setTaxonomyAction(e.target.value); setConfirmed(false); }}><option value="rename">{t("重命名或合并", "Rename or merge")}</option><option value="delete">{t("移除分类", "Remove category")}</option></select></label></div>
            {taxonomy === "folder" ? <FolderPicker label={t("当前文件夹", "Current folder")} value={name} onChange={value => { setName(value); setConfirmed(false); }} allowCreate={false} allowUnfiled={false}/>
              : <label className="field">{t("当前名称", "Current name")}<input required value={name} maxLength={128} list={`${foldersId}-taxonomy`} onChange={e => { setName(e.target.value); setConfirmed(false); }}/></label>}
            <datalist id={`${foldersId}-taxonomy`}>{(facets.tags || []).map(item => <option key={item.value} value={item.value}/>)}</datalist>
            {taxonomyAction === "rename" && <label className="field">{t("新名称", "New name")}<input required value={newName} maxLength={taxonomy === "tag" ? 128 : 2048} onChange={e => { setNewName(e.target.value); setConfirmed(false); }}/></label>}
            <p className="hint">{t("作用于书库中所有使用该名称的收藏。移除文件夹会把其中收藏移到未分类；移除标签只解除标签关联，不删除收藏。目标名称已存在时会合并。", "Applies to all bookmarks with this exact name. Removing a folder unfiles its bookmarks; removing a tag removes only that label. An existing destination is merged.")}</p>
          </>}
          {action.kind === "export" && <>
            <label className="field">{t("导出范围", "Scope")}<select value={scope} onChange={e => setScope(e.target.value)}>
              <option value="all">{t("整个书签库", "Entire library")}</option>
              <option value="filtered" disabled={searching && frozen.semantic}>{t("当前筛选和搜索结果", "Current filters and search results")}</option>
              <option value="page" disabled={!frozen.pageIds.length}>{t("打开窗口时的本页结果", "This page when the dialog opened")}</option>
              <option value="selected" disabled={!frozen.selectedCount}>{t(`已选择的 ${frozen.selectedCount.toLocaleString()} 条`, `${frozen.selectedCount.toLocaleString()} selected bookmarks`)}</option>
            </select></label>
            <label className="field">{t("文件格式", "Format")}<select value={format} onChange={e => setFormat(e.target.value)}><option value="json">JSON · {t("书签、正文与摘要", "Bookmarks, saved text and summaries")}</option><option value="html">HTML · {t("导入浏览器", "Import into a browser")}</option></select></label>
            <p className="hint">{t("JSON 可恢复收藏、已保存的正文、摘要和范围内的对话；已有本地内容优先。向量索引需重新建立。HTML 只导出书签信息；含逗号的标签请用 JSON 保留。", "JSON restores bookmarks, saved text, summaries and in-scope conversations, keeping existing local content. Vector indexes must be rebuilt. HTML contains bookmark metadata only. Use JSON to preserve tags containing commas.")}</p>
            {searching && frozen.semantic && <p className="hint">{t("语义搜索按已加载的结果导出，请选择当前页或已选择的收藏。", "Export semantic search from the loaded results using this page or your selected bookmarks.")}</p>}
          </>}
          {processing && <>
            {!ids && action.kind === "process" && <label className="field">{mode === "summarize" ? t("摘要处理范围", "Summary scope") : t("正文抓取范围", "Page fetch scope")}<select aria-label={mode === "summarize" ? t("摘要处理范围", "Summary scope") : t("正文抓取范围", "Page fetch scope")} value={processTarget}
              onChange={event => { setProcessTarget(event.target.value); setConfirmed(false); setTargetCount(null); }}>
              <option value="current">{action.scopeLabel || t("当前范围", "Current scope")}</option>
              {mode === "summarize" && <><option value="pending">{t("当前未生成", "Pending in current scope")}</option><option value="failed">{t("当前失败重试", "Failures in current scope")}</option></>}
              <option value="all">{t("整个书签库", "Entire library")}</option>
            </select></label>}
            <p>{ids ? t(`处理选中的 ${ids.length} 条收藏。`, `Process ${ids.length} selected bookmarks.`)
              : processTarget === "all" ? t("整个书签库", "Entire library")
              : [processScope?.folder, processScope?.tag, processScope?.domain, processScope?.q].filter(Boolean).join(" · ") || t("处理当前范围中符合条件的收藏。", "Process eligible bookmarks in the selected scope.")}</p>
            <p className="hint">{mode === "fetch" ? t("会访问收藏的网址以提取正文，不调用 AI 模型。受隐私排除或访问限制的页面会跳过或记录失败。", "Visits the saved websites to fetch text without calling AI. Privacy-excluded or inaccessible pages are skipped or reported.") : t("标题、网址、文件夹和已有正文会发送给已配置的聊天模型；不要求向量模型。未保存正文时会明确标注基于标题推断。", "Sends titles, URLs, folders and saved text to your chat model. No embedding model is needed. Missing text is labeled as title-based inference.")}</p>
            {mode === "summarize" && !chatReady && <p role="alert" className="error">{t("请先在设置中配置并测试聊天模型。", "Configure and test the chat model in Settings first.")}</p>}
            {countError ? <p className="error" role="alert">{countError}</p> : <p className="processing-count" role="status">{targetCount === null ? t("正在计算处理范围…", "Counting eligible bookmarks…") : <>
              {t(`本次将处理 ${targetCount.toLocaleString()} 条。`, `${targetCount.toLocaleString()} eligible bookmarks. `)}
              {force ? t("包括已完成且未变化的内容，将重新处理。", "Includes completed, unchanged content for reprocessing.")
                : t("已完成且未变化的内容会跳过。", "Completed, unchanged content is skipped.")}
            </>}</p>}
            <p className="hint">{t("任务可暂停，重启后可继续。无需逐条打开书签。", "Pause and resume after restarting. No need to open bookmarks individually.")}</p>
          </>}
          {deleting && <p className="deletion-note"><Trash2 size={18}/>{t(`将删除 ${ids?.length || 0} 条收藏，以及它们在 Facetmark 中的正文和索引。此操作无法撤销，建议先导出备份。`, `Delete ${ids?.length || 0} bookmarks and their Facetmark text and indexes. This cannot be undone; export a backup first.`)}</p>}
          {needsConsent && <label className="check consent"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>{deleting ? t("我确认删除这些收藏", "I confirm deletion") : t("我确认应用到使用该分类的全部收藏", "Apply to all bookmarks using this category")}</label>}
        </fieldset>
        {action.kind === "create" && action.notice && <p className="notice" role="status">{action.notice}</p>}
        {error && <p className="error" role="alert">{error}</p>}
        {duplicateId !== null && <CapsuleButton type="button" className="secondary library-open-existing" disabled={busy} onClick={() => { setOpen(false); onPreview(duplicateId); }}><BookOpen size={16}/>{t("打开已有收藏", "Open saved bookmark")}</CapsuleButton>}
        {pendingWrite && <div className="library-write-recovery" role="status"><p>{pendingWrite.confirmed
          ? t("这次操作已经保存。重新读取收藏状态即可，不会重复修改收藏。", "This operation was saved. Reload the collection status to continue.")
          : rejectedWrite ? t("这次操作未保存。可以恢复原来的内容和选择，修改后再提交。", "This operation was not saved. Restore its original content and selection, then edit before submitting.")
          : t("这次操作的结果尚未确认。先读取已保存的结果，或重试同一次操作；原来的内容和选择会保持一致。", "This operation has not been confirmed. Read the saved result or retry the same operation with its original content and selection.")}</p></div>}
        {storageWarning && <p className="notice" role="status">{t("恢复记录暂时无法保存到本机，请保留当前窗口。", "The recovery record could not be saved on this device. Keep this window open.")}</p>}
        {running && action.kind !== "export" && !pendingWrite && <p className="notice">{t("请等待当前任务完成，再修改收藏或启动新任务。", "Wait for the current task before editing or starting another task.")}</p>}
        </div>
        <div className="library-dialog-footer"><CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => setOpen(false)}>{pendingWrite ? t("稍后处理", "Continue later") : t("取消", "Cancel")}</CapsuleButton>
        {pendingWrite ? <>
          <CapsuleButton type="button" className="primary" disabled={busy} onClick={() => void readWrite()}><RotateCcw size={16}/>{pendingWrite.confirmed ? t("重新读取收藏", "Reload collection") : t("读取保存结果", "Read saved result")}</CapsuleButton>
          {!pendingWrite.confirmed && (rejectedWrite
            ? <CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => void restoreDraft()}>{t("修改原操作", "Edit original operation")}</CapsuleButton>
            : <CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => void write(pendingWrite)}>{t("重试同一次操作", "Retry this operation")}</CapsuleButton>)}
        </> : <CapsuleButton className={`primary ${deleting ? "danger-action" : ""}`} disabled={busy || (running && action.kind !== "export") || (needsConsent && !confirmed) || (action.kind === "taxonomy" && !name.trim()) || (processing && ((mode === "summarize" && !chatReady) || targetCount === null || targetCount === 0 || !!countError)) || (action.kind === "bulk" && ["tag-add", "tag-remove"].includes(operation) && !tags.length)}>
          {busy ? <LoaderCircle size={16} className="spin"/> : deleting ? <Trash2 size={16}/> : <Check size={16}/>}{busy ? t("正在处理…", "Working…") : action.kind === "export" ? t("下载导出文件", "Download export") : processing ? t("开始任务", "Start task") : deleting ? t("确认删除", "Delete bookmarks") : t("保存", "Save")}
        </CapsuleButton>}</div>
      </form>
      </OverlayMotion>
    </Dialog.Content>}
    </AnimatePresence>
  </Dialog.Portal></Dialog.Root>;
}
