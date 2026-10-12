import { useEffect, useRef, useState } from "react";
import { ExternalLink, Eye, Folder, Sparkles } from "lucide-react";
import { post, safeUrl, type Bookmark } from "./api";
import { useText } from "./locale";

export function BookmarkCard({ record, selected, checked, disabled, display, onCheck, onPreview, onSummarize }: {
  record: Bookmark; selected: boolean; checked: boolean; disabled: boolean;
  display: "summary" | "original"; onCheck: () => void;
  onPreview: (button: HTMLButtonElement) => void; onSummarize?: () => void;
}) {
  const t = useText();
  const [expanded, setExpanded] = useState(false);
  const [clipped, setClipped] = useState(false);
  const summary = useRef<HTMLParagraphElement>(null);
  const href = safeUrl(record.url);
  const trackOpen = () => { post("/open", { bookmark_id: record.bookmark_id }).catch(() => {}); };
  const text = display === "summary" ? record.summary || record.snippet : record.snippet;
  useEffect(() => {
    const element = summary.current;
    if (!element || expanded) return;
    const measure = () => setClipped(element.scrollHeight > element.clientHeight + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [text, expanded]);
  const label = display === "summary" && record.summary
    ? record.summary_basis === "title" ? t("标题推断", "Inferred from title") : t("AI 摘要", "AI summary")
    : text ? t("正文摘录", "Page excerpt") : t("暂无摘要", "No summary yet");
  return <article data-bookmark-id={record.bookmark_id}
    className={`result-row ${selected ? "selected" : ""} ${checked ? "batch-selected" : ""}`}>
    <div className="result-copy">
      <div className="result-source">
        <input type="checkbox" className="bookmark-check" checked={checked} disabled={disabled}
          aria-label={t(`选择 ${record.title || record.url}`, `Select ${record.title || record.url}`)} onChange={onCheck}
          onKeyDown={event => {
            if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
            event.preventDefault();
            const controls = [...(event.currentTarget.closest(".result-list")?.querySelectorAll<HTMLInputElement>(".bookmark-check") || [])];
            controls[controls.indexOf(event.currentTarget) + (event.key === "ArrowDown" ? 1 : -1)]?.focus();
          }}/>
        <span className="site-letter" aria-hidden="true">{(record.domain || "F").slice(0, 1).toUpperCase()}</span>
        <span className="source-domain">{record.domain}</span>
        {href && <a className="bookmark-external" href={href} target="_blank" rel="noreferrer" onClick={trackOpen}
          aria-label={t(`打开原网页：${record.title || record.url}`, `Open original: ${record.title || record.url}`)}><ExternalLink size={15}/></a>}
      </div>
      {href ? <a className="result-title" href={href} target="_blank" rel="noreferrer" title={record.title || record.url}
        onClick={trackOpen} onAuxClick={event => { if (event.button === 1) trackOpen(); }}>{record.title || record.url}</a>
        : <span className="result-title">{record.title || record.url}</span>}
      <div className={`bookmark-description ${expanded ? "expanded" : ""}`}>
        <span className="summary-basis">{label}</span>
        <p ref={summary} className="result-summary">{text || t("可批量生成摘要，在列表中直接浏览。", "Generate summaries in bulk and read them here.")}</p>
        {!!text && (clipped || expanded) && <button className="text-button summary-expand" aria-expanded={expanded}
          onClick={() => setExpanded(!expanded)}>{expanded ? t("收起", "Collapse") : t("展开全文", "Show full text")}</button>}
      </div>
      {record.summary_status === "failed" && <p className="summary-failure">{t("上次生成失败", "Last attempt failed")}
        {onSummarize && <button className="text-button" disabled={disabled} onClick={onSummarize}>{t("重试", "Retry")}</button>}</p>}
      <div className="result-meta">
        <span className="result-folder" title={record.folder}><Folder size={12}/><span>{record.folder || t("未分类", "Unfiled")}</span></span>
        <div className="bookmark-actions">
          {onSummarize && <button className="icon-button" disabled={disabled} onClick={onSummarize}
            aria-label={t("生成此条摘要", "Summarize this bookmark")} title={t("生成摘要", "Summarize")}><Sparkles size={15}/></button>}
          <button className="bookmark-preview" disabled={disabled} onClick={event => onPreview(event.currentTarget)}
            onKeyDown={event => {
              if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
              event.preventDefault();
              const controls = [...(event.currentTarget.closest(".result-list")?.querySelectorAll<HTMLButtonElement>(".bookmark-preview") || [])];
              controls[controls.indexOf(event.currentTarget) + (event.key === "ArrowDown" ? 1 : -1)]?.focus();
            }}
            aria-label={t(`预览：${record.title || record.url}`, `Preview: ${record.title || record.url}`)} aria-pressed={selected}><Eye size={15}/>{t("预览", "Preview")}</button>
        </div>
      </div>
    </div>
  </article>;
}
