// The arithmetic behind the dashboards. `node --test tests/web/*.test.mjs`
//
// derive.js is pure on purpose: no DOM, no fetch, no translation. These tests
// pin the denominators and the drawing order, because a stacked bar whose
// segments do not sum to the total, or a coverage bar drawn against the wrong
// base, is wrong in a way nobody would catch by eye.

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import {
  RUNGS,
  ADVANCED_RUNGS,
  EDGE_WEIGHTS,
  HEALTH_TONE,
  healthBands,
  queueBands,
  coverageRows,
  edgeRows,
  groupByKind,
  factRows,
  sourceIndex,
} from "../../src/facetmark/web/static/derive.js";

describe("RUNGS", () => {
  test("offers the four cheap configurations, full first as the fallback", () => {
    assert.deepEqual(RUNGS.map((r) => r.id), ["full", "A", "B", "C"]);
    assert.equal(RUNGS[0].fallback, true);
  });

  test("every rung names a strings.json key and a why key", () => {
    for (const r of RUNGS) {
      assert.match(r.key, /^mode\.\w+$/);
      assert.match(r.why, /^mode\.\w+\.why$/);
    }
  });
});

describe("ADVANCED_RUNGS", () => {
  test("holds the two rungs the pillbar does not offer", () => {
    assert.deepEqual(ADVANCED_RUNGS.map((r) => r.id), ["D", "E"]);
  });

  test("does not overlap the main pillbar", () => {
    const main = new Set(RUNGS.map((r) => r.id));
    for (const r of ADVANCED_RUNGS) assert.ok(!main.has(r.id));
  });
});

describe("healthBands", () => {
  test("groups verdicts into the four drawing bands", () => {
    const { bands } = healthBands({ alive: 8, drifted: 2, gone: 1, unknown: 1 });
    assert.deepEqual(
      bands.map((b) => [b.cls, b.n]),
      [["ok", 8], ["warn", 2], ["bad", 1], ["mute", 1]],
    );
  });

  test("counts unchecked in the denominator, so a fresh library is not flattered", () => {
    // 1 alive out of 1 checked reads as 100% if unchecked is dropped. With it
    // counted, 1 alive out of 101 is the honest 1%.
    const { total, bands } = healthBands({ alive: 1, unchecked: 100 });
    assert.equal(total, 101);
    assert.equal(bands.length, 1);
    assert.equal(Math.round(bands[0].pct), 1);
  });

  test("bands sum to the total and percentages to 100", () => {
    const h = { alive: 5, drifted: 1, restricted: 1, gone: 1, soft_gone: 1, unreachable: 1 };
    const { total, bands } = healthBands(h);
    assert.equal(bands.reduce((a, b) => a + b.n, 0), total);
    assert.equal(Math.round(bands.reduce((a, b) => a + b.pct, 0)), 100);
  });

  test("treats absence as an empty bar, not a crash", () => {
    assert.deepEqual(healthBands(undefined), { total: 0, bands: [] });
    assert.deepEqual(healthBands({}), { total: 0, bands: [] });
  });
});

describe("queueBands", () => {
  test("draws done, leased, pending, failed in order", () => {
    const { bands } = queueBands({ done: 6, leased: 1, pending: 2, failed: 1 });
    assert.deepEqual(
      bands.map((b) => [b.cls, b.n]),
      [["ok", 6], ["warn", 1], ["mute", 2], ["bad", 1]],
    );
  });

  test("only done is green; failed is the one that needs a reader", () => {
    const { bands } = queueBands({ done: 3, failed: 2 });
    const tone = Object.fromEntries(bands.map((b) => [b.cls, b.n]));
    assert.equal(tone.ok, 3);
    assert.equal(tone.bad, 2);
  });

  test("the denominator is every item the queue holds", () => {
    const { total } = queueBands({ done: 3, pending: 7 });
    assert.equal(total, 10);
  });

  test("treats absence as an empty bar", () => {
    assert.deepEqual(queueBands(undefined), { total: 0, bands: [] });
  });
});

