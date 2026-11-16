import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../../src/health-local-state.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { loadHealthOperations, saveHealthOperation, clearHealthOperation, healthRequest, originalHealthRun, validHealthRun, validHealthCounts, healthStoragePrefix } =
  await import("data:text/javascript;base64," + Buffer.from(compiled).toString("base64"));
const descriptor = Object.getOwnPropertyDescriptor(globalThis, "localStorage"), values = new Map();
const install = () => Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
  get length() { return values.size; }, key: index => [...values.keys()][index] ?? null,
  getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key),
} });
afterEach(() => { values.clear(); if (descriptor) Object.defineProperty(globalThis, "localStorage", descriptor); else delete globalThis.localStorage; });
const original = { version: 1, requestId: "health-original", createdAt: 10, limit: 20, libraryId: "a".repeat(64) };
const run = { request_id: original.requestId, state: "running", params: { limit: 20, ids: null, expected_library: original.libraryId },
  targets_count: 18, started_at: 100, finished_at: null, report: null, error: "" };
const report = { considered: 18, probed: 18, escalated: 0, recovered_bodies: 0, by_status: { alive: 18 }, confirmed_gone: [], errors: [] };

test("the original limit and library are frozen and only that exact run can confirm acceptance", () => {
  install(); saveHealthOperation({ ...original, token: "synthetic-private", path: "/other-action" });
  assert.deepEqual(loadHealthOperations(), [original]);
  assert.deepEqual(healthRequest(original), { limit: 20, request_id: original.requestId, expected_library: original.libraryId });
  assert.deepEqual(originalHealthRun(run, original), run);
  for (const changed of [{ ...run, request_id: "other" }, { ...run, params: { ...run.params, limit: 50 } },
    { ...run, params: { ...run.params, ids: [1] } }, { ...run, params: { ...run.params, expected_library: "b".repeat(64) } }]) {
    assert.equal(originalHealthRun(changed, original), null);
  }
  assert.equal([...values.values()].join("").includes("synthetic-private"), false);
});

test("switching a library retains other originals and each window owns a separate key", () => {
  install(); saveHealthOperation(original); saveHealthOperation({ ...original, requestId: "other", libraryId: "b".repeat(64) });
  assert.deepEqual(loadHealthOperations(original.libraryId), [original]);
  assert.equal(loadHealthOperations().length, 2);
  clearHealthOperation(original.requestId); assert.equal(loadHealthOperations()[0].requestId, "other");
});

test("the bounded store refuses to evict or change an unresolved original", () => {
  install(); for (let index = 0; index < 8; index++) saveHealthOperation({ ...original, requestId: `health-${index}`, createdAt: index });
  assert.throws(() => saveHealthOperation({ ...original, requestId: "ninth" }), /Finish/);
  assert.throws(() => saveHealthOperation({ ...original, requestId: "health-0", createdAt: 0, limit: 50 }), /unchanged/);
  assert.equal(loadHealthOperations().length, 8);
});

test("malformed storage and malformed counters cannot become a fresh request or a rendered result", () => {
  install(); values.set(healthStoragePrefix + "wrong-id", JSON.stringify(original));
  assert.throws(() => loadHealthOperations(), /could not be read/);
  assert.throws(() => saveHealthOperation({ ...original, requestId: "new" }), /could not be read/);
  assert.equal(values.size, 1);
  assert.equal(validHealthCounts({ alive: null }), false); assert.equal(validHealthCounts({ alive: -1 }), false);
  for (const invalid of [{ ...run, targets_count: "18" }, { ...run, report: {} }, { ...run, params: null },
    { ...run, state: "done" }, { ...run, state: "done", report: { ...report, errors: null } }]) assert.equal(validHealthRun(invalid), false);
  assert.equal(validHealthRun({ ...run, state: "done", finished_at: 102, report }), true);
});
