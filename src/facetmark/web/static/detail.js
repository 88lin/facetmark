// The bookmark dialog: `/bookmark/{id}` and `/bookmark/{id}/related`.
//
// One record, three tabs, and the only modal on the page. Two things here are
// about correctness rather than looks. The fact grid names the fields the
// record actually has -- `indexed.chars` and `indexed.lang`, not a word count
// and not a language, because neither of those exists -- and the related tab
// groups by edge kind rather than pouring five kinds of relationship into one
// ranked list, since "saved in the same sitting" and "reads like this one" are
// not comparable scores.
//
// The focus handling is not decoration either: a dialog that does not trap
// Tab, does not answer Escape and does not put focus back where it came from
// is a keyboard trap wearing a close button.

import { api } from "./api.js";
import { EDGE_WEIGHTS, HEALTH_TONE, factRows, groupByKind } from "./derive.js";
import { $, $$, btn, card, el, facts, link, pill, skeleton, togglePill } from "./dom.js";
import { count, shortUrl, whenAdded } from "./format.js";
import { failPanel } from "./panels.js";
import { S, t } from "./state.js";

const FOCUSABLE =
  'a[href], button:not(:disabled), input:not(:disabled), [tabindex]:not([tabindex="-1"])';

let ui = null;
let rec = null;
let tab = "about";
let related = null;
let relatedKind = "";
let relatedFor = null;
let generation = 0;
/** Where focus was before the dialog opened, so it can go back there. */
let opener = null;

// ------------------------------------------------------------------- header

function headerFor(r) {
  const head = el("div");
  const a = link(r.url, "surl", shortUrl(r.url));
  a.addEventListener("click", () => {
    void api.opened(r.bookmark_id, "").catch(() => undefined);
  });
  head.appendChild(a);

  const marks = el("div", "marks");
  const status = r.health?.status;
  if (status && status !== "unknown") {
    marks.appendChild(pill(HEALTH_TONE[status] ?? "mute", t(`health.${status}`)));
  }
  if (r.in_graveyard) marks.appendChild(pill("bad", t("detail.graveyard")));
  if (r.privacy_skipped) marks.appendChild(pill("mute", t("detail.private")));
  if (r.content_type) marks.appendChild(pill("mute", r.content_type));
  if (r.domain) marks.appendChild(pill("mute", r.domain));
  if (marks.childElementCount) head.appendChild(marks);
  return head;
}

// -------------------------------------------------------------------- about

/** Topics, entities and remembered intents: three lists of short strings. */
function tagRow(titleKey, values, tone) {
  if (!values?.length) return null;
  const box = el("div", "tagset");
  box.appendChild(el("h3", "caps", t(titleKey)));
  const marks = el("div", "marks");
  for (const v of values) marks.appendChild(pill(tone, v));
  box.appendChild(marks);
  return box;
}

function drawAbout() {
  const panel = ui.about;
  panel.replaceChildren();
  if (!rec) return;

  if (rec.summary) {
    panel.appendChild(el("p", "prose", rec.summary));
    // A summary written from the title alone is an inference about the page,
    // not a report from it -- the page was never fetched -- and the badge is
    // the reason the `basis` column exists. Karakeep-imported summaries carry
    // their own basis and stay unbadged here.
    if (rec.indexed?.summary_basis === "title") {
      const b = pill("warn", t("detail.basis.title"));
      b.title = t("detail.basis.title.why");
      panel.appendChild(b);
    }
  }

  if (rec.key_points?.length) {
    const list = el("ul", "points");
    for (const p of rec.key_points) list.appendChild(el("li", null, p));
    panel.appendChild(list);
  }

  for (const node of [
    tagRow("detail.topics", rec.topics, "vec"),
    tagRow("detail.entities", rec.entities, "mute"),
    // What this page was searched for, as recorded by the intent index. These
    // are the reader's own past queries, not model output.
    tagRow("detail.intents", rec.intent_queries, "lex"),
  ]) {
    if (node) panel.appendChild(node);
  }

  const rows = factRows(rec).map((f) => ({
    label: t(f.key),
    value:
      f.kind === "date"
        ? whenAdded(f.value, S.lang) || String(f.value)
        : f.kind === "num"
          ? count(f.value, S.lang)
          : String(f.value),
    zero: f.kind === "num" && !f.value,
    tone: f.tone,
  }));
  panel.appendChild(facts(rows));
}

