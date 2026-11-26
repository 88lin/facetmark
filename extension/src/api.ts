// One place that knows how to talk to the local server.
//
// Requests go out from extension contexts, never from a content script.
// Chrome 142 tightened Local Network Access: a page-context fetch to 127.0.0.1
// can be blocked or prompted, while an extension worker holding an explicit
// host permission is not. Keeping the transport here also means the pairing
// token never enters a web page's world.

export interface Settings {
  endpoint: string;
  token: string;
  channelB: boolean;
  paused: boolean;
}

export const DEFAULTS: Settings = {
  endpoint: "http://127.0.0.1:8787",
  token: "",
  channelB: false,
  paused: false,
};

export async function loadSettings(): Promise<Settings> {
  const got = await chrome.storage.local.get(DEFAULTS);
  return {
    endpoint: typeof got.endpoint === "string" && got.endpoint.trim() ? got.endpoint : DEFAULTS.endpoint,
    token: typeof got.token === "string" ? got.token : "",
    channelB: got.channelB === true,
    paused: got.paused === true,
  };
}

export async function saveSettings(patch: Partial<Settings>): Promise<void> {
  await chrome.storage.local.set(patch);
}

// Written without a constructor parameter property on purpose: that is the one
// piece of TypeScript that cannot be erased by simply deleting types, and every
// file here has to survive `node --experimental-strip-types` so the tests can
// import the shipping source rather than a compiled copy of it.
export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = "http") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export interface RequestContext {
  signal?: AbortSignal;
  settings?: Settings;
}

export const REQUEST_TIMEOUT_MS = 20_000;
export const PAGE_ORIGINS = ["http://*/*", "https://*/*"];

export function normalizeEndpoint(raw: string): string {
  let url: URL;
  try { url = new URL(raw.trim() || DEFAULTS.endpoint); }
  catch { throw new ApiError("Enter a valid http:// or https:// server address", 0, "endpoint"); }
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new ApiError("Use an http:// or https:// server address without credentials, query or fragment", 0, "endpoint");
  }
  return url.href.replace(/\/+$/, "");
}

export function requiredOrigins(endpoint: string, pages: boolean): string[] {
  const server = new URL(normalizeEndpoint(endpoint));
  return [...new Set([`${server.protocol}//${server.hostname}/*`, ...(pages ? PAGE_ORIGINS : [])])];
}

async function request<T>(path: string, init: RequestInit = {}, context: RequestContext = {}): Promise<T> {
  const s = context.settings ?? await loadSettings();
  const endpoint = normalizeEndpoint(s.endpoint);
  const external = context.signal ?? init.signal;
  const controller = new AbortController();
  const headers = new Headers(init.headers ?? {});
  headers.set("Content-Type", "application/json");
  headers.set("X-Facetmark-Client", "extension");
  if (s.token) headers.set("Authorization", `Bearer ${s.token}`);
  let timedOut = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let rejectAbort: (error: Error) => void = () => undefined;
  const aborted = new Promise<never>((_resolve, reject) => { rejectAbort = reject; });
  const onAbort = () => {
    controller.abort();
    rejectAbort(new DOMException("Request cancelled", "AbortError"));
  };
  external?.addEventListener("abort", onAbort, { once: true });
  if (external?.aborted) onAbort();
  const deadline = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
      reject(new ApiError("Server request timed out; check the connection and retry", 0, "timeout"));
    }, REQUEST_TIMEOUT_MS);
  });
  const read = async (): Promise<T> => {
    if (external?.aborted) throw new DOMException("Request cancelled", "AbortError");
    const res = await fetch(`${endpoint}${path}`, { ...init, signal: controller.signal, headers });
    const raw = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(raw); }
    catch {
      if (res.ok) throw new ApiError("Server returned an unreadable response; keep the original operation and retry", res.status, "invalid");
    }
    if (res.status === 401) throw new ApiError("Pairing token rejected; open settings", 401);
    if (!res.ok) {
      const record = parsed && typeof parsed === "object" ? parsed as Record<string, unknown> : {};
      const detail = record.detail;
      const message = typeof detail === "string" ? detail : detail && typeof detail === "object"
        && typeof (detail as Record<string, unknown>).message === "string" ? String((detail as Record<string, unknown>).message) : "";
      throw new ApiError(message || `Server returned HTTP ${res.status}; retry when it is available`, res.status);
    }
    return parsed as T;
  };
  try {
    return await Promise.race([read(), deadline, aborted]);
  } catch (error) {
    if (external?.aborted) throw new DOMException("Request cancelled", "AbortError");
    if (timedOut) throw new ApiError("Server request timed out; check the connection and retry", 0, "timeout");
    if (error instanceof ApiError) throw error;
    throw new ApiError("Server unreachable; start Facetmark and check the saved address", 0, "network");
  } finally {
    if (timer !== undefined) clearTimeout(timer);
    external?.removeEventListener("abort", onAbort);
  }
}

