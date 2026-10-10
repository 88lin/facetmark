export type Bookmark = {
  bookmark_id: number;
  title: string;
  url: string;
  domain: string;
  folder: string;
  summary?: string;
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
  state: string;
  current?: string;
  done?: string[];
  planned?: string[];
  error?: string;
  log?: string[];
  cancel_requested?: boolean;
  elapsed?: number;
  params?: { mode?: "index" | "fetch" | "summarize"; bookmark_ids?: number[] };
  items?: { done: number; total: number };
};
export type Setup = {
  library_revision?: string;
  bookmarks: number;
  demo: boolean;
  pending_apply: boolean;
  vector_compatible: boolean;
  has_vectors: boolean;
  channels: Record<string, { configured: boolean; tested: boolean }>;
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
  ) {
    super(message);
  }
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(typeof options.body === "string" ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  const data = await response.json();
  if (!response.ok)
    throw new ApiError(
      response.status,
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((item: { msg?: string }) => item.msg || "Invalid value").join("; ")
          : `HTTP ${response.status}`,
    );
  return data as T;
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
    const data = await response.json();
    throw new ApiError(response.status, typeof data.detail === "string" ? data.detail : `HTTP ${response.status}`);
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
