// Service worker: omnibox, context menu, and the channel-B fetch worker.
//
// Channel B exists because roughly one page in fifty is invisible to a plain
// HTTP fetch - login walls, SPA shells that render client-side, hosts that
// refuse unknown user agents. The browser is already logged in and already
// runs the JavaScript, so the extension can read what the server cannot. It
// does that in a background tab, three at a time, and it stops the moment the
// user pauses it.

import { ApiError, api, loadSettings, saveSettings } from "./api.ts";

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
    await api.save({ url, title: tab?.title ?? url, folder: "" });
    await badge("ok");
  } catch (e) {
    await badge("err", e instanceof ApiError ? e.message : String(e));
  }
});

chrome.omnibox.onInputChanged.addListener(async (text, suggest) => {
  if (text.trim().length < 2) return;
  try {
    const res = await api.quick(text, 6);
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
  await chrome.tabs.create({ url });
});

chrome.alarms.onAlarm.addListener((a) => {
  if (a.name === ALARM) void drainQueue();
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "drain") {
    drainQueue()
      .then((n) => sendResponse({ ok: true, processed: n }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true; // async reply
  }
  if (msg?.type === "pause") {
    saveSettings({ paused: !!msg.value }).then(() => sendResponse({ ok: true }));
    return true;
  }
  return false;
});

let draining = false;

/** Pull leased items, render each in a background tab, hand the text back. */
export async function drainQueue(): Promise<number> {
  const s = await loadSettings();
  if (!s.channelB || s.paused || draining) return 0;
  draining = true;
  let done = 0;
  let unauthorized = false;
  try {
    const { items } = await api.queueNext(BATCH);
    for (const item of items) {
      const fresh = await loadSettings();
      if (fresh.paused) break;
      try {
        const got = await renderInTab(item.url);
        await api.queueComplete({
          bookmark_id: item.bookmark_id,
          body: got.text,
          title: got.title,
          final_url: got.url,
        });
      } catch (e) {
        await api.queueComplete({
          bookmark_id: item.bookmark_id,
          error: e instanceof Error ? e.message : String(e),
        });
      }
      done += 1;
      await progress(done, items.length);
    }
  } catch (e) {
    // A server that is simply not running is not worth a badge: the drain is a
    // background activity and the next alarm will try again. A rejected pairing
    // token is worth one, because it will never fix itself, and without a
    // signal channel B is indistinguishable from channel B doing nothing.
    unauthorized = e instanceof ApiError && e.status === 401;
  } finally {
    draining = false;
    await chrome.action.setBadgeText({ text: "" });
    if (unauthorized) await badge("err", "pairing token rejected - open options");
  }
  return done;
}

interface Rendered {
  text: string;
  title: string;
  url: string;
}

function renderInTab(url: string): Promise<Rendered> {
  return new Promise((resolve, reject) => {
    let settled = false;
    let tabId: number | undefined;
    let onUpdated: ((id: number, info: chrome.tabs.TabChangeInfo) => void) | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const finish = async (fn: () => void) => {
      if (settled) return;
      settled = true;
      if (onUpdated) chrome.tabs.onUpdated.removeListener(onUpdated);
      if (timer !== undefined) clearTimeout(timer);
      if (tabId !== undefined) {
        try {
          await chrome.tabs.remove(tabId);
        } catch {
          /* already closed */
        }
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

      onUpdated = (id: number, info: chrome.tabs.TabChangeInfo) => {
        if (id !== id0 || info.status !== "complete") return;
        setTimeout(async () => {
          try {
            const [res] = await chrome.scripting.executeScript({
              target: { tabId: id0 },
              func: extractFromPage,
            });
            const value = res?.result as Rendered | undefined;
            // Trimmed, because that is the test the server applies before it
            // decides whether a body counts (`complete_browser_item` strips
            // first). Sending whitespace across and letting the far side reject
            // it costs a round trip and replaces a reason the extension knows
            // -- the page rendered nothing -- with a generic one it does not.
            if (!value || !value.text.trim()) throw new Error("page had no readable text");
            await finish(() => resolve(value));
          } catch (e) {
            await finish(() => reject(e instanceof Error ? e : new Error(String(e))));
          }
        }, QUIET_MS);
      };

      chrome.tabs.onUpdated.addListener(onUpdated);
    });
  });
}

/** Runs in the page. Keep it dependency-free: it is injected as source. */
function extractFromPage(): { text: string; title: string; url: string } {
  const drop = "script,style,noscript,nav,header,footer,aside,iframe,svg,form";
  const root = document.querySelector("article, main, [role=main]") ?? document.body;
  const clone = root.cloneNode(true) as HTMLElement;
  clone.querySelectorAll(drop).forEach((n) => n.remove());
  const text = (clone.innerText || "").replace(/\n{3,}/g, "\n\n").trim();
  return { text: text.slice(0, 200000), title: document.title, url: location.href };
}

async function progress(done: number, total: number): Promise<void> {
  await chrome.action.setBadgeText({ text: `${done}/${total}` });
  await chrome.action.setBadgeBackgroundColor({ color: "#0279EE" });
}

async function badge(kind: "ok" | "err", title?: string): Promise<void> {
  await chrome.action.setBadgeText({ text: kind === "ok" ? "+1" : "!" });
  await chrome.action.setBadgeBackgroundColor({
    color: kind === "ok" ? "#75A025" : "#FF9400",
  });
  if (title) await chrome.action.setTitle({ title: `Facetmark: ${title}` });
  setTimeout(() => void chrome.action.setBadgeText({ text: "" }), 2500);
}

function escapeXml(s: string): string {
  return s.replace(/[<>&"']/g, (c) =>
    ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&apos;" })[c] as string,
  );
}
