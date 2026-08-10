// The settings view: what this server is configured with, and one job runner.
//
// Two things share this page because they share a cause. You come here to
// point facetmark at a model, and the next thing you want is to find out
// whether that worked -- first by probing it, then by watching an index run
// finish. Splitting them across two screens would mean typing a key on one
// page and learning it was wrong on another.
//
// Three facts about the server shape this file:
//
//   * An environment variable outranks the config file. A box whose value is
//     locked by `FACETMARK_API_KEY` is rendered read-only and says so, because
//     the alternative is a reader typing into a box that cannot win.
//   * The key is never sent back. `/admin/settings` returns `sk-...a1b2`, so
//     an untouched key field must not be submitted -- writing the mask back
//     would set the key to the mask.
//   * Cancelling an index job takes effect at the next stage boundary, not
//     immediately. The button says so rather than pretending otherwise.

import { api, ApiError } from "./api.js";
import { $, btn, card, el, pill } from "./dom.js";
import { failPanel } from "./panels.js";
import * as setup from "./setup.js";
import { S, t } from "./state.js";

/** The seven stages `service.index_all` reports, in the order it reports them. */
const STAGES = [
  "fetch",
  "enrich",
  "embed_content",
  "filter_intents",
  "embed_intents",
  "sessions",
  "edges",
];

/** How often to ask about a running job. Two seconds, and only while running. */
const POLL_MS = 2000;

/** The fields the model form owns, in the order they are asked for. */
const MODEL_FIELDS = ["api_key", "base_url", "chat_model", "embed_model"];

/** Everything else writable, grouped so the page is not one long list. */
const GROUPS = [
  { key: "settings.group.embed", fields: ["embed_backend", "embed_dim", "local_embed_path"] },
  {
    key: "settings.group.limits",
    fields: ["request_timeout", "fetch_concurrency", "enrich_concurrency"],
  },
  {
    key: "settings.group.privacy",
    fields: ["privacy_excluded_domains", "chat_model_fallbacks"],
  },
];

let ui = null;
let generation = 0;
let cfg = null;
/** The setInterval handle for the job poll. Never more than one. */
let poll = 0;
let job = null;

// ------------------------------------------------------------------ fields

const rowOf = (key) => cfg?.settings?.find((r) => r.key === key) ?? null;

/** A value the server sent, as something an input can hold. */
function asText(value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

/**
 * One labelled input.
 *
 * The returned node carries `read()`, which returns `undefined` when the field
 * should not be part of the write: unchanged, or locked by the environment. A
 * PUT that sends every field every time would rewrite the config file with
 * values the reader never touched.
 */
function field(key) {
  const r = rowOf(key);
  const wrap = el("div", "fld");
  const id = `set-${key}`;
  const lab = el("label", null, t(`settings.f.${key}`));
  lab.htmlFor = id;
  wrap.appendChild(lab);

  const input = el("input", "field");
  input.id = id;
  input.spellcheck = false;
  input.autocomplete = "off";
  const initial = asText(r?.value);
  if (r?.secret) {
    input.type = "password";
    input.value = "";
    input.placeholder = r.set ? initial : t("settings.f.api_key.unset");
  } else {
    input.type = "text";
    input.value = initial;
  }
  if (r?.locked) {
    input.readOnly = true;
    input.setAttribute("aria-describedby", `${id}-why`);
  }
  wrap.appendChild(input);

  const why = el("p", "hint");
  why.id = `${id}-why`;
  why.appendChild(document.createTextNode(t(`settings.h.${key}`)));
  if (r) {
    why.appendChild(document.createTextNode(" "));
    const src = pill(
      r.locked ? "warn" : r.source === "file" ? "ok" : "mute",
      t(`settings.src.${r.source}`),
    );
    why.appendChild(src);
    if (r.needs_restart) why.appendChild(pill("mute", t("settings.restart")));
  }
  wrap.appendChild(why);

  wrap.read = () => {
    if (!r || r.locked) return undefined;
    const v = input.value.trim();
    if (r.secret) return v === "" ? undefined : v;
    return v === initial ? undefined : v;
  };
  wrap.probe = () => input.value.trim();
  return wrap;
}

// -------------------------------------------------------------- model form

function modelForm() {
  const sec = el("section", "tint");
  sec.appendChild(el("h2", null, t("settings.model.title")));
  sec.appendChild(el("p", "lede", t("settings.model.lede")));

  const form = el("form", "grid2");
  const fields = new Map(MODEL_FIELDS.map((k) => [k, field(k)]));
  for (const f of fields.values()) form.appendChild(f);
  sec.appendChild(form);

  const say = el("p", "note");
  say.setAttribute("aria-live", "polite");
  const save = btn(t("settings.save"), "primary");
  save.type = "submit";
  const test = btn(t("settings.test"), "", () => void probe(fields, say));
  sec.appendChild(el("div", "row")).append(save, test, say);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    void write(fields, say, save);
  });
  return sec;
}

