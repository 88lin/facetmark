// Shared, mutable UI state.
//
// Six view modules and one dialog all need the same few things: the current
// translator, the current language, and the cached /stats and /health
// documents. Threading those through every function signature would be noise,
// and an exported `let` cannot be reassigned from the importing side, so the
// mutable parts live on one object.
//
// `open` and `go` are set by app.js at boot. A view calling them directly
// instead of importing app.js is the difference between a hook and an import
// cycle: app.js imports every view, so no view may import app.js.

export const S = {
  lang: "en",
  strings: { en: {}, zh: {} },
  say: (k) => k,
  /** Cached `/stats`. Null until something asks for it. */
  stats: null,
  /** Cached `/health`. Null until something asks for it. */
  health: null,
  /** open(bookmarkId) -> shows the detail dialog */
  open: () => {},
  /** go(view) -> switches the visible view */
  go: () => {},
  /** sitting(sessionId) -> opens the sittings view on one sitting */
  sitting: () => {},
  /** redraw() -> re-renders whatever view is on screen */
  redraw: () => {},
};

/**
 * `/stats`, fetched once per pairing.
 *
 * Four views want it and none of them should pay for it twice. A failure
 * resolves to null rather than throwing: every caller has something useful to
 * draw without it, and an empty-library message is a better outcome than an
 * error page.
 */
export async function ensureStats(api) {
  if (S.stats) return S.stats;
  try {
    S.stats = await api.stats();
  } catch {
    S.stats = null;
  }
  return S.stats;
}

/** `/health`. Public, unauthenticated, and the only way to know the provider. */
export async function ensureHealth(api) {
  if (S.health) return S.health;
  try {
    S.health = await api.health();
  } catch {
    S.health = null;
  }
  return S.health;
}

/** The translator, read at call time so a language switch is picked up. */
export function t(key, vars) {
  return S.say(key, vars);
}

/**
 * A translation, or a fallback when the key is missing.
 *
 * `t` echoes an unknown key back, which is the right default on screen but the
 * wrong one here: without a fallback, echo the key rather than looking up
 * `undefined` and rendering the string "undefined".
 */
export function tOr(key, fallbackKey) {
  const s = t(key);
  if (s !== key) return s;
  return fallbackKey ? t(fallbackKey) : s;
}
