// Every request this page makes.
//
// One `call` so the pairing token, the JSON content type and the error mapping
// are decided once. Query strings are built with URLSearchParams rather than
// with template literals: `?q=` takes whatever the reader typed, and a stray
// `&` in a query would otherwise silently become a second parameter.
//
// The three endpoints deliberately missing are `/queue/next`, `/queue/complete`
// and `/bookmark` (POST). The first two are a worker lease protocol -- a page
// that leases a job and is then closed leaves that job stuck until the lease
// expires, so a browser tab is the wrong client for them. The third is the
// extension's save path, and this page is a reader, not a saver.

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`);
    this.status = status;
  }
}

let token = "";

export function setToken(v) {
  token = v ?? "";
}

export function getToken() {
  return token;
}

export async function call(path, init = {}) {
  let res;
  try {
    res = await fetch(path, {
      ...init,
      headers: {
        // Only a string body is JSON. A `File` goes up as raw bytes, and
        // labelling those `application/json` would be a claim the server can
        // see is false the moment it tries to parse them.
        ...(typeof init.body === "string" ? { "content-type": "application/json" } : {}),
        ...(token ? { authorization: `Bearer ${token}` } : {}),
        ...(init.headers ?? {}),
      },
    });
  } catch (cause) {
    // A failed fetch to our own origin means the server went away. Status 0 is
    // this client's convention for "never got an HTTP response at all", which
    // is a different problem from any status the server could return.
    throw new ApiError(0, String(cause));
  }
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json()).detail ?? "";
    } catch {
      /* an error body that is not JSON is not worth a second failure */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

/** `?a=1&b=2`, or "" when nothing survives. Undefined and null are dropped. */
export function qs(params) {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

const post = (path, body) => call(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  // -- search ------------------------------------------------------------
  quick: (q, limit) => call(`/quick${qs({ q, limit })}`),
  search: ({ q, limit, offset = 0, depth = 0, config = "full", expand }) =>
    post("/search", {
      q,
      limit,
      offset,
      ...(depth ? { depth } : {}),
      ...(config ? { config } : {}),
      ...(expand === undefined ? {} : { expand }),
    }),
  suggest: (text, limit = 8) => post("/suggest", { text, limit }),
  // The query-language completer: fields, values from this library, sorts.
  suggestQuery: (text, limit = 8) => post("/suggest/query", { text, limit }),
  // Save-activity buckets for the library view's timeline strip.
  timeline: () => call("/timeline"),
  synthesize: (q, limit = 8) => post("/synthesize", { q, limit }),
  opened: (id, query) => post("/open", { bookmark_id: id, query }),

  // -- one bookmark ------------------------------------------------------
  bookmark: (id, body = false) => call(`/bookmark/${id}${qs({ body: body ? "true" : "" })}`),
  related: (id, kind = "", limit = 20) => call(`/bookmark/${id}/related${qs({ kind, limit })}`),

  // -- sittings ----------------------------------------------------------
  sessions: ({ limit = 50, offset = 0, minSize = 2 } = {}) =>
    call(`/sessions${qs({ limit, offset, min_size: minSize })}`),
  session: (id) => call(`/session/${id}`),

  // -- the server itself -------------------------------------------------
  stats: () => call("/stats"),
  health: () => call("/health"),
  queueStats: () => call("/queue/stats"),
  linkHealth: () => call("/link-health/summary"),
  linkHealthOf: (id) => call(`/link-health/${id}`),
  // The only call on this page that reaches anything outside this machine, so
  // it is never made without an explicit confirmation naming the ceiling.
  linkHealthCheck: (limit) => post("/link-health/check", { limit }),
  graveyard: (limit = 100) => call(`/graveyard${qs({ limit })}`),

  // -- setting the machine up -------------------------------------------
  //
  // Everything below is `/admin/*`: loopback-only, token-gated, and off
  // entirely when FACETMARK_ADMIN_API is false. These are the calls that
  // change what is on this machine rather than read it, which is why they are
  // grouped apart from the rest.

  /**
   * A bookmark export, sent as the raw body.
   *
   * Not `FormData`: multipart would need `python-multipart` on the server for
   * no gain, and a `File` is already a `Blob` that `fetch` will stream. The
   * name travels in a header because the body is the file, not a field in it.
   */
  adminImport: (file) =>
    call("/admin/import", {
      method: "POST",
      body: file,
      headers: { "x-filename": encodeURIComponent(file.name ?? "") },
    }),
  adminIndex: ({ fetch: doFetch = true, limit = null, force = false } = {}) =>
    post("/admin/index", { fetch: doFetch, limit, force }),
  adminJob: () => call("/admin/job"),
  adminCancel: () => post("/admin/job/cancel", {}),
  adminSettings: () => call("/admin/settings"),
  adminSettingsWrite: (values) =>
    call("/admin/settings", { method: "PUT", body: JSON.stringify({ values }) }),
  /** Probe credentials without saving them. Chat and embed answer separately. */
  adminSettingsTest: (patch) => post("/admin/settings/test", patch),
};
