import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../../src/mcp-local-state.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { loadMcpOperations, saveMcpOperation, clearMcpOperation, mcpRequest, mcpAcceptedStatus, mcpReceiptStatus, validMcpStatus, mcpStoragePrefix } =
  await import("data:text/javascript;base64," + Buffer.from(compiled).toString("base64"));
const descriptor = Object.getOwnPropertyDescriptor(globalThis, "localStorage"), values = new Map();
const install = () => Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
  get length() { return values.size; }, key: index => [...values.keys()][index] ?? null,
  getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key),
} });
afterEach(() => { values.clear(); if (descriptor) Object.defineProperty(globalThis, "localStorage", descriptor); else delete globalThis.localStorage; });
const original = { version: 1, requestId: "mcp-original", createdAt: 10, expectedRevision: "a".repeat(64), change: { rotate_token: true } };
const status = { revision: "b".repeat(64), enabled: true, configured: true, running: true, transport_ready: true,
  status: "ready", error: "", endpoint: "http://127.0.0.1:8787/mcp/", token: "synthetic-current-token",
  client_config: {}, locked: { enabled: false, token: false }, last_request_at: null, probe: null };
const receipt = { request_id: original.requestId, action: "configure", state: "accepted", accepted_revision: "c".repeat(64),
  accepted_at: 100, superseded: true, status };

test("the original change keeps its revision and ID, and no credentials or arbitrary route enter recovery storage", () => {
  install();
  saveMcpOperation({ ...original, token: "synthetic-private-token", path: "/admin/token/rotate",
    change: { ...original.change, enabled: false, token: "synthetic-private-token" } });
  const saved = loadMcpOperations()[0];
  assert.deepEqual(saved, { ...original, change: { rotate_token: true, enabled: false } });
  assert.deepEqual(mcpRequest(saved), { rotate_token: true, enabled: false, request_id: original.requestId, expected_revision: original.expectedRevision });
  assert.equal([...values.values()].join("").includes("synthetic-private-token"), false);
  assert.equal([...values.values()].join("").includes("/admin/token/rotate"), false);
});

test("different windows retain separate changes, and the bounded store never evicts an unresolved original", () => {
  install();
  for (let index = 0; index < 8; index++) saveMcpOperation({ ...original, requestId: `mcp-${index}`, createdAt: index });
  assert.throws(() => saveMcpOperation({ ...original, requestId: "ninth" }), /Finish/);
  assert.equal(loadMcpOperations().length, 8);
  assert.throws(() => saveMcpOperation({ ...original, requestId: "mcp-0", createdAt: 0, change: { enabled: false } }), /unchanged/);
  clearMcpOperation("mcp-4");
  assert.deepEqual(loadMcpOperations().map(item => item.requestId), ["mcp-0", "mcp-1", "mcp-2", "mcp-3", "mcp-5", "mcp-6", "mcp-7"]);
});

test("malformed or mismatched storage cannot become a fresh write or be silently erased", () => {
  install();
  values.set(mcpStoragePrefix + "wrong-id", JSON.stringify(original));
  assert.throws(() => loadMcpOperations(), /could not be read/);
  assert.throws(() => saveMcpOperation({ ...original, requestId: "new" }), /could not be read/);
  assert.equal(values.size, 1);
});

test("receipts confirm only the original ID and well-formed current configuration, including a closed original", () => {
  assert.deepEqual(mcpReceiptStatus(receipt, original), status);
  assert.deepEqual(mcpReceiptStatus({ ...receipt, state: "closed" }, original), status);
  assert.deepEqual(mcpAcceptedStatus({ ...status, operation: receipt }, original), status);
  for (const bad of [{ ...receipt, request_id: "other" }, { ...receipt, action: "probe" }, { ...receipt, state: "unknown" },
    { ...receipt, accepted_revision: "broken" }, { ...receipt, status: { ...status, locked: null } },
    { ...receipt, status: { ...status, probe: { ok: true, tools: NaN } } }]) assert.equal(mcpReceiptStatus(bad, original), null);
  assert.equal(mcpAcceptedStatus({ ...status, operation: { ...receipt, state: "closed" } }, original), null);
  assert.equal(validMcpStatus({ ...status, last_request_at: "yesterday" }), false);
  assert.equal(validMcpStatus({ ...status, client_config: [] }), false);
});
