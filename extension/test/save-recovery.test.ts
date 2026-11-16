import assert from "node:assert/strict";
import { before, beforeEach, test } from "node:test";
import { api, ApiError } from "../src/api.ts";
import { ownerKey, putDelivery } from "../src/delivery.ts";
import { confirmSaves, readSaves, retrySave, savePage } from "../src/save-delivery.ts";
import { install, reset } from "./stub.ts";

const stub = install();
before(async () => { await import("../src/background.ts"); });
beforeEach(() => reset(stub));
const page = { url: "https://example.com/original", title: "Original title", tags: ["original"] };

function lostSave(): void {
  stub.routes.set("/bookmark", () => ({ status: 503, json: { detail: "Synthetic response lost" } }));
  stub.routes.set("/client/operations/", () => ({ status: 404, json: {} }));
}

test("the page payload is frozen before the first await including nested tags", async () => {
  lostSave();
  const draft = structuredClone(page);
  const result = savePage(draft);
  draft.url = "https://example.com/new";
  draft.title = "Changed title";
  draft.tags.push("changed");
  await assert.rejects(result);
  const [stored] = await readSaves();
  assert.equal(stored.body.url, page.url);
  assert.equal(stored.body.title, page.title);
  assert.deepEqual(stored.body.tags, page.tags);
  assert.deepEqual(stub.calls[0].body, stored.body);
});

test("an explicit settings retry sends the same request and content", async () => {
  lostSave();
  await assert.rejects(savePage(page));
  const [original] = await readSaves();
  stub.routes.set("/bookmark", () => ({ status: 200, json: { bookmark_id: 8, created: true } }));
  const result = await stub.sendMessage({ type: "retry-save", request_id: original.body.request_id });
  assert.equal(result.ok, true);
  const writes = stub.calls.filter(call => call.path === "/bookmark");
  assert.deepEqual(writes.map(call => call.body), [original.body, original.body]);
  assert.deepEqual(await readSaves(), []);
});

test("confirmation is read only and a found receipt never resaves a deleted page", async () => {
  lostSave();
  await assert.rejects(savePage(page));
  const [original] = await readSaves();
  stub.routes.set("/client/operations/", () => ({ status: 200, json: {
    request_id: original.body.request_id, action: "save", result: { bookmark_id: 8, created: true },
  } }));
  assert.equal(await confirmSaves(), 1);
  assert.equal(stub.calls.filter(call => call.path === "/bookmark").length, 1);
  assert.deepEqual(await readSaves(), []);
});

test("retry on another saved connection preserves the original request without network writes", async () => {
  lostSave();
  await assert.rejects(savePage(page));
  const original = await readSaves();
  await stub.setSettings({ token: "another-token" });
  const count = stub.calls.length;
  await assert.rejects(retrySave(original[0].body.request_id), /original saved connection/);
  assert.deepEqual(await readSaves(), original);
  assert.equal(stub.calls.length, count);
});

test("clearing is refused before either kind of original result is removed during a save", async () => {
  const owner = await ownerKey({ endpoint: "http://127.0.0.1:8787", token: "t", channelB: true, paused: false });
  await putDelivery({ version: 1, owner, savedAt: Date.now(), body: {
    bookmark_id: 7, lease_id: "lease", source_url: page.url, request_id: "reading-original", body: "original text",
  } });
  let release!: () => void;
  const hold = new Promise<void>(resolve => { release = resolve; });
  let started!: () => void;
  const entered = new Promise<void>(resolve => { started = resolve; });
  stub.routes.set("/bookmark", async () => { started(); await hold; return { status: 503, json: {} }; });
  const result = savePage(page).catch(error => error);
  await entered;
  try {
    const response = await stub.sendMessage({ type: "discard-deliveries" });
    assert.equal(response.ok, false);
    assert.match(String(response.error), /current page save/);
    assert.equal((stub.settings["fetch-deliveries"] as unknown[]).length, 1);
    assert.equal((await readSaves()).length, 1);
  } finally { release(); await result; }
  const cleared = await stub.sendMessage({ type: "discard-deliveries" });
  assert.equal(cleared.ok, true);
  assert.equal(stub.settings["save-deliveries"], undefined);
  assert.equal(stub.settings["fetch-deliveries"], undefined);
});

test("stale settings cannot overwrite another window and the actual background path reports it", async () => {
  const old = { endpoint: "http://127.0.0.1:8787", token: "t", channelB: true, paused: false };
  await stub.setSettings({ token: "new-token" });
  const response = await stub.sendMessage({ type: "settings-update", expected: old, settings: { ...old, paused: true } });
  assert.equal(response.ok, false);
  assert.equal(response.code, "settings-changed");
  assert.equal(stub.settings.token, "new-token");
  assert.equal(stub.settings.paused, false);
});

test("malformed search entries and nested filter fields return an actionable error", async () => {
  const base = { hits: [], expanded: [], took_ms: { total: 2 }, limit: 20, offset: 0, depth: 20, total: 0,
    has_more: false, depth_capped: false, filters: null };
  for (const change of [{ hits: [null] }, { expanded: [null] }, { filters: { fields: [null] } },
    { took_ms: { total: "wrong" } }, { has_more: "wrong" }]) {
    stub.routes.set("/search", () => ({ status: 200, json: { ...base, ...change } }));
    await assert.rejects(api.search("query"), (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, "invalid");
      assert.match(error.message, /Search returned/);
      return true;
    });
  }
});
