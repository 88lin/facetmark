// The facetmark search page.
//
// Structure: this file owns the DOM and the network. Everything that can be
// wrong in a way a person would not notice on screen -- paging arithmetic,
// the result counter, date and number formatting -- lives in paging.js and
// format.js, which are pure and are unit tested under tests/web/.
//
// Nothing here writes innerHTML. Titles, snippets and folder names come out of
// the user's own library, which is a browser bookmark export: it contains
// whatever HTML the pages it was scraped from contained. textContent
// everywhere is not defensive style, it is the reason this page cannot be
// made to execute a bookmark.

import { FACET_KEYS, count, shortUrl, totalMs, whenAdded } from "./format.js";
import { applyTo, pickLang, translator } from "./i18n.js";
import { advance, mergePage, nextRequest, pageLabel, startCursor } from "./paging.js";

const PAGE = 20;
const DEBOUNCE_MS = 160;
const TOKEN_KEY = "fm-token";
const LANG_KEY = "fm-lang";
const THEME_KEY = "fm-theme";

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};

const ui = {
  q: $("#q"),
  form: $("#ask"),
  status: $("#status"),
  panel: $("#panel"),
  results: $("#results"),
  more: $("#more"),
  around: $("#around"),
  aroundHead: $("#around-head"),
  aroundList: $("#around-list"),
  stats: $("#stats"),
  version: $("#version"),
};

let t = (k) => k;
let strings = { en: {}, zh: {} };
let lang = "en";
let token = "";
let stats = null; // cached /stats, fetched lazily
let rows = [];
let neighbours = [];
let cursor = startCursor("");
let generation = 0;
let timer;
// Kept so a language switch can redraw the status line without re-querying.
let lastTook = {};
let lastTail = "";

