// The system view: `/health`, `/queue/stats`, `/link-health/*` and
// `/graveyard`.
//
// Four independent reads, drawn from four independently settled promises: one
// of them failing is a section with an error in it, not a blank page. `/health`
// is the only public route on this server, so the server card is the one thing
// here that still renders when the page has no token at all.
//
// `/link-health/check` is the single control on this page that reaches the
// public internet. It is behind a button, and the button is behind a
// confirmation that names how many outbound requests it will make, because a
// reader clicking around a local tool should never accidentally announce their
// bookmark list to a few dozen third-party servers.

import { api } from "./api.js";
import { HEALTH_TONE, healthBands } from "./derive.js";
import { $, block, btn, card, el, facts, link, numberCard, numbers, pill, skeleton, stackBar } from "./dom.js";
import { count, shortUrl, uptimeParts, whenAdded } from "./format.js";
import { failPanel } from "./panels.js";
import { S, t } from "./state.js";

/** The ceiling the confirmation names, and the limit actually sent. */
const CHECK_LIMIT = 50;
const GRAVE_LIMIT = 100;

let ui = null;
let generation = 0;
let last = null;
/** The node holding the link-health bar, so a check can refresh only that. */
let linksHost = null;

function dur(seconds) {
  return uptimeParts(seconds)
    .map((p) => `${p.n}${t(`unit.${p.unit}`)}`)
    .join(" ");
}

function section(titleKey, noteKey, settled, draw) {
  const sec = block(t(titleKey), noteKey ? t(noteKey) : undefined);
  if (settled.status === "rejected") {
    const into = el("div");
    sec.appendChild(into);
    failPanel(settled.reason, into);
    return sec;
  }
  draw(sec, settled.value);
  return sec;
}

// ------------------------------------------------------------------ server

function drawServer(sec, h) {
  const up = uptimeParts(h.uptime_s);
  sec.appendChild(
    numbers([
      numberCard(up.map((p) => `${p.n}${t(`unit.${p.unit}`)}`).join(" "), t("sys.uptime"), "ink"),
      numberCard(count(h.bookmarks, S.lang), t("stats.bookmarks")),
    ]),
  );
  const box = card();
  // A labelled table rather than a headline with badges beside it: the version
  // and the provider are two different facts and a single caption under both
  // of them can only describe one.
  //
  // "mock" is a deterministic stand-in, not a model. It is the difference
  // between a synthesis about your library and a fixture, so it reads as a
  // caution rather than as a neutral fact.
  box.appendChild(
    facts([
      { label: t("sys.version"), value: `facetmark v${h.version}` },
      {
        label: t("sys.provider"),
        value: h.provider === "mock" ? t("sys.provider.mock") : h.provider,
        tone: h.provider === "mock" ? "warn" : "ok",
      },
      {
        label: t("sys.state"),
        value: h.ok ? t("sys.ok") : t("sys.notok"),
        tone: h.ok ? "ok" : "bad",
      },
    ]),
  );
  sec.appendChild(box);
}

// ------------------------------------------------------------------- queue

function drawQueue(sec, q) {
  const box = card();
  const known = ["pending", "leased", "done", "failed"];
  const rows = known
    .filter((k) => q[k] !== undefined)
    .map((k) => ({ label: t(`queue.${k}`), value: count(q[k], S.lang), zero: !q[k] }));
  rows.push({ label: t("queue.waiting"), value: count(q.waiting, S.lang), zero: !q.waiting });
  box.appendChild(facts(rows));
  sec.appendChild(box);
}

// ------------------------------------------------------------------- links

function drawReport(rep, into) {
  const box = card();
  box.appendChild(
    facts([
      { label: t("sys.check.considered"), value: count(rep.considered, S.lang) },
      { label: t("sys.check.probed"), value: count(rep.probed, S.lang) },
      { label: t("sys.check.escalated"), value: count(rep.escalated, S.lang), zero: !rep.escalated },
      {
        label: t("sys.check.recovered"),
        value: count(rep.recovered_bodies, S.lang),
        zero: !rep.recovered_bodies,
      },
      {
        label: t("sys.check.gone"),
        value: count((rep.confirmed_gone ?? []).length, S.lang),
        zero: !(rep.confirmed_gone ?? []).length,
        tone: (rep.confirmed_gone ?? []).length ? "bad" : undefined,
      },
      {
        label: t("sys.check.errors"),
        value: count((rep.errors ?? []).length, S.lang),
        zero: !(rep.errors ?? []).length,
      },
    ]),
  );
  const marks = el("div", "marks");
  for (const [k, v] of Object.entries(rep.by_status ?? {})) {
    marks.appendChild(pill(HEALTH_TONE[k] ?? "mute", `${t(`health.${k}`)} ${count(v, S.lang)}`));
  }
  if (marks.childElementCount) box.appendChild(marks);
  into.replaceChildren(box);
}

async function runCheck(into) {
  into.replaceChildren(el("p", "status", t("sys.check.running")));
  try {
    drawReport(await api.linkHealthCheck(CHECK_LIMIT), into);
    // The bar above is now out of date. Redrawing the whole view would throw
    // away the report the reader just asked for, so only the bar is refreshed.
    void refreshLinks();
  } catch (e) {
    failPanel(e, into);
  }
}

