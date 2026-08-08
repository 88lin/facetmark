// The synthesise view: `/synthesize`.
//
// The endpoint answers a question out of the pages the library already holds
// and returns claims, each carrying the numbered sources it was drawn from.
// This view's whole job is to keep that provenance attached: a claim is only
// worth reading if the two clicks back to the page it came from are right
// there, which is why every citation is a button that lights up its source
// card rather than a footnote marker.
//
// What it deliberately does not show is a confidence score. `Synthesis` has no
// per-claim confidence field -- the server returns `{text, sources}` and
// nothing else -- so a percentage next to a claim would be invented. The
// citation count is the honest version of the same signal.

import { api, getToken } from "./api.js";
import { HEALTH_TONE, sourceIndex } from "./derive.js";
import { $, btn, card, el, link, pill, skeleton } from "./dom.js";
import { count, shortUrl } from "./format.js";
import { failPanel, showPanel, tokenPanel } from "./panels.js";
import { S, ensureHealth, t } from "./state.js";

let ui = null;
/** The last `/synthesize` document, kept so a language switch can redraw. */
let doc = null;
let asked = "";
let generation = 0;
let limit = 8;

export function focus() {
  ui?.q.focus();
}

// ------------------------------------------------------------------ notices

/**
 * The panel above the form.
 *
 * `provider: "mock"` is not a failure and the button stays live: the mock
 * provider returns deterministic text, which is exactly what the test suite
 * wants and exactly what a reader must not mistake for an answer about their
 * own library. Saying so once, up front, is cheaper than a disclaimer on every
 * claim.
 */
async function notice() {
  const h = await ensureHealth(api);
  if (h?.provider === "mock") {
    showPanel({
      title: t("ask.mock.title"),
      body: t("ask.mock.body"),
      cmd: t("ask.mock.cmd"),
      tone: "warn",
      into: ui.panel,
    });
    return;
  }
  ui.panel.replaceChildren();
}

// ------------------------------------------------------------------- claims

