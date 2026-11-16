import type { Language } from "./locale";
import type { ChatLaunch } from "./chat-types";

export type ChatOperation = {
  id: string; originKey: string; requestId: string; mode: "send" | "retry" | "regenerate";
  text: string; language: Language; profileId: string; created: boolean; confirmed: boolean; rejected?: boolean;
  creation?: { id: string; request_id: string; title: string; bookmark_ids: number[]; profile_id: string };
};
export type ChatLocalState = {
  version: 1; drafts: Record<string, string>; connections: Record<string, string>;
  operations: Record<string, ChatOperation>;
  scope: ChatLaunch;
};
const storageKey = "fm-chat-drafts";
const identity = (value: unknown): value is string => typeof value === "string" && /^[a-zA-Z0-9_-]{1,64}$/.test(value);
const key = (value: string) => identity(value) || /^draft:\d{1,17}$/.test(value);
const object = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === "object" && !Array.isArray(value));
const requestId = (value: unknown): value is string => typeof value === "string" && /^[\w.-]{1,128}$/.test(value);

function validScope(value: unknown): value is ChatLaunch {
  return object(value) && typeof value.nonce === "number" && Number.isSafeInteger(value.nonce) && value.nonce >= 0
    && Array.isArray(value.bookmark_ids) && value.bookmark_ids.length <= 12
    && value.bookmark_ids.every(id => Number.isSafeInteger(id) && id > 0)
    && (value.title === undefined || (typeof value.title === "string" && value.title.length <= 500));
}

function validOperation(value: unknown): value is ChatOperation {
  if (!object(value) || !identity(value.id) || typeof value.originKey !== "string" || !key(value.originKey)
    || !requestId(value.requestId) || !["send", "retry", "regenerate"].includes(String(value.mode))
    || typeof value.text !== "string" || value.text.length > 4000
    || !["zh", "en"].includes(String(value.language)) || typeof value.profileId !== "string"
    || (value.profileId !== "" && !identity(value.profileId))
    || typeof value.created !== "boolean" || typeof value.confirmed !== "boolean"
    || (value.rejected !== undefined && typeof value.rejected !== "boolean")) return false;
  if (!value.creation) return value.created;
  const creation = value.creation;
  return object(creation) && identity(creation.id) && requestId(creation.request_id)
    && typeof creation.title === "string" && creation.title.length <= 120
    && Array.isArray(creation.bookmark_ids) && creation.bookmark_ids.length <= 12
    && creation.bookmark_ids.every(id => Number.isSafeInteger(id) && id > 0)
    && creation.profile_id === value.profileId;
}

export function emptyChatLocalState(): ChatLocalState {
  return { version: 1, drafts: {}, connections: {}, operations: {}, scope: { nonce: 0, bookmark_ids: [] } };
}

function normalized(value: Record<string, unknown>): ChatLocalState {
  const scope = value.scope;
  return { version: 1,
    scope: validScope(scope) ? { nonce: scope.nonce, bookmark_ids: [...scope.bookmark_ids],
      ...(scope.title !== undefined ? { title: scope.title } : {}) } : { nonce: 0, bookmark_ids: [] },
    drafts: Object.fromEntries(Object.entries(object(value.drafts) ? value.drafts : {}).filter(([id, text]) =>
      key(id) && typeof text === "string" && text.length <= 4000).slice(-24)) as Record<string, string>,
    connections: Object.fromEntries(Object.entries(object(value.connections) ? value.connections : {}).filter(([id, connection]) =>
      key(id) && (connection === "" || identity(connection))).slice(-24)) as Record<string, string>,
    operations: Object.fromEntries(Object.entries(object(value.operations) ? value.operations : {}).filter(([id, operation]) =>
      key(id) && validOperation(operation) && (id === operation.id || id === operation.originKey)).slice(-24)
      .map(([id, item]) => {
        const operation = item as ChatOperation;
        return [id, { id: operation.id, originKey: operation.originKey, requestId: operation.requestId, mode: operation.mode,
          text: operation.text, language: operation.language, profileId: operation.profileId, created: operation.created,
          confirmed: operation.confirmed, ...(operation.rejected !== undefined ? { rejected: operation.rejected } : {}),
          ...(operation.creation ? { creation: { id: operation.creation.id, request_id: operation.creation.request_id,
            title: operation.creation.title, bookmark_ids: [...operation.creation.bookmark_ids], profile_id: operation.creation.profile_id } } : {}),
        }];
      })) as Record<string, ChatOperation>,
  };
}

export function loadChatLocalState(): ChatLocalState {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw || raw.length > 1_000_000) return emptyChatLocalState();
    const value: unknown = JSON.parse(raw);
    if (!object(value) || value.version !== 1) return emptyChatLocalState();
    return normalized(value);
  } catch { return emptyChatLocalState(); }
}

export function saveChatLocalState(value: ChatLocalState): boolean {
  try {
    // Only the current drafts, connection IDs and unsettled HTTP actions live
    // here. Answers and credentials belong to their existing server stores.
    localStorage.setItem(storageKey, JSON.stringify(normalized(value)));
    return true;
  } catch { return false; }
}
