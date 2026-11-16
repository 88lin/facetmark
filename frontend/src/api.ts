export type Bookmark = {
  bookmark_id: number;
  title: string;
  ai_title?: string;
  url: string;
  domain: string;
  folder: string;
  summary?: string;
  summary_basis?: string;
  summary_status?: "pending" | "done" | "failed";
  summary_error?: string;
  summary_language?: string;
  snippet?: string;
  tags?: string[];
  date_added?: number;
  body_text?: string;
  key_points?: string[];
  intent_queries?: string[];
  privacy_skipped?: boolean;
  indexed?: { summary_basis: string; enriched_by: string; error: string };
  source?: string;
  managed_externally?: boolean;
  facets?: string[];
};
export type Page = {
  summary_counts?: { total: number; pending: number; done: number; failed: number };
  items?: Bookmark[];
  hits?: Bookmark[];
  total: number;
  offset: number;
  limit: number;
  depth?: number;
  has_more: boolean;
  depth_capped?: boolean;
  degraded_from?: string;
};
export type Job = {
  id?: string;
  resumable?: boolean;
  pause_requested?: boolean;
  state: string;
  current?: string;
  done?: string[];
  planned?: string[];
  error?: string;
  log?: string[];
  cancel_requested?: boolean;
  elapsed?: number;
  params?: { mode?: "index" | "fetch" | "summarize"; bookmark_ids?: number[]; scope?: CollectionScope | null };
  items?: { done: number; total: number; failed?: number };
};
export type CollectionScope = {
  folder?: string; tag?: string; domain?: string; session?: number;
  q?: string; status?: "all" | "pending" | "done" | "failed"; exclude_ids?: number[];
};
export type Setup = {
  library_revision?: string;
  bookmarks: number;
  demo: boolean;
  summary_language?: "auto" | "zh" | "en";
  pending_apply: boolean;
  vector_compatible: boolean;
  has_vectors: boolean;
  channels: Record<string, { configured: boolean; tested: boolean;
    validation?: "ready" | "unconfigured" | "changed" | "untested"; tested_model?: string; tested_at?: number | null }>;
  stats: Record<string, unknown>;
};
export type Setting = {
  key: string;
  value: unknown;
  set: boolean;
  locked: boolean;
  secret: boolean;
  pending_restart: boolean;
  source: string;
};
export type Probe = {
  ok: boolean;
  ms?: number;
  model: string;
  error?: string;
  warning?: string;
  dim?: number;
  expected_dim?: number;
  dim_matches?: boolean;
};
let token = "";
export const setToken = (value: string) => {
  token = value;
};
export const getToken = () => token;
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public readonly details?: Readonly<Record<string, unknown>>,
  ) {
    super(message);
  }
}
const serviceMessage = (zh: string, en: string) =>
  typeof document !== "undefined" && document.documentElement.lang.startsWith("zh") ? zh : en;

async function responseError(response: Response): Promise<ApiError> {
  let data: { detail?: unknown } | null = null;
  try { data = await response.json(); } catch { /* A proxy error page is not JSON. */ }
  const detail = data?.detail;
  const details = detail && typeof detail === "object" && !Array.isArray(detail)
    ? detail as Record<string, unknown> : undefined;
  const message = typeof detail === "string" ? detail
    : Array.isArray(detail) ? detail.map(item => typeof item?.msg === "string" ? item.msg : "Invalid value").join("; ")
      : typeof details?.message === "string" && details.message ? details.message
      : serviceMessage("服务请求失败（HTTP " + response.status + "），请重试。",
        "Service request failed (HTTP " + response.status + "). Please retry.");
  return new ApiError(response.status, message, details);
}

type ApiOptions = RequestInit & { timeoutMs?: number };
export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  // Reads should recover from an unresponsive local service. Writes and model
  // operations keep their server-side budgets; aborting them does not undo them.
  const { timeoutMs = (options.method || "GET").toUpperCase() === "GET" ? 20_000 : 0, ...init } = options;
  const headers = new Headers(init.headers);
  if (token && !headers.has("Authorization")) headers.set("Authorization", "Bearer " + token);
  if (typeof init.body === "string" && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const abort = new AbortController();
  const cancel = () => abort.abort(init.signal?.reason);
  if (init.signal?.aborted) cancel();
  else init.signal?.addEventListener("abort", cancel, { once: true });
  let timedOut = false;
  const timer = timeoutMs > 0 ? setTimeout(() => { timedOut = true; abort.abort(); }, timeoutMs) : undefined;
  try {
    const response = await fetch(path, { cache: "no-store", ...init, headers, signal: abort.signal });
    if (!response.ok) throw await responseError(response);
    if (response.status === 204 || response.status === 205) return undefined as T;
    try { return await response.json() as T; }
    catch (cause) {
      if (abort.signal.aborted) throw cause;
      throw new ApiError(response.status, serviceMessage("服务返回了无法读取的结果，请重试。",
        "The service returned an unreadable response. Please retry."));
    }
  } catch (cause) {
    if (init.signal?.aborted) throw init.signal.reason;
    if (timedOut) throw new ApiError(0, serviceMessage("服务响应超时，请重试。",
      "The service did not respond in time. Please retry."));
    if (cause instanceof ApiError) throw cause;
    throw new ApiError(0, serviceMessage("无法连接本地服务，请检查服务是否运行后重试。",
      "Cannot reach the local service. Check that it is running, then retry."));
  } finally {
    clearTimeout(timer);
    init.signal?.removeEventListener("abort", cancel);
  }
}
export const post = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body), signal });

export async function downloadExport(body: unknown) {
  const response = await fetch("/admin/library/export", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  const blob = await response.blob();
  const address = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = address;
  anchor.download = response.headers.get("content-disposition")?.match(/filename="?([^";]+)"?/)?.[1] || "facetmark-export.json";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(address), 1000);
}
export const query = (values: Record<string, string | number | undefined>) =>
  new URLSearchParams(
    Object.entries(values)
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)]),
  ).toString();
export const safeUrl = (url: string) => {
  try {
    const parsed = new URL(url);
    return ["https:", "http:"].includes(parsed.protocol) ? parsed.href : undefined;
  } catch {
    return undefined;
  }
};