async function write(fields, say, save) {
  const values = {};
  for (const [key, f] of fields) {
    const v = f.read();
    if (v !== undefined) values[key] = v;
  }
  if (!Object.keys(values).length) {
    say.className = "note";
    say.textContent = t("settings.nochange");
    return;
  }
  save.disabled = true;
  say.className = "note";
  say.textContent = t("settings.saving");
  try {
    const r = await api.adminSettingsWrite(values);
    cfg = { path: r.path ?? cfg?.path, settings: r.settings };
    setup.invalidate();
    say.className = "note ok";
    say.textContent = r.restart_required?.length
      ? t("settings.saved.restart", { keys: r.restart_required.join(", ") })
      : t("settings.saved", { n: r.applied?.length ?? Object.keys(values).length });
    // Redraw so `source` flips from default to file and the mask updates.
    draw();
  } catch (e) {
    say.className = "note bad";
    say.textContent = e instanceof ApiError ? e.message : String(e);
  } finally {
    save.disabled = false;
  }
}

/**
 * Probe without saving.
 *
 * Chat and embed are reported separately because they fail separately, and
 * constantly: aggregated endpoints will happily serve a chat model and 404
 * every embedding request, and one combined verdict hides which half is dead.
 */
async function probe(fields, say) {
  say.className = "note";
  say.textContent = t("settings.testing");
  const patch = {};
  for (const [key, f] of fields) {
    const v = f.probe();
    if (v) patch[key] = v;
  }
  try {
    const r = await api.adminSettingsTest(patch);
    const line = (kind, res) =>
      res?.ok
        ? t("settings.probe.ok", { kind: t(`settings.probe.${kind}`), ms: res.ms ?? 0 })
        : t("settings.probe.bad", {
            kind: t(`settings.probe.${kind}`),
            why: res?.error ?? t("settings.probe.unknown"),
          });
    const bad = !r.chat?.ok || !r.embed?.ok;
    say.className = bad ? "note bad" : "note ok";
    say.textContent = `${line("chat", r.chat)} \u00b7 ${line("embed", r.embed)}`;
  } catch (e) {
    say.className = "note bad";
    say.textContent = e instanceof ApiError ? e.message : String(e);
  }
}

// ---------------------------------------------------------------- the rest

function otherGroups() {
  const out = [];
  for (const g of GROUPS) {
    const sec = el("section", "block");
    sec.appendChild(el("h2", null, t(g.key)));
    const form = el("form", "grid2");
    const fields = new Map(g.fields.map((k) => [k, field(k)]));
    for (const f of fields.values()) form.appendChild(f);
    sec.appendChild(form);
    const say = el("p", "note");
    say.setAttribute("aria-live", "polite");
    const save = btn(t("settings.save"), "");
    save.type = "submit";
    sec.appendChild(el("div", "row")).append(save, say);
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      void write(fields, say, save);
    });
    out.push(sec);
  }
  return out;
}

// -------------------------------------------------------------------- job

/** A stage's state, from the job document. */
function stageState(j, name) {
  if (!j || j.state === "idle") return "todo";
  if (j.stages?.some((s) => s.name === name)) return "done";
  if (j.current === name) return "now";
  return j.state === "running" ? "todo" : "skipped";
}

