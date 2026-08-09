// Paging arithmetic for the result list. Pure functions, no DOM, no fetch --
// which is the point: this is the part that has to be right, so it is the part
// that is unit tested (tests/web/paging.test.mjs) instead of being clicked at.
//
// This mirrors `extension/src/api.ts`. The two clients page the same server the
// same way, and the rules below are not obvious enough to be re-derived
// independently twice.

/** @typedef {{query: string, seen: number, depth: number, total: number, more: boolean, capped: boolean}} Cursor */

/** @returns {Cursor} */
export function startCursor(query) {
  return { query, seen: 0, depth: 0, total: 0, more: false, capped: false };
}

/**
 * Fold one server response into the cursor.
 *
 * `seen` is `offset + hits.length`, never `seen + hits.length`. The search box
 * renders twice per query -- the lexical first paint and then the full
 * pipeline, both at offset 0 -- and adding lengths would count page one twice
 * and then skip a page's worth of results. It would also strand the cursor
 * above the row count whenever the second ranking returns fewer rows than the
 * first, which is common when the pipeline abstains on a facet.
 *
 * `depth` is sticky. The server reports the depth it actually ranked at, and
 * every later page has to be asked for at that same depth: with more than one
 * facet in play, RRF is not order-stable as the pool deepens, so re-deriving
 * the depth on page two produces a ranking that disagrees with page one about
 * what page one was.
 *
 * @param {Cursor} cur
 * @returns {Cursor}
 */
export function advance(cur, r) {
  return {
    query: cur.query,
    seen: (r.offset ?? 0) + (r.hits?.length ?? 0),
    depth: r.depth || cur.depth,
    total: r.total ?? 0,
    more: Boolean(r.has_more),
    capped: Boolean(r.depth_capped),
  };
}

/**
 * Arguments for the next page, or null when there is nothing left to ask for.
 * @param {Cursor} cur
 * @returns {{offset: number, limit: number, depth: number} | null}
 */
export function nextRequest(cur, size) {
  if (!cur.more || !cur.query) return null;
  return { offset: cur.seen, limit: size, depth: cur.depth };
}

/**
 * Append a page to the rows already on screen, dropping anything already
 * shown.
 *
 * Deduplication is not paranoia. `has_more` is an upper bound in a multi-facet
 * configuration, and a library that changes between two requests -- the
 * fetcher finishing a page, the extension saving a tab -- can shift the window
 * under the reader. A repeated row is the visible symptom; two rows with the
 * same key is also a rendering bug in any list that keys by id.
 */
export function mergePage(rows, incoming) {
  const known = new Set(rows.map((h) => h.bookmark_id));
  return rows.concat((incoming ?? []).filter((h) => !known.has(h.bookmark_id)));
}

/**
 * The counter above the list, as message key plus interpolation values. The
 * caller turns it into words, because the words are translated and this module
 * is not.
 *
 * Never states `total` as a total when the server called it a floor: at the
 * depth ceiling the pool was truncated, so `total` is a count of what fusion
 * considered, which is a lower bound on what the library holds.
 *
 * @returns {{key: string, vars: Record<string, number>}}
 */
export function pageLabel(cur) {
  if (!cur.seen) return { key: "results.none", vars: {} };
  // Always 1: the list accumulates from offset 0 rather than replacing itself
  // page by page, so the reader is looking at the whole window, not the last
  // slice of it.
  const from = 1;
  if (cur.more) {
    return {
      key: cur.capped ? "results.window_capped" : "results.window",
      vars: { from, to: cur.seen, total: cur.total },
    };
  }
  return { key: "results.all", vars: { n: cur.seen } };
}
