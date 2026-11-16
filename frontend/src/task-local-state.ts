import type { CollectionScope, Job } from "./api";

export type TaskStart = { mode: "index" | "fetch" | "summarize"; confirmed: boolean; bookmark_ids?: number[];
  scope?: CollectionScope | null; fetch?: boolean; force?: boolean; limit?: number | null;
  summary_language?: "zh" | "en"; summary_prompt?: string; preview_revision?: string; preview_prompt_hash?: string };
export type TaskChange = { kind: "start"; values: TaskStart }
  | { kind: "resume"; jobId: string; runId?: string }
  | { kind: "pause" | "cancel"; jobId: string; runId: string };
export type TaskOperation = { version: 1; requestId: string; createdAt: number; confirmed: boolean;
  refused?: boolean; rejected?: boolean; change: TaskChange };
export type TaskReceipt = { request_id: string; action: string; job_id: string; run_id: string;
  result: Job | { cancel_requested: boolean; job: Job }; job?: Job };
export const taskStoragePrefix = "fm-task-operation:";
const object = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === "object" && !Array.isArray(value));
const identity = (value: unknown): value is string => typeof value === "string" && /^[a-zA-Z0-9_.-]{1,128}$/.test(value);
const runIdentity = (value: unknown): value is string => typeof value === "string" && /^[a-zA-Z0-9_-]{1,64}$/.test(value);
const text = (value: unknown, max: number): value is string => typeof value === "string" && value.length <= max && !value.includes("\0");
const number = (value: unknown): value is number => typeof value === "number" && Number.isSafeInteger(value) && value > 0;
const ids = (value: unknown): value is number[] => Array.isArray(value) && value.length <= 10000 && value.every(number)
  && value.length === new Set(value).size;

function scope(value: unknown): CollectionScope | null | undefined {
  if (value === null) return null;
  if (!object(value)) return undefined;
  const result: CollectionScope = {};
  for (const key of ["folder", "tag", "domain", "q"] as const) {
    if (value[key] !== undefined) { if (!text(value[key], key === "q" ? 4096 : 2048)) return undefined; result[key] = value[key]; }
  }
  if (value.session !== undefined) { if (!number(value.session)) return undefined; result.session = value.session; }
  if (value.status !== undefined) {
    if (!["all", "pending", "done", "failed"].includes(String(value.status))) return undefined;
    result.status = value.status as CollectionScope["status"];
  }
  if (value.exclude_ids !== undefined) { if (!ids(value.exclude_ids)) return undefined; result.exclude_ids = [...value.exclude_ids]; }
  return result;
}

function start(value: unknown): TaskStart | null {
  if (!object(value) || !["index", "fetch", "summarize"].includes(String(value.mode)) || typeof value.confirmed !== "boolean") return null;
  if (value.mode !== "fetch" && !value.confirmed) return null;
  const result: TaskStart = { mode: value.mode as TaskStart["mode"], confirmed: value.confirmed };
  if (value.bookmark_ids !== undefined) {
    if (!ids(value.bookmark_ids) || !value.bookmark_ids.length || value.mode === "index") return null;
    result.bookmark_ids = [...value.bookmark_ids];
  }
  if (value.scope !== undefined) { const clean = scope(value.scope); if (clean === undefined || value.mode === "index") return null; result.scope = clean; }
  for (const key of ["fetch", "force"] as const) {
    if (value[key] !== undefined) { if (typeof value[key] !== "boolean") return null; result[key] = value[key]; }
  }
  if (value.limit !== undefined) { if (value.limit !== null && !number(value.limit)) return null; result.limit = value.limit; }
  if (value.summary_language !== undefined) {
    if (value.summary_language !== "zh" && value.summary_language !== "en") return null;
    result.summary_language = value.summary_language;
  }
  for (const key of ["summary_prompt", "preview_revision", "preview_prompt_hash"] as const) {
    if (value[key] !== undefined) { if (!text(value[key], key === "summary_prompt" ? 10000 : 256)) return null; result[key] = value[key]; }
  }
  return result;
}

