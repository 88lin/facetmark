// The sittings view: `/sessions` and `/session/{id}`.
//
// A sitting is a run of bookmarks saved close together in time, clustered by
// `sessions.py`. It is the cheapest structure in the whole library -- it needs
// no model, no fetch and no vector, only `date_added` -- and it is the one the
// search page leans on for "saved around these", so it is worth a page of its
// own.
//
// The list endpoint returns rows, not a count and not a `has_more`, so paging
// here is the honest version of that: ask for one more page and offer another
// button only if the last one came back full.

import { api, getToken } from "./api.js";
import { $, btn, el, link, togglePill } from "./dom.js";
import { count, shortUrl, uptimeParts, whenAdded } from "./format.js";
import { failPanel, showPanel, tokenPanel } from "./panels.js";
import { S, t } from "./state.js";

const PAGE = 25;
const SIZES = [2, 3, 5];

let ui = null;
let rows = [];
let offset = 0;
let minSize = 2;
let generation = 0;
/** Expanded sittings, by id. Each maps to its `/session/{id}` record. */
const opened = new Map();
/** One sitting, reached from the detail dialog rather than from this list. */
let focused = null;
/**
 * A sitting the detail dialog asked for, not yet fetched.
 *
 * The request and the route change arrive together, so this has to be recorded
 * before the router runs: `render()` used to start a list load whose
 * `generation` bump then threw away the single-sitting reply that was already
 * in flight, and the dialog's "Open" landed you on the full list instead.
 */
let wanted = null;

/** A span in at most two units. The units are translated; the numbers are not. */
function dur(seconds) {
  return uptimeParts(seconds)
    .map((p) => `${p.n}${t(`unit.${p.unit}`)}`)
    .join(" ");
}

function titleOf(s) {
  return s.label || t("sitting.untitled", { id: s.session_id });
}

// -------------------------------------------------------------------- rows

function memberLine(b) {
  const line = el("div", "line");
  const grow = el("div", "grow");
  const a = link(b.url, "t", b.title || shortUrl(b.url));
  a.addEventListener("click", () => {
    void api.opened(b.bookmark_id, "").catch(() => undefined);
  });
  grow.append(a, el("div", "w", [b.domain, b.folder].filter(Boolean).join(" \u00b7 ")));
  line.appendChild(grow);
  const peek = btn("\u22ef", "round peek", () => S.open(b.bookmark_id));
  peek.setAttribute("aria-label", t("detail.open"));
  peek.title = t("detail.open");
  line.appendChild(peek);
  return line;
}

function membersOf(rec) {
  const box = el("div", "rows tight");
  for (const b of rec.bookmarks ?? []) box.appendChild(memberLine(b));
  if (rec.method) {
    // Why these bookmarks are one sitting: the clustering method and the gap
    // it allowed. Without it a sitting is an assertion; with it, it is a rule.
    box.appendChild(
      el("p", "dim note", t("sitting.method", { method: rec.method, gap: dur(rec.eps_seconds) })),
    );
  }
  return box;
}

/** Five hues, dealt by position. Decoration -- see `.sitting` in app.css. */
const HUES = ["", "f-lex", "f-edge", "f-intent", "f-tri"];

/**
 * The frame a sitting is drawn in, wherever it appears: a dashed box in one of
 * five hues, with the page count set large in the gutter. `trailing` is the
 * control the row ends with -- expand, or the way back out of a focused one.
 */
function sittingBox(s, { hue = "", expanded = false, trailing }) {
  const box = el("div", ["sitting", hue, expanded ? "open" : ""].filter(Boolean).join(" "));
  // The page count, set large: it is the one number that makes a sitting a
  // sitting, and it was previously a chip the same size as everything else.
  // Numeral and unit are split so the numeral can be display-sized without
  // dragging the word up with it -- and so the row is not printing "6" twice.
  const size = el("div", "count");
  size.appendChild(el("i", "bignum", count(s.size, S.lang)));
  size.appendChild(el("div", "caps", t("sitting.unit")));
  box.appendChild(size);
  const head = el("div", "line");
  const grow = el("div", "grow");
  grow.appendChild(el("div", "t", titleOf(s)));
  grow.appendChild(
    el(
      "div",
      "w",
      [whenAdded(s.started_at, S.lang), s.span_seconds ? dur(s.span_seconds) : ""]
        .filter(Boolean)
        .join(" \u00b7 "),
    ),
  );
  head.append(grow, trailing);
  box.appendChild(head);
  return box;
}

