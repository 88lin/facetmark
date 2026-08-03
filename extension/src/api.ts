// One place that knows how to talk to the local server.
//
// Every request goes out from the service worker, never from a content script.
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
  channelB: true,
  paused: false,
};

export async function loadSettings(): Promise<Settings> {
  const got = await chrome.storage.local.get(DEFAULTS);
  return { ...DEFAULTS, ...got } as Settings;
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

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const s = await loadSettings();
  const headers = new Headers(init.headers ?? {});
  headers.set("Content-Type", "application/json");
  if (s.token) headers.set("Authorization", `Bearer ${s.token}`);
  let res: Response;
  try {
    res = await fetch(`${s.endpoint}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("server unreachable - is `facetmark serve` running?", 0);
  }
  if (res.status === 401) throw new ApiError("pairing token rejected", 401);
  if (!res.ok) throw new ApiError(`${res.status} ${res.statusText}`, res.status);
  return (await res.json()) as T;
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
  /** Expansion rows only: the bookmark id this one was reached from. */
  via?: number;
  via_kind?: string;
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
}

export const api = {
  health: () =>
    request<{ ok: boolean; version: string; bookmarks: number; provider: string }>("/health"),
  stats: () => request<Record<string, unknown>>("/stats"),
  quick: (q: string, limit = 10) =>
    request<SearchResponse>(`/quick?q=${encodeURIComponent(q)}&limit=${limit}`),
  search: (q: string, limit = 20) =>
    request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify({ q, limit }),
    }),
  save: (body: { url: string; title: string; folder?: string }) =>
    request<{ bookmark_id: number; created?: boolean }>("/bookmark", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  opened: (bookmark_id: number, query: string) =>
    request<{ ok: boolean }>("/open", {
      method: "POST",
      body: JSON.stringify({ bookmark_id, query }),
    }),
  queueNext: (n = 3) =>
    request<{
      items: { bookmark_id: number; url: string; title: string; reason: string;
               attempt: number }[];
      queue: Record<string, number>;
      waiting: number;
    }>(`/queue/next?n=${n}`),
  queueComplete: (body: {
    bookmark_id: number;
    body?: string;
    title?: string;
    final_url?: string;
    error?: string;
  }) =>
    request<{ bookmark_id: number; stored: boolean; changed: boolean;
              queue: Record<string, number> }>("/queue/complete", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  // Only the states that have rows are present, plus `waiting`. Read with `??`.
  queueStats: () => request<Record<string, number>>("/queue/stats"),
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
