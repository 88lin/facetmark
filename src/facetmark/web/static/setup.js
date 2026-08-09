// The first-run view: get bookmarks in, point at a model, build the index.
//
// This is the only screen in the app drawn at Tier 2 -- hand-drawn dashed
// frames, a serif numeral per step, colour used decoratively. `scene-app.md`
// forbids that in the operating surfaces, and rightly: a search box you use
// forty times a day should be quiet. This page is the opposite. It is read
// once, carefully, by someone who has just installed a thing and does not yet
// know what it does, and the decoration is doing work there -- three framed
// panels in three colours read as three steps before a word of it is read.
//
// It routes itself away once all three steps are done, and app.js only sends
// a reader here when at least one of them is not.

import { api } from "./api.js";
import { $, btn, el } from "./dom.js";
import { failPanel } from "./panels.js";
import { S, t } from "./state.js";

/** Frame colours, in order. Three steps, three of the palette's three hues. */
const TONES = ["", "lex", "intent"];

let ui = null;
let generation = 0;
/** The last `/admin/settings` read, so a redraw does not re-request it. */
let cfg = null;

// ------------------------------------------------------------------- state

/**
 * Which of the three steps are done.
 *
 * `vectors[0]` is the count of content vectors: bookmarks that were fetched,
 * enriched and embedded. It is the honest test of "is this library searchable"
 * -- a row in the table with no vector behind it is invisible to three of the
 * four facets.
 */
export function progress(stats, settings) {
  const rows = settings?.settings ?? [];
  const get = (key) => rows.find((r) => r.key === key);
  const local = get("embed_backend")?.value === "local";
  return {
    imported: Boolean(stats?.bookmarks),
    model: local || Boolean(get("api_key")?.set),
    // Local embeddings still need the index run; only the vectors say so.
    indexed: Boolean(stats?.vectors?.[0]),
    bookmarks: stats?.bookmarks ?? 0,
    vectors: stats?.vectors?.[0] ?? 0,
    local,
  };
}

/** True when there is nothing left for this page to tell anyone. */
export function settled(p) {
  return p.imported && p.model && p.indexed;
}

// ------------------------------------------------------------------ pieces

/**
 * One dashed frame. `n` is the numeral, `tone` the frame colour, `done`
 * swaps the numeral for a tick and dims the frame.
 */
function step(n, tone, done, titleKey, bodyKey, controls) {
  const box = el("section", tone ? `sketch ${tone}` : "sketch");
  if (done) box.classList.add("done");
  // The visible label is one glyph -- a serif numeral, or a tick. "Step 2"
  // beside a numeral 2 is the same fact twice, and the frame is only tall
  // enough for one of them. The words go to the accessible name instead, where
  // "Step 2 of 3" is worth having and costs no room.
  box.setAttribute("aria-label", t(done ? "setup.done" : "setup.step", { n }));
  const label = el("span", "label");
  label.appendChild(el("i", "stepnum", done ? "\u2713" : String(n)));
  box.appendChild(label);
  box.appendChild(el("h2", null, t(titleKey)));
  box.appendChild(el("p", null, t(bodyKey)));
  for (const node of controls) if (node) box.appendChild(node);
  return box;
}

/** A row of buttons under a step. */
function row(...nodes) {
  const r = el("div", "row");
  for (const n of nodes) if (n) r.appendChild(n);
  return r;
}

/** A short result line -- what happened, in one sentence, in place. */
function note(text, tone) {
  return el("p", tone ? `note ${tone}` : "note", text);
}

// ------------------------------------------------------------------ import

/**
 * The file picker.
 *
 * A hidden `<input type=file>` driven by a real button, rather than a styled
 * file input: browsers will not let the native control be restyled far enough
 * to look like anything else on this page, and its default label is a
 * different word in every browser.
 */
function importControls(host) {
  const input = el("input");
  input.type = "file";
  input.accept = ".html,.htm,.json";
  input.hidden = true;
  const pick = btn(t("setup.import.pick"), "primary");
  pick.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    const file = input.files?.[0];
    input.value = "";
    if (file) void runImport(file, host);
  });
  host.append(input);
  return row(pick, el("span", "dim", t("setup.import.kinds")));
}

