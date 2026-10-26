import { useContext, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ArrowRight, CalendarDays, ChevronLeft, ChevronRight, LoaderCircle, RefreshCw } from "lucide-react";
import { api } from "./api";
import { Locale, useText } from "./locale";
import { CapsuleButton } from "./ui/controls";
import { useReducedMotion } from "./useReducedMotion";
import "./activity-timeline.css";

type TimelineResponse = {
  days: { key: string; from: number; to: number; count: number }[];
  months: { key: string; count: number }[];
  older: number;
  oldest: number | null;
};
type Period = { key: string; from: number; to: number; count: number };
type Timeline = { days: Period[]; months: Period[]; older: Period | null };
const daySeconds = 86400;

function utcDay(timestamp: number): string {
  const date = new Date(timestamp * 1000).toISOString().slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new Error("Unsupported timeline date");
  return date;
}

function countIsValid(count: number) {
  return Number.isSafeInteger(count) && count >= 0;
}

function readTimeline(response: TimelineResponse): Timeline {
  if (!response || !Array.isArray(response.days) || !Array.isArray(response.months)
    || !countIsValid(response.older) || (response.days.length !== 0 && response.days.length !== 7))
    throw new Error("Invalid timeline response");
  const days = response.days.map(period => {
    if (!Number.isSafeInteger(period.from) || period.from % daySeconds !== 0
      || period.to !== period.from + daySeconds || !countIsValid(period.count)
      || period.key !== "day:" + utcDay(period.from)) throw new Error("Invalid day bucket");
    return period;
  }).sort((a, b) => b.from - a.from);
  const recentStart = days.length ? days[days.length - 1].from : null;
  if (days.some((period, index) => period.from !== days[0].from - index * daySeconds))
    throw new Error("Non-contiguous recent days");
  if (response.months.length && recentStart === null) throw new Error("Missing recent boundary");
  const months = response.months.map(period => {
    const match = /^month:(\d{4})-(\d{2})$/.exec(period.key);
    if (!match || !countIsValid(period.count)) throw new Error("Invalid month bucket");
    const year = Number(match[1]), month = Number(match[2]);
    if (year < 1970 || month < 1 || month > 12) throw new Error("Invalid month date");
    const from = Date.UTC(year, month - 1, 1) / 1000;
    // The service counts only dates before the earliest recent-day bucket.
    // Keep the linked query on that same boundary, including at month changes.
    const to = Math.min(Date.UTC(year, month, 1) / 1000, recentStart!);
    if (from >= to) throw new Error("Month overlaps recent days");
    utcDay(to);
    return { ...period, from, to };
  }).sort((a, b) => b.from - a.from);
  if (new Set(months.map(period => period.key)).size !== months.length) throw new Error("Duplicate month bucket");
  let older: Period | null = null;
  if (response.older > 0) {
    if (!months.length || !Number.isSafeInteger(response.oldest) || response.oldest! <= 0)
      throw new Error("Missing older boundary");
    const from = Math.floor(response.oldest! / daySeconds) * daySeconds, to = months[months.length - 1].from;
    if (from >= to) throw new Error("Invalid older boundary");
    utcDay(from);
    older = { key: "older", from, to, count: response.older };
  }
  return { days, months, older };
}

function periodQuery(period: Period) {
  // Timeline months exclude missing and zero timestamps. Strictly after the
  // epoch preserves that rule for an old library whose earliest day is 1970-01-01.
  const lower = period.from === 0 ? "added:>1970-01-01" : "added:>=" + utcDay(period.from);
  return `${lower} added:<${utcDay(period.to)}`;
}

function rangeLabel(period: Period) {
  const first = utcDay(period.from), last = utcDay(period.to - 1);
  return first === last ? first : `${first}–${last}`;
}

