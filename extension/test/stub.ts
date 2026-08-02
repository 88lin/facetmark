// A hand-written stand-in for the slice of the extension APIs that the service
// worker actually touches.
//
// The point is not to emulate Chrome. It is to make the drain loop runnable
// off a browser so that its failure paths -- a tab that will not open, a
// rejected token, a page with no text -- can be asserted instead of reasoned
// about. Everything the worker calls is here; anything it does not call is
// deliberately absent, so a new dependency on the browser shows up as a
// TypeError in a test rather than as silence in the field.

export interface FetchCall {
  path: string;
  method: string;
  body: unknown;
}

export type TabBehaviour = "ok" | "lastError" | "noTab" | "silent";

export interface Stub {
  calls: FetchCall[];
  routes: Map<string, () => { status: number; json: unknown }>;
  settings: Record<string, unknown>;
  tabs: { behaviour: TabBehaviour; created: string[]; removed: number[] };
  /** What `extractFromPage` would have returned. `null` renders an empty page. */
  page: { text: string; title: string; url: string } | null;
  badges: string[];
  titles: string[];
}

const BASE = "http://127.0.0.1:8787";

export function install(): Stub {
  const stub: Stub = {
    calls: [],
    routes: new Map(),
    settings: { endpoint: BASE, token: "t", channelB: true, paused: false },
    tabs: { behaviour: "ok", created: [], removed: [] },
    page: { text: "the body of the page", title: "A Page", url: `${BASE}/final` },
    badges: [],
    titles: [],
  };

  let nextTabId = 100;
  const updated: ((id: number, info: { status?: string }) => void)[] = [];
  const noop = () => undefined;
  const listener = { addListener: noop, removeListener: noop };

  const chrome = {
    runtime: {
      id: "stub",
      lastError: undefined as { message: string } | undefined,
      onInstalled: listener,
      onMessage: listener,
      sendMessage: async () => ({ ok: true }),
    },
    contextMenus: { create: noop, onClicked: listener },
    omnibox: { onInputChanged: listener, onInputEntered: listener },
    alarms: { create: noop, onAlarm: listener },
    storage: {
      local: {
        get: async (defaults: Record<string, unknown>) => ({ ...defaults, ...stub.settings }),
        set: async (patch: Record<string, unknown>) => {
          Object.assign(stub.settings, patch);
        },
      },
    },
    action: {
      setBadgeText: async (o: { text: string }) => {
        stub.badges.push(o.text);
      },
      setBadgeBackgroundColor: async () => undefined,
      setTitle: async (o: { title: string }) => {
        stub.titles.push(o.title);
      },
    },
    scripting: {
      executeScript: async () => [{ result: stub.page ?? { text: "", title: "", url: "" } }],
    },
    tabs: {
      onUpdated: {
        addListener: (fn: (id: number, info: { status?: string }) => void) => {
          updated.push(fn);
        },
        removeListener: (fn: (id: number, info: { status?: string }) => void) => {
          const i = updated.indexOf(fn);
          if (i >= 0) updated.splice(i, 1);
        },
      },
      create: (props: { url: string }, cb?: (tab: { id?: number } | undefined) => void) => {
        stub.tabs.created.push(props.url);
        const id = nextTabId++;
        if (!cb) return Promise.resolve({ id });
        if (stub.tabs.behaviour === "silent") return undefined;
        if (stub.tabs.behaviour === "lastError") {
          // Chrome's contract: `lastError` is set and the tab argument is
          // `undefined`. This is the shape that used to throw inside the
          // callback and leave the promise unsettled forever.
          chrome.runtime.lastError = { message: "No tab with id" };
          cb(undefined);
          chrome.runtime.lastError = undefined;
          return undefined;
        }
        if (stub.tabs.behaviour === "noTab") {
          cb({});
          return undefined;
        }
        cb({ id });
        // The worker registers its listener after `create` returns, so the
        // load event has to arrive on a later turn, as it does in a browser.
        setTimeout(() => {
          for (const fn of [...updated]) fn(id, { status: "complete" });
        }, 0);
        return undefined;
      },
      remove: async (id: number) => {
        stub.tabs.removed.push(id);
      },
      query: async () => [],
    },
  };

  const fetchStub = async (url: string, init: RequestInit = {}) => {
    const path = String(url).slice(BASE.length);
    stub.calls.push({
      path,
      method: init.method ?? "GET",
      body: init.body ? JSON.parse(String(init.body)) : null,
    });
    const key = [...stub.routes.keys()].find((k) => path.startsWith(k));
    const made = key ? stub.routes.get(key)!() : { status: 404, json: {} };
    return {
      ok: made.status >= 200 && made.status < 300,
      status: made.status,
      statusText: String(made.status),
      json: async () => made.json,
    };
  };

  const g = globalThis as unknown as Record<string, unknown>;
  g.chrome = chrome;
  g.fetch = fetchStub;
  return stub;
}

export function reset(stub: Stub): void {
  stub.calls.length = 0;
  stub.routes.clear();
  stub.tabs.created.length = 0;
  stub.tabs.removed.length = 0;
  stub.tabs.behaviour = "ok";
  stub.badges.length = 0;
  stub.titles.length = 0;
  stub.page = { text: "the body of the page", title: "A Page", url: `${BASE}/final` };
  Object.assign(stub.settings, { endpoint: BASE, token: "t", channelB: true, paused: false });
}

/** Fail loudly instead of hanging: an unsettled promise is the bug under test. */
export async function within<T>(ms: number, p: Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout>;
  const bell = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error(`did not settle within ${ms}ms`)), ms);
  });
  try {
    return await Promise.race([p, bell]);
  } finally {
    clearTimeout(timer!);
  }
}
