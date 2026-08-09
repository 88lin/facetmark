// Display formatting. `node --test tests/web/*.test.mjs`
//
// `whenAdded` takes `nowMs` as an argument for exactly this reason: a relative
// date formatter tested against the wall clock passes all year and then fails
// on a leap day, or worse, is written to be untestable and never checked.

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import {
  FACET_KEYS,
  totalMs,
  count,
  whenAdded,
  shortUrl,
  pct,
  uptimeParts,
  interpolate,
} from "../../src/facetmark/web/static/format.js";

describe("FACET_KEYS", () => {
  test("names the four facets the pipeline can attribute a hit to", () => {
    assert.deepEqual(Object.keys(FACET_KEYS).sort(), [
      "content",
      "intent",
      "lex_seg",
      "lex_tri",
    ]);
  });

  test("every value is a strings.json key, not a word", () => {
    for (const v of Object.values(FACET_KEYS)) assert.match(v, /^facet\.\w+$/);
  });
});

describe("totalMs", () => {
  test("prefers the total the server computed", () => {
    assert.equal(totalMs({ total: 54.4, embed: 30, search: 24 }), 54);
  });

  test("sums the stages when there is no total", () => {
    assert.equal(totalMs({ embed: 30.2, search: 24.1 }), 54);
  });

  test("is zero rather than NaN for a missing breakdown", () => {
    // `took_ms` is absent from `/quick`. `${undefined} ms` is the bug this
    // function exists to prevent.
    assert.equal(totalMs(undefined), 0);
    assert.equal(totalMs({}), 0);
  });
});

describe("count", () => {
  test("groups thousands", () => {
    assert.equal(count(1710, "en"), "1,710");
    assert.equal(count(1710, "zh"), "1,710");
  });

  test("leaves small numbers alone and treats nothing as zero", () => {
    assert.equal(count(80, "en"), "80");
    assert.equal(count(undefined, "en"), "0");
    assert.equal(count(null, "zh"), "0");
  });
});

describe("whenAdded", () => {
  const NOW = 1_700_000_000_000;
  const ago = (days) => NOW / 1000 - days * 86400;

  test("english", () => {
    assert.equal(whenAdded(ago(0), "en", NOW), "today");
    assert.equal(whenAdded(ago(5), "en", NOW), "5 days ago");
    assert.equal(whenAdded(ago(29), "en", NOW), "29 days ago");
    assert.equal(whenAdded(ago(30), "en", NOW), "last month");
    assert.equal(whenAdded(ago(45), "en", NOW), "2 months ago");
    assert.equal(whenAdded(ago(365), "en", NOW), "last year");
    assert.equal(whenAdded(ago(800), "en", NOW), "2 years ago");
  });

  test("chinese", () => {
    assert.equal(whenAdded(ago(0), "zh", NOW), "今天");
    assert.equal(whenAdded(ago(5), "zh", NOW), "5天前");
    assert.equal(whenAdded(ago(45), "zh", NOW), "2个月前");
    assert.equal(whenAdded(ago(365), "zh", NOW), "去年");
    assert.equal(whenAdded(ago(800), "zh", NOW), "2年前");
  });

  test("says nothing rather than something wrong", () => {
    // An imported library has rows with no timestamp at all, and rows dated in
    // the future by a browser profile whose clock was off.
    assert.equal(whenAdded(0, "en", NOW), "");
    assert.equal(whenAdded(null, "en", NOW), "");
    assert.equal(whenAdded(undefined, "en", NOW), "");
    assert.equal(whenAdded(ago(-30), "en", NOW), "");
  });

  test("reads seconds, not milliseconds", () => {
    // `date_added` is seconds. Passing milliseconds would date every bookmark
    // fifty thousand years in the future, which the guard above would hide.
    assert.equal(whenAdded(ago(5) * 1000, "en", NOW), "");
  });
});

