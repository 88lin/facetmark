import { useEffect, useRef, useState } from "react";
import { Check, Folder, Globe2, LoaderCircle, Search, Tags, X } from "lucide-react";
import { api, query } from "./api";
import { useText } from "./locale";

type Field = "folder" | "tag" | "domain";
type Group = "folders" | "tags" | "domains";
type Facet = { value: string; count: number };
type FacetPage = { items: Facet[]; total: number; has_more: boolean };

export function FacetBrowser({ filters, enabled = true, revision, onSelect }: {
  filters: { folder?: string; tag?: string; domain?: string; session?: number };
  enabled?: boolean;
  revision: number;
  onSelect: (field: Field, value: string | undefined) => void;
}) {
  const t = useText();
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
  const field: Field = group === "folders" ? "folder" : group === "tags" ? "tag" : "domain";
  const groups = [
    { key: "folders" as const, label: t("文件夹", "Folders"), Icon: Folder },
    { key: "tags" as const, label: t("标签", "Tags"), Icon: Tags },
    { key: "domains" as const, label: t("站点", "Sites"), Icon: Globe2 },
  ];

  useEffect(() => { setOffset(0); }, [revision]);
  useEffect(() => {
    if (!enabled) return;
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
  }, [group, text, offset, retry, revision, enabled]);

  function resetList() {
    setOffset(0);
    setItems([]);
    setMore(false);
    setLoading(true);
    scroller.current?.scrollTo({ top: 0 });
  }

  return <section className="facet-browser" aria-label={t("分类与筛选", "Categories and filters")}>
    <div className="facet-browser-heading">
      <h2>{t("分类", "Categories")}</h2>
      <span>{text ? t("精确匹配优先", "Exact first") : t("按名称排列", "A–Z")}</span>
    </div>
    <div className="facet-types" role="group" aria-label={t("分类类型", "Category type")}>
      {groups.map(({ key, label, Icon }) => <button key={key} type="button"
        aria-pressed={group === key} onClick={() => {
          if (group === key) return;
          resetList(); setText(""); setGroup(key);
        }}><Icon size={14} /><span>{label}</span></button>)}
    </div>
    <label className="facet-search">
      <Search size={15} aria-hidden="true" />
      <input aria-label={t("查找分类", "Find a category")} value={text}
        placeholder={t("查找分类…", "Find a category…")} maxLength={512}
        onChange={e => { resetList(); setText(e.target.value); }} />
      {text && <button type="button" aria-label={t("清空分类搜索", "Clear category search")}
        onClick={() => { resetList(); setText(""); }}><X size={14} /></button>}
    </label>
    <nav className="facet-options" ref={scroller} tabIndex={0}
      aria-label={group === "folders" ? t("按文件夹浏览", "Browse by folder") :
        group === "tags" ? t("按标签浏览", "Browse by tag") : t("按站点浏览", "Browse by site")}
      aria-busy={loading}>
      <button className="facet-option facet-any" type="button" aria-pressed={filters[field] === undefined}
        onClick={() => onSelect(field, undefined)}>
        <span>{group === "folders" ? t("全部文件夹", "All folders") :
          group === "tags" ? t("不限标签", "Any tag") : t("不限站点", "Any site")}</span>
        {filters[field] === undefined && <Check size={14} aria-hidden="true" />}
      </button>
      {group === "folders" && !text && <button className="facet-option" type="button"
        aria-pressed={filters.folder === ""} onClick={() => onSelect("folder", "")}>
        <span>{t("未分类", "Unfiled")}</span>
        {filters.folder === "" && <Check size={14} aria-hidden="true" />}
      </button>}
      {items.map(item => <button className="facet-option" key={item.value} type="button"
        title={item.value} aria-pressed={filters[field] === item.value}
        onClick={() => onSelect(field, item.value)}>
        <span>{item.value}</span><small>{item.count}</small>
      </button>)}
      {error ? <div className="facet-feedback" role="alert">
        <p>{t("分类暂时无法加载。", "Categories could not be loaded.")}</p>
        <button className="text-button" onClick={() => setRetry(value => value + 1)}>{t("重试", "Retry")}</button>
      </div> : loading ? <div className="facet-feedback" role="status">
        <LoaderCircle size={15} className="spin" />{t("正在加载…", "Loading…")}
      </div> : !items.length ? <p className="facet-feedback">{t("没有匹配的分类", "No matching categories")}</p> : null}
      {!error && more && <button className="facet-load-more" type="button" disabled={loading}
        onClick={() => setOffset(items.length)}>{t("显示更多分类", "Show more categories")}</button>}
    </nav>
    <span className="facet-range" aria-live="polite">
      {!loading && !error ? t(`${items.length} / ${total} 个分类`, `${items.length} of ${total} categories`) : ""}
    </span>
  </section>;
}
