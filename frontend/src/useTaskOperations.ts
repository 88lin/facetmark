import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";
import type { Language } from "./locale";
import { clearTaskOperation, loadTaskOperations, saveTaskOperation, taskRequest, taskResult, taskStoragePrefix, validTaskReceipt,
  type TaskChange, type TaskOperation } from "./task-local-state";

export function useTaskOperations({ enabled, language, onAccepted }: { enabled: boolean; language: Language; onAccepted: (change: TaskChange) => Promise<void> }) {
  const t = (zh: string, en: string) => language === "zh" ? zh : en;
  const [operations, setOperations] = useState(loadTaskOperations), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [showRecovery, setShowRecovery] = useState(operations.length > 0);
  const pending = useRef(operations), gate = useRef(false), live = useRef(true), callback = useRef(onAccepted);
  const abort = useRef<AbortController | null>(null), initial = useRef(new Set(operations.map(value => value.requestId)));
  callback.current = onAccepted;
  useEffect(() => {
    live.current = true;
    const changed = (event: StorageEvent) => {
      if (event.key === null || event.key.startsWith(taskStoragePrefix)) {
        const values = loadTaskOperations(); pending.current = values; setOperations(values);
        setShowRecovery(values.length > 0);
        for (const value of values) initial.current.add(value.requestId);
      }
    };
    window.addEventListener("storage", changed);
    return () => { live.current = false; abort.current?.abort(); window.removeEventListener("storage", changed); };
  }, []);

  function keep(value: TaskOperation | null, requestId: string) {
    const stored = value ? saveTaskOperation(value) : clearTaskOperation(requestId);
    if (!value && !stored) return false;
    pending.current = stored ? loadTaskOperations() : [...pending.current.filter(item => item.requestId !== requestId), ...(value ? [value] : [])]
      .sort((a, b) => a.createdAt - b.createdAt);
    if (live.current) setOperations(pending.current);
    if (live.current && !pending.current.length) setShowRecovery(false);
    return stored;
  }
  async function confirmed(value: TaskOperation) {
    const accepted = { ...value, confirmed: true, refused: false, rejected: false };
    keep(accepted, value.requestId);
    if (!live.current) return true;
    try {
      await callback.current(value.change);
      if (!keep(null, value.requestId)) {
        setShowRecovery(true);
        setError(t("任务已接受，但无法清理本机恢复记录。可以再次读取确认。", "Task accepted; the local recovery record could not be cleared. Read again."));
      } else if (live.current) setError("");
    } catch (failure) { if (live.current) { setShowRecovery(true); setError(String(failure)); } }
    return true;
  }
  async function lookup(value: TaskOperation, signal: AbortSignal) {
    try {
      const result = await api<unknown>(`/admin/jobs/operations/${encodeURIComponent(value.requestId)}`, { signal });
      if (!validTaskReceipt(result, value)) throw new Error(t("无法核对原任务的接受记录。", "The task acceptance record could not be verified."));
      return result;
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 404) return null;
      throw failure;
    }
  }
  async function execute(value: TaskOperation, signal: AbortSignal) {
    const request = taskRequest(value);
    try {
      const result = await api<unknown>(request.path, { method: "POST", body: JSON.stringify(request.body), signal, timeoutMs: 20_000 });
      if (!taskResult(result, value.change)) throw new Error(t("任务返回内容不完整，原任务已保留。", "The task response is incomplete. The original task is retained."));
      return await confirmed(value);
    } catch (failure) {
      if (!live.current || signal.aborted) return false;
      setShowRecovery(true);
      setError(String(failure));
      const refused = failure instanceof ApiError && [400, 401, 403, 404, 409, 410, 413, 422].includes(failure.status);
      const unresolved = refused ? { ...value, refused: true } : value;
      if (refused) keep(unresolved, value.requestId);
      try {
        if (await lookup(unresolved, signal)) return await confirmed(unresolved);
        if (refused) keep({ ...unresolved, rejected: true }, value.requestId);
      } catch (readFailure) { if (live.current && !signal.aborted) setError(String(readFailure)); }
      return false;
    }
  }
  async function run(change: TaskChange) {
    if (gate.current) return false;
    if (pending.current.length && (change.kind !== "cancel" || pending.current.some(value => value.change.kind === "cancel"
      && value.change.jobId === change.jobId && value.change.runId === change.runId))) { setShowRecovery(true); return false; }
    if (!enabled) throw new Error(t("先恢复本机连接，再操作任务。", "Restore the local connection before operating tasks."));
    gate.current = true; setBusy(true); setError("");
    const value: TaskOperation = { version: 1, requestId: crypto.randomUUID(), createdAt: Date.now(), confirmed: false, change: structuredClone(change) };
    const controller = new AbortController(); abort.current = controller;
    try {
      if (!saveTaskOperation(value)) throw new Error(t("无法保留本机任务恢复记录。请检查本机存储后重试。", "The local task recovery record could not be saved. Check local storage and retry."));
      keep(value, value.requestId);
      return await execute(value, controller.signal);
    } finally { gate.current = false; if (live.current) setBusy(false); }
  }
  async function check(requestId: string, resend = false) {
    if (gate.current || !enabled) return false;
    const value = pending.current.find(item => item.requestId === requestId);
    if (!value) return false;
    setShowRecovery(true);
    gate.current = true; setBusy(true); setError("");
    const controller = new AbortController(); abort.current = controller;
    try {
      if (value.confirmed || await lookup(value, controller.signal)) return await confirmed(value);
      if (value.refused) { keep({ ...value, rejected: true }, value.requestId); return false; }
      if (resend && !value.rejected) return await execute(value, controller.signal);
      return false;
    } catch (failure) { if (live.current && !controller.signal.aborted) setError(String(failure)); return false; }
    finally { gate.current = false; if (live.current) setBusy(false); }
  }
  async function abandon(requestId: string): Promise<TaskChange | null> {
    if (gate.current || !enabled) return null;
    const value = pending.current.find(item => item.requestId === requestId);
    if (!value?.rejected || value.confirmed) return null;
    gate.current = true; setBusy(true); setError("");
    const controller = new AbortController(); abort.current = controller;
    try {
      if (await lookup(value, controller.signal)) { await confirmed(value); return null; }
      if (!live.current || controller.signal.aborted) return null;
      if (!keep(null, requestId)) { setError(t("无法清理本机恢复记录。", "The local recovery record could not be cleared.")); return null; }
      return structuredClone(value.change);
    } catch (failure) { if (live.current && !controller.signal.aborted) setError(String(failure)); return null; }
    finally { gate.current = false; if (live.current) setBusy(false); }
  }
  useEffect(() => {
    if (!enabled || busy) return;
    const value = operations.find(item => initial.current.has(item.requestId));
    if (!value) return;
    initial.current.delete(value.requestId);
    void check(value.requestId);
  }, [enabled, busy, operations]);
  return { operations, showRecovery, busy, error, run, check, abandon, clearError: () => setError("") };
}
