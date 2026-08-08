// The arithmetic behind the dashboards and the detail dialog.
//
// Pure: no DOM, no fetch, no translation. Everything here can be wrong in a way
// nobody would notice on screen -- a progress bar drawn against the wrong
// denominator, a stacked bar whose segments do not sum to the total, a fact row
// that quietly drops a zero -- so it is separated out and unit tested in
// tests/web/derive.test.mjs, the same arrangement paging.js and format.js use.
//
// Translation keys are returned, never translated strings. The caller owns the
// language.

/**
 * The retrieval configurations this page offers.
 *
 * Named by mechanism, because that is the only thing about them that is a fact.
 * `pipeline.py` defines A as the content vector alone and B as the content
 * vector *plus* the two lexical facets -- B is not a lexical-only rung, and
 * there is no lexical-only rung in the ladder at all. `full` is what /search
 * uses when the caller says nothing.
 *
 * The remaining named configurations (D, E, the `_nolex` variants, `fused`)
 * exist server-side and still work if you call the API directly. They are not
 * offered here because D and E add a context pass, a graph walk and a reranker,
 * and a search box that can silently cost a model call per keystroke is a
 * different product.
 */
export const RUNGS = [
  { id: "full", key: "mode.full", why: "mode.full.why", fallback: true },
  { id: "A", key: "mode.A", why: "mode.A.why" },
  { id: "B", key: "mode.B", why: "mode.B.why" },
  { id: "C", key: "mode.C", why: "mode.C.why" },
];

/** `edges.WEIGHTS`, mirrored so the graph card can say what an edge is worth. */
export const EDGE_WEIGHTS = {
  session: 1.0,
  semantic: 0.8,
  supersession: 0.7,
  anchor_sibling: 0.5,
  same_domain: 0.15,
};

/** Which pill colour a link verdict gets. `unchecked` is absence, not a fault. */
export const HEALTH_TONE = {
  alive: "ok",
  drifted: "warn",
  restricted: "warn",
  soft_gone: "bad",
  gone: "bad",
  unreachable: "mute",
  unknown: "mute",
  unchecked: "mute",
};

/** The stacked bar, in drawing order. `unchecked` is the unfilled remainder. */
const BANDS = [
  { cls: "ok", keys: ["alive"] },
  { cls: "warn", keys: ["drifted", "restricted"] },
  { cls: "bad", keys: ["gone", "soft_gone"] },
  { cls: "mute", keys: ["unreachable", "unknown"] },
];

/**
 * Link health as one bar.
 *
 * The denominator is the sum of every verdict including `unchecked`, so the
 * bar answers "how much of the library do we know about" rather than "how much
 * of what we checked was alive" -- on a fresh library those two differ by two
 * orders of magnitude, and the second one flatters the number.
 *
 * @returns {{total: number, bands: Array<{cls: string, n: number, pct: number}>}}
 */
export function healthBands(health) {
  const h = health ?? {};
  const total = Object.values(h).reduce((a, b) => a + (Number(b) || 0), 0);
  const bands = BANDS.map(({ cls, keys }) => {
    const n = keys.reduce((a, k) => a + (Number(h[k]) || 0), 0);
    return { cls, n, pct: total ? (n / total) * 100 : 0 };
  }).filter((b) => b.n > 0);
  return { total, bands };
}

/**
 * The coverage bars, each with the denominator that makes it true.
 *
 * `indexable`, not `bookmarks`: pages skipped for privacy are never fetched or
 * embedded, so counting them in the denominator would report a permanent
 * shortfall as if it were work outstanding. Intent vectors are counted against
 * the intent queries that were kept, because that is the only population they
 * can exist for.
 */
export function coverageRows(stats) {
  const s = stats ?? {};
  const base = s.indexable || 0;
  const vec = Array.isArray(s.vectors) ? s.vectors : [0, 0];
  const kept = s.intent_kept || 0;
  return [
    { key: "stats.with_body", n: s.with_body ?? 0, total: base },
    { key: "stats.enriched", n: s.enriched ?? 0, total: base },
    { key: "stats.vec_content", n: vec[0] ?? 0, total: base, vec: true },
    { key: "stats.vec_intent", n: vec[1] ?? 0, total: kept || base, gold: true, vec: true },
  ];
}

/** Edge counts, biggest first, each carrying its fusion weight. */
export function edgeRows(byKind) {
  return Object.entries(byKind ?? {})
    .map(([kind, n]) => ({ kind, n: Number(n) || 0, weight: EDGE_WEIGHTS[kind] }))
    .sort((a, b) => b.n - a.n || a.kind.localeCompare(b.kind));
}

/** Neighbours grouped by edge kind, heaviest kind first. */
export function groupByKind(rows) {
  const out = new Map();
  for (const r of rows ?? []) {
    const k = r.kind || "unknown";
    if (!out.has(k)) out.set(k, []);
    out.get(k).push(r);
  }
  return [...out.entries()].sort(
    (a, b) => (EDGE_WEIGHTS[b[0]] ?? 0) - (EDGE_WEIGHTS[a[0]] ?? 0) || a[0].localeCompare(b[0]),
  );
}

/**
 * The fact grid in the detail dialog.
 *
 * Field names follow the record, not the wish list in the issue that asked for
 * this: there is no `word_count` and no `language` on a bookmark. There is
 * `indexed.chars`, which is characters of extracted text, and `indexed.lang`,
 * which is what the extractor detected. Renaming them on screen would invent
 * two fields that nothing measures.
 *
 * Zeros survive the filter. "Opened 0 times" is the single most informative
 * value that field takes, and it is the input to the cold layer.
 *
 * @returns {Array<{key: string, value: any, kind: "text"|"num"|"date", tone?: string}>}
 */
export function factRows(rec) {
  const r = rec ?? {};
  const ix = r.indexed ?? {};
  const rows = [
    { key: "detail.folder", value: r.folder, kind: "text" },
    { key: "detail.depth", value: r.folder_depth, kind: "num" },
    { key: "detail.added", value: r.date_added, kind: "date" },
    { key: "detail.opens", value: r.open_count ?? 0, kind: "num" },
    { key: "detail.last_open", value: r.last_opened_at, kind: "date" },
    { key: "detail.utility", value: r.utility, kind: "text" },
    { key: "detail.kind", value: r.content_type, kind: "text" },
    { key: "detail.lang", value: ix.lang, kind: "text" },
    { key: "detail.chars", value: ix.chars ?? 0, kind: "num" },
    { key: "detail.extractor", value: ix.extractor, kind: "text" },
    { key: "detail.channel", value: ix.channel, kind: "text" },
    { key: "detail.http", value: ix.http_status, kind: "num" },
    { key: "detail.fetched", value: ix.fetched_at, kind: "date" },
    { key: "detail.enriched_by", value: ix.enriched_by, kind: "text" },
    { key: "detail.error", value: ix.error, kind: "text", tone: "bad" },
  ];
  return rows.filter((x) => x.value !== "" && x.value !== null && x.value !== undefined);
}

/**
 * Sources by their citation number.
 *
 * `/synthesize` numbers sources from 1 and the claims cite those numbers, so a
 * claim citing [3] must find source 3 even if the list came back out of order
 * or with a gap. Indexing the array positionally would silently mis-attribute.
 */
export function sourceIndex(sources) {
  const m = new Map();
  for (const src of sources ?? []) m.set(Number(src.n), src);
  return m;
}
