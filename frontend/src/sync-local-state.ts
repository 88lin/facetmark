import type { SyncConfig, SyncDraft, SyncPreview, SyncReceipt, SyncStatus } from "./sync-types";

export type SyncChangeRequest = { kind: "configure"; values: SyncConfig & { expected_revision?: string } }
  | { kind: "apply"; previewId: string; resolutions: Record<string, string> };
export type SyncOperation = { version: 1; requestId: string; createdAt: number; confirmed: boolean;
  refused?: boolean; rejected?: boolean; change: SyncChangeRequest | { kind: "receipt"; action: "configure" | "apply" } };
export type SyncWorkspace = { version: 1; draft: SyncDraft; configRevision?: string; previewId?: string; resolutions: Record<string, string>; confirmed: boolean };
export const syncStoragePrefix = "fm-sync-operation:";
export const syncWorkspaceKey = "fm-sync-workspace";
const object = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === "object" && !Array.isArray(value));
const identity = (value: unknown): value is string => typeof value === "string" && /^[a-zA-Z0-9_.-]{1,128}$/.test(value);
const folder = (value: unknown): value is string => typeof value === "string" && value.length <= 4096 && !value.includes("\0");
const revision = (value: unknown): value is string => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const quantity = (value: unknown): value is number => typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const path = (value: unknown): value is string => typeof value === "string" && value.length <= 32768 && !value.includes("\0");
function counts(value: unknown): boolean {
  return object(value) && ["upload_new", "upload_update", "upload_delete", "download_new", "download_update", "download_delete", "unchanged", "conflicts"]
    .every(key => quantity(value[key]));
}
function metadata(value: unknown): boolean {
  return value === null || (object(value) && typeof value.url === "string" && /^https?:\/\//.test(value.url)
    && typeof value.title === "string" && typeof value.folder === "string" && Array.isArray(value.tags)
    && value.tags.every(tag => typeof tag === "string") && (value.date_added === null || (quantity(value.date_added) && value.date_added <= 32503680000)));
}
function config(value: unknown): SyncConfig | null {
  if (!object(value) || !folder(value.folder) || typeof value.enabled !== "boolean" || typeof value.auto_sync !== "boolean"
    || typeof value.poll_seconds !== "number" || !Number.isInteger(value.poll_seconds) || value.poll_seconds < 30 || value.poll_seconds > 3600) return null;
  return { folder: value.folder, enabled: value.enabled, auto_sync: value.auto_sync, poll_seconds: value.poll_seconds };
}
function resolutions(value: unknown): Record<string, string> | null {
  if (!object(value) || Object.keys(value).length > 100000) return null;
  const result: Record<string, string> = {};
  for (const [key, choice] of Object.entries(value)) {
    if (!/^[0-9a-f-]{36}$/.test(key) || typeof choice !== "string" || !/^(local|remote|delete|remote:[0-9a-f-]{36})$/.test(choice)) return null;
    result[key] = choice;
  }
  return result;
}
function normalize(value: unknown): SyncOperation | null {
  if (!object(value) || value.version !== 1 || !identity(value.requestId) || typeof value.confirmed !== "boolean"
    || typeof value.createdAt !== "number" || !Number.isSafeInteger(value.createdAt) || value.createdAt < 0
    || (value.refused !== undefined && typeof value.refused !== "boolean")
    || (value.rejected !== undefined && typeof value.rejected !== "boolean")
    || (value.confirmed && (value.refused || value.rejected)) || !object(value.change)) return null;
  let change: SyncOperation["change"];
  if (value.change.kind === "configure") {
    const values = config(value.change.values); if (!values || !object(value.change.values)) return null;
    const expected = value.change.values.expected_revision;
    if (expected !== undefined && !revision(expected)) return null;
    change = { kind: "configure", values: { ...values, ...(expected !== undefined ? { expected_revision: expected } : {}) } };
  } else if (value.change.kind === "apply" && identity(value.change.previewId) && value.change.previewId.length <= 64) {
    const choices = resolutions(value.change.resolutions); if (!choices) return null;
    change = { kind: "apply", previewId: value.change.previewId, resolutions: choices };
  } else if (value.change.kind === "receipt" && value.confirmed && (value.change.action === "configure" || value.change.action === "apply")) change = { kind: "receipt", action: value.change.action };
  else return null;
  return { version: 1, requestId: value.requestId, createdAt: value.createdAt, confirmed: value.confirmed,
    ...(value.refused !== undefined ? { refused: value.refused } : {}), ...(value.rejected !== undefined ? { rejected: value.rejected } : {}), change };
}
export function loadSyncOperations(): SyncOperation[] {
  try {
    const result: SyncOperation[] = [];
    for (let index = 0; index < Math.min(localStorage.length, 10000); index++) {
      const key = localStorage.key(index); if (!key?.startsWith(syncStoragePrefix)) continue;
      const raw = localStorage.getItem(key); if (!raw || raw.length > 3000000) continue;
      try { const value = normalize(JSON.parse(raw)); if (value && key === syncStoragePrefix + value.requestId) result.push(value); }
      catch { /* Unreadable records remain untouched and cannot become requests. */ }
    }
    return result.sort((a, b) => a.createdAt - b.createdAt).slice(0, 8);
  } catch { return []; }
}
export function saveSyncOperation(value: SyncOperation): boolean {
  try {
    const clean = normalize(value);
    if (!clean || (loadSyncOperations().length >= 8 && !localStorage.getItem(syncStoragePrefix + clean.requestId))) return false;
    const raw = JSON.stringify(clean); if (raw.length > 3000000) return false;
    localStorage.setItem(syncStoragePrefix + clean.requestId, raw); return true;
  } catch { return false; }
}
export function clearSyncOperation(requestId: string): boolean {
  try { if (!identity(requestId)) return false; localStorage.removeItem(syncStoragePrefix + requestId); return true; }
  catch { return false; }
}
export function syncRequest(value: SyncOperation) {
  const change = value.change;
  if (change.kind === "receipt") return null;
  return change.kind === "configure" ? { path: "/admin/library/sync/config", body: { ...change.values, request_id: value.requestId } }
    : { path: "/admin/library/sync/apply", body: { preview_id: change.previewId, resolutions: { ...change.resolutions }, request_id: value.requestId } };
}
function workspace(value: unknown): SyncWorkspace | null {
  if (!object(value) || value.version !== 1 || !object(value.draft) || !folder(value.draft.folder)
    || typeof value.draft.enabled !== "boolean" || typeof value.draft.auto_sync !== "boolean"
    || typeof value.draft.poll_seconds !== "string" || value.draft.poll_seconds.length > 32 || typeof value.confirmed !== "boolean"
    || (value.previewId !== undefined && (!identity(value.previewId) || value.previewId.length > 64))
    || (value.configRevision !== undefined && !revision(value.configRevision))) return null;
  const choices = resolutions(value.resolutions); if (!choices) return null;
  return { version: 1, draft: { folder: value.draft.folder, enabled: value.draft.enabled, auto_sync: value.draft.auto_sync,
    poll_seconds: value.draft.poll_seconds }, ...(value.previewId !== undefined ? { previewId: value.previewId } : {}),
    ...(value.configRevision !== undefined ? { configRevision: value.configRevision } : {}),
    resolutions: choices, confirmed: value.confirmed };
}
export function loadSyncWorkspace(): SyncWorkspace | null {
  try { const raw = localStorage.getItem(syncWorkspaceKey); return raw && raw.length <= 3000000 ? workspace(JSON.parse(raw)) : null; }
  catch { return null; }
}
export function saveSyncWorkspace(value: SyncWorkspace): boolean {
  try { const clean = workspace(value); if (!clean) return false; const raw = JSON.stringify(clean); if (raw.length > 3000000) return false;
    localStorage.setItem(syncWorkspaceKey, raw); return true; }
  catch { return false; }
}
export function validSyncStatus(value: unknown): value is SyncStatus {
  if (!config(value) || !object(value) || typeof value.configured !== "boolean" || typeof value.needs_review !== "boolean"
    || typeof value.last_error !== "string" || !quantity(value.pending_conflicts)
    || (value.last_sync_at !== null && !quantity(value.last_sync_at))
    || (value.last_sync_id !== undefined && value.last_sync_id !== null && !identity(value.last_sync_id))
    || !revision(value.config_revision) || !Array.isArray(value.pending_operations)) return false;
  const ids = new Set<string>();
  return value.pending_operations.every(item => {
    if (!object(item) || !identity(item.request_id) || ids.has(item.request_id) || !quantity(item.created_at)
      || !folder(item.folder) || !counts(item.counts) || (item.backup_path !== null && !path(item.backup_path)) || typeof item.error !== "string") return false;
    ids.add(item.request_id); return true;
  });
}
export function validSyncPreview(value: unknown, previewId?: string): value is SyncPreview {
  if (!object(value) || !identity(value.preview_id) || value.preview_id.length > 64 || (previewId !== undefined && value.preview_id !== previewId)
    || !quantity(value.expires_at) || !counts(value.counts) || !quantity(value.excluded_karakeep) || !quantity(value.excluded_unsupported)
    || typeof value.stale !== "boolean" || !Array.isArray(value.conflicts) || !Array.isArray(value.changes)
    || !object(value.counts) || value.counts.conflicts !== value.conflicts.length) return false;
  const ids = new Set<string>();
  const conflictsValid = value.conflicts.every(item => {
    if (!object(item) || !identity(item.id) || ids.has(item.id) || typeof item.reason !== "string"
      || (item.can_delete !== undefined && typeof item.can_delete !== "boolean") || !metadata(item.local) || !metadata(item.remote)
      || !Array.isArray(item.remote_versions)) return false;
    ids.add(item.id);
    const choices = new Set<string>();
    return item.remote_versions.every(version => {
      if (!object(version) || typeof version.choice !== "string" || !/^remote:[0-9a-f-]{36}$/.test(version.choice)
        || choices.has(version.choice) || !metadata(version.record)) return false;
      choices.add(version.choice); return true;
    });
  });
  return conflictsValid && value.changes.every(item => {
    if (!object(item) || !identity(item.id) || ids.has(item.id) || !metadata(item.local) || !metadata(item.remote) || !metadata(item.target)
      || !Array.isArray(item.directions) || !item.directions.length || new Set(item.directions).size !== item.directions.length
      || !item.directions.every(direction => direction === "upload" || direction === "download")) return false;
    ids.add(item.id); return true;
  });
}
export function validSyncReceipt(value: unknown, requestId: string, action?: SyncChangeRequest["kind"]): value is SyncReceipt {
  if (!object(value) || value.request_id !== requestId || (value.action !== "configure" && value.action !== "apply")
    || (action !== undefined && value.action !== action) || (value.state !== "done" && value.state !== "pending") || !validSyncStatus(value.current_status)) return false;
  if (value.action === "configure") return value.state === "done" && validSyncStatus(value.result);
  return object(value.result) && value.result.request_id === requestId && value.result.accepted === true
    && value.result.complete === (value.state === "done") && counts(value.result.counts) && validSyncStatus(value.result.status)
    && typeof value.result.error === "string" && folder(value.result.folder)
    && (value.result.backup_path === null || path(value.result.backup_path))
    && (value.result.published_commit === null || (typeof value.result.published_commit === "string" && /^[0-9a-f-]{36}$/.test(value.result.published_commit)));
}
