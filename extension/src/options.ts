import { api, ApiError, loadSettings, normalizeEndpoint, requiredOrigins, type Settings, summarizeQueue } from "./api.ts";
import { ownerKey, readDeliveries } from "./delivery.ts";
import { readSaves } from "./save-delivery.ts";
import { applyI18n, initLangToggle, t } from "./i18n.ts";
import { describeError, queueText, workerRequest } from "./ui.ts";

const $ = <T extends HTMLElement>(selector: string): T => document.querySelector(selector) as T;
const form = $<HTMLFormElement>("#connection-form");
const endpoint = $<HTMLInputElement>("#endpoint");
const token = $<HTMLInputElement>("#token");
const channelB = $<HTMLInputElement>("#channelB");
const paused = $<HTMLInputElement>("#paused");
const state = $("#state");
let saved: Settings | undefined;
let busy = false;
let busyKind = "";
let generation = 0;
let reading: AbortController | undefined;
let noteKey = "";
let noteArgs: (string | number)[] = [];
let lastError: unknown;
let pauseOperation: Promise<void> | undefined;

function setNote(key: string, ...args: (string | number)[]): void {
  noteKey = key;
  noteArgs = args;
  lastError = undefined;
}

function draftChanged(): void {
  $("#connection-draft").hidden = !saved || (endpoint.value === saved.endpoint && token.value === saved.token);
}

function lock(value: boolean, kind = ""): void {
  busy = value;
  busyKind = value ? kind : "";
  if (value) { generation += 1; reading?.abort(); }
  for (const id of ["save", "drain", "confirm", "retry-results", "discard", "reload-settings", "refresh"]) {
    $<HTMLButtonElement>(`#${id}`).disabled = value;
  }
  document.querySelectorAll<HTMLButtonElement>("[data-retry-save]").forEach(button => { button.disabled = value || button.dataset.otherConnection === "true"; });
  endpoint.disabled = token.disabled = channelB.disabled = value;
  paused.disabled = value && kind !== "drain";
  form.setAttribute("aria-busy", String(value));
}

function showError(error: unknown): void {
  lastError = error;
  state.textContent = [noteKey && t(noteKey, ...noteArgs), describeError(error)].filter(Boolean).join(" · ");
  state.className = "connection-status bad";
  if (error instanceof ApiError && error.code === "settings-changed") $("#reload-settings").hidden = false;
}

async function refresh(): Promise<void> {
  const mine = ++generation;
  reading?.abort();
  const controller = reading = new AbortController();
  state.textContent = [noteKey && t(noteKey, ...noteArgs), t("opt.reading")].filter(Boolean).join(" · ");
  state.className = "connection-status";
  try {
    const settings = await loadSettings();
    const health = await api.health({ settings, signal: controller.signal });
    if (!health?.ok || !Number.isSafeInteger(health.bookmarks) || health.bookmarks < 0) throw new ApiError(t("opt.badResponse"), 200, "invalid");
    const queue = summarizeQueue(await api.queueStats({ settings, signal: controller.signal }));
    if (mine !== generation) return;
    const parts = [noteKey && t(noteKey, ...noteArgs), t("opt.connected", health.bookmarks), queueText(queue) || t("opt.queueEmpty")];
    if (settings.paused) parts.push(t("opt.pausedMsg"));
    else if (!settings.channelB) parts.push(t("opt.channelOff"));
    state.textContent = parts.filter(Boolean).join(" · ");
    state.className = "connection-status ok";
    lastError = undefined;
  } catch (error) {
    if (mine === generation && !controller.signal.aborted) showError(error);
  }
  if (mine === generation) await renderPending();
}

async function hydrate(): Promise<void> {
  const settings = saved = await loadSettings();
  endpoint.value = settings.endpoint;
  token.value = settings.token;
  channelB.checked = settings.channelB;
  paused.checked = settings.paused;
  $("#reload-settings").hidden = true;
  draftChanged();
}

