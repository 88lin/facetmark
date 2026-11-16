import { ApiError, type QueueSummary } from "./api.ts";
import { t } from "./i18n.ts";

export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return t("pop.tokenRejected");
    if (error.code === "network") return t("pop.serverUnreachable");
    if (error.code === "timeout") return t("opt.timeout");
    if (error.code === "permission") return t("opt.permissionDenied");
    if (error.code === "settings-changed") return t("opt.changedElsewhere");
    if (error.code === "invalid") return t("opt.badResponse");
  }
  return error instanceof Error ? error.message : String(error);
}

export function queueText(queue: QueueSummary): string {
  return [queue.ready && t("queue.ready", queue.ready), queue.waiting && t("queue.waiting", queue.waiting),
    queue.leased && t("queue.leased", queue.leased), queue.failed && t("queue.failed", queue.failed)]
    .filter(Boolean).join(" · ");
}

export async function workerRequest<T>(message: object): Promise<T> {
  let result: unknown;
  try { result = await chrome.runtime.sendMessage(message); }
  catch (error) { throw new Error(`${t("opt.swNoAnswer")} · ${error instanceof Error ? error.message : String(error)}`); }
  if (!result || typeof result !== "object" || !("ok" in result)) throw new Error(t("opt.swNoAnswer"));
  const value = result as Record<string, unknown>;
  if (value.ok !== true) {
    throw new ApiError(typeof value.error === "string" ? value.error : t("opt.swNoAnswer"),
      typeof value.status === "number" ? value.status : 0, typeof value.code === "string" ? value.code : "worker");
  }
  return value as T;
}
