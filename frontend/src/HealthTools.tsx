import { useEffect, useRef, useState } from "react";
import { ExternalLink, LoaderCircle, RefreshCw, ShieldCheck } from "lucide-react";
import { api, post, type Bookmark } from "./api";
import { useText } from "./locale";
import { CapsuleButton } from "./ui/controls";
import "./health-tools.css";

type HealthBookmark = Bookmark & { health?: { status: string; checked_at?: number | null; archive_url?: string } };
type HealthReport = {
  considered: number; probed: number; escalated: number; recovered_bodies: number;
  by_status: Record<string, number>; confirmed_gone: number[]; errors: string[];
};

export function HealthTools({ onPreview, disabled = false }: { onPreview?: (bookmarkId: number) => void; disabled?: boolean } = {}) {
  const t = useText();
  const [limit, setLimit] = useState(20), [busy, setBusy] = useState(false), [loading, setLoading] = useState(false);
  const [counts, setCounts] = useState<Record<string, number> | null>(null);
  const [dead, setDead] = useState<HealthBookmark[]>([]), [error, setError] = useState("");
  const [report, setReport] = useState<HealthReport | null>(null);
  const [checkedAt, setCheckedAt] = useState<number | null>(null);
  const gate = useRef(false), revision = useRef(0), request = useRef<AbortController | null>(null);
  useEffect(() => () => { request.current?.abort(); revision.current++; }, []);
  const label = (status: string) => ({
    unchecked: t("待检查", "Unchecked"), alive: t("可访问", "Reachable"),
    restricted: t("访问受限", "Restricted"), drifted: t("内容已变化", "Content changed"),
    soft_gone: t("内容疑似移除", "Content may be removed"), gone: t("疑似失效", "Appears gone"),
    unreachable: t("暂时无法连接", "Temporarily unreachable"), unknown: t("尚无结论", "Unknown"),
  } as Record<string, string>)[status] || t("尚无结论", "Unknown");

  async function load() {
    request.current?.abort();
    const pending = new AbortController(); request.current = pending;
    const current = ++revision.current; setLoading(true); setError("");
    const results = await Promise.allSettled([
      api<Record<string, number>>("/link-health/summary", { signal: pending.signal }),
      api<HealthBookmark[]>("/graveyard?limit=50", { signal: pending.signal }),
    ]);
    if (pending.signal.aborted || current !== revision.current) return;
    const errors = [];
    if (results[0].status === "fulfilled") setCounts(results[0].value);
    else errors.push(String(results[0].reason));
    if (results[1].status === "fulfilled") setDead(results[1].value);
    else errors.push(String(results[1].reason));
    setError(errors.join(" · ")); setLoading(false);
  }
  async function check() {
    if (gate.current || disabled) return;
    gate.current = true; setBusy(true); setError("");
    try {
      const result = await post<HealthReport>("/link-health/check", { limit });
      setReport(result); setCheckedAt(Date.now());
      await load();
    } catch (failure) { setError(String(failure)); }
    finally { gate.current = false; setBusy(false); }
  }

  return <details className="health-tools" onToggle={event => {
    if (event.currentTarget.open && !counts && !loading) void load();
  }}>
    <summary><ShieldCheck size={18}/><span>{t("链接健康检查", "Link health check")}</span></summary>
    <p className="health-intro">{t("查看已保存的链接状态，或检查到期的收藏。检查会访问原网址；仍会保留收藏和已保存的内容。",
      "Review saved link status or check bookmarks that are due. Checking visits their original URLs; bookmarks and saved content remain available.")}</p>
    <div className="health-actions">
      <label>{t("本次最多检查", "Check up to")}
        <select value={limit} disabled={busy || disabled} onChange={event => setLimit(Number(event.target.value))}
          aria-label={t("链接检查数量", "Link check limit")}>
          {[20, 50, 100, 500].map(value => <option key={value} value={value}>{value} {t("条", "links")}</option>)}
        </select>
      </label>
      <CapsuleButton type="button" className="secondary" disabled={busy || disabled} onClick={check}>
        {busy ? <LoaderCircle size={16} className="spin"/> : <ShieldCheck size={16}/>}
        {busy ? t("检查中…", "Checking…") : t("检查链接", "Check links")}
      </CapsuleButton>
      <CapsuleButton type="button" className="text-button" disabled={loading || busy} onClick={() => load()}>
        <RefreshCw size={15}/>{t("刷新已保存结果", "Refresh saved results")}
      </CapsuleButton>
    </div>
    {disabled && <p className="health-note">{t("当前处理任务结束后可以检查链接。", "Check links when the current processing task finishes.")}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {loading && !counts && <p className="health-note" role="status">{t("正在读取已保存的结果…", "Loading saved results…")}</p>}
    {counts && <div className="health-saved-summary">
      <h3>{t("已保存的检查结果", "Saved check results")}</h3>
      <dl className="health-counts" aria-label={t("保存的链接状态数量", "Saved link status counts")}>
        {Object.entries(counts).filter(([, count]) => count > 0).map(([status, count]) => <div key={status}>
          <dt>{label(status)}</dt><dd>{count.toLocaleString()}</dd>
        </div>)}
      </dl>
      {!Object.values(counts).some(value => value > 0) && <p className="health-note">{t("暂时没有可检查的收藏。", "There are no bookmarks to check yet.")}</p>}
    </div>}
    {report && <div className="health-latest" role="status">
      <h3>{t("本次检查", "This check")}{checkedAt && <time dateTime={new Date(checkedAt).toISOString()}>{new Date(checkedAt).toLocaleString(t("zh-CN", "en-US"))}</time>}</h3>
      <p>{report.probed ? t(`检查了 ${report.probed} 条链接`, `Checked ${report.probed} links`)
        : t("当前没有到期的链接，未重复访问近期已检查的页面。", "No links are due; recently checked pages were not visited again.")}
        {report.recovered_bodies > 0 && t(` · 找回 ${report.recovered_bodies} 条正文`, ` · Recovered page text for ${report.recovered_bodies}`)}</p>
      {Object.keys(report.by_status).length > 0 && <ul className="health-result-statuses">{Object.entries(report.by_status).map(([status, count]) => <li key={status}>{label(status)} <strong>{count}</strong></li>)}</ul>}
      {report.errors.length > 0 && <div className="health-errors" role="alert"><p>{t("部分检查未完成：", "Some checks could not finish:")}</p><ul>{report.errors.map((failure, index) => <li key={index}>{failure}</li>)}</ul></div>}
    </div>}
    {counts && <section className="health-confirmed-gone" aria-labelledby="confirmed-gone-heading">
      <h3 id="confirmed-gone-heading">{t("已确认失效的收藏", "Confirmed unavailable bookmarks")}</h3>
      <p className="health-note">{t("这里只列出多次确认的失效链接，最多显示 50 条。它们仍保留在收藏中，可以查看已保存内容。",
        "Only repeatedly confirmed unavailable links appear here, up to 50 at a time. They remain in your collection and their saved content can still be read.")}</p>
      {dead.length ? <ul className="health-bookmarks">{dead.map(record => <li key={record.bookmark_id}>
        <div><strong>{record.ai_title || record.title || record.url}</strong><span>{record.domain || record.url}</span>
          {record.health?.checked_at && <time dateTime={new Date(record.health.checked_at * 1000).toISOString()}>{t("最近检查：", "Last checked: ")}{new Date(record.health.checked_at * 1000).toLocaleDateString(t("zh-CN", "en-US"))}</time>}</div>
        <div className="health-bookmark-actions">
          {onPreview && <CapsuleButton type="button" className="secondary" onClick={() => onPreview(record.bookmark_id)}>{t("查看保存内容", "Read saved content")}</CapsuleButton>}
          <a href={record.url} target="_blank" rel="noreferrer">{t("原链接", "Original URL")}<ExternalLink size={13}/></a>
          {record.health?.archive_url && <a href={record.health.archive_url} target="_blank" rel="noreferrer">{t("网页存档", "Web archive")}<ExternalLink size={13}/></a>}
        </div>
      </li>)}</ul> : <p className="health-note">{t("没有已确认失效的收藏。", "No bookmarks are confirmed unavailable.")}</p>}
    </section>}
  </details>;
}
