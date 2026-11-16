import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../../src/chat-local-state.ts", import.meta.url), "utf8");
const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { emptyChatLocalState, loadChatLocalState, saveChatLocalState } = await import("data:text/javascript;base64," + Buffer.from(js).toString("base64"));
const previousStorage = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
const values = new Map();
const install = () => Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
  getItem: key => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value),
} });
afterEach(() => {
  values.clear();
  if (previousStorage) Object.defineProperty(globalThis, "localStorage", previousStorage);
  else delete globalThis.localStorage;
});

const operation = { id: "allocated-chat", originKey: "draft:123", requestId: "one-send", mode: "send",
  text: "Original frozen question", language: "en", profileId: "careful", created: false, confirmed: false,
  creation: { id: "allocated-chat", request_id: "one-send.create", title: "Two saved pages", bookmark_ids: [11, 12], profile_id: "careful" } };

test("refresh retains the unsent draft separately from the exact unresolved send and scope", () => {
  install();
  const state = { ...emptyChatLocalState(), scope: { nonce: 123, bookmark_ids: [11, 12], title: "Two saved pages" },
    drafts: { "draft:123": "Next question typed while sending" }, connections: { "draft:123": "careful" },
    operations: { "draft:123": operation } };
  assert.equal(saveChatLocalState(state), true);
  assert.deepEqual(loadChatLocalState(), state);
  state.drafts["draft:123"] = "New editing does not change the frozen request";
  assert.equal(loadChatLocalState().operations["draft:123"].text, "Original frozen question");
});

test("local storage keeps only allowed draft fields and never adopts unknown credentials or answers", () => {
  install();
  const state = { ...emptyChatLocalState(), answer: "Do not store answers here", api_key: "Do not store credentials here",
    scope: { nonce: 123, bookmark_ids: [11], api_key: "extra" },
    operations: { "draft:123": { ...operation, credentials: "extra", creation: { ...operation.creation, api_key: "extra" } } } };
  assert.equal(saveChatLocalState(state), true);
  const saved = values.get("fm-chat-drafts");
  assert.ok(!saved.includes("api_key") && !saved.includes("credentials") && !saved.includes("answer"));
  assert.deepEqual(loadChatLocalState().operations["draft:123"], operation);
});

test("damaged, unsupported, oversized or mismatched records do not become sendable actions", () => {
  install();
  for (const raw of ["{broken", JSON.stringify({ version: 9 }), "x".repeat(1_000_001)]) {
    values.set("fm-chat-drafts", raw);
    assert.deepEqual(loadChatLocalState(), emptyChatLocalState());
    assert.equal(values.get("fm-chat-drafts"), raw);
  }
  values.set("fm-chat-drafts", JSON.stringify({ ...emptyChatLocalState(),
    scope: { nonce: -1, bookmark_ids: [0] }, drafts: { "draft:123": "retained", bad: 7 },
    operations: { mismatch: operation, "draft:123": { ...operation, language: "unsupported" } } }));
  assert.deepEqual(loadChatLocalState(), { ...emptyChatLocalState(), drafts: { "draft:123": "retained" } });
});

test("storage failures are reported and recent drafts stay bounded", () => {
  install();
  const drafts = Object.fromEntries(Array.from({ length: 30 }, (_, index) => ["chat-" + index, "Question " + index]));
  assert.equal(saveChatLocalState({ ...emptyChatLocalState(), drafts }), true);
  assert.equal(Object.keys(loadChatLocalState().drafts).length, 24);
  assert.equal(loadChatLocalState().drafts["chat-29"], "Question 29");
  Object.defineProperty(globalThis, "localStorage", { configurable: true, get() { throw new Error("Synthetic storage failure"); } });
  assert.equal(saveChatLocalState(emptyChatLocalState()), false);
  assert.deepEqual(loadChatLocalState(), emptyChatLocalState());
});
