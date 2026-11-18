import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Pencil, StickyNote } from "lucide-react";
import { api, ApiError, type Bookmark } from "./api";
import { useText } from "./locale";
import { CapsuleButton } from "./ui/controls";
import { readNoteDraft, removeNoteDraft, savedNote, writeNoteDraft, type NoteDraft, type SavedNote } from "./note-local-state";
import "./reader-notes.css";

type State = { saved: SavedNote; local: NoteDraft; editing: boolean; conflict: boolean; canEditPending: boolean; error: string; message: string };
function fromRecord(record: Bookmark): SavedNote {
  return { bookmark_id: record.bookmark_id, note: record.note || "", revision: record.note_revision || 0,
    updated_at: record.note_updated_at || 0, legacy_text: record.legacy_note_text || "" };
}
const message = (error: unknown) => error instanceof Error ? error.message : String(error);

export default function ReaderNotes({ record, emptyToolbar }: { record: Bookmark; emptyToolbar?: HTMLElement | null }) {
  const t = useText();
  const [state, render] = useState<State>(() => {
    const saved = fromRecord(record);
    let local: NoteDraft | null = null;
    try { local = readNoteDraft(localStorage, record.bookmark_id, record.url); } catch { /* Storage can be disabled. */ }
    return { saved, local: local || { version: 1, bookmarkId: record.bookmark_id, url: record.url, draft: saved.note, baseRevision: saved.revision },
      editing: Boolean(local), conflict: Boolean(local && !local.pending && local.baseRevision !== saved.revision), canEditPending: false, error: "", message: "" };
  });
  const current = useRef(state), alive = useRef(true), lock = useRef(false), editor = useRef<HTMLTextAreaElement>(null);
  const [busy, setBusy] = useState(false);
  const update = (next: State) => { current.current = next; if (alive.current) render(next); };
  const persist = (value: NoteDraft) => { try { return writeNoteDraft(localStorage, value); } catch { return false; } };
  const clear = () => { try { return removeNoteDraft(localStorage, record.bookmark_id); } catch { return false; } };
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => {
    const incoming = fromRecord(record), previous = current.current;
    if (incoming.revision <= previous.saved.revision || previous.local.pending) return;
    const dirty = previous.local.draft !== previous.saved.note;
    const local = dirty ? previous.local : { ...previous.local, draft: incoming.note, baseRevision: incoming.revision };
    if (!dirty) clear();
    update({ ...previous, saved: incoming, local, conflict: dirty });
  }, [record.note_revision, record.note, record.note_updated_at, record.legacy_note_text]);
  useEffect(() => { if (state.editing && !state.local.pending) editor.current?.focus({ preventScroll: true }); }, [state.editing]);

  const accepted = (value: unknown, original: NoteDraft) => {
    const result = savedNote(value), operation = original.pending;
    if (!result || !operation || result.bookmark_id !== record.bookmark_id || result.note !== operation.note
        || result.revision !== operation.baseRevision + 1) throw new Error(t("保存回执不完整，请重新读取确认。", "The save receipt is incomplete. Read it again to confirm."));
    // A late response from an unmounted editor cannot erase a newer draft.
    let stored: NoteDraft | null = null;
    try { stored = readNoteDraft(localStorage, record.bookmark_id, record.url); } catch { /* Keep the confirmation in memory. */ }
    if (stored?.pending?.requestId === operation.requestId) clear();
    if (current.current.local.pending?.requestId !== operation.requestId) return;
    update({ ...current.current, saved: result, local: { version: 1, bookmarkId: record.bookmark_id, url: record.url,
      draft: result.note, baseRevision: result.revision }, conflict: false, editing: false, canEditPending: false, error: "",
      message: t("笔记已保存。", "Note saved.") });
  };
  const run = async (work: () => Promise<void>) => {
    if (lock.current) return;
    lock.current = true; setBusy(true);
    try { await work(); }
    catch (error) { update({ ...current.current, error: message(error), message: "" }); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  };
  const send = async (original: NoteDraft) => {
    const operation = original.pending!;
    try {
      const result = await api(`/admin/library/bookmarks/${record.bookmark_id}/note`, { method: "PATCH", timeoutMs: 20_000,
        body: JSON.stringify({ request_id: operation.requestId, note: operation.note, base_revision: operation.baseRevision }) });
      accepted(result, original);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409 && error.details?.code === "note_conflict") {
        const saved = savedNote(error.details.current);
        if (saved?.bookmark_id === record.bookmark_id) {
          const local = { ...original }; delete local.pending;
          const retained = persist(local);
          update({ ...current.current, saved, local, conflict: true, canEditPending: false,
            error: retained ? "" : t("草稿未能在本机保留，请先复制内容。", "The draft could not be kept on this device. Copy it first."), message: "" });
          return;
        }
      }
      throw error;
    }
  };
  const save = () => run(async () => {
    const previous = current.current;
    if (previous.conflict || previous.local.pending) return;
    const local: NoteDraft = { ...previous.local, pending: { requestId: `note-${crypto.randomUUID()}`,
      note: previous.local.draft, baseRevision: previous.local.baseRevision } };
    if (!persist(local)) throw new Error(t("本机草稿无法保存，请先复制笔记再重试。", "The local draft could not be stored. Copy your note before retrying."));
    update({ ...previous, local, canEditPending: false, error: "", message: "" });
    await send(local);
  });
  const confirm = () => run(async () => {
    const previous = current.current, operation = previous.local.pending;
    if (!operation) return;
    try {
      const value = await api<{ action: string; result: unknown }>(`/admin/library/operations/${operation.requestId}`);
      if (value.action !== `note:${record.bookmark_id}`) throw new Error(t("回执对应其他操作，原草稿已保留。", "This receipt belongs to another operation. Your original draft is retained."));
      accepted(value.result, previous.local);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        update({ ...current.current, canEditPending: true, error: "", message: t("尚未找到保存回执。可以重试原保存，或返回修改。", "No save receipt was found. Retry the original save or return to editing.") });
        return;
      }
      throw error;
    }
  });
  const reread = () => run(async () => {
    const value = savedNote(await api(`/admin/library/bookmarks/${record.bookmark_id}/note`));
    if (!value || value.bookmark_id !== record.bookmark_id) throw new Error(t("笔记读取结果不完整，草稿已保留。", "The note response is incomplete. Your draft is retained."));
    const previous = current.current, dirty = previous.local.draft !== previous.saved.note;
    const local = dirty || previous.local.pending ? previous.local : { ...previous.local, draft: value.note, baseRevision: value.revision };
    if (!dirty && !local.pending) clear();
    update({ ...previous, saved: value, local, conflict: !local.pending && local.baseRevision !== value.revision,
      error: "", message: t("已重新读取保存的笔记。", "Saved note reloaded.") });
  });
  const change = (draft: string) => {
    const previous = current.current;
    if (lock.current || previous.local.pending) return;
    const local = { ...previous.local, draft };
    const retained = persist(local);
    update({ ...previous, local, error: retained ? "" : t("本机草稿未能保留，请复制内容后保存。", "The local draft could not be retained. Copy it before saving."), message: "" });
  };
  const start = () => { update({ ...current.current, editing: true, message: "" }); };
  const dirty = state.local.draft !== state.saved.note;
  const empty = !state.editing && !state.saved.note && !dirty && !state.local.pending
    && !state.conflict && !state.error && !state.message && !state.saved.legacy_text;
  const section = <section className={`reader-notes${empty ? " is-empty" : ""}`} data-bookmark-id={record.bookmark_id} aria-label={t("我的笔记", "My note")}>
    <div className="reader-notes-heading">{!empty && <h2><StickyNote size={16} aria-hidden="true"/>{t("我的笔记", "My note")}</h2>}
      {!state.editing && <CapsuleButton type="button" className="text-button" onClick={start}>
        <Pencil size={14} aria-hidden="true"/>{dirty || state.local.pending ? t("继续编辑笔记", "Continue note draft") : state.saved.note ? t("编辑笔记", "Edit note") : t("写笔记", "Write a note")}
      </CapsuleButton>}</div>
    {!state.editing && !empty && (state.saved.note ? <details className="reader-note-saved"><summary>{t("阅读完整笔记", "Read full note")}</summary>
      <p className="reader-note-text">{state.saved.note}</p></details> : <p className="reader-note-invitation">{t("记下收藏的原因，或自己的想法。", "Remember why you saved this page, or add your own thoughts.")}</p>)}
    {!state.editing && dirty && <p className="reader-note-help" role="status">{t("未保存的草稿已保留。", "Your unsaved draft is retained.")}</p>}
    {state.editing && <form className="reader-note-editor" onSubmit={event => { event.preventDefault(); void save(); }}>
      <label htmlFor={`reader-note-${record.bookmark_id}`}>{t("个人阅读笔记", "Personal reading note")}</label>
      <textarea ref={editor} id={`reader-note-${record.bookmark_id}`} value={state.local.draft} maxLength={60_000}
        readOnly={busy || Boolean(state.local.pending)} onChange={event => change(event.currentTarget.value)}
        aria-describedby={`reader-note-help-${record.bookmark_id}`} />
      <p className="reader-note-help" id={`reader-note-help-${record.bookmark_id}`}>
        {t("草稿在本机保留；点击保存写入收藏。完整 JSON 导出包含笔记。", "Drafts stay on this device. Save to keep the note with this page. Full JSON exports include notes.")}</p>
      {state.conflict && <div className="reader-note-conflict" role="status"><p>{t("其他窗口已保存新版本，你的草稿仍在输入框里。", "Another window saved a new version. Your draft remains in the editor.")}</p>
        <details><summary>{t("核对已保存版本", "Review the saved version")}</summary><p className="reader-note-text">{state.saved.note || t("已保存版本为空。", "The saved version is empty.")}</p></details>
        <div className="reader-note-actions"><CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => {
          const local = { ...current.current.local, baseRevision: current.current.saved.revision };
          if (persist(local)) update({ ...current.current, local, conflict: false, error: "", message: t("草稿已保留，可继续修改后保存。", "Your draft is retained. Edit it and save when ready.") });
        }}>{t("保留草稿继续修改", "Keep draft and continue")}</CapsuleButton>
          <CapsuleButton type="button" className="text-button" disabled={busy} onClick={() => {
            const saved = current.current.saved; clear(); update({ ...current.current, local: { ...current.current.local, draft: saved.note, baseRevision: saved.revision }, conflict: false, error: "", message: "" });
          }}>{t("采用已保存版本", "Use saved version")}</CapsuleButton></div></div>}
      {state.local.pending && <div className="reader-note-recovery" role="status"><p>{t("这次保存的结果尚未确认，原内容已保留。重开页面不会自动保存。", "This save has not been confirmed. Its original content is retained. Reopening does not save automatically.")}</p>
        <div className="reader-note-actions"><CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => void confirm()}>{t("读取保存回执", "Read save receipt")}</CapsuleButton>
          <CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => void run(() => send(current.current.local))}>{t("重试原保存", "Retry original save")}</CapsuleButton>
          {state.canEditPending && <CapsuleButton type="button" className="text-button" disabled={busy} onClick={() => {
            const local = { ...current.current.local }; delete local.pending;
            if (persist(local)) update({ ...current.current, local, conflict: local.baseRevision !== current.current.saved.revision, canEditPending: false, message: "", error: "" });
          }}>{t("返回修改", "Return to editing")}</CapsuleButton>}</div></div>}
      {!state.local.pending && <div className="reader-note-actions"><CapsuleButton type="submit" className="primary" disabled={busy || state.conflict || !dirty}>{busy ? t("正在保存…", "Saving…") : t("保存笔记", "Save note")}</CapsuleButton>
        <CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => update({ ...current.current, editing: false })}>{t("收起编辑，保留草稿", "Close editor, keep draft")}</CapsuleButton></div>}
    </form>}
    {state.saved.legacy_text && <details className="reader-note-legacy"><summary>{t("旧版导入保留的文字", "Text retained from an older import")}</summary>
      <p className="reader-note-help">{t("其中可能包含笔记和分类文字，可核对后复制到个人笔记。", "This may contain notes and classification text. Review it and copy useful text into your note.")}</p>
      <p className="reader-note-text">{state.saved.legacy_text}</p></details>}
    {state.error && <div className="reader-note-error" role="alert"><p>{state.error}</p><CapsuleButton type="button" className="secondary" disabled={busy} onClick={() => void reread()}>{t("重读笔记，保留草稿", "Reload note, keep draft")}</CapsuleButton></div>}
    {state.message && <p className="reader-note-message" role="status">{state.message}</p>}
  </section>;
  // Only the truly empty entry shares the reader toolbar. The editor, saved
  // text and recovery states retain their original place in the reading flow.
  return empty && emptyToolbar ? createPortal(section, emptyToolbar) : section;
}
