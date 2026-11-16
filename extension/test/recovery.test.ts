import assert from "node:assert/strict";
import { before, beforeEach, test } from "node:test";
import { setImmediate } from "node:timers/promises";
import { api, ApiError } from "../src/api.ts";
import { install, reset } from "./stub.ts";

const stub = install();
let drainQueue: (manual?: boolean) => Promise<number>;
const ITEM = { bookmark_id: 7, url: "https://example.com/a", title: "A", reason: "wall", attempt: 1, lease_id: "lease-first" };

before(async () => { ({ drainQueue } = await import("../src/background.ts")); });
beforeEach(() => reset(stub));

function serve() {
  stub.routes.set("/queue/next", () => ({ status: 200, json: { items: [ITEM], queue: { leased: 1 }, waiting: 0 } }));
  stub.routes.set("/queue/complete", () => ({ status: 200, json: { bookmark_id: 7, stored: true, changed: true, queue: { done: 1 } } }));
  stub.routes.set("/queue/release", () => ({ status: 200, json: { released: 1 } }));
}

async function tabStarted() {
  // The connection owner uses native WebCrypto, which is not flushed by one
  // setImmediate. Advance fake page clocks only after the real async setup
  // reaches tabs.create; otherwise a failed test leaves its drain in the next
  // test's reset storage and permission state.
  const deadline = performance.now() + 2_000;
  while (!stub.tabs.created.length && performance.now() < deadline) await setImmediate();
  assert.equal(stub.tabs.created.length, 1, "the drain must reach the original tab before advancing its clock");
  await setImmediate();
}

test("manual reading reports a real API failure instead of claiming an empty queue", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  t.after(async () => { t.mock.timers.tick(25_000); await setImmediate(); });
  stub.routes.set("/queue/next", () => ({ status: 503, json: { detail: "Synthetic server unavailable" } }));
  await assert.rejects(drainQueue(true), /Synthetic server unavailable/);
  assert.deepEqual(stub.tabs.created, []);
});

test("an incompatible queue response does not become zero successfully processed pages", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  t.after(async () => { t.mock.timers.tick(25_000); await setImmediate(); });
  stub.routes.set("/queue/next", () => ({ status: 200, json: { items: [{ ...ITEM, lease_id: undefined }] } }));
  await assert.rejects(drainQueue(true), /Update Facetmark/);
  assert.deepEqual(stub.tabs.created, []);
});

test("a server rejection retains its useful reason", async () => {
  stub.routes.set("/bookmark", () => ({ status: 409, json: { detail: "Wait for the running task before changing bookmarks" } }));
  await assert.rejects(api.save({ url: ITEM.url, title: "A" }), (error: unknown) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 409);
    assert.match(error.message, /running task/);
    return true;
  });
});

test("a hanging request has a deadline and aborts its transport", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let aborted = false;
  stub.routes.set("/health", (init) => new Promise((_resolve, reject) => {
    init.signal?.addEventListener("abort", () => { aborted = true; reject(new DOMException("aborted", "AbortError")); }, { once: true });
  }));
  const pending = api.health().catch((error: unknown) => error);
  await setImmediate();
  t.mock.timers.tick(21_000);
  await setImmediate();
  assert.equal(aborted, true, "a stuck request must release the worker");
  const error = await pending;
  assert.ok(error instanceof ApiError);
  assert.match(error.message, /timed out/i);
});

test("a fully loaded tab is read without relying on another load event", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  t.after(async () => { t.mock.timers.tick(25_000); await setImmediate(); });
  serve();
  stub.tabs.behaviour = "complete";
  const pending = drainQueue();
  await tabStarted();
  t.mock.timers.tick(1_500);
  assert.equal(await pending, 1);
  assert.equal(stub.tabs.scripts, 1, "already-complete pages must not wait for a missing event");
});

test("missing page permission does not lease work or open tabs", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  t.after(async () => { t.mock.timers.tick(25_000); await setImmediate(); });
  serve();
  stub.tabs.behaviour = "complete";
  stub.permissions.allowed = false;
  const pending = drainQueue();
  assert.equal(await pending, 0);
  assert.deepEqual(stub.calls, []);
  assert.deepEqual(stub.tabs.created, []);
  assert.deepEqual(stub.permissions.requested, [], "permission is requested only from a user gesture");
});

test("pausing closes the current tab and releases its unprocessed lease", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  t.after(async () => { t.mock.timers.tick(25_000); await setImmediate(); });
  serve();
  stub.tabs.behaviour = "loading";
  const pending = drainQueue();
  await tabStarted();
  assert.equal(stub.tabs.created.length, 1);
  await stub.setSettings({ paused: true });
  assert.equal(await pending, 0);
  assert.equal(stub.tabs.removed.length, 1, "pause must close an in-progress page immediately");
  assert.equal(stub.calls.filter((call) => call.path === "/queue/complete").length, 0);
  assert.equal(stub.calls.filter((call) => call.path === "/queue/release").length, 1);
});

test("delivery failure preserves the page and never invents a fetch error", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  t.after(async () => { t.mock.timers.tick(25_000); await setImmediate(); });
  serve();
  stub.tabs.behaviour = "ok";
  let delivered = 0;
  stub.routes.set("/queue/complete", () => ({ status: ++delivered === 1 ? 503 : 200,
    json: { bookmark_id: 7, stored: true, changed: true, queue: { done: 1 } } }));
  const pending = drainQueue();
  await tabStarted();
  t.mock.timers.tick(0);
  await setImmediate();
  t.mock.timers.tick(1_500);
  assert.equal(await pending, 0);
  const completions = stub.calls.filter((call) => call.path === "/queue/complete");
  assert.equal(completions.length, 1, "delivery failure must not be posted as a second page failure");
  assert.equal((completions[0].body as Record<string, unknown>).body, "the body of the page");
  assert.ok(stub.settings["fetch-deliveries"], "exact text stays local until the server acknowledges it");
});
