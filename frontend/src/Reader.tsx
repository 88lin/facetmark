import { CapsuleButton } from "./ui/controls";
import { useLayoutEffect, useMemo, useRef, type ReactNode } from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  ChevronDown,
  FileText,
  Folder,
  Maximize2,
  Minimize2,
  PanelRightClose,
  Pencil,
  Sparkles,
  Tags,
  Trash2,
} from "lucide-react";
import { type Bookmark, post, safeUrl } from "./api";
import { useText, type Language } from "./locale";
import { SearchExplanation } from "./SearchTools";
import { ScrollProgress } from "./components/ui/scroll-progress";
import { ReaderOutline } from "./components/ui/reader-outline";
import { useTabIndicator } from "./motion";
import { type LibraryAction } from "./LibraryTools";

export function Skeleton({ rows = false }: { rows?: boolean }) {
  return (
    <div className={rows ? "skeleton-list" : "skeleton-article"} aria-hidden="true">
      {Array.from({ length: rows ? 6 : 4 }, (_, i) => (
        <div className="skeleton-group" key={i}>
          <span />
          <span />
          <span />
        </div>
      ))}
    </div>
  );
}

export default function Reader({
  record,
  selected,
  pending,
  error,
  related,
  relatedLoading,
  relatedError,
  tab,
  setTab,
  hit,
  search,
  language,
  onClose,
  onRetry,
  onSelect,
  onQuery,
  onTag,
  focus,
  onFocus,
  canFocus,
  position,
  total,
  onPrevious,
  onNext,
  onAction,
  running,
}: {
  record: Bookmark | null;
  selected: number | null;
  pending: boolean;
  error: string;
  related: Bookmark[];
  relatedLoading: boolean;
  relatedError: string;
  tab: string;
  setTab: (tab: string) => void;
  hit?: Bookmark;
  search: string;
  language: Language;
  onClose: () => void;
  onRetry: () => void;
  onSelect: (id: number) => void;
  onQuery: (query: string) => void;
  onTag: (tag: string) => void;
  focus: boolean;
  onFocus: () => void;
  canFocus: boolean;
  position: number;
  total: number;
  onPrevious?: () => void;
  onNext?: () => void;
  onAction?: (action: LibraryAction) => void;
  running: boolean;
}) {
  const t = useText();
  const scroller = useRef<HTMLDivElement>(null);
  const scrollPositions = useRef<Record<string, number>>({});
  const tabs = useTabIndicator(`${tab}-${language}`);
  const hasSummary = Boolean(record?.summary && (record.ai_title || record.indexed?.enriched_by
    || record.indexed?.summary_basis === "karakeep"));
  const paragraphs = useMemo(
    () =>
      (record?.body_text || "")
        .split(/\n\s*\n/)
        .filter((p, i) => p.trim() && (i !== 0 || p.trim() !== record?.title)),
    [record?.body_text, record?.title],
  );
  // Only explicit Markdown headings become sections. Plain source text is never
  // reinterpreted as a heading merely because it happens to be short.
  const sections = useMemo(
    () => [
      { id: "reader-start", label: t("阅读开头", "Start of reading") },
      ...(hasSummary ? [{ id: "reader-summary", label: t("AI 概览", "AI overview") }] : []),
      ...(record?.body_text ? [{ id: "reader-source", label: t("保存的原文", "Saved source text") }] : []),
      ...paragraphs.flatMap((p, i) =>
        /^#{1,3}\s+[^\n]+$/.test(p.trim())
          ? [{ id: `reader-section-${i}`, label: p.replace(/^#{1,3}\s+/, "") }]
          : [],
      ),
    ],
    [paragraphs, language, hasSummary, record?.body_text],
  );
  useLayoutEffect(() => {
    scrollPositions.current = {};
    if (scroller.current) scroller.current.scrollTop = 0;
  }, [selected]);
  useLayoutEffect(() => {
    if (scroller.current) scroller.current.scrollTop = scrollPositions.current[tab] || 0;
  }, [tab]);
  const changeTab = (value: string) => {
    if (scroller.current) scrollPositions.current[tab] = scroller.current.scrollTop;
    setTab(value);
  };
  const outlineSections = useMemo(() => sections.slice(1), [sections]);
  const showOutline = focus && tab === "body" && !pending && !error && outlineSections.length > 1;
  const visibleRecord = record || hit;
  const managed = Boolean(record?.managed_externally || record?.source === "karakeep");
  const canProcess = Boolean(record && !record.privacy_skipped && onAction);
  const original = safeUrl(visibleRecord?.url || "");
  let content: ReactNode;
  if (pending)
    content = (
      <>
        <span className="sr-only" role="status">
          {t("正在读取…", "Loading page…")}
        </span>
        <Skeleton />
      </>
    );
  else if (error)
    content = (
      <div className="reading-empty">
        <h3>{t("暂时无法读取这条收藏", "This page could not be loaded")}</h3>
        <p className="error" role="alert">
          {error}
        </p>
        <CapsuleButton className="secondary" onClick={onRetry}>
          {t("重试", "Retry")}
        </CapsuleButton>
      </div>
    );
  else if (tab === "body")
    content = record?.body_text || hasSummary ? (
      <>
      {hasSummary ? <section id="reader-summary" className="reader-summary" aria-label={t("AI 概览", "AI overview")}>
        <div className="reader-section-heading">
          <h2><Sparkles size={16}/>{t("AI 概览", "AI overview")}</h2>
          {canProcess && <CapsuleButton className="text-button" disabled={running}
            aria-label={t("重新生成这篇摘要", "Regenerate this summary")}
            onClick={() => onAction?.({ kind: "process", mode: "summarize", ids: [selected!] })}>
            {t("重新生成", "Regenerate")}
          </CapsuleButton>}
        </div>
        <p className="reader-summary-basis">{record?.indexed?.summary_basis === "title"
          ? t("基于标题与网址推断，尚未读取正文", "Inferred from title and URL; page text has not been read")
          : record?.indexed?.summary_basis === "karakeep" ? t("来自 Karakeep 的摘要", "Summary from Karakeep")
            : t("基于保存的原文生成", "Generated from saved source text")}</p>
        <p className="reader-summary-text">{record?.summary}</p>
        {!!record?.key_points?.length && <ul>{record.key_points.map((point, i) => <li key={i}>{point}</li>)}</ul>}
      </section> : canProcess && <div className="reader-summary-invitation">
        <span>{t("为这篇收藏生成标题、摘要和要点", "Generate a title, summary and key points for this page")}</span>
        <CapsuleButton className="secondary" disabled={running}
          onClick={() => onAction?.({ kind: "process", mode: "summarize", ids: [selected!] })}>
          <Sparkles size={15}/>{t("生成这篇摘要", "Summarize this page")}
        </CapsuleButton>
      </div>}
      {record?.summary_error && <p className="reader-summary-error" role="status">
        {hasSummary ? t("最近一次生成失败，已保留上次摘要。", "The last generation failed. The previous summary is retained.")
          : t("摘要生成失败。", "Summary generation failed.")} {record.summary_error}
      </p>}
      <section id="reader-source" className="reader-source" aria-label={t("保存的原文", "Saved source text")}>
      <div className="reader-section-heading"><h2><FileText size={16}/>{t("保存的原文", "Saved source text")}</h2></div>
      {record?.body_text ? <div className="body-text">
        {paragraphs.map((p, i) =>
          /^#{1,3}\s+[^\n]+$/.test(p.trim()) ? (
            <h2 id={`reader-section-${i}`} key={i}>
              {p.replace(/^#{1,3}\s+/, "")}
            </h2>
          ) : (
            <p key={i}>{p}</p>
          ),
        )}
      </div> : <div className="reader-source-missing">
        <p>{t("正文尚未保存，提取后可在这里接着读。", "Source text has not been saved. Fetch it to continue reading here.")}</p>
        {canProcess && <CapsuleButton className="secondary" disabled={running}
          onClick={() => onAction?.({ kind: "process", mode: "fetch", ids: [selected!] })}>
          <FileText size={15}/>{t("提取这篇正文", "Fetch this page")}
        </CapsuleButton>}
      </div>}
      </section>
      </>
    ) : (
      <div className="reading-empty">
        <FileText size={24} />
        <h3>{t("还没有阅读内容", "No reading content yet")}</h3>
        <p>
          {t(
            "提取正文即可在这里阅读，也可以先根据标题与网址生成 AI 概览。",
            "Fetch source text to read here, or generate an AI overview from the title and URL first.",
          )}
        </p>
        {record?.summary_error && <p className="error" role="status">{record.summary_error}</p>}
        {canProcess && <div className="reader-empty-actions">
          <CapsuleButton className="secondary" disabled={running} onClick={() => onAction?.({ kind: "process", mode: "fetch", ids: [selected!] })}><FileText size={15}/>{t("提取这篇正文", "Fetch this page")}</CapsuleButton>
          <CapsuleButton className="secondary" disabled={running} onClick={() => onAction?.({ kind: "process", mode: "summarize", ids: [selected!] })}><Sparkles size={15}/>{t("生成这篇摘要", "Summarize this page")}</CapsuleButton>
        </div>}
      </div>
    );
  else
    content = relatedLoading ? (
      <>
        <p role="status">{t("正在读取相关书签…", "Loading related pages…")}</p>
        <Skeleton />
      </>
    ) : relatedError ? (
      <div role="alert">
        <h3>{t("暂时无法读取相关书签", "Related pages could not be loaded")}</h3>
        <p className="error">{relatedError}</p>
        <CapsuleButton className="secondary" onClick={onRetry}>
          {t("重试相关书签", "Retry related pages")}
        </CapsuleButton>
      </div>
    ) : related.length ? (
      <div className="related-list">
        {related.map((r) => (
          <CapsuleButton
            className="related-item"
            key={r.bookmark_id}
            onClick={() => onSelect(r.bookmark_id)}
          >
            <small>{r.domain}</small>
            <span>{r.ai_title || r.title || r.url}</span>
            <ArrowUpRight size={14} />
          </CapsuleButton>
        ))}
      </div>
    ) : (
      <div className="reading-empty">
        <BookOpen size={24} />
        <h3>{t("线索会在这里相遇", "Connections start here")}</h3>
        <p>
          {t(
            "暂无相关书签。完成索引后，关联会在这里出现。",
            "No related pages yet. Connections appear here after indexing.",
          )}
        </p>
      </div>
    );
  return (
    <>
      <header className="preview-heading">
        {selected !== null && (
          <CapsuleButton className="reader-back" onClick={onClose}>
            <ArrowLeft size={17} />
            <span>{t("返回收藏", "Back to collection")}</span>
          </CapsuleButton>
        )}
        <div className="reader-actions">
          {position >= 0 && (
            <span className="reader-count">
              {position + 1} / {total}
            </span>
          )}
          {selected !== null && (
            <>
              <CapsuleButton
                className="icon-button"
                title={t("上一条收藏", "Previous bookmark")}
                aria-label={t("上一条收藏", "Previous bookmark")}
                disabled={!onPrevious}
                onClick={onPrevious}
              >
                <ArrowUp />
              </CapsuleButton>
              <CapsuleButton
                className="icon-button"
                title={t("下一条收藏", "Next bookmark")}
                aria-label={t("下一条收藏", "Next bookmark")}
                disabled={!onNext}
                onClick={onNext}
              >
                <ArrowDown />
              </CapsuleButton>
              <span className="toolbar-divider" />
              {canFocus && (
                <CapsuleButton
                  className="icon-button focus-reading"
                  title={
                    focus ? t("收起阅读", "Restore split view") : t("展开阅读", "Expand reading")
                  }
                  aria-label={
                    focus ? t("收起阅读", "Restore split view") : t("展开阅读", "Expand reading")
                  }
                  aria-pressed={focus}
                  onClick={onFocus}
                >
                  {focus ? <Minimize2 /> : <Maximize2 />}
                  <span>{focus ? t("收起", "Restore") : t("专注阅读", "Focus")}</span>
                </CapsuleButton>
              )}
              {canFocus && (
                <CapsuleButton
                  className="icon-button"
                  title={t("关闭预览", "Close preview")}
                  aria-label={t("关闭预览", "Close preview")}
                  onClick={onClose}
                >
                  <PanelRightClose />
                </CapsuleButton>
              )}
            </>
          )}
        </div>
      </header>
      {selected === null ? (
        <div className="reader-welcome">
          <BookOpen size={34} strokeWidth={1.25} />
          <h2>{t("让收藏，重新有用。", "A place to return to your ideas.")}</h2>
          <p>
            {t(
              "找到一条线索，打开一段思考。\n选择收藏，在这里接着读。",
              "Find a clue. Follow a thought.\nChoose a saved page and keep reading here.",
            )}
          </p>
          <div>
            <kbd>↑</kbd>
            <kbd>↓</kbd>
            <span>{t("浏览收藏", "Browse results")}</span>
            <kbd>Esc</kbd>
            <span>{t("返回列表", "Back to results")}</span>
          </div>
        </div>
      ) : (
        <>
          <div
            className="preview-tabs"
            ref={tabs}
            role="tablist"
            aria-label={t("预览内容", "Preview content")}
          >
            {[
              ["body", t("阅读", "Read")],
              ["related", t("相关书签", "Related")],
            ].map(([id, label]) => (
              <CapsuleButton
                role="tab"
                id={`preview-tab-${id}`}
                aria-controls="preview-tabpanel"
                tabIndex={tab === id ? 0 : -1}
                aria-selected={tab === id}
                key={id}
                onClick={() => changeTab(id)}
                onKeyDown={(e) => {
                  if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(e.key)) return;
                  e.preventDefault();
                  const ids = ["body", "related"];
                  const next =
                    e.key === "Home"
                      ? "body"
                      : e.key === "End"
                        ? "related"
                        : ids[(ids.indexOf(id) + (e.key === "ArrowRight" ? 1 : ids.length - 1)) % ids.length];
                  changeTab(next);
                  document.getElementById(`preview-tab-${next}`)?.focus();
                }}
              >
                {id === "body" ? (
                  <FileText size={14} aria-hidden="true" />
                ) : (
                  <BookOpen size={14} aria-hidden="true" />
                )}
                {label}
              </CapsuleButton>
            ))}
            <span className="tab-indicator" aria-hidden="true" />
          </div>
          <div className="preview-scroll" ref={scroller} aria-busy={pending}>
            <div className={`reader-layout ${showOutline ? "with-outline" : ""}`}>
              <article id="reader-start" className="reader-article">
                <div className="preview-title">
                  <div className="article-source">
                    {original ? (
                      <a
                        className="source-link"
                        href={original}
                        target="_blank"
                        rel="noreferrer"
                        title={t("打开原网页", "Open original")}
                        onClick={() => {
                          post("/open", { bookmark_id: selected, query: search }).catch(() => {});
                        }}
                      >
                        {visibleRecord?.domain}
                        <ArrowUpRight size={13} />
                      </a>
                    ) : (
                      <span>{visibleRecord?.domain || t("正在读取来源…", "Loading source…")}</span>
                    )}
                    <span className="source-rule" />
                    <span>
                      {visibleRecord?.date_added
                        ? new Date(visibleRecord.date_added * 1000).toLocaleDateString(
                            language === "zh" ? "zh-CN" : "en",
                            { year: "numeric", month: "short", day: "numeric" },
                          )
                        : ""}
                    </span>
                  </div>
                  <h1>
                    {visibleRecord?.ai_title || visibleRecord?.title ||
                      visibleRecord?.url ||
                      t("正在读取收藏…", "Loading bookmark…")}
                  </h1>
                  <div className="article-options">
                  <details className="article-details">
                    <summary>
                      {t("收藏信息与检索线索", "Saved details & search context")}
                      <ChevronDown size={13} aria-hidden="true" />
                    </summary>
                    {record?.ai_title && record.title && record.ai_title !== record.title && <p className="reader-original-title">
                      <span>{t("原始标题", "Original title")}</span>{record.title}
                    </p>}
                    <div className="article-context">
                      <span>
                        <Folder size={13} />
                        {visibleRecord?.folder || t("未分类", "Unfiled")}
                      </span>
                      {!!record?.tags?.length && (
                        <div className="preview-tags">
                          {record.tags.map((tag) => (
                            <CapsuleButton key={tag} onClick={() => onTag(tag)}>
                              <Tags size={11} />
                              {tag}
                            </CapsuleButton>
                          ))}
                        </div>
                      )}
                    </div>
                    {search.trim() && <SearchExplanation hit={hit} />}
                    {!!record?.intent_queries?.length && <div className="reader-context-queries">
                      <h3>{t("这些问题也能找到它", "Questions that lead here")}</h3>
                      {record.intent_queries.map((query, i) => <CapsuleButton className="suggested-query" key={i}
                        onClick={() => onQuery(query)}>{query}<ArrowUpRight size={14}/></CapsuleButton>)}
                    </div>}
                    {record && onAction && <div className="reader-manage-actions">
                      {canProcess && <>
                        <CapsuleButton className="secondary" disabled={running} onClick={() => onAction({ kind: "process", mode: "fetch", ids: [record.bookmark_id] })}><FileText size={14}/>{t("提取正文", "Fetch text")}</CapsuleButton>
                        <CapsuleButton className="secondary" disabled={running} onClick={() => onAction({ kind: "process", mode: "summarize", ids: [record.bookmark_id] })}><Sparkles size={14}/>{t("生成摘要", "Summarize")}</CapsuleButton>
                      </>}
                      {!managed && <CapsuleButton className="text-button delete-bookmark" disabled={running} onClick={() => onAction({ kind: "delete", ids: [record.bookmark_id] })}><Trash2 size={14}/>{t("删除收藏", "Delete bookmark")}</CapsuleButton>}
                      {managed && <p className="hint">{t("这条收藏由 Karakeep 管理，请在来源端编辑或删除。", "This bookmark is managed by Karakeep. Edit or delete it there.")}</p>}
                    </div>}
                  </details>
                  {record && onAction && !managed && <CapsuleButton className="secondary reader-edit" disabled={running} onClick={() => onAction({ kind: "edit", record })}><Pencil size={14}/>{t("编辑", "Edit")}</CapsuleButton>}
                  </div>
                </div>
                <div
                  className="reading"
                  role="tabpanel"
                  id="preview-tabpanel"
                  aria-labelledby={`preview-tab-${tab}`}
                  tabIndex={0}
                >
                  {content}
                </div>
                {record?.privacy_skipped && (
                  <p className="notice">
                    {t(
                      "此书签已从云端处理和正文抓取中排除。",
                      "This bookmark is excluded from model processing and fetching.",
                    )}
                  </p>
                )}
              </article>
              {showOutline && (
                <ReaderOutline
                  containerRef={scroller}
                  sections={outlineSections}
                  contentKey={`${selected}-${tab}`}
                />
              )}
            </div>
          </div>
          {!pending && !error && tab === "body" && record?.body_text && <ScrollProgress
            containerRef={scroller}
            sections={tab === "body" ? sections : []}
            contentKey={`${selected}-${tab}`}
          />}
        </>
      )}
    </>
  );
}
