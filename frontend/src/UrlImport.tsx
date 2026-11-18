import { useEffect, useId, useRef, useState } from "react";
import { ArrowRight, Check, ChevronDown, History, Link, LoaderCircle, RefreshCw, X } from "lucide-react";
import { api, ApiError, post, safeUrl } from "./api";
import { FolderPicker } from "./FolderPicker";
import { useText } from "./locale";
import { CapsuleButton } from "./ui/controls";
import "./url-import.css";

type UrlItem = { line: number; url: string; title: string; status: string; bookmark_id?: number };
type UrlPreview = { items: UrlItem[]; counts: Record<string, number>; revision: string };
type UrlReport = { parsed: number; inserted: number; merged_duplicates: number; skipped: number; items: UrlItem[]; import_id: string };
type UrlApply = { text: string; folder: string; revision: string; request_id: string };
function savedDraft() {
  try {
    const value = JSON.parse(sessionStorage.getItem("fm-url-import-draft") || "null");
    if (typeof value?.text === "string" && value.text.length <= 2_000_000 && typeof value.folder === "string" && value.folder.length <= 2048)
      return value as { text: string; folder: string };
  } catch { /* Draft storage is optional. */ }
  return { text: "", folder: "" };
}

function UrlItems({ items }: { items: UrlItem[] }) {
  const t = useText();
  const [visible, setVisible] = useState(50);
  useEffect(() => setVisible(50), [items]);
  const label: Record<string, string> = { new: t("将导入", "Will import"), existing: t("已在收藏中", "Already saved"),
    duplicate: t("本批重复", "Duplicate in batch"), invalid: t("网址无效", "Invalid URL"), imported: t("已导入", "Imported") };
  return <>
    <ol className="url-import-items">{items.slice(0, visible).map(item => {
      const href = item.status !== "invalid" ? safeUrl(item.url) : undefined;
      return <li key={item.line} data-status={item.status}>
      <span className="url-import-line">{item.line}</span>
      <span className="url-import-state">{item.status === "imported" ? <Check size={15}/> : item.status === "invalid" ? <X size={15}/> : null}{label[item.status] || item.status}</span>
      <div className="url-import-address">{href
        ? <a className="url-import-title" href={href} target="_blank" rel="noreferrer">{item.title || item.url}</a>
        : <span className="url-import-title">{item.title || item.url}</span>}
        {item.title && <small>{item.url}</small>}
        <details className="url-import-details">
          <summary>{t("完整标题与网址", "Full title and URL")}<ChevronDown size={14} aria-hidden="true"/></summary>
          <dl className="url-import-full">
            {item.title && <div><dt>{t("标题", "Title")}</dt><dd>{item.title}</dd></div>}
            <div><dt>{t("网址", "URL")}</dt><dd>{item.url}</dd></div>
          </dl>
        </details>
      </div>
    </li>;
    })}</ol>
    {visible < items.length && <CapsuleButton className="text-button" type="button" onClick={() => setVisible(value => value + 50)}>
      {t("显示更多", "Show more")} ({Math.min(visible, items.length)} / {items.length})
    </CapsuleButton>}
  </>;
}

