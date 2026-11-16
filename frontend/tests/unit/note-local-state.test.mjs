import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";
const source = await readFile(new URL("../../src/note-local-state.ts", import.meta.url), "utf8");
const js = ts.transpileModule(source, { fileName: "note-local-state.ts", compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { savedNote, noteDraft, readNoteDraft, writeNoteDraft, removeNoteDraft, noteStoragePrefix } =
  await import("data:text/javascript;base64," + Buffer.from(js).toString("base64"));
const store = () => {
  const values = new Map();
  return { get length() { return values.size; }, key: index => [...values.keys()][index] ?? null,
    getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
};
const original = { version: 1, bookmarkId: 42, url: "https://notes.example/page", draft: "  原来的笔记\n  keep spaces\n", baseRevision: 3,
  pending: { requestId: "original-note-save", note: "  原来的笔记\n  keep spaces\n", baseRevision: 3 } };
test("refresh retains exact note and version and cannot attach it to another page", () => {
  const storage = store();
  assert.equal(writeNoteDraft(storage, original), true);
  assert.deepEqual(readNoteDraft(storage, 42, original.url), original);
  assert.equal(readNoteDraft(storage, 42, "https://notes.example/another"), null);
  assert.equal(readNoteDraft(storage, 43, original.url), null);
  assert.equal(removeNoteDraft(storage, 42), true);
  assert.equal(readNoteDraft(storage, 42, original.url), null);
});
test("damaged and unsupported drafts cannot turn into a save and unrelated secrets are excluded", () => {
  for (const value of [{ ...original, version: 2 }, { ...original, baseRevision: true }, { ...original, draft: "x".repeat(60_001) },
    { ...original, pending: { ...original.pending, note: "a different request" } }, { ...original, draft: "nul\0text" }]) assert.equal(noteDraft(value), null);
  assert.deepEqual(noteDraft({ ...original, token: "synthetic-secret", answers: ["private-answer"] }), original);
  const storage = store(); storage.setItem(noteStoragePrefix + "42", "not JSON");
  assert.equal(readNoteDraft(storage, 42, original.url), null);
  assert.equal(storage.getItem(noteStoragePrefix + "42"), "not JSON");
});
test("capacity and storage failures preserve unfinished drafts instead of evicting them", () => {
  const storage = store();
  for (let i = 1; i <= 24; i++) assert.equal(writeNoteDraft(storage, { ...original, bookmarkId: i }), true);
  assert.equal(writeNoteDraft(storage, original), false);
  assert.deepEqual(readNoteDraft(storage, 1, original.url), { ...original, bookmarkId: 1 });
  assert.equal(writeNoteDraft({ ...storage, setItem: () => { throw new Error("quota"); } }, original), false);
});
test("a malformed save result is never treated as an accepted note", () => {
  const result = { bookmark_id: 42, note: original.draft, revision: 4, updated_at: 10, legacy_text: "" };
  assert.deepEqual(savedNote(result), result);
  for (const value of [{ ...result, note: null }, { ...result, revision: true }, { ...result, bookmark_id: 0 }, { ...result, legacy_text: undefined }]) assert.equal(savedNote(value), null);
});
