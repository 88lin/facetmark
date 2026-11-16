export type McpStatus = {
  revision: string; enabled: boolean; configured: boolean; running: boolean; transport_ready: boolean;
  status: "disabled" | "ready" | "starting" | "unconfigured"; error: string;
  endpoint: string; token: string; client_config: Record<string, unknown>; codex_config?: string;
  locked: { enabled: boolean; token: boolean }; last_request_at: number | null;
  probe?: { ok: boolean; server?: string; tools?: number; resources?: number; templates?: number; error?: string } | null;
};
export type McpChange = { enabled?: boolean; rotate_token?: true };
export type McpOperation = {
  version: 1; requestId: string; createdAt: number; expectedRevision: string; change: McpChange;
};
export const mcpStoragePrefix = "fm-mcp-operation:";
const digest = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const id = (value: unknown): value is string => typeof value === "string" && /^[a-zA-Z0-9_.-]{1,128}$/.test(value);
const record = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === "object" && !Array.isArray(value));

function original(value: unknown): McpOperation {
  if (!record(value) || value.version !== 1 || !id(value.requestId) || !digest(value.expectedRevision)
    || !Number.isSafeInteger(value.createdAt) || Number(value.createdAt) < 0 || !record(value.change)
    || (value.change.enabled !== undefined && typeof value.change.enabled !== "boolean")
    || (value.change.rotate_token !== undefined && value.change.rotate_token !== true)
    || (value.change.enabled === undefined && value.change.rotate_token !== true)) {
    throw new Error("The saved original MCP change could not be read");
  }
  const change: McpChange = {};
  if (typeof value.change.enabled === "boolean") change.enabled = value.change.enabled;
  if (value.change.rotate_token === true) change.rotate_token = true;
  return { version: 1, requestId: value.requestId, createdAt: Number(value.createdAt), expectedRevision: value.expectedRevision, change };
}

export function loadMcpOperations(): McpOperation[] {
  const found: McpOperation[] = [];
  for (let index = 0; index < localStorage.length; index++) {
    const key = localStorage.key(index);
    if (!key?.startsWith(mcpStoragePrefix)) continue;
    const raw = localStorage.getItem(key);
    if (raw === null || raw.length > 2048) throw new Error("The saved original MCP change could not be read");
    const value = original(JSON.parse(raw));
    if (key !== mcpStoragePrefix + value.requestId) throw new Error("The saved original MCP change could not be read");
    found.push(value);
  }
  return found.sort((a, b) => a.createdAt - b.createdAt || a.requestId.localeCompare(b.requestId));
}

export function saveMcpOperation(value: McpOperation): void {
  const safe = original(value);
  const current = loadMcpOperations();
  const existing = current.find(item => item.requestId === safe.requestId);
  if (existing && JSON.stringify(existing) !== JSON.stringify(safe)) throw new Error("Keep the original MCP change unchanged");
  if (!existing && current.length >= 8) throw new Error("Finish saved MCP changes before making another change");
  localStorage.setItem(mcpStoragePrefix + safe.requestId, JSON.stringify(safe));
}

export function clearMcpOperation(requestId: string): void {
  if (!id(requestId)) throw new Error("Invalid original MCP request");
  localStorage.removeItem(mcpStoragePrefix + requestId);
}

export function mcpRequest(value: McpOperation) {
  const safe = original(value);
  return { ...safe.change, request_id: safe.requestId, expected_revision: safe.expectedRevision };
}

export function validMcpStatus(value: unknown): value is McpStatus {
  if (!record(value) || !digest(value.revision) || !["disabled", "ready", "starting", "unconfigured"].includes(String(value.status))
    || !["enabled", "configured", "running", "transport_ready"].every(key => typeof value[key] === "boolean")
    || !["error", "endpoint", "token"].every(key => typeof value[key] === "string")
    || !record(value.client_config) || !record(value.locked)
    || typeof value.locked.enabled !== "boolean" || typeof value.locked.token !== "boolean"
    || (value.codex_config !== undefined && typeof value.codex_config !== "string")
    || (value.last_request_at !== null && (!Number.isSafeInteger(value.last_request_at) || Number(value.last_request_at) < 0))) return false;
  if (value.probe !== undefined && value.probe !== null) {
    if (!record(value.probe) || typeof value.probe.ok !== "boolean") return false;
    for (const key of ["tools", "resources", "templates"]) {
      if (value.probe[key] !== undefined && (!Number.isSafeInteger(value.probe[key]) || Number(value.probe[key]) < 0)) return false;
    }
    for (const key of ["server", "error"]) if (value.probe[key] !== undefined && typeof value.probe[key] !== "string") return false;
  }
  return true;
}

export function mcpReceiptStatus(value: unknown, operation: McpOperation): McpStatus | null {
  if (!record(value) || value.request_id !== operation.requestId || value.action !== "configure"
    || !["accepted", "closed"].includes(String(value.state)) || !digest(value.accepted_revision)
    || !Number.isSafeInteger(value.accepted_at) || Number(value.accepted_at) < 0
    || typeof value.superseded !== "boolean" || !validMcpStatus(value.status)
    || value.superseded !== (value.accepted_revision !== value.status.revision)) return null;
  return value.status;
}

export function mcpAcceptedStatus(value: unknown, operation: McpOperation): McpStatus | null {
  if (!record(value)) return null;
  const receipt = value.operation;
  if (!record(receipt) || receipt.state !== "accepted" || !validMcpStatus(value)) return null;
  const status: McpStatus & { operation?: unknown } = { ...value };
  delete status.operation;
  return mcpReceiptStatus({ ...receipt, status }, operation);
}