// These mirror `SearchHit.as_dict` and `SearchResponse.as_dict` in
// `search/pipeline.py`. `request<T>` is an unchecked cast -- the compiler will
// believe anything written here -- so the boundary is pinned from the Python
// side instead, by a test that reads this file and compares it against a real
// response. Renaming a field there and not here is a caught error, not a
// silent `undefined` on screen.
export interface Hit {
  bookmark_id: number;
  url: string;
  title: string;
  score: number;
  /** Which facets retrieved this row: the closest thing to "why am I seeing this". */
  facets: string[];
  snippet: string;
  folder: string;
  domain: string;
  date_added: number | null;
  cold: boolean;
  /** The user's own filing words. Verbatim, never translated. */
  tags: string[];
  /** Expansion rows only: the bookmark id this one was reached from. */
  via?: number;
  via_kind?: string;
}

/**
 * What the server parsed out of the query string, when it parsed anything.
 *
 * `null` on the response means the query carried no syntax at all, which is
 * not the same as "no filters matched": it is the compatibility guarantee,
 * that a plain query took the path it always took. Every key here is absent
 * rather than empty when it has nothing to say, so `?? []` is the idiom.
 */
export interface QueryFilters {
  fields?: { field: string; value: string; negate: boolean }[];
  /** Free words the query excluded with a leading `-`. */
  exclude?: string[];
  sort?: string;
  /**
   * Tokens that looked like syntax and did not parse (`added:90d`). The server
   * answered the rest of the query rather than failing, so this is the only
   * signal a user gets that part of what they typed did not apply.
   */
  ignored?: string[];
}

export interface SearchResponse {
  query: string;
  hits: Hit[];
  /** One-hop neighbours of the top hits. Its own group, never interleaved. */
  expanded: Hit[];
  /** A breakdown by stage, not a scalar: `understand`, `facets`, ..., `total`. */
  took_ms: Record<string, number>;
  config: string;
  understanding?: { labels: string[]; time_window?: [number, number] | null } | null;
  /** The window actually served, after the server clamped it. Not an echo. */
  limit: number;
  offset: number;
  /**
   * The candidate depth this ranking was produced at. Send it back on the next
   * page: with more than one facet in play, fusion only orders identically
   * across pages when the depth is held fixed.
   */
  depth: number;
  /**
   * How many documents matched. Exact for a browse, where the filters are the
   * retrieval; for a ranked query it is the size of the pool that was ranked,
   * and a lower bound on the library's matches when `depth_capped`.
   */
  total: number;
  has_more: boolean;
  /** The pool was cut by the server's depth ceiling, not by the library ending. */
  depth_capped: boolean;
  /** The query language the server read out of `query`, or `null` for none. */
  filters: QueryFilters | null;
  /** The sort directive that applied, `""` when the query asked for none. */
  sort: string;
}

export interface QueueItem {
  bookmark_id: number;
  url: string;
  title: string;
  reason: string;
  attempt: number;
  lease_id: string;
}

export interface CompleteBody {
  bookmark_id: number;
  body?: string;
  title?: string;
  final_url?: string;
  error?: string;
  lease_id: string;
  source_url: string;
  request_id: string;
}

export interface SaveBody {
  url: string;
  title: string;
  folder?: string;
  tags?: string[];
  request_id?: string;
}

export interface SaveResult { bookmark_id: number; created?: boolean; tags?: string[] }

function validate<T>(value: T, valid: boolean, message = "Server response is incomplete; keep the original operation and retry"): T {
  if (!valid) throw new ApiError(message, 200, "invalid");
  return value;
}

