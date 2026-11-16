// Service worker: omnibox, context menu, and the channel-B fetch worker.
//
// Channel B exists because roughly one page in fifty is invisible to a plain
// HTTP fetch - login walls, SPA shells that render client-side, hosts that
// refuse unknown user agents. The browser is already logged in and already
// runs the JavaScript, so the extension can read what the server cannot. It
// does that in a background tab, three at a time, and it stops the moment the
// user pauses it.

import { ApiError, api, type CompleteBody, loadSettings, normalizeEndpoint, type QueueItem, requiredOrigins,
  type RequestContext, saveSettings, type Settings } from "./api.ts";
import { ownerKey, type PendingDelivery, putDelivery, readDeliveries, removeDelivery } from "./delivery.ts";
import { clearPendingResults, confirmSaves, retrySave, savePage } from "./save-delivery.ts";

const QUIET_MS = 1500; // settle time after readyState=complete, for late renders
const TAB_TIMEOUT_MS = 20000;
const BATCH = 3;
const ALARM = "facetmark-queue";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "facetmark-save",
    title: "Save to Facetmark",
    contexts: ["page", "link"],
  });
  chrome.alarms.create(ALARM, { periodInMinutes: 5 });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "facetmark-save") return;
  const url = info.linkUrl ?? tab?.url ?? "";
  if (!url) return;
  try {
    await savePage({ url, title: info.linkUrl ? info.linkUrl : tab?.title ?? url, folder: "" });
    await badge("ok");
  } catch (e) {
    await badge("err", e instanceof ApiError ? e.message : String(e));
  }
});

let suggestionGeneration = 0;
let suggestionController: AbortController | undefined;
chrome.omnibox.onInputChanged.addListener(async (text, suggest) => {
  const mine = ++suggestionGeneration;
  suggestionController?.abort();
  const controller = suggestionController = new AbortController();
  if (text.trim().length < 2) { suggest([]); return; }
  try {
    const res = await api.quick(text, 6, 0, undefined, { signal: controller.signal });
    if (mine !== suggestionGeneration) return;
    suggest(
      res.hits.map((h) => ({
        content: h.url,
        description: `${escapeXml(h.title)} <dim>${escapeXml(h.domain)}</dim>`,
      })),
    );
  } catch {
    /* omnibox stays quiet when the server is down */
  }
});

chrome.omnibox.onInputEntered.addListener(async (text) => {
  const url = /^https?:\/\//.test(text)
    ? text
    : `chrome-extension://${chrome.runtime.id}/popup.html?q=${encodeURIComponent(text)}`;
  try { await chrome.tabs.create({ url }); }
  catch (error) { await badge("err", error instanceof Error ? error.message : String(error)); }
});

chrome.alarms.onAlarm.addListener((a) => {
  if (a.name === ALARM) void drainQueue();
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "open-page") {
    openOriginal(msg).then(() => sendResponse({ ok: true }))
      .catch((error) => sendResponse(messageError(error)));
    return true;
  }
  if (msg?.type === "save-page") {
    savePage(msg.body).then((result) => sendResponse({ ok: true, result }))
      .catch((error) => sendResponse(messageError(error)));
    return true;
  }
  if (msg?.type === "retry-save") {
    retrySave(msg.request_id).then((result) => sendResponse({ ok: true, result }))
      .catch((error) => sendResponse(messageError(error)));
    return true;
  }
  if (msg?.type === "confirm-deliveries") {
    confirmBrowserResults().then((confirmed) => sendResponse({ ok: true, confirmed }))
      .catch((error) => sendResponse(messageError(error)));
    return true;
  }
  if (msg?.type === "resume-deliveries") {
    resumeBrowserResults().then((processed) => sendResponse({ ok: true, processed }))
      .catch((error) => sendResponse(messageError(error)));
    return true;
  }
  if (msg?.type === "drain") {
    drainQueue(true)
      .then((n) => sendResponse({ ok: true, processed: n }))
      .catch((error) => sendResponse(messageError(error)));
    return true; // async reply
  }
  if (msg?.type === "pause") {
    saveSettings({ paused: !!msg.value }).then(() => sendResponse({ ok: true }))
      .catch((error) => sendResponse({ ok: false, error: String(error) }));
    return true;
  }
  if (msg?.type === "settings-update") {
    updateSettings(msg.settings, msg.expected).then((settings) => sendResponse({ ok: true, settings }))
      .catch((error) => sendResponse(messageError(error)));
    return true;
  }
  if (msg?.type === "discard-deliveries") {
    discardBrowserResults().then(() => sendResponse({ ok: true }))
      .catch((error) => sendResponse(messageError(error)));
    return true;
  }
  return false;
});

let draining = false;
let activeController: AbortController | undefined;
let activeSettings: Settings | undefined;
let configuring = false;

