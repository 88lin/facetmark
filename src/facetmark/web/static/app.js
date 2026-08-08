// The facetmark page: shell, router, language and theme.
//
// This file owns no view. It owns the frame around them -- which panel is
// visible, which language the static markup is in, where the token came from
// -- and the three hooks the views call back through (`S.open`, `S.go`,
// `S.redraw`). The views import `state.js`, never this file, so the module
// graph stays a tree: app.js -> views -> {api, dom, derive, format, state}.
//
// Everything that can be wrong in a way a person would not notice on screen --
// paging arithmetic, coverage denominators, date and number formatting --
// lives in paging.js, derive.js and format.js, which are pure and unit tested
// under tests/web/.

import { api, setToken } from "./api.js";
import * as ask from "./ask.js";
import * as detail from "./detail.js";
import { $, $$ } from "./dom.js";
import { applyTo, pickLang, translator } from "./i18n.js";
import * as library from "./library.js";
import * as search from "./search.js";
import * as sessions from "./sessions.js";
import { S, ensureStats } from "./state.js";
import * as system from "./system.js";

const TOKEN_KEY = "fm-token";
const LANG_KEY = "fm-lang";
const THEME_KEY = "fm-theme";

/**
 * The five views, in tab order.
 *
 * `wide` widens the content column from the reading measure to the dashboard
 * one. `scene-app.md` gives 820px for reading and 1200px for data-dense
 * screens; a table of counters at reading width is a column of orphaned
 * numbers.
 */
const VIEWS = {
  search: { panel: "#view-search", mod: search },
  ask: { panel: "#view-ask", mod: ask },
  library: { panel: "#view-library", mod: library, wide: true },
  sessions: { panel: "#view-sessions", mod: sessions },
  system: { panel: "#view-system", mod: system, wide: true },
};
const ORDER = Object.keys(VIEWS);

let ui = null;
let theme = "system";

function viewName() {
  const name = location.hash.replace(/^#\//, "");
  return ORDER.includes(name) ? name : "search";
}

// ------------------------------------------------------------------ chrome

/** The counts on the tabs. Quiet until `/stats` has actually answered. */
function badges() {
  const s = S.stats;
  const set = (node, value) => {
    if (value === undefined || value === null) return;
    node.textContent = new Intl.NumberFormat(S.lang === "zh" ? "zh-CN" : "en-US").format(value);
    node.hidden = false;
  };
  set(ui.nLibrary, s?.bookmarks);
  set(ui.nSessions, s?.sessions);
}

function route() {
  const name = viewName();
  const view = VIEWS[name];
  for (const [key, v] of Object.entries(VIEWS)) {
    $(v.panel).hidden = key !== name;
  }
  for (const b of $$(".tab")) {
    if (b.dataset.view === name) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  }
  ui.main.classList.toggle("wide", Boolean(view.wide));
  if (name === "search") search.focus();
  void Promise.resolve(view.mod.render()).then(badges);
}

/** Language state and the static markup only. Generated text is per view. */
function applyLang(next) {
  S.lang = next;
  S.say = translator(S.strings, next);
  document.documentElement.lang = next === "zh" ? "zh-CN" : "en";
  ui.lang.textContent = next === "zh" ? "EN" : "\u4e2d\u6587";
  applyTo(document, S.say);
  badges();
  try {
    localStorage.setItem(LANG_KEY, next);
  } catch {
    /* private mode: the choice then lasts for this tab only */
  }
}

function setTheme(next) {
  theme = next;
  document.documentElement.setAttribute(
    "data-theme",
    next === "system"
      ? matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : next,
  );
  ui.themeGlyph.textContent =
    next === "light" ? "\u2600" : next === "dark" ? "\u263e" : "\u25d1";
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    /* ignore */
  }
}

// ----------------------------------------------------------------- keyboard