/** A citation chip. Clicking it scrolls to the source and lights it. */
function cite(n) {
  const b = btn(String(n), null, () => {
    const target = $(`#src-${n}`);
    if (!target) return;
    for (const lit of ui.out.querySelectorAll(".src.lit")) lit.classList.remove("lit");
    target.classList.add("lit");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  b.className = "pill cite";
  const src = sourceIndex(doc?.sources).get(n);
  b.title = src ? src.title || shortUrl(src.url) : `#${n}`;
  return b;
}

function claimCard(claim, i) {
  const box = el("div", "claim");
  box.appendChild(el("span", "n", i + 1));
  box.appendChild(el("p", null, claim.text));
  const cites = el("div", "cites");
  for (const n of claim.sources ?? []) cites.appendChild(cite(n));
  // Not a confidence score. The number of distinct sources a claim rests on is
  // the only support signal this endpoint actually reports -- and a single
  // chip already says "one source" without being counted.
  const many = (claim.sources ?? []).length;
  if (many > 1) cites.appendChild(el("span", "dim", t("ask.cite.n", { n: many })));
  box.appendChild(cites);
  return box;
}

// ------------------------------------------------------------------ sources

function sourceCard(s) {
  const box = card("src");
  box.id = `src-${s.n}`;

  const head = el("div", "line");
  head.appendChild(el("span", "no", s.n));
  const grow = el("div", "grow");
  const a = link(s.url, "t", s.title || shortUrl(s.url));
  // Opening a source is an open like any other, and the cold layer is built
  // out of opens. Not recording it here would make the synthesise view a blind
  // spot in the one signal a bookmark export does not come with.
  a.addEventListener("click", () => {
    void api.opened(s.bookmark_id, asked).catch(() => undefined);
  });
  grow.append(a, el("div", "w", shortUrl(s.url)));
  head.appendChild(grow);

  const marks = el("div", "marks");
  if (s.health && s.health !== "unknown") {
    // The server also sends `badge`, a short English phrase. It is not
    // translated server-side, so rendering it would put English into the
    // Chinese page; the status maps onto a key we already have in both.
    marks.appendChild(pill(HEALTH_TONE[s.health] ?? "mute", t(`health.${s.health}`)));
  }
  const peek = btn("\u22ef", "round peek", () => S.open(s.bookmark_id));
  peek.setAttribute("aria-label", t("detail.open"));
  peek.title = t("detail.open");
  head.append(marks, peek);
  box.appendChild(head);

  if (s.excerpt) box.appendChild(el("p", "prose", s.excerpt));
  return box;
}

// -------------------------------------------------------------------- draw

function drawGaps(gaps) {
  if (!gaps?.length) return null;
  const box = el("div", "panel warn");
  box.appendChild(el("h2", null, t("ask.gaps")));
  box.appendChild(el("p", null, t("ask.gaps.why")));
  const list = el("ul", "points");
  // The gap strings are the server's own words about the retrieval it just
  // ran -- which facets came back empty, how many cited pages look dead. They
  // are data, so they are shown as they arrive rather than translated into a
  // sentence nobody measured.
  for (const g of gaps) list.appendChild(el("li", null, g));
  box.appendChild(list);
  return box;
}

function draw() {
  ui.out.replaceChildren();
  if (!doc) return;

  // Under the mock provider `degraded` is a foregone conclusion, and the
  // notice above already explains why in more useful words. Two stacked
  // panels saying the same thing is how a page starts feeling like a form.
  if (doc.degraded && S.health?.provider !== "mock") {
    const box = el("div", "panel bad");
    box.appendChild(el("h2", null, t("ask.degraded")));
    box.appendChild(el("p", null, t("ask.degraded.why")));
    ui.out.appendChild(box);
  }

  const claims = doc.claims ?? [];
  if (claims.length) {
    const sec = el("section", "block");
    sec.appendChild(el("h2", null, t("ask.claims", { n: count(claims.length, S.lang) })));
    const stack = el("div", "rows");
    claims.forEach((c, i) => stack.appendChild(claimCard(c, i)));
    sec.appendChild(stack);
    ui.out.appendChild(sec);
  } else {
    showPanel({ title: t("ask.none"), body: t("ask.none.body"), into: ui.out });
  }

  const gaps = drawGaps(doc.gaps);
  if (gaps) ui.out.appendChild(gaps);

  const sources = doc.sources ?? [];
  if (sources.length) {
    const sec = el("section", "block");
    sec.appendChild(el("h2", null, t("ask.sources", { n: count(sources.length, S.lang) })));
    sec.appendChild(el("p", "lede", t("ask.sources.lede")));
    const stack = el("div", "rows");
    for (const s of sources) stack.appendChild(sourceCard(s));
    sec.appendChild(stack);
    ui.out.appendChild(sec);
  }

  if (doc.model) {
    ui.out.appendChild(el("p", "dim mono", t("ask.model", { model: doc.model })));
  }
}

// -------------------------------------------------------------------- run

async function run(q) {
  if (!q) return;
  const mine = ++generation;
  asked = q;
  ui.go.disabled = true;
  ui.out.replaceChildren(skeleton(3));
  try {
    const r = await api.synthesize(q, limit);
    if (mine !== generation) return;
    doc = r;
    draw();
    void notice();
  } catch (e) {
    if (mine !== generation) return;
    doc = null;
    ui.out.replaceChildren();
    failPanel(e, ui.panel);
  } finally {
    if (mine === generation) ui.go.disabled = false;
  }
}

// ------------------------------------------------------------------- shell

export async function render() {
  if (!getToken()) return tokenPanel(false, ui.panel);
  if (doc) {
    draw();
    return notice();
  }
  ui.out.replaceChildren();
  return notice();
}

export function preset(q) {
  ui.q.value = q;
}

export function mount() {
  ui = {
    form: $("#askform"),
    q: $("#aq"),
    go: $("#ago"),
    limit: $("#alimit"),
    panel: $("#apanel"),
    out: $("#aout"),
  };

  ui.form.addEventListener("submit", (e) => {
    e.preventDefault();
    void run(ui.q.value.trim());
  });

  ui.limit.addEventListener("change", () => {
    const v = Number(ui.limit.value);
    // The server caps this at 20 and rejects 0. Clamping here means a typo in
    // the box is a clamped number rather than a 422 the reader has to decode.
    limit = Number.isFinite(v) ? Math.max(1, Math.min(20, Math.round(v))) : 8;
    ui.limit.value = String(limit);
  });
}