function record(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function validHit(hit: unknown): boolean {
  return record(hit) && Number.isSafeInteger(hit.bookmark_id) && Number(hit.bookmark_id) > 0
    && typeof hit.url === "string" && typeof hit.title === "string"
    && typeof hit.domain === "string" && typeof hit.folder === "string"
    && typeof hit.snippet === "string" && typeof hit.cold === "boolean"
    && strings(hit.tags) && strings(hit.facets)
    && (hit.via_kind === undefined || typeof hit.via_kind === "string");
}

function validFilters(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  return record(value) && (value.sort === undefined || typeof value.sort === "string")
    && (value.exclude === undefined || strings(value.exclude))
    && (value.ignored === undefined || strings(value.ignored))
    && (value.fields === undefined || (Array.isArray(value.fields) && value.fields.every(
      (field) => record(field) && typeof field.field === "string" && typeof field.value === "string"
        && typeof field.negate === "boolean",
    )));
}

function searchResult(value: SearchResponse): SearchResponse {
  return validate(value, record(value) && Array.isArray(value.hits) && value.hits.every(validHit)
    && Array.isArray(value.expanded) && value.expanded.every(validHit)
    && record(value.took_ms) && Object.values(value.took_ms).every((ms) => typeof ms === "number" && Number.isFinite(ms) && ms >= 0)
    && [value.limit, value.offset, value.depth, value.total].every((n) => Number.isSafeInteger(n) && n >= 0)
    && typeof value.has_more === "boolean" && typeof value.depth_capped === "boolean"
    && validFilters(value.filters)
    && (value.understanding === null || value.understanding === undefined
      || (record(value.understanding) && strings(value.understanding.labels))),
  "Search returned an incomplete response; retry the search");
}

export const api = {
  health: (context?: RequestContext) =>
    request<{ ok: boolean; version: string; bookmarks: number; provider: string }>("/health", {}, context),
  stats: () => request<Record<string, unknown>>("/stats"),
  quick: (q: string, limit = 10, offset = 0, depth?: number, context?: RequestContext) =>
    request<SearchResponse>(
      `/quick?q=${encodeURIComponent(q)}&limit=${limit}&offset=${offset}` +
        (depth ? `&depth=${depth}` : ""),
      {}, context,
    ).then(searchResult),
  search: (q: string, limit = 20, offset = 0, depth?: number, context?: RequestContext) =>
    request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify(depth ? { q, limit, offset, depth } : { q, limit, offset }),
    }, context).then(searchResult),
  save: (body: SaveBody, context?: RequestContext) =>
    request<SaveResult>("/bookmark", {
      method: "POST",
      body: JSON.stringify(body),
    }, context).then((value) => validate(value, !!value && Number.isSafeInteger(value.bookmark_id) && value.bookmark_id > 0
      && (value.created === undefined || typeof value.created === "boolean"))),
  opened: (bookmark_id: number, query: string, context?: RequestContext) =>
    request<{ ok: boolean }>("/open", {
      method: "POST",
      body: JSON.stringify({ bookmark_id, query }),
    }, context),
  queueNext: (n = 3, context?: RequestContext) =>
    request<{
      items: QueueItem[];
      queue: Record<string, number>;
      waiting: number;
      busy?: boolean;
    }>(`/queue/next?n=${n}`, {}, context).then((value) => validate(value, !!value && Array.isArray(value.items)
      && value.items.every((item) => record(item) && Number.isSafeInteger(item.bookmark_id) && item.bookmark_id > 0
        && typeof item.url === "string" && /^https?:\/\//i.test(item.url) && typeof item.title === "string"
        && typeof item.lease_id === "string" && !!item.lease_id)
      && (value.busy === undefined || typeof value.busy === "boolean"),
    "Update Facetmark to support recoverable browser reading")),
  queueComplete: (body: CompleteBody, context?: RequestContext) =>
    request<{ bookmark_id: number; stored: boolean; changed: boolean;
              queue: Record<string, number> }>("/queue/complete", {
      method: "POST",
      body: JSON.stringify(body),
    }, context).then((value) => validate(value, !!value && value.bookmark_id === body.bookmark_id
      && typeof value.stored === "boolean" && typeof value.changed === "boolean")),
  queueRelease: (items: Pick<QueueItem, "bookmark_id" | "lease_id">[], context?: RequestContext) =>
    request<{ released: number }>("/queue/release", { method: "POST", body: JSON.stringify({ items }) }, context),
  receipt: (request_id: string, context?: RequestContext) =>
    request<{ request_id: string; action: string; result: Record<string, unknown> }>(
      `/client/operations/${encodeURIComponent(request_id)}`, {}, context,
    ).then((value) => validate(value, !!value && value.request_id === request_id
      && ["save", "complete"].includes(value.action) && record(value.result))),
  // Only the states that have rows are present, plus `waiting`. Read with `??`.
  queueStats: (context?: RequestContext) => request<Record<string, number>>("/queue/stats", {}, context)
    .then(value => validate(value, record(value) && Object.values(value).every(n => Number.isSafeInteger(n) && n >= 0))),
};

// ---------------------------------------------------------------------------
// queue arithmetic
//
// `/queue/stats` is a `GROUP BY state` -- so a state with no rows is absent,
// not zero -- plus one derived number, `waiting`. The server computes `waiting`
// as "pending AND next_attempt_at is still in the future", which makes it a
// *subset* of `pending`, and it reports the two separately for exactly one
// reason, written down in `fetch/store.py`: so that `pending: 40` next to an
// empty lease response stops looking like a bug.
//
// Both surfaces here used to print `pending` under the label "waiting for the
// browser", which threw that distinction away and reintroduced the confusion
// the server had gone out of its way to prevent: the user clicks *fetch queued
// pages*, gets "processed 0 page(s)", and the count next to it does not move.
// Nothing is broken in that picture -- the items are serving a backoff -- but
// nothing on screen says so.