async function persist(snapshot: Settings, baseline: Settings): Promise<void> {
  await workerRequest<{ settings: Settings }>({ type: "settings-update", settings: snapshot, expected: baseline });
  saved = snapshot;
  $("#reload-settings").hidden = true;
  draftChanged();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (busy || !saved) return;
  let snapshot: Settings;
  try { snapshot = { ...saved, endpoint: normalizeEndpoint(endpoint.value), token: token.value.trim() }; }
  catch (error) { showError(error); endpoint.focus(); return; }
  const baseline = saved;
  lock(true, "save");
  // Request access in the original gesture, before any asynchronous work.
  const permission = chrome.permissions.request({ origins: requiredOrigins(snapshot.endpoint, snapshot.channelB) });
  const operation = (async () => {
    try {
      if (!await permission) throw new ApiError(t("opt.permissionDenied"), 0, "permission");
      await persist(snapshot, baseline);
      endpoint.value = snapshot.endpoint;
      token.value = snapshot.token;
      draftChanged();
      setNote("opt.saved");
      await refresh();
    } catch (error) { showError(error); }
    finally { lock(false); }
  })();
  void operation;
});

for (const field of [endpoint, token]) field.addEventListener("input", draftChanged);

paused.addEventListener("change", () => {
  if (!saved || (busy && busyKind !== "drain")) return;
  const value = paused.checked;
  const baseline = saved;
  const wasDraining = busyKind === "drain";
  if (!wasDraining) lock(true, "pause");
  paused.disabled = true;
  const operation = (async () => {
    try {
      await persist({ ...baseline, paused: value }, baseline);
      setNote(value ? "opt.pauseSaved" : "opt.resumeSaved");
      if (!wasDraining) await refresh();
    } catch (error) { paused.checked = baseline.paused; showError(error); }
    finally {
      if (!wasDraining) lock(false);
      else paused.disabled = false;
    }
  })();
  pauseOperation = operation;
  void operation.finally(() => { if (pauseOperation === operation) pauseOperation = undefined; });
});

channelB.addEventListener("change", () => {
  if (busy || !saved) return;
  const enabled = channelB.checked;
  const baseline = saved;
  const permission = enabled ? chrome.permissions.request({ origins: requiredOrigins(baseline.endpoint, true) }) : Promise.resolve(true);
  lock(true, "permission");
  void (async () => {
    try {
      if (!await permission) throw new ApiError(t("opt.permissionDenied"), 0, "permission");
      await persist({ ...baseline, channelB: enabled }, baseline);
      setNote(enabled ? "opt.readingEnabled" : "opt.readingDisabled");
      await refresh();
    } catch (error) { channelB.checked = baseline.channelB; showError(error); }
    finally { lock(false); }
  })();
});

function action(kind: string, message: object, notice: (result: Record<string, unknown>) => void): void {
  if (busy) return;
  lock(true, kind);
  state.textContent = t(kind === "drain" ? "opt.fetching" : "opt.reading");
  void (async () => {
    try {
      const result = await workerRequest<Record<string, unknown>>(message);
      if (kind === "drain") await pauseOperation;
      notice(result);
      await refresh();
    } catch (error) { showError(error); await renderPending(); }
    finally { lock(false); }
  })();
}

$("#drain").addEventListener("click", () => action("drain", { type: "drain" }, (result) => {
  if (!Number.isSafeInteger(result.processed) || Number(result.processed) < 0) throw new ApiError(t("opt.badResponse"), 200, "invalid");
  setNote(result.processed ? "opt.fetchFinished" : saved?.paused ? "opt.pauseSaved" : "opt.nothingReady", Number(result.processed));
}));
$("#refresh").addEventListener("click", () => { setNote(""); void refresh(); });
$("#reload-settings").addEventListener("click", () => {
  if (busy || (!$("#connection-draft").hidden && !window.confirm(t("opt.reloadConfirm")))) return;
  lock(true, "load");
  setNote("");
  void hydrate().then(refresh).catch(showError).finally(() => lock(false));
});
$("#confirm").addEventListener("click", () => action("confirm", { type: "confirm-deliveries" }, (result) => {
  if (!Number.isSafeInteger(result.confirmed) || Number(result.confirmed) < 0) throw new ApiError(t("opt.badResponse"), 200, "invalid");
  setNote(result.confirmed ? "opt.confirmed" : "opt.notConfirmed", Number(result.confirmed));
}));
$("#retry-results").addEventListener("click", () => action("recover", { type: "resume-deliveries" }, (result) => {
  if (!Number.isSafeInteger(result.processed) || Number(result.processed) < 0) throw new ApiError(t("opt.badResponse"), 200, "invalid");
  setNote("opt.resultsSent", Number(result.processed));
}));
$("#discard").addEventListener("click", () => {
  if (!busy && window.confirm(t("opt.discardConfirm"))) action("discard", { type: "discard-deliveries" }, () => setNote("opt.discarded"));
});