// ---------------------------------------------------------------- transport

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`);
    this.status = status;
  }
}

async function call(path, init = {}) {
  let res;
  try {
    res = await fetch(path, {
      ...init,
      headers: {
        ...(init.body ? { "content-type": "application/json" } : {}),
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

const api = {
  quick: (q, limit) => call(`/quick?q=${encodeURIComponent(q)}&limit=${limit}`),
  search: (q, limit, offset = 0, depth = 0) =>
    call("/search", {
      method: "POST",
      body: JSON.stringify({ q, limit, offset, ...(depth ? { depth } : {}) }),
    }),
  stats: () => call("/stats"),
  opened: (id, query) =>
    call("/open", { method: "POST", body: JSON.stringify({ bookmark_id: id, query }) }),
};

// ------------------------------------------------------------------ panels

function clearPanel() {
  ui.panel.replaceChildren();
}

/** A translation, or a fallback when the key is missing (`t` echoes the key). */
function tOr(key, fallbackKey) {
  const s = t(key);
  if (s !== key) return s;
  // `t` echoes an unknown key back, which is the right default on screen but
  // the wrong one here: without a fallback, echo the key rather than looking
  // up `undefined` and rendering the string "undefined".
  return fallbackKey ? t(fallbackKey) : s;
}

/** A titled block with optional prose, a shell command, and extra nodes. */
function showPanel({ title, body, cmd, bad = false, extra = [], into = ui.panel }) {
  const box = el("div", bad ? "panel bad" : "panel");
  box.appendChild(el("h2", null, title));
  for (const line of [].concat(body ?? [])) {
    if (line) box.appendChild(el("p", null, line));
  }
  if (cmd) {
    const pre = el("pre", "cmd");
    pre.appendChild(el("code", null, cmd));
    box.appendChild(pre);
  }
  for (const node of extra) box.appendChild(node);
  into.replaceChildren(box);
}

function tokenPanel(rejected = false, into = ui.panel) {
  const form = el("form", "pair");
  const input = el("input");
  input.type = "password";
  input.autocomplete = "off";
  input.spellcheck = false;
  input.placeholder = t("token.placeholder");
  input.setAttribute("aria-label", t("token.placeholder"));
  const submit = el("button", "btn primary", t("token.save"));
  submit.type = "submit";
  form.append(input, submit);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const v = input.value.trim();
    if (!v) return;
    token = v;
    try {
      localStorage.setItem(TOKEN_KEY, v);
    } catch {
      /* private mode: the token then lives for this tab only, which is fine */
    }
    clearPanel();
    stats = null;
    void refresh();
  });
  showPanel({
    title: t("err.token.title"),
    body: [t("err.token.body"), rejected ? t("token.bad") : ""],
    cmd: t("err.token.cmd"),
    bad: rejected,
    extra: [form],
    into,
  });
}

function failPanel(e, into = ui.panel) {
  if (e instanceof ApiError && e.status === 401) return tokenPanel(true, into);
  if (e instanceof ApiError && e.status === 0) {
    return showPanel({
      title: t("err.offline.title"),
      body: t("err.offline.body"),
      cmd: t("err.offline.cmd"),
      bad: true,
      into,
    });
  }
  showPanel({ title: t("err.generic.title"), body: e?.message ?? String(e), bad: true, into });
}

/**
 * What to say when the reader is looking at an empty list.
 *
 * The distinction this makes is the reason the library view exists at all: a
 * first-time user with an unimported library, a user who imported but never
 * indexed, and a user whose query genuinely matches nothing all see an empty
 * page, and only one of the three has a search problem.
 */
function emptyPanel(queried) {
  const s = stats;
  if (s && !s.bookmarks) {
    return showPanel({
      title: t("setup.import.title"),
      body: t("setup.import.body"),
      cmd: t("setup.import.cmd"),
    });
  }
  const vec = Array.isArray(s?.vectors) ? s.vectors[0] : 0;
  if (s && s.bookmarks && !s.with_body && !vec) {
    return showPanel({
      title: t("setup.index.title"),
      body: t("setup.index.body", { n: count(s.bookmarks, lang) }),
      cmd: t("setup.index.cmd"),
    });
  }
  if (!queried) {
    return showPanel({ title: t("start.title"), body: t("start.body") });
  }
  const waiting = s ? (s.queue?.pending ?? 0) + (s.queue?.leased ?? 0) : 0;
  showPanel({
    title: t("empty.title"),
    body: [t("empty.body"), waiting ? t("empty.queue", { n: count(waiting, lang) }) : ""],
  });
}

// ----------------------------------------------------------------- results

function hitRow(h, neighbour) {
  const li = el("li", "fresh");
  const a = el("a", "hit");
  a.href = h.url;
  a.target = "_blank";
  a.rel = "noopener";

  a.appendChild(el("div", "title", h.title || shortUrl(h.url)));
  a.appendChild(el("div", "where", [h.domain, h.folder].filter(Boolean).join(" \u00b7 ")));

  if (h.snippet) a.appendChild(el("div", "snippet", h.snippet));

  // Every chip carries its own explanation. "asked as" and "substring" are the
  // shortest honest labels for those facets, but they are jargon to a reader
  // who has just installed this, and a legend somewhere else on the page is a
  // legend nobody reads.
  const chip = (cls, key, fallbackKey) => {
    const span = el("span", cls, tOr(key, fallbackKey));
    const hint = tOr(`${key}.why`, fallbackKey ? `${fallbackKey}.why` : "");
    if (hint && !hint.endsWith(".why")) span.title = hint;
    return span;
  };

  const marks = el("div", "marks");
  if (neighbour) {
    marks.appendChild(chip("chip via", `edge.${h.via_kind}`, "mark.linked"));
  } else {
    for (const f of h.facets ?? []) {
      if (FACET_KEYS[f]) marks.appendChild(chip("chip", FACET_KEYS[f]));
      else marks.appendChild(el("span", "chip", f));
    }
  }
  if (h.cold) marks.appendChild(chip("chip cold", "mark.cold"));
  const when = whenAdded(h.date_added, lang);
  if (when) marks.appendChild(el("span", "chip when", when));
  if (marks.childElementCount) a.appendChild(marks);

  // Recording the open is what eventually makes the cold layer mean something:
  // a browser export carries no usage telemetry at all, so until facetmark has
  // watched a few opens of its own, "never opened" is true of everything.
  a.addEventListener("click", () => {
    void api.opened(h.bookmark_id, cursor.query).catch(() => undefined);
  });

  li.appendChild(a);
  return li;
}

function renderResults({ append = false } = {}) {
  if (!append) ui.results.replaceChildren();
  const already = ui.results.childElementCount;
  const frag = document.createDocumentFragment();
  for (const h of rows.slice(already)) frag.appendChild(hitRow(h, false));
  ui.results.appendChild(frag);

  ui.more.replaceChildren();
  if (nextRequest(cursor, PAGE)) {
    const b = el("button", "btn", t("results.more"));
    b.type = "button";
    b.addEventListener("click", () => void loadMore(b));
    ui.more.appendChild(b);
  }

  // The expansion group is one hop out through the link graph: neighbours of
  // the answers, not answers. Interleaving them would misstate why they are on
  // screen, so they keep their own heading -- and before the extension grew
  // one, they were simply never shown, which made the whole graph facet
  // invisible.
  ui.around.hidden = neighbours.length === 0;
  ui.aroundHead.textContent = t("group.expanded", { n: count(neighbours.length, lang) });
  ui.aroundList.replaceChildren();
  for (const h of neighbours) ui.aroundList.appendChild(hitRow(h, true));
}

function skeleton() {
  const ol = el("ol", "skeleton");
  for (let i = 0; i < 5; i++) ol.appendChild(el("li"));
  ui.results.replaceChildren(ol);
}

function note(cur, took, tail) {
  lastTook = took ?? {};
  lastTail = tail ?? "";
  const { key, vars } = pageLabel(cur);
  const parts = [
    cur.seen === 1 ? t("results.one") : t(key, vars),
    t("results.ms", { ms: count(totalMs(took), lang) }),
  ];
  if (tail) parts.push(tail);
  ui.status.textContent = parts.join(" \u00b7 ");
}

// ------------------------------------------------------------------ search

async function run(q, { force = false } = {}) {
  if (!q) {
    rows = [];
    neighbours = [];
    cursor = startCursor("");
    ui.results.replaceChildren();
    ui.more.replaceChildren();
    ui.around.hidden = true;
    ui.status.textContent = "";
    await ensureStats();
    emptyPanel(false);
    return;
  }
  if (!force && q === cursor.query && rows.length) return;

  const mine = ++generation;
  cursor = startCursor(q);
  clearPanel();
  ui.status.textContent = t("results.searching");
  skeleton();

  // Stage one is FTS5 and answers in single-digit milliseconds; stage two needs
  // an embedding round trip. Drawing nothing until stage two is what makes
  // otherwise fast search feel slow. The cursor deliberately does not follow
  // stage one: it is a different ranking, with its own depth, and paging from
  // it would continue a list that is about to be replaced.
  try {
    const quick = await api.quick(q, 10);
    if (mine !== generation) return;
    rows = quick.hits ?? [];
    neighbours = [];
    renderResults();
    ui.status.textContent = [
      rows.length ? t("results.all", { n: count(rows.length, lang) }) : t("results.searching"),
      t("results.lexical"),
    ].join(" \u00b7 ");
  } catch (e) {
    if (mine === generation) {
      ui.results.replaceChildren();
      ui.status.textContent = "";
      failPanel(e);
    }
    return;
  }

  try {
    const full = await api.search(q, PAGE);
    if (mine !== generation) return;
    rows = full.hits ?? [];
    neighbours = full.expanded ?? [];
    cursor = advance(cursor, full);
    renderResults();
    // The understanding labels are the pipeline's own words for what it thought
    // the query was about. They are data, not UI copy, so they are shown
    // untranslated -- inventing a translation for a model's output would be
    // asserting something about it that nobody checked.
    const labels = full.understanding?.labels?.join(" + ");
    note(cursor, full.took_ms, labels || t("results.ranked"));
    if (!rows.length && !neighbours.length) {
      await ensureStats();
      if (mine === generation) emptyPanel(true);
    }
  } catch (e) {
    // Stage one is already on screen and is a real answer, so a stage-two
    // failure downgrades the page rather than blanking it.
    if (mine === generation) failPanel(e);
  }
}

async function loadMore(button) {
  const req = nextRequest(cursor, PAGE);
  if (!req) return;
  const mine = generation;
  const before = ui.results.childElementCount;
  button.disabled = true;
  button.textContent = t("results.loading");
  try {
    // `req.depth` is the whole point: it pins the candidate depth to the one
    // page 1 was ranked at, so this page continues that ranking instead of
    // re-fusing over a deeper pool and disagreeing about what page 1 was.
    const more = await api.search(cursor.query, req.limit, req.offset, req.depth);
    if (mine !== generation) return;
    rows = mergePage(rows, more.hits);
    cursor = advance(cursor, more);
    renderResults({ append: true });
    // The tail names the ranking mode, which page 2 shares with page 1. Passing
    // "" here would silently drop it and make the line look like it changed.
    note(cursor, more.took_ms, lastTail);
    // `renderResults` replaces the button, which drops focus on the floor: for
    // a keyboard reader the next Tab would restart at the top of the document,
    // above twenty rows they have already read. Move focus to the first row
    // that was just added, which is where they asked to go.
    ui.results.children[before]?.querySelector("a")?.focus();
  } catch (e) {
    if (mine === generation) {
      button.disabled = false;
      button.textContent = t("results.more");
      failPanel(e);
    }
  }
}

// ----------------------------------------------------------------- library

async function ensureStats() {
  if (stats) return stats;
  try {
    stats = await api.stats();
  } catch {
    stats = null; // an empty state without stats is still better than an error
  }
  return stats;
}

function statGroup(titleKey, entries, noteKey) {
  const rowsIn = entries.filter(([, v]) => v !== undefined && v !== null);
  if (!rowsIn.length) return null;
  const sec = el("section", "stat-group");
  sec.appendChild(el("h2", null, t(titleKey)));
  const dl = el("dl");
  for (const [label, value] of rowsIn) {
    const row = el("div", value ? "stat" : "stat zero");
    row.appendChild(el("dt", null, label));
    row.appendChild(el("dd", null, count(value, lang)));
    dl.appendChild(row);
  }
  sec.appendChild(dl);
  if (noteKey) sec.appendChild(el("p", "note", t(noteKey)));
  return sec;
}

/** Sub-dictionaries (`queue`, `health`, `edges_by_kind`) keyed by a prefix. */
function fromMap(map, prefix) {
  return Object.entries(map ?? {}).map(([k, v]) => [
    t(`${prefix}.${k}`) === `${prefix}.${k}` ? k : t(`${prefix}.${k}`),
    v,
  ]);
}

async function showLibrary() {
  ui.stats.replaceChildren(el("p", "status", t("stats.loading")));
  let s;
  try {
    s = stats = await api.stats();
  } catch (e) {
    failPanel(e, ui.stats);
    return;
  }
  const vec = Array.isArray(s.vectors) ? s.vectors : [0, 0];
  const cold = s.cold_layer ?? {};
  const groups = [
    statGroup("stats.group.library", [
      [t("stats.bookmarks"), s.bookmarks],
      [t("stats.indexable"), s.indexable],
      [t("stats.privacy_skipped"), s.privacy_skipped],
      [t("stats.domains"), s.domains],
    ]),
    statGroup(
      "stats.group.text",
      [
        [t("stats.with_body"), s.with_body],
        [t("stats.enriched"), s.enriched],
        [t("stats.intent_kept"), s.intent_kept],
      ],
      "stats.note.text",
    ),
    statGroup("stats.group.vectors", [
      [t("stats.vec_content"), vec[0]],
      [t("stats.vec_intent"), vec[1]],
      [t("stats.content_vectors_stale"), s.content_vectors_stale],
    ]),
    statGroup("stats.group.graph", [
      [t("stats.sessions"), s.sessions],
      [t("stats.edges"), s.edges],
      ...fromMap(s.edges_by_kind, "edge"),
    ]),
    statGroup(
      "stats.group.queue",
      [...fromMap(s.queue, "queue"), [t("queue.waiting"), s.queue_waiting]],
      "stats.note.queue",
    ),
    statGroup("stats.group.health", fromMap(s.health, "health")),
    statGroup(
      "stats.group.cold",
      [
        [t("cold.cold"), cold.cold],
        [t("cold.servable_cold"), cold.servable_cold],
        [t("cold.unservable_cold"), cold.unservable_cold],
        [t("cold.never_opened"), cold.never_opened],
        [t("cold.older_than_cutoff"), cold.older_than_cutoff],
        [t("cold.old_and_never_opened"), cold.old_and_never_opened],
        [t("cold.health_unchecked"), cold.health_unchecked],
      ],
      "stats.note.cold",
    ),
  ].filter(Boolean);
  ui.stats.replaceChildren(...groups);
}

// ------------------------------------------------------------------- shell

function currentView() {
  return location.hash === "#/library" ? "library" : "search";
}

/** Redraw whatever is on screen. Half of this page is generated text, so a
 *  language switch, a fresh token and a view change all end up here.
 *
 *  Re-renders from the rows already in memory rather than re-querying:
 *  switching to the library tab and back, or flipping to Chinese, is not a new
 *  question and should not cost an embedding round trip. */
async function refresh() {
  if (currentView() === "library") return showLibrary();
  if (!token) return tokenPanel(false);
  if (cursor.query) {
    if (rows.length || neighbours.length) {
      renderResults();
      note(cursor, lastTook, lastTail);
      return;
    }
    return run(cursor.query, { force: true });
  }
  await ensureStats();
  emptyPanel(false);
}

function route() {
  const view = currentView();
  $("#view-search").hidden = view !== "search";
  $("#view-library").hidden = view === "search";
  for (const b of document.querySelectorAll(".view")) {
    if (b.dataset.view === view) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  }
  if (view === "search") ui.q.focus();
  void refresh();
}

/** Language state and the static markup only. Generated text is `refresh`. */
function applyLang(next) {
  lang = next;
  t = translator(strings, lang);
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  $("#lang").textContent = lang === "zh" ? "EN" : "\u4e2d\u6587";
  applyTo(document, t);
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {
    /* private mode: the choice then lasts for this tab only */
  }
}

function setTheme(next) {
  document.documentElement.setAttribute(
    "data-theme",
    next === "system"
      ? matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : next,
  );
  $("#theme-glyph").textContent = next === "light" ? "\u2600" : next === "dark" ? "\u263e" : "\u25d1";
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    /* ignore */
  }
}

function wire() {
  ui.q.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => void run(ui.q.value.trim()), DEBOUNCE_MS);
  });
  ui.form.addEventListener("submit", (e) => {
    e.preventDefault();
    clearTimeout(timer);
    void run(ui.q.value.trim(), { force: true });
  });

  for (const b of document.querySelectorAll(".view")) {
    b.addEventListener("click", () => {
      location.hash = b.dataset.view === "library" ? "#/library" : "#/search";
    });
  }
  window.addEventListener("hashchange", route);

  $("#lang").addEventListener("click", () => {
    applyLang(lang === "zh" ? "en" : "zh");
    void refresh();
  });

  let theme = "system";
  try {
    theme = localStorage.getItem(THEME_KEY) ?? "system";
  } catch {
    /* ignore */
  }
  $("#theme").addEventListener("click", () => {
    theme = theme === "system" ? "light" : theme === "light" ? "dark" : "system";
    setTheme(theme);
  });
  setTheme(theme);

  document.addEventListener("keydown", (e) => {
    const typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName ?? "");
    if (e.key === "/" && !typing) {
      e.preventDefault();
      location.hash = "#/search";
      ui.q.focus();
      ui.q.select();
      return;
    }
    if (e.key === "Escape" && currentView() === "search") {
      ui.q.value = "";
      ui.q.focus();
      void run("");
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      const links = [...document.querySelectorAll(".hit")];
      if (!links.length) return;
      const at = links.indexOf(document.activeElement);
      // From the query box, ArrowDown enters the list; ArrowUp from the first
      // row goes back to it, so the keyboard path is a loop, not a trap.
      const next = e.key === "ArrowDown" ? at + 1 : at - 1;
      e.preventDefault();
      if (next < 0) ui.q.focus();
      else links[Math.min(next, links.length - 1)].focus();
    }
  });
}

async function boot() {
  // Strings and pairing in parallel: neither needs the other and both are on
  // loopback, so the page is interactive in about one round trip.
  const [loaded, paired] = await Promise.allSettled([
    fetch("/app/static/strings.json").then((r) => r.json()),
    fetch("/app/boot", { cache: "no-store" }).then((r) => r.json()),
  ]);
  if (loaded.status === "fulfilled") strings = loaded.value;

  if (paired.status === "fulfilled") {
    ui.version.textContent = `v${paired.value.version}`;
    // Not paired is not an error. The server declines to hand a token to a
    // page it cannot confirm was loaded from this machine, which is exactly
    // what it is meant to do -- see `_pairing_gate` in api.py. The stored
    // token is the fallback for that case.
    if (paired.value.paired) token = paired.value.token;
  }
  if (!token) {
    try {
      token = localStorage.getItem(TOKEN_KEY) ?? "";
    } catch {
      /* ignore */
    }
  }

  let storedLang = null;
  try {
    storedLang = localStorage.getItem(LANG_KEY);
  } catch {
    /* ignore */
  }
  applyLang(pickLang(storedLang, navigator.languages ?? [navigator.language]));

  wire();

  const preset = new URLSearchParams(location.search).get("q");
  if (preset) ui.q.value = preset;
  cursor = startCursor(preset ?? "");
  route();
}

void boot();
