// The library dashboard: `/stats`.
//
// The old version of this view printed every counter the endpoint returns as a
// definition list, which is accurate and tells a reader nothing: 964 next to
// the word "enriched" is only meaningful against the 1,197 pages that could
// have been enriched. So every number that is a share of something is drawn as
// a share of that thing, with the denominator that makes it true chosen in
// derive.js and unit tested there.
//
// Nothing on this page is an evaluation. Counts of what is indexed are facts
// about this database; they say nothing about whether retrieval is any good.

import { api } from "./api.js";
import { HEALTH_TONE, coverageRows, edgeRows, healthBands, queueBands } from "./derive.js";
import { $, barRow, block, card, el, facts, fbadge, numberCard, numbers, pill, skeleton, stackBar } from "./dom.js";
import { FACET_KEYS, FACET_ORDER, FACET_TONE, count, pct } from "./format.js";
import { failPanel } from "./panels.js";
import { S, t } from "./state.js";
let ui = null;
let generation = 0;

/** `count / total · 42%`. Digits and punctuation only, so it needs no words. */
function reading(n, total) {
  return `${count(n, S.lang)} / ${count(total, S.lang)} \u00b7 ${pct(n, total)}%`;
}

function factsFrom(map, prefix, extra = []) {
  const rows = Object.entries(map ?? {}).map(([k, v]) => ({
    label: t(`${prefix}.${k}`),
    value: count(v, S.lang),
    zero: !v,
  }));
  return facts([...rows, ...extra]);
}

// -------------------------------------------------------------------- parts

/**
 * The save-activity timeline: the last week as columns, older months as pills.
 *
 * Ported from hister's history view, on the one column a bookmark library
 * actually has: `date_added`. Every bucket is a button whose click runs a
 * query-language search (`added:2026-08-03`, `added:2026-04`) -- the timeline
 * is a browser over the same syntax the search box accepts, not a separate
 * feature with its own hidden state.
 */
function timelineStrip(tl) {
  const sec = block(t("tl.title"), t("tl.lede"));
  const box = card();
  const days = el("div", "tl-days");
  days.setAttribute("role", "group");
  days.setAttribute("aria-label", t("tl.days"));
  const max = Math.max(1, ...tl.days.map((d) => d.count));
  for (const d of tl.days) {
    const day = d.key.slice(4); // `day:2026-08-03` -> `2026-08-03`
    const col = el("button", "tl-day");
    col.type = "button";
    // A day you saved nothing on is still a column -- seven bars with a gap in
    // them is the shape of the week, and dropping the empty ones would redraw
    // the axis every day. It is not a *button*, though: it would tab-stop and
    // then run a search that is guaranteed to return nothing, which on a quiet
    // week is most of the strip.
    col.disabled = !d.count;
    col.style.setProperty("--h", `${Math.round((d.count / max) * 100)}%`);
    col.setAttribute("aria-label", `${day} \u00b7 ${count(d.count, S.lang)}`);
    col.title = `${day} \u00b7 ${count(d.count, S.lang)}`;
    col.appendChild(el("span", "n", d.count || ""));
    col.addEventListener("click", () => S.search(`added:${day} sort:date`));
    days.appendChild(col);
  }
  box.appendChild(days);

  // Months are clickable: each one is one `added:` token, so the timeline
  // and the search box are the same language.
  const months = el("div", "tl-months");
  for (const m of tl.months ?? []) {
    const key = m.key.slice(6); // `month:2026-04` -> `2026-04`
    const b = el("button", "pill act");
    b.type = "button";
    b.textContent = `${key} \u00b7 ${count(m.count, S.lang)}`;
    b.addEventListener("click", () => S.search(`added:${key}`));
    months.appendChild(b);
  }
  if (tl.older) {
    months.appendChild(el("span", "tl-old", t("tl.older", { n: count(tl.older, S.lang) })));
  }
  box.appendChild(months);
  sec.appendChild(box);
  return sec;
}

function topNumbers(s) {
  return numbers([
    numberCard(count(s.bookmarks, S.lang), t("stats.bookmarks"), "ink"),
    numberCard(count(s.indexable, S.lang), t("stats.indexable")),
    numberCard(count(s.enriched, S.lang), t("stats.enriched"), "gold"),
    numberCard(count(s.sessions, S.lang), t("stats.sessions"), "edge"),
  ]);
}

