import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, ChevronDown, Folder, FolderOpen, FolderPlus, Inbox, LoaderCircle, Search } from "lucide-react";
import { api, query } from "./api";
import { useText } from "./locale";
import { OverlayMotion } from "./overlay-motion";
import { useReducedMotion } from "./useReducedMotion";
import "./folder-picker.css";

type FolderPage = { items: { value: string; count: number }[]; total: number; has_more: boolean };

export function FolderPath({ value }: { value: string }) {
  const split = value.lastIndexOf(" / ");
  return <span className="folder-path">{split < 0 ? <span>{value}</span> : <>
    <span>{value.slice(split + 3)}</span><small>{value.slice(0, split)}</small>
  </>}</span>;
}

/** Uses the complete paginated directory, never the overview's top-200 facets.
 * Search is only a draft: a folder changes only after an explicit selection. */
export function FolderPicker({ value, onChange, label, allowCreate = true, allowUnfiled = true }: {
  value: string; onChange: (value: string) => void; label: string;
  allowCreate?: boolean; allowUnfiled?: boolean;
}) {
  const t = useText();
  const reduced = useReducedMotion();
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [request, setRequest] = useState({ q: "", offset: 0 });
  const [page, setPage] = useState<FolderPage>({ items: [], total: 0, has_more: false });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const draft = request.q.trim();

  useEffect(() => {
    if (!open) return;
    search.current?.focus();
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !root.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const abort = new AbortController();
    setLoading(true); setError(false);
    const timer = setTimeout(() => {
      api<FolderPage>(`/bookmarks/facets/folders?${query({ q: draft, offset: request.offset, limit: 50 })}`, { signal: abort.signal })
        .then(data => {
          if (abort.signal.aborted) return;
          setPage(old => ({ ...data, items: request.offset === 0 ? data.items :
            [...new Map([...old.items, ...data.items].map(item => [item.value, item])).values()] }));
        })
        .catch(() => { if (!abort.signal.aborted) setError(true); })
        .finally(() => { if (!abort.signal.aborted) setLoading(false); });
    }, draft ? 180 : 0);
    return () => { clearTimeout(timer); abort.abort(); };
  }, [open, request.q, request.offset, retry]);

  function choose(folder: string) {
    onChange(folder); setOpen(false); trigger.current?.focus({ preventScroll: true });
  }

  function onKeyDown(event: KeyboardEvent) {
    if (!open || event.nativeEvent.isComposing) return;
    if (event.key === "Escape") {
      event.preventDefault(); event.stopPropagation();
      setOpen(false); trigger.current?.focus({ preventScroll: true });
      return;
    }
    // Enter in the search box must never submit the surrounding bookmark form.
    if (event.target === search.current && event.key === "Enter") { event.preventDefault(); return; }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    if (event.target === search.current && ["Home", "End"].includes(event.key)) return;
    const options = [...(root.current?.querySelectorAll<HTMLButtonElement>("[data-folder-option]:not(:disabled)") ?? [])];
    if (!options.length) return;
    event.preventDefault();
    const index = options.indexOf(event.target as HTMLButtonElement);
    const next = event.key === "Home" ? 0 : event.key === "End" ? options.length - 1 :
      event.key === "ArrowDown" ? (index + 1) % options.length : index < 0 ? options.length - 1 : (index - 1 + options.length) % options.length;
    options[next].focus();
  }

  const selectedMissing = value && !draft && !page.items.some(item => item.value === value);
  const canCreate = allowCreate && draft && !loading && !error &&
    draft !== value && !page.items.some(item => item.value === draft);
  return <div className="folder-picker field" ref={root} data-open={open} onKeyDown={onKeyDown}
    onBlur={event => { if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <span id={`${id}-label`}>{label}</span>
    <motion.button data-overlay-motion type="button" className="folder-picker-trigger" ref={trigger} aria-expanded={open}
      whileTap={reduced ? undefined : { scale: 0.985 }} transition={{ duration: 0.12 }}
      aria-controls={`${id}-panel`} aria-labelledby={`${id}-label ${id}-value`}
      onClick={() => {
        if (!open) { setRequest({ q: "", offset: 0 }); setPage({ items: [], total: 0, has_more: false }); setLoading(true); }
        setOpen(!open);
      }}>
      {value ? <FolderOpen size={18} /> : <Inbox size={18} />}
      <motion.span key={value} id={`${id}-value`} initial={reduced ? false : { opacity: 0.65, y: 3 }}
        animate={{ opacity: 1, y: 0 }} transition={{ duration: reduced ? 0 : 0.18 }}>
        {value || (allowUnfiled ? t("未分类", "Unfiled") : t("选择文件夹", "Choose a folder"))}
      </motion.span>
      <ChevronDown size={16} className="folder-picker-chevron" />
    </motion.button>
    <AnimatePresence>
    {open && <OverlayMotion key="folder-menu" id={`${id}-panel`} className="folder-picker-panel" role="region" aria-labelledby={`${id}-label`}>
      <label className="folder-picker-search"><Search size={17} aria-hidden="true" />
        <input ref={search} value={request.q} aria-label={t("搜索文件夹", "Search folders")}
          maxLength={2048} placeholder={allowCreate ? t("搜索或输入新文件夹名称…", "Search or enter a new folder name…") : t("搜索文件夹…", "Search folders…")}
          onChange={event => { setRequest({ q: event.target.value, offset: 0 }); setPage({ items: [], total: 0, has_more: false }); setLoading(true); setError(false); }} />
      </label>
      <div className="folder-picker-options" aria-busy={loading}>
        {allowUnfiled && <motion.button data-overlay-motion type="button" data-folder-option aria-pressed={value === ""} onClick={() => choose("")}
          whileTap={reduced ? undefined : { scale: 0.98 }}>
          <Inbox size={17}/><span>{t("未分类", "Unfiled")}</span>{value === "" && <Check size={16}/>}
        </motion.button>}
        {selectedMissing && <motion.button data-overlay-motion type="button" data-folder-option title={value} aria-pressed="true" onClick={() => choose(value)}
          whileTap={reduced ? undefined : { scale: 0.98 }}>
          <FolderOpen size={17}/><FolderPath value={value}/><Check size={16}/>
        </motion.button>}
        {page.items.map(item => <motion.button data-overlay-motion type="button" key={item.value} data-folder-option title={item.value}
          whileTap={reduced ? undefined : { scale: 0.98 }}
          aria-pressed={value === item.value} onClick={() => choose(item.value)}>
          <Folder size={17}/><FolderPath value={item.value}/>
          {value === item.value ? <Check size={16}/> : <small className="folder-picker-count">{item.count.toLocaleString()}</small>}
        </motion.button>)}
        {error ? <div className="folder-picker-feedback" role="alert">
          <span>{t("无法加载文件夹。", "Could not load folders.")}</span>
          <button type="button" className="text-button" onClick={() => setRetry(old => old + 1)}>{t("重试", "Retry")}</button>
        </div> : loading ? <p className="folder-picker-feedback" role="status"><LoaderCircle size={16} className="spin"/>{t("正在加载…", "Loading…")}</p>
          : !page.items.length ? <p className="folder-picker-feedback">{draft ? t("没有匹配的文件夹", "No matching folders") : t("还没有文件夹", "No folders yet")}</p> : null}
        {!error && page.has_more && <button type="button" className="folder-picker-more" disabled={loading}
          onClick={() => setRequest(old => ({ ...old, offset: page.items.length }))}>
          {t(`加载更多（${page.items.length} / ${page.total}）`, `Load more (${page.items.length} / ${page.total})`)}
        </button>}
        {canCreate && <motion.button data-overlay-motion type="button" data-folder-option className="folder-picker-create" onClick={() => choose(draft)}
          whileTap={reduced ? undefined : { scale: 0.98 }}>
          <FolderPlus size={18}/><span>{t(`使用新文件夹「${draft}」`, `Use new folder “${draft}”`)}</span>
        </motion.button>}
      </div>
      {allowCreate && <p className="folder-picker-note">{t("新文件夹会在保存收藏时创建；用「 / 」分隔层级。", "New folders are created when you save. Use “ / ” for nested paths.")}</p>}
    </OverlayMotion>}
    </AnimatePresence>
  </div>;
}