// ------------------------------------------------------------------ related

function neighbourLine(n) {
  const line = el("div", "line");
  const grow = el("div", "grow");
  const a = link(n.url, "t", n.title || shortUrl(n.url));
  a.addEventListener("click", () => {
    void api.opened(n.bookmark_id, "").catch(() => undefined);
  });
  grow.append(a, el("div", "w", [n.domain, n.folder].filter(Boolean).join(" \u00b7 ")));
  line.appendChild(grow);
  const peek = btn("\u22ef", "round peek", () => void open(n.bookmark_id));
  peek.setAttribute("aria-label", t("detail.open"));
  peek.title = t("detail.open");
  line.appendChild(peek);
  return line;
}

function drawRelated() {
  const panel = ui.related;
  panel.replaceChildren();
  if (!related) return;

  const groups = groupByKind(related);
  const bar = el("div", "pillbar");
  bar.appendChild(
    togglePill(t("related.all"), relatedKind === "", () => {
      relatedKind = "";
      drawRelated();
    }, count(related.length, S.lang)),
  );
  for (const [kind, rows] of groups) {
    bar.appendChild(
      togglePill(t(`edge.${kind}`), relatedKind === kind, () => {
        relatedKind = kind;
        drawRelated();
      }, count(rows.length, S.lang)),
    );
  }
  panel.appendChild(bar);

  if (!related.length) {
    panel.appendChild(el("p", "dim note", t("related.none")));
    return;
  }

  for (const [kind, rows] of groups) {
    if (relatedKind && kind !== relatedKind) continue;
    const sec = el("section", "block");
    const head = el("div", "group-head");
    head.appendChild(el("h3", "caps", t(`edge.${kind}`)));
    // The fusion weight is the honest answer to "why is this one first". It is
    // a constant in `edges.py`, not a similarity, so it is labelled as a
    // weight rather than shown as a score.
    if (EDGE_WEIGHTS[kind] !== undefined) {
      head.appendChild(el("span", "dim", t("related.weight", { w: EDGE_WEIGHTS[kind] })));
    }
    sec.appendChild(head);
    const box = card();
    for (const n of rows) box.appendChild(neighbourLine(n));
    sec.appendChild(box);
    panel.appendChild(sec);
  }
}

async function loadRelated() {
  if (!rec) return;
  if (relatedFor === rec.bookmark_id && related) return drawRelated();
  const mine = generation;
  ui.related.replaceChildren(skeleton(3));
  try {
    const rows = await api.related(rec.bookmark_id, "", 20);
    if (mine !== generation) return;
    related = rows ?? [];
    relatedFor = rec.bookmark_id;
    relatedKind = "";
    drawRelated();
  } catch (e) {
    if (mine === generation) failPanel(e, ui.related);
  }
}

// ----------------------------------------------------------------- sittings

function drawSittings() {
  const panel = ui.sittings;
  panel.replaceChildren();
  const rows = rec?.sessions ?? [];
  if (!rows.length) {
    panel.appendChild(el("p", "dim note", t("detail.sittings.none")));
    return;
  }
  panel.appendChild(el("p", "lede", t("detail.sittings.lede")));
  const box = card();
  for (const s of rows) {
    const line = el("div", "line");
    const grow = el("div", "grow");
    grow.appendChild(el("div", "t", s.label || t("sitting.untitled", { id: s.session_id })));
    grow.appendChild(
      el(
        "div",
        "w",
        [t("sitting.size", { n: count(s.size, S.lang) }), whenAdded(s.started_at, S.lang)]
          .filter(Boolean)
          .join(" \u00b7 "),
      ),
    );
    line.appendChild(grow);
    line.appendChild(
      btn(t("sitting.see"), "small", () => {
        close();
        S.sitting(s.session_id);
      }),
    );
    box.appendChild(line);
  }
  panel.appendChild(box);
}

