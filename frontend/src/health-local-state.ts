export type HealthReport = {
  considered: number; probed: number; escalated: number; recovered_bodies: number;
  by_status: Record<string, number>; confirmed_gone: number[]; errors: string[];
};
export type HealthRun = {
  request_id: string; state: "running" | "stopping" | "done" | "partial" | "failed" | "cancelled" | "interrupted" | "closed";
  params: { limit: number; ids: number[] | null; expected_library: string | null }; targets_count: number;
  started_at: number; finished_at: number | null; report: HealthReport | null; error: string;
};
export type HealthOperation = { version: 1; requestId: string; createdAt: number; limit: number; libraryId: string };
export const healthStoragePrefix = "fm-health-operation:";
const record = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === "object" && !Array.isArray(value));
const integer = (value: unknown): value is number => Number.isSafeInteger(value) && Number(value) >= 0;
const requestId = (value: unknown): value is string => typeof value === "string" && value !== "current" && /^[a-zA-Z0-9_.-]{1,128}$/.test(value);
export const validHealthLibrary = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
export const validHealthCounts = (value: unknown): value is Record<string, number> => record(value) && Object.values(value).every(integer);
export function validHealthReport(value: unknown): value is HealthReport {
  return record(value) && ["considered", "probed", "escalated", "recovered_bodies"].every(key => integer(value[key]))
    && validHealthCounts(value.by_status) && Array.isArray(value.confirmed_gone) && value.confirmed_gone.every(id => integer(id) && id > 0)
    && Array.isArray(value.errors) && value.errors.every(error => typeof error === "string");
}
export function validHealthRun(value: unknown): value is HealthRun {
  if (!record(value) || !requestId(value.request_id) || !["running", "stopping", "done", "partial", "failed", "cancelled", "interrupted", "closed"].includes(String(value.state))
    || !record(value.params) || !integer(value.params.limit) || value.params.limit < 1 || value.params.limit > 1000
    || value.params.ids !== null && (!Array.isArray(value.params.ids) || !value.params.ids.every(id => integer(id) && id > 0))
    || value.params.expected_library !== null && !validHealthLibrary(value.params.expected_library)
    || !integer(value.targets_count) || value.targets_count > value.params.limit || !integer(value.started_at)
    || value.finished_at !== null && !integer(value.finished_at) || typeof value.error !== "string"
    || value.report !== null && !validHealthReport(value.report)) return false;
  return !["done", "partial"].includes(String(value.state)) || validHealthReport(value.report);
}
export function originalHealthRun(value: unknown, operation: HealthOperation): HealthRun | null {
  return validHealthRun(value) && value.request_id === operation.requestId
    && value.params.limit === operation.limit && value.params.ids === null && value.params.expected_library === operation.libraryId ? value : null;
}
function original(value: unknown): HealthOperation {
  if (!record(value) || value.version !== 1 || !requestId(value.requestId) || !integer(value.createdAt)
    || !integer(value.limit) || value.limit < 1 || value.limit > 1000 || !validHealthLibrary(value.libraryId)) throw new Error("The saved original link check could not be read");
  return { version: 1, requestId: value.requestId, createdAt: value.createdAt, limit: value.limit, libraryId: value.libraryId };
}
export function loadHealthOperations(libraryId?: string): HealthOperation[] {
  const found: HealthOperation[] = [];
  for (let index = 0; index < localStorage.length; index++) {
    const key = localStorage.key(index);
    if (!key?.startsWith(healthStoragePrefix)) continue;
    const raw = localStorage.getItem(key);
    if (raw === null || raw.length > 1024) throw new Error("The saved original link check could not be read");
    const value = original(JSON.parse(raw));
    if (key !== healthStoragePrefix + value.requestId) throw new Error("The saved original link check could not be read");
    found.push(value);
  }
  return found.filter(value => !libraryId || value.libraryId === libraryId).sort((a, b) => a.createdAt - b.createdAt || a.requestId.localeCompare(b.requestId));
}
export function saveHealthOperation(value: HealthOperation): void {
  const safe = original(value), current = loadHealthOperations(), existing = current.find(item => item.requestId === safe.requestId);
  if (existing && JSON.stringify(existing) !== JSON.stringify(safe)) throw new Error("Keep the original link check unchanged");
  if (!existing && current.length >= 8) throw new Error("Finish saved link checks before making another request");
  localStorage.setItem(healthStoragePrefix + safe.requestId, JSON.stringify(safe));
}
export function clearHealthOperation(id: string): void {
  if (!requestId(id)) throw new Error("Invalid original link check request");
  localStorage.removeItem(healthStoragePrefix + id);
}
export function healthRequest(value: HealthOperation) {
  const safe = original(value);
  return { limit: safe.limit, request_id: safe.requestId, expected_library: safe.libraryId };
}
