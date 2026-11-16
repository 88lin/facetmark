import { api, ApiError, loadSettings, normalizeEndpoint, type SaveBody, type SaveResult, type Settings } from "./api.ts";
import { FETCH_DELIVERIES_KEY, ownerKey } from "./delivery.ts";

export interface PendingSave {
  version: 1;
  owner: string;
  endpoint: string;
  body: SaveBody & { request_id: string };
  savedAt: number;
  error?: string;
}

export const SAVE_DELIVERIES_KEY = "save-deliveries";
const KEY = SAVE_DELIVERIES_KEY;
let saving = false;

export async function readSaves(): Promise<PendingSave[]> {
  const stored = (await chrome.storage.local.get({ [KEY]: [] }))[KEY] as unknown;
  if (!Array.isArray(stored) || stored.length > 24 || stored.some((value) => value?.version !== 1
    || typeof value.owner !== "string" || typeof value.endpoint !== "string" || !Number.isFinite(value.savedAt)
    || !value.body || typeof value.body.url !== "string" || !/^https?:\/\//i.test(value.body.url)
    || typeof value.body.title !== "string" || typeof value.body.request_id !== "string"
    || !/^[a-zA-Z0-9_.-]{1,128}$/.test(value.body.request_id)
    || (value.body.folder !== undefined && typeof value.body.folder !== "string")
    || (value.body.tags !== undefined && (!Array.isArray(value.body.tags)
      || value.body.tags.some((tag: unknown) => typeof tag !== "string")))
    || (value.error !== undefined && typeof value.error !== "string"))) {
    throw new Error("Pending saved pages could not be read; review them in settings");
  }
  return stored as PendingSave[];
}

async function put(value: PendingSave): Promise<void> {
  const all = await readSaves();
  const index = all.findIndex((item) => item.body.request_id === value.body.request_id);
  if (index < 0) {
    if (all.length >= 24) throw new Error("Confirm pending saves before saving another page");
    all.push(value);
  } else {
    if (all[index].owner !== value.owner || JSON.stringify(all[index].body) !== JSON.stringify(value.body)) {
      throw new Error("The original saved-page request changed; keep it for review");
    }
    all[index] = value;
  }
  await chrome.storage.local.set({ [KEY]: all });
}

async function remove(requestId: string): Promise<void> {
  await chrome.storage.local.set({ [KEY]: (await readSaves()).filter((item) => item.body.request_id !== requestId) });
}

function confirmedResult(action: string, value: Record<string, unknown>): SaveResult {
  if (action !== "save" || !Number.isSafeInteger(value.bookmark_id) || Number(value.bookmark_id) <= 0
    || (value.created !== undefined && typeof value.created !== "boolean")) {
    throw new ApiError("The original page save could not be confirmed", 200, "invalid");
  }
  return value as unknown as SaveResult;
}

async function deliver(pending: PendingSave, settings: Settings, recovering: boolean): Promise<SaveResult> {
  try {
    if (recovering) {
      try {
        const receipt = await api.receipt(pending.body.request_id, { settings });
        const result = confirmedResult(receipt.action, receipt.result);
        await remove(pending.body.request_id);
        return result;
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404) throw error;
      }
    }
    const result = await api.save(pending.body, { settings });
    await remove(pending.body.request_id);
    return result;
  } catch (error) {
    await put({ ...pending, error: (error instanceof Error ? error.message : String(error)).slice(0, 800) });
    throw error;
  }
}

export async function savePage(input: SaveBody): Promise<SaveResult> {
  if (saving) throw new Error("Another page save is being confirmed; wait and retry");
  saving = true;
  try {
    // Freeze the complete payload before storage, hashing or any other await.
    const snapshot = structuredClone(input);
    if (!snapshot || typeof snapshot.url !== "string" || typeof snapshot.title !== "string"
      || (snapshot.folder !== undefined && typeof snapshot.folder !== "string")
      || (snapshot.tags !== undefined && (!Array.isArray(snapshot.tags) || snapshot.tags.some((tag) => typeof tag !== "string")))) {
      throw new Error("This page could not be read; open an http:// or https:// page and retry");
    }
    const url = new URL(snapshot.url);
    if (!["http:", "https:"].includes(url.protocol)) throw new Error("This page cannot be saved; open an http:// or https:// page");
    const settings = await loadSettings();
    const owner = await ownerKey(settings);
    let pending = (await readSaves()).find((item) => item.owner === owner && item.body.url === snapshot.url);
    const recovering = !!pending;
    if (!pending) {
      pending = { version: 1, owner, endpoint: normalizeEndpoint(settings.endpoint),
        body: { ...snapshot, request_id: `ext-save-${crypto.randomUUID()}` }, savedAt: Date.now() };
      await put(pending);
    }
    return await deliver(pending, settings, recovering);
  } finally { saving = false; }
}

/** An explicit settings-page retry can only send the original stored payload. */
export async function retrySave(requestId: string): Promise<SaveResult> {
  if (saving) throw new Error("Wait for the current page save before retrying its original request");
  saving = true;
  try {
    const settings = await loadSettings();
    const owner = await ownerKey(settings);
    const pending = (await readSaves()).find((item) => item.body.request_id === requestId);
    if (!pending) throw new Error("This original save is no longer pending; refresh the saved results");
    if (pending.owner !== owner) throw new Error("Use the original saved connection before retrying this page");
    return await deliver(pending, settings, true);
  } finally { saving = false; }
}

/** Read only: confirming an accepted result never sends another save. */
export async function confirmSaves(): Promise<number> {
  if (saving) throw new Error("Wait for the current page save before confirming saved results");
  saving = true;
  let confirmed = 0;
  try {
    const settings = await loadSettings();
    const owner = await ownerKey(settings);
    for (const pending of await readSaves()) {
      if (pending.owner !== owner) continue;
      try {
        const saved = await api.receipt(pending.body.request_id, { settings });
        confirmedResult(saved.action, saved.result);
        await remove(pending.body.request_id);
        confirmed += 1;
      } catch (error) { if (!(error instanceof ApiError) || error.status !== 404) throw error; }
    }
    return confirmed;
  } finally { saving = false; }
}

export async function clearPendingResults(): Promise<void> {
  if (saving) throw new Error("Wait for the current page save before clearing pending results");
  saving = true;
  try {
    // One storage operation after both locks are held, including corrupt entries.
    await chrome.storage.local.remove([FETCH_DELIVERIES_KEY, SAVE_DELIVERIES_KEY]);
  } finally { saving = false; }
}
