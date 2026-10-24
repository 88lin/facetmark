import { useEffect, useId, useRef, useState, type CSSProperties, type KeyboardEvent, type RefObject } from "react";
import { AnimatePresence, motion, useIsPresent } from "motion/react";
import { ChevronRight, LoaderCircle } from "lucide-react";
import { api, query } from "./api";
import { CollectionFolderIcon } from "./CollectionFolderIcon";
import { useText } from "./locale";
import { useReducedMotion } from "./useReducedMotion";
import { CapsuleButton } from "./ui/controls";
import "./folder-tree.css";

type Folder = { value: string; label: string; count: number; has_children: boolean };
type FolderPage = { items: Folder[]; total: number; has_more: boolean };
type CachedPage = { revision: number; page: FolderPage; offset: number };
type TreeProps = {
  selected?: string; folderPath?: string[]; enabled: boolean; revision: number;
  onSelect: (folder: string) => void;
};
type BranchProps = TreeProps & {
  parent: string; depth: number; expanded: Set<string>;
  cache: RefObject<Map<string, CachedPage>>;
  toggle: (folder: string) => void;
};

function ancestors(parts: string[] = []) {
  return parts.slice(0, -1).map((_, index) => parts.slice(0, index + 1).join("/"));
}

/** Each visible branch requests one bounded server page. Closing it aborts its
 * request. A library revision hides stale entries before the next effect runs. */
function FolderBranch({ parent, depth, enabled, revision, selected, expanded, toggle, onSelect, cache }: BranchProps) {
  const t = useText();
  const cached = cache.current.get(parent);
  const initial = cached?.revision === revision ? cached : null;
  const [cursor, setCursor] = useState({ revision, offset: initial?.offset || 0 });
  const offset = cursor.revision === revision ? cursor.offset : 0;
  const [snapshot, setSnapshot] = useState<CachedPage | null>(initial);
  const [pending, setPending] = useState(!initial);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const lastRetry = useRef(0);
  const page = snapshot?.revision === revision ? snapshot.page : null;
  const loading = pending || (!page && !error);
  useEffect(() => {
    if (!enabled) return;
    const known = cache.current.get(parent);
    const force = lastRetry.current !== retry;
    lastRetry.current = retry;
    if (!force && known?.revision === revision && known.offset === offset) {
      setSnapshot(known); setPending(false); setError(false); return;
    }
    const controller = new AbortController();
    setPending(true); setError(false);
    api<FolderPage>(`/bookmarks/folders/tree?${query({ parent, limit: 50, offset })}`, { signal: controller.signal })
      .then(data => {
        if (controller.signal.aborted) return;
        const previous = cache.current.get(parent);
        const next = { revision, offset, page: { ...data, items: offset === 0 ? data.items :
          [...new Map([...(previous?.revision === revision ? previous.page.items : []), ...data.items]
            .map(item => [item.value, item])).values()] } };
        cache.current.set(parent, next);
        setSnapshot(next);
      })
      .catch(() => { if (!controller.signal.aborted) setError(true); })
      .finally(() => { if (!controller.signal.aborted) setPending(false); });
    return () => controller.abort();
  }, [enabled, parent, revision, offset, retry, cache]);

  return <ul className="facet-tree-branch" aria-busy={loading} aria-label={parent || t("顶层文件夹", "Top-level folders")}>
    {page?.items.map(folder => <FolderNode key={folder.value} folder={folder} parent={parent} depth={depth}
      selected={selected} enabled={enabled} revision={revision} expanded={expanded} toggle={toggle} onSelect={onSelect} cache={cache} />)}
    {error ? <li className="facet-tree-feedback" role="alert">
      <p>{t(parent ? "子文件夹暂时无法加载。" : "文件夹暂时无法加载。",
        parent ? "Subfolders could not be loaded." : "Folders could not be loaded.")}</p>
      <CapsuleButton type="button" className="facet-retry" onClick={() => setRetry(value => value + 1)}>{t("重试", "Retry")}</CapsuleButton>
    </li> : loading ? <li className="facet-tree-feedback" role="status">
      <LoaderCircle size={15} className="spin" />{t("正在加载文件夹…", "Loading folders…")}
    </li> : !page?.items.length ? <li className="facet-tree-feedback">{t("还没有文件夹", "No folders yet")}</li> : null}
    {!error && page?.has_more && <li className="facet-tree-more">
      <CapsuleButton type="button" className="facet-load-more" disabled={loading}
        onClick={() => setCursor({ revision, offset: page.items.length })}>
        {t(`显示更多${parent ? "子文件夹" : "文件夹"}（${page.items.length} / ${page.total}）`,
          `Show more ${parent ? "subfolders" : "folders"} (${page.items.length} / ${page.total})`)}
      </CapsuleButton>
    </li>}
  </ul>;
}