function sittingCard(s, expanded, i) {
  const toggle = btn(expanded ? t("sitting.hide") : t("sitting.see"), "small", () =>
    void flip(s.session_id, toggle),
  );
  toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
  const box = sittingBox(s, { hue: HUES[i % HUES.length], expanded, trailing: toggle });
  const rec = opened.get(s.session_id);
  if (expanded && rec) box.appendChild(membersOf(rec));
  return box;
}

// ------------------------------------------------------------------- draw

function drawSizes() {
  ui.sizes.replaceChildren();
  for (const n of SIZES) {
    ui.sizes.appendChild(
      togglePill(t("sessions.min.n", { n }), n === minSize, () => {
        if (n === minSize) return;
        minSize = n;
        void load({ reset: true });
      }),
    );
  }
}

function drawList() {
  ui.list.replaceChildren();
  if (!rows.length) {
    showPanel({ title: t("sessions.none"), body: t("sessions.none.body"), into: ui.list });
    ui.more.replaceChildren();
    return;
  }
  const stack = el("div", "sittings");
  rows.forEach((s, i) => stack.appendChild(sittingCard(s, opened.has(s.session_id), i)));
  ui.list.appendChild(stack);

  ui.more.replaceChildren();
  // A full page is the only evidence there is another one. Asking the server
  // for a count it does not compute would be inventing one.
  if (rows.length >= offset) {
    const b = btn(t("results.more"), null, () => void load({ button: b }));
    ui.more.appendChild(b);
  }
}

function drawFocused() {
  ui.list.replaceChildren();
  ui.more.replaceChildren();
  const back = btn(t("sitting.back"), "small", () => {
    focused = null;
    drawList();
  });
  // One sitting on its own gets the same frame it had in the list, so arriving
  // here from the detail dialog does not look like arriving somewhere else.
  const box = sittingBox(focused, { expanded: true, trailing: back });
  box.appendChild(membersOf(focused));
  const stack = el("div", "sittings");
  stack.appendChild(box);
  ui.list.appendChild(stack);
}

// -------------------------------------------------------------------- load

async function flip(id, button) {
  if (opened.has(id)) {
    opened.delete(id);
    drawList();
    return;
  }
  button.disabled = true;
  try {
    opened.set(id, await api.session(id));
  } catch (e) {
    button.disabled = false;
    return failPanel(e, ui.more);
  }
  drawList();
}

async function load({ reset = false, button } = {}) {
  const mine = ++generation;
  if (reset) {
    rows = [];
    offset = 0;
    opened.clear();
    focused = null;
  }
  if (button) {
    button.disabled = true;
    button.textContent = t("results.loading");
  }
  try {
    const page = await api.sessions({ limit: PAGE, offset, minSize });
    if (mine !== generation) return;
    rows = rows.concat(page ?? []);
    offset += PAGE;
    drawList();
  } catch (e) {
    if (mine === generation) failPanel(e, ui.list);
  }
}

// ------------------------------------------------------------------- shell

/** Ask for one sitting. Honoured by the next `render()`, not before it. */
export function focus(id) {
  wanted = id;
}

/** Show one sitting on its own. The detail dialog links here. */
async function openSitting(id) {
  const mine = ++generation;
  ui.list.replaceChildren(el("p", "status", t("sitting.loading")));
  ui.more.replaceChildren();
  try {
    const rec = await api.session(id);
    if (mine !== generation) return;
    focused = rec;
    drawFocused();
  } catch (e) {
    if (mine === generation) failPanel(e, ui.list);
  }
}

export async function render() {
  drawSizes();
  if (!getToken()) return tokenPanel(false, ui.list);
  if (wanted !== null) {
    const id = wanted;
    wanted = null;
    return openSitting(id);
  }
  if (focused) return drawFocused();
  if (rows.length) return drawList();
  return load({ reset: true });
}

export function mount() {
  ui = { sizes: $("#minsize"), list: $("#slist"), more: $("#smore") };
  drawSizes();
}
