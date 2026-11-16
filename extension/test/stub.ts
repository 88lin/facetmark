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

export type TabBehaviour = "ok" | "lastError" | "noTab" | "silent" | "complete" | "loading";

type Reply = { status: number; json: unknown; raw?: string } | Response;

export interface Stub {
  calls: FetchCall[];
  routes: Map<string, (init: RequestInit) => Reply | Promise<Reply>>;
  settings: Record<string, unknown>;
  tabs: { behaviour: TabBehaviour; created: string[]; removed: number[]; scripts: number;
    update: (id: number, status: string) => void };
  permissions: { allowed: boolean; grant: boolean; requested: string[][] };
  setSettings: (patch: Record<string, unknown>) => Promise<void>;
  sendMessage: (message: Record<string, unknown>) => Promise<Record<string, unknown>>;
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
    tabs: { behaviour: "ok", created: [], removed: [], scripts: 0, update: () => undefined },
    permissions: { allowed: true, grant: true, requested: [] },
    setSettings: async () => undefined,
    sendMessage: async () => ({}),
    page: { text: "the body of the page", title: "A Page", url: `${BASE}/final` },
    badges: [],
    titles: [],
  };

  let nextTabId = 100;
  const updated: ((id: number, info: { status?: string }) => void)[] = [];
  const changed: ((changes: Record<string, { newValue: unknown }>, area: string) => void)[] = [];
  const messages: ((message: Record<string, unknown>, sender: object, respond: (response: Record<string, unknown>) => void) => boolean)[] = [];
  const noop = () => undefined;
  const listener = { addListener: noop, removeListener: noop };

  const chrome = {
    runtime: {
      id: "stub",
      lastError: undefined as { message: string } | undefined,
      onInstalled: listener,
      onMessage: { addListener: (fn: typeof messages[number]) => messages.push(fn) },
      sendMessage: (message: Record<string, unknown>): Promise<Record<string, unknown>> => new Promise((resolve) => {
        for (const handle of messages) if (handle(message, {}, resolve)) return;
        if (!messages.length) resolve({});
      }),
    },
    contextMenus: { create: noop, onClicked: listener },
    omnibox: { onInputChanged: listener, onInputEntered: listener },
    alarms: { create: noop, onAlarm: listener },
    storage: {
      onChanged: { addListener: (fn: typeof changed[number]) => changed.push(fn) },
      local: {
        get: async (defaults: Record<string, unknown>) => structuredClone(Object.fromEntries(
          Object.entries(defaults).map(([key, value]) => [key, stub.settings[key] ?? value]),
        )),
        set: async (patch: Record<string, unknown>) => {
          Object.assign(stub.settings, structuredClone(patch));
          const changes = Object.fromEntries(Object.entries(patch).map(([key, newValue]) => [key, { newValue }]));
          for (const fn of changed) fn(changes, "local");
        },
        remove: async (keys: string | string[]) => {
          for (const key of typeof keys === "string" ? [keys] : keys) delete stub.settings[key];
        },
      },
    },
    permissions: {
      contains: async () => stub.permissions.allowed,
      request: async (value: { origins: string[] }) => {
        stub.permissions.requested.push(value.origins);
        if (stub.permissions.grant) stub.permissions.allowed = true;
        return stub.permissions.grant;
      },
      onRemoved: listener,
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
      executeScript: async () => {
        stub.tabs.scripts += 1;
        return [{ result: stub.page ?? { text: "", title: "", url: "" } }];
      },
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
      get: async (id: number) => ({ id, status: stub.tabs.behaviour === "loading" ? "loading" : "complete" }),
      create: (props: { url: string }, cb?: (tab: { id?: number; status?: string } | undefined) => void) => {
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
        cb({ id, status: stub.tabs.behaviour === "complete" ? "complete" : "loading" });
        if (stub.tabs.behaviour === "complete" || stub.tabs.behaviour === "loading") return undefined;
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
    const made = key ? await stub.routes.get(key)!(init) : { status: 404, json: {} };
    if (made instanceof Response) return made;
    return new Response(made.raw ?? JSON.stringify(made.json), { status: made.status });
  };

  const g = globalThis as unknown as Record<string, unknown>;
  g.chrome = chrome;
  g.fetch = fetchStub;
  stub.setSettings = chrome.storage.local.set;
  stub.sendMessage = chrome.runtime.sendMessage;
  stub.tabs.update = (id, status) => { for (const fn of [...updated]) fn(id, { status }); };
  return stub;
}

export function reset(stub: Stub): void {
  stub.calls.length = 0;
  stub.routes.clear();
  stub.tabs.created.length = 0;
  stub.tabs.removed.length = 0;
  stub.tabs.behaviour = "ok";
  stub.tabs.scripts = 0;
  stub.permissions.allowed = true;
  stub.permissions.grant = true;
  stub.permissions.requested.length = 0;
  stub.badges.length = 0;
  stub.titles.length = 0;
  stub.page = { text: "the body of the page", title: "A Page", url: `${BASE}/final` };
  for (const key of Object.keys(stub.settings)) delete stub.settings[key];
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