function keys(e) {
  // The dialog runs its own trap. Two handlers both answering Escape would
  // close the dialog and clear the query behind it in the same keystroke.
  if (detail.isOpen()) return;
  const typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName ?? "");

  if (e.key === "/" && !typing) {
    e.preventDefault();
    S.go("search");
    search.focus();
    return;
  }
  if (viewName() !== "search") return;
  if (e.key === "Escape") {
    search.clearQuery();
    return;
  }
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    const links = search.rowLinks();
    if (!links.length) return;
    const at = links.indexOf(document.activeElement);
    // From the query box, ArrowDown enters the list; ArrowUp from the first
    // row goes back to it, so the keyboard path is a loop, not a trap.
    const next = e.key === "ArrowDown" ? at + 1 : at - 1;
    e.preventDefault();
    if (next < 0) search.focus();
    else links[Math.min(next, links.length - 1)].focus();
  }
}

// --------------------------------------------------------------------- boot

function wire() {
  for (const b of $$(".tab")) {
    b.addEventListener("click", () => S.go(b.dataset.view));
  }
  window.addEventListener("hashchange", route);

  ui.lang.addEventListener("click", () => {
    applyLang(S.lang === "zh" ? "en" : "zh");
    // A language switch is not a new question. Views that can relabel what is
    // already in memory do; the rest re-render from their cache.
    const mod = VIEWS[viewName()].mod;
    void (mod.relabel ?? mod.render)();
    detail.render();
  });

  ui.theme.addEventListener("click", () => {
    setTheme(theme === "system" ? "light" : theme === "light" ? "dark" : "system");
  });

  document.addEventListener("keydown", keys);
}

async function boot() {
  ui = {
    main: $("#main"),
    lang: $("#lang"),
    theme: $("#theme"),
    themeGlyph: $("#theme-glyph"),
    version: $("#version"),
    nLibrary: $("#n-library"),
    nSessions: $("#n-sessions"),
  };

  search.mount();
  ask.mount();
  library.mount();
  sessions.mount();
  system.mount();
  detail.mount();

  S.open = (id) => void detail.open(id);
  S.go = (name) => {
    const next = `#/${ORDER.includes(name) ? name : "search"}`;
    if (location.hash === next) route();
    else location.hash = next;
  };
  S.sitting = (id) => {
    S.go("sessions");
    void sessions.openSitting(id);
  };
  S.redraw = () => VIEWS[viewName()].mod.render();

  // Strings and pairing in parallel: neither needs the other and both are on
  // loopback, so the page is interactive in about one round trip.
  const [loaded, paired] = await Promise.allSettled([
    fetch("/app/static/strings.json").then((r) => r.json()),
    fetch("/app/boot", { cache: "no-store" }).then((r) => r.json()),
  ]);
  if (loaded.status === "fulfilled") S.strings = loaded.value;

  let token = "";
  if (paired.status === "fulfilled") {
    ui.version.textContent = `v${paired.value.version}`;
    // Not paired is not an error. The server declines to hand a token to a
    // page it cannot confirm was loaded from this machine, which is exactly
    // what it is meant to do -- see `_pairing_gate` in api.py. The stored
    // token is the fallback for that case.
    if (paired.value.paired) token = paired.value.token;
  }
  if (!token) {
    try {
      token = localStorage.getItem(TOKEN_KEY) ?? "";
    } catch {
      /* ignore */
    }
  }
  setToken(token);

  let storedLang = null;
  let storedTheme = null;
  try {
    storedLang = localStorage.getItem(LANG_KEY);
    storedTheme = localStorage.getItem(THEME_KEY);
  } catch {
    /* ignore */
  }
  applyLang(pickLang(storedLang, navigator.languages ?? [navigator.language]));
  setTheme(storedTheme ?? "system");

  wire();

  // `?q=` is how the extension hands a query over, and how a bookmarked search
  // survives a reload. It presets both boxes: which one it lands in is the
  // hash's decision, not the query string's.
  const preset = new URLSearchParams(location.search).get("q");
  if (preset) {
    search.preset(preset);
    ask.preset(preset);
  }

  route();
  // The tab counts are worth one background request. Nothing waits on it.
  void ensureStats(api).then(badges);
}

void boot();
