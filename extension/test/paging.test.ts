// The popup renders every query twice -- lexical first paint, then the full
// pipeline over the top -- and both stages report offset 0. That is the shape
// that breaks a naive "seen += hits.length" cursor, so it is the shape most of
// these tests are about. Everything here is pure: no DOM, no fetch.

import assert from "node:assert/strict";
import { describe, test } from "node:test";

import {
  advance,
  describePage,
  nextRequest,
  startCursor,
  type Hit,
  type PageCursor,
  type SearchResponse,
} from "../src/api.ts";

function hit(i: number): Hit {
  return {
    bookmark_id: i + 1,
    url: `https://e.test/${i}`,
    title: `hit ${i}`,
    score: 1,
    facets: ["content"],
    snippet: "",
    folder: "",
    domain: "e.test",
    date_added: 0,
    cold: false,
  };
}

function response(over: Partial<SearchResponse> & { n?: number }): SearchResponse {
  const { n = 0, ...rest } = over;
  return {
    query: "kafka",
    hits: Array.from({ length: n }, (_, i) => hit(i)),
    expanded: [],
    took_ms: {},
    config: "fused",
    limit: 20,
    offset: 0,
    depth: 60,
    total: 0,
    has_more: false,
    depth_capped: false,
    ...rest,
  };
}

describe("startCursor", () => {
  test("a fresh cursor asks for nothing until a response says there is more", () => {
    const cur = startCursor("kafka");
    assert.equal(cur.seen, 0);
    assert.equal(nextRequest(cur, 20), null);
    assert.equal(describePage(cur), "no results");
  });
});

describe("advance", () => {
  test("the two-stage first paint counts one page, not two", () => {
    // Lexical lands first with 20 rows at offset 0; the full pipeline replaces
    // them with its own 20 rows, also at offset 0. `seen` is 20 throughout. A
    // cursor that added lengths would say 40 and then skip results 21-40.
    let cur = startCursor("kafka");
    cur = advance(cur, response({ n: 20, offset: 0, total: 50, has_more: true }));
    assert.equal(cur.seen, 20);
    cur = advance(cur, response({ n: 20, offset: 0, total: 50, has_more: true }));
    assert.equal(cur.seen, 20);
  });

  test("seen follows the server's offset, so a shorter second ranking cannot strand it", () => {
    let cur = startCursor("kafka");
    cur = advance(cur, response({ n: 20, offset: 0, total: 50, has_more: true }));
    cur = advance(cur, response({ n: 12, offset: 0, total: 12, has_more: false }));
    assert.equal(cur.seen, 12);
    assert.equal(nextRequest(cur, 20), null);
  });

  test("a page arriving at an offset advances the cursor past it", () => {
    let cur = startCursor("kafka");
    cur = advance(cur, response({ n: 20, offset: 0, total: 50, has_more: true }));
    cur = advance(cur, response({ n: 20, offset: 20, total: 50, has_more: true }));
    assert.equal(cur.seen, 40);
  });

  test("the first response's depth is kept, and later pages inherit it", () => {
    // The whole point of the parameter: page 2 must be a slice of the ranking
    // page 1 came from, which means sending back the depth page 1 was served
    // at rather than letting the server derive a deeper one.
    let cur = startCursor("kafka");
    cur = advance(cur, response({ n: 20, depth: 60, total: 90, has_more: true }));
    assert.equal(cur.depth, 60);
    assert.deepEqual(nextRequest(cur, 20), { offset: 20, limit: 20, depth: 60 });
  });

  test("a response that omits depth does not clear the pinned one", () => {
    let cur = startCursor("kafka");
    cur = advance(cur, response({ n: 20, depth: 60, total: 90, has_more: true }));
    cur = advance(cur, response({ n: 20, offset: 20, depth: 0, total: 90, has_more: true }));
    assert.equal(cur.depth, 60);
  });
});

describe("nextRequest", () => {
  test("nothing is requested once the server says the results ran out", () => {
    let cur = startCursor("kafka");
    cur = advance(cur, response({ n: 8, total: 8, has_more: false }));
    assert.equal(nextRequest(cur, 20), null);
  });

  test("an empty query is never paged", () => {
    const cur: PageCursor = { ...startCursor(""), seen: 20, more: true, total: 50, depth: 60 };
    assert.equal(nextRequest(cur, 20), null);
  });

  test("the page size is the caller's, not the server's last limit", () => {
    let cur = startCursor("kafka");
    cur = advance(cur, response({ n: 20, limit: 20, total: 90, has_more: true }));
    assert.equal(nextRequest(cur, 5)?.limit, 5);
  });
});

describe("describePage", () => {
  test("a capped total is shown as a floor, because that is what it is", () => {
    // `depth_capped` means the server stopped looking, so `total` is a lower
    // bound. Printing "20 of 200" there would be a number the server never
    // claimed.
    let cur = startCursor("kafka");
    cur = advance(
      cur,
      response({ n: 20, total: 200, has_more: true, depth_capped: true }),
    );
    assert.equal(describePage(cur), "20 of 200+ (depth limit reached)");
  });

  test("an exact total is shown as one", () => {
    let cur = startCursor("kafka");
    cur = advance(cur, response({ n: 20, total: 90, has_more: true }));
    assert.equal(describePage(cur), "20 of 90");
  });

  test("the last page states a count rather than a fraction of itself", () => {
    let cur = startCursor("kafka");
    cur = advance(cur, response({ n: 3, total: 3, has_more: false }));
    assert.equal(describePage(cur), "3 results");
    cur = advance(cur, response({ n: 1, total: 1, has_more: false }));
    assert.equal(describePage(cur), "1 result");
  });
});
