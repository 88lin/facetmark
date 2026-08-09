// The search view: the query box, the suggestion list, the retrieval mode
// pills, the result cards and paging.
//
// Two things here are load-bearing and easy to get wrong by accident. The
// generation counter: every keystroke can start a request, and an older reply
// arriving after a newer one would redraw the wrong answer, so a reply whose
// generation is stale is dropped rather than rendered. And the cursor's depth,
// which paging.js pins to the depth page one was ranked at -- with more than
// one facet in play, RRF is not order-stable as the candidate pool deepens.

import { api, getToken } from "./api.js";
import { ADVANCED_RUNGS, RUNGS } from "./derive.js";
import { $, btn, el, numberCard, numbers, pill, skeleton, togglePill } from "./dom.js";
import { FACET_KEYS, count, shortUrl, totalMs, whenAdded } from "./format.js";
import { advance, mergePage, nextRequest, pageLabel, startCursor } from "./paging.js";
import { failPanel, showPanel, tokenPanel } from "./panels.js";
import { S, ensureStats, t, tOr } from "./state.js";

const PAGE = 20;
const DEBOUNCE_MS = 160;
// Slower than the search debounce on purpose: suggestions are a second opinion
// while you type, and firing them at the same rate as the search they sit under
// would double the request count for no extra information.
const SUGGEST_MS = 200;
const SUGGEST_MIN = 4;

let ui = null;
let rows = [];
let neighbours = [];
let cursor = startCursor("");
let generation = 0;
let timer;
let sugTimer;
let sugGeneration = 0;
let sugRows = [];
let sugAt = -1;
// Kept so a language switch can redraw the status line without re-querying.
let lastTook = {};
let lastTail = "";
let rung = "full";
let expand = 8;

export function query() {
  return cursor.query;
}

export function focus() {
  ui?.q.focus();
}

// ------------------------------------------------------------------- rungs

function drawRungs() {
  const bar = ui.rungs;
  bar.replaceChildren();
  for (const r of RUNGS) {
    bar.appendChild(
      togglePill(t(r.key), r.id === rung, () => {
        if (rung === r.id) return;
        rung = r.id;
        drawRungs();
        if (cursor.query) void run(cursor.query, { force: true });
      }),
    );
  }
  drawAdvanced();
  const chosen = [...RUNGS, ...ADVANCED_RUNGS].find((r) => r.id === rung) ?? RUNGS[0];
  ui.rungNote.textContent = t(chosen.why);
}

/**
 * The two expensive rungs, inside the "More options" drawer.
 *
 * They are the same choice as the four in the pillbar -- one `rung` variable,
 * one `config` on the request -- so they render as a second pill group rather
 * than as a separate control. Keeping them in the drawer is what stops a
 * reader from landing on a model-call-per-keystroke rung by brushing past it.
 */
function drawAdvanced() {
  if (!ui.advRungs) return;
  ui.advRungs.replaceChildren();
  for (const r of ADVANCED_RUNGS) {
    ui.advRungs.appendChild(
      togglePill(t(r.key), r.id === rung, () => {
        if (rung === r.id) return;
        rung = r.id;
        drawRungs();
        if (cursor.query) void run(cursor.query, { force: true });
      }),
    );
  }
}

// -------------------------------------------------------------- suggestions

function closeSuggest() {
  sugRows = [];
  sugAt = -1;
  ui.sugg.replaceChildren();
  ui.sugg.hidden = true;
  ui.q.setAttribute("aria-expanded", "false");
}

function drawSuggest() {
  ui.sugg.replaceChildren();
  sugRows.forEach((h, i) => {
    const li = el("li");
    li.setAttribute("role", "presentation");
    const b = el("button");
    b.type = "button";
    b.id = `sug-${i}`;
    b.setAttribute("role", "option");
    b.setAttribute("aria-selected", i === sugAt ? "true" : "false");
    b.appendChild(el("span", "t", h.title || shortUrl(h.url)));
    b.appendChild(el("span", "w", [h.domain, h.folder].filter(Boolean).join(" \u00b7 ")));
    b.addEventListener("click", () => {
      ui.q.value = h.title || shortUrl(h.url);
      closeSuggest();
      void run(ui.q.value.trim(), { force: true });
    });
    li.appendChild(b);
    ui.sugg.appendChild(li);
  });
  const foot = el("li", "sugg-foot", t("sugg.foot"));
  foot.setAttribute("role", "presentation");
  ui.sugg.appendChild(foot);
  ui.sugg.hidden = false;
  ui.q.setAttribute("aria-expanded", "true");
  ui.q.setAttribute("aria-activedescendant", sugAt >= 0 ? `sug-${sugAt}` : "");
}

