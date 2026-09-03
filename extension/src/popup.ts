// Two-stage search box.
//
// Stage one is the FTS5 path, which answers in single-digit milliseconds and
// goes on screen immediately. Stage two is the full four-facet pipeline, which
// needs an embedding round trip and arrives a few hundred milliseconds later,
// then replaces the list in place. Waiting for stage two before drawing
// anything is what makes otherwise fast search feel slow.

import {
  ApiError,
  type PageCursor,
  advance,
  api,
  describePage,
  describeQueue,
  type Hit,
  nextRequest,
  type QueryFilters,
  startCursor,
  summarizeQueue,
} from "./api.ts";
import { applyI18n, initLangToggle, t } from "./i18n.ts";

const DEBOUNCE_MS = 150;
const PAGE = 20;

const $ = <T extends HTMLElement>(sel: string): T =>
  document.querySelector(sel) as T;

const input = $<HTMLInputElement>("#q");
const list = $<HTMLUListElement>("#results");
const status = $<HTMLDivElement>("#status");
const saveBtn = $<HTMLButtonElement>("#save");

let timer: number | undefined;
let generation = 0;
let lastQuery = "";
let lastNote = "";
// The rendered list is state now, not a function argument: "load more" appends
// to it, so the previous pages have to survive the next render.
let rows: Hit[] = [];
let neighbours: Hit[] = [];
let cursor: PageCursor = startCursor("");

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
    rows = [];
    neighbours = [];
    cursor = startCursor("");
    list.innerHTML = "";
    status.textContent = "";
    lastNote = "";
    return;
  }
  const mine = ++generation;
  lastQuery = q;
  cursor = startCursor(q);
  try {
    const quick = await api.quick(q, 10);
    if (mine === generation) {
      rows = quick.hits;
      neighbours = [];
      // The cursor deliberately does not follow the lexical pass. It is a
      // different ranking from the full pipeline -- different facets, its own
      // depth -- so paging from it would continue a list that is about to be
      // replaced.
      render(withFilters(
        `${quick.hits.length} · ${ms(quick.took_ms)} ms · ${t("pop.lexical")}`,
        quick.filters,
      ));
    }
  } catch (e) {
    if (mine === generation) fail(e);
    return;
  }
  try {
    const full = await api.search(q, PAGE);
    if (mine === generation) {
      rows = full.hits;
      neighbours = full.expanded ?? [];
      cursor = advance(cursor, full);
      const labels = full.understanding?.labels?.join(" + ") ?? "";
      render(withFilters(
        `${describePage(cursor)} · ${ms(full.took_ms)} ms · ${labels || t("pop.ranked")}`,
        full.filters,
      ));
    }
  } catch (e) {
    if (mine === generation) status.textContent = describe(e);
  }
}

async function loadMore(button: HTMLButtonElement): Promise<void> {
  const req = nextRequest(cursor, PAGE);
  if (!req) return;
  const mine = generation;
  button.disabled = true;
  button.textContent = t("pop.loading");
  try {
    // `req.depth` is the whole point: it pins the candidate depth to the one
    // page 1 was ranked at, so this page continues that ranking rather than
    // re-fusing at a deeper pool and disagreeing about what page 1 was.
    const more = await api.search(cursor.query, req.limit, req.offset, req.depth);
    if (mine !== generation) return;
    const known = new Set(rows.map((h) => h.bookmark_id));
    rows = rows.concat(more.hits.filter((h) => !known.has(h.bookmark_id)));
    cursor = advance(cursor, more);
    render(`${describePage(cursor)} · ${ms(more.took_ms)} ms`);
  } catch (e) {
    if (mine === generation) {
      button.disabled = false;
      button.textContent = describe(e);
    }
  }
}

/** `took_ms` is a per-stage breakdown. Printing the object gives "[object Object]". */
function ms(took: Record<string, number> | undefined): string {
  const total = took?.total ?? Object.values(took ?? {}).reduce((a, b) => a + b, 0);
  return String(Math.round(total));
}

/**
 * The grammar the server read out of the box, as a compact line.
 *
 * The popup is 360px wide and has one status line, so this is terse on
 * purpose. The part that is not optional is `ignored`: the server answers the
 * rest of a query whose filter did not parse, and without this the user sees a
 * result list that quietly ignored half of what they typed.
 */
function filterSummary(filters: QueryFilters | null | undefined): string {
  if (!filters) return "";
  const parts: string[] = [];
  for (const f of filters.fields ?? []) {
    parts.push(`${f.negate ? "-" : ""}${f.field}:${f.value}`);
  }
  for (const term of filters.exclude ?? []) parts.push(`-${term}`);
  if (filters.sort) parts.push(`sort:${filters.sort}`);
  for (const bad of filters.ignored ?? []) parts.push(`${t("pop.ignored")} ${bad}`);
  return parts.join(" · ");
}

/** A note, plus the grammar echo when the query carried any. */
function withFilters(note: string, filters: QueryFilters | null | undefined): string {
  const applied = filterSummary(filters);
  return applied ? `${note} · ${applied}` : note;
}