function PeriodStrip({ children, className, labelledBy }: { children: ReactNode; className: string; labelledBy: string }) {
  const t = useText(), reduced = useReducedMotion();
  const strip = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({ overflow: false, start: true, end: true });
  useEffect(() => {
    const element = strip.current;
    if (!element) return;
    const measure = () => setEdges({ overflow: element.scrollWidth > element.clientWidth + 2,
      start: element.scrollLeft <= 1, end: element.scrollLeft + element.clientWidth >= element.scrollWidth - 2 });
    const wheel = (event: WheelEvent) => {
      if (event.ctrlKey || Math.abs(event.deltaX) >= Math.abs(event.deltaY)) return;
      const delta = event.deltaY * (event.deltaMode === 1 ? 24 : event.deltaMode === 2 ? element.clientWidth : 1);
      const maximum = element.scrollWidth - element.clientWidth;
      if (maximum <= 2 || (delta < 0 && element.scrollLeft <= 1) || (delta > 0 && element.scrollLeft >= maximum - 1)) return;
      event.preventDefault(); element.scrollLeft += delta;
    };
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    for (const child of element.children) observer.observe(child);
    element.addEventListener("scroll", measure, { passive: true });
    element.addEventListener("wheel", wheel, { passive: false });
    measure();
    return () => { observer.disconnect(); element.removeEventListener("scroll", measure); element.removeEventListener("wheel", wheel); };
  }, [children]);
  const move = (direction: number) => strip.current?.scrollBy({ left: direction * strip.current.clientWidth * .8, behavior: reduced ? "instant" : "smooth" });
  return <div className="activity-scroller" data-overflow={edges.overflow}>
    {edges.overflow && <CapsuleButton type="button" className="activity-scroll-button" disabled={edges.start}
      aria-label={t("向左浏览日期", "Scroll dates left")} onClick={() => move(-1)}><ChevronLeft size={17}/></CapsuleButton>}
    <div ref={strip} className={className} role="group" aria-labelledby={labelledBy} tabIndex={edges.overflow ? 0 : undefined}
      onKeyDown={event => {
        if (event.target !== event.currentTarget || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        if (event.key === "Home" || event.key === "End") event.currentTarget.scrollTo({ left: event.key === "Home" ? 0 : event.currentTarget.scrollWidth, behavior: reduced ? "instant" : "smooth" });
        else move(event.key === "ArrowLeft" ? -1 : 1);
      }}>{children}</div>
    {edges.overflow && <CapsuleButton type="button" className="activity-scroll-button" disabled={edges.end}
      aria-label={t("向右浏览日期", "Scroll dates right")} onClick={() => move(1)}><ChevronRight size={17}/></CapsuleButton>}
  </div>;
}

export function ActivityTimeline({ revision = 0, onSelect }: {
  revision?: number;
  onSelect: (query: string) => void;
}) {
  const language = useContext(Locale), t = useText(), id = useId();
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [loading, setLoading] = useState(true), [failed, setFailed] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setFailed(false);
    api<TimelineResponse>("/timeline?months=12", { signal: controller.signal })
      .then(response => { if (!controller.signal.aborted) setTimeline(readTimeline(response)); })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [revision, refreshVersion]);
  const locale = language === "zh" ? "zh-CN" : "en-US";
  const number = (count: number) => count.toLocaleString(locale);
  const countLabel = (count: number) => t(`${number(count)} 条收藏`, `${number(count)} ${count === 1 ? "bookmark" : "bookmarks"}`);
  const dayDate = new Intl.DateTimeFormat(locale, { month: "numeric", day: "numeric", timeZone: "UTC" });
  const monthDate = new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", timeZone: "UTC" });
  const recentCount = timeline?.days.reduce((sum, period) => sum + period.count, 0) || 0;
  const hasActivity = Boolean(recentCount || timeline?.months.some(period => period.count) || timeline?.older);
  const largestDay = Math.max(1, ...(timeline?.days.map(period => period.count) || []));
  const bucket = (period: Period, kind: "day" | "month") => <button type="button"
    key={period.key} data-period={period.key} className={`activity-bucket activity-bucket-${kind}`}
    disabled={loading || period.count === 0}
    aria-label={`${rangeLabel(period)} UTC · ${countLabel(period.count)}${period.count ? t("，查看收藏", ", view bookmarks") : ""}`}
    title={`${rangeLabel(period)} · UTC`}
    onFocus={event => event.currentTarget.scrollIntoView({ block: "nearest", inline: "nearest" })}
    onClick={() => onSelect(periodQuery(period))}>
    <span className="activity-bucket-date">{kind === "day" ? dayDate.format(period.from * 1000) : monthDate.format(period.from * 1000)}</span>
    <strong className="activity-bucket-count">{number(period.count)}</strong>
    {kind === "day" ? <span className="activity-day-meter" aria-hidden="true"><span style={{ width: `${period.count / largestDay * 100}%` }}/></span>
      : <span className="activity-bucket-range">{rangeLabel(period)}</span>}
  </button>;

  return <section className="activity-timeline" aria-labelledby={id} aria-busy={loading}>
    <header className="activity-heading">
      <div>
        <h2 id={id}><CalendarDays size={18} aria-hidden="true"/>{t("收藏活动", "Saving activity")}</h2>
        <p>{t("按保存时间浏览，所有日期与范围均采用 UTC。", "Browse by save time. All dates and ranges use UTC.")}</p>
      </div>
      <CapsuleButton type="button" className="text-button activity-refresh" disabled={loading}
        aria-label={failed ? t("重试收藏活动", "Retry saving activity") : t("刷新收藏活动", "Refresh saving activity")}
        onClick={() => setRefreshVersion(version => version + 1)}>
        {loading ? <LoaderCircle size={15} className="spin"/> : <RefreshCw size={15}/>}{failed ? t("重试", "Retry") : t("刷新", "Refresh")}
      </CapsuleButton>
    </header>
    {loading && <p className="activity-loading" role="status">{timeline ? t("正在刷新收藏活动…", "Refreshing saving activity…") : t("正在读取收藏活动…", "Loading saving activity…")}</p>}
    {failed && <p className="activity-error" role="alert">{timeline
      ? t("未能刷新收藏活动，下面显示上次读取的结果。", "Saving activity could not be refreshed. The previous results are shown below.")
      : t("暂时无法读取收藏活动，请重试。", "Saving activity could not be loaded. Please retry.")}</p>}
    {timeline && hasActivity && <>
      <div className="activity-period-heading">
        <h3 id={`${id}-days`}>{t("近 7 天", "Last 7 days")}<span>{countLabel(recentCount)}</span></h3>
        <p>{rangeLabel({ ...timeline.days[0], from: timeline.days[timeline.days.length - 1].from })} · UTC</p>
      </div>
      <PeriodStrip className="activity-day-strip" labelledBy={`${id}-days`}>
        {timeline.days.map(period => bucket(period, "day"))}
      </PeriodStrip>
      <div className="activity-period-heading">
        <h3 id={`${id}-months`}>{t("过去月份", "Earlier months")}</h3>
        <p>{t(`${utcDay(timeline.days[timeline.days.length - 1].from)} 之前 · UTC`, `Before ${utcDay(timeline.days[timeline.days.length - 1].from)} · UTC`)}</p>
      </div>
      {timeline.months.length ? <PeriodStrip className="activity-month-strip" labelledBy={`${id}-months`}>
        {timeline.months.map(period => bucket(period, "month"))}
      </PeriodStrip> : <p className="activity-no-months">{t("更早的月份暂无收藏。", "No bookmarks in earlier months.")}</p>}
      {timeline.older && <CapsuleButton type="button" className="text-button activity-older" data-period="older"
        disabled={loading} aria-label={`${rangeLabel(timeline.older)} UTC · ${countLabel(timeline.older.count)}${t("，查看更早收藏", ", view older bookmarks")}`}
        onClick={() => onSelect(periodQuery(timeline.older!))}>
        <span>{t("更早的收藏", "Older bookmarks")} · {countLabel(timeline.older.count)}<small>{rangeLabel(timeline.older)} · UTC</small></span><ArrowRight size={15}/>
      </CapsuleButton>}
    </>}
    {timeline && !hasActivity && !failed && !loading && <p className="activity-empty">{t("暂无收藏活动。带有保存时间的收藏会显示在这里。", "No saving activity yet. Bookmarks with a save date will appear here.")}</p>}
  </section>;
}
