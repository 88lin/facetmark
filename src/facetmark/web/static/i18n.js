// Two languages, one JSON file, no build step.
//
// The strings live in `strings.json` rather than in JS so that Python can read
// them: `tests/test_web.py` asserts the two language maps have identical key
// sets, and that every key the HTML and the JS ask for exists in both. A
// missing translation is otherwise invisible until a reader hits that exact
// screen in that exact language.

import { interpolate } from "./format.js";

export const LANGS = ["en", "zh"];

/** `localStorage`, else the browser's preference, else English. */
export function pickLang(stored, navigatorLangs) {
  if (LANGS.includes(stored)) return stored;
  for (const l of navigatorLangs ?? []) {
    if (String(l).toLowerCase().startsWith("zh")) return "zh";
    if (String(l).toLowerCase().startsWith("en")) return "en";
  }
  return "en";
}

/**
 * @param {{en: Record<string,string>, zh: Record<string,string>}} strings
 * @returns {(key: string, vars?: Record<string, string|number>) => string}
 */
export function translator(strings, lang) {
  const table = strings[lang] ?? strings.en ?? {};
  const fallback = strings.en ?? {};
  return (key, vars) => {
    // Falling back to the key itself rather than to an empty string: a screen
    // reading `results.window` is a bug report, a blank one is a mystery.
    const raw = table[key] ?? fallback[key] ?? key;
    return vars ? interpolate(raw, vars) : raw;
  };
}

/**
 * Translate the static markup in place.
 *
 * `data-i18n` sets text content. `data-i18n-attr="placeholder:key, title:key"`
 * sets attributes -- placeholders, tooltips and `aria-label`s are text a
 * reader sees too, and leaving them English was the first thing that went
 * wrong when this page was tried in Chinese.
 */
export function applyTo(root, t) {
  for (const el of root.querySelectorAll("[data-i18n]")) {
    el.textContent = t(el.dataset.i18n);
  }
  for (const el of root.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of el.dataset.i18nAttr.split(",")) {
      const [attr, key] = pair.split(":").map((s) => s.trim());
      if (attr && key) el.setAttribute(attr, t(key));
    }
  }
}
