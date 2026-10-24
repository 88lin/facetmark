import { CapsuleButton } from "./ui/controls";
import { useEffect, useRef, useState } from "react";
import { ArrowDownWideNarrow, ChevronDown, SlidersHorizontal, Pause, Play } from "lucide-react";
import { post, type CollectionScope, type Job, type Page } from "./api";
import { useText } from "./locale";
import { SelectionPill } from "./InteractionMotion";

export function CollectionTools({ scope, page, display, onDisplay, sort, onSort, onStatus, disabled,
  job, refresh, admin }: {
  scope: CollectionScope; page: Page | null; display: "summary" | "original";
  onDisplay: (value: "summary" | "original") => void; sort: string; onSort: (value: string) => void;
  onStatus: (value: CollectionScope["status"]) => void; disabled: boolean;
  job: Job; refresh: () => Promise<void>; admin: boolean;
}) {
  const t = useText();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const displayMenu = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const dismiss = (event: PointerEvent) => { if (event.target instanceof Node && displayMenu.current && !displayMenu.current.contains(event.target)) displayMenu.current.open = false; };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);
  const counts = page?.summary_counts;
  async function taskAction() {
    setBusy(true); setError("");
    try {
      await post(job.state === "running" ? "/admin/jobs/pause" : "/admin/jobs/resume", { resume_id: job.id, confirmed: true });
      await refresh();
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  return <div className="collection-tools">
    <div className="collection-status" role="group" aria-label={t("摘要状态", "Summary status")}>
      {(["all", "pending", "done", "failed"] as const).map((status, i) => <CapsuleButton key={status} data-status={status} aria-pressed={(scope.status || "all") === status}
        onClick={() => onStatus(status)}><SelectionPill active={(scope.status || "all") === status} group="summary-status" />{[t("全部", "All"), t("待生成", "Pending"), t("有摘要", "Summarized"), t("失败", "Failed")][i]}
        <span>{disabled || !counts ? "…" : counts[status === "all" ? "total" : status].toLocaleString()}</span></CapsuleButton>)}
    </div>
    <label className="collection-sort"><ArrowDownWideNarrow size={16} aria-hidden="true"/><span className="sr-only">{t("排序", "Sort")}</span><select aria-label={t("排序", "Sort")} value={sort} onChange={e => onSort(e.target.value)}>
      <option value="newest">{t("最近收藏", "Newest saved")}</option><option value="oldest">{t("最早收藏", "Oldest saved")}</option>
      <option value="title">{t("标题顺序", "Title")}</option>
    </select></label>
    <details ref={displayMenu} className="collection-options-menu"
      onBlur={event => { if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) event.currentTarget.open = false; }}
      onKeyDown={event => { if (event.key === "Escape") { event.stopPropagation(); event.currentTarget.open = false; event.currentTarget.querySelector("summary")?.focus(); } }}>
      <summary aria-label={t("显示内容", "Display content")}><SlidersHorizontal size={15}/><span>{t("显示", "Display")}</span><ChevronDown className="disclosure-chevron" size={14} aria-hidden="true"/></summary>
      <div className="collection-options">
      <div className="summary-display" role="group" aria-label={t("列表内容", "Collection content")}>
        <CapsuleButton aria-pressed={display === "summary"} onClick={() => onDisplay("summary")}>{t("摘要", "Summaries")}</CapsuleButton>
        <CapsuleButton aria-pressed={display === "original"} onClick={() => onDisplay("original")}>{t("原文摘录", "Excerpts")}</CapsuleButton>
      </div>
      </div>
    </details>
    {admin && job.params?.mode !== "index" && (job.state === "running" || job.resumable) && <div className="collection-job">
      <span>{job.state === "running" ? t("正在处理", "Processing") : t("任务已保存，可继续", "Task saved; ready to resume")} · {job.items?.done.toLocaleString() || 0} / {job.items?.total.toLocaleString() || 0}
        {!!job.items?.failed && t(` · ${job.items.failed} 条失败`, ` · ${job.items.failed} failed`)}</span>
      <CapsuleButton className="secondary" disabled={busy || job.pause_requested} onClick={taskAction}>{job.state === "running" ? <Pause size={15}/> : <Play size={15}/>}
        {job.pause_requested ? t("正在暂停…", "Pausing…") : job.state === "running" ? t("暂停", "Pause") : t("继续任务", "Resume")}</CapsuleButton>
    </div>}
    {error && <p className="error" role="alert">{error}</p>}
  </div>;
}