function moveSuggest(step) {
  if (!sugRows.length) return false;
  sugAt = (sugAt + step + sugRows.length + 1) % (sugRows.length + 1);
  if (sugAt === sugRows.length) sugAt = -1;
  drawSuggest();
  return true;
}

async function askSuggest(text) {
  if (text.length < SUGGEST_MIN) return closeSuggest();
  const mine = ++sugGeneration;
  try {
    const r = await api.suggest(text, 6);
    if (mine !== sugGeneration) return;
    sugRows = r.hits ?? [];
    sugAt = -1;
    if (!sugRows.length) return closeSuggest();
    drawSuggest();
  } catch {
    // A suggestion list is an optimisation. It never gets to interrupt.
    closeSuggest();
  }
}

// ------------------------------------------------------------------ results

/** Every chip carries its own explanation, because a legend nobody reads is
 *  not an explanation. */
function chip(tone, key, fallbackKey) {
  const hint = tOr(`${key}.why`, fallbackKey ? `${fallbackKey}.why` : "");
  return pill(tone, tOr(key, fallbackKey), hint && !hint.endsWith(".why") ? hint : undefined);
}

/**
 * The snippet with the query terms marked.
 *
 * Built from DOM text nodes, never `innerHTML`: the snippet is whatever the
 * scraped page contained and the query is whatever the reader typed, and
 * either one can carry a `<`. Case-insensitive on the assumption that the
 * reader is matching a memory, not a token; CJK queries match the raw
 * substring, which is the only segmentation-independent rule.
 */
function snippetNode(text, query) {
  const box = el("div", "snippet");
  const terms = [...new Set((query ?? "").split(/\s+/).filter(Boolean))];
  if (!text || !terms.length) {
    box.textContent = text ?? "";
    return box;
  }
  const lower = text.toLowerCase();
  // One pass, longest term first at each position, so "vector search" marks
  // the phrase where both words are present rather than the two words apart.
  const sorted = terms.map((w) => w.toLowerCase()).sort((a, b) => b.length - a.length);
  let at = 0;
  while (at < text.length) {
    let hitLen = 0;
    for (const term of sorted) {
      if (term && lower.startsWith(term, at)) {
        hitLen = term.length;
        break;
      }
    }
    if (hitLen) {
      box.appendChild(el("mark", null, text.slice(at, at + hitLen)));
      at += hitLen;
    } else {
      // Extend the plain run to just before the next match, so the text is a
      // handful of nodes rather than one per character.
      let next = text.length;
      for (const term of sorted) {
        if (!term) continue;
        const i = lower.indexOf(term, at + 1);
        if (i !== -1 && i < next) next = i;
      }
      box.appendChild(document.createTextNode(text.slice(at, next)));
      at = next;
    }
  }
  return box;
}

function hitCard(h, rank, neighbour) {
  const li = el("li", "row-wrap");
  const a = el("a", neighbour ? "hit near" : "hit");
  a.href = h.url;
  a.target = "_blank";
  a.rel = "noopener";

  if (!neighbour) a.appendChild(el("span", "rank", rank));
  a.appendChild(el("div", "title", h.title || shortUrl(h.url)));
  a.appendChild(el("div", "where", [h.domain, h.folder].filter(Boolean).join(" \u00b7 ")));
  if (h.snippet) a.appendChild(snippetNode(h.snippet, neighbour ? "" : cursor.query));

  const marks = el("div", "marks");
  if (neighbour) {
    marks.appendChild(chip("edge", `edge.${h.via_kind}`, "mark.linked"));
  } else {
    for (const f of h.facets ?? []) {
      // Vector facets read blue, lexical facets read gold. That split is the
      // one distinction in a result row a reader actually has to learn.
      const tone = f === "lex_seg" || f === "lex_tri" ? "lex" : "vec";
      if (FACET_KEYS[f]) marks.appendChild(chip(tone, FACET_KEYS[f]));
      else marks.appendChild(pill(tone, f));
    }
  }
  if (h.cold) marks.appendChild(chip("warn", "mark.cold"));
  if (h.content_type) marks.appendChild(pill("mute", h.content_type));
  const when = whenAdded(h.date_added, S.lang);
  if (when) marks.appendChild(pill("mute", when));
  if (marks.childElementCount) a.appendChild(marks);

  // Recording the open is what eventually makes the cold layer mean something:
  // a browser export carries no usage telemetry at all, so until facetmark has
  // watched a few opens of its own, "never opened" is true of everything.
  a.addEventListener("click", () => {
    void api.opened(h.bookmark_id, cursor.query).catch(() => undefined);
  });

  const peek = btn("\u22ef", "round peek", () => S.open(h.bookmark_id));
  peek.setAttribute("aria-label", t("detail.open"));
  peek.title = t("detail.open");

  li.append(a, peek);
  return li;
}