/**
 * What the four paths are, in one place, once.
 *
 * The result rows show a badge per path but a badge has room for two words.
 * This is the only surface in the app with room for the sentence, so it lives
 * here rather than as a tooltip nobody hovers or a legend under every search.
 */
function facetLegend() {
  const sec = block(t("stats.group.facets"), t("stats.note.facets"));
  const box = el("div", "tint content facetgrid");
  for (const f of FACET_ORDER) {
    const row = el("div", "fitem");
    row.appendChild(fbadge(FACET_TONE[f], t(FACET_KEYS[f])));
    row.appendChild(el("p", null, t(`${FACET_KEYS[f]}.why`)));
    box.appendChild(row);
  }
  sec.appendChild(box);
  return sec;
}

function coverage(s) {
  const rows = coverageRows(s);
  const text = rows.filter((r) => !r.vec);
  const vecs = rows.filter((r) => r.vec);

  const one = block(t("stats.group.text"), t("stats.note.text"));
  const boxA = card();
  const barsA = el("div", "bars");
  for (const r of text) barsA.appendChild(barRow(t(r.key), pct(r.n, r.total), reading(r.n, r.total)));
  boxA.appendChild(barsA);
  boxA.appendChild(
    facts([{ label: t("stats.intent_kept"), value: count(s.intent_kept, S.lang), zero: !s.intent_kept }]),
  );
  one.appendChild(boxA);

  const two = block(t("stats.group.vectors"), t("stats.note.vectors"));
  const boxB = card();
  const barsB = el("div", "bars");
  for (const r of vecs) {
    barsB.appendChild(barRow(t(r.key), pct(r.n, r.total), reading(r.n, r.total), r.gold));
  }
  boxB.appendChild(barsB);
  boxB.appendChild(
    facts([
      {
        label: t("stats.content_vectors_stale"),
        value: count(s.content_vectors_stale, S.lang),
        zero: !s.content_vectors_stale,
        tone: s.content_vectors_stale ? "warn" : undefined,
      },
    ]),
  );
  two.appendChild(boxB);
  return [one, two];
}

function health(s) {
  const { total, bands } = healthBands(s.health);
  const sec = block(t("stats.group.health"), t("stats.note.health"));
  const box = card();
  box.appendChild(stackBar(bands));
  const legend = el("div", "legend");
  // Every verdict the server reported, largest first -- `summary()` already
  // sorts them, and `unchecked` is in there as a real category rather than as
  // the leftover space in the bar.
  for (const [k, v] of Object.entries(s.health ?? {})) {
    legend.appendChild(pill(HEALTH_TONE[k] ?? "mute", `${t(`health.${k}`)} ${count(v, S.lang)}`));
  }
  box.appendChild(legend);
  // Never checked is not a verdict, so it cannot be counted as one. The note
  // right above this says exactly that, and a total that swept the unchecked
  // in with the rest would contradict it.
  if (total) {
    const checked = total - (s.health?.unchecked ?? 0);
    box.appendChild(
      el(
        "p",
        "dim note",
        t("stats.health.total", { n: count(checked, S.lang), total: count(total, S.lang) }),
      ),
    );
  }
  sec.appendChild(box);
  return sec;
}

function graph(s) {
  const sec = block(t("stats.group.graph"), t("stats.note.graph"));
  const rows = edgeRows(s.edges_by_kind);
  const box = card();
  const bars = el("div", "bars");
  for (const r of rows) {
    // The weight is what fusion multiplies this edge kind by. It is a constant
    // in `edges.py`, not something measured here.
    const tail = r.weight === undefined ? "" : ` \u00b7 \u00d7${r.weight}`;
    bars.appendChild(
      barRow(t(`edge.${r.kind}`), pct(r.n, s.edges), `${count(r.n, S.lang)}${tail}`),
    );
  }
  box.appendChild(bars);
  box.appendChild(
    facts([
      { label: t("stats.edges"), value: count(s.edges, S.lang) },
      { label: t("stats.sessions"), value: count(s.sessions, S.lang) },
    ]),
  );
  sec.appendChild(box);
  return sec;
}