function messageError(error: unknown): { ok: false; error: string; status?: number; code?: string } {
  return { ok: false, error: error instanceof Error ? error.message : String(error),
    ...(error instanceof ApiError ? { status: error.status, code: error.code } : {}) };
}

async function openOriginal(message: { url: string; bookmark_id: number; query: string; settings?: Settings }): Promise<void> {
  const url = new URL(message.url);
  if (!["http:", "https:"].includes(url.protocol) || !Number.isSafeInteger(message.bookmark_id)
    || message.bookmark_id <= 0 || typeof message.query !== "string") throw new Error("The saved link could not be opened");
  const settings = await loadSettings();
  await chrome.tabs.create({ url: url.href });
  if (message.settings?.endpoint === settings.endpoint && message.settings.token === settings.token) {
    // Keep the record alive in the worker after a native popup closes on tab activation.
    await api.opened(message.bookmark_id, message.query, { settings }).catch(() => undefined);
  }
}

export async function updateSettings(input: Settings, expected: Settings): Promise<Settings> {
  if (configuring) throw new ApiError("Connection settings are being saved in another window; read them again", 409, "settings-changed");
  configuring = true;
  try {
    const snapshot = structuredClone(input);
    if (!snapshot || typeof snapshot.endpoint !== "string" || typeof snapshot.token !== "string"
      || typeof snapshot.channelB !== "boolean" || typeof snapshot.paused !== "boolean") {
      throw new ApiError("The connection settings are incomplete; read them again", 0, "invalid");
    }
    snapshot.endpoint = normalizeEndpoint(snapshot.endpoint);
    snapshot.token = snapshot.token.trim();
    const current = await loadSettings();
    if (!expected || (["endpoint", "token", "channelB", "paused"] as const).some(key => current[key] !== expected[key])) {
      throw new ApiError("Connection settings changed in another window; read them before saving", 409, "settings-changed");
    }
    if ((snapshot.endpoint !== current.endpoint || (!current.channelB && snapshot.channelB))
      && !await chrome.permissions.contains({ origins: requiredOrigins(snapshot.endpoint, snapshot.channelB) })) {
      throw new ApiError("Website access was not granted; allow the saved connection in settings", 0, "permission");
    }
    await saveSettings(snapshot);
    return snapshot;
  } finally { configuring = false; }
}

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local" || !activeSettings) return;
  if (changes.paused?.newValue === true || changes.channelB?.newValue === false
    || (changes.endpoint && changes.endpoint.newValue !== activeSettings.endpoint)
    || (changes.token && changes.token.newValue !== activeSettings.token)) activeController?.abort();
});
chrome.permissions.onRemoved.addListener(() => activeController?.abort());

async function confirmBrowserResults(): Promise<number> {
  if (draining) throw new Error("Pause the current reading before confirming pending results");
  draining = true;
  try {
    const settings = await loadSettings();
    const owner = await ownerKey(settings);
    let confirmed = await confirmSaves();
    for (const delivery of await readDeliveries()) {
      if (delivery.owner !== owner) continue;
      try {
        const saved = await api.receipt(delivery.body.request_id, { settings });
        if (saved.action !== "complete" || saved.result.bookmark_id !== delivery.body.bookmark_id
          || typeof saved.result.stored !== "boolean" || typeof saved.result.changed !== "boolean") {
          throw new ApiError("The original browser result could not be confirmed", 200, "invalid");
        }
        await removeDelivery(delivery.body.request_id);
        confirmed += 1;
      } catch (error) { if (!(error instanceof ApiError) || error.status !== 404) throw error; }
    }
    return confirmed;
  } finally { draining = false; }
}

async function discardBrowserResults(): Promise<void> {
  if (draining) throw new Error("Pause the current reading before clearing pending results");
  draining = true;
  try { await clearPendingResults(); }
  finally { draining = false; }
}

async function resumeBrowserResults(): Promise<number> {
  if (draining) throw new Error("Pause the current reading before sending its original results");
  draining = true;
  try {
    const settings = await loadSettings();
    const owner = await ownerKey(settings);
    let processed = 0;
    for (const delivery of await readDeliveries()) {
      if (delivery.owner !== owner) throw new Error("Use the original saved connection before sending these results");
      await acknowledge(delivery, { settings }, true);
      processed += 1;
    }
    return processed;
  } finally { draining = false; }
}

