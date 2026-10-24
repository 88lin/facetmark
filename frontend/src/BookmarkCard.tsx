import { CapsuleButton as Button } from "./ui/controls";
import { useEffect, useId, useRef, useState } from "react";
import { AlertCircle, ArrowUpRight, Check, CheckCircle2, ChevronDown, Clock3, Eye, Pencil, Sparkles } from "lucide-react";
import { post, safeUrl, type Bookmark } from "./api";
import { useText } from "./locale";
import { motion } from "motion/react";
import { useReducedMotion } from "./useReducedMotion";
import { CollectionFolderIcon } from "./CollectionFolderIcon";
import "./bookmark-card.css";

export function BookmarkCard({ record, selected, checked, disabled, display, entranceOrder = 0, onCheck, onPreview, onSummarize, onEdit }: {
  record: Bookmark; selected: boolean; checked: boolean; disabled: boolean;
  entranceOrder?: number;
  display: "summary" | "original"; onCheck: () => void;
  onPreview: (button: HTMLButtonElement) => void; onSummarize?: () => void; onEdit?: () => void;
}) {
  const t = useText();
  const reduced = useReducedMotion();
  const id = useId();
  const [expanded, setExpanded] = useState(false);
  const [clipped, setClipped] = useState(false);
  const summary = useRef<HTMLParagraphElement>(null);
  const href = safeUrl(record.url);
  const title = record.title || record.url;
  const trackOpen = (event?: { button: number }) => {
    // Native auxiliary activation is counted separately from the primary click.
    if (event && event.button !== 0) return;
    post("/open", { bookmark_id: record.bookmark_id }).catch(() => {});
  };
  const text = display === "summary" ? record.summary || record.snippet : record.snippet;
  const label = display === "summary" && record.summary
    ? record.summary_basis === "title" ? t("标题推断", "Inferred from title") : t("AI 摘要", "AI summary")
    : text ? t("正文摘录", "Page excerpt") : display === "original" ? t("暂无正文", "No page text yet") : t("暂无摘要", "No summary yet");
  useEffect(() => { setExpanded(false); setClipped(false); }, [record.bookmark_id, display, text]);
  useEffect(() => {
    const element = summary.current;
    if (!element || expanded) return;
    const measure = () => setClipped(element.scrollHeight > element.clientHeight + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [text, expanded, display, record.bookmark_id, label]);
  const status = record.summary_status || (record.summary ? "done" : "pending");
  const StatusIcon = status === "failed" ? AlertCircle : status === "done" ? CheckCircle2 : Clock3;
  const statusLabel = record.privacy_skipped ? t("已跳过摘要", "Summary skipped")
    : status === "failed" ? t("上次生成失败", "Last attempt failed")
      : status === "done" ? t("摘要已生成", "Summary ready") : t("待生成摘要", "Awaiting summary");

  const sourceLetter = (record.domain || "F").replace(/^www\./, "").slice(0, 1).toUpperCase();
  const sourceTone = [...(record.domain || "")].reduce((sum, letter) => sum + letter.charCodeAt(0), 0) % 4;
  const savedDate = record.date_added ? new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" })
    .format(new Date(record.date_added * 1000)) : "";

  return <motion.article data-bookmark-id={record.bookmark_id} data-source-tone={sourceTone} aria-labelledby={`${id}-title`}
    layout={reduced ? false : "position"}
    initial={reduced ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
    transition={{ opacity: { duration: reduced ? 0 : 0.26, delay: reduced ? 0 : Math.min(entranceOrder, 5) * 0.025 },
      y: { duration: reduced ? 0 : 0.38, ease: [0.22, 1, 0.36, 1] }, layout: { type: "spring", stiffness: 340, damping: 32 } }}
    onPointerMove={event => {
      if (reduced || event.pointerType !== "mouse") return;
      const bounds = event.currentTarget.getBoundingClientRect();
      event.currentTarget.style.setProperty("--glint-x", `${event.clientX - bounds.left}px`);
      event.currentTarget.style.setProperty("--glint-y", `${event.clientY - bounds.top}px`);
    }}
    onPointerLeave={event => {
      event.currentTarget.style.removeProperty("--glint-x");
      event.currentTarget.style.removeProperty("--glint-y");
    }}
    className={`result-row ${selected ? "selected" : ""} ${checked ? "batch-selected" : ""}`}>
    <header className="result-source">
      <span className="source-symbol" aria-hidden="true">{sourceLetter}</span>
      <span className="source-domain" title={record.domain || record.url}>{record.domain || t("已存网页", "Saved page")}</span>
      {savedDate && <time className="bookmark-date" dateTime={new Date(record.date_added! * 1000).toISOString()}>{savedDate}</time>}
      {href && <a className="bookmark-external" href={href} target="_blank" rel="noreferrer" onClick={trackOpen}
        onAuxClick={event => { if (event.button === 1) trackOpen(); }}
        title={t("打开原网页", "Open original")}
        aria-label={t(`打开原网页：${title}`, `Open original: ${title}`)}><ArrowUpRight size={17}/></a>}
      <label className="bookmark-select" title={t("选择收藏", "Select bookmark")}>
        <input type="checkbox" className="bookmark-check" checked={checked} disabled={disabled}
          aria-label={t(`选择 ${title}`, `Select ${title}`)} onChange={onCheck}
          onKeyDown={event => {
            if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
            event.preventDefault();
            const controls = [...(event.currentTarget.closest(".result-list")?.querySelectorAll<HTMLInputElement>(".bookmark-check:not(:disabled)") || [])];
            controls[controls.indexOf(event.currentTarget) + (event.key === "ArrowDown" ? 1 : -1)]?.focus();
          }}/>
        <span className="bookmark-check-frame" aria-hidden="true">
          {reduced ? <span className="bookmark-check-fill" style={{ transform: checked ? "scale(1)" : "scale(0)" }}/> :
            <motion.span className="bookmark-check-fill" initial={false} animate={{ scale: checked ? 1 : 0 }}
              transition={{ duration: 0.16, ease: [0.2, 0.7, 0.3, 1] }}/>}
          <Check size={15} className={checked ? "is-checked" : ""}/>
        </span>
      </label>
    </header>

    <h3 id={`${id}-title`} className="bookmark-heading">
      {href ? <a className="result-title" href={href} target="_blank" rel="noreferrer" title={title}
        onClick={trackOpen} onAuxClick={event => { if (event.button === 1) trackOpen(); }}>{title}</a>
        : <span className="result-title">{title}</span>}
    </h3>

    <div className={`bookmark-description ${expanded ? "expanded" : ""}`}>
      <div className="bookmark-description-heading">
        {!!text && (clipped || expanded) && <Button type="button" className="summary-expand" aria-expanded={expanded}
          aria-controls={`${id}-summary`} aria-label={expanded ? t("收起", "Collapse") : t("展开全文", "Show full text")}
          title={expanded ? t("收起", "Collapse") : t("展开全文", "Show full text")}
          onClick={() => setExpanded(value => !value)}>
          <span>{expanded ? t("收起", "Less") : t("展开", "More")}</span><ChevronDown size={14}/>
        </Button>}
      </div>
      <p id={`${id}-summary`} ref={summary} className={`result-summary ${text ? "" : "is-empty"}`}>
        <span className="summary-basis">{label}</span>{" "}
        {text || (display === "original" ? t("预览中可抓取正文，或直接打开原网页。", "Fetch page text in Preview, or open the original website.") : t("可生成摘要，在收藏中直接浏览。", "Generate a summary to read it here."))}
      </p>
    </div>

    <div className="bookmark-metadata">
      <div className={`bookmark-status ${status === "failed" ? "summary-failure" : ""}`} data-summary-status={status}>
        <StatusIcon size={14} aria-hidden="true"/><span>{statusLabel}</span>
        {status === "failed" && onSummarize && <Button type="button" className="bookmark-retry" disabled={disabled}
          onClick={onSummarize}>{t("重试", "Retry")}</Button>}
      </div>
      {!!record.tags?.length && <ul className="bookmark-tags" aria-label={t("标签", "Tags")}>
        {record.tags.map((tag, index) => <li key={`${tag}-${index}`}>{tag}</li>)}
      </ul>}
    </div>

    <footer className="result-meta">
      <span className="result-folder" title={record.folder || t("未分类", "Unfiled")}>
        <CollectionFolderIcon size={15}/><span>{record.folder || t("未分类", "Unfiled")}</span>
      </span>
      <div className="bookmark-actions">
        {onEdit && <Button type="button" className="bookmark-action" disabled={disabled} onClick={onEdit}
          aria-label={t(`编辑：${title}`, `Edit: ${title}`)} title={t("编辑收藏", "Edit bookmark")}><Pencil size={16}/></Button>}
        {onSummarize && <Button type="button" className="bookmark-action" disabled={disabled} onClick={onSummarize}
          aria-label={t("生成此条摘要", "Summarize this bookmark")} title={t("生成摘要", "Summarize")}><Sparkles size={16}/></Button>}
        <Button type="button" className="bookmark-preview" disabled={disabled} onClick={event => onPreview(event.currentTarget)}
          onKeyDown={event => {
            if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
            event.preventDefault();
            const controls = [...(event.currentTarget.closest(".result-list")?.querySelectorAll<HTMLButtonElement>(".bookmark-preview:not(:disabled)") || [])];
            controls[controls.indexOf(event.currentTarget) + (event.key === "ArrowDown" ? 1 : -1)]?.focus();
          }}
          aria-label={t(`预览：${title}`, `Preview: ${title}`)} aria-pressed={selected}>
          <Eye size={16}/><span>{t("预览", "Preview")}</span>
        </Button>
      </div>
    </footer>
  </motion.article>;
}
