import { useEffect, useRef, useState } from "react";
import { post, type Setup } from "./api";
import type { LibraryAction } from "./LibraryTools";
import type { Language } from "./locale";

type SummaryAction = Extract<LibraryAction, { kind: "process" }>;

export function useSummaryGeneration({ setup, running, language, onStarted }: {
  setup: Setup | null; running: boolean; language: Language; onStarted: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [needsConnection, setNeedsConnection] = useState(false);
  const gate = useRef(false), abort = useRef<AbortController | null>(null);
  useEffect(() => () => abort.current?.abort(), []);
  const t = (zh: string, en: string) => language === "zh" ? zh : en;
  async function generate(action: SummaryAction) {
    if (gate.current || running) return;
    setError(""); setNeedsConnection(false);
    if (!setup?.demo && !setup?.channels.chat.tested) {
      setNeedsConnection(true);
      setError(t("请先在 AI 连接中测试并保存聊天模型，然后生成摘要。", "Test and save the chat connection before generating summaries."));
      return;
    }
    if (action.ids && !action.ids.length) return;
    gate.current = true; setBusy(true);
    const request = new AbortController(); abort.current = request;
    const values = { mode: "summarize", bookmark_ids: action.ids ? [...action.ids] : undefined,
      scope: action.scope ? { ...action.scope, exclude_ids: action.scope.exclude_ids ? [...action.scope.exclude_ids] : undefined } : undefined,
      force: action.reprocess ?? Boolean(action.ids?.length),
      summary_language: setup?.summary_language === "zh" || setup?.summary_language === "en" ? setup.summary_language : language };
    try {
      const preview = await post<{ total: number; revision: string; prompt_hash?: string }>("/admin/jobs/preview", values, request.signal);
      if (!preview.total) {
        setError(t("当前范围没有待生成内容。勾选收藏后可重新生成。", "There is nothing pending in this scope. Select bookmarks to regenerate them."));
        return;
      }
      // The explicit Generate action authorizes the described model request.
      await post("/admin/jobs/start", { ...values, confirmed: true, preview_revision: preview.revision,
        preview_prompt_hash: preview.prompt_hash }, request.signal);
      if (!request.signal.aborted) await onStarted();
    } catch (failure) {
      if (!request.signal.aborted) setError(String(failure));
    } finally {
      gate.current = false;
      if (!request.signal.aborted) setBusy(false);
    }
  }
  return { busy, error, needsConnection, generate, clearError: () => { setError(""); setNeedsConnection(false); } };
}
