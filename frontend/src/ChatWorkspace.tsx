import { useEffect, useRef, useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { ArrowLeft, ArrowUpRight, BookOpen, Check, Copy, History, LoaderCircle,
  MessageCircle, Plus, RotateCcw, Search, Send, Square, Trash2, X } from "lucide-react";
import { api, ApiError, post, safeUrl, type Setup } from "./api";
import { useText, type Language } from "./locale";
import { CapsuleButton } from "./ui/controls";
import { useReducedMotion } from "./useReducedMotion";
import type { ChatLaunch, ChatMessage, ChatSource, Conversation, ConversationSummary } from "./chat-types";
import type { ModelProfile } from "./ModelProfiles";
import { loadChatLocalState, saveChatLocalState, type ChatLocalState, type ChatOperation } from "./chat-local-state";
import "./chat-workspace.css";

const selectedConversation = (value?: string | null) => {
  try {
    if (value === null) localStorage.removeItem("fm-chat-current");
    else if (value !== undefined) localStorage.setItem("fm-chat-current", value);
    const id = localStorage.getItem("fm-chat-current");
    return id && /^[a-zA-Z0-9_-]{1,64}$/.test(id) ? id : null;
  } catch { return null; }
};

function replyText(text: string, sources: ChatSource[], onPreview: (id: number) => void): ReactNode[] {
  return text.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`|\[\d{1,3}\])/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index}>{part.slice(1, -1)}</code>;
    const number = /^\[(\d+)\]$/.exec(part);
    const source = number ? sources.find(item => item.n === Number(number[1])) : undefined;
    return source ? <CapsuleButton key={index} type="button" className="chat-citation"
      aria-label={"[" + source.n + "] " + (source.ai_title || source.title)}
      disabled={source.bookmark_id === null}
      onClick={() => { if (source.bookmark_id !== null) onPreview(source.bookmark_id); }}>{part}</CapsuleButton> : part;
  });
}

type RunningRequest = { controller: AbortController; id: string | null; requestId: string };

export function ChatWorkspace({ active, launch, setup, language, onPreview, onSettings, onBack }: {
  active: boolean; launch: ChatLaunch | null; setup: Setup | null; language: Language;
  onPreview: (id: number) => void; onSettings: () => void; onBack: () => void;
}) {
  const t = useText(), reduced = useReducedMotion();
  const stored = useRef<ChatLocalState | null>(null);
  if (!stored.current) stored.current = loadChatLocalState();
  const [currentId, setCurrentId] = useState<string | null>(() => selectedConversation());
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [scope, setScope] = useState<ChatLaunch>(stored.current.scope);
  const [drafts, setDrafts] = useState(stored.current.drafts);
  const [connections, setConnections] = useState(stored.current.connections);
  const [operations, setOperations] = useState(stored.current.operations);
  const [storageWarning, setStorageWarning] = useState(false);
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [profilesBusy, setProfilesBusy] = useState(false);
  const [profilesError, setProfilesError] = useState("");
  const [profilesRevision, setProfilesRevision] = useState(0);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [readFailure, setReadFailure] = useState<string | null>(null);
  const [readRevision, setReadRevision] = useState(0);
  const [requestRevision, setRequestRevision] = useState(0);
  const [cancelling, setCancelling] = useState<string | null>(null);
  const [copied, setCopied] = useState<number | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyItems, setHistoryItems] = useState<ConversationSummary[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyFilter, setHistoryFilter] = useState("");
  const [historyBusy, setHistoryBusy] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [historyRevision, setHistoryRevision] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<ConversationSummary | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const currentRef = useRef(currentId), selectionRevision = useRef(0);
  const draftSequence = useRef(Date.now());
  const optimisticMessageId = useRef(0);
  const requests = useRef(new Map<string, RunningRequest>());
  const cache = useRef(new Map<string, Conversation>());
  const skipLoad = useRef<string | null>(null);
  const stopGate = useRef(new Set<string>()), deleteGate = useRef(false);
  const historyMoreGate = useRef(false), historyVersion = useRef(0);
  const historyMoreRequest = useRef<AbortController | null>(null);
  const recoveryRead = useRef<AbortController | null>(null);
  const editor = useRef<HTMLTextAreaElement>(null), messages = useRef<HTMLDivElement>(null);
  const nearBottom = useRef(true);
  const currentKey = currentId || "draft:" + scope.nonce;
  const draft = Object.hasOwn(drafts, currentKey) ? drafts[currentKey] : "";
  const localRequest = requests.current.get(currentKey);
  const running = Boolean(conversation?.running || localRequest);
  const operation = Object.hasOwn(operations, currentKey) ? operations[currentKey] : undefined;
  const profileId = Object.hasOwn(connections, currentKey) ? connections[currentKey] : conversation?.profile_id ?? "";
  const chosenProfile = profiles.find(profile => profile.id === profileId);
  const ready = Boolean(profileId ? chosenProfile?.tested : setup?.demo || setup?.channels.chat.tested);
  const stopping = cancelling === currentKey || stopGate.current.has(currentKey);
  const currentError = errors[currentKey] || "";
  const lastMessage = conversation?.messages.at(-1);
  const canRetry = lastMessage?.role === "assistant" && ["error", "cancelled"].includes(lastMessage.status);
  const canRegenerate = lastMessage?.role === "assistant" && lastMessage.status === "complete";
  const pinned = currentId ? conversation?.bookmark_ids || [] : scope.bookmark_ids;

  const saveLocal = (changes: Partial<ChatLocalState>) => {
    const value = { ...stored.current!, ...changes };
    stored.current = value;
    setDrafts(value.drafts); setConnections(value.connections); setOperations(value.operations);
    setStorageWarning(!saveChatLocalState(value));
  };
  const writeDraft = (key: string, text: string) => {
    const next = { ...stored.current!.drafts }; delete next[key];
    if (text) next[key] = text;
    saveLocal({ drafts: next });
  };
  const keepOperation = (key: string, value: ChatOperation) => {
    const next = { ...stored.current!.operations };
    for (const [previous, item] of Object.entries(next)) if (item.requestId === value.requestId) delete next[previous];
    next[key] = value;
    saveLocal({ operations: next });
  };
  const forgetOperation = (requestId: string) => {
    const next = { ...stored.current!.operations };
    for (const [key, item] of Object.entries(next)) if (item.requestId === requestId) delete next[key];
    saveLocal({ operations: next });
  };
  const readPath = (id: string, requestId?: string) => "/chat/conversations/" + id +
    (requestId ? "?request_id=" + encodeURIComponent(requestId) : "");
  const moveLocalDraft = (id: string, item: ChatOperation) => {
    const value = stored.current!, nextDrafts = { ...value.drafts }, nextConnections = { ...value.connections };
    if (item.originKey !== id && Object.hasOwn(nextDrafts, item.originKey)) {
      nextDrafts[id] = nextDrafts[item.originKey]; delete nextDrafts[item.originKey];
    }
    if (!Object.hasOwn(nextConnections, id)) nextConnections[id] = Object.hasOwn(value.connections, item.originKey)
      ? value.connections[item.originKey] : item.profileId;
    saveLocal({ drafts: nextDrafts, connections: nextConnections });
  };

  const apply = (value: Conversation, authoritative = true) => {
    const pending = Object.entries(stored.current!.operations).find(([, item]) => item.id === value.id);
    const receipt = pending && value.delivery?.request_id === pending[1].requestId ? value.delivery : undefined;
    if (authoritative && pending && pending[0] !== value.id) {
      moveLocalDraft(value.id, pending[1]);
      keepOperation(value.id, { ...pending[1], id: value.id, created: true });
    }
    if (authoritative && pending && (receipt?.accepted || value.messages.some(message => message.id > 0 && message.request_id === pending[1].requestId))) {
      const [key, item] = pending, nextDrafts = { ...stored.current!.drafts }, nextOperations = { ...stored.current!.operations };
      if (item.mode === "send") for (const draftKey of [item.originKey, value.id]) {
        if (nextDrafts[draftKey]?.trim() === item.text) delete nextDrafts[draftKey];
      }
      delete nextOperations[key];
      if (receipt ? receipt.running : value.running) nextOperations[value.id] = { ...item, id: value.id, created: true, confirmed: true };
      else delete nextOperations[value.id];
      saveLocal({ drafts: nextDrafts, operations: nextOperations });
      setErrors(previous => ({ ...previous, [item.originKey]: "", [value.id]: "" }));
    } else if (authoritative && pending?.[1].rejected && receipt?.accepted === false) {
      forgetOperation(pending[1].requestId);
    }
    cache.current.set(value.id, value);
    if (cache.current.size > 24) {
      const oldest = [...cache.current.keys()].find(id => id !== currentRef.current && !requests.current.has(id));
      if (oldest) cache.current.delete(oldest);
    }
    if (currentRef.current === value.id) { setConversation(value); if (authoritative) setReadFailure(null); }
  };
  const attach = (value: Conversation, operation: ChatOperation, version: number) => {
    cache.current.set(value.id, value);
    moveLocalDraft(value.id, operation);
    if (selectionRevision.current !== version) return;
    if (currentRef.current !== value.id) skipLoad.current = value.id;
    currentRef.current = value.id;
    setCurrentId(value.id); setConversation(value); selectedConversation(value.id);
    setErrors(previous => ({ ...previous, [value.id]: previous[value.id] || previous[operation.originKey] || "" }));
  };
  const choose = (id: string | null) => {
    selectionRevision.current++;
    currentRef.current = id;
    setCurrentId(id); setConversation(id ? cache.current.get(id) || null : null); setReadFailure(null);
    selectedConversation(id);
    nearBottom.current = true;
    setHistoryOpen(false);
  };
  const newConversation = (next?: ChatLaunch) => {
    if (next) draftSequence.current = Math.max(draftSequence.current, next.nonce);
    const value = next ? { ...next, title: next.title?.slice(0, 500) } : { nonce: ++draftSequence.current, bookmark_ids: [] };
    setScope(value); saveLocal({ scope: value }); choose(null);
    requestAnimationFrame(() => editor.current?.focus({ preventScroll: true }));
  };
  useEffect(() => {
    if (launch) newConversation(launch);
    // A new reader launch is explicit; ordinary navigation preserves the draft.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [launch?.nonce]);
  useEffect(() => {
    if (!active) return;
    const abort = new AbortController();
    setProfilesBusy(true); setProfilesError("");
    api<{ profiles: ModelProfile[] }>("/admin/model-profiles?channel=chat", { signal: abort.signal })
      .then(value => { if (!abort.signal.aborted) setProfiles(value.profiles); })
      .catch(failure => { if (!abort.signal.aborted) setProfilesError(String(failure)); })
      .finally(() => { if (!abort.signal.aborted) setProfilesBusy(false); });
    return () => abort.abort();
  }, [active, profilesRevision]);
  useEffect(() => {
    if (!active || !currentId) { setLoading(false); return; }
    if (skipLoad.current === currentId) { skipLoad.current = null; return; }
    const id = currentId, abort = new AbortController();
    setLoading(true); setReadFailure(null); setErrors(previous => ({ ...previous, [id]: "" }));
    const pending = Object.values(stored.current!.operations).find(item => item.id === id);
    api<Conversation>(readPath(id, pending?.requestId), { signal: abort.signal })
      .then(value => { if (!abort.signal.aborted) apply(value); })
      .catch(failure => {
        if (!abort.signal.aborted) { setReadFailure(id); setErrors(previous => ({ ...previous, [id]: String(failure) })); }
      }).finally(() => { if (!abort.signal.aborted && currentRef.current === id) setLoading(false); });
    return () => abort.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, currentId, readRevision]);
  useEffect(() => {
    if (!active) return;
    const abort = new AbortController(), version = ++historyVersion.current;
    setHistoryBusy(true); setHistoryError("");
    api<{ items: ConversationSummary[]; total: number }>("/chat/conversations?limit=50&offset=0", { signal: abort.signal })
      .then(value => { if (!abort.signal.aborted) { setHistoryItems(value.items); setHistoryTotal(value.total); } })
      .catch(failure => { if (!abort.signal.aborted) setHistoryError(String(failure)); })
      .finally(() => { if (!abort.signal.aborted) setHistoryBusy(false); });
    return () => {
      abort.abort(); historyMoreRequest.current?.abort();
      if (historyVersion.current === version) historyVersion.current++;
    };
  }, [active, historyRevision]);
  useEffect(() => {
    if (!active || !currentId || !running) return;
    const id = currentId, abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const pending = Object.values(stored.current!.operations).find(item => item.id === id);
        const value = await api<Conversation>(readPath(id, pending?.requestId), { signal: abort.signal });
        if (!abort.signal.aborted) {
          apply(value);
          if (value.running || requests.current.has(id)) timer = setTimeout(poll, 1400);
          else setHistoryRevision(previous => previous + 1);
        }
      } catch (failure) {
        if (!abort.signal.aborted) {
          setErrors(previous => ({ ...previous, [id]: String(failure) }));
          timer = setTimeout(poll, 3000);
        }
      }
    };
    timer = setTimeout(poll, 1000);
    return () => { clearTimeout(timer); abort.abort(); };
    // requestRevision refreshes the local gate after a long POST completes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, currentId, running, requestRevision]);
  useEffect(() => {
    if (!active || !nearBottom.current) return;
    messages.current?.scrollTo({ top: messages.current.scrollHeight,
      behavior: reduced || running ? "instant" : "smooth" });
  }, [active, conversation?.messages, currentId, reduced, running]);
  useEffect(() => {
    if (!active || currentId) return;
    requestAnimationFrame(() => editor.current?.focus({ preventScroll: true }));
  }, [active, currentId]);
  useEffect(() => () => { for (const request of requests.current.values()) request.controller.abort(); }, []);
  useEffect(() => () => recoveryRead.current?.abort(), [active, currentId, scope.nonce]);
  useEffect(() => {
    if (copied === null) return;
    const timer = setTimeout(() => setCopied(null), 1800);
    return () => clearTimeout(timer);
  }, [copied]);

  async function send(mode: "send" | "retry" | "regenerate" = "send") {
    const retry = mode === "retry", regenerate = mode === "regenerate";
    if (!ready || loading || running || requests.current.has(currentKey) || stopGate.current.has(currentKey) || operation
      || (currentId && (!conversation || readFailure === currentId))
      || (mode === "send" && !draft.trim()) || (mode !== "send" && !currentId)
      || (retry && !canRetry) || (regenerate && !canRegenerate)) return;
    const requestId = crypto.randomUUID(), id = currentId || crypto.randomUUID();
    const value: ChatOperation = { id, originKey: currentKey, mode, text: mode === "send" ? draft.trim() : "",
      requestId, language, profileId, created: Boolean(currentId), confirmed: false,
      ...(!currentId ? { creation: { id, request_id: requestId + ".create",
        title: (scope.title || draft.trim().slice(0, 80)).slice(0, 120), bookmark_ids: [...scope.bookmark_ids], profile_id: profileId } } : {}),
    };
    await deliver(value);
  }

  async function deliver(snapshot: ChatOperation) {
    if (recoveryRead.current || requests.current.has(snapshot.id) || requests.current.has(snapshot.originKey) || stopGate.current.has(snapshot.originKey)) return;
    const selectedVersion = selectionRevision.current, originKey = snapshot.originKey, text = snapshot.text;
    let operation = { ...snapshot, rejected: false };
    const retry = operation.mode === "retry", regenerate = operation.mode === "regenerate";
    const controller = new AbortController(), request: RunningRequest = {
      controller, id: operation.created ? operation.id : null, requestId: operation.requestId,
    };
    let id = operation.id, key = operation.created ? id : originKey;
    requests.current.set(originKey, request); requests.current.set(id, request);
    keepOperation(key, operation); setRequestRevision(previous => previous + 1);
    setErrors(previous => ({ ...previous, [key]: "" }));
    nearBottom.current = true;
    try {
      if (!operation.created && operation.creation) {
        const created = await post<Conversation>("/chat/conversations", operation.creation, controller.signal);
        if (controller.signal.aborted) return;
        id = created.id; key = id; request.id = id;
        operation = { ...operation, id, created: true };
        keepOperation(id, operation);
        // Keep the draft key gated until this request finishes, including the
        // interval before React commits the newly created conversation ID.
        requests.current.set(key, request);
        attach(created, operation, selectedVersion);
      }
      if (controller.signal.aborted) return;
      if (currentRef.current === null && operation.created) {
        const restored = cache.current.get(id) || await api<Conversation>(readPath(id, operation.requestId), { signal: controller.signal });
        attach(restored, operation, selectedVersion);
        keepOperation(id, operation);
      }
      const existing = cache.current.get(id);
      if (existing) {
        const now = Math.floor(Date.now() / 1000);
        // Use distinct local IDs even when the clock ticks between constructing
        // the question and reply. Server message IDs are positive.
        const pending: ChatMessage = { id: --optimisticMessageId.current, role: "assistant", content: "", status: "pending", sources: [], model: "", created_at: now,
          request_id: request.requestId };
        const optimistic: ChatMessage[] = retry ? existing.messages.map((item, index) =>
          index === existing.messages.length - 1 ? { ...item, content: "", status: "pending" as const,
            sources: [], model: "", request_id: request.requestId } : item) : regenerate ? [...existing.messages, pending] : [
          ...existing.messages,
          { id: --optimisticMessageId.current, role: "user", content: text, status: "complete", sources: [], model: "", created_at: now,
            request_id: request.requestId },
          pending,
        ];
        apply({ ...existing, running: true, messages: optimistic }, false);
      }
      const value = await post<Conversation>("/chat/conversations/" + id + "/messages", {
        ...(retry ? { retry: true } : regenerate ? { regenerate: true } : { text }),
        language: operation.language, profile_id: operation.profileId, request_id: request.requestId,
      }, controller.signal);
      apply(value);
    } catch (failure) {
      if (!controller.signal.aborted) {
        setErrors(previous => ({ ...previous, [key]: String(failure) }));
        if (failure instanceof ApiError && failure.status >= 400 && failure.status < 500 && failure.status !== 408) {
          operation = { ...operation, rejected: true };
          keepOperation(key, operation);
          if (failure.status === 410) forgetOperation(operation.requestId);
        }
        try {
          const latest = await api<Conversation>(readPath(id, operation.requestId), { signal: controller.signal });
          if (controller.signal.aborted) return;
          if (!operation.created) {
            operation = { ...operation, id: latest.id, created: true };
            keepOperation(latest.id, operation);
            attach(latest, operation, selectedVersion);
          }
          apply(latest);
          if (operation.rejected && !latest.delivery && !latest.messages.some(message => message.request_id === operation.requestId))
            forgetOperation(operation.requestId);
        } catch { /* The persisted action can be read or retried with its original receipt. */ }
      }
    } finally {
      if (requests.current.get(key) === request) requests.current.delete(key);
      if (requests.current.get(snapshot.id) === request) requests.current.delete(snapshot.id);
      if (requests.current.get(originKey) === request) requests.current.delete(originKey);
      setRequestRevision(previous => previous + 1); setHistoryRevision(previous => previous + 1);
    }
  }

  async function readPending(snapshot: ChatOperation) {
    if (recoveryRead.current || requests.current.has(snapshot.id) || requests.current.has(snapshot.originKey)) return;
    const request = new AbortController(), version = selectionRevision.current;
    recoveryRead.current = request; setLoading(true);
    try {
      const value = await api<Conversation>(readPath(snapshot.id, snapshot.requestId), { signal: request.signal });
      if (request.signal.aborted) return;
      const restored = { ...snapshot, id: value.id, created: true };
      keepOperation(value.id, restored); attach(value, restored, version); apply(value);
    } catch (failure) {
      if (!request.signal.aborted) {
        setErrors(previous => ({ ...previous, [currentKey]: String(failure) }));
        if (snapshot.rejected && failure instanceof ApiError && failure.status === 404) forgetOperation(snapshot.requestId);
      }
    } finally {
      if (recoveryRead.current === request) { recoveryRead.current = null; setLoading(false); }
    }
  }

  async function loadMoreHistory() {
    if (historyMoreGate.current || historyBusy) return;
    historyMoreGate.current = true;
    const request = new AbortController(), version = historyVersion.current;
    historyMoreRequest.current = request; setHistoryBusy(true); setHistoryError("");
    try {
      const value = await api<{ items: ConversationSummary[]; total: number }>("/chat/conversations?limit=50&offset=" + historyItems.length,
        { signal: request.signal });
      if (!request.signal.aborted && historyVersion.current === version) {
        setHistoryItems(previous => { const known = new Set(previous.map(item => item.id)); return [...previous, ...value.items.filter(item => !known.has(item.id))]; });
        setHistoryTotal(value.total);
      }
    } catch (failure) {
      if (!request.signal.aborted && historyVersion.current === version) setHistoryError(String(failure));
    } finally {
      if (historyMoreRequest.current === request) { historyMoreRequest.current = null; historyMoreGate.current = false; }
      if (historyVersion.current === version) setHistoryBusy(false);
    }
  }

  async function stop() {
    if (!running || stopGate.current.has(currentKey)) return;
    stopGate.current.add(currentKey);
    const request = requests.current.get(currentKey), id = currentId || request?.id || null;
    const requestId = request?.requestId || (lastMessage?.status === "pending" ? lastMessage.request_id : undefined);
    setCancelling(currentKey); setErrors(previous => ({ ...previous, [currentKey]: "" }));
    try {
      if (id) {
        const result = await post<{ cancelled: boolean }>("/chat/conversations/" + id + "/cancel",
          requestId ? { request_id: requestId } : {});
        if (!result.cancelled) {
          const latest = await api<Conversation>(readPath(id, requestId));
          apply(latest);
          if (latest.running) throw new Error(t("未能停止当前回答，请重试。", "The current reply could not be stopped. Try again."));
        }
      }
      request?.controller.abort();
      if (requests.current.get(currentKey) === request) requests.current.delete(currentKey);
      if (id) apply(await api<Conversation>(readPath(id, requestId)));
    } catch (failure) {
      setErrors(previous => ({ ...previous, [currentKey]: String(failure) }));
    } finally {
      stopGate.current.delete(currentKey);
      setCancelling(null); setRequestRevision(previous => previous + 1);
      setHistoryRevision(previous => previous + 1);
      if (currentRef.current === id) editor.current?.focus({ preventScroll: true });
    }
  }

  async function deleteConversation() {
    if (!deleteTarget || deleteGate.current) return;
    deleteGate.current = true;
    setDeleteBusy(true); setDeleteError("");
    try {
      try { await api("/chat/conversations/" + deleteTarget.id, { method: "DELETE" }); }
      catch (failure) { if (!(failure instanceof ApiError) || failure.status !== 404) throw failure; }
      cache.current.delete(deleteTarget.id);
      const nextDrafts = { ...stored.current!.drafts }, nextConnections = { ...stored.current!.connections }, nextOperations = { ...stored.current!.operations };
      delete nextDrafts[deleteTarget.id]; delete nextConnections[deleteTarget.id];
      for (const [key, item] of Object.entries(nextOperations)) if (item.id === deleteTarget.id) delete nextOperations[key];
      saveLocal({ drafts: nextDrafts, connections: nextConnections, operations: nextOperations });
      if (currentRef.current === deleteTarget.id) newConversation();
      setDeleteTarget(null); setHistoryRevision(previous => previous + 1);
    } catch (failure) { setDeleteError(String(failure)); }
    finally { deleteGate.current = false; setDeleteBusy(false); }
  }

  const historyMatches = historyItems.filter(item => item.title.toLocaleLowerCase().includes(historyFilter.trim().toLocaleLowerCase()));
  const suggestions = pinned.length ? [t("这篇收藏的关键结论是什么？", "What are this page's main conclusions?"),
    t("把具体方法整理成操作步骤。", "Turn its methods into practical steps."),
    t("它的适用条件和局限是什么？", "When is it useful, and what are its limits?")]
    : [t("找出我收藏的 SQLite 相关内容。", "Find what I saved about SQLite."),
      t("我收藏了哪些可恢复任务的实现方法？", "What did I save about resumable tasks?")];

  return <section className="chat-workspace" hidden={!active} aria-labelledby="chat-heading">
    <header className="chat-heading">
      <div><h1 id="chat-heading"><MessageCircle size={23}/>{t("AI 对话", "AI chat")}</h1>
        <p>{t("从保存的内容提问，沿着来源继续阅读。", "Ask about saved content and follow its sources.")}</p></div>
      <div className="chat-heading-actions">
        <CapsuleButton type="button" className="secondary" onClick={() => newConversation()}><Plus size={16}/>{t("新对话", "New chat")}</CapsuleButton>
        <CapsuleButton type="button" className="secondary" onClick={() => { setHistoryOpen(true); setHistoryRevision(previous => previous + 1); }}><History size={16}/>{t("历史", "History")}</CapsuleButton>
        <CapsuleButton type="button" className="text-button chat-back" onClick={onBack}><ArrowLeft size={16}/><span>{t("返回收藏", "Back to collection")}</span></CapsuleButton>
      </div>
    </header>
    <div className="chat-context" role="status"><BookOpen size={14}/>
      <span>{pinned.length ? conversation?.title || scope.title || t("所选收藏", "Selected pages") : t("整个收藏库", "Your bookmark library")}</span>
      {pinned.length > 0 && <small>{t(pinned.length + " 篇", pinned.length + " pages")}</small>}
      {pinned.length > 0 && <CapsuleButton type="button" className="text-button" onClick={() => newConversation()}>{t("问整个书库", "Ask the library")}</CapsuleButton>}
    </div>
    <div className="chat-messages" ref={messages} tabIndex={0} role="log" aria-live="polite"
      aria-relevant="additions text" aria-label={t("对话消息", "Chat messages")}
      aria-busy={loading || running} onScroll={event => {
        const box = event.currentTarget;
        nearBottom.current = box.scrollHeight - box.scrollTop - box.clientHeight < 100;
      }}>
      {loading && !conversation ? <p className="chat-loading" role="status"><LoaderCircle className="spin" size={18}/>{t("正在读取对话…", "Loading conversation…")}</p>
        : currentId && readFailure === currentId && !conversation ? <div className="chat-empty chat-read-failure" role="alert">
          <h2>{t("暂时无法读取这段对话", "This conversation could not be loaded")}</h2>
          <p>{currentError}</p>
          <CapsuleButton type="button" className="secondary" onClick={() => setReadRevision(value => value + 1)}>{t("重新读取对话", "Reload conversation")}</CapsuleButton>
        </div>
        : !conversation?.messages.length ? <div className="chat-empty">
          <div className="chat-empty-mark"><MessageCircle size={30}/></div>
          <h2>{pinned.length ? t("聊聊这篇收藏", "Talk about this saved page") : t("和收藏聊一聊", "Have a conversation with your library")}</h2>
          <p>{t("追问细节、比较方法，或整理下一步。回答会引用保存的原文或摘要。", "Explore details, compare methods or decide what to do next. Answers cite saved text or summaries.")}</p>
          <div className="chat-suggestions">{suggestions.map(text => <CapsuleButton key={text} type="button" className="secondary" onClick={() => {
            writeDraft(currentKey, text); editor.current?.focus();
          }}>{text}<ArrowUpRight size={14}/></CapsuleButton>)}</div>
        </div> : conversation.messages.map(message => <article className={"chat-message " + message.role} key={message.id} data-status={message.status}>
          <div className="chat-message-author">{message.role === "user" ? t("你", "You") : "Facetmark"}
            {message.role === "assistant" && message.model && <span>{message.model}</span>}</div>
          {message.status === "pending" ? <p className="chat-generating" role="status"><LoaderCircle className="spin" size={16}/>{t("正在整理保存的内容…", "Working through your saved content…")}</p>
            : <div className="chat-message-content">{message.content.split(/\n\s*\n/).filter(Boolean).map((paragraph, index) => <p key={index}>{replyText(paragraph, message.sources || [], onPreview)}</p>)}</div>}
          {message.status === "cancelled" && <p className="chat-message-state">{t("已停止生成，可重试这个问题。", "Generation stopped. You can retry this question.")}</p>}
          {message.status === "error" && <p className="chat-message-state" role="alert">{t("回答未完成，可重试这个问题。", "The answer could not be completed. You can retry it.")}</p>}
          {!!message.sources?.length && <details className="chat-sources" open>
            <summary>{t("引用的收藏", "Cited bookmarks")} · {message.sources.length}</summary>
            {message.sources.map((source, index) => <div className="chat-source" key={`${source.n || index + 1}:${source.bookmark_id ?? "missing"}`}>
              <CapsuleButton type="button" className="chat-source-preview" disabled={source.bookmark_id === null}
                aria-label={t("查看引用：", "Read source: ") + (source.ai_title || source.title)} onClick={() => { if (source.bookmark_id !== null) onPreview(source.bookmark_id); }}>
                <span className="chat-source-number">[{source.n || index + 1}]</span><span>{source.ai_title || source.title || source.url}
                  {source.bookmark_id === null ? <small>{t("来源已不在书库中，仍可打开原网址", "Source no longer in the library; its original URL is available")}</small>
                    : source.basis === "title" && <small>{t("基于标题推断", "Inferred from title")}</small>}</span>
              </CapsuleButton>
              {safeUrl(source.url) && <a href={safeUrl(source.url)} target="_blank" rel="noreferrer" aria-label={t("打开来源网页", "Open source website")}><ArrowUpRight size={17}/></a>}
            </div>)}
          </details>}
          {message.role === "assistant" && message.status === "complete" && message.content && <CapsuleButton type="button" className="text-button chat-copy" aria-label={t("复制回答", "Copy answer")}
            onClick={async () => { try { await navigator.clipboard.writeText(message.content); setCopied(message.id); }
              catch { setErrors(previous => ({ ...previous, [currentKey]: t("无法复制，请选择回答文字复制。", "Copy failed. Select the answer text to copy it.") })); } }}>
            {copied === message.id ? <Check size={14}/> : <Copy size={14}/>} {copied === message.id ? t("已复制", "Copied") : t("复制", "Copy")}
          </CapsuleButton>}
        </article>)}
    </div>
    <div className="chat-composer-area">
      <div className="chat-composer-status" role="region" aria-label={t("连接与发送状态", "Connection and send status")} tabIndex={0}>
      <div className="chat-model-choice">
        <label htmlFor="chat-connection"><span aria-hidden="true">
          <span className="chat-model-label">{t("本段对话的模型连接", "Connection for this conversation")}</span>
          <span className="chat-model-label-compact">{t("模型连接", "Connection")}</span>
        </span>
          <select id="chat-connection" value={profileId} aria-label={t("本段对话的模型连接", "Connection for this conversation")}
            disabled={running || loading || Boolean(operation) || stopping}
            onChange={event => saveLocal({ connections: { ...stored.current!.connections, [currentKey]: event.currentTarget.value } })}>
            <option value="">{t("使用摘要连接", "Use the summary connection")}</option>
            {profileId && !chosenProfile && <option value={profileId}>{profilesBusy ? t("正在读取连接…", "Loading connection…") : t("连接已移除或暂时无法读取", "Connection removed or unavailable")}</option>}
            {profiles.map(profile => <option key={profile.id} value={profile.id}>{profile.name}{!profile.tested ? t(" · 需要测试", " · needs a test") : ""}</option>)}
          </select>
        </label>
        <span className="chat-model-help">{chosenProfile ? chosenProfile.model || chosenProfile.agent : t("可在设置中保存其他连接", "Save other connections in Settings")}</span>
      </div>
      {profilesError && <div className="chat-feedback" role="alert"><span>{profilesError}</span><CapsuleButton type="button" className="text-button" disabled={profilesBusy} onClick={() => setProfilesRevision(value => value + 1)}>{t("重读连接", "Reload connections")}</CapsuleButton></div>}
      {operation && !operation.confirmed && !localRequest && <div className="chat-delivery-recovery" role="status">
        <p>{t("上次发送的结果暂时无法确认。重新读取对话，或继续同一次发送。", "The last send could not be confirmed. Reload the conversation or resume the same send.")}</p>
        <div><CapsuleButton type="button" className="secondary" disabled={loading || stopping} onClick={() => void readPending(operation)}>{t("重新读取对话", "Reload conversation")}</CapsuleButton>
          <CapsuleButton type="button" className="secondary" disabled={loading || stopping} onClick={() => void deliver(operation)}>{t("重试提交", "Retry submission")}</CapsuleButton></div>
      </div>}
      {currentId && conversation && readFailure === currentId && (!operation || operation.confirmed) && <div className="chat-read-recovery" role="status"><span>{t("显示的是已读取的对话，重新读取后再继续发送。", "These are the previously loaded messages. Reload before sending again.")}</span>
        <CapsuleButton type="button" className="secondary" disabled={loading} onClick={() => setReadRevision(value => value + 1)}>{t("重新读取对话", "Reload conversation")}</CapsuleButton></div>}
      {currentError && <div className="chat-feedback" role="alert"><span>{currentError}</span><CapsuleButton type="button" className="icon-button" aria-label={t("关闭对话提示", "Dismiss chat message")}
        onClick={() => setErrors(previous => ({ ...previous, [currentKey]: "" }))}><X size={15}/></CapsuleButton></div>}
      {!ready && <div className="chat-connection-notice"><span>{profileId
        ? profilesBusy ? t("正在读取这段对话的连接，草稿会保留。", "Loading this conversation's connection. Your draft is retained.")
          : profilesError ? t("暂时无法确认这个连接，请重新读取连接后再发送。草稿会保留。", "This connection could not be confirmed. Reload connections before sending; your draft is retained.")
            : !chosenProfile ? t("这段对话的连接已移除，请选择其他连接。已保存的回答和草稿会保留。", "This conversation's connection was removed. Choose another connection; saved answers and your draft are retained.")
              : t("此连接需先测试；可以继续写草稿。", "Test this connection before sending; you can keep drafting.")
        : setup === null ? t("正在读取已保存的聊天连接，草稿会保留。", "Loading your saved chat connection. Your draft is retained.")
          : t("可以先写问题，测试并保存聊天连接后再发送。", "Draft a question now, then test and save a chat connection before sending.")}</span>
        {(profileId || setup !== null) && <CapsuleButton type="button" className="text-button" onClick={onSettings}>{t("设置 AI 连接", "Set up AI connection")}</CapsuleButton>}</div>}
      {canRetry && !running && !operation && <div className="chat-retry"><span>{t("继续刚才的问题", "Continue your last question")}</span>
        <CapsuleButton type="button" className="secondary" disabled={!ready || loading || readFailure === currentId} onClick={() => void send("retry")}><RotateCcw size={15}/>{t("重试回答", "Retry answer")}</CapsuleButton></div>}
      {canRegenerate && !running && !operation && <div className="chat-retry chat-regenerate">
        <span>{t("旧回答会保留。", "The previous answer is kept.")}</span>
        <CapsuleButton type="button" className="secondary" disabled={!ready || loading || readFailure === currentId} onClick={() => void send("regenerate")}><RotateCcw size={15}/>{t("重新回答", "Answer again")}</CapsuleButton>
      </div>}
      {storageWarning && <p className="chat-storage-warning" role="status">{t("草稿暂时无法在本机保存，请保留当前窗口。", "The draft could not be saved on this device. Keep this window open.")}</p>}
      </div>
      <form className="chat-composer" onSubmit={event => { event.preventDefault(); void send(); }}>
        <label className="sr-only" htmlFor="chat-question">{t("对收藏提问", "Ask about bookmarks")}</label>
        <textarea id="chat-question" ref={editor} value={draft} maxLength={4000} rows={2} disabled={loading || stopping}
          placeholder={pinned.length ? t("追问这篇收藏的内容…", "Ask about this saved page…") : t("想从收藏里了解什么？", "What would you like to learn from your bookmarks?")}
          onChange={event => {
            const text = event.currentTarget.value;
            writeDraft(currentKey, text);
          }}
          onKeyDown={event => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.nativeEvent.keyCode !== 229) {
              event.preventDefault(); if (!running) void send();
            }
          }}/>
        {running ? <CapsuleButton type="button" className="secondary chat-send" disabled={stopping} onClick={() => void stop()} aria-label={t("停止生成", "Stop generation")}>
          {stopping ? <LoaderCircle className="spin" size={17}/> : <Square size={16}/>}<span>{stopping ? t("正在停止", "Stopping") : t("停止", "Stop")}</span>
        </CapsuleButton> : <CapsuleButton type="submit" className="primary chat-send" disabled={!ready || loading || !draft.trim() || Boolean(operation) || Boolean(currentId && (!conversation || readFailure === currentId))} aria-label={t("发送问题", "Send question")}><Send size={17}/><span>{t("发送", "Send")}</span></CapsuleButton>}
      </form>
      <p className="chat-composer-hint">{t("Enter 发送 · Shift + Enter 换行", "Enter to send · Shift + Enter for a new line")}</p>
    </div>
    <Dialog.Root open={historyOpen} onOpenChange={setHistoryOpen}><Dialog.Portal>
      <Dialog.Overlay className="chat-history-overlay"/>
      <Dialog.Content className="chat-history-panel" aria-describedby="chat-history-description">
        <div className="chat-history-heading"><Dialog.Title>{t("对话历史", "Chat history")}</Dialog.Title><Dialog.Close asChild><CapsuleButton type="button" className="icon-button" aria-label={t("关闭对话历史", "Close chat history")}><X size={18}/></CapsuleButton></Dialog.Close></div>
        <Dialog.Description id="chat-history-description">{t("继续之前的问题，历史保存在你的书库中。", "Continue a previous conversation. History is saved in your library.")}</Dialog.Description>
        <label className="chat-history-search"><Search size={16}/><input value={historyFilter} onChange={event => setHistoryFilter(event.target.value)} aria-label={t("搜索已加载对话", "Search loaded conversations")} placeholder={t("搜索已加载对话", "Search loaded conversations")}/></label>
        <div className="chat-history-list">
          {historyError && <p className="error" role="alert">{historyError}<CapsuleButton type="button" className="text-button" onClick={() => setHistoryRevision(previous => previous + 1)}>{t("重试", "Retry")}</CapsuleButton></p>}
          {historyBusy && !historyItems.length ? <p role="status">{t("正在读取历史…", "Loading history…")}</p>
            : !historyMatches.length ? <p className="chat-history-empty">{historyFilter ? t("已加载的对话中没有匹配结果。", "No loaded conversations match.") : t("开始第一次对话后，历史会出现在这里。", "Your first conversation will appear here.")}</p>
              : historyMatches.map(item => <div className={"chat-history-item " + (item.id === currentId ? "active" : "")} key={item.id}>
                <CapsuleButton type="button" className="chat-history-open" aria-current={item.id === currentId ? "true" : undefined} onClick={() => choose(item.id)}>
                  <span>{item.title || t("未命名对话", "Untitled chat")}</span><small>{new Date(item.updated_at * 1000).toLocaleDateString(language === "zh" ? "zh-CN" : "en")}{item.running ? " · " + t("正在生成", "Generating") : ""}</small>
                </CapsuleButton>
                <CapsuleButton type="button" className="icon-button" disabled={item.running} aria-label={t("删除对话：", "Delete chat: ") + item.title} onClick={() => { setDeleteTarget(item); setDeleteError(""); }}><Trash2 size={15}/></CapsuleButton>
              </div>)}
          {historyItems.length < historyTotal && <CapsuleButton type="button" className="secondary chat-history-more" disabled={historyBusy} onClick={() => void loadMoreHistory()}>{t("加载更多历史", "Load more history")}</CapsuleButton>}
        </div>
      </Dialog.Content>
    </Dialog.Portal></Dialog.Root>
    <Dialog.Root open={Boolean(deleteTarget)} onOpenChange={open => { if (!open && !deleteBusy) setDeleteTarget(null); }}><Dialog.Portal>
      <Dialog.Overlay className="chat-delete-overlay"/>
      <Dialog.Content className="chat-delete-dialog" aria-describedby="chat-delete-description">
        <Dialog.Title>{t("删除这段对话？", "Delete this conversation?")}</Dialog.Title>
        <Dialog.Description id="chat-delete-description">{deleteTarget?.title}</Dialog.Description>
        {deleteError && <p className="error" role="alert">{deleteError}</p>}
        <div><CapsuleButton type="button" className="secondary" disabled={deleteBusy} onClick={() => setDeleteTarget(null)}>{t("取消", "Cancel")}</CapsuleButton>
          <CapsuleButton type="button" className="primary" disabled={deleteBusy} onClick={() => void deleteConversation()}>{t("删除对话", "Delete chat")}</CapsuleButton></div>
      </Dialog.Content>
    </Dialog.Portal></Dialog.Root>
  </section>;
}
