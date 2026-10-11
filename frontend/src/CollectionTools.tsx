import { useState } from "react";
import { Sparkles, Pause, Play, CheckCheck, X } from "lucide-react";
import { post, type CollectionScope, type Job, type Page } from "./api";
import { useText } from "./locale";
import type { LibraryAction } from "./LibraryTools";

export function CollectionTools({ scope, page, display, onDisplay, sort, onSort, onStatus, disabled,
  allMatching, selectedCount, onAll, onClear, onSummarizeSelection, onAction, job, refresh, admin }: {
  scope: CollectionScope; page: Page | null; display: "summary" | "original";
  onDisplay: (value: "summary" | "original") => void; sort: string; onSort: (value: string) => void;
  onStatus: (value: CollectionScope["status"]) => void; disabled: boolean;
  allMatching: boolean; selectedCount: number; onAll: () => void; onClear: () => void;
  onSummarizeSelection: () => void;
  onAction: (action: LibraryAction) => void; job: Job; refresh: () => Promise<void>; admin: boolean;
}) {
  const t = useText();
  const [target, setTarget] = useState("current");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const counts = page?.summary_counts;
  const process = () => onAction({ kind: "process", mode: "summarize",
    scope: target === "all" ? {} : target === "pending" || target === "failed" ? { ...scope, status: target, exclude_ids: [] } : scope,
    scopeLabel: target === "all" ? t("整个书签库", "Entire library") : target === "pending" ? t("当前筛选中的未生成内容", "Pending in current filters")
      : target === "failed" ? t("当前筛选中的失败内容", "Failures in current filters") : t("当前筛选结果", "Current matching results") });
  async function taskAction() {
    setBusy(true); setError("");
    try {
      await post(job.state === "running" ? "/admin/jobs/pause" : "/admin/jobs/resume", { resume_id: job.id, confirmed: true });
      await refresh();
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  return <div className="collection-tools">
    <div className="collection-status" role="group" aria-label={t("摘要状态", "Summary status")}>
      {(["all", "pending", "done", "failed"] as const).map((status, i) => <button key={status} aria-pressed={(scope.status || "all") === status}
        onClick={() => onStatus(status)}>{[t("全部", "All"), t("待生成", "Pending"), t("有摘要", "Summarized"), t("失败", "Failed")][i]}
        <span>{(counts?.[status === "all" ? "total" : status] ?? 0).toLocaleString()}</span></button>)}
    </div>
    <div className="collection-options">
      <div className="summary-display" role="group" aria-label={t("列表内容", "Collection content")}>
        <button aria-pressed={display === "summary"} onClick={() => onDisplay("summary")}>{t("摘要", "Summaries")}</button>
        <button aria-pressed={display === "original"} onClick={() => onDisplay("original")}>{t("原文摘录", "Excerpts")}</button>
      </div>
      <label className="collection-sort"><span className="sr-only">{t("排序", "Sort")}</span><select aria-label={t("排序", "Sort")} value={sort} onChange={e => onSort(e.target.value)}>
        <option value="newest">{t("最近收藏", "Newest saved")}</option><option value="oldest">{t("最早收藏", "Oldest saved")}</option>
        <option value="title">{t("标题顺序", "Title")}</option><option value="domain">{t("按站点", "Website")}</option>
      </select></label>
      {admin && <div className="collection-process">
        <select aria-label={t("摘要处理范围", "Summary scope")} value={target} onChange={e => setTarget(e.target.value)}>
          <option value="current">{t("当前筛选", "Current filters")}</option><option value="pending">{t("当前未生成", "Pending in filters")}</option>
          <option value="failed">{t("当前失败重试", "Retry failures")}</option><option value="all">{t("整个书签库", "Entire library")}</option>
        </select><button className="primary" disabled={disabled || job.state === "running"} onClick={process}><Sparkles size={16}/>{t("批量生成摘要", "Generate summaries")}</button>
      </div>}
    </div>
    {admin && <div className="collection-selection">
      <button className="text-button" disabled={disabled || !page?.total} onClick={onAll}><CheckCheck size={15}/>{t(`全选符合条件的 ${(page?.total || 0).toLocaleString()} 条`, `Select all ${(page?.total || 0).toLocaleString()} matches`)}</button>
      {!!selectedCount && <><span role="status">{t(`已选 ${selectedCount.toLocaleString()} 条${allMatching ? " · 跨页生效" : ""}`, `${selectedCount.toLocaleString()} selected${allMatching ? " · across pages" : ""}`)}</span>
        <button className="text-button" disabled={disabled || job.state === "running"} onClick={onSummarizeSelection}><Sparkles size={15}/>{t("生成所选摘要", "Summarize selected")}</button>
        <button className="text-button" onClick={onClear}><X size={14}/>{t("清空", "Clear")}</button></>}
    </div>}
    {admin && job.params?.mode !== "index" && (job.state === "running" || job.resumable) && <div className="collection-job">
      <span>{job.state === "running" ? t("正在处理", "Processing") : t("任务已暂停，可继续", "Task saved; ready to resume")} · {job.items?.done.toLocaleString() || 0} / {job.items?.total.toLocaleString() || 0}
        {!!job.items?.failed && t(` · ${job.items.failed} 条失败`, ` · ${job.items.failed} failed`)}</span>
      <button className="secondary" disabled={busy || job.pause_requested} onClick={taskAction}>{job.state === "running" ? <Pause size={15}/> : <Play size={15}/>}
        {job.pause_requested ? t("正在暂停…", "Pausing…") : job.state === "running" ? t("暂停", "Pause") : t("继续任务", "Resume")}</button>
    </div>}
    {error && <p className="error" role="alert">{error}</p>}
  </div>;
}