function renderResults({ append = false } = {}) {
  if (!append) ui.results.replaceChildren();
  const already = ui.results.childElementCount;
  const frag = document.createDocumentFragment();
  rows.slice(already).forEach((h, i) => frag.appendChild(hitCard(h, already + i + 1, false)));
  ui.results.appendChild(frag);

  ui.more.replaceChildren();
  if (nextRequest(cursor, PAGE)) {
    const b = btn(t("results.more"), null, () => void loadMore(b));
    ui.more.appendChild(b);
  }

  // The expansion group is one hop out through the link graph: neighbours of
  // the answers, not answers. Interleaving them would misstate why they are on
  // screen, so they keep their own heading.
  ui.around.hidden = neighbours.length === 0;
  ui.aroundHead.textContent = t("group.expanded", { n: count(neighbours.length, S.lang) });
  ui.aroundList.replaceChildren();
  for (const h of neighbours) ui.aroundList.appendChild(hitCard(h, 0, true));
}

function note(cur, took, tail) {
  lastTook = took ?? {};
  lastTail = tail ?? "";
  const { key, vars } = pageLabel(cur);
  const parts = [
    cur.seen === 1 ? t("results.one") : t(key, vars),
    t("results.ms", { ms: count(totalMs(took), S.lang) }),
  ];
  if (tail) parts.push(tail);
  ui.status.textContent = parts.join(" \u00b7 ");
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
  const s = S.stats;
  const into = ui.panel;
  if (s && !s.bookmarks) {
    return showPanel({
      title: t("setup.import.title"),
      body: t("setup.import.body"),
      cmd: t("setup.import.cmd"),
      into,
    });
  }
  const vec = Array.isArray(s?.vectors) ? s.vectors[0] : 0;
  if (s && s.bookmarks && !s.with_body && !vec) {
    return showPanel({
      title: t("setup.index.title"),
      body: t("setup.index.body", { n: count(s.bookmarks, S.lang) }),
      cmd: t("setup.index.cmd"),
      into,
    });
  }
  if (!queried) {
    // A library that already holds pages earns its census on the first screen:
    // the four headline numbers above the invitation copy, so the page is not
    // a search box floating in whitespace. The same four cards the library
    // view leads with, so the two screens agree about what counts.
    if (s && s.bookmarks) {
      const strip = numbers([
        numberCard(count(s.bookmarks, S.lang), t("stats.bookmarks"), "ink"),
        numberCard(count(s.indexable, S.lang), t("stats.indexable")),
        numberCard(count(s.enriched, S.lang), t("stats.enriched"), "gold"),
        numberCard(count(s.sessions, S.lang), t("stats.sessions"), "pop"),
      ]);
      return showPanel({ title: t("start.title"), body: t("start.body"), extra: [strip], into });
    }
    return showPanel({ title: t("start.title"), body: t("start.body"), into });
  }
  const waiting = s ? (s.queue?.pending ?? 0) + (s.queue?.leased ?? 0) : 0;
  showPanel({
    title: t("empty.title"),
    body: [t("empty.body"), waiting ? t("empty.queue", { n: count(waiting, S.lang) }) : ""],
    into,
  });
}

// ------------------------------------------------------------------- search