describe("coverageRows", () => {
  const stats = {
    indexable: 100,
    with_body: 80,
    enriched: 60,
    intent_kept: 40,
    vectors: [90, 30],
  };

  test("measures body, enrichment and content vectors against indexable, not bookmarks", () => {
    const rows = coverageRows(stats);
    const byKey = Object.fromEntries(rows.map((r) => [r.key, r]));
    assert.equal(byKey["stats.with_body"].total, 100);
    assert.equal(byKey["stats.enriched"].total, 100);
    assert.equal(byKey["stats.vec_content"].total, 100);
  });

  test("measures intent vectors against the intent queries that were kept", () => {
    const rows = coverageRows(stats);
    const intent = rows.find((r) => r.key === "stats.vec_intent");
    assert.equal(intent.n, 30);
    assert.equal(intent.total, 40);
    assert.equal(intent.gold, true);
  });

  test("falls back to the indexable base when nothing was kept", () => {
    const rows = coverageRows({ indexable: 50, vectors: [10, 0], intent_kept: 0 });
    const intent = rows.find((r) => r.key === "stats.vec_intent");
    assert.equal(intent.total, 50);
  });

  test("survives a missing stats block", () => {
    const rows = coverageRows(undefined);
    assert.equal(rows.length, 4);
    for (const r of rows) assert.equal(r.n, 0);
  });
});

describe("edgeRows", () => {
  test("sorts biggest first and attaches the fusion weight", () => {
    const rows = edgeRows({ same_domain: 9, session: 3, semantic: 5 });
    assert.deepEqual(rows.map((r) => r.kind), ["same_domain", "semantic", "session"]);
    assert.equal(rows.find((r) => r.kind === "session").weight, EDGE_WEIGHTS.session);
  });

  test("breaks count ties by name so the order is stable", () => {
    const rows = edgeRows({ semantic: 2, session: 2 });
    assert.deepEqual(rows.map((r) => r.kind), ["semantic", "session"]);
  });

  test("treats absence as no rows", () => {
    assert.deepEqual(edgeRows(undefined), []);
  });
});

describe("groupByKind", () => {
  test("groups neighbours and orders the heaviest kind first", () => {
    const rows = [
      { kind: "same_domain", id: 1 },
      { kind: "session", id: 2 },
      { kind: "session", id: 3 },
    ];
    const groups = groupByKind(rows);
    assert.deepEqual(groups.map(([k]) => k), ["session", "same_domain"]);
    assert.equal(groups[0][1].length, 2);
  });

  test("files a missing kind under unknown", () => {
    const groups = groupByKind([{ id: 1 }]);
    assert.equal(groups[0][0], "unknown");
  });

  test("treats absence as no groups", () => {
    assert.deepEqual(groupByKind(undefined), []);
  });
});

describe("factRows", () => {
  test("keeps a zero, because opened 0 times is the most informative value", () => {
    const rows = factRows({ open_count: 0, indexed: { chars: 0 } });
    const keys = rows.map((r) => r.key);
    assert.ok(keys.includes("detail.opens"));
    assert.ok(keys.includes("detail.chars"));
  });

  test("drops empty, null and undefined but not a real value", () => {
    const rows = factRows({ folder: "", utility: null, content_type: "article" });
    const keys = rows.map((r) => r.key);
    assert.ok(!keys.includes("detail.folder"));
    assert.ok(!keys.includes("detail.utility"));
    assert.ok(keys.includes("detail.kind"));
  });

  test("flags the extractor error as the bad row", () => {
    const rows = factRows({ indexed: { error: "boom" } });
    const err = rows.find((r) => r.key === "detail.error");
    assert.equal(err.tone, "bad");
  });

  test("reads chars and lang from indexed, not from invented top-level fields", () => {
    const rows = factRows({ indexed: { chars: 1234, lang: "en" } });
    const byKey = Object.fromEntries(rows.map((r) => [r.key, r.value]));
    assert.equal(byKey["detail.chars"], 1234);
    assert.equal(byKey["detail.lang"], "en");
  });

  test("treats absence as only the two defaulted numeric rows", () => {
    // `open_count ?? 0` and `indexed.chars ?? 0` default to zero, and zeros
    // survive the filter, so even an empty record shows those two.
    const rows = factRows(undefined);
    assert.deepEqual(rows.map((r) => r.key).sort(), ["detail.chars", "detail.opens"]);
  });
});

describe("sourceIndex", () => {
  test("indexes by the citation number, not the array position", () => {
    // /synthesize numbers sources from 1; a claim citing [3] must find source
    // 3 even when the list comes back out of order.
    const m = sourceIndex([{ n: 3, title: "c" }, { n: 1, title: "a" }]);
    assert.equal(m.get(3).title, "c");
    assert.equal(m.get(1).title, "a");
  });

  test("treats absence as an empty map", () => {
    assert.equal(sourceIndex(undefined).size, 0);
  });
});

describe("HEALTH_TONE", () => {
  test("maps every verdict to a pill tone, with unchecked as absence", () => {
    assert.equal(HEALTH_TONE.alive, "ok");
    assert.equal(HEALTH_TONE.gone, "bad");
    assert.equal(HEALTH_TONE.unchecked, "mute");
  });
});