function normalize(value: unknown): TaskOperation | null {
  if (!object(value) || value.version !== 1 || !identity(value.requestId) || typeof value.confirmed !== "boolean"
    || typeof value.createdAt !== "number" || !Number.isSafeInteger(value.createdAt) || value.createdAt < 0
    || (value.refused !== undefined && typeof value.refused !== "boolean")
    || (value.rejected !== undefined && typeof value.rejected !== "boolean") || (value.confirmed && (value.rejected || value.refused))
    || !object(value.change)) return null;
  const input = value.change;
  let change: TaskChange;
  if (input.kind === "start") { const values = start(input.values); if (!values) return null; change = { kind: "start", values }; }
  else if (input.kind === "resume" && runIdentity(input.jobId) && (input.runId === undefined || runIdentity(input.runId)))
    change = { kind: "resume", jobId: input.jobId, ...(input.runId !== undefined ? { runId: input.runId } : {}) };
  else if ((input.kind === "pause" || input.kind === "cancel") && runIdentity(input.jobId) && runIdentity(input.runId))
    change = { kind: input.kind, jobId: input.jobId, runId: input.runId };
  else return null;
  return { version: 1, requestId: value.requestId, createdAt: value.createdAt, confirmed: value.confirmed,
    ...(value.refused !== undefined ? { refused: value.refused } : {}),
    ...(value.rejected !== undefined ? { rejected: value.rejected } : {}), change };
}

export function loadTaskOperations(): TaskOperation[] {
  try {
    const result: TaskOperation[] = [];
    for (let index = 0; index < Math.min(localStorage.length, 10000); index++) {
      const key = localStorage.key(index);
      if (!key?.startsWith(taskStoragePrefix)) continue;
      const raw = localStorage.getItem(key);
      if (!raw || raw.length > 160000) continue;
      try { const value = normalize(JSON.parse(raw)); if (value && key === taskStoragePrefix + value.requestId) result.push(value); }
      catch { /* Leave unreadable records untouched. They cannot become task requests. */ }
    }
    return result.sort((a, b) => a.createdAt - b.createdAt).slice(0, 24);
  } catch { return []; }
}

export function saveTaskOperation(value: TaskOperation): boolean {
  try {
    const clean = normalize(value);
    if (!clean || (loadTaskOperations().length >= 24 && !localStorage.getItem(taskStoragePrefix + clean.requestId))) return false;
    const raw = JSON.stringify(clean); if (raw.length > 160000) return false;
    localStorage.setItem(taskStoragePrefix + clean.requestId, raw); return true;
  } catch { return false; }
}
export function clearTaskOperation(requestId: string): boolean {
  try { if (!identity(requestId)) return false; localStorage.removeItem(taskStoragePrefix + requestId); return true; }
  catch { return false; }
}
export function taskRequest(value: TaskOperation) {
  const change = value.change, request_id = value.requestId;
  if (change.kind === "start") return { path: "/admin/jobs/start", body: { ...structuredClone(change.values), request_id } };
  if (change.kind === "resume") return { path: "/admin/jobs/resume", body: { resume_id: change.jobId,
    ...(change.runId !== undefined ? { resume_run_id: change.runId } : {}), confirmed: true, request_id } };
  return { path: `/admin/jobs/${change.kind}`, body: { job_id: change.jobId, run_id: change.runId, request_id } };
}
export function taskResult(value: unknown, change: TaskChange): Job | null {
  const job = change.kind === "cancel" && object(value) ? value.job : value;
  if (!object(job) || !runIdentity(job.id) || !runIdentity(job.run_id) || !text(job.state, 32) || !job.state) return null;
  if (change.kind !== "start" && (job.id !== change.jobId || (change.kind !== "resume" && job.run_id !== change.runId))) return null;
  return job as Job;
}
export function validTaskReceipt(value: unknown, operation: TaskOperation): value is TaskReceipt {
  if (!object(value) || value.request_id !== operation.requestId || value.action !== operation.change.kind) return false;
  const result = taskResult(value.result, operation.change);
  return Boolean(result && value.job_id === result.id && value.run_id === result.run_id);
}
