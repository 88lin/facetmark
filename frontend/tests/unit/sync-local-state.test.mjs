import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../../src/sync-local-state.ts", import.meta.url), "utf8");
const js = ts.transpileModule(source, { fileName: "sync-local-state.ts", compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { loadSyncOperations, saveSyncOperation, clearSyncOperation, syncRequest, loadSyncWorkspace, saveSyncWorkspace,
  validSyncStatus, validSyncPreview, validSyncReceipt, syncStoragePrefix, syncWorkspaceKey } =
  await import("data:text/javascript;base64," + Buffer.from(js).toString("base64"));
const descriptor = Object.getOwnPropertyDescriptor(globalThis, "localStorage"), values = new Map();
const install = () => Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
  get length() { return values.size; }, key: index => [...values.keys()][index] ?? null,
  getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key),
} });
afterEach(() => { values.clear(); if (descriptor) Object.defineProperty(globalThis, "localStorage", descriptor); else delete globalThis.localStorage; });
const sid = "b7f4abbc-fd77-4c02-9a75-e2ded81105c5", cid = "6ee91c2a-c876-442d-8f21-e2ded81105c5";
const original = { version: 1, requestId: "original-sync", createdAt: 10, confirmed: false,
  change: { kind: "apply", previewId: "original-preview", resolutions: { [sid]: `remote:${cid}` } } };
const config = { folder: "C:\\synthetic\\shared", enabled: true, auto_sync: false, poll_seconds: 60 };
const counts = { upload_new: 1, upload_update: 0, upload_delete: 0, download_new: 0, download_update: 0, download_delete: 0, unchanged: 0, conflicts: 0 };
const status = { ...config, configured: true, needs_review: true, last_error: "", pending_conflicts: 0,
  last_sync_at: null, last_sync_id: null, config_revision: "a".repeat(64), pending_operations: [] };
const applied = { request_id: original.requestId, accepted: true, complete: true, error: "", folder: config.folder,
  counts, backup_path: null, published_commit: cid, status };
const receipt = { request_id: original.requestId, action: "apply", state: "done", result: applied, current_status: status };

test("refresh retains exact conflict choices and separate windows keep independent original operations", () => {
  install(); const first = structuredClone(original);
  assert.equal(saveSyncOperation(first), true);
  first.change.resolutions[sid] = "delete"; first.change.previewId = "later-preview";
  const second = { ...original, requestId: "other-window", createdAt: 20, change: { kind: "configure", values: { ...config, expected_revision: status.config_revision } } };
  assert.equal(saveSyncOperation(second), true);
  assert.deepEqual(loadSyncOperations(), [original, second]);
  assert.deepEqual(syncRequest(loadSyncOperations()[0]), { path: "/admin/library/sync/apply",
    body: { request_id: original.requestId, preview_id: original.change.previewId, resolutions: original.change.resolutions } });
  assert.equal(syncRequest(second).body.expected_revision, status.config_revision);
  assert.equal(clearSyncOperation(second.requestId), true);
  assert.deepEqual(loadSyncOperations(), [original]);
});

test("local drafts preserve rapid input, preview selection and the configuration revision without storing credentials", () => {
  install();
  const workspace = { version: 1, draft: { ...config, folder: "C:\\synthetic\\未保存路径", poll_seconds: "invalid draft" },
    configRevision: status.config_revision, previewId: original.change.previewId, resolutions: original.change.resolutions, confirmed: true };
  assert.equal(saveSyncWorkspace({ ...workspace, api_key: "PRIVATE_KEY", body_text: "PRIVATE_BODY" }), true);
  assert.deepEqual(loadSyncWorkspace(), workspace);
  assert.equal(values.get(syncWorkspaceKey).includes("PRIVATE_"), false);
  assert.equal(saveSyncOperation({ ...original, api_key: "PRIVATE_KEY", path: "/admin/token/rotate",
    change: { ...original.change, content: "PRIVATE_BODY" } }), true);
  assert.deepEqual(loadSyncOperations(), [original]);
  assert.equal(values.get(syncStoragePrefix + original.requestId).includes("PRIVATE_"), false);
});

test("malformed operations and unsafe conflict choices cannot become writes or replace their records", () => {
  install();
  for (const value of [{ ...original, version: 2 }, { ...original, confirmed: true, rejected: true },
    { ...original, change: { ...original.change, resolutions: { [sid]: "automatic" } } },
    { ...original, change: { kind: "configure", values: { ...config, poll_seconds: 0 } } },
    { ...original, change: { kind: "configure", values: { ...config, expected_revision: "wrong" } } },
    { ...original, change: { kind: "apply", previewId: "../another", resolutions: {} } }]) assert.equal(saveSyncOperation(value), false);
  values.set(syncStoragePrefix + "wrong-key", JSON.stringify(original));
  values.set(syncStoragePrefix + "unreadable", "not-json");
  values.set(syncStoragePrefix + "oversized", " ".repeat(3000001));
  assert.deepEqual(loadSyncOperations(), []);
  assert.equal(values.size, 3);
});

