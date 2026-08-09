// Paging arithmetic. `node --test tests/web/*.test.mjs`
//
// These live under `tests/` rather than beside the module so they stay out of
// the wheel, and they are `.mjs` because `node --test` parses a bare `.js`
// under a package-less directory as CommonJS.
//
// The rules under test are the ones that were wrong in the first draft and are
// invisible in a screenshot: a second render at the same offset must not
// advance the cursor twice, and page two must be asked for at the depth page
// one was actually ranked at.

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import {
  startCursor,
  advance,
  nextRequest,
  mergePage,
  pageLabel,
} from "../../src/facetmark/web/static/paging.js";
import { interpolate } from "../../src/facetmark/web/static/format.js";

const STRINGS = JSON.parse(
  readFileSync(
    fileURLToPath(new URL("../../src/facetmark/web/static/strings.json", import.meta.url)),
    "utf8",
  ),
);

/** A server response, with only the fields the cursor reads. */
const page = (o) => ({
  offset: 0,
  hits: [],
  depth: 50,
  total: 0,
  has_more: false,
  depth_capped: false,
  ...o,
});

const hits = (from, n) =>
  Array.from({ length: n }, (_, i) => ({ bookmark_id: from + i, title: `b${from + i}` }));

describe("startCursor", () => {
  test("carries the query and nothing else", () => {
    assert.deepEqual(startCursor("rust"), {
      query: "rust",
      seen: 0,
      depth: 0,
      total: 0,
      more: false,
      capped: false,
    });
  });
});

describe("advance", () => {
  test("counts the window, not the sum of the pages", () => {
    const c = advance(startCursor("q"), page({ offset: 20, hits: hits(20, 20), total: 77 }));
    assert.equal(c.seen, 40);
  });

  test("a second render at the same offset does not double-count", () => {
    // The search box paints twice per query: `/quick` first, then `/search`,
    // both at offset 0. Accumulating lengths here would set `seen` to 30 and
    // page two would start past ten results nobody ever saw.
    let c = advance(startCursor("q"), page({ offset: 0, hits: hits(0, 10), total: 77 }));
    c = advance(c, page({ offset: 0, hits: hits(0, 20), total: 77, has_more: true }));
    assert.equal(c.seen, 20);
    assert.deepEqual(nextRequest(c, 20), { offset: 20, limit: 20, depth: 50 });
  });

  test("a shorter second ranking pulls the cursor back rather than stranding it", () => {
    let c = advance(startCursor("q"), page({ offset: 0, hits: hits(0, 20) }));
    c = advance(c, page({ offset: 0, hits: hits(0, 6), has_more: true }));
    assert.equal(c.seen, 6, "cursor must track the rows on screen");
  });

  test("depth is pinned by the first response", () => {
    // RRF is not order-stable as the pool deepens once more than one facet is
    // in play, so a page two ranked at a different depth disagrees with page
    // one about what page one was.
    let c = advance(startCursor("q"), page({ depth: 50, hits: hits(0, 20), has_more: true }));
    c = advance(c, page({ offset: 20, hits: hits(20, 20), depth: 0, has_more: true }));
    assert.equal(c.depth, 50);
    assert.equal(nextRequest(c, 20).depth, 50);
  });

  test("a depth the server does report wins, because the server is the one ranking", () => {
    let c = advance(startCursor("q"), page({ depth: 50, hits: hits(0, 20), has_more: true }));
    c = advance(c, page({ offset: 20, hits: hits(20, 20), depth: 120, has_more: true }));
    assert.equal(c.depth, 120);
  });

  test("survives a response missing every optional field", () => {
    const c = advance(startCursor("q"), {});
    assert.deepEqual(c, { query: "q", seen: 0, depth: 0, total: 0, more: false, capped: false });
  });
});

describe("nextRequest", () => {
  test("is null when the server said there is no more", () => {
    const c = advance(startCursor("q"), page({ hits: hits(0, 3), total: 3 }));
    assert.equal(nextRequest(c, 20), null);
  });

  test("is null without a query, so a cleared box cannot page", () => {
    const c = advance(startCursor(""), page({ hits: hits(0, 20), has_more: true }));
    assert.equal(nextRequest(c, 20), null);
  });

  test("offsets by what was served, not by what was asked for", () => {
    // A page can come back short -- the privacy filter drops rows after the
    // limit is applied. Offsetting by the requested 20 would skip the tail.
    const c = advance(startCursor("q"), page({ offset: 0, hits: hits(0, 14), has_more: true }));
    assert.deepEqual(nextRequest(c, 20), { offset: 14, limit: 20, depth: 50 });
  });
});

describe("mergePage", () => {
  test("appends in order", () => {
    assert.deepEqual(
      mergePage(hits(0, 2), hits(2, 2)).map((h) => h.bookmark_id),
      [0, 1, 2, 3],
    );
  });

  test("drops a row already on screen", () => {
    // `has_more` is an upper bound with several facets in play, and the library
    // can change between two requests. A repeated row is the visible symptom.
    const merged = mergePage(hits(0, 3), [{ bookmark_id: 2 }, { bookmark_id: 3 }]);
    assert.deepEqual(
      merged.map((h) => h.bookmark_id),
      [0, 1, 2, 3],
    );
  });

  test("tolerates a page with no hits array at all", () => {
    assert.deepEqual(mergePage(hits(0, 2), undefined).length, 2);
  });

  test("does not mutate the rows it was given", () => {
    const rows = hits(0, 2);
    mergePage(rows, hits(2, 2));
    assert.equal(rows.length, 2);
  });
});

describe("pageLabel", () => {
  const label = (o) => pageLabel(advance(startCursor("q"), page(o)));

  test("no rows", () => {
    assert.deepEqual(label({}), { key: "results.none", vars: {} });
  });

  test("first page of many", () => {
    assert.deepEqual(label({ hits: hits(0, 20), total: 77, has_more: true }), {
      key: "results.window",
      vars: { from: 1, to: 20, total: 77 },
    });
  });

  test("middle page", () => {
    assert.deepEqual(label({ offset: 20, hits: hits(20, 20), total: 77, has_more: true }), {
      key: "results.window",
      vars: { from: 1, to: 40, total: 77 },
    });
  });

  test("the exact last page reads as a count, not as a window", () => {
    assert.deepEqual(label({ offset: 60, hits: hits(60, 17), total: 77, has_more: false }), {
      key: "results.all",
      vars: { n: 77 },
    });
  });

  test("at the depth ceiling the total is a floor and the label says so", () => {
    assert.equal(
      label({ hits: hits(0, 20), total: 200, has_more: true, depth_capped: true }).key,
      "results.window_capped",
    );
  });
});

describe("the labels and the strings agree", () => {
  // The Python suite checks the two languages against each other. Nothing
  // checks either of them against the values this module actually supplies,
  // which is the direction a placeholder rename breaks in.
  const cases = [
    { key: "results.none", vars: {} },
    { key: "results.window", vars: { from: 1, to: 20, total: 77 } },
    { key: "results.window_capped", vars: { from: 1, to: 20, total: 200 } },
    { key: "results.all", vars: { n: 77 } },
  ];

  for (const lang of ["en", "zh"]) {
    for (const { key, vars } of cases) {
      test(`${lang} ${key} is fully filled in`, () => {
        const raw = STRINGS[lang][key];
        assert.ok(raw, `${lang} has no ${key}`);
        const out = interpolate(raw, vars);
        assert.ok(!/\{\w+\}/.test(out), `unfilled placeholder in ${lang} ${key}: ${out}`);
      });
    }
  }
});
