import { CapsuleButton } from "./ui/controls";
import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown, Globe2, Inbox, LoaderCircle, Search, Settings2, Tags, X } from "lucide-react";
import { api, query } from "./api";
import { useText } from "./locale";
import { SelectionPill, useContentMotion } from "./InteractionMotion";
import { CollectionFolderIcon } from "./CollectionFolderIcon";
import { FolderTree } from "./FolderTree";
import "./facet-browser.css";

type Field = "folder" | "tag" | "domain";
type Group = "folders" | "tags" | "domains";
type Facet = { value: string; count: number };
type FacetPage = { items: Facet[]; total: number; has_more: boolean };

export function FacetBrowser({ filters, folderPath, enabled = true, revision, onSelect, onManage }: {
  filters: { folder?: string; tag?: string; domain?: string; session?: number };
  folderPath?: string[];
  enabled?: boolean;
  revision: number;
  onSelect: (field: Field, value: string | undefined) => void;
  onManage?: () => void;
}) {
  const t = useText();
  const groupId = useId();
  const [group, setGroup] = useState<Group>("folders");
  const [text, setText] = useState("");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<Facet[]>([]);
  const [total, setTotal] = useState(0);
  const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const scroller = useRef<HTMLElement>(null);
  useContentMotion(scroller, group, undefined, "x");
  const field: Field = group === "folders" ? "folder" : group === "tags" ? "tag" : "domain";
  const browseFolders = group === "folders" && !text;
  const groups = [
    { key: "folders" as const, label: t("文件夹", "Folders") },
    { key: "tags" as const, label: t("标签", "Tags") },
    { key: "domains" as const, label: t("站点", "Sites") },
  ];

  useEffect(() => { setOffset(0); }, [revision]);
  useEffect(() => {
    if (!enabled) return;
    if (browseFolders) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    setError(false);
    const timer = setTimeout(() => {
      api<FacetPage>(`/bookmarks/facets/${group}?${query({ q: text, limit: 50, offset })}`, {
        signal: controller.signal,
      }).then((data) => {
        if (controller.signal.aborted) return;
        setItems((old) => offset === 0 ? data.items :
          [...new Map([...old, ...data.items].map(item => [item.value, item])).values()]);
        setTotal(data.total);
        setMore(data.has_more);
      }).catch(() => {
        if (!controller.signal.aborted) setError(true);
      }).finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    }, text ? 180 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [group, text, offset, retry, revision, enabled, browseFolders]);

  function resetList() {
    setOffset(0);
    setItems([]);
    setMore(false);
    setLoading(true);
    scroller.current?.scrollTo({ top: 0 });
  }

  return <section className="facet-browser" aria-label={t("分类与筛选", "Categories and filters")}>
    <div className="facet-browser-toolbar">
    <div className="facet-types" role="group" aria-label={t("分类类型", "Category type")}>
      {groups.map(({ key, label }) => <CapsuleButton key={key} type="button" className="facet-type"
        aria-label={label} title={label} aria-pressed={group === key} onClick={() => {
          if (group === key) return;
          resetList(); setText(""); setGroup(key);
        }}><SelectionPill active={group === key} group={`${groupId}-directory-type`} />
          {key === "folders" ? <CollectionFolderIcon size={19} active={group === key}/> : <span>{label}</span>}
        </CapsuleButton>)}
    </div>
      {onManage && <CapsuleButton type="button" className="facet-manage" onClick={onManage}
        title={t("整理文件夹与标签", "Organize folders and tags")} aria-label={t("整理文件夹与标签", "Organize folders and tags")}><Settings2 size={16}/></CapsuleButton>}
    </div>
    <label className="facet-search">
      <Search size={15} aria-hidden="true" />
      <input aria-label={t("查找分类", "Find a category")} value={text}
        placeholder={group === "folders" ? t("搜索文件夹…", "Search folders…") : group === "tags" ? t("搜索标签…", "Search tags…") : t("搜索站点…", "Search sites…")} maxLength={2048}
        onChange={e => { resetList(); setText(e.target.value); }} />
      {text && <CapsuleButton type="button" className="facet-search-clear" aria-label={t("清空分类搜索", "Clear category search")}
        onClick={() => { resetList(); setText(""); }}><X size={14} /></CapsuleButton>}
    </label>
    {browseFolders && filters.folder && <details className="facet-location">
      <summary title={filters.folder}><CollectionFolderIcon active/><span>{folderPath?.at(-1) || filters.folder}</span><ChevronDown size={14}/></summary>
      <p title={filters.folder}>{folderPath?.join(" / ") || filters.folder}</p>
      <CapsuleButton type="button" className="facet-locate" onClick={() => { resetList(); setText(filters.folder!); }}>
        <Search size={14}/>{t("定位当前文件夹", "Find this folder")}
      </CapsuleButton>
    </details>}
    {!browseFolders && filters[field] && !items.some(item => item.value === filters[field]) && <CapsuleButton type="button" className="facet-current"
      title={filters[field]} onClick={() => { resetList(); setText(filters[field]!); setRetry(value => value + 1); }}>
      <Check size={15}/><span>{filters[field]}</span><Search size={14}/>
    </CapsuleButton>}
    <nav className="facet-options" ref={scroller} tabIndex={0}
      aria-label={group === "folders" ? t("按文件夹浏览", "Browse by folder") :
        group === "tags" ? t("按标签浏览", "Browse by tag") : t("按站点浏览", "Browse by site")}
      aria-busy={loading}>
      <CapsuleButton className="facet-option facet-any" type="button" aria-pressed={filters[field] === undefined}
        onClick={() => onSelect(field, undefined)}>
        {group === "folders" ? <CollectionFolderIcon active={filters.folder === undefined}/> : group === "tags" ? <Tags size={18}/> : <Globe2 size={18}/>}
        <span className="facet-label">{group === "folders" ? t("全部文件夹", "All folders") :
          group === "tags" ? t("不限标签", "Any tag") : t("不限站点", "Any site")}</span>
        <span className="facet-count"/>
        <Check className="facet-selected-mark" size={14} aria-hidden="true" />
      </CapsuleButton>
      {group === "folders" && !text && <CapsuleButton className="facet-option" type="button"
        aria-pressed={filters.folder === ""} onClick={() => onSelect("folder", "")}>
        <Inbox size={18}/>
        <span className="facet-label">{t("未分类", "Unfiled")}</span>
        <span className="facet-count"/>
        <Check className="facet-selected-mark" size={14} aria-hidden="true" />
      </CapsuleButton>}
      <div className="facet-tree-container" hidden={!browseFolders}>
        <FolderTree selected={filters.folder} folderPath={folderPath} enabled={enabled && browseFolders} revision={revision}
          onSelect={folder => onSelect("folder", folder)} />
      </div>
      {!browseFolders && items.map(item => {
        const split = group === "folders" ? item.value.lastIndexOf(" / ") : -1;
        return <CapsuleButton className="facet-option" key={item.value} type="button"
          title={item.value} aria-label={`${item.value} ${item.count}`} aria-pressed={filters[field] === item.value}
          onClick={() => onSelect(field, item.value)}>
          {group === "folders" ? <CollectionFolderIcon active={filters.folder === item.value}/> : group === "tags" ? <Tags size={18}/> : <Globe2 size={18}/>}
          <span className="facet-label">{split >= 0 ? <><span>{item.value.slice(split + 3)}</span><small className="facet-parent">{item.value.slice(0, split)}</small></> : item.value}</span>
          <small className="facet-count">{item.count.toLocaleString()}</small>
          <Check className="facet-selected-mark" size={14} aria-hidden="true"/>
        </CapsuleButton>;
      })}
      {!browseFolders && (error ? <div className="facet-feedback" role="alert">
        <p>{t("分类暂时无法加载。", "Categories could not be loaded.")}</p>
        <CapsuleButton type="button" className="facet-retry" onClick={() => setRetry(value => value + 1)}>{t("重试", "Retry")}</CapsuleButton>
      </div> : loading ? <div className="facet-feedback" role="status">
        <LoaderCircle size={15} className="spin" />{t("正在加载…", "Loading…")}
      </div> : !items.length ? <p className="facet-feedback">{t("没有匹配的分类", "No matching categories")}</p> : null)}
      {!browseFolders && !error && more && <CapsuleButton className="facet-load-more" type="button" disabled={loading}
        onClick={() => setOffset(items.length)}>{t("显示更多分类", "Show more categories")}</CapsuleButton>}
    </nav>
    <span className={browseFolders ? "sr-only" : "facet-range"} aria-live="polite">
      {browseFolders ? t("展开箭头浏览子目录", "Expand an arrow to browse subfolders") :
        !loading && !error ? t(`${items.length} / ${total} 个分类`, `${items.length} of ${total} categories`) : ""}
    </span>
  </section>;
}
