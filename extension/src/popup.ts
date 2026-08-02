// Two-stage search box.
//
// Stage one is the FTS5 path, which answers in single-digit milliseconds and
// goes on screen immediately. Stage two is the full four-facet pipeline, which
// needs an embedding round trip and arrives a few hundred milliseconds later,
// then replaces the list in place. Waiting for stage two before drawing
// anything is what makes otherwise fast search feel slow.

import { ApiError, api, type Hit } from "./api.js";

const DEBOUNCE_MS = 150;

const $ = <T extends HTMLElement>(sel: string): T =>
  document.querySelector(sel) as T;

const input = $<HTMLInputElement>("#q");
const list = $<HTMLUListElement>("#results");
const status = $<HTMLDivElement>("#status");
const saveBtn = $<HTMLButtonElement>("#save");

let timer: number | undefined;
let generation = 0;
let lastQuery = "";

input.addEventListener("input", () => {
  window.clearTimeout(timer);
  timer = window.setTimeout(() => void run(input.value.trim()), DEBOUNCE_MS);
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const first = list.querySelector<HTMLAnchorElement>("a[data-id]");
    if (first) first.click();
  }
});

async function run(q: string): Promise<void> {
  if (!q) {
    list.innerHTML = "";
    status.textContent = "";
    return;
  }
  const mine = ++generation;
  lastQuery = q;
  try {
    const quick = await api.quick(q, 10);
    if (mine === generation) render(quick.hits, [], `${ms(quick.took_ms)} ms · lexical`);
  } catch (e) {
    if (mine === generation) fail(e);
    return;
  }
  try {
    const full = await api.search(q, 20);
    if (mine === generation) {
      const labels = full.understanding?.labels?.join(" + ") ?? "";
      render(full.hits, full.expanded ?? [], `${ms(full.took_ms)} ms · ${labels || "ranked"}`);
    }
  } catch (e) {
    if (mine === generation) status.textContent = describe(e);
  }
}

/** `took_ms` is a per-stage breakdown. Printing the object gives "[object Object]". */
function ms(took: Record<string, number> | undefined): string {
  const total = took?.total ?? Object.values(took ?? {}).reduce((a, b) => a + b, 0);
  return String(Math.round(total));
}

/** Why this row is on screen: the facets that retrieved it, in words. */
const FACET_LABEL: Record<string, string> = {
  content: "about",
  intent: "asked as",
  lex_seg: "words",
  lex_tri: "substring",
};

function render(hits: Hit[], expanded: Hit[], note: string): void {
  status.textContent = `${hits.length} result${hits.length === 1 ? "" : "s"} · ${note}`;
  list.innerHTML = "";
  for (const h of hits) list.appendChild(row(h));
  // The expansion group is one hop out through the link graph: not answers to
  // the query, neighbours of the answers. Interleaving them would be a lie
  // about why they are there, so they get their own heading -- and without one
  // they were simply never shown, which made the whole graph facet invisible.
  if (expanded.length) {
    const head = document.createElement("li");
    head.className = "group";
    head.textContent = `saved around these · ${expanded.length}`;
    list.appendChild(head);
    for (const h of expanded) list.appendChild(row(h, true));
  }
}

function row(h: Hit, neighbour = false): HTMLLIElement {
  const li = document.createElement("li");
  const a = document.createElement("a");
  a.href = h.url;
  a.dataset.id = String(h.bookmark_id);
  a.className = neighbour ? "hit neighbour" : "hit";

  const title = document.createElement("div");
  title.className = "title";
  title.textContent = h.title || h.url;
  a.appendChild(title);

  const why = neighbour
    ? h.via_kind || "linked"
    : (h.facets ?? []).map((f) => FACET_LABEL[f] ?? f).join("+");
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = [h.domain, h.folder, why].filter(Boolean).join(" · ");
  a.appendChild(meta);

  if (h.cold) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = "cold";
    meta.appendChild(badge);
  }
  if (h.snippet) {
    const sn = document.createElement("div");
    sn.className = "snippet";
    sn.textContent = h.snippet;
    a.appendChild(sn);
  }

  a.addEventListener("click", (e) => {
    e.preventDefault();
    void api.opened(h.bookmark_id, lastQuery).catch(() => undefined);
    void chrome.tabs.create({ url: h.url });
    window.close();
  });
  li.appendChild(a);
  return li;
}

function describe(e: unknown): string {
  if (e instanceof ApiError && e.status === 401) return "pairing token rejected - open options";
  if (e instanceof ApiError && e.status === 0) return "server unreachable - run `facetmark serve`";
  return e instanceof Error ? e.message : String(e);
}

function fail(e: unknown): void {
  list.innerHTML = "";
  status.textContent = describe(e);
}

saveBtn.addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) return;
  saveBtn.disabled = true;
  try {
    const res = await api.save({ url: tab.url, title: tab.title ?? tab.url });
    saveBtn.textContent = res.created === false ? "already saved" : "saved";
  } catch (e) {
    saveBtn.textContent = describe(e);
  } finally {
    window.setTimeout(() => {
      saveBtn.disabled = false;
      saveBtn.textContent = "save this page";
    }, 1800);
  }
});

// Deep link from the omnibox: popup.html?q=...
const preset = new URLSearchParams(location.search).get("q");
if (preset) {
  input.value = preset;
  void run(preset);
}
input.focus();

void api
  .queueStats()
  .then((s) => {
    const pending = Number(s.pending ?? 0);
    if (pending > 0) $("#queue").textContent = `${pending} page(s) waiting for the browser`;
  })
  .catch(() => undefined);
