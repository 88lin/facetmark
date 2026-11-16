import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";
import { useText } from "./locale";
import type { SyncReceipt } from "./sync-types";
import { clearSyncOperation, loadSyncOperations, saveSyncOperation, syncRequest, syncStoragePrefix, validSyncReceipt,
  type SyncChangeRequest, type SyncOperation } from "./sync-local-state";

export function useSyncOperations(onAccepted: (receipt: SyncReceipt, change?: SyncChangeRequest) => Promise<void>) {
  const t = useText();
  const [operations, setOperations] = useState(loadSyncOperations), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [showRecovery, setShowRecovery] = useState(operations.length > 0);
  const pending = useRef(operations), gate = useRef(false), live = useRef(true), callback = useRef(onAccepted);
  const controller = useRef<AbortController | null>(null);
  callback.current = onAccepted;
  const actionOf = (value?: SyncOperation) => value?.change.kind === "receipt" ? value.change.action : value?.change.kind;
  function keep(value: SyncOperation | null, requestId: string) {
    const saved = value ? saveSyncOperation(value) : clearSyncOperation(requestId);
    if (!value && !saved) return false;
    pending.current = saved ? loadSyncOperations() : [...pending.current.filter(item => item.requestId !== requestId), ...(value ? [value] : [])];
    if (live.current) { setOperations(pending.current); if (!pending.current.length) setShowRecovery(false); }
    return saved;
  }
  async function accept(receipt: SyncReceipt, value?: SyncOperation) {
    const original: SyncOperation = value ?? { version: 1, requestId: receipt.request_id, createdAt: Date.now(), confirmed: true, change: { kind: "receipt", action: receipt.action } };
    keep({ ...original, confirmed: true, refused: false, rejected: false }, original.requestId);
    if (!live.current) return true;
    try {
      await callback.current(receipt, original.change.kind === "receipt" ? undefined : original.change);
      if (!live.current) return true;
      if (receipt.state === "done") {
        if (!keep(null, original.requestId)) {
          setShowRecovery(true);
          setError(t("结果已保存，但无法清理本机恢复记录。可以再次读取确认。", "The result is saved, but its local recovery record could not be cleared. Read again."));
        } else setError("");
      } else {
        setShowRecovery(true);
        setError("");
      }
    } catch (failure) {
      if (live.current) {
        setShowRecovery(true);
        setError(t("操作已接受，但未能刷新书签库。请重新读取结果。", "The operation was accepted, but the library could not refresh. Read the result again.") + " " + String(failure));
      }
    }
    return true;
  }
  async function lookup(requestId: string, signal: AbortSignal, kind?: SyncChangeRequest["kind"]) {
    try {
      const receipt = await api<unknown>(`/admin/library/sync/operations/${encodeURIComponent(requestId)}`, { signal });
      if (!validSyncReceipt(receipt, requestId, kind)) throw new Error(t("无法核对原同步操作的保存结果。", "The original synchronization result could not be verified."));
      return receipt;
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 404) return null;
      throw failure;
    }
  }
  async function execute(value: SyncOperation, signal: AbortSignal) {
    const request = syncRequest(value);
    if (!request) throw new Error(t("原结果已接受，只能读取或完成原发送。", "The original result was accepted. Only read it or complete its original delivery."));
    try {
      const result = await api<unknown>(request.path, { method: "POST", body: JSON.stringify(request.body), signal, timeoutMs: 20000 });
      const state = value.change.kind === "apply" && result && typeof result === "object" && "complete" in result && result.complete === false ? "pending" : "done";
      const receipt = { request_id: value.requestId, action: value.change.kind, state, result,
        current_status: value.change.kind === "apply" && result && typeof result === "object" && "status" in result ? result.status : result };
      if (!validSyncReceipt(receipt, value.requestId, actionOf(value))) throw new Error(t("同步返回内容不完整，原操作已保留。", "The synchronization response is incomplete. The original operation is retained."));
      return await accept(receipt, value);
    } catch (failure) {
      if (!live.current || signal.aborted) return false;
      setShowRecovery(true); setError(String(failure));
      const refused = failure instanceof ApiError && [400, 401, 403, 404, 409, 410, 413, 422].includes(failure.status);
      const retained = refused ? { ...value, refused: true } : value;
      if (refused) keep(retained, value.requestId);
      try {
        const receipt = await lookup(value.requestId, signal, actionOf(value));
        if (receipt) return await accept(receipt, retained);
        if (refused) keep({ ...retained, rejected: true }, value.requestId);
      } catch (readFailure) { if (live.current && !signal.aborted) setError(String(readFailure)); }
      return false;
    }
  }
  async function locked<T>(work: (signal: AbortSignal) => Promise<T>): Promise<T | undefined> {
    if (gate.current) return undefined;
    gate.current = true; if (live.current) { setBusy(true); setError(""); }
    const abort = new AbortController(); controller.current = abort;
    try { return await work(abort.signal); }
    catch (failure) { if (live.current && !abort.signal.aborted) { setShowRecovery(true); setError(String(failure)); } return undefined; }
    finally { gate.current = false; if (live.current) setBusy(false); }
  }
  async function run(change: SyncChangeRequest) {
    const disabling = change.kind === "configure" && !change.values.enabled && pending.current.every(value => value.confirmed);
    if (pending.current.length && !disabling) { setShowRecovery(true); return false; }
    return Boolean(await locked(async signal => {
      const value: SyncOperation = { version: 1, requestId: crypto.randomUUID(), createdAt: Date.now(), confirmed: false, change: structuredClone(change) };
      if (!saveSyncOperation(value)) throw new Error(t("无法保留本机同步恢复记录。请检查本机存储后重试。", "The local synchronization recovery record could not be saved. Check local storage and retry."));
      keep(value, value.requestId);
      return await execute(value, signal);
    }));
  }
  async function check(requestId: string, retry = false) {
    return locked(async signal => {
      const value = pending.current.find(item => item.requestId === requestId);
      const receipt = await lookup(requestId, signal, actionOf(value));
      if (receipt) {
        if (retry && receipt.state === "pending") {
          const result = await api<unknown>(`/admin/library/sync/operations/${encodeURIComponent(requestId)}/retry`, { method: "POST", body: "{}", signal, timeoutMs: 20000 });
          const next = { ...receipt, state: result && typeof result === "object" && "complete" in result && result.complete ? "done" : "pending", result,
            current_status: result && typeof result === "object" && "status" in result ? result.status : receipt.current_status };
          if (!validSyncReceipt(next, requestId, "apply")) throw new Error(t("无法核对原发送的完成结果。原同步已保留。", "The original delivery result could not be verified. The original sync is retained."));
          return await accept(next, value);
        }
        return await accept(receipt, value);
      }
      if (!value) throw new Error(t("未找到已接受的原同步。请重新读取设置。", "The accepted original sync was not found. Reload settings."));
      if (value.confirmed) throw new Error(t("原操作已接受，但暂时无法读取保存结果。请稍后再读。", "The original operation was accepted, but its saved result is unavailable. Read again later."));
      if (value.refused) keep({ ...value, rejected: true }, value.requestId);
      if (retry && !value.refused) return await execute(value, signal);
      return false;
    });
  }
  async function abandon(requestId: string): Promise<SyncChangeRequest | null> {
    const result = await locked(async signal => {
      const value = pending.current.find(item => item.requestId === requestId);
      if (!value || !value.rejected || value.confirmed || value.change.kind === "receipt") return null;
      const receipt = await lookup(requestId, signal, value.change.kind);
      if (receipt) { await accept(receipt, value); return null; }
      if (!keep(null, requestId)) throw new Error(t("无法清理本机恢复记录。原操作已保留。", "The local recovery record could not be cleared. The original operation is retained."));
      setError(""); return value.change;
    });
    return result ?? null;
  }
  useEffect(() => {
    live.current = true;
    const initial = [...pending.current];
    if (initial.length) void locked(async signal => {
      for (const value of initial) {
        const receipt = await lookup(value.requestId, signal, actionOf(value));
        if (receipt) await accept(receipt, value);
        else if (value.refused) keep({ ...value, rejected: true }, value.requestId);
      }
    });
    const changed = (event: StorageEvent) => {
      if (event.key === null || event.key.startsWith(syncStoragePrefix)) {
        pending.current = loadSyncOperations(); setOperations(pending.current); setShowRecovery(pending.current.length > 0);
      }
    };
    window.addEventListener("storage", changed);
    return () => { live.current = false; controller.current?.abort(); window.removeEventListener("storage", changed); };
  }, []);
  return { operations, busy, error, showRecovery, run, check, abandon, isBusy: () => gate.current };
}