describe("shortUrl", () => {
  test("drops the scheme, the www and a bare slash", () => {
    assert.equal(shortUrl("https://www.example.com/"), "example.com");
    assert.equal(shortUrl("http://example.com"), "example.com");
  });

  test("keeps the path and the query, because they are what tells two rows apart", () => {
    assert.equal(shortUrl("https://docs.rs/tokio/latest?q=1"), "docs.rs/tokio/latest?q=1");
  });

  test("keeps the port, because 8787 and 8788 are different servers", () => {
    assert.equal(shortUrl("http://127.0.0.1:8787/app"), "127.0.0.1:8787/app");
  });

  test("truncates a long tail with an ellipsis", () => {
    const out = shortUrl("https://example.com/" + "a".repeat(200));
    assert.ok(out.endsWith("\u2026"));
    assert.ok(out.length < 80);
    assert.ok(out.startsWith("example.com/"));
  });

  test("falls back to the raw string instead of throwing", () => {
    // A browser export holds `javascript:` bookmarklets and Firefox `place:`
    // rows. Throwing here would take the whole result list down with it.
    assert.equal(shortUrl("not a url"), "not a url");
    assert.equal(shortUrl(""), "");
    assert.equal(shortUrl(undefined), "");
  });
});

describe("pct", () => {
  test("rounds a share of a whole", () => {
    assert.equal(pct(1, 3), 33);
    assert.equal(pct(2, 3), 67);
  });

  test("is zero rather than NaN when there is no denominator", () => {
    // A fresh library has zero indexable rows; every coverage bar divides by
    // it. `NaN%` on screen is the bug this guard exists to prevent.
    assert.equal(pct(5, 0), 0);
    assert.equal(pct(5, undefined), 0);
    assert.equal(pct(5, -1), 0);
  });

  test("clamps to 100 when the numerator overruns, and to 0 below", () => {
    assert.equal(pct(11, 10), 100);
    assert.equal(pct(-2, 10), 0);
  });

  test("treats a missing numerator as zero", () => {
    assert.equal(pct(undefined, 10), 0);
    assert.equal(pct(null, 10), 0);
  });
});

describe("uptimeParts", () => {
  test("shows at most two units, biggest first", () => {
    assert.deepEqual(uptimeParts(90061), [
      { n: 1, unit: "d" },
      { n: 1, unit: "h" },
    ]);
    assert.deepEqual(uptimeParts(3660), [
      { n: 1, unit: "h" },
      { n: 1, unit: "m" },
    ]);
  });

  test("drops a zero second unit rather than pad with it", () => {
    assert.deepEqual(uptimeParts(86400), [{ n: 1, unit: "d" }]);
    assert.deepEqual(uptimeParts(7200), [{ n: 2, unit: "h" }]);
  });

  test("shows seconds only on their own", () => {
    // A server up for four hours and nine seconds has been up for four hours.
    assert.deepEqual(uptimeParts(4 * 3600 + 9), [{ n: 4, unit: "h" }]);
    assert.deepEqual(uptimeParts(45), [{ n: 45, unit: "s" }]);
  });

  test("floors a fraction and clamps a negative to zero", () => {
    assert.deepEqual(uptimeParts(59.9), [{ n: 59, unit: "s" }]);
    assert.deepEqual(uptimeParts(-5), [{ n: 0, unit: "s" }]);
    assert.deepEqual(uptimeParts(undefined), [{ n: 0, unit: "s" }]);
  });
});

describe("interpolate", () => {
  test("fills named placeholders", () => {
    assert.equal(interpolate("{from}-{to} of {total}", { from: 1, to: 20, total: 77 }), "1-20 of 77");
  });

  test("leaves an unknown placeholder visible rather than blanking it", () => {
    // A silently empty slot reads as a finished sentence. `{oops}` on screen
    // is a bug report.
    assert.equal(interpolate("{a} {oops}", { a: 1 }), "1 {oops}");
  });

  test("survives no vars at all", () => {
    assert.equal(interpolate("{n} results", undefined), "{n} results");
    assert.equal(interpolate("plain", { n: 1 }), "plain");
  });

  test("fills a zero, which is falsy and would be skipped by a lazier check", () => {
    assert.equal(interpolate("{n} left", { n: 0 }), "0 left");
  });
});