function queue(s) {
  const sec = block(t("stats.group.queue"), t("stats.note.queue"));
  const box = card();
  // The bar first: how drained the queue is, at a glance. The fact rows under
  // it carry the exact counts, so the two never print the same number twice.
  const { total, bands } = queueBands(s.queue);
  if (total) box.appendChild(stackBar(bands));
  box.appendChild(
    factsFrom(s.queue, "queue", [
      { label: t("queue.waiting"), value: count(s.queue_waiting, S.lang), zero: !s.queue_waiting },
    ]),
  );
  sec.appendChild(box);
  return sec;
}

function cold(s) {
  const c = s.cold_layer ?? {};
  const sec = block(t("stats.group.cold"), t("stats.note.cold"));
  const grid = el("div", "grid duo");
  const left = card();
  left.appendChild(
    facts([
      { label: t("cold.cold"), value: count(c.cold, S.lang), zero: !c.cold },
      { label: t("cold.servable_cold"), value: count(c.servable_cold, S.lang), zero: !c.servable_cold },
      {
        label: t("cold.unservable_cold"),
        value: count(c.unservable_cold, S.lang),
        zero: !c.unservable_cold,
      },
    ]),
  );
  const right = card();
  right.appendChild(
    facts([
      { label: t("cold.never_opened"), value: count(c.never_opened, S.lang), zero: !c.never_opened },
      {
        label: t("cold.older_than_cutoff"),
        value: count(c.older_than_cutoff, S.lang),
        zero: !c.older_than_cutoff,
      },
      {
        label: t("cold.old_and_never_opened"),
        value: count(c.old_and_never_opened, S.lang),
        zero: !c.old_and_never_opened,
      },
      {
        label: t("cold.health_unchecked"),
        value: count(c.health_unchecked, S.lang),
        zero: !c.health_unchecked,
      },
    ]),
  );
  grid.append(left, right);
  sec.appendChild(grid);
  return sec;
}

function shape(s) {
  const sec = block(t("stats.group.library"), t("stats.note.library"));
  const box = card();
  box.appendChild(
    facts([
      { label: t("stats.bookmarks"), value: count(s.bookmarks, S.lang) },
      { label: t("stats.indexable"), value: count(s.indexable, S.lang) },
      {
        label: t("stats.privacy_skipped"),
        value: count(s.privacy_skipped, S.lang),
        zero: !s.privacy_skipped,
      },
      { label: t("stats.domains"), value: count(s.domains, S.lang) },
    ]),
  );
  sec.appendChild(box);
  return sec;
}

// ------------------------------------------------------------------- shell

export async function render() {
  const mine = ++generation;
  ui.stats.replaceChildren(el("p", "status", t("stats.loading")), skeleton(3));
  let s;
  try {
    s = await api.stats();
  } catch (e) {
    if (mine === generation) failPanel(e, ui.stats);
    return;
  }
  if (mine !== generation) return;
  S.stats = s;
  // The timeline is a second document fetched in parallel; a failure or an
  // empty library leaves the dashboard exactly as it was, minus one block.
  let tl = null;
  try {
    tl = await api.timeline();
  } catch {
    tl = null;
  }
  if (mine !== generation) return;
  // Two columns from here down, so the page stops being one tall ribbon of
  // identical white cards. The KPI row and the legend stay full width because
  // both are read before anything else on the page.
  const cols = el("div", "cols2");
  cols.append(...coverage(s), health(s), graph(s), queue(s), cold(s), shape(s));
  ui.stats.replaceChildren(
    topNumbers(s),
    facetLegend(),
    ...(tl && s.bookmarks ? [timelineStrip(tl)] : []),
    cols,
  );
}

export function mount() {
  ui = { stats: $("#stats"), refresh: $("#lib-refresh") };
  // A manual refresh, because the dashboard is a snapshot and the queue moves.
  // Clearing the cache is what makes the re-render a real refetch rather than
  // a redraw of the numbers already on screen.
  ui.refresh?.addEventListener("click", () => {
    S.stats = null;
    void render();
  });
}
