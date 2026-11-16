import { type CompleteBody, normalizeEndpoint, type Settings } from "./api.ts";

export interface PendingDelivery {
  version: 1;
  owner: string;
  body: CompleteBody;
  savedAt: number;
  rejected?: boolean;
  error?: string;
}

export const FETCH_DELIVERIES_KEY = "fetch-deliveries";
const KEY = FETCH_DELIVERIES_KEY;
const LIMIT = 6;

export async function ownerKey(settings: Settings): Promise<string> {
  const raw = new TextEncoder().encode(JSON.stringify([normalizeEndpoint(settings.endpoint), settings.token]));
  const digest = await crypto.subtle.digest("SHA-256", raw);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
}

export async function readDeliveries(): Promise<PendingDelivery[]> {
  const stored = (await chrome.storage.local.get({ [KEY]: [] }))[KEY] as unknown;
  if (!Array.isArray(stored) || stored.length > LIMIT || stored.some((item) => {
    const body = item?.body;
    return item?.version !== 1 || typeof item.owner !== "string" || !Number.isFinite(item.savedAt)
      || !body || !Number.isSafeInteger(body.bookmark_id) || body.bookmark_id <= 0
      || typeof body.lease_id !== "string" || !body.lease_id || typeof body.source_url !== "string"
      || !/^https?:\/\//i.test(body.source_url) || typeof body.request_id !== "string"
      || !/^[a-zA-Z0-9_.-]{1,128}$/.test(body.request_id)
      || (body.body !== undefined && (typeof body.body !== "string" || body.body.length > 200_000))
      || (body.error !== undefined && typeof body.error !== "string");
  })) throw new Error("Pending browser results could not be read; open settings to review them");
  return stored as PendingDelivery[];
}

export async function putDelivery(delivery: PendingDelivery): Promise<void> {
  const all = await readDeliveries();
  const index = all.findIndex((item) => item.body.request_id === delivery.body.request_id);
  if (index < 0) {
    if (all.length >= LIMIT) throw new Error("Finish pending browser results before reading more pages");
    all.push(delivery);
  } else {
    if (all[index].owner !== delivery.owner || JSON.stringify(all[index].body) !== JSON.stringify(delivery.body)) {
      throw new Error("The original browser result changed; keep it for review");
    }
    all[index] = delivery;
  }
  await chrome.storage.local.set({ [KEY]: all });
}

export async function removeDelivery(requestId: string): Promise<void> {
  await chrome.storage.local.set({ [KEY]: (await readDeliveries()).filter((item) => item.body.request_id !== requestId) });
}