async function acknowledge(delivery: PendingDelivery, context: RequestContext, recovering = false): Promise<void> {
  try {
    if (recovering) {
      try {
        const receipt = await api.receipt(delivery.body.request_id, context);
        if (receipt.action !== "complete" || receipt.result.bookmark_id !== delivery.body.bookmark_id
          || typeof receipt.result.stored !== "boolean" || typeof receipt.result.changed !== "boolean") {
          throw new ApiError("The original browser result could not be confirmed", 200, "invalid");
        }
        await removeDelivery(delivery.body.request_id);
        return;
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404) throw error;
      }
      if (delivery.rejected) throw new Error(delivery.error || "Review the pending browser result in settings");
    }
    await api.queueComplete(delivery.body, context);
    await removeDelivery(delivery.body.request_id);
  } catch (error) {
    if (!(error instanceof DOMException && error.name === "AbortError")) {
      const rejected = error instanceof ApiError && [400, 404, 409, 422].includes(error.status)
        && !/^Wait for /i.test(error.message);
      await putDelivery({ ...delivery, rejected: delivery.rejected || rejected,
        error: (error instanceof Error ? error.message : String(error)).slice(0, 800) });
    }
    throw error;
  }
}

/** Pull leased items, render each in a background tab, hand the text back. */
export async function drainQueue(manual = false): Promise<number> {
  if (draining) {
    if (manual) throw new Error("Page reading is already running; pause it or wait for it to finish");
    return 0;
  }
  draining = true;
  const controller = new AbortController();
  activeController = controller;
  let done = 0;
  let problem = "";
  let items: QueueItem[] = [];
  let index = 0;
  const retained = new Set<string>();
  let settings: Settings | undefined;
  let failure: unknown;
  try {
    const s = settings = activeSettings = await loadSettings();
    if (!s.channelB || s.paused) {
      if (manual) throw new Error(s.paused ? "Page reading is paused; resume it in settings" : "Allow page reading in settings first");
      return 0;
    }
    if (!await chrome.permissions.contains({ origins: requiredOrigins(s.endpoint, true) })) {
      throw new ApiError("Website access is missing; allow page reading in settings", 0, "permission");
    }
    const context: RequestContext = { settings: s, signal: controller.signal };
    const owner = await ownerKey(s);
    const pending = await readDeliveries();
    for (const delivery of pending) {
      if (delivery.owner !== owner) {
        throw new Error("Pending results belong to another saved connection; review them in settings");
      }
      await acknowledge(delivery, context, true);
      done += 1;
    }
    if (controller.signal.aborted) return done;
    const leased = await api.queueNext(BATCH, context);
    if (leased.busy) {
      if (manual) throw new Error("Wait for the running Facetmark task before reading queued pages");
      return done;
    }
    items = leased.items;
    for (; index < items.length; index += 1) {
      const item = items[index];
      if (controller.signal.aborted) break;
      let body: CompleteBody;
      try {
        const got = await renderInTab(item.url, controller.signal);
        body = {
          bookmark_id: item.bookmark_id,
          body: got.text,
          title: got.title,
          final_url: got.url,
          lease_id: item.lease_id,
          source_url: item.url,
          request_id: `ext-${crypto.randomUUID()}`,
        };
      } catch (e) {
        if (controller.signal.aborted) break;
        body = {
          bookmark_id: item.bookmark_id,
          error: e instanceof Error ? e.message : String(e),
          lease_id: item.lease_id,
          source_url: item.url,
          request_id: `ext-${crypto.randomUUID()}`,
        };
      }
      const delivery: PendingDelivery = { version: 1, owner, body, savedAt: Date.now() };
      await putDelivery(delivery);
      retained.add(item.lease_id);
      await acknowledge(delivery, context);
      retained.delete(item.lease_id);
      done += 1;
      await progress(done, items.length);
    }
  } catch (e) {
    if (!controller.signal.aborted) failure = e;
    if (!controller.signal.aborted && (manual || !(e instanceof ApiError) || e.status === 401
      || e.code === "permission" || e.code === "invalid" || retained.size)) {
      problem = e instanceof ApiError && e.status === 401 ? "pairing token rejected - open options"
        : e instanceof Error ? e.message : String(e);
    }
  } finally {
    if (settings && items.length) {
      const unprocessed = items.slice(index).filter((item) => !retained.has(item.lease_id));
      if (unprocessed.length) {
        try {
          await api.queueRelease(unprocessed.map(({ bookmark_id, lease_id }) => ({ bookmark_id, lease_id })), { settings });
        } catch { /* Exact leases expire if the server is temporarily unavailable. */ }
      }
    }
    activeController = undefined;
    activeSettings = undefined;
    draining = false;
    await chrome.action.setBadgeText({ text: "" });
    if (problem) await badge("err", problem);
  }
  if (manual && failure) throw failure;
  return done;
}

interface Rendered {
  text: string;
  title: string;
  url: string;
}

