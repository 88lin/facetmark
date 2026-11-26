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
  type Hit,
  loadSettings,
  nextRequest,
  type QueryFilters,
  type QueueSummary,
  type RequestContext,
  type Settings,
  startCursor,
  summarizeQueue,
} from "./api.ts";
import { applyI18n, initLangToggle, t } from "./i18n.ts";
import { readSaves } from "./save-delivery.ts";
import { describeError, queueText, workerRequest } from "./ui.ts";

const DEBOUNCE_MS = 150;
const PAGE = 20;

const $ = <T extends HTMLElement>(sel: string): T =>
  document.querySelector(sel) as T;

const input = $<HTMLInputElement>("#q");
const list = $<HTMLUListElement>("#results");
const status = $<HTMLDivElement>("#status");
const retrySearch = $<HTMLButtonElement>("#search-retry");
const saveBtn = $<HTMLButtonElement>("#save");

let timer: number | undefined;
let generation = 0;
let lastQuery = "";
let lastNote: () => string = () => "";
let reading: AbortController | undefined;
let composing = false;
let paging = false;
let saving = false;
let saveNote = "";
let saveError: unknown;
let queue: QueueSummary | undefined;
let searchSettings: Settings | undefined;
// The rendered list is state now, not a function argument: "load more" appends
// to it, so the previous pages have to survive the next render.
let rows: Hit[] = [];
let neighbours: Hit[] = [];
let cursor: PageCursor = startCursor("");

function invalidate(): void {
  generation += 1;
  reading?.abort();
  window.clearTimeout(timer);
  rows = []; neighbours = []; paging = false; lastQuery = "";
  searchSettings = undefined;
  cursor = startCursor("");
  list.replaceChildren();
  retrySearch.hidden = true;
  lastNote = () => input.value.trim() ? t("pop.searching") : "";
  status.textContent = lastNote();
  if (!input.value.trim()) empty(t("pop.start"));
}

function scheduleSearch(eventComposing = false): void {
  const value = input.value.trim();
  invalidate();
  if (composing || eventComposing || !value) return;
  timer = window.setTimeout(() => void run(value), DEBOUNCE_MS);
}

function finishComposition(): void {
  composing = false;
  scheduleSearch();
}

input.addEventListener("input", event => scheduleSearch((event as InputEvent).isComposing));
input.addEventListener("compositionstart", () => { composing = true; invalidate(); });
input.addEventListener("compositionend", finishComposition);
input.addEventListener("blur", () => { if (composing) finishComposition(); });
retrySearch.addEventListener("click", () => {
  input.focus();
  invalidate();
  void run(input.value.trim());
});

input.addEventListener("keydown", (e) => {
  if (e.isComposing || composing || e.keyCode === 229) return;
  if (e.key === "Escape") { input.value = ""; invalidate(); return; }
  if (e.key === "Enter") {
    e.preventDefault();
    const first = list.querySelector<HTMLAnchorElement>("a[data-id]");
    if (first && lastQuery === input.value.trim()) first.click();
    else { window.clearTimeout(timer); void run(input.value.trim()); }
  }
});

async function run(q: string): Promise<void> {
  retrySearch.hidden = true;
  const mine = ++generation;
  reading?.abort();
  const controller = reading = new AbortController();
  const context: RequestContext = { signal: controller.signal };
  if (!q) {
    rows = [];
    neighbours = [];
    cursor = startCursor("");
    list.innerHTML = "";
    status.textContent = "";
    lastNote = () => "";
    lastQuery = "";
    empty(t("pop.start"));
    return;
  }
  lastQuery = q;
  cursor = startCursor(q);
  let keywordLoaded = false;
  try {
    context.settings = await loadSettings();
    if (mine !== generation) return;
    searchSettings = context.settings;
    try {
      const quick = await api.quick(q, 10, 0, undefined, context);
      if (mine !== generation) return;
      keywordLoaded = true;
      rows = quick.hits; neighbours = [];
      // Paging starts from the ranked result, whose depth can differ.
      render(() => withFilters(`${quick.hits.length} · ${t("pop.lexical")}`, quick.filters));
    } catch {
      if (controller.signal.aborted || mine !== generation) return;
    }
    const full = await api.search(q, PAGE, 0, undefined, context);
    if (mine === generation) {
      rows = full.hits;
      neighbours = full.expanded ?? [];
      cursor = advance(cursor, full);
      render(() => withFilters(pageText(cursor), full.filters));
    }
  } catch (e) {
    if (mine !== generation) return;
    retrySearch.hidden = false;
    if (!keywordLoaded) { fail(e); return; }
    lastNote = () => `${t(rows.length ? "pop.keywordRetained" : "pop.keywordEmpty")} · ${describeSearchError(e)}`;
    status.textContent = lastNote();
  }
}