export async function run(q, { force = false } = {}) {
  if (!q) {
    rows = [];
    neighbours = [];
    cursor = startCursor("");
    ui.results.replaceChildren();
    ui.more.replaceChildren();
    ui.around.hidden = true;
    ui.status.textContent = "";
    await ensureStats(api);
    emptyPanel(false);
    return;
  }
  if (!force && q === cursor.query && rows.length) return;

  const mine = ++generation;
  cursor = startCursor(q);
  ui.panel.replaceChildren();
  ui.status.textContent = t("results.searching");
  ui.results.replaceChildren(skeleton(5));

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
      rows.length ? t("results.all", { n: count(rows.length, S.lang) }) : t("results.searching"),
      t("results.lexical"),
    ].join(" \u00b7 ");
  } catch (e) {
    if (mine === generation) {
      ui.results.replaceChildren();
      ui.status.textContent = "";
      failPanel(e, ui.panel);
    }
    return;
  }

  try {
    const full = await api.search({ q, limit: PAGE, config: rung, expand });
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
      await ensureStats(api);
      if (mine === generation) emptyPanel(true);
    }
  } catch (e) {
    // Stage one is already on screen and is a real answer, so a stage-two
    // failure downgrades the page rather than blanking it.
    if (mine === generation) failPanel(e, ui.panel);
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
    const more = await api.search({
      q: cursor.query,
      limit: req.limit,
      offset: req.offset,
      depth: req.depth,
      config: rung,
      // Neighbours belong to the query, not to a page of it. Asking for them
      // again would append a second copy of the same group.
      expand: 0,
    });
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
      failPanel(e, ui.panel);
    }
  }
}

// -------------------------------------------------------------------- shell

/** Redraw from the rows already in memory. A language switch is not a new
 *  question and should not cost an embedding round trip. */
export async function render() {
  drawRungs();
  if (!getToken()) return tokenPanel(false, ui.panel);
  if (cursor.query) {
    if (rows.length || neighbours.length) {
      renderResults();
      note(cursor, lastTook, lastTail);
      return;
    }
    return run(cursor.query, { force: true });
  }
  await ensureStats(api);
  emptyPanel(false);
}

export function preset(q) {
  ui.q.value = q;
  cursor = startCursor(q);
}

export function mount() {
  ui = {
    form: $("#seek"),
    q: $("#q"),
    sugg: $("#sugg"),
    rungs: $("#rungs"),
    rungNote: $("#rung-note"),
    optsToggle: $("#opts-toggle"),
    opts: $("#opts"),
    advRungs: $("#adv-rungs"),
    expand: $("#expand"),
    status: $("#status"),
    panel: $("#panel"),
    results: $("#results"),
    more: $("#more"),
    around: $("#around"),
    aroundHead: $("#around-head"),
    aroundList: $("#around-list"),
  };

  ui.q.addEventListener("input", () => {
    const v = ui.q.value.trim();
    clearTimeout(timer);
    clearTimeout(sugTimer);
    timer = setTimeout(() => void run(v), DEBOUNCE_MS);
    sugTimer = setTimeout(() => void askSuggest(v), SUGGEST_MS);
  });

  ui.form.addEventListener("submit", (e) => {
    e.preventDefault();
    clearTimeout(timer);
    // Both timers, not just the search one. The suggestion timer is the
    // slower of the two, so a submit typed straight after the last keystroke
    // closes the list and then watches it reopen over the results.
    clearTimeout(sugTimer);
    closeSuggest();
    void run(ui.q.value.trim(), { force: true });
  });

  ui.q.addEventListener("keydown", (e) => {
    if (ui.sugg.hidden) return;
    if (e.key === "ArrowDown" && moveSuggest(1)) return e.preventDefault();
    if (e.key === "ArrowUp" && moveSuggest(-1)) return e.preventDefault();
    if (e.key === "Escape") {
      e.stopPropagation();
      return closeSuggest();
    }
    if (e.key === "Enter" && sugAt >= 0) {
      e.preventDefault();
      ui.sugg.querySelector(`#sug-${sugAt}`)?.click();
    }
  });
  ui.q.addEventListener("blur", () => setTimeout(closeSuggest, 140));

  ui.optsToggle.addEventListener("click", () => {
    const open = ui.opts.hidden;
    ui.opts.hidden = !open;
    ui.optsToggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  ui.expand.addEventListener("change", () => {
    const v = Number(ui.expand.value);
    expand = Number.isFinite(v) ? Math.max(0, Math.min(20, Math.round(v))) : 8;
    ui.expand.value = String(expand);
    if (cursor.query) void run(cursor.query, { force: true });
  });

  drawRungs();
}

/** The list the shell's ArrowUp/ArrowDown walks. */
export function rowLinks() {
  return [...ui.results.querySelectorAll(".hit"), ...ui.aroundList.querySelectorAll(".hit")];
}

export function clearQuery() {
  ui.q.value = "";
  closeSuggest();
  ui.q.focus();
  void run("");
}