// --------------------------------------------------------------------- tabs

function showTab(next) {
  tab = next;
  for (const b of $$(".utab", ui.sheet)) {
    b.setAttribute("aria-selected", b.dataset.tab === tab ? "true" : "false");
  }
  ui.about.hidden = tab !== "about";
  ui.related.hidden = tab !== "related";
  ui.sittings.hidden = tab !== "sittings";
  if (tab === "related") void loadRelated();
  if (tab === "sittings") drawSittings();
}

// ------------------------------------------------------------------- dialog

function trap(e) {
  if (e.key === "Escape") {
    e.preventDefault();
    // The page-level handler bows out while the dialog is open, but this
    // listener is on the capture phase: by the time the event bubbles the
    // dialog is already shut, the guard reads false, and Escape went on to
    // clear the query behind it. Stop the key here.
    e.stopPropagation();
    return close();
  }
  if (e.key !== "Tab") return;
  const stops = $$(FOCUSABLE, ui.sheet).filter((n) => n.offsetParent !== null);
  if (!stops.length) return;
  const first = stops[0];
  const last = stops[stops.length - 1];
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault();
    first.focus();
  }
}

export function close() {
  if (ui.overlay.hidden) return;
  ui.overlay.hidden = true;
  document.removeEventListener("keydown", trap, true);
  document.body.style.overflow = "";
  generation++;
  // Back to the row that opened it. Dropping focus on a hidden dialog sends
  // the next Tab to the top of the document, which for a reader twenty rows
  // down is worse than not being able to open the dialog at all.
  opener?.focus?.();
  opener = null;
}

export function isOpen() {
  return !ui.overlay.hidden;
}

export async function open(id) {
  const mine = ++generation;
  if (ui.overlay.hidden) {
    opener = document.activeElement;
    ui.overlay.hidden = false;
    document.addEventListener("keydown", trap, true);
    // The sheet scrolls; the page behind it must not, or a trackpad flick
    // scrolls the results out from under the dialog.
    document.body.style.overflow = "hidden";
  }
  ui.sheet.scrollTop = 0;
  ui.title.textContent = t("detail.loading");
  ui.head.replaceChildren();
  ui.about.replaceChildren(skeleton(2));
  ui.related.replaceChildren();
  ui.sittings.replaceChildren();
  ui.shut.focus();
  showTab("about");

  try {
    const r = await api.bookmark(id);
    if (mine !== generation) return;
    rec = r;
    related = null;
    relatedFor = null;
    ui.title.textContent = r.title || shortUrl(r.url);
    ui.head.replaceChildren(headerFor(r));
    drawAbout();
  } catch (e) {
    if (mine !== generation) return;
    rec = null;
    ui.title.textContent = t("err.generic.title");
    ui.about.replaceChildren();
    failPanel(e, ui.about);
  }
}

/** Redraw the open dialog in the current language. */
export function render() {
  if (ui.overlay.hidden || !rec) return;
  ui.head.replaceChildren(headerFor(rec));
  drawAbout();
  if (tab === "related") drawRelated();
  if (tab === "sittings") drawSittings();
}

export function mount() {
  ui = {
    overlay: $("#overlay"),
    sheet: $("#sheet"),
    shut: $("#shut"),
    title: $("#sheet-title"),
    head: $("#sheet-head"),
    about: $("#upanel-about"),
    related: $("#upanel-related"),
    sittings: $("#upanel-sittings"),
  };

  ui.shut.addEventListener("click", close);
  // Clicking the backdrop closes; clicking inside the sheet must not, which is
  // why this listens on the overlay and checks the target rather than
  // listening on the sheet and stopping propagation.
  ui.overlay.addEventListener("click", (e) => {
    if (e.target === ui.overlay) close();
  });
  for (const b of $$(".utab", ui.sheet)) {
    b.addEventListener("click", () => showTab(b.dataset.tab));
  }
}