async function loadMore(button: HTMLButtonElement): Promise<void> {
  const req = nextRequest(cursor, PAGE);
  if (!req || paging) return;
  const mine = generation;
  const previousSize = rows.length;
  const hadFocus = document.activeElement === button;
  paging = true;
  button.disabled = true;
  button.textContent = t("pop.loading");
  try {
    // `req.depth` is the whole point: it pins the candidate depth to the one
    // page 1 was ranked at, so this page continues that ranking rather than
    // re-fusing at a deeper pool and disagreeing about what page 1 was.
    const more = await api.search(cursor.query, req.limit, req.offset, req.depth, { signal: reading?.signal, settings: searchSettings });
    if (mine !== generation) return;
    const known = new Set(rows.map((h) => h.bookmark_id));
    rows = rows.concat(more.hits.filter((h) => !known.has(h.bookmark_id)));
    cursor = advance(cursor, more);
    paging = false;
    render(() => withFilters(pageText(cursor), more.filters));
    if (hadFocus && document.activeElement === document.body) {
      const next = rows.length > previousSize ? list.querySelectorAll<HTMLAnchorElement>("a[data-id]")[previousSize] : undefined;
      (next ?? input).focus();
    }
  } catch (e) {
    if (mine === generation) {
      lastNote = () => describeSearchError(e);
      paging = false;
      render(lastNote);
      if (hadFocus && document.activeElement === document.body)
        list.querySelector<HTMLButtonElement>(".more button")?.focus();
    }
  } finally { if (mine === generation) paging = false; }
}

function pageText(value: PageCursor): string {
  if (value.windowEnded) return t("pop.windowEnded", value.seen);
  return value.more ? t(value.capped ? "pop.pageCapped" : "pop.page", value.seen, value.total) : t("pop.resultCount", value.seen);
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

function render(note: () => string): void {
  const hits = rows;
  const expanded = neighbours;
  const focusedId = list.querySelector<HTMLAnchorElement>("a[data-id]:focus")?.dataset.id;
  lastNote = note;
  status.textContent = note();
  list.innerHTML = "";
  if (!hits.length && !expanded.length) {
    empty(t("pop.empty"));
    if (focusedId) input.focus();
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
  if (focusedId) {
    (list.querySelector<HTMLAnchorElement>(`a[data-id="${CSS.escape(focusedId)}"]`) ?? input).focus();
  }
}

function empty(message: string): void {
  const li = document.createElement("li");
  li.className = "empty";
  const glyph = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  glyph.setAttribute("viewBox", "0 0 24 24");
  glyph.setAttribute("fill", "none");
  glyph.setAttribute("stroke", "currentColor");
  glyph.setAttribute("stroke-width", "1.5");
  glyph.setAttribute("stroke-linecap", "round");
  glyph.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M21 21l-5-5M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0");
  glyph.appendChild(path);
  li.append(glyph, document.createTextNode(message));
  list.replaceChildren(li);
}

function moreRow(): HTMLLIElement {
  const li = document.createElement("li");
  li.className = "more";
  const b = document.createElement("button");
  b.type = "button";
  b.className = "ext-button";
  b.disabled = paging;
  b.textContent = cursor.capped
    ? `${t("pop.more")} · ${t("pop.pageCapped", cursor.seen, cursor.total)}`
    : `${t("pop.more")} · ${t("pop.page", cursor.seen, cursor.total)}`;
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
  if (openable) { a.href = h.url; a.target = "_blank"; a.rel = "noopener noreferrer"; }
  else { a.tabIndex = 0; a.setAttribute("role", "link"); a.setAttribute("aria-disabled", "true"); }
  a.dataset.id = String(h.bookmark_id);
  a.className = neighbour ? "hit neighbour" : "hit";

  const title = document.createElement("div");
  title.className = "title";
  title.title = h.title || h.url;
  title.textContent = title.title;
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
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    if (!openable) return;
    const query = lastQuery;
    void workerRequest({ type: "open-page", url: h.url, bookmark_id: h.bookmark_id, query, settings: searchSettings }).then(() => {
      window.close();
    }).catch(error => { status.textContent = describeError(error); });
  });
  li.appendChild(a);
  return li;
}