function checkControl() {
  const wrap = el("div");
  const start = btn(t("sys.check"), "small", () => {
    const ask = el("div", "panel warn");
    ask.appendChild(el("h2", null, t("sys.check.confirm")));
    ask.appendChild(el("p", null, t("sys.check.confirm.body", { n: CHECK_LIMIT })));
    const row = el("div", "controls");
    row.appendChild(btn(t("sys.check.go"), "primary small", () => void runCheck(wrap)));
    row.appendChild(btn(t("sys.check.cancel"), "small", () => wrap.replaceChildren(start)));
    ask.appendChild(row);
    wrap.replaceChildren(ask);
  });
  wrap.appendChild(start);
  return wrap;
}

function linkBody(summary) {
  const { total, bands } = healthBands(summary);
  const box = card();
  // The bar carries the proportions and the legend carries the counts. A third
  // row spelling out one band again was the same number printed three times.
  box.appendChild(stackBar(bands));
  const legend = el("div", "legend");
  for (const [k, v] of Object.entries(summary ?? {})) {
    legend.appendChild(pill(HEALTH_TONE[k] ?? "mute", `${t(`health.${k}`)} ${count(v, S.lang)}`));
  }
  box.appendChild(legend);
  if (total) {
    const checked = total - (summary?.unchecked ?? 0);
    box.appendChild(
      el(
        "p",
        "dim note",
        t("stats.health.total", { n: count(checked, S.lang), total: count(total, S.lang) }),
      ),
    );
  }
  return box;
}

function drawLinks(sec, summary) {
  linksHost = el("div");
  linksHost.appendChild(linkBody(summary));
  sec.appendChild(linksHost);
  sec.appendChild(checkControl());
}

async function refreshLinks() {
  try {
    const summary = await api.linkHealth();
    if (last) last.links = { status: "fulfilled", value: summary };
    linksHost?.replaceChildren(linkBody(summary));
  } catch {
    /* the report is the answer the reader asked for; the bar can wait */
  }
}

// --------------------------------------------------------------- graveyard

/**
 * One dead link, with its verdict fetched fresh on request.
 *
 * The list already carries a health block, but it is a snapshot of the moment
 * the list was built. `GET /link-health/{id}` is a read of the current row, so
 * a check run in another tab -- or the one this page just ran -- shows up here
 * without a reload.
 */
function graveLine(r) {
  const wrap = el("div", "line");
  const grow = el("div", "grow");
  grow.append(link(r.url, "t", r.title || shortUrl(r.url)), el("div", "w", shortUrl(r.url)));
  wrap.appendChild(grow);
  const status = r.health?.status;
  if (status) wrap.appendChild(pill(HEALTH_TONE[status] ?? "mute", t(`health.${status}`)));

  const detail = el("div");
  const why = btn(t("sys.grave.detail"), "small", async () => {
    why.disabled = true;
    try {
      const st = await api.linkHealthOf(r.bookmark_id);
      detail.replaceChildren(
        facts([
          { label: t("sys.grave.status"), value: t(`health.${st.status}`), tone: "bad" },
          { label: t("sys.grave.confidence"), value: String(st.confidence ?? "") },
          { label: t("sys.grave.http"), value: st.http_status ? String(st.http_status) : "" },
          { label: t("sys.grave.checked"), value: whenAdded(st.checked_at, S.lang) },
          {
            label: t("sys.grave.failures"),
            value: count(st.consecutive_failures, S.lang),
            zero: !st.consecutive_failures,
          },
          { label: t("sys.grave.next"), value: whenAdded(st.next_check_after, S.lang) },
        ]),
      );
      if (st.archive_url) {
        detail.appendChild(link(st.archive_url, "surl", t("sys.grave.archive")));
      }
    } catch (e) {
      failPanel(e, detail);
    } finally {
      why.disabled = false;
    }
  });
  wrap.appendChild(why);

  const box = el("div");
  box.append(wrap, detail);
  return box;
}

function drawGrave(sec, list) {
  const box = card();
  if (!list.length) {
    box.appendChild(el("p", "dim", t("sys.grave.none")));
  } else {
    for (const r of list) box.appendChild(graveLine(r));
  }
  sec.appendChild(box);
}

// ------------------------------------------------------------------- shell

export async function render() {
  const mine = ++generation;
  ui.sys.replaceChildren(skeleton(4));
  const [h, q, links, grave] = await Promise.allSettled([
    api.health(),
    api.queueStats(),
    api.linkHealth(),
    api.graveyard(GRAVE_LIMIT),
  ]);
  if (mine !== generation) return;
  if (h.status === "fulfilled") S.health = h.value;
  last = { h, q, links, grave };
  ui.sys.replaceChildren(
    section("sys.server", null, h, drawServer),
    section("sys.queue", "sys.queue.why", q, drawQueue),
    section("sys.links", "sys.links.why", links, drawLinks),
    section("sys.grave", "sys.grave.why", grave, drawGrave),
  );
}

/** Redraw in the current language, without four more requests. */
export function relabel() {
  if (!last) return render();
  ui.sys.replaceChildren(
    section("sys.server", null, last.h, drawServer),
    section("sys.queue", "sys.queue.why", last.q, drawQueue),
    section("sys.links", "sys.links.why", last.links, drawLinks),
    section("sys.grave", "sys.grave.why", last.grave, drawGrave),
  );
}

export function mount() {
  ui = { sys: $("#sys") };
}
