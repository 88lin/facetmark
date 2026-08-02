// Pairing and channel-B controls.
//
// The token is printed once by `facetmark serve` and pasted here. It is a
// shared secret between two programs on the same machine, which is enough:
// the server binds to the loopback interface, so the only callers are local.

import { DEFAULTS, api, loadSettings, saveSettings } from "./api.js";

const $ = <T extends HTMLElement>(s: string) => document.querySelector(s) as T;

const endpoint = $<HTMLInputElement>("#endpoint");
const token = $<HTMLInputElement>("#token");
const channelB = $<HTMLInputElement>("#channelB");
const paused = $<HTMLInputElement>("#paused");
const state = $<HTMLDivElement>("#state");

async function refresh(): Promise<void> {
  const s = await loadSettings();
  endpoint.value = s.endpoint || DEFAULTS.endpoint;
  token.value = s.token;
  channelB.checked = s.channelB;
  paused.checked = s.paused;
  try {
    const h = await api.health();
    const q = await api.queueStats();
    state.textContent = `connected · ${h.bookmarks} bookmarks · ${q.pending ?? 0} waiting for the browser`;
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
  state.textContent = "fetching queued pages...";
  const res = await chrome.runtime.sendMessage({ type: "drain" });
  state.textContent = res?.ok ? `processed ${res.processed} page(s)` : String(res?.error);
  await refresh();
});

void refresh();
