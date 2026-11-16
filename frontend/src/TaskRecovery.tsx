import { ArrowLeft, Check, RefreshCw, Send } from "lucide-react";
import { useText } from "./locale";
import { CapsuleButton } from "./ui/controls";
import type { TaskChange, TaskOperation } from "./task-local-state";
import "./task-recovery.css";

export function TaskRecovery({ operations, busy, error, onCheck, onRetry, onEdit }: { operations: TaskOperation[]; busy: boolean;
  error: string; onCheck: (requestId: string) => void; onRetry: (requestId: string) => void; onEdit: (requestId: string) => void }) {
  const t = useText();
  const name = (change: TaskChange) => change.kind === "start" ? change.values.mode === "summarize" ? t("生成摘要", "Generate summaries")
    : change.values.mode === "fetch" ? t("抓取正文", "Fetch page text") : t("建立完整索引", "Build full index")
    : change.kind === "resume" ? t("继续任务", "Resume task") : change.kind === "pause" ? t("暂停任务", "Pause task") : t("取消任务", "Cancel task");
  const scope = (change: Extract<TaskChange, { kind: "start" }>) => {
    if (change.values.bookmark_ids) return t(`原范围：${change.values.bookmark_ids.length} 条选定收藏`, `Original scope: ${change.values.bookmark_ids.length} selected bookmarks`);
    const saved = change.values.scope;
    const status = saved?.status === "pending" ? t("待生成", "Pending") : saved?.status === "failed" ? t("失败", "Failed")
      : saved?.status === "done" ? t("已完成", "Completed") : "";
    const parts = [saved?.folder && t("文件夹：", "Folder: ") + saved.folder, saved?.tag && t("标签：", "Tag: ") + saved.tag,
      saved?.domain && t("来源：", "Source: ") + saved.domain, saved?.q && t("关键词：", "Keywords: ") + saved.q,
      saved?.session && t(`浏览批次 ${saved.session}`, `Browsing session ${saved.session}`), status,
      saved?.exclude_ids?.length && t(`排除 ${saved.exclude_ids.length} 条收藏`, `${saved.exclude_ids.length} bookmarks excluded`)];
    return t("原范围：", "Original scope: ") + (parts.filter(Boolean).join(" · ") || t("整个收藏库", "Entire collection"));
  };
  if (!operations.length) return null;
  return <aside className="task-recovery" aria-label={t("任务操作恢复", "Task operation recovery")} aria-busy={busy}>
    {operations.map(value => <div className="task-recovery-item" key={value.requestId}>
      <div className="task-recovery-copy"><strong>{value.confirmed ? <Check size={17}/> : <RefreshCw size={17}/>}{name(value.change)}</strong>
        <p role="status">{value.confirmed ? t("操作已接受。重新读取状态即可，已处理内容会保留。", "Operation accepted. Read the status again; completed content is retained.")
          : value.rejected ? t("原操作未被接受。可以返回修改任务范围。", "The original operation was not accepted. You can revise the task scope.")
          : t("结果尚未确认，原任务已保留。先读取接受记录，再决定是否继续原请求。", "The result is unconfirmed and the original task is retained. Read its acceptance record before continuing.")}</p>
        {value.change.kind === "start" && (scope(value.change).length > 160
          ? <details className="task-recovery-scope"><summary>{t("查看原任务范围", "View original task scope")}</summary><p>{scope(value.change)}</p></details>
          : <p className="task-recovery-scope">{scope(value.change)}</p>)}
        {value.change.kind === "start" && value.change.values.mode !== "index" && <p>{value.change.values.force
          ? t("包括已完成的收藏，将按原请求重新处理。", "Includes completed bookmarks for reprocessing as originally requested.")
          : t("保留已完成的内容，只处理原范围内待完成的收藏。", "Retains completed content and processes unfinished bookmarks in the original scope.")}</p>}
      </div>
      <div className="task-recovery-actions"><CapsuleButton className="secondary" disabled={busy} onClick={() => onCheck(value.requestId)}>
        <RefreshCw size={16}/>{t("读取任务结果", "Read task result")}</CapsuleButton>
        {!value.confirmed && !value.rejected && <CapsuleButton className="secondary" disabled={busy} onClick={() => onRetry(value.requestId)}>
          <Send size={16}/>{t("继续原任务请求", "Continue original request")}</CapsuleButton>}
        {value.rejected && !value.confirmed && <CapsuleButton className="secondary" disabled={busy} onClick={() => onEdit(value.requestId)}>
          <ArrowLeft size={16}/>{t("返回修改任务", "Revise task")}</CapsuleButton>}
      </div>
    </div>)}
    {error && <p className="error" role="alert">{error}</p>}
  </aside>;
}