async function runImport(file, host) {
  const status = el("p", "note");
  status.setAttribute("aria-live", "polite");
  status.textContent = t("setup.import.working", { name: file.name });
  host.appendChild(status);
  try {
    const r = await api.adminImport(file);
    S.stats = null;
    status.replaceWith(
      note(
        t("setup.import.ok", {
          inserted: r.inserted ?? 0,
          updated: r.updated ?? 0,
          skipped: (r.non_indexable ?? 0) + (r.privacy_skipped ?? 0),
        }),
        "ok",
      ),
    );
    await render();
  } catch (e) {
    const into = el("div");
    status.replaceWith(into);
    failPanel(e, into);
  }
}

// ------------------------------------------------------------------- index

function indexControls(p, host) {
  const go = btn(t("setup.index.run"), "primary");
  go.disabled = !p.imported;
  go.addEventListener("click", () => void startIndex(host));
  return row(go, p.imported ? null : el("span", "dim", t("setup.index.need")));
}

/**
 * Start the job here, watch it there.
 *
 * The progress UI lives in Settings, which owns the polling loop. Two views
 * polling one job would be two answers to one question, and the one you are
 * not looking at would still be asking.
 */
async function startIndex(host) {
  try {
    await api.adminIndex({ fetch: true });
    S.go("settings");
  } catch (e) {
    const into = el("div");
    host.appendChild(into);
    failPanel(e, into);
  }
}

// ------------------------------------------------------------------ render

function draw(p) {
  const host = el("div", "steps");

  const imported = step(
    1,
    TONES[0],
    p.imported,
    "setup.import.title",
    p.imported ? "setup.import.have" : "setup.import.body",
    [],
  );
  imported.appendChild(
    p.imported
      ? note(t("setup.import.count", { n: p.bookmarks }), "ok")
      : importControls(imported),
  );
  host.appendChild(imported);

  const model = step(
    2,
    TONES[1],
    p.model,
    "setup.model.title",
    p.local ? "setup.model.local" : p.model ? "setup.model.have" : "setup.model.body",
    [row(btn(t(p.model ? "setup.model.review" : "setup.model.set"), "", () => S.go("settings")))],
  );
  host.appendChild(model);

  const indexed = step(
    3,
    TONES[2],
    p.indexed,
    "setup.index.title",
    p.indexed ? "setup.index.have" : "setup.index.body",
    [],
  );
  indexed.appendChild(
    p.indexed ? note(t("setup.index.count", { n: p.vectors }), "ok") : indexControls(p, indexed),
  );
  host.appendChild(indexed);

  if (settled(p)) {
    const done = el("div", "tint context setup-done");
    done.appendChild(el("h2", null, t("setup.ready.title")));
    done.appendChild(el("p", null, t("setup.ready.body")));
    done.appendChild(row(btn(t("setup.ready.go"), "primary", () => S.go("search"))));
    host.appendChild(done);
  }

  ui.steps.replaceChildren(host);
}

export async function render() {
  const mine = ++generation;
  if (!cfg) {
    try {
      cfg = await api.adminSettings();
    } catch {
      // Admin off, or no token yet. The stats half still tells the reader
      // where they are; the model step falls back to "not set", which is the
      // safe assumption and still links somewhere useful.
      cfg = null;
    }
  }
  if (mine !== generation) return;
  let stats = S.stats;
  if (!stats) {
    try {
      stats = S.stats = await api.stats();
    } catch {
      stats = null;
    }
  }
  if (mine !== generation) return;
  draw(progress(stats, cfg));
}

/** Language switch: the same facts, relabelled. No requests. */
export function relabel() {
  return render();
}

/** Called after a job or a settings write, so the ticks are not stale. */
export function invalidate() {
  cfg = null;
}

export function mount() {
  ui = { steps: $("#setup-steps") };
}
