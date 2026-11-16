import type { CollectionScope } from "./api";

export type BookmarkValues = { url: string; title: string; folder: string; tags: string[] };
export type LibraryChange =
  | { kind: "create"; values: BookmarkValues }
  | { kind: "edit"; bookmarkId: number; values: Partial<BookmarkValues> }
  | { kind: "bulk"; ids: number[]; action: "move" | "tag-add" | "tag-remove" | "delete"; folder?: string; tags?: string[] }
  | { kind: "taxonomy"; kindOfName: "folder" | "tag"; action: "rename" | "delete"; name: string; newName?: string };
export type LibraryOperation = { version: 1; requestId: string; createdAt: number; confirmed: boolean; change: LibraryChange; draft?: BookmarkValues };
export type LibraryReceipt = { request_id: string; action: string; result: { bookmark_id?: number; ids?: number[]; deleted?: number } };
export const libraryStoragePrefix = "fm-library-operation:";
const object = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === "object" && !Array.isArray(value));
const identity = (value: unknown): value is string => typeof value === "string" && /^[a-zA-Z0-9_.-]{1,128}$/.test(value);
const id = (value: unknown): value is number => typeof value === "number" && Number.isSafeInteger(value) && value > 0;
const text = (value: unknown, max: number): value is string => typeof value === "string" && value.length <= max && !value.includes("\0");
const tagList = (value: unknown): value is string[] => Array.isArray(value) && value.length <= 100
  && value.every(tag => text(tag, 128) && Boolean(tag.trim()));

function bookmarkValues(value: unknown, partial: boolean): Partial<BookmarkValues> | null {
  if (!object(value)) return null;
  const result: Partial<BookmarkValues> = {};
  for (const key of ["url", "title", "folder", "tags"] as const) {
    if (!Object.hasOwn(value, key)) { if (partial) continue; return null; }
    const field = value[key];
    if (key === "tags") { if (!tagList(field)) return null; result.tags = [...field]; }
    else { if (!text(field, key === "url" ? 8192 : 2048) || (key === "url" && !field.trim())) return null; result[key] = field; }
  }
  return Object.keys(result).length ? result : null;
}

function normalizeChange(value: unknown): LibraryChange | null {
  if (!object(value)) return null;
  if (value.kind === "create" || value.kind === "edit") {
    const values = bookmarkValues(value.values, value.kind === "edit");
    if (!values) return null;
    if (value.kind === "create") return { kind: "create", values: values as BookmarkValues };
    return id(value.bookmarkId) ? { kind: "edit", bookmarkId: value.bookmarkId, values } : null;
  }
  if (value.kind === "bulk" && Array.isArray(value.ids) && value.ids.length > 0 && value.ids.length <= 1000 && value.ids.every(id)) {
    const ids = [...new Set(value.ids)] as number[];
    if (value.action === "delete") return { kind: "bulk", ids, action: "delete" };
    if (value.action === "move" && text(value.folder, 2048)) return { kind: "bulk", ids, action: "move", folder: value.folder };
    if ((value.action === "tag-add" || value.action === "tag-remove") && tagList(value.tags) && value.tags.length)
      return { kind: "bulk", ids, action: value.action, tags: [...value.tags] };
  }
  if (value.kind === "taxonomy" && ["folder", "tag"].includes(String(value.kindOfName))
    && text(value.name, value.kindOfName === "tag" ? 128 : 2048) && value.name.trim()) {
    const kindOfName = value.kindOfName as "folder" | "tag", name = value.name;
    if (value.action === "delete") return { kind: "taxonomy", kindOfName, action: "delete", name };
    if (value.action === "rename" && text(value.newName, kindOfName === "tag" ? 128 : 2048) && value.newName.trim())
      return { kind: "taxonomy", kindOfName, action: "rename", name, newName: value.newName };
  }
  return null;
}

function normalized(value: unknown): LibraryOperation | null {
  if (!object(value) || value.version !== 1 || !identity(value.requestId) || typeof value.confirmed !== "boolean"
    || typeof value.createdAt !== "number" || !Number.isSafeInteger(value.createdAt) || value.createdAt < 0) return null;
  const change = normalizeChange(value.change);
  if (!change) return null;
  const draft = change.kind === "edit" && value.draft !== undefined ? bookmarkValues(value.draft, false) : undefined;
  if (change.kind === "edit" && value.draft !== undefined && !draft) return null;
  return { version: 1, requestId: value.requestId, createdAt: value.createdAt, confirmed: value.confirmed, change,
    ...(draft ? { draft: draft as BookmarkValues } : {}) };
}

export function loadLibraryOperations(): LibraryOperation[] {
  try {
    const result: LibraryOperation[] = [];
    for (let index = 0; index < Math.min(localStorage.length, 10000); index++) {
      const key = localStorage.key(index);
      if (!key?.startsWith(libraryStoragePrefix)) continue;
      const raw = localStorage.getItem(key);
      if (!raw || raw.length > 64000) continue;
      try {
        const value = normalized(JSON.parse(raw));
        if (value && key === libraryStoragePrefix + value.requestId) result.push(value);
      } catch { /* Leave a damaged record untouched; it cannot become a write. */ }
    }
    return result.sort((a, b) => b.createdAt - a.createdAt).slice(0, 24);
  } catch { return []; }
}

export function saveLibraryOperation(value: LibraryOperation): boolean {
  try {
    const clean = normalized(value);
    if (!clean) return false;
    // Each request has its own key, so another window cannot replace this
    // operation with a different edit. Reading this record never sends it.
    localStorage.setItem(libraryStoragePrefix + clean.requestId, JSON.stringify(clean));
    return true;
  } catch { return false; }
}

export function clearLibraryOperation(requestId: string): boolean {
  try { if (!identity(requestId)) return false; localStorage.removeItem(libraryStoragePrefix + requestId); return true; }
  catch { return false; }
}

export function libraryRequest(value: LibraryOperation) {
  const change = value.change, request_id = value.requestId;
  if (change.kind === "create") return { path: "/admin/library/bookmarks", method: "POST", action: "create", body: { ...change.values, request_id } };
  if (change.kind === "edit") return { path: "/admin/library/bookmarks/" + change.bookmarkId, method: "PATCH",
    action: "edit:" + change.bookmarkId, body: { ...change.values, request_id } };
  if (change.kind === "bulk") return { path: "/admin/library/bulk", method: "POST", action: "bulk",
    body: { ids: [...change.ids], action: change.action, ...(change.folder !== undefined ? { folder: change.folder } : {}),
      ...(change.tags ? { tags: [...change.tags] } : {}), request_id } };
  return { path: "/admin/library/taxonomy", method: "POST", action: "taxonomy",
    body: { kind: change.kindOfName, action: change.action, name: change.name,
      ...(change.newName !== undefined ? { new_name: change.newName } : {}), request_id } };
}

export type ExportContext = { current: CollectionScope; selectedIds: number[]; pageIds: number[];
  allMatching: boolean; selectedCount: number; semantic: boolean };
export function exportRequest(context: ExportContext, scope: string, format: string) {
  if (scope === "selected") return context.allMatching ? { format, scope: structuredClone(context.current) }
    : { format, ids: [...context.selectedIds] };
  if (scope === "page") return { format, ids: [...context.pageIds] };
  if (scope === "filtered") return { format, scope: structuredClone(context.current) };
  return { format, scope: {} };
}