test("the bounded store retains confirmed and uncertain operations and never evicts an unresolved delivery", () => {
  install();
  for (let index = 0; index < 8; index++) assert.equal(saveSyncOperation({ ...original, requestId: `operation-${index}`, createdAt: index }), true);
  assert.equal(saveSyncOperation({ ...original, requestId: "ninth-operation" }), false);
  assert.equal(saveSyncOperation({ ...original, requestId: "operation-0", createdAt: 0, confirmed: true }), true);
  assert.equal(loadSyncOperations().length, 8);
  assert.equal(loadSyncOperations()[0].confirmed, true);
});

test("a damaged success response cannot confirm a synchronization or clear its original request", () => {
  assert.equal(validSyncReceipt(receipt, original.requestId, "apply"), true);
  for (const changed of [{ ...receipt, request_id: "other-operation" }, { ...receipt, action: "configure" },
    { ...receipt, result: { ...applied, accepted: "true" } }, { ...receipt, result: { ...applied, counts: {} } },
    { ...receipt, result: { ...applied, counts: { ...counts, upload_new: -1 } } },
    { ...receipt, result: { ...applied, complete: false } }, { ...receipt, result: { ...applied, backup_path: {} } },
    { ...receipt, result: { ...applied, published_commit: "different-id" } },
    { ...receipt, current_status: { ...status, config_revision: "bad-revision" } },
    { ...receipt, current_status: { ...status, last_sync_at: NaN } }]) assert.equal(validSyncReceipt(changed, original.requestId, "apply"), false);
});

test("accepted pending delivery and saved configuration receipts have distinct valid states", () => {
  const pending = { ...receipt, state: "pending", result: { ...applied, complete: false, error: "Shared drive is offline" } };
  assert.equal(validSyncReceipt(pending, original.requestId, "apply"), true);
  assert.equal(validSyncReceipt({ ...pending, state: "done" }, original.requestId, "apply"), false);
  assert.equal(validSyncReceipt({ request_id: "configure-once", action: "configure", state: "done", result: status, current_status: status }, "configure-once", "configure"), true);
  assert.equal(validSyncStatus({ ...status, pending_operations: [{ request_id: "pending-once", created_at: 10, folder: config.folder, counts, backup_path: null, error: "offline" }] }), true);
  assert.equal(validSyncStatus({ ...status, pending_operations: [{ request_id: "pending-once", created_at: 10, folder: config.folder, counts: {}, backup_path: null, error: "offline" }] }), false);
});

test("server-only accepted results can survive a refresh failure without manufacturing a new write", () => {
  install();
  const accepted = { ...original, confirmed: true, change: { kind: "receipt", action: "apply" } };
  assert.equal(saveSyncOperation(accepted), true);
  assert.deepEqual(loadSyncOperations(), [accepted]);
  assert.equal(syncRequest(loadSyncOperations()[0]), null);
  assert.equal(saveSyncOperation({ ...accepted, confirmed: false }), false);
});

test("preview recovery verifies its original ID, complete metadata and conflict versions", () => {
  const record = { url: "https://synthetic.example/read", title: "Read me", folder: "Reading", tags: [], date_added: null };
  const preview = { preview_id: "original-preview", expires_at: 1700000000, counts: { ...counts, conflicts: 1 }, changes: [], excluded_karakeep: 0, excluded_unsupported: 0, stale: false,
    conflicts: [{ id: sid, reason: "local_and_remote_changed", local: record, remote: null, remote_versions: [{ choice: `remote:${cid}`, record }] }] };
  assert.equal(validSyncPreview(preview, "original-preview"), true);
  assert.equal(validSyncPreview(preview, "different-preview"), false);
  assert.equal(validSyncPreview({ ...preview, conflicts: [{ ...preview.conflicts[0], local: { ...record, tags: null } }] }), false);
  assert.equal(validSyncPreview({ ...preview, conflicts: [{ ...preview.conflicts[0], remote_versions: [{ choice: "automatic", record }] }] }), false);
  assert.equal(validSyncPreview({ ...preview, counts: { ...counts, conflicts: Infinity } }), false);
});

test("known refusals retain content while acceptance is unresolved and storage failure is explicit", () => {
  install();
  assert.equal(saveSyncOperation({ ...original, refused: true, rejected: false }), true);
  assert.equal(loadSyncOperations()[0].refused, true);
  assert.equal(loadSyncOperations()[0].rejected, false);
  assert.equal(saveSyncOperation({ ...original, refused: true, confirmed: true }), false);
  Object.defineProperty(globalThis, "localStorage", { configurable: true, get() { throw new Error("blocked storage"); } });
  assert.deepEqual(loadSyncOperations(), []);
  assert.equal(saveSyncOperation(original), false);
  assert.equal(clearSyncOperation(original.requestId), false);
  assert.equal(saveSyncWorkspace({ version: 1, draft: { ...config, poll_seconds: "60" }, resolutions: {}, confirmed: false }), false);
});
