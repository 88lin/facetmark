// Language choice and lookup. `node --test tests/web/*.test.mjs`

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { LANGS, pickLang, translator, applyTo } from "../../src/facetmark/web/static/i18n.js";

const STRINGS = JSON.parse(
  readFileSync(
    fileURLToPath(new URL("../../src/facetmark/web/static/strings.json", import.meta.url)),
    "utf8",
  ),
);

describe("pickLang", () => {
  test("a stored choice wins over the browser", () => {
    assert.equal(pickLang("en", ["zh-CN"]), "en");
    assert.equal(pickLang("zh", ["en-US"]), "zh");
  });

  test("a stored value that is not a language we have is ignored", () => {
    // `localStorage` is shared with anything else on 127.0.0.1 and outlives
    // any rename of ours.
    assert.equal(pickLang("de", ["zh-TW"]), "zh");
    assert.equal(pickLang(null, ["en-GB"]), "en");
  });

  test("reads regional tags", () => {
    for (const tag of ["zh", "zh-CN", "zh-TW", "zh-Hans", "ZH-hant"]) {
      assert.equal(pickLang(null, [tag]), "zh", tag);
    }
    for (const tag of ["en", "en-US", "en-AU"]) {
      assert.equal(pickLang(null, [tag]), "en", tag);
    }
  });

  test("takes the reader's first supported preference, not the first entry", () => {
    assert.equal(pickLang(null, ["fr-FR", "zh-CN", "en-US"]), "zh");
  });

  test("english when there is nothing to go on", () => {
    assert.equal(pickLang(null, []), "en");
    assert.equal(pickLang(undefined, undefined), "en");
    assert.equal(pickLang(null, ["fr", "de"]), "en");
  });

  test("LANGS is what the switch offers", () => {
    assert.deepEqual(LANGS, ["en", "zh"]);
    assert.deepEqual(Object.keys(STRINGS).sort(), [...LANGS].sort());
  });
});

describe("translator", () => {
  const s = { en: { hi: "Hello", only: "English only", n: "{n} results" }, zh: { hi: "你好" } };

  test("looks up in the chosen language", () => {
    assert.equal(translator(s, "zh")("hi"), "你好");
    assert.equal(translator(s, "en")("hi"), "Hello");
  });

  test("falls back to english for a key that language is missing", () => {
    assert.equal(translator(s, "zh")("only"), "English only");
  });

  test("falls back to the key itself, never to blank", () => {
    // A screen reading `results.window` is a bug report. A blank one is a
    // mystery, and it is the one a reader will not report.
    assert.equal(translator(s, "en")("results.nope"), "results.nope");
    assert.equal(translator(s, "zh")("results.nope"), "results.nope");
  });

  test("interpolates only when asked", () => {
    assert.equal(translator(s, "en")("n", { n: 3 }), "3 results");
    assert.equal(translator(s, "en")("n"), "{n} results");
  });

  test("an unknown language reads as english rather than as keys", () => {
    assert.equal(translator(s, "de")("hi"), "Hello");
    assert.equal(translator({}, "en")("hi"), "hi");
  });

  test("works against the real strings file", () => {
    for (const lang of LANGS) {
      const t = translator(STRINGS, lang);
      assert.equal(t("nav.search"), STRINGS[lang]["nav.search"]);
      assert.ok(t("nav.search").length > 0);
    }
  });
});

describe("applyTo", () => {
  // A DOM stub rather than jsdom: the function touches five members, and a
  // dependency added to a no-build page for one test would be the wrong trade.
  const el = (dataset) => ({
    dataset,
    textContent: null,
    attrs: {},
    setAttribute(k, v) {
      this.attrs[k] = v;
    },
  });
  const root = (byText, byAttr) => ({
    querySelectorAll: (sel) => (sel === "[data-i18n]" ? byText : byAttr),
  });

  test("sets text content", () => {
    const a = el({ i18n: "hi" });
    applyTo(root([a], []), (k) => k.toUpperCase());
    assert.equal(a.textContent, "HI");
  });

  test("sets several attributes from one declaration", () => {
    // `placeholder` and `aria-label` are text a reader sees too; leaving them
    // English was the first thing that went wrong in Chinese.
    const a = el({ i18nAttr: "placeholder:box.hint, aria-label:box.label" });
    applyTo(root([], [a]), (k) => `<${k}>`);
    assert.deepEqual(a.attrs, { placeholder: "<box.hint>", "aria-label": "<box.label>" });
  });

  test("ignores a malformed pair instead of setting a garbage attribute", () => {
    const a = el({ i18nAttr: "title:t, ,broken" });
    applyTo(root([], [a]), (k) => k);
    assert.deepEqual(a.attrs, { title: "t" });
  });
});
