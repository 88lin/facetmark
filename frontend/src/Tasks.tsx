import { CapsuleButton } from "./ui/controls";
import { useEffect, useState } from "react";
import { Check, Circle, Download, LoaderCircle, Pause, Play, RefreshCw, Sparkles, X } from "lucide-react";
import { api, post, type Job, type Setup } from "./api";
import { useText } from "./locale";

export function Tasks({
  job,
  setup,
  refresh,
  onProcess,
  onBack,
}: {
  job: Job;
  setup: Setup | null;
  refresh: () => Promise<void>;
  onProcess: (mode: "fetch" | "summarize") => void;
  onBack: () => void;
}) {
  const t = useText();
  const [consent, setConsent] = useState(false);
  const [fetchPages, setFetchPages] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<Job[]>([]);
  const [savedError, setSavedError] = useState(false);
  const [savedRevision, setSavedRevision] = useState(0);
  useEffect(() => {
    const abort = new AbortController();
    setSavedError(false);
    api<{ items: Job[] }>("/admin/jobs", { signal: abort.signal })
      .then(data => { if (!abort.signal.aborted) setSaved(data.items); })
      .catch(() => { if (!abort.signal.aborted) setSavedError(true); });
    return () => abort.abort();
  }, [job.id, job.state, savedRevision]);
  const mode = job.params?.mode || "index";
  const running = job.state === "running";
  const taskName =
    mode === "fetch"
      ? t("正文抓取", "Page fetch")
      : mode === "summarize"
        ? t("摘要生成", "Summary generation")
        : t("完整索引", "Full indexing");
  const names: Record<string, string> = {
    fetch: t("读取网页正文", "Fetch page text"),
    enrich: t("生成摘要与意图", "Generate summaries and intents"),
    embed_content: t("构建正文向量", "Embed page content"),
    filter_intents: t("筛选检索意图", "Filter search intents"),
    embed_intents: t("构建意图向量", "Embed search intents"),
    sessions: t("整理浏览批次", "Reconstruct saving sessions"),
    edges: t("连接相关书签", "Connect related bookmarks"),
  };
  const states: Record<string, string> = {
    idle: t("尚未开始", "Not started"),
    running: t(`${taskName}进行中`, `${taskName} in progress`),
    done: t(`${taskName}已完成`, `${taskName} completed`),
    partial: t(`${taskName}部分完成`, `${taskName} partially completed`),
    failed: t(`${taskName}未完成`, `${taskName} failed`),
    cancelled: t("任务已取消", "Task cancelled"),
    interrupted: t("上次任务被中断", "Previous task was interrupted"),
    paused: t("任务已暂停", "Task paused"),
  };
  const descriptions: Record<string, string> = {
    idle: t("先抓取正文或生成摘要；需要语义检索时，再建立完整索引。", "Start with page text or summaries. Build a full index when you need semantic search."),
    running: t("任务在后台继续，切换页面不会中断。", "Work continues in the background when you switch views."),
    paused: t("进度已保存。点击继续，处理剩余收藏。", "Progress is saved. Resume to process the remaining bookmarks."),
    done: t("处理已完成，可以返回收藏查看结果。", "Processing is complete. Return to the collection to view the results."),
    partial: t("部分内容未完成，请查看失败提示后重试。", "Some items could not be completed. Review the failure details before retrying."),
    failed: t("处理已停止，请查看错误并重试。", "Processing stopped. Review the error and retry."),
    cancelled: t("处理已取消，已完成的内容仍然保留。", "Processing was cancelled. Completed content has been kept."),
    interrupted: t("上次处理已中断，请继续已保存的任务或重新运行。", "Processing was interrupted. Resume the saved task or run it again."),
  };
  async function action(path: string, body: unknown) {
    setBusy(true);
    setError("");
    try {
      await post(path, body);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  const canIndex =
    setup?.demo ||
    (setup?.channels.chat.tested &&
      setup?.channels.embed.tested &&
      !setup?.pending_apply &&
      setup?.vector_compatible);
  return (
    <section className="tasks">
      <div className={`section-heading task-current task-state-${job.state}`}>
        <h2>{states[job.state] || job.state}</h2>
        <p>
          {descriptions[job.state] || t("请查看当前任务状态。", "Review the current task status.")}
        </p>
        {mode !== "index" && job.id && <p className="task-scope">{t("处理范围：", "Scope: ")}{job.params?.bookmark_ids
          ? t(`${job.params.bookmark_ids.length} 条选定收藏`, `${job.params.bookmark_ids.length} selected bookmarks`)
          : [job.params?.scope?.folder, job.params?.scope?.tag, job.params?.scope?.domain, job.params?.scope?.q].filter(Boolean).join(" · ") || t("书签库中的任务快照", "Saved library selection")}</p>}
      </div>
      {mode !== "index" && job.items && (
        <div className="task-progress">
          <p role="status">
            {t(
              `已处理 ${job.items.done} / ${job.items.total} 条待处理书签`,
              `Processed ${job.items.done} of ${job.items.total} pending bookmarks`,
            )}
          </p>
          {job.items.total > 0 && (
            <progress
              value={job.items.done}
              max={job.items.total}
              aria-label={t("书签处理进度", "Bookmark processing progress")}
            />
          )}
          {!!job.items.failed && <p className="error">{mode === "summarize"
            ? t(`${job.items.failed} 条处理失败。继续此任务会重试失败项，保留已完成的结果。`, `${job.items.failed} failed. Resume this task to retry failures and keep completed results.`)
            : t(`${job.items.failed} 条正文抓取失败。继续此任务只处理失败和未完成的收藏。`, `${job.items.failed} page fetches failed. Resume this task to process only failed and unfinished bookmarks.`)}</p>}
        </div>
      )}
      {running ? (
        <div className="task-current-actions">
          {mode !== "index" && <CapsuleButton className="secondary" disabled={busy || job.pause_requested}
            onClick={() => action("/admin/jobs/pause", {})}><Pause/>{job.pause_requested ? t("正在暂停…", "Pausing…") : t("暂停任务", "Pause task")}</CapsuleButton>}
          <p role="status">
            {job.cancel_requested
              ? t(
                  "已请求取消，将在当前阶段结束后停止。",
                  "Cancellation requested. Stopping after the current stage.",
                )
              : job.pause_requested ? t("正在保存当前批次，完成后暂停。", "Saving the current batch before pausing.") : t(
                  "正在处理当前阶段，所需时间取决于页面和模型服务。",
                  "Processing this stage. Time depends on the pages and model service.",
                )}
          </p>
          <CapsuleButton
            className="secondary"
            disabled={busy || job.cancel_requested}
            onClick={() => action("/admin/job/cancel", {})}
          >
            <X />
            {t("取消任务", "Cancel task")}
          </CapsuleButton>
        </div>
      ) : (
        <div className="task-current-actions">
          {job.resumable && <CapsuleButton className="primary" disabled={busy}
            onClick={() => action("/admin/jobs/resume", { resume_id: job.id, confirmed: true })}><Play/>{job.state === "partial" ? t("重试此任务失败项", "Retry this task's failures") : t("继续上次任务", "Resume saved task")}</CapsuleButton>}
          {job.state !== "idle" && <CapsuleButton className="secondary" onClick={onBack}>{t("返回收藏查看内容", "Return to collection")}</CapsuleButton>}
        </div>
      )}
      {(error || job.error) && (
        <p className="error" role="alert">
          {error || job.error}
        </p>
      )}
      <div className="task-shortcuts" aria-label={t("处理操作", "Processing actions")}>
        <div className="task-operation">
        <CapsuleButton className="secondary" disabled={busy || running} onClick={() => onProcess("fetch")}>
          <Download />
          {t("抓取网页正文", "Fetch page text")}
        </CapsuleButton>
        <p>{t("读取原网页，保存可供阅读和生成摘要的正文。无需模型。", "Save original page text for reading and summaries. No model needed.")}</p>
        </div>
        <div className="task-operation">
        <CapsuleButton className="secondary" disabled={busy || running} onClick={() => onProcess("summarize")}>
          <Sparkles />
          {t("生成阅读摘要", "Generate summaries")}
        </CapsuleButton>
        <p>{t("用已连接的 AI 生成摘要，可在确认前选择处理范围。", "Generate summaries with your connected AI. Review the scope before starting.")}</p>
        </div>
      </div>
      {savedError && <div className="error" role="alert"><p>{t("无法读取已保存的任务，请重试。", "Saved tasks could not be loaded. Please retry.")}</p>
        <CapsuleButton className="text-button" onClick={() => setSavedRevision(value => value + 1)}>{t("重试读取任务", "Retry saved tasks")}</CapsuleButton></div>}
      {saved.filter(item => item.id !== job.id).map(item => <div className="collection-job" key={item.id}>
        <span>{item.params?.mode === "summarize" ? t("已保存的摘要任务", "Saved summary task") : t("已保存的抓取任务", "Saved fetch task")} · {item.items?.done ?? 0} / {item.items?.total ?? 0}
          {!!item.items?.failed && t(` · ${item.items.failed} 条失败`, ` · ${item.items.failed} failed`)}</span>
        <CapsuleButton className="secondary" disabled={busy || running} onClick={() => action("/admin/jobs/resume", { resume_id: item.id, confirmed: true })}><Play/>{t("继续", "Resume")}</CapsuleButton>
      </div>)}
      {job.state !== "idle" && mode === "index" && (
        <p className="hint">
          {job.params?.bookmark_ids
            ? t(
                `范围：${job.params.bookmark_ids.length} 条所选书签`,
                `Scope: ${job.params.bookmark_ids.length} selected bookmarks`,
              )
            : t("范围：书签库中符合条件的书签", "Scope: eligible bookmarks in your library")}
        </p>
      )}
      {mode === "index" && ["interrupted", "failed", "cancelled", "partial"].includes(job.state) && (
        <p className="notice">
          {t(
            "可以再次运行。未变化且已经完成的内容会被指纹检查跳过。",
            "Run again to resume. Fingerprints skip completed, unchanged content.",
          )}
        </p>
      )}
      {job.state !== "idle" && <ol className="stages">
        {(job.planned || Object.keys(names)).map((name) => (
          <li key={name} className={job.current === name && running ? "current" : ""}>
            {job.done?.includes(name) ? (
              <Check />
            ) : job.current === name && running ? (
              <LoaderCircle className="spin" />
            ) : (
              <Circle />
            )}
            <span>{names[name] || name}</span>
            {job.done?.includes(name) && <small>{t("完成", "Done")}</small>}
          </li>
        ))}
      </ol>}
      {!running && (
        <div className="task-index-section">
          <details className="index-consent" open={mode === "index" && job.state !== "idle"}>
          <summary>{t("建立完整索引", "Build the full index")}<span>{t("可选 · 用于语义检索与关联", "Optional · Semantic search and connections")}</span></summary>
          <p>
            {t(
              "索引会将非隐私排除书签的标题、网址、已提取正文和生成的检索意图发送至你配置的聊天与向量服务。使用云端服务时，这些内容会离开本机。",
              "Indexing sends titles, URLs, extracted page text and generated search intents from non-excluded bookmarks to your configured chat and embedding services. With cloud services, this content leaves your device.",
            )}
          </p>
          <label className="check">
            <input
              type="checkbox"
              checked={fetchPages}
              onChange={(e) => setFetchPages(e.target.checked)}
            />
            {t("先访问原网页，提取正文", "Fetch original pages first")}
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            {t("我已了解并确认开始处理", "I understand and confirm processing")}
          </label>
          {!canIndex && (
            <p className="hint">
              {t(
                "请先保存、测试并应用两条模型连接。也可以继续使用关键词检索。",
                "Save, test and apply both model connections first. Keyword search remains available.",
              )}
            </p>
          )}
          <CapsuleButton
            className="primary"
            disabled={!consent || !canIndex || busy}
            onClick={() => action("/admin/index", { fetch: fetchPages, confirmed: true })}
          >
            {job.state === "idle" ? <Play /> : <RefreshCw />}
            {t("开始索引", "Start indexing")}
          </CapsuleButton>
          </details>
        </div>
      )}
      <details className="advanced">
        <summary>{t("任务日志与资料库诊断", "Task log and library diagnostics")}</summary>
        <pre>{job.log?.join("\n") || t("暂无日志", "No log yet")}</pre>
        <pre>{JSON.stringify(setup?.stats, null, 2)}</pre>
      </details>
    </section>
  );
}