$("#show-token").addEventListener("click", () => {
  token.type = token.type === "password" ? "text" : "password";
  renderTokenButton();
});
function renderTokenButton(): void {
  $("#show-token").textContent = t(token.type === "password" ? "opt.showToken" : "opt.hideToken");
  $("#show-token").setAttribute("aria-pressed", String(token.type === "text"));
}

let pendingGeneration = 0;
async function renderPending(): Promise<void> {
  const mine = ++pendingGeneration;
  try {
    const [deliveries, saves, settings] = await Promise.all([readDeliveries(), readSaves(), loadSettings()]);
    const owner = await ownerKey(settings);
    if (mine !== pendingGeneration) return;
    const list = $("#pending-results");
    const open = new Set(Array.from(list.querySelectorAll<HTMLDetailsElement>("details[open]"), detail => detail.dataset.requestId));
    list.replaceChildren();
    $("#pending-panel").hidden = !deliveries.length && !saves.length;
    $("#retry-results").hidden = !deliveries.length;
    $("#pending-count").textContent = t("opt.pendingCount", saves.length + deliveries.length);
    for (const item of [...saves, ...deliveries]) {
      const body = item.body;
      const isSave = "url" in body;
      const details = document.createElement("details");
      details.className = "pending-result";
      details.dataset.requestId = body.request_id;
      details.open = open.has(body.request_id);
      const summary = document.createElement("summary");
      summary.textContent = `${t(isSave ? "opt.pendingSave" : "opt.pendingReading")} · ${body.title || (isSave ? body.url : body.source_url)}`;
      details.appendChild(summary);
      const content = document.createElement("div");
      content.className = "pending-content";
      const source = document.createElement("a");
      source.href = isSave ? body.url : body.source_url;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = source.href;
      content.appendChild(source);
      const meta = document.createElement("p");
      meta.className = "pending-meta";
      meta.textContent = t("opt.pendingDate", new Date(item.savedAt).toLocaleString(document.documentElement.lang));
      if ("endpoint" in item) meta.textContent += ` · ${item.endpoint}`;
      if (isSave && body.folder) meta.textContent += ` · ${body.folder}`;
      if (isSave && body.tags?.length) meta.textContent += ` · ${body.tags.join(" · ")}`;
      content.appendChild(meta);
      if (item.owner !== owner) {
        const mismatch = document.createElement("p");
        mismatch.className = "pending-error";
        mismatch.textContent = t("opt.otherConnection");
        content.appendChild(mismatch);
      }
      if (item.error) {
        const problem = document.createElement("p");
        problem.className = "pending-error";
        problem.textContent = item.error;
        content.appendChild(problem);
      }
      if (isSave) {
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "ext-button";
        retry.dataset.retrySave = body.request_id;
        retry.dataset.otherConnection = String(item.owner !== owner);
        retry.disabled = busy || item.owner !== owner;
        retry.textContent = t("opt.retrySave");
        retry.addEventListener("click", () => action("recover", { type: "retry-save", request_id: body.request_id }, () => setNote("opt.originalSaved")));
        content.appendChild(retry);
      } else if (body.body) {
        let loaded = false;
        const reveal = () => {
          if (!details.open || loaded) return;
          loaded = true;
          const text = document.createElement("pre");
          text.textContent = body.body!;
          text.tabIndex = 0;
          content.appendChild(text);
        };
        details.addEventListener("toggle", reveal);
        reveal();
      }
      details.appendChild(content);
      list.appendChild(details);
    }
  } catch (error) {
    if (mine !== pendingGeneration) return;
    $("#pending-panel").hidden = false;
    $("#pending-results").textContent = describeError(error);
  }
}

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local") return;
  if (changes["fetch-deliveries"] || changes["save-deliveries"]) void renderPending();
  if (!busy && saved && ["endpoint", "token", "channelB", "paused"].some((key) => {
    return changes[key] && changes[key].newValue !== saved![key as keyof Settings];
  })) $("#reload-settings").hidden = false;
});

applyI18n();
initLangToggle();
renderTokenButton();
document.addEventListener("langchange", () => {
  renderTokenButton();
  if (lastError) showError(lastError);
  else if (!busy) void refresh();
  else state.textContent = t(busyKind === "drain" ? "opt.fetching" : "opt.reading");
  void renderPending();
});
lock(true, "load");
void hydrate().then(refresh).catch(showError).finally(() => lock(false));