export function UrlImport({ refresh, onDone, disabled = false, onActiveChange }: {
  refresh: () => Promise<void>; onDone?: () => void; disabled?: boolean; onActiveChange?: (active: boolean) => void;
}) {
  const t = useText(), id = useId();
  const [draft, setDraft] = useState(savedDraft), [candidate, setCandidate] = useState<UrlPreview | null>(null);
  const [report, setReport] = useState<UrlReport | null>(null), [busy, setBusy] = useState("");
  const [error, setError] = useState(""), [needsRefresh, setNeedsRefresh] = useState(false);
  const gate = useRef(false), mounted = useRef(true), previewRequest = useRef<AbortController | null>(null);
  const lastApply = useRef<UrlApply | null>(null);
  useEffect(() => { onActiveChange?.(!!busy); return () => onActiveChange?.(false); }, [busy, onActiveChange]);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; previewRequest.current?.abort(); }; }, []);
  useEffect(() => { try { sessionStorage.setItem("fm-url-import-draft", JSON.stringify(draft)); } catch { /* Optional. */ } }, [draft]);
  function change(value: Partial<typeof draft>) {
    if (gate.current || disabled) return;
    setDraft(old => ({ ...old, ...value })); setCandidate(null); setReport(null); setError(""); setNeedsRefresh(false); lastApply.current = null;
  }
  async function inspect() {
    if (gate.current || disabled) return;
    gate.current = true; setBusy("preview"); setError(""); setReport(null); setNeedsRefresh(false);
    const request = new AbortController(); previewRequest.current = request;
    try {
      const value = await api<UrlPreview>("/admin/import/urls/preview", { method: "POST", body: JSON.stringify(draft), signal: request.signal, timeoutMs: 20_000 });
      if (mounted.current) {
        setCandidate(value);
        lastApply.current = { ...draft, revision: value.revision, request_id: crypto.randomUUID() };
      }
    } catch (failure) { if (mounted.current && !request.signal.aborted) setError(failure instanceof Error ? failure.message : String(failure)); }
    finally { gate.current = false; if (mounted.current) setBusy(""); }
  }
  async function importUrls() {
    if (gate.current || disabled || !lastApply.current) return;
    gate.current = true; setBusy("apply"); setError("");
    let received = false;
    try {
      const value = await post<UrlReport>("/admin/import/urls", lastApply.current);
      received = true;
      if (mounted.current) { setReport(value); setCandidate(null); }
      await refresh();
      if (mounted.current) setNeedsRefresh(false);
    } catch (failure) {
      if (mounted.current) {
        setNeedsRefresh(received);
        if (!received && failure instanceof ApiError && failure.status === 409) {
          setCandidate(null); lastApply.current = null;
          setError(t("收藏库已变化，请重新预览。输入内容已保留。", "The library changed. Preview again; your input is retained."));
        } else setError(received ? t("网址已导入，但收藏列表未能刷新。请重新读取收藏。", "URLs were imported, but the collection could not refresh. Reload it.")
          : failure instanceof Error ? failure.message : String(failure));
      }
    } finally { gate.current = false; if (mounted.current) setBusy(""); }
  }
  async function reload() {
    if (gate.current) return;
    gate.current = true; setBusy("reload");
    try { await refresh(); if (mounted.current) { setNeedsRefresh(false); setError(""); } }
    catch { if (mounted.current) setError(t("收藏列表仍未能刷新，请重试。", "The collection still could not refresh. Retry.")); }
    finally { gate.current = false; if (mounted.current) setBusy(""); }
  }
  return <details className="url-import">
    <summary><Link size={18}/><span>{t("批量粘贴网址", "Paste multiple URLs")}</span><ChevronDown size={16} className="import-section-chevron" aria-hidden="true"/></summary>
    <p id={id + "-hint"}>{t("每行一个完整网址，最多 500 条。先预览再导入，已有收藏会保留；这一步不会抓取网页或调用 AI。", "Paste one complete URL per line, up to 500. Preview before importing. Existing bookmarks are kept; this step does not fetch pages or call AI.")}</p>
    <form onSubmit={event => { event.preventDefault(); void inspect(); }} aria-busy={!!busy}>
      <label className="url-import-input">{t("网址列表", "URL list")}
        <textarea value={draft.text} maxLength={2_000_000} rows={6} aria-describedby={id + "-hint"} disabled={disabled || !!busy}
          placeholder={"https://example.com/article\nhttps://example.org/guide"} onChange={event => change({ text: event.target.value })}/>
      </label>
      <FolderPicker label={t("导入到文件夹", "Import into folder")} value={draft.folder} onChange={folder => change({ folder })} disabled={disabled || !!busy}/>
      <div className="url-import-actions">
        <CapsuleButton type="submit" className="secondary" disabled={disabled || !!busy || !draft.text.trim()}>
          {busy === "preview" && <LoaderCircle size={16} className="spin"/>}{t("预览网址", "Preview URLs")}
        </CapsuleButton>
        {candidate && <CapsuleButton type="button" className="primary" disabled={disabled || !!busy || !candidate.counts.new} onClick={() => void importUrls()}>
          {t("导入 " + candidate.counts.new + " 条新网址", "Import " + candidate.counts.new + " new URLs")}<ArrowRight size={16}/>
        </CapsuleButton>}
        {busy === "apply" && <span role="status"><LoaderCircle size={16} className="spin"/>{t("正在导入网址…", "Importing URLs…")}</span>}
      </div>
    </form>
    {candidate && <section className="url-import-preview" aria-label={t("网址预览", "URL preview")}>
      <p role="status">{t("将添加 " + candidate.counts.new + " 条；已存在 " + candidate.counts.existing + " 条；本批重复 " + candidate.counts.duplicate + " 条；无效 " + candidate.counts.invalid + " 条。",
        "Will add " + candidate.counts.new + "; already saved " + candidate.counts.existing + "; batch duplicates " + candidate.counts.duplicate + "; invalid " + candidate.counts.invalid + ".")}</p>
      <UrlItems items={candidate.items}/>
    </section>}
    {report && <section className="url-import-result" aria-label={t("网址导入结果", "URL import result")}>
      <p role="status"><Check size={17}/>{t("已添加 " + report.inserted + " 条网址，跳过 " + report.merged_duplicates + " 条重复和 " + report.skipped + " 条无效网址。",
        "Added " + report.inserted + " URLs. Skipped " + report.merged_duplicates + " duplicates and " + report.skipped + " invalid URLs.")}</p>
      <UrlItems items={report.items}/>
      {onDone && <CapsuleButton type="button" className="primary" disabled={!!busy || needsRefresh} onClick={onDone}>{t("查看已导入的收藏", "View imported bookmarks")}<ArrowRight size={16}/></CapsuleButton>}
    </section>}
    {error && <div className="import-error" role="alert"><p className="error">{error}</p>
      {needsRefresh ? <CapsuleButton type="button" className="secondary" disabled={!!busy} onClick={() => void reload()}>{t("重新读取收藏", "Reload collection")}</CapsuleButton>
        : lastApply.current && !report && <CapsuleButton type="button" className="secondary" disabled={disabled || !!busy} onClick={() => void importUrls()}>{t("重试导入", "Retry import")}</CapsuleButton>}
    </div>}
  </details>;
}

