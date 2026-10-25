import { useEffect, useRef, useState } from "react";
import { ArrowRight, Globe, LoaderCircle, RefreshCw, Square } from "lucide-react";
import { api, post } from "./api";
import { CapsuleButton } from "./ui/controls";
import { useText } from "./locale";
import "./site-import.css";

type Options = { start_url: string; max_pages: number; same_domain: boolean };
type SiteJob = {
  id?: string; state: string; params?: Options; cancel_requested?: boolean; retryable?: boolean;
  current_url?: string; error?: string;
  report?: { pages_attempted: number; pages_fetched: number; inserted: number; already_known: number;
    bodies_stored: number; errors: number; skipped: number; robots_denied: number; privacy_skipped: number;
    off_domain_skipped: number; notes: string[] };
};
const defaults: Options = { start_url: "", max_pages: 25, same_domain: true };
function savedDraft(): Options {
  try {
    const value = JSON.parse(sessionStorage.getItem("fm-site-import-draft") || "null");
    return value && typeof value.start_url === "string" && typeof value.max_pages === "number"
      && typeof value.same_domain === "boolean" ? value : defaults;
  } catch { return defaults; }
}

export function SiteImport({ refresh, onDone }: { refresh: () => Promise<void>; onDone?: () => void }) {
  const t = useText();
  const [open, setOpen] = useState(false), [options, setOptions] = useState<Options>(savedDraft);
  const [job, setJob] = useState<SiteJob>({ state: "idle" });
  const [busy, setBusy] = useState(""), [loading, setLoading] = useState(false), [error, setError] = useState("");
  const gate = useRef(false), revision = useRef(0), request = useRef<AbortController | null>(null);
  const mounted = useRef(true), finished = useRef("");
  const running = job.state === "running";
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; request.current?.abort(); revision.current++; };
  }, []);
  useEffect(() => {
    try { sessionStorage.setItem("fm-site-import-draft", JSON.stringify(options)); } catch { /* Optional draft storage. */ }
  }, [options]);

  async function accept(value: SiteJob) {
    setJob(value);
    if (value.id && value.state !== "running" && finished.current !== value.id) {
      finished.current = value.id;
      try { await refresh(); } catch (failure) { if (mounted.current) setError(String(failure)); }
    }
  }
  async function load() {
    request.current?.abort();
    const pending = new AbortController(); request.current = pending;
    const version = ++revision.current; setLoading(true);
    try {
      const value = await api<SiteJob>("/admin/crawl", { signal: pending.signal });
      if (!pending.signal.aborted && version === revision.current) { setError(""); await accept(value); }
    } catch (failure) {
      if (!pending.signal.aborted && version === revision.current) setError(String(failure));
    } finally { if (!pending.signal.aborted && version === revision.current) setLoading(false); }
  }
  useEffect(() => { if (open) void load(); }, [open]);
  useEffect(() => {
    if (!open || !running || busy || loading) return;
    const timer = window.setTimeout(() => void load(), 1200);
    return () => window.clearTimeout(timer);
  }, [open, running, job, busy, loading]);

  async function run(kind: "start" | "stop", params = options) {
    if (gate.current) return;
    if (kind === "start") {
      try {
        const url = new URL(params.start_url);
        if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) throw new Error();
        if (!Number.isInteger(params.max_pages) || params.max_pages < 1 || params.max_pages > 500) throw new Error();
      } catch {
        setError(t("请输入有效的 HTTP(S) 网址，页数范围为 1–500。", "Enter a valid HTTP(S) URL and a page limit from 1 to 500."));
        return;
      }
    }
    gate.current = true; request.current?.abort(); revision.current++;
    setBusy(kind); setLoading(false); setError("");
    try {
      const value = await post<SiteJob>(kind === "start" ? "/admin/crawl" : "/admin/crawl/cancel", kind === "start" ? params : {});
      if (mounted.current) await accept(value);
    } catch (failure) { if (mounted.current) setError(String(failure)); }
    finally { gate.current = false; if (mounted.current) setBusy(""); }
  }
  const status = ({ idle: t("按需导入一个网站", "Import a site when needed"),
    running: t("正在导入网站…", "Importing site…"), done: t("网站扫描已完成", "Site scan complete"),
    partial: t("扫描完成，部分页面未能导入", "Scan complete; some pages could not be imported"),
    cancelled: t("导入已停止，已保存的页面仍可使用", "Import stopped; saved pages remain available"),
    interrupted: t("上次导入被中断，已保存的页面仍可使用", "Previous import interrupted; saved pages remain available"),
    failed: t("网站导入未完成", "Site import could not finish") } as Record<string, string>)[job.state] || job.state;
  const report = job.report;

  return <details className="site-import" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary><Globe size={18}/><span>{t("从网站导入页面", "Import pages from a site")}</span></summary>
    <p className="site-import-intro">{t("适合把一小段文档或文章目录加入收藏。默认最多扫描 25 页，只跟随同站点链接；会遵守抓取设置和隐私排除规则。", "Add a documentation section or article directory to your library. Scan up to 25 pages by default, follow links on the same site, and use your fetch settings and privacy exclusions.")}</p>
    <form className="site-import-form" onSubmit={event => { event.preventDefault(); void run("start"); }}>
      <label className="site-import-url">{t("起始网址", "Starting URL")}
        <input type="url" required placeholder="https://example.com/docs/" value={options.start_url}
          disabled={running || Boolean(busy)} onChange={event => setOptions(value => ({ ...value, start_url: event.target.value }))}/>
      </label>
      <label>{t("最多扫描页数", "Maximum pages to scan")}
        <input type="number" min={1} max={500} step={1} required value={options.max_pages}
          disabled={running || Boolean(busy)} onChange={event => setOptions(value => ({ ...value, max_pages: Number(event.target.value) }))}/>
      </label>
      <label className="check-row site-import-scope"><input type="checkbox" checked={options.same_domain}
        disabled={running || Boolean(busy)} onChange={event => setOptions(value => ({ ...value, same_domain: event.target.checked }))}/>
        {t("只跟随同站点链接", "Follow same-site links only")}</label>
      <div className="site-import-actions">
        {running ? <CapsuleButton type="button" className="secondary" disabled={Boolean(busy)} onClick={() => run("stop")}>
          {busy === "stop" ? <LoaderCircle className="spin" size={16}/> : <Square size={15}/>}
          {busy === "stop" ? t("正在停止…", "Stopping…") : t("停止网站导入", "Stop site import")}
        </CapsuleButton> : <CapsuleButton type="submit" className="primary" disabled={Boolean(busy) || loading}>
          {busy === "start" ? <LoaderCircle className="spin" size={16}/> : <Globe size={16}/>}
          {busy === "start" ? t("正在开始…", "Starting…") : t("开始网站导入", "Import site")}</CapsuleButton>}
        <CapsuleButton type="button" className="text-button" disabled={Boolean(busy) || loading} onClick={() => load()}>
          <RefreshCw size={15}/>{t("刷新状态", "Refresh status")}</CapsuleButton>
      </div>
    </form>
    <p className="site-import-note">{t("扫描页数包含失败或被拒绝的页面。后台任务会在离开页面后继续；停止会保留已导入内容。这里不会自动调用 AI，可稍后生成摘要。", "The page budget includes failed or denied pages. Import continues after you leave this view; Stop keeps pages already saved. Generate AI summaries later if needed.")}</p>
    <div className="site-import-result" role="status" aria-live="polite">
      <strong>{status}</strong>
      {running && job.params && <progress aria-label={t("网站导入进度", "Site import progress")}
        max={job.params.max_pages} value={report?.pages_attempted || 0}/>}
      {report && <dl>
        {[[t("已扫描", "Scanned"), report.pages_attempted], [t("已获取", "Fetched"), report.pages_fetched],
          [t("新增收藏", "Added"), report.inserted], [t("已有收藏", "Already saved"), report.already_known],
          [t("保存正文", "Page text saved"), report.bodies_stored], [t("获取失败", "Failed"), report.errors],
          [t("跳过或拒绝", "Skipped or denied"), report.skipped + report.robots_denied + report.privacy_skipped]].map(([label, count]) =>
          <div key={String(label)}><dt>{label}</dt><dd>{count}</dd></div>)}
      </dl>}
      {!running && job.retryable && job.params && <div className="site-import-rerun">
        <p>{t("重新导入会从起点扫描，并按网址去重，保留已有正文。", "Rerun scans from the starting URL, deduplicates pages, and preserves existing page text.")}</p>
        <CapsuleButton type="button" className="secondary" disabled={Boolean(busy)} onClick={() => run("start", job.params!)}>
          <RefreshCw size={15}/>{t("重新导入这个网站", "Rerun this site import")}</CapsuleButton>
      </div>}
      {!running && (report?.inserted || report?.bodies_stored) && onDone ? <CapsuleButton type="button" className="text-button" onClick={onDone}>
        {t("查看已导入的收藏", "View imported bookmarks")}<ArrowRight size={15}/></CapsuleButton> : null}
    </div>
    {(error || job.error) && <p className="error" role="alert">{error || job.error}</p>}
    {report?.notes?.length ? <details className="site-import-notes"><summary>{t("查看未导入原因", "Review import notes")}</summary>
      <ul>{report.notes.map((note, index) => <li key={index}>{note}</li>)}</ul></details> : null}
  </details>;
}
