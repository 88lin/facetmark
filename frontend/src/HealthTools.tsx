import { useEffect, useRef, useState } from "react";
import { ExternalLink, LoaderCircle, RefreshCw, ShieldCheck, Square } from "lucide-react";
import { api, ApiError, type Bookmark } from "./api";
import { clearHealthOperation, healthRequest, loadHealthOperations, originalHealthRun, saveHealthOperation,
  validHealthCounts, validHealthLibrary, validHealthRun, type HealthOperation, type HealthRun } from "./health-local-state";
import { useText } from "./locale";
import { CapsuleButton } from "./ui/controls";
import "./health-tools.css";

type HealthBookmark = Bookmark & { health?: { status: string; checked_at?: number | null; archive_url?: string } };
export function HealthTools({ onPreview, onChanged, disabled = false }: { onPreview?: (bookmarkId: number) => void; onChanged?: () => void; disabled?: boolean } = {}) {
  const t = useText();
  const [limit, setLimit] = useState(20), [busy, setBusy] = useState(false), [loading, setLoading] = useState(false);
  const [opened, setOpened] = useState(() => { try { return loadHealthOperations().length > 0; } catch { return false; } });
  const [known, setKnown] = useState(false), [remoteBusy, setRemoteBusy] = useState(false);
  const [libraryId, setLibraryId] = useState("");
  const [counts, setCounts] = useState<Record<string, number> | null>(null);
  const [dead, setDead] = useState<HealthBookmark[]>([]), [error, setError] = useState("");
  const [actionFailure, setActionFailure] = useState<{ requestId: string; kind: "check" | "close" | "stop"; message: string } | null>(null);
  const [run, setRun] = useState<HealthRun | null>(null), [operations, setOperations] = useState<HealthOperation[]>([]);
  const [absent, setAbsent] = useState(""), [storageError, setStorageError] = useState("");
  const gate = useRef(false), revision = useRef(0), request = useRef<AbortController | null>(null);
  const reading = useRef<object | null>(null);
  const visible = useRef(opened); visible.current = opened;
  const changeCallback = useRef(onChanged); changeCallback.current = onChanged;
  const wasRunning = useRef<boolean | null>(null);
  const mounted = useRef(true);
  const invalid = () => new Error(t("检查返回了无法确认的结果，请保留原请求并重新读取。", "The check returned an unreadable result. Keep the original request and read it again."));
  function originals(owner?: string) {
    try { const values = loadHealthOperations(owner); setOperations(values); setStorageError(""); return values; }
    catch {
      setStorageError(t("无法读取已保存的原检查。读取成功前不会开始新的网址检查。", "Saved checks could not be read. Read them successfully before checking another URL."));
      return null;
    }
  }
  useEffect(() => {
    mounted.current = true;
    originals();
    return () => { mounted.current = false; request.current?.abort(); revision.current++; };
  }, []);
  useEffect(() => {
    if (!opened) return;
    void load(); const timer = setInterval(() => { void load(); }, 3000);
    const changed = (event: StorageEvent) => {
      if (event.storageArea === localStorage && (event.key === null || event.key.startsWith("fm-health-operation:"))) void load();
    };
    window.addEventListener("storage", changed);
    return () => { clearInterval(timer); request.current?.abort(); revision.current++; window.removeEventListener("storage", changed); };
  }, [opened]);
  const label = (status: string) => ({
    unchecked: t("待检查", "Unchecked"), alive: t("可访问", "Reachable"),
    restricted: t("访问受限", "Restricted"), drifted: t("内容已变化", "Content changed"),
    soft_gone: t("内容疑似移除", "Content may be removed"), gone: t("疑似失效", "Appears gone"),
    unreachable: t("暂时无法连接", "Temporarily unreachable"), unknown: t("尚无结论", "Unknown"),
  } as Record<string, string>)[status] || t("尚无结论", "Unknown");

  async function load() {
    if (gate.current || reading.current && !request.current?.signal.aborted) return;
    const owner = {}; reading.current = owner;
    try { await readSavedResults(); }
    finally {
      if (reading.current === owner) {
        reading.current = null;
        if (mounted.current) setLoading(false);
      }
    }
  }
  function confirmFailure(found: HealthRun) {
    setActionFailure(previous => !previous || previous.requestId !== found.request_id
      || previous.kind === "stop" && found.state === "running" ? previous : null);
  }
  function runningState(value: boolean) {
    setRemoteBusy(value);
    if (wasRunning.current !== value && (value || wasRunning.current !== null)) changeCallback.current?.();
    wasRunning.current = value;
  }
  async function readSavedResults() {
    request.current?.abort();
    const pending = new AbortController(); request.current = pending;
    const current = ++revision.current; setLoading(true); setError("");
    const results = await Promise.allSettled([
      api<unknown>("/link-health/summary", { signal: pending.signal }),
      api<unknown>("/graveyard?limit=50", { signal: pending.signal }),
      api<unknown>("/link-health/runs/current", { signal: pending.signal }),
    ]);
    if (pending.signal.aborted || current !== revision.current || !mounted.current) return;
    const failures: string[] = [];
    if (results[0].status === "fulfilled" && validHealthCounts(results[0].value)) setCounts(results[0].value);
    else failures.push(results[0].status === "rejected" ? String(results[0].reason) : invalid().message);
    const books = results[1].status === "fulfilled" ? results[1].value : null;
    if (Array.isArray(books) && books.every(value => value && typeof value === "object" && Number.isSafeInteger(value.bookmark_id)
      && ["title", "url", "folder"].every(key => typeof value[key] === "string") && (value.ai_title === undefined || typeof value.ai_title === "string")
      && (value.domain === undefined || typeof value.domain === "string") && (value.health === undefined || value.health && typeof value.health === "object"
        && typeof value.health.status === "string" && (value.health.checked_at === undefined || value.health.checked_at === null || Number.isSafeInteger(value.health.checked_at))
        && (value.health.archive_url === undefined || typeof value.health.archive_url === "string")))) setDead(books);
    else failures.push(results[1].status === "rejected" ? String(results[1].reason) : invalid().message);
    try {
      if (results[2].status === "rejected") throw results[2].reason;
      const value = results[2].value as { library_id?: unknown; running?: unknown; run?: unknown } | null;
      if (!value || !validHealthLibrary(value.library_id) || typeof value.running !== "boolean" || value.run !== null && !validHealthRun(value.run)) throw invalid();
      setLibraryId(value.library_id); setRun(value.run as HealthRun | null); runningState(value.running); setKnown(true); setAbsent("");
      if (value.run) confirmFailure(value.run as HealthRun);
      const original = originals(value.library_id)?.[0];
      if (original) {
        setLimit(original.limit);
        try {
          const alreadyRead = originalHealthRun(value.run, original);
          const result = alreadyRead ?? await api<unknown>(`/link-health/runs/${encodeURIComponent(original.requestId)}`, { signal: pending.signal });
          if (pending.signal.aborted || current !== revision.current || !mounted.current) return;
          const found = originalHealthRun(result, original); if (!found) throw invalid();
          setRun(found); setAbsent(""); confirmFailure(found);
          if (!["running", "stopping"].includes(found.state)) { clearHealthOperation(original.requestId); originals(value.library_id); }
        } catch (failure) {
          if (pending.signal.aborted || current !== revision.current || !mounted.current) return;
          if (failure instanceof ApiError && failure.status === 404) setAbsent(original.requestId);
          else throw failure;
        }
      }
    } catch (failure) { setKnown(false); setAbsent(""); failures.push(String(failure)); }
    setError(failures.join(" · ")); setLoading(false);
  }
  async function send(original: HealthOperation, closing = false) {
    if (gate.current || !closing && disabled) return;
    gate.current = true; setBusy(true); setError(""); setActionFailure(null);
    request.current?.abort(); const current = ++revision.current;
    try {
      saveHealthOperation(original); originals(original.libraryId);
      const path = closing ? `/link-health/runs/${encodeURIComponent(original.requestId)}/close` : "/link-health/check";
      const result = await api<unknown>(path, { method: "POST", body: JSON.stringify(healthRequest(original)), timeoutMs: 20_000 });
      const next = originalHealthRun(result, original); if (!next) throw invalid();
      if (closing || !["running", "stopping"].includes(next.state)) clearHealthOperation(original.requestId);
      if (mounted.current && current === revision.current) {
        setRun(next); runningState(["running", "stopping"].includes(next.state)); setKnown(true); originals(original.libraryId); setAbsent("");
      }
    } catch (failure) {
      if (mounted.current && current === revision.current) setActionFailure({ requestId: original.requestId,
        kind: closing ? "close" : "check", message: String(failure) });
    }
    finally {
      gate.current = false;
      if (mounted.current) { setBusy(false); if (visible.current) void load(); }
    }
  }
  async function check() {
    if (gate.current || disabled || !known || remoteBusy) return;
    const saved = originals(libraryId); if (!saved || saved.length) return;
    await send({ version: 1, requestId: `health-${crypto.randomUUID()}`, createdAt: Date.now(), limit, libraryId });
  }
  async function stop() {
    if (!run || gate.current) return;
    const originalId = run.request_id; gate.current = true; setBusy(true); setError(""); setActionFailure(null);
    request.current?.abort(); const current = ++revision.current;
    try {
      const result = await api<unknown>(`/link-health/runs/${encodeURIComponent(originalId)}/stop`, { method: "POST", timeoutMs: 20_000 });
      if (!validHealthRun(result) || result.request_id !== originalId) throw invalid();
      if (mounted.current && current === revision.current) setRun(result);
    } catch (failure) {
      if (mounted.current && current === revision.current) setActionFailure({ requestId: originalId, kind: "stop", message: String(failure) });
    }
    finally { gate.current = false; if (mounted.current) { setBusy(false); if (visible.current) void load(); } }
  }
  const original = operations[0];
  const accepted = original && run?.request_id === original.requestId;
  const uncertain = Boolean(original && !accepted);
  const running = Boolean(run && ["running", "stopping"].includes(run.state));
  const report = run?.report, checkedAt = run?.finished_at ? run.finished_at * 1000 : null;
  const visibleError = [actionFailure?.message, error, storageError].filter(Boolean).join(" · ");

  return <details className="health-tools" open={opened} onToggle={event => setOpened(event.currentTarget.open)}>
    <summary><ShieldCheck size={18}/><span>{t("链接健康检查", "Link health check")}</span></summary>
    <p className="health-intro">{t("查看已保存的链接状态，或检查到期的收藏。检查会访问原网址；仍会保留收藏和已保存的内容。",
      "Review saved link status or check bookmarks that are due. Checking visits their original URLs; bookmarks and saved content remain available.")}</p>
    <div className="health-actions">
      <label>{t("本次最多检查", "Check up to")}
        <select value={original?.limit ?? limit} disabled={busy || disabled || running || operations.length > 0} onChange={event => setLimit(Number(event.target.value))}
          aria-label={t("链接检查数量", "Link check limit")}>
          {[...new Set([20, 50, 100, 500, limit, ...(original ? [original.limit] : [])])].sort((a, b) => a - b).map(value => <option key={value} value={value}>{value} {t("条", "links")}</option>)}
        </select>
      </label>
      <CapsuleButton type="button" className="secondary" disabled={!known || busy || disabled || remoteBusy || running || operations.length > 0 || Boolean(storageError)} onClick={check}>
        {busy || running ? <LoaderCircle size={16} className="spin"/> : <ShieldCheck size={16}/>}
        {running ? t("检查进行中", "Check in progress") : t("检查链接", "Check links")}
      </CapsuleButton>
      <CapsuleButton type="button" className="text-button" disabled={loading || busy} onClick={() => load()}>
        <RefreshCw size={15}/>{t("刷新已保存结果", "Refresh saved results")}
      </CapsuleButton>
    </div>
    {disabled && <p className="health-note">{t("当前处理任务结束后可以检查链接。", "Check links when the current processing task finishes.")}</p>}
    {visibleError && <p className="error" role="alert">{visibleError}</p>}
    {original && uncertain && !busy && <section className="health-recovery" aria-label={t("原链接检查恢复", "Original link check recovery")}>
      <h3>{t("确认原链接检查", "Confirm the original link check")}</h3>
      <p>{t(`原请求最多检查 ${original.limit} 条到期链接。重开页面只读取结果，不会再次访问网址。`,
        `The original request checks up to ${original.limit} due links. Reopening reads the result without visiting URLs again.`)}</p>
      <div className="health-actions">
        <CapsuleButton type="button" className="secondary" onClick={() => load()}>{t("读取原检查", "Read original check")}</CapsuleButton>
        {absent === original.requestId && <>
          <CapsuleButton type="button" className="secondary" disabled={disabled || remoteBusy} onClick={() => send(original)}>{t("继续原检查", "Continue original check")}</CapsuleButton>
          <CapsuleButton type="button" className="text-button" onClick={() => send(original, true)}>{t("返回已保存结果", "Return to saved results")}</CapsuleButton>
        </>}
      </div>
    </section>}
    {running && run && <section className="health-running" aria-label={t("当前链接检查", "Current link check")}>
      <h3><LoaderCircle size={16} className="spin"/>{run.state === "stopping" ? t("正在停止检查", "Stopping the check") : t("正在检查链接", "Checking links")}</h3>
      <p>{t(`本次范围包含 ${run.targets_count} 条到期链接。离开页面后检查仍会继续，回到这里可以读取同一次结果。`,
        `This check includes ${run.targets_count} due links. It continues after leaving the page; return here to read the same result.`)}</p>
      <CapsuleButton type="button" className="secondary" disabled={busy || run.state === "stopping"} onClick={stop}><Square size={14}/>{t("停止检查", "Stop check")}</CapsuleButton>
    </section>}
    {remoteBusy && !running && <p className="health-note" role="status">{t("另一客户端正在检查链接；可以刷新已保存结果，暂不开始新的检查。", "Another client is checking links. Refresh saved results while that check finishes.")}</p>}
    {run && ["failed", "cancelled", "interrupted"].includes(run.state) && <div className="health-run-notice" role="status">
      <p>{run.state === "cancelled" ? t("检查已停止。收藏和之前保存的检查结果仍在。", "The check stopped. Your bookmarks and previously saved results remain available.")
        : run.state === "interrupted" ? t("上次检查已中断，没有自动重查网址。可以查看保存结果，或明确开始新检查。", "The previous check was interrupted. URLs were not checked automatically. Review saved results or explicitly start a new check.")
          : t("本次检查未能完成。已保存的结果和收藏仍保留，可以先核对。", "This check could not finish. Your bookmarks and saved results remain available for review.")}</p>
      {run.error && <details><summary>{t("查看原因", "Show reason")}</summary><p>{run.error}</p></details>}
    </div>}
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
