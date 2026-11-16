import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../../src/library-local-state.ts", import.meta.url), "utf8");
const js = ts.transpileModule(source, { fileName: "library-local-state.ts", compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { loadLibraryOperations, saveLibraryOperation, clearLibraryOperation, libraryRequest, exportRequest, libraryStoragePrefix } =
  await import("data:text/javascript;base64," + Buffer.from(js).toString("base64"));
const descriptor = Object.getOwnPropertyDescriptor(globalThis, "localStorage"), values = new Map();
const install = () => Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
  get length() { return values.size; }, key: index => [...values.keys()][index] ?? null,
  getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key),
} });
afterEach(() => { values.clear(); if (descriptor) Object.defineProperty(globalThis, "localStorage", descriptor); else delete globalThis.localStorage; });
const operation = { version: 1, requestId: "saved-edit", createdAt: 10, confirmed: false,
  change: { kind: "edit", bookmarkId: 17, values: { title: "Original submitted title", tags: ["Original tag"] } } };

test("refresh preserves the frozen edit and another window keeps a separate operation", () => {
  install();
  const original = structuredClone(operation);
  assert.equal(saveLibraryOperation(original), true);
  original.change.values.title = "Later local title"; original.change.values.tags.push("Later tag");
  const second = { ...operation, requestId: "second-window", createdAt: 20, change: { kind: "bulk", ids: [23, 24], action: "delete" } };
  assert.equal(saveLibraryOperation(second), true);
  assert.deepEqual(loadLibraryOperations(), [second, operation]);
  assert.deepEqual(libraryRequest(loadLibraryOperations()[1]), { path: "/admin/library/bookmarks/17", method: "PATCH", action: "edit:17",
    body: { title: "Original submitted title", tags: ["Original tag"], request_id: "saved-edit" } });
  assert.equal(clearLibraryOperation("second-window"), true);
  assert.deepEqual(loadLibraryOperations(), [operation]);
});

test("only known collection fields survive; storage cannot turn a saved edit into another endpoint", () => {
  install();
  assert.equal(saveLibraryOperation({ ...operation, path: "/admin/token/rotate", api_key: "synthetic-extra-key",
    change: { ...operation.change, values: { ...operation.change.values, api_key: "synthetic-extra-key" } } }), true);
  const raw = values.get(libraryStoragePrefix + operation.requestId);
  assert.ok(!raw.includes("api_key") && !raw.includes("/admin/token"));
  assert.deepEqual(loadLibraryOperations(), [operation]);
});

test("damaged, mismatched, unsupported and oversized records are retained but cannot be submitted", () => {
  install();
  const key = libraryStoragePrefix + operation.requestId;
  for (const raw of ["{damaged", JSON.stringify({ ...operation, version: 2 }), JSON.stringify({ ...operation, requestId: "other-id" }),
    JSON.stringify({ ...operation, change: { kind: "rotate-token" } }), JSON.stringify({ ...operation, change: { kind: "edit", bookmarkId: 17, values: {} } }), "x".repeat(64001)]) {
    values.set(key, raw); assert.deepEqual(loadLibraryOperations(), []); assert.equal(values.get(key), raw);
  }
});

test("a confirmed operation stays read-only after refresh and storage failures are reported", () => {
  install();
  assert.equal(saveLibraryOperation({ ...operation, confirmed: true }), true);
  assert.equal(loadLibraryOperations()[0].confirmed, true);
  Object.defineProperty(globalThis, "localStorage", { configurable: true, get() { throw new Error("Synthetic storage failure"); } });
  assert.equal(saveLibraryOperation(operation), false); assert.equal(clearLibraryOperation(operation.requestId), false);
  assert.deepEqual(loadLibraryOperations(), []);
});

test("an edit keeps its complete draft if the original is removed, while sending only changed fields", () => {
  install();
  const draft = { url: "https://synthetic.example/original", title: "Original submitted title", folder: "Original folder", tags: ["Original tag"] };
  assert.equal(saveLibraryOperation({ ...operation, draft: { ...draft, credentials: "synthetic-extra-key" } }), true);
  const restored = loadLibraryOperations()[0];
  assert.deepEqual(restored.draft, draft);
  assert.deepEqual(libraryRequest(restored).body, { title: "Original submitted title", tags: ["Original tag"], request_id: "saved-edit" });
  assert.ok(!values.get(libraryStoragePrefix + operation.requestId).includes("credentials"));
  assert.equal(saveLibraryOperation({ ...operation, draft: { ...draft, url: "" } }), false);
});

test("cross-page export preserves keyword, state and exceptions instead of exporting the loaded page", () => {
  const context = { current: { folder: "Chosen", q: "remembered page", status: "failed", exclude_ids: [4] },
    selectedIds: [], pageIds: [1, 2, 3], allMatching: true, selectedCount: 145, semantic: false };
  const selected = exportRequest(context, "selected", "json");
  assert.deepEqual(selected, { format: "json", scope: context.current });
  context.current.exclude_ids.push(5); context.current.q = "New search";
  assert.equal(selected.scope.q, "remembered page"); assert.deepEqual(selected.scope.exclude_ids, [4]);
  assert.deepEqual(exportRequest({ ...context, allMatching: false, selectedIds: [20, 21] }, "selected", "html"), { format: "html", ids: [20, 21] });
  assert.deepEqual(exportRequest(context, "page", "json"), { format: "json", ids: [1, 2, 3] });
  assert.deepEqual(exportRequest(context, "all", "json"), { format: "json", scope: {} });
});