function FolderNode({ folder, ...tree }: BranchProps & { folder: Folder }) {
  const t = useText();
  const id = useId();
  const open = tree.expanded.has(folder.value);
  const selected = tree.selected === folder.value;
  const canSelect = folder.count > 0;
  return <li className="facet-tree-node" data-folder-node={folder.value}>
    <div className="facet-tree-row" style={{ "--folder-depth": Math.min(tree.depth, 3) } as CSSProperties}>
      {folder.has_children ? <CapsuleButton type="button" className="facet-expand"
        aria-label={t(`${open ? "收起" : "展开"}「${folder.label}」`, `${open ? "Collapse" : "Expand"} “${folder.label}”`)}
        aria-expanded={open} aria-controls={id} onClick={() => tree.toggle(folder.value)}>
        <ChevronRight size={14} aria-hidden="true" />
      </CapsuleButton> : <span className="facet-tree-spacer" aria-hidden="true" />}
      <CapsuleButton type="button" className="facet-option facet-folder-select" title={folder.value}
        data-folder-select={folder.value} data-exact-folder={canSelect}
        aria-label={canSelect ? `${folder.value} ${folder.count}` : t(`${folder.value}，浏览子文件夹`, `${folder.value}, browse subfolders`)}
        aria-pressed={canSelect ? selected : undefined}
        aria-expanded={!canSelect && folder.has_children ? open : undefined}
        aria-controls={!canSelect && folder.has_children ? id : undefined}
        onClick={() => canSelect ? tree.onSelect(folder.value) : tree.toggle(folder.value)}>
        <CollectionFolderIcon active={selected} expanded={open} size={24} />
        <span className="facet-label">{folder.label}</span>
        <small className="facet-count" title={canSelect ? t("此文件夹中的收藏数，不含子目录", "Saved pages in this exact folder, excluding subfolders") : undefined}>
          {canSelect ? folder.count.toLocaleString() : ""}
        </small>
      </CapsuleButton>
    </div>
    <AnimatePresence initial={false}>
      {folder.has_children && open && <FolderChildren key={folder.value} {...tree} parent={folder.value} depth={tree.depth + 1} id={id} />}
    </AnimatePresence>
  </li>;
}

function FolderChildren({ id, ...tree }: BranchProps & { id: string }) {
  const present = useIsPresent();
  const reduced = useReducedMotion();
  return <motion.div id={id} className="facet-tree-children" inert={!present} aria-hidden={!present}
    initial={reduced ? false : { height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
    exit={{ height: reduced ? "auto" : 0, opacity: 0 }}
    transition={{ height: { duration: reduced ? 0 : 0.24, ease: [0.22, 1, 0.36, 1] }, opacity: { duration: reduced ? 0 : 0.16 } }}>
    <FolderBranch {...tree} enabled={tree.enabled && present} />
  </motion.div>;
}

export function FolderTree(props: TreeProps) {
  const root = useRef<HTMLDivElement>(null);
  const cache = useRef(new Map<string, CachedPage>());
  const previousRevision = useRef(props.revision);
  useEffect(() => {
    if (previousRevision.current !== props.revision) {
      cache.current.clear(); previousRevision.current = props.revision;
    }
  }, [props.revision]);
  const [expanded, setExpanded] = useState(() => new Set(ancestors(props.folderPath)));
  useEffect(() => {
    if (!props.folderPath?.length) return;
    setExpanded(previous => new Set([...previous, ...ancestors(props.folderPath)]));
  }, [props.folderPath]);
  const toggle = (folder: string) => setExpanded(previous => {
    const next = new Set(previous);
    if (next.has(folder)) next.delete(folder); else next.add(folder);
    return next;
  });
  function onKeyDown(event: KeyboardEvent) {
    if (event.nativeEvent.isComposing || !(event.target instanceof HTMLButtonElement) || !event.target.hasAttribute("data-folder-select")) return;
    const value = event.target.dataset.folderSelect!;
    const buttons = [...root.current!.querySelectorAll<HTMLButtonElement>("[data-folder-select]")]
      .filter(button => !button.closest("[inert], [hidden]"));
    const index = buttons.indexOf(event.target);
    const focus = (button?: HTMLButtonElement) => button?.focus({ preventScroll: false });
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      focus(buttons[event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 :
        Math.max(0, Math.min(buttons.length - 1, index + (event.key === "ArrowDown" ? 1 : -1)))]);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      const node = event.target.closest(".facet-tree-node")!;
      if (node.querySelector(":scope > .facet-tree-row > .facet-expand")) {
        if (!expanded.has(value)) toggle(value);
        else {
          const branch = node.querySelector(":scope > .facet-tree-children");
          focus(buttons.find(button => branch?.contains(button)));
        }
      }
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      if (expanded.has(value)) toggle(value);
      else {
        const parentNode = event.target.closest(".facet-tree-node")?.parentElement?.closest(".facet-tree-node");
        focus(parentNode?.querySelector<HTMLButtonElement>(":scope > .facet-tree-row [data-folder-select]") || undefined);
      }
    }
  }
  return <div className="facet-folder-tree" ref={root} onKeyDown={onKeyDown}>
    <FolderBranch {...props} parent="" depth={0} expanded={expanded} toggle={toggle} cache={cache} />
  </div>;
}