function describeSearchError(error: unknown): string {
  return error instanceof ApiError && error.code === "invalid" ? t("pop.badSearchResponse") : describeError(error);
}

function fail(e: unknown): void {
  list.innerHTML = "";
  lastNote = () => describeSearchError(e);
  status.textContent = lastNote();
}

saveBtn.addEventListener("click", async () => {
  if (saving) return;
  saving = true;
  saveBtn.disabled = true;
  saveNote = "pop.saving";
  saveError = undefined;
  renderSave();
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.url || !/^https?:\/\//i.test(tab.url)) throw new Error(t("pop.unsupportedPage"));
    const value = await workerRequest<{ result: { bookmark_id: number; created?: boolean } }>({
      type: "save-page", body: { url: tab.url, title: tab.title ?? tab.url },
    });
    const res = value.result;
    if (!res || !Number.isSafeInteger(res.bookmark_id) || res.bookmark_id <= 0
      || (res.created !== undefined && typeof res.created !== "boolean")) throw new ApiError(t("opt.badResponse"), 200, "invalid");
    saveNote = res.created === false ? "pop.alreadySaved" : "pop.saved";
  } catch (e) {
    saveNote = "";
    saveError = e;
  } finally {
    saving = false;
    saveBtn.disabled = false;
    renderSave();
    await showPending();
  }
});

function renderSave(): void {
  saveBtn.textContent = t(saving ? "pop.saving" : "pop.save");
  const message = $("#save-status");
  message.textContent = saveError ? describeError(saveError) : saveNote ? t(saveNote) : "";
  message.className = saveError ? "bad" : saveNote && !saving ? "ok" : "";
}

async function showPending(): Promise<void> {
  try { $("#save-recovery").hidden = !(await readSaves()).length; }
  catch { $("#save-recovery").hidden = false; }
}

// Deep link from the omnibox: popup.html?q=...
applyI18n();
initLangToggle();
input.disabled = false;
saveBtn.disabled = false;
const preset = new URLSearchParams(location.search).get("q");
if (preset) {
  input.value = preset;
  void run(preset);
} else empty(t("pop.start"));
input.focus();

void api
  .queueStats()
  .then((s) => {
    queue = summarizeQueue(s);
    $("#queue").textContent = queueText(queue);
  })
  .catch(() => undefined);

void showPending();
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local") return;
  if (changes["save-deliveries"]) void showPending();
  if (changes.endpoint || changes.token) {
    invalidate();
    if (input.value.trim()) { lastNote = () => t("pop.connectionChanged"); status.textContent = lastNote(); }
  }
});
// Re-render the list in the new language without a round trip: the chips, the
// group heading and the empty state are all translated at draw time.
document.addEventListener("langchange", () => {
  applyI18n();
  renderSave();
  if (rows.length || neighbours.length || lastQuery) render(lastNote);
  else { status.textContent = lastNote(); if (!input.value.trim()) empty(t("pop.start")); }
  if (queue) $("#queue").textContent = queueText(queue);
});
