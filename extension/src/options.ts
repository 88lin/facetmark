// Pairing and channel-B controls.
//
// The token is printed once by `facetmark serve` and pasted here. It is a
// shared secret between two programs on the same machine, which is enough:
// the server binds to the loopback interface, so the only callers are local.

import {
  DEFAULTS,
  api,
  describeQueue,
  loadSettings,
  saveSettings,
  summarizeQueue,
} from "./api.ts";

const $ = <T extends HTMLElement>(s: string) => document.querySelector(s) as T;

const endpoint = $<HTMLInputElement>("#endpoint");
const token = $<HTMLInputElement>("#token");
const channelB = $<HTMLInputElement>("#channelB");
const paused = $<HTMLInputElement>("#paused");
const state = $<HTMLDivElement>("#state");

// `note` carries the outcome of whatever the user just clicked. It is a
// parameter rather than a separate write to `state` because `refresh` is
// always called straight afterwards, and used to overwrite the outcome line
// before anyone could read it.
async function refresh(note = ""): Promise<void> {
  const s = await loadSettings();
  endpoint.value = s.endpoint || DEFAULTS.endpoint;
  token.value = s.token;
  channelB.checked = s.channelB;
  paused.checked = s.paused;
  try {
    const h = await api.health();
    const q = summarizeQueue(await api.queueStats());
    const queue = describeQueue(q) || "queue empty";
    state.textContent = [note, `connected · ${h.bookmarks} bookmarks`, queue]
      .filter(Boolean)
      .join(" · ");
    state.className = "ok";
  } catch (e) {
    state.textContent = e instanceof Error ? e.message : String(e);
    state.className = "bad";
  }
}

$("#save").addEventListener("click", async () => {
  await saveSettings({
    endpoint: endpoint.value.replace(/\/+$/, ""),
    token: token.value.trim(),
    channelB: channelB.checked,
    paused: paused.checked,
  });
  await refresh();
});

$("#drain").addEventListener("click", async () => {
  // A drain that reads nothing is the normal case in several situations that
  // look identical from here -- channel B switched off, paused, everything
  // already fetched, everything in backoff. Say which one it was; `refresh`
  // then prints the queue breakdown underneath.
  if (!channelB.checked) {
    state.textContent = "channel B is off - nothing will be fetched";
    return;
  }
  if (paused.checked) {
    state.textContent = "paused - unpause to let the browser fetch";
    return;
  }
  state.textContent = "fetching queued pages...";
  const res = await chrome.runtime.sendMessage({ type: "drain" });
  if (!res?.ok) {
    state.textContent = String(res?.error ?? "the service worker did not answer");
    state.className = "bad";
    return;
  }
  await refresh(
    res.processed ? `fetched ${res.processed} page(s)` : "nothing was ready to fetch",
  );
});

void refresh();
