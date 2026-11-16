export type SavedNote = { bookmark_id: number; note: string; revision: number; updated_at: number; legacy_text: string };
export type NoteDraft = { version: 1; bookmarkId: number; url: string; draft: string; baseRevision: number;
  pending?: { requestId: string; note: string; baseRevision: number } };
export const noteStoragePrefix = "fm-note-draft:";
const plain = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === "object" && !Array.isArray(value));
const revision = (value: unknown): value is number => typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const text = (value: unknown, maximum: number): value is string => typeof value === "string" && value.length <= maximum && !value.includes("\0");

export function savedNote(value: unknown): SavedNote | null {
  if (!plain(value) || !revision(value.bookmark_id) || value.bookmark_id < 1 || !text(value.note, 60_000)
      || !revision(value.revision) || !revision(value.updated_at) || !text(value.legacy_text, 2_000_000)) return null;
  return { bookmark_id: value.bookmark_id, note: value.note, revision: value.revision,
    updated_at: value.updated_at, legacy_text: value.legacy_text };
}
export function noteDraft(value: unknown): NoteDraft | null {
  if (!plain(value) || value.version !== 1 || !revision(value.bookmarkId) || value.bookmarkId < 1
      || !text(value.url, 8192) || !value.url || !text(value.draft, 60_000) || !revision(value.baseRevision)) return null;
  const result: NoteDraft = { version: 1, bookmarkId: value.bookmarkId, url: value.url, draft: value.draft, baseRevision: value.baseRevision };
  if (value.pending !== undefined) {
    const pending = value.pending;
    if (!plain(pending) || typeof pending.requestId !== "string" || !/^[a-zA-Z0-9_.-]{1,128}$/.test(pending.requestId)
        || !text(pending.note, 60_000) || !revision(pending.baseRevision)
        || pending.note !== result.draft || pending.baseRevision !== result.baseRevision) return null;
    result.pending = { requestId: pending.requestId, note: pending.note, baseRevision: pending.baseRevision };
  }
  return result;
}
export function readNoteDraft(storage: Storage, bookmarkId: number, url: string): NoteDraft | null {
  try {
    const raw = storage.getItem(noteStoragePrefix + bookmarkId);
    if (!raw || raw.length > 800_000) return null;
    const value = noteDraft(JSON.parse(raw));
    return value?.bookmarkId === bookmarkId && value.url === url ? value : null;
  } catch { return null; }
}
export function writeNoteDraft(storage: Storage, value: NoteDraft): boolean {
  const clean = noteDraft(value);
  if (!clean) return false;
  try {
    const key = noteStoragePrefix + value.bookmarkId;
    // Unfinished notes are never displaced by another page's draft.
    if (storage.getItem(key) === null && Array.from({ length: storage.length }, (_, i) => storage.key(i))
      .filter(entry => entry?.startsWith(noteStoragePrefix)).length >= 24) return false;
    storage.setItem(key, JSON.stringify(clean));
    return true;
  } catch { return false; }
}
export function removeNoteDraft(storage: Storage, bookmarkId: number): boolean {
  try { storage.removeItem(noteStoragePrefix + bookmarkId); return true; } catch { return false; }
}