export interface QueueSummary {
  /** Pending and leasable right now: this is what a drain will actually take. */
  ready: number;
  /** Pending but serving a retry backoff. Waiting on a clock, not on a browser. */
  waiting: number;
  /** Handed out to a browser and not yet returned. Reclaimed after the lease expires. */
  leased: number;
  /** Gave up after the last retry. Needs a person, not another attempt. */
  failed: number;
  /** Read out successfully at some point. */
  done: number;
}

export function summarizeQueue(raw: Record<string, number> | undefined): QueueSummary {
  const n = (k: string): number => {
    const v = Number(raw?.[k] ?? 0);
    return Number.isFinite(v) && v > 0 ? v : 0;
  };
  const pending = n("pending");
  const waiting = Math.min(n("waiting"), pending);
  return {
    ready: pending - waiting,
    waiting,
    leased: n("leased"),
    failed: n("failed"),
    done: n("done"),
  };
}

/** One line for a status bar, or "" when there is nothing outstanding to say. */
export function describeQueue(s: QueueSummary): string {
  const parts: string[] = [];
  if (s.ready) parts.push(`${s.ready} ready for the browser`);
  if (s.waiting) parts.push(`${s.waiting} retrying later`);
  if (s.leased) parts.push(`${s.leased} in flight`);
  if (s.failed) parts.push(`${s.failed} gave up`);
  return parts.join(" · ");
}

// ---------------------------------------------------------------------------
// paging
//
// Kept here, as pure functions over plain data, for the same reason
// `summarizeQueue` is: the popup has no DOM stand-in in the test suite, so any
// logic that lives inside an event handler is logic nothing can assert. What
// is easy to get wrong about paging is not the fetch, it is the bookkeeping --
// pinning the depth, not counting the first page twice when the full pipeline
// replaces the lexical one at the same offset, and not claiming a total that
// the server described as a lower bound.

export interface PageCursor {
  /** The query these pages belong to. Typing a new one starts over. */
  query: string;
  /** Rows on screen. Derived from the last response, never incremented blindly. */
  seen: number;
  /**
   * Depth to pin on every later page, so page N+1 continues page N instead of
   * being a fresh opinion about the same query. 0 until a response says.
   */
  depth: number;
  /** Documents the server ranked. A lower bound when `capped`. */
  total: number;
  more: boolean;
  /** `total` was cut by the server's depth ceiling, not by the library ending. */
  capped: boolean;
  windowEnded: boolean;
}

export function startCursor(query: string): PageCursor {
  return { query, seen: 0, depth: 0, total: 0, more: false, capped: false, windowEnded: false };
}

/** Fold one response into the cursor. */
export function advance(cur: PageCursor, r: SearchResponse): PageCursor {
  // `offset + length`, not `seen + length`. Stage one (lexical) and stage two
  // (the full pipeline) both render offset 0, and adding lengths would
  // double-count the first page and then skip a page's worth of results; it
  // would also strand the cursor above the row count whenever the second
  // ranking is shorter than the first.
  const seen = (r.offset ?? 0) + r.hits.length;
  const total = r.total ?? 0;
  return {
    query: cur.query,
    seen,
    depth: r.depth || cur.depth,
    total,
    more: Boolean(r.has_more),
    capped: Boolean(r.depth_capped),
    // has_more can refer to more candidates outside this pinned ranking.
    windowEnded: Boolean(r.has_more && (!r.hits.length || (total > 0 && seen >= total))),
  };
}

/** Arguments for the next page, or null when there is nothing further to ask for. */
export function nextRequest(
  cur: PageCursor,
  size: number,
): { offset: number; limit: number; depth: number } | null {
  if (!cur.more || !cur.query || cur.windowEnded) return null;
  return { offset: cur.seen, limit: size, depth: cur.depth };
}

/** The counter above the list. Never states a total the server called a floor. */
export function describePage(cur: PageCursor): string {
  if (cur.windowEnded) return `${cur.seen} shown (end of current ranking)`;
  if (!cur.seen) return "no results";
  if (cur.more) {
    return cur.capped
      ? `${cur.seen} of ${cur.total}+ (depth limit reached)`
      : `${cur.seen} of ${cur.total}`;
  }
  return `${cur.seen} result${cur.seen === 1 ? "" : "s"}`;
}