function jobSection() {
  const sec = el("section", "tint lex");
  sec.appendChild(el("h2", null, t("settings.job.title")));
  sec.appendChild(el("p", "lede", t("settings.job.lede")));

  const running = job?.state === "running";
  const bar = el("div", "stages");
  bar.setAttribute("role", "group");
  bar.setAttribute("aria-label", t("settings.job.title"));
  // Component 11, the system flow bar. The ordinal is not decoration here:
  // the seven stage names include `embed_content` and `embed_intents`, which
  // are the same two words in both languages, so the number is what tells a
  // reader where in the run they are.
  for (const [i, name] of STAGES.entries()) {
    const s = stageState(job, name);
    const seg = el("div", `stage ${s}`);
    seg.appendChild(el("i", "bignum", String(i + 1)));
    seg.appendChild(el("span", "nm", t(`stage.${name}`)));
    const got = job?.stages?.find((x) => x.name === name);
    seg.appendChild(el("span", "vl", got ? String(got.value) : s === "now" ? "\u2026" : ""));
    bar.appendChild(seg);
  }
  sec.appendChild(bar);

  const line = el("p", "note");
  line.setAttribute("aria-live", "polite");
  if (!job || job.state === "idle") line.textContent = t("settings.job.idle");
  else if (running) {
    line.textContent = t("settings.job.running", {
      pct: Math.round((job.progress ?? 0) * 100),
      stage: t(`stage.${job.current ?? STAGES[0]}`),
    });
  } else if (job.state === "done") line.textContent = t("settings.job.done", { s: job.elapsed ?? 0 });
  else if (job.state === "cancelled") line.textContent = t("settings.job.cancelled");
  else line.textContent = t("settings.job.failed", { why: job.error ?? "" });
  sec.appendChild(line);

  const run = btn(t("settings.job.run"), "primary", () => void start(false));
  run.disabled = running;
  const force = btn(t("settings.job.force"), "", () => void start(true));
  force.disabled = running;
  const stop = btn(t("settings.job.stop"), "", () => void cancel());
  stop.disabled = !running || Boolean(job?.cancel_requested);
  const row = el("div", "row");
  row.append(run, force, stop);
  if (job?.cancel_requested && running) row.appendChild(el("span", "dim", t("settings.job.stopping")));
  sec.appendChild(row);

  if (job?.log?.length) {
    const log = el("pre", "log");
    log.textContent = job.log.slice(-12).join("\n");
    sec.appendChild(log);
  }
  return sec;
}

async function start(force) {
  try {
    job = await api.adminIndex({ fetch: true, force });
    watch();
    draw();
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      await refreshJob();
      draw();
      return;
    }
    const into = el("div");
    ui.body.appendChild(into);
    failPanel(e, into);
  }
}

async function cancel() {
  try {
    const r = await api.adminCancel();
    if (r.job) job = r.job;
    draw();
  } catch {
    /* the next poll will say what actually happened */
  }
}

async function refreshJob() {
  try {
    job = await api.adminJob();
  } catch {
    job = null;
  }
}

/**
 * Poll only while something is running, and stop the moment it is not.
 *
 * The timer survives a route change on purpose. An index run started here and
 * watched from the search page is still the thing that decides whether the
 * search page has anything to show, so the poll that clears the stats cache
 * when it finishes has to outlive the view that started it. It redraws only
 * when this panel is the visible one.
 */
function watch() {
  if (poll) return;
  poll = setInterval(() => {
    void (async () => {
      await refreshJob();
      if (job?.state !== "running") {
        stopWatching();
        // The library changed under the rest of the app. Drop the caches so
        // the tab counts and the setup ticks are not describing the old one.
        S.stats = null;
        setup.invalidate();
      }
      if (ui && !$("#view-settings").hidden) draw();
    })();
  }, POLL_MS);
}

function stopWatching() {
  if (!poll) return;
  clearInterval(poll);
  poll = 0;
}

// ------------------------------------------------------------------ render

function draw() {
  if (!cfg) return;
  const where = card("where");
  where.appendChild(el("h2", null, t("settings.file.title")));
  where.appendChild(el("p", null, t("settings.file.body")));
  where.appendChild(el("pre", "cmd")).appendChild(el("code", null, cfg.path));
  ui.body.replaceChildren(modelForm(), jobSection(), ...otherGroups(), where);
}

export async function render() {
  const mine = ++generation;
  ui.body.replaceChildren(el("p", "dim", t("settings.loading")));
  const [c, j] = await Promise.allSettled([api.adminSettings(), api.adminJob()]);
  if (mine !== generation) return;
  if (c.status === "rejected") {
    failPanel(c.reason, ui.body);
    return;
  }
  cfg = c.value;
  job = j.status === "fulfilled" ? j.value : null;
  if (job?.state === "running") watch();
  draw();
}

/** Language switch. Same document, different words -- no requests. */
export function relabel() {
  if (!cfg) return render();
  draw();
}

export function mount() {
  ui = { body: $("#settings-body") };
}
