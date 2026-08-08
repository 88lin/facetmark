// Display formatting. Pure functions, no DOM -- unit tested in
// tests/web/format.test.mjs.

/**
 * Why a row is on screen, in words rather than in facet identifiers.
 *
 * The same four words the extension popup and the site's marker legend use. A
 * fifth vocabulary for the same four facets would be a fifth thing to keep in
 * sync, so unknown facets fall through to their raw name instead of being
 * invented here.
 */
export const FACET_KEYS = {
  content: "facet.content",
  intent: "facet.intent",
  lex_seg: "facet.lex_seg",
  lex_tri: "facet.lex_tri",
};

/** `took_ms` is a per-stage breakdown. `${took} ms` renders "[object Object] ms". */
export function totalMs(took) {
  if (!took) return 0;
  if (typeof took.total === "number") return Math.round(took.total);
  return Math.round(Object.values(took).reduce((a, b) => a + b, 0));
}

/** Thousands separators in the reader's locale. 1710 is harder to read than 1,710. */
export function count(n, lang) {
  return new Intl.NumberFormat(lang === "zh" ? "zh-CN" : "en-US").format(n ?? 0);
}

/**
 * When a page was bookmarked, coarsely.
 *
 * Coarse on purpose. `date_added` on an imported library is the browser's
 * timestamp, which for bookmarks migrated between profiles or machines is
 * frequently the migration date rather than the day the user saved the page.
 * Printing a precise date would dress that up as a fact; a month, or "3 years
 * ago", is about as much as the field can honestly support.
 *
 * @param {number|null|undefined} ts seconds since the epoch
 * @param {number} nowMs injected so the tests are not clock-dependent
 */
export function whenAdded(ts, lang, nowMs = Date.now()) {
  if (!ts) return "";
  const days = Math.floor((nowMs / 1000 - ts) / 86400);
  if (days < 0) return "";
  const rtf = new Intl.RelativeTimeFormat(lang === "zh" ? "zh-CN" : "en-US", {
    numeric: "auto",
  });
  if (days < 1) return rtf.format(0, "day");
  if (days < 30) return rtf.format(-days, "day");
  if (days < 365) return rtf.format(-Math.round(days / 30), "month");
  return rtf.format(-Math.round(days / 365), "year");
}

/**
 * A URL shortened to something a person can read in a list.
 *
 * Falls back to the raw string rather than throwing: the library holds
 * whatever the browser export held, including `javascript:` bookmarklets and
 * `place:` entries that `new URL()` parses in surprising ways.
 */
export function shortUrl(url) {
  try {
    const u = new URL(url);
    const tail = (u.pathname === "/" ? "" : u.pathname) + u.search;
    const host = u.host.replace(/^www\./, "");
    return tail.length > 48 ? host + tail.slice(0, 47) + "\u2026" : host + tail;
  } catch {
    return url ?? "";
  }
}

/**
 * A share of a whole, as a whole number of percent.
 *
 * Clamped at both ends. `with_body` can exceed `indexable` on a library that
 * was indexed before a privacy rule was tightened, and a progress bar drawn at
 * 104% is a rendering bug rather than a fact about the library.
 */
export function pct(n, total) {
  if (!total || total <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round(((n ?? 0) / total) * 100)));
}

/**
 * How long the server has been up, as at most two units.
 *
 * Returns pairs rather than a string because the units are translated and this
 * module is not. Seconds are only ever shown on their own: a server that has
 * been up for four hours and nine seconds has been up for four hours.
 *
 * @returns {Array<{n: number, unit: "d"|"h"|"m"|"s"}>}
 */
export function uptimeParts(seconds) {
  const total = Math.max(0, Math.floor(seconds ?? 0));
  const d = Math.floor(total / 86400);
  const h = Math.floor((total % 86400) / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (d) return h ? [{ n: d, unit: "d" }, { n: h, unit: "h" }] : [{ n: d, unit: "d" }];
  if (h) return m ? [{ n: h, unit: "h" }, { n: m, unit: "m" }] : [{ n: h, unit: "h" }];
  if (m) return [{ n: m, unit: "m" }];
  return [{ n: s, unit: "s" }];
}

/**
 * Fill `{name}` placeholders. Deliberately dumb: the strings file is ours, the
 * values are numbers and identifiers, and nothing here reaches innerHTML.
 */
export function interpolate(template, vars) {
  return String(template).replace(/\{(\w+)\}/g, (m, k) =>
    Object.hasOwn(vars ?? {}, k) ? String(vars[k]) : m,
  );
}
