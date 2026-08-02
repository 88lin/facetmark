// The channel-B worker, run without a browser.
//
// Every test here is a way the loop can go wrong that is invisible from the
// type checker: a tab that will not open, a page with no text, a token the
// server no longer accepts. The first of those used to hang the promise, and a
// hang is not a failing test unless something is holding a clock -- hence
// `within`.

import assert from "node:assert/strict";
import { before, beforeEach, describe, test } from "node:test";

import { type Stub, install, reset, within } from "./stub.ts";

const stub: Stub = install();
let drainQueue: () => Promise<number>;

const ITEM = { bookmark_id: 7, url: "https://example.com/a", title: "A", reason: "wall",
               attempt: 1 };

function serveOneItem(): void {
  stub.routes.set("/queue/next", () => ({
    status: 200,
    json: { items: [ITEM], queue: { pending: 1 }, waiting: 0 },
  }));
  stub.routes.set("/queue/complete", () => ({
    status: 200,
    json: { bookmark_id: 7, stored: true, changed: true, queue: {} },
  }));
}

function completions(): Record<string, unknown>[] {
  return stub.calls
    .filter((c) => c.path.startsWith("/queue/complete"))
    .map((c) => c.body as Record<string, unknown>);
}

before(async () => {
  // Imported after the globals exist: the module registers listeners on load.
  ({ drainQueue } = await import("../src/background.ts"));
});

beforeEach(() => reset(stub));

describe("drainQueue", () => {
  test("reads a page out of a tab and hands the text back", async () => {
    serveOneItem();
    const n = await within(8000, drainQueue());
    assert.equal(n, 1);
    assert.deepEqual(stub.tabs.created, ["https://example.com/a"]);
    assert.deepEqual(completions(), [
      { bookmark_id: 7, body: "the body of the page", title: "A Page",
        final_url: "http://127.0.0.1:8787/final" },
    ]);
    assert.equal(stub.tabs.removed.length, 1, "the background tab is closed again");
  });

  test("a tab that will not open is reported, not waited on forever", async () => {
    // `chrome.tabs.create` answers with `undefined` and sets `lastError`.
    // Reading `.id` off that threw inside a callback the promise could not see,
    // so the drain never settled and channel B stopped for the session.
    serveOneItem();
    stub.tabs.behaviour = "lastError";
    const n = await within(4000, drainQueue());
    assert.equal(n, 1);
    const [done] = completions();
    assert.equal(done.bookmark_id, 7);
    assert.match(String(done.error), /No tab with id/);
    assert.equal(done.body, undefined, "no body was invented for a tab that never opened");
  });

  test("a tab handle with no id is the same kind of failure", async () => {
    serveOneItem();
    stub.tabs.behaviour = "noTab";
    const n = await within(4000, drainQueue());
    assert.equal(n, 1);
    assert.match(String(completions()[0].error), /would not open a tab/);
  });

  test("a page that rendered nothing readable is a failure with a reason", async () => {
    serveOneItem();
    stub.page = { text: "   ", title: "", url: "" };
    const n = await within(8000, drainQueue());
    assert.equal(n, 1);
    assert.match(String(completions()[0].error), /no readable text/);
    assert.equal(stub.tabs.removed.length, 1);
  });

  test("paused means no request at all, not a request that is thrown away", async () => {
    serveOneItem();
    stub.settings.paused = true;
    assert.equal(await within(2000, drainQueue()), 0);
    assert.deepEqual(stub.calls, []);
    assert.deepEqual(stub.tabs.created, []);
  });

  test("channel B switched off is also silent", async () => {
    serveOneItem();
    stub.settings.channelB = false;
    assert.equal(await within(2000, drainQueue()), 0);
    assert.deepEqual(stub.calls, []);
  });

  test("a server that is down is not an error the user has to see", async () => {
    stub.routes.set("/queue/next", () => ({ status: 503, json: {} }));
    assert.equal(await within(2000, drainQueue()), 0);
    assert.deepEqual(stub.titles, [], "no badge title for something that retries by itself");
  });

  test("a rejected pairing token is an error the user has to see", async () => {
    // It will never fix itself. Without a signal, channel B is
    // indistinguishable from channel B having nothing to do.
    stub.routes.set("/queue/next", () => ({ status: 401, json: {} }));
    assert.equal(await within(2000, drainQueue()), 0);
    assert.equal(stub.titles.length, 1);
    assert.match(stub.titles[0], /pairing token rejected/);
  });
});