type HistoryItem = { id: string; source: string; label: string; created_at: number; state: string; error: string; result: Partial<UrlReport> & { updated?: number; warnings?: string[]; pages_attempted?: number } };
type HistoryPage = { items: HistoryItem[]; offset: number; limit: number; has_more: boolean };
export function ImportHistory({ revision }: { revision: unknown }) {
  const t = useText();
  const [open, setOpen] = useState(false), [data, setData] = useState<HistoryPage | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [details, setDetails] = useState<Record<string, HistoryItem>>({}), [detailBusy, setDetailBusy] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [detailError, setDetailError] = useState<{ id: string; message: string } | null>(null);
  const pending = useRef<AbortController | null>(null), detailRequest = useRef<AbortController | null>(null);
  const nextOffset = useRef(0);
  async function load(offset = 0) {
    pending.current?.abort(); const request = new AbortController(); pending.current = request;
    nextOffset.current = offset; setBusy(true); setError("");
    try {
      const value = await api<HistoryPage>("/admin/import/history?limit=20&offset=" + offset, { signal: request.signal });
      if (!request.signal.aborted) setData(old => ({ ...value, items: offset === 0 ? value.items
        : [...new Map([...(old?.items || []), ...value.items].map(item => [item.id, item])).values()] }));
    } catch (failure) { if (!request.signal.aborted) setError(failure instanceof Error ? failure.message : String(failure)); }
    finally { if (!request.signal.aborted) setBusy(false); }
  }
  useEffect(() => {
    setDetails({}); setExpanded({}); setDetailBusy(""); setDetailError(null);
    if (open) void load(); else setBusy(false);
    return () => { pending.current?.abort(); detailRequest.current?.abort(); };
  }, [open, revision]);
  async function detail(identity: string) {
    if (detailBusy) return;
    if (details[identity]) { setExpanded(old => ({ ...old, [identity]: !old[identity] })); return; }
    const request = new AbortController(); detailRequest.current = request; setDetailBusy(identity); setDetailError(null);
    try {
      const value = await api<HistoryItem>("/admin/import/history/" + identity, { signal: request.signal });
      if (!request.signal.aborted) { setDetails(old => ({ ...old, [identity]: value })); setExpanded(old => ({ ...old, [identity]: true })); }
    } catch (failure) { if (!request.signal.aborted) setDetailError({ id: identity, message: failure instanceof Error ? failure.message : String(failure) }); }
    finally { if (!request.signal.aborted) setDetailBusy(""); }
  }
  const source: Record<string, string> = { urls: t("粘贴网址", "Pasted URLs"), file: t("导出文件", "Export file"), browser: t("浏览器来源", "Browser source"), site: t("网站导入", "Site import") };
  const states: Record<string, string> = { running: t("正在导入", "Importing"), failed: t("导入失败", "Import failed"),
    partial: t("有跳过或提醒", "Contains skips or notes"), cancelled: t("导入已停止", "Import stopped"),
    interrupted: t("导入已中断", "Import interrupted"), done: t("导入完成", "Import complete") };
  return <details className="import-history" aria-busy={busy || !!detailBusy} onToggle={event => setOpen(event.currentTarget.open)}>
    <summary><History size={18}/><span>{t("导入历史", "Import history")}</span><ChevronDown size={16} className="import-section-chevron" aria-hidden="true"/></summary>
    <div className="import-history-heading"><p>{t("在本机保留导入结果，方便重新查看新增、重复和失败原因。", "Import results stay on this machine so you can review additions, duplicates and failures.")}</p>
      <CapsuleButton type="button" className="text-button" disabled={busy} onClick={() => void load()}><RefreshCw size={16}/>{t("刷新记录", "Refresh history")}</CapsuleButton>
    </div>
    {busy && <p role="status"><LoaderCircle className="spin" size={16}/>{t("正在读取导入记录…", "Loading import history…")}</p>}
    {data && !data.items.length && !busy && <p>{t("还没有导入记录。下一次导入的结果会保存在这里。", "No import history yet. Your next import will be recorded here.")}</p>}
    <ol className="import-history-list">{data?.items.map(item => <li key={item.id}>
      <div className="import-history-title"><strong>{item.source === "urls" ? source.urls : item.label}</strong>
        <time dateTime={new Date(item.created_at * 1000).toISOString()}>{new Intl.DateTimeFormat(t("zh-CN", "en-US"), { dateStyle: "medium", timeStyle: "short" }).format(item.created_at * 1000)}</time></div>
      <p className="import-history-outcome">{source[item.source] || item.source} · {states[item.state] || item.state}
        {item.result.inserted !== undefined && " · " + t("新增 " + item.result.inserted, "Added " + item.result.inserted)}
        {!!item.result.updated && " · " + t("更新 " + item.result.updated, "Updated " + item.result.updated)}
        {!!item.result.merged_duplicates && " · " + t("重复 " + item.result.merged_duplicates, "Duplicates " + item.result.merged_duplicates)}</p>
      {item.error && <p className="error">{item.error}</p>}
      {item.result.warnings?.map((warning, index) => <p className="import-history-note" key={index}>{warning}</p>)}
      {item.source === "urls" && <CapsuleButton type="button" className="text-button" disabled={!!detailBusy}
        aria-expanded={!!expanded[item.id]} aria-controls={"import-items-" + item.id} onClick={() => void detail(item.id)}>
        {detailBusy === item.id && <LoaderCircle className="spin" size={15}/>}{expanded[item.id] ? t("收起逐项结果", "Hide item results")
          : detailError?.id === item.id ? t("重试读取逐项结果", "Retry item results") : t("查看逐项结果", "View item results")}</CapsuleButton>}
      {detailError?.id === item.id && <p className="error" role="alert">{detailError.message}</p>}
      {expanded[item.id] && details[item.id]?.result.items && <div id={"import-items-" + item.id}><UrlItems items={details[item.id].result.items!}/></div>}
    </li>)}</ol>
    {!error && data?.has_more && <CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => void load(data.offset + data.limit)}>{t("加载更早记录", "Load earlier imports")}</CapsuleButton>}
    {error && <div className="import-error" role="alert"><p className="error">{error}</p><CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => void load(nextOffset.current)}>{t("重试读取记录", "Retry history")}</CapsuleButton></div>}
  </details>;
}
