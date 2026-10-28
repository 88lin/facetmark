import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowLeft, ArrowRight, Clock3, Layers3, LoaderCircle, RefreshCw } from "lucide-react";
import { api, post } from "./api";
import { ActivityTimeline } from "./ActivityTimeline";
import { useText, type Language } from "./locale";
import { CapsuleButton } from "./ui/controls";
import "./saving-sessions.css";

type Session = { session_id: number; label: string; started_at: number; ended_at?: number;
  size: number; method?: string };

export function SavingSessions({ language, revision, disabled, onBack, onSession, onPeriod, onRebuilt }: {
  revision: number;
  language: Language; disabled: boolean; onBack: () => void; onSession: (id: number) => void;
  onPeriod: (query: string) => void; onRebuilt: () => Promise<void>;
}) {
  const t = useText();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true), [more, setMore] = useState(false);
  const [rebuilding, setRebuilding] = useState(false), [refreshVersion, setRefreshVersion] = useState(0);
  const [error, setError] = useState(""), [notice, setNotice] = useState("");
  const [retryOffset, setRetryOffset] = useState<number | null>(0);
  const request = useRef<AbortController | null>(null);
  const rebuildingRef = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; request.current?.abort(); }; }, []);
  async function load(offset = 0) {
    if (!mounted.current) return;
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setLoading(true); setError("");
    try {
      const data = await api<Session[]>(`/sessions?limit=40&offset=${offset}`, { signal: controller.signal });
      if (controller.signal.aborted) return;
      setSessions(previous => offset ? [...previous, ...data.filter(row => !previous.some(item => item.session_id === row.session_id))] : data);
      setMore(data.length === 40);
    } catch (e) { if (!controller.signal.aborted) { setRetryOffset(offset); setError(String(e)); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }
  useEffect(() => { void load(); return () => request.current?.abort(); }, [revision]);
  async function rebuild() {
    if (rebuildingRef.current) return;
    rebuildingRef.current = true; setRebuilding(true); setError(""); setNotice("");
    try {
      const result = await post<{ sessions: number; assigned: number }>("/admin/sessions/rebuild", {});
      if (mounted.current) {
        setNotice(t(`已整理 ${result.sessions.toLocaleString()} 个批次，包含 ${result.assigned.toLocaleString()} 条收藏。`,
          `Organized ${result.sessions.toLocaleString()} sessions containing ${result.assigned.toLocaleString()} bookmarks.`));
        await load();
        if (mounted.current) setRefreshVersion(value => value + 1);
      }
      await onRebuilt();
    } catch (e) { if (mounted.current) { setRetryOffset(null); setError(String(e)); } }
    finally { rebuildingRef.current = false; if (mounted.current) setRebuilding(false); }
  }
  const locale = language === "zh" ? "zh-CN" : "en-US";
  const date = (timestamp: number) => new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", day: "numeric" }).format(timestamp * 1000);
  const time = (timestamp: number) => new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit" }).format(timestamp * 1000);
  return <div className="saving-sessions">
    <header className="page-heading sessions-heading">
      <div><h1>{t("浏览批次", "Saving sessions")}</h1>
        <p>{t("按日期找回收藏，或回到当时一起保存的一组页面。", "Find bookmarks by date or revisit pages you saved together.")}</p></div>
      <CapsuleButton className="text-button support-back" type="button" onClick={onBack}><ArrowLeft size={16}/>{t("返回收藏", "Back to collection")}</CapsuleButton>
    </header>
    <ActivityTimeline revision={revision + refreshVersion} onSelect={onPeriod}/>
    <section className="sessions-section" aria-labelledby="sessions-title" aria-busy={loading || rebuilding}>
      <header className="sessions-section-heading">
        <div><h2 id="sessions-title"><Layers3 size={18}/>{t("一起保存的页面", "Saved together")}</h2>
          <p>{t("可按 20 分钟间隔重新整理，批量导入按文件夹归组。无需配置 AI。", "Reorganize saves with a 20-minute gap; bulk imports use folders. No AI setup required.")}</p></div>
        <div className="sessions-actions">
          <CapsuleButton type="button" className="text-button" disabled={loading || rebuilding} onClick={() => { void load(); setRefreshVersion(value => value + 1); }} aria-label={t("刷新浏览批次", "Refresh saving sessions")}><RefreshCw size={15}/>{t("刷新", "Refresh")}</CapsuleButton>
          <CapsuleButton type="button" className="secondary" disabled={disabled || rebuilding || loading} onClick={rebuild}>
            {rebuilding ? <LoaderCircle size={16} className="spin"/> : <Layers3 size={16}/>} {rebuilding ? t("正在整理…", "Organizing…") : t("整理浏览批次", "Organize sessions")}
          </CapsuleButton>
        </div>
      </header>
      {error && <div className="sessions-error" role="alert"><p>{t("未能更新浏览批次。", "Could not update saving sessions.")} {error}</p>
        <CapsuleButton type="button" className="text-button" disabled={loading || rebuilding || (retryOffset === null && disabled)}
          onClick={() => retryOffset === null ? rebuild() : load(retryOffset)}>
          {retryOffset === null ? t("重新整理批次", "Retry organizing sessions") : t("重试浏览批次", "Retry saving sessions")}</CapsuleButton></div>}
      {notice && <p className="notice" role="status">{notice}</p>}
      {loading && <p className="sessions-loading" role="status"><LoaderCircle size={16} className="spin"/>{t("正在读取浏览批次…", "Loading saving sessions…")}</p>}
      <div className="sessions-list">
        {sessions.map(session => <button type="button" className="session-row" key={session.session_id}
          disabled={rebuilding} onClick={() => onSession(session.session_id)}>
          <span className="session-symbol" aria-hidden="true">{session.method === "folder" ? <Layers3 size={19}/> : <Clock3 size={19}/>}</span>
          <span className="session-copy"><strong>{session.label || date(session.started_at)}</strong>
            <span className="session-meta">{session.label && <span>{date(session.started_at)}</span>}
              <span>{session.method === "folder" ? t("批量导入 · 同一文件夹", "Bulk import · same folder")
                : `${time(session.started_at)}${session.ended_at && session.ended_at > session.started_at ? " – " + (date(session.ended_at) !== date(session.started_at) ? date(session.ended_at) + " " : "") + time(session.ended_at) : ""}`}</span>
            </span></span>
          <span className="session-count">{session.size.toLocaleString(locale)}<small>{t("条收藏", "bookmarks")}</small></span>
          <ArrowRight className="session-open" size={17} aria-hidden="true"/>
        </button>)}
      </div>
      {!sessions.length && !loading && !error && <div className="sessions-empty"><Clock3 size={26}/>
        <h3>{t("还没有整理好的批次", "No sessions organized yet")}</h3>
        <p>{t("上方可直接按日期浏览。点击“整理浏览批次”，即可把已有收藏按保存时间归组。", "Browse dates above, or choose Organize sessions to group the bookmarks you already saved.")}</p></div>}
      {more && <CapsuleButton type="button" className="secondary sessions-more" disabled={loading || rebuilding} onClick={() => load(sessions.length)}><ArrowDown size={16}/>{t("加载更多", "Load more")}</CapsuleButton>}
    </section>
  </div>;
}
