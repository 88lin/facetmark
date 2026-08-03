// `/queue/stats` is a `GROUP BY state` plus one derived number. These pin the
// arithmetic that turns it into a sentence, because getting it wrong is not a
// crash -- it is a plausible-looking count that contradicts what the button
// next to it does.

import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { describeQueue, summarizeQueue } from "../src/api.ts";

describe("summarizeQueue", () => {
  test("waiting is carved out of pending, not added to it", () => {
    // The server computes `waiting` as "pending AND still in backoff". Adding
    // the two would double-count; ignoring `waiting` is what the UI used to do.
    const s = summarizeQueue({ pending: 40, waiting: 31, done: 2100 });
    assert.equal(s.ready, 9);
    assert.equal(s.waiting, 31);
    assert.equal(s.ready + s.waiting, 40);
  });

  test("a state with no rows is absent from the payload, not zero", () => {
    const s = summarizeQueue({ done: 7 });
    assert.deepEqual(s, { ready: 0, waiting: 0, leased: 0, failed: 0, done: 7 });
  });

  test("a queue entirely in backoff has nothing ready", () => {
    // This is the shape that made a drain look broken: 324 pending, an empty
    // lease response, and a status line that said "324 waiting for the browser".
    const s = summarizeQueue({ pending: 324, waiting: 324 });
    assert.equal(s.ready, 0);
    assert.equal(s.waiting, 324);
  });

  test("an impossible payload still yields a countable one", () => {
    const s = summarizeQueue({ pending: 2, waiting: 9, leased: -1 });
    assert.equal(s.ready, 0, "never negative");
    assert.equal(s.waiting, 2, "never more waiting than pending");
    assert.equal(s.leased, 0);
  });

  test("nothing at all is not a crash", () => {
    assert.deepEqual(summarizeQueue(undefined), {
      ready: 0,
      waiting: 0,
      leased: 0,
      failed: 0,
      done: 0,
    });
  });
});

describe("describeQueue", () => {
  test("a queue with only finished work has nothing to say", () => {
    assert.equal(describeQueue(summarizeQueue({ done: 2376 })), "");
  });

  test("backoff and readiness are named differently", () => {
    const line = describeQueue(summarizeQueue({ pending: 40, waiting: 31 }));
    assert.match(line, /9 ready for the browser/);
    assert.match(line, /31 retrying later/);
  });

  test("only outstanding work is mentioned", () => {
    const line = describeQueue(summarizeQueue({ pending: 3, leased: 1, failed: 5, done: 900 }));
    assert.equal(line, "3 ready for the browser · 1 in flight · 5 gave up");
    assert.doesNotMatch(line, /900/);
  });
});
