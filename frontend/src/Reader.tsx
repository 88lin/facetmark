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
  Sparkles,
  Tags,
} from "lucide-react";
import { type Bookmark, post, safeUrl } from "./api";
import { useText, type Language } from "./locale";
import { SearchExplanation } from "./SearchTools";
import { ScrollProgress } from "./components/ui/scroll-progress";
import { useTabIndicator } from "./motion";

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
}) {
  const t = useText();
  const scroller = useRef<HTMLDivElement>(null);
  const scrollPositions = useRef<Record<string, number>>({});
  const tabs = useTabIndicator(`${tab}-${language}`);
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
      { id: "reader-start", label: t("文章开头", "Start of article") },
      ...paragraphs.flatMap((p, i) =>
        /^#{1,3}\s+[^\n]+$/.test(p.trim())
          ? [{ id: `reader-section-${i}`, label: p.replace(/^#{1,3}\s+/, "") }]
          : [],
      ),
    ],
    [paragraphs, language],
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
  const visibleRecord = record || hit;
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
        <button className="secondary" onClick={onRetry}>
          {t("重试", "Retry")}
        </button>
      </div>
    );
  else if (tab === "body")
    content = record?.body_text ? (
      <div className="body-text">
        {paragraphs.map((p, i) =>
          /^#{1,3}\s+[^\n]+$/.test(p.trim()) ? (
            <h2 id={`reader-section-${i}`} key={i}>
              {p.replace(/^#{1,3}\s+/, "")}
            </h2>
          ) : (
            <p key={i}>{p}</p>
          ),
        )}
      </div>
    ) : (
      <div className="reading-empty">
        <FileText size={24} />
        <h3>{t("正文还未保存", "Page text is not saved yet")}</h3>
        <p>
          {t(
            "仍可用标题和网址搜索。可在任务中提取正文，或直接打开原网页。",
            "Search still works on titles and URLs. Fetch text from Tasks, or open the original page.",
          )}
        </p>
      </div>
    );
  else if (tab === "summary")
    content = (
      <>
        <div className="summary-label">
          <Sparkles size={15} />
          {record?.indexed?.summary_basis === "title"
            ? t("基于标题推断", "Inferred from title")
            : t("基于已保存内容", "From saved content")}
        </div>
        <p>
          {record?.indexed?.enriched_by
            ? record.summary
            : t(
                "尚未生成 AI 摘要。配置模型后，在任务中开始索引。",
                "No AI summary yet. Configure models and start indexing from Tasks.",
              )}
        </p>
        {!!record?.key_points?.length && (
          <ul>
            {record.key_points.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        )}
        {!!record?.intent_queries?.length && (
          <>
            <h3>{t("这些问题也能找到它", "Questions that lead here")}</h3>
            {record.intent_queries.map((q) => (
              <button className="suggested-query" key={q} onClick={() => onQuery(q)}>
                {q}
                <ArrowUpRight size={14} />
              </button>
            ))}
          </>
        )}
      </>
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
        <button className="secondary" onClick={onRetry}>
          {t("重试相关书签", "Retry related pages")}
        </button>
      </div>
    ) : related.length ? (
      <div className="related-list">
        {related.map((r) => (
          <button
            className="related-item"
            key={r.bookmark_id}
            onClick={() => onSelect(r.bookmark_id)}
          >
            <small>{r.domain}</small>
            <span>{r.title || r.url}</span>
            <ArrowUpRight size={14} />
          </button>
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
        {!canFocus && selected !== null && (
          <button className="reader-back" onClick={onClose}>
            <ArrowLeft size={17} />
            <span>{t("返回收藏", "Back to collection")}</span>
          </button>
        )}
        <div className="reader-actions">
          {position >= 0 && (
            <span className="reader-count">
              {position + 1} / {total}
            </span>
          )}
          {selected !== null && (
            <>
              <button
                className="icon-button"
                title={t("上一条收藏", "Previous bookmark")}
                aria-label={t("上一条收藏", "Previous bookmark")}
                disabled={!onPrevious}
                onClick={onPrevious}
              >
                <ArrowUp />
              </button>
              <button
                className="icon-button"
                title={t("下一条收藏", "Next bookmark")}
                aria-label={t("下一条收藏", "Next bookmark")}
                disabled={!onNext}
                onClick={onNext}
              >
                <ArrowDown />
              </button>
              <span className="toolbar-divider" />
              {canFocus && (
                <button
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
                </button>
              )}
              {canFocus && (
                <button
                  className="icon-button"
                  title={t("关闭预览", "Close preview")}
                  aria-label={t("关闭预览", "Close preview")}
                  onClick={onClose}
                >
                  <PanelRightClose />
                </button>
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
              ["body", t("正文", "Page text")],
              ["summary", t("AI 摘要", "AI summary")],
              ["related", t("相关书签", "Related")],
            ].map(([id, label]) => (
              <button
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
                  const ids = ["body", "summary", "related"];
                  const next =
                    e.key === "Home"
                      ? "body"
                      : e.key === "End"
                        ? "related"
                        : ids[(ids.indexOf(id) + (e.key === "ArrowRight" ? 1 : 2)) % 3];
                  changeTab(next);
                  document.getElementById(`preview-tab-${next}`)?.focus();
                }}
              >
                {id === "body" ? (
                  <FileText size={14} aria-hidden="true" />
                ) : id === "summary" ? (
                  <Sparkles size={14} aria-hidden="true" />
                ) : (
                  <BookOpen size={14} aria-hidden="true" />
                )}
                {label}
              </button>
            ))}
            <span className="tab-indicator" aria-hidden="true" />
          </div>
          <div className="preview-scroll" ref={scroller} aria-busy={pending}>
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
                  {visibleRecord?.title ||
                    visibleRecord?.url ||
                    t("正在读取收藏…", "Loading bookmark…")}
                </h1>
                <details className="article-details">
                  <summary>
                    {t("收藏信息与检索线索", "Saved details & search context")}
                    <ChevronDown size={13} aria-hidden="true" />
                  </summary>
                  <div className="article-context">
                    <span>
                      <Folder size={13} />
                      {visibleRecord?.folder || t("未分类", "Unfiled")}
                    </span>
                    {!!record?.tags?.length && (
                      <div className="preview-tags">
                        {record.tags.map((tag) => (
                          <button key={tag} onClick={() => onTag(tag)}>
                            <Tags size={11} />
                            {tag}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  {search.trim() && <SearchExplanation hit={hit} />}
                </details>
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
          </div>
          <ScrollProgress
            containerRef={scroller}
            sections={tab === "body" ? sections : []}
            contentKey={`${selected}-${tab}`}
            showProgress={Boolean(!pending && !error && tab === "body" && record?.body_text)}
          />
        </>
      )}
    </>
  );
}
