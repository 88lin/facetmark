import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../../src/task-local-state.ts", import.meta.url), "utf8");
const js = ts.transpileModule(source, { fileName: "task-local-state.ts", compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { loadTaskOperations, saveTaskOperation, clearTaskOperation, taskRequest, taskResult, validTaskReceipt, taskStoragePrefix } =
  await import("data:text/javascript;base64," + Buffer.from(js).toString("base64"));
const descriptor = Object.getOwnPropertyDescriptor(globalThis, "localStorage"), values = new Map();
const install = () => Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
  get length() { return values.size; }, key: index => [...values.keys()][index] ?? null,
  getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key),
} });
afterEach(() => { values.clear(); if (descriptor) Object.defineProperty(globalThis, "localStorage", descriptor); else delete globalThis.localStorage; });
const original = { version: 1, requestId: "original-task", createdAt: 10, confirmed: false,
  change: { kind: "start", values: { mode: "summarize", confirmed: true, force: true, bookmark_ids: [17, 23],
    scope: { folder: "Reading", q: "SQLite", status: "pending", exclude_ids: [24] }, preview_revision: "original-selection", preview_prompt_hash: "original-prompt" } } };

test("refresh keeps the exact task scope and another window cannot replace it with a different action", () => {
  install();
  const value = structuredClone(original);
  assert.equal(saveTaskOperation(value), true);
  value.change.values.bookmark_ids.push(25); value.change.values.scope.exclude_ids.push(26); value.change.values.scope.folder = "Later";
  const second = { version: 1, requestId: "another-window", createdAt: 20, confirmed: false,
    change: { kind: "pause", jobId: "saved-job", runId: "first-run" } };
  assert.equal(saveTaskOperation(second), true);
  assert.deepEqual(loadTaskOperations(), [original, second]);
  const request = taskRequest(loadTaskOperations()[0]);
  assert.deepEqual(request.body.bookmark_ids, [17, 23]);
  assert.deepEqual(request.body.scope, original.change.values.scope);
  assert.equal(request.body.request_id, original.requestId);
  assert.equal(clearTaskOperation(second.requestId), true);
  assert.deepEqual(loadTaskOperations(), [original]);
});

test("storage drops unrelated paths, credentials and messages and cannot manufacture a different endpoint", () => {
  install();
  const value = { ...original, path: "/admin/token/rotate", api_key: "synthetic-key", answers: ["private reply"],
    change: { ...original.change, values: { ...original.change.values, api_key: "synthetic-key", messages: ["private reply"], endpoint: "/admin/token/rotate" } } };
  assert.equal(saveTaskOperation(value), true);
  assert.deepEqual(loadTaskOperations(), [original]);
  assert.equal(taskRequest(loadTaskOperations()[0]).path, "/admin/jobs/start");
  assert.equal([...values.values()].join("").includes("synthetic-key"), false);
  assert.equal([...values.values()].join("").includes("private reply"), false);
});

test("unsafe scopes, invalid controls, unknown versions and oversized records stay unsendable", () => {
  install();
  for (const value of [{ ...original, version: 2 }, { ...original, confirmed: true, rejected: true },
    { ...original, change: { kind: "cancel", jobId: "job" } },
    { ...original, change: { kind: "start", values: { ...original.change.values, bookmark_ids: [17, 17] } } },
    { ...original, change: { kind: "start", values: { ...original.change.values, confirmed: false } } },
    { ...original, change: { kind: "start", values: { ...original.change.values, scope: { exclude_ids: [Number.MAX_SAFE_INTEGER + 1] } } } }]) {
    assert.equal(saveTaskOperation(value), false);
  }
  values.set(taskStoragePrefix + "wrong-key", JSON.stringify(original));
  values.set(taskStoragePrefix + "too-long", " ".repeat(160001));
  values.set(taskStoragePrefix + "malformed", "not-json");
  assert.deepEqual(loadTaskOperations(), []);
  assert.equal(values.size, 3);
});

test("resume and controls retain the original attempt and receipts cannot confirm another operation", () => {
  const pause = { version: 1, requestId: "pause-request", createdAt: 10, confirmed: false,
    change: { kind: "pause", jobId: "original-job", runId: "original-run" } };
  assert.deepEqual(taskRequest(pause).body, { request_id: "pause-request", job_id: "original-job", run_id: "original-run" });
  assert.deepEqual(taskRequest({ ...pause, change: { ...pause.change, kind: "resume" } }).body,
    { request_id: "pause-request", resume_id: "original-job", resume_run_id: "original-run", confirmed: true });
  const job = { id: "original-job", run_id: "original-run", state: "running" };
  const receipt = { request_id: "pause-request", action: "pause", job_id: job.id, run_id: job.run_id, result: job };
  assert.equal(validTaskReceipt(receipt, pause), true);
  assert.equal(validTaskReceipt({ ...receipt, action: "cancel" }, pause), false);
  assert.equal(validTaskReceipt({ ...receipt, request_id: "different-request" }, pause), false);
  assert.equal(taskResult({ ...job, run_id: "newer-run" }, pause.change), null);
  assert.equal(validTaskReceipt({ ...receipt, result: { ...job, run_id: "newer-run" } }, pause), false);
});

test("confirmed records survive a read failure and the bounded store never evicts another unresolved task", () => {
  install();
  assert.equal(saveTaskOperation({ ...original, confirmed: true }), true);
  assert.equal(loadTaskOperations()[0].confirmed, true);
  for (let index = 1; index < 24; index++) assert.equal(saveTaskOperation({ ...original, requestId: `request-${index}`, createdAt: 10 + index }), true);
  assert.equal(saveTaskOperation({ ...original, requestId: "twenty-fifth-task" }), false);
  assert.equal(loadTaskOperations().length, 24);
  assert.equal(saveTaskOperation({ ...original, confirmed: true }), true);
  assert.equal(values.has(taskStoragePrefix + original.requestId), true);
});

test("actual local storage failures are reported instead of losing the unresolved operation silently", () => {
  Object.defineProperty(globalThis, "localStorage", { configurable: true, get() { throw new Error("blocked storage"); } });
  assert.deepEqual(loadTaskOperations(), []);
  assert.equal(saveTaskOperation(original), false);
  assert.equal(clearTaskOperation(original.requestId), false);
});

test("a known refusal survives a failed receipt read without prematurely claiming non-acceptance", () => {
  install();
  const refused = { ...original, refused: true, rejected: false,
    change: { ...original.change, values: { ...original.change.values, force: false } } };
  assert.equal(saveTaskOperation(refused), true);
  const restored = loadTaskOperations()[0];
  assert.equal(restored.refused, true);
  assert.equal(restored.rejected, false);
  assert.equal(taskRequest(restored).body.force, false);
  assert.deepEqual(taskRequest(restored).body.scope, original.change.values.scope);
  assert.equal(saveTaskOperation({ ...refused, confirmed: true }), false);
});