function renderInTab(url: string, signal: AbortSignal): Promise<Rendered> {
  return new Promise((resolve, reject) => {
    let settled = false;
    let tabId: number | undefined;
    let onUpdated: ((id: number, info: chrome.tabs.TabChangeInfo) => void) | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let quietTimer: ReturnType<typeof setTimeout> | undefined;
    let reading = false;
    const onAbort = () => void finish(() => reject(new DOMException("Reading paused", "AbortError")));

    const finish = (fn: () => void) => {
      if (settled) return;
      settled = true;
      if (onUpdated) chrome.tabs.onUpdated.removeListener(onUpdated);
      if (timer !== undefined) clearTimeout(timer);
      if (quietTimer !== undefined) clearTimeout(quietTimer);
      signal.removeEventListener("abort", onAbort);
      if (tabId !== undefined) {
        void chrome.tabs.remove(tabId).catch(() => undefined);
      }
      fn();
    };

    // Armed before the tab is asked for rather than after it arrives. The
    // deadline used to start inside the `tabs.create` callback, which left the
    // one case it most needed to cover uncovered: a `tabs.create` that never
    // calls back at all. Every path out of here now has a clock on it.
    timer = setTimeout(
      () => void finish(() => reject(new Error("timeout waiting for the page"))),
      TAB_TIMEOUT_MS,
    );
    signal.addEventListener("abort", onAbort, { once: true });
    if (signal.aborted) { onAbort(); return; }

    const readWhenReady = () => {
      if (settled || reading || quietTimer !== undefined) return;
      quietTimer = setTimeout(async () => {
        quietTimer = undefined;
        if (settled || signal.aborted) return;
        reading = true;
        try {
          const [res] = await chrome.scripting.executeScript({ target: { tabId: tabId! }, func: extractFromPage });
          const value = res?.result as Rendered | undefined;
          if (!value || typeof value.text !== "string" || !value.text.trim()) throw new Error("page had no readable text");
          finish(() => resolve(value));
        } catch (e) {
          finish(() => reject(e instanceof Error ? e : new Error(String(e))));
        }
      }, QUIET_MS);
    };
    onUpdated = (id, info) => {
      if (id !== tabId || settled) return;
      if (info.status === "loading" && quietTimer !== undefined) {
        clearTimeout(quietTimer);
        quietTimer = undefined;
      }
      if (info.status === "complete") readWhenReady();
    };
    chrome.tabs.onUpdated.addListener(onUpdated);

    chrome.tabs.create({ url, active: false, pinned: true }, (tab) => {
      // Chrome passes `undefined` here and sets `lastError` when the tab could
      // not be opened. Reading `tab.id` in that case throws a TypeError inside
      // a callback that no `try` can see and that the promise never hears
      // about, so a single unopenable URL wedged `drainQueue` -- and with it
      // the whole of channel B -- until the service worker happened to restart.
      const err = chrome.runtime.lastError;
      if (err || tab?.id === undefined) {
        void finish(() =>
          reject(new Error(err?.message ?? "the browser would not open a tab")),
        );
        return;
      }
      if (settled) {
        // The deadline won the race. Do not leave the tab behind.
        void chrome.tabs.remove(tab.id).catch(() => undefined);
        return;
      }
      const id0 = tab.id;
      tabId = id0;

      if (tab.status === "complete") readWhenReady();
      void chrome.tabs.get(id0).then((current) => {
        if (current.status === "complete") readWhenReady();
      }).catch((error) => finish(() => reject(new Error(String(error)))));
    });
  });
}

/** Runs in the page. Keep it dependency-free: it is injected as source. */
function extractFromPage(): { text: string; title: string; url: string } {
  const drop = "script,style,noscript,nav,header,footer,aside,iframe,svg,form";
  const root = document.querySelector("article, main, [role=main]") ?? document.body;
  const clone = root.cloneNode(true) as HTMLElement;
  clone.querySelectorAll(drop).forEach((n) => n.remove());
  const text = (clone.innerText || clone.textContent || "").replace(/\n{3,}/g, "\n\n").trim();
  return { text: text.slice(0, 200000), title: document.title, url: location.href };
}

async function progress(done: number, total: number): Promise<void> {
  await chrome.action.setBadgeText({ text: `${done}/${total}` });
  await chrome.action.setBadgeBackgroundColor({ color: "#0279EE" });
}

async function badge(kind: "ok" | "err", title?: string): Promise<void> {
  await chrome.action.setBadgeText({ text: kind === "ok" ? "+1" : "!" });
  await chrome.action.setBadgeBackgroundColor({
    color: kind === "ok" ? "#235fe5" : "#b73754",
  });
  if (title) await chrome.action.setTitle({ title: `Facetmark: ${title}` });
  setTimeout(() => void chrome.action.setBadgeText({ text: "" }), 2500);
}

function escapeXml(s: string): string {
  return s.replace(/[<>&"']/g, (c) =>
    ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&apos;" })[c] as string,
  );
}