/** Why this row is on screen: the facets that retrieved it, in words. */
const FACET_KEY: Record<string, string> = {
  content: "pop.about",
  intent: "pop.askedAs",
  lex_seg: "pop.words",
  lex_tri: "pop.substring",
};

function render(note: string): void {
  const hits = rows;
  const expanded = neighbours;
  lastNote = note;
  status.textContent = note;
  list.innerHTML = "";
  if (!hits.length && !expanded.length) {
    const li = document.createElement("li");
    li.className = "empty";
    const glyph = document.createElement("span");
    glyph.className = "glyph";
    glyph.textContent = "○";
    li.appendChild(glyph);
    li.appendChild(document.createTextNode(t("pop.empty")));
    list.appendChild(li);
    return;
  }
  for (const h of hits) list.appendChild(row(h));
  if (nextRequest(cursor, PAGE)) list.appendChild(moreRow());
  // The expansion group is one hop out through the link graph: not answers to
  // the query, neighbours of the answers. Interleaving them would be a lie
  // about why they are there, so they get their own heading -- and without one
  // they were simply never shown, which made the whole graph facet invisible.
  if (expanded.length) {
    const head = document.createElement("li");
    head.className = "group";
    head.textContent = `${t("pop.group")} · ${expanded.length}`;
    list.appendChild(head);
    for (const h of expanded) list.appendChild(row(h, true));
  }
}

function moreRow(): HTMLLIElement {
  const li = document.createElement("li");
  li.className = "more";
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = cursor.capped
    ? `${t("pop.more")} (${cursor.seen} of ${cursor.total}+)`
    : `${t("pop.more")} (${cursor.seen} of ${cursor.total})`;
  b.addEventListener("click", () => void loadMore(b));
  li.appendChild(b);
  return li;
}

function row(h: Hit, neighbour = false): HTMLLIElement {
  const li = document.createElement("li");
  const a = document.createElement("a");
  // `href` only for a scheme a browser will navigate to. A bookmark can hold
  // `javascript:` -- a bookmarklet is a bookmark -- and a middle-click or
  // ctrl-click never reaches the handler below. This is an extension page, so
  // that navigation would run in a privileged context; it never becomes an
  // href unless it is http(s), and `chrome.tabs.create` refuses those schemes
  // anyway, which is the second reason the row simply does not open.
  const openable = /^https?:\/\//i.test(h.url);
  if (openable) a.href = h.url;
  else a.tabIndex = 0;
  a.dataset.id = String(h.bookmark_id);
  a.className = neighbour ? "hit neighbour" : "hit";

  const title = document.createElement("div");
  title.className = "title";
  title.textContent = h.title || h.url;
  a.appendChild(title);

  const meta = document.createElement("div");
  meta.className = "meta";
  const lead = [h.domain, h.folder].filter(Boolean).join(" · ");
  if (lead) meta.appendChild(document.createTextNode(lead));
  if (neighbour) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = h.via_kind || t("pop.linked");
    meta.appendChild(chip);
  } else {
    for (const f of h.facets ?? []) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = t(FACET_KEY[f] ?? f);
      meta.appendChild(chip);
    }
  }
  a.appendChild(meta);

  if (h.cold) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = t("pop.cold");
    meta.appendChild(badge);
  }
  // Tags are the user's own filing vocabulary, verbatim: shown untranslated
  // for the same reason the facet chips are translated -- these are not our
  // words, and rendering them as anything else would assert something nobody
  // checked about what the user meant.
  for (const tag of h.tags ?? []) {
    const chip = document.createElement("span");
    chip.className = "chip tag";
    chip.textContent = `#${tag}`;
    meta.appendChild(chip);
  }
  if (h.snippet) {
    const sn = document.createElement("div");
    sn.className = "snippet";
    sn.textContent = h.snippet;
    a.appendChild(sn);
  }

  a.addEventListener("click", (e) => {
    e.preventDefault();
    if (!openable) return;
    void api.opened(h.bookmark_id, lastQuery).catch(() => undefined);
    void chrome.tabs.create({ url: h.url });
    window.close();
  });
  li.appendChild(a);
  return li;
}

function describe(e: unknown): string {
  if (e instanceof ApiError && e.status === 401) return t("pop.tokenRejected");
  if (e instanceof ApiError && e.status === 0) return t("pop.serverUnreachable");
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
    saveBtn.textContent = res.created === false ? t("pop.alreadySaved") : t("pop.saved");
  } catch (e) {
    saveBtn.textContent = describe(e);
  } finally {
    window.setTimeout(() => {
      saveBtn.disabled = false;
      saveBtn.textContent = t("pop.save");
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
    const line = describeQueue(summarizeQueue(s));
    if (line) $("#queue").textContent = line;
  })
  .catch(() => undefined);

applyI18n();
initLangToggle();
// Re-render the list in the new language without a round trip: the chips, the
// group heading and the empty state are all translated at draw time.
document.addEventListener("langchange", () => {
  applyI18n();
  if (rows.length || neighbours.length) render(lastNote);
});
