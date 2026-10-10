import { useEffect, useId, useRef, useState } from "react";
import { Command } from "cmdk";
import {
  CornerDownLeft,
  Folder,
  Globe2,
  LoaderCircle,
  SlidersHorizontal,
  Sparkles,
  Tags,
} from "lucide-react";
import { post, type Bookmark } from "./api";
import { useText } from "./locale";
import "./search-tools.css";

type Suggestion = { label: string; insert: string; detail: string };
type Answer = {
  claims: { text: string; sources: number[] }[];
  sources: { n: number; bookmark_id: number; title: string; basis: string }[];
  gaps: string[];
  degraded: boolean;
  model: string;
};

export function QuerySuggestions({
  text,
  onSelect,
}: {
  text: string;
  onSelect: (value: string) => void;
}) {
  const t = useText();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Suggestion[]>([]);
  const [busy, setBusy] = useState(true);
  const [failed, setFailed] = useState(false);
  const [revision, setRevision] = useState(0);
  const details = useRef<HTMLDetailsElement>(null);
  const trigger = useRef<HTMLElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const descriptionId = useId();
  const fragment = text.match(/(?:^|\s)(-?\w+:(?:"[^"]*"|[^\s]*)|[^\s]+)$/)?.[1] || "";
  useEffect(() => {
    if (!open) return;
    const abort = new AbortController();
    setItems([]);
    setBusy(true);
    setFailed(false);
    post<{ suggestions: Suggestion[] }>(
      "/suggest/query",
      { text: fragment, limit: 6 },
      abort.signal,
    )
      .then((data) => {
        if (!abort.signal.aborted) setItems(data.suggestions.slice(0, 6));
      })
      .catch(() => {
        if (!abort.signal.aborted) setFailed(true);
      })
      .finally(() => {
        if (!abort.signal.aborted) setBusy(false);
      });
    return () => abort.abort();
  }, [open, fragment, revision]);
  useEffect(() => {
    if (!open) return;
    list.current?.focus({ preventScroll: true });
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !details.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);
  const applySuggestion = (item: Suggestion) => {
    const colon = item.insert.indexOf(":");
    const value = item.insert.slice(colon + 1);
    const insert =
      colon >= 0 && /\s/.test(value) && !value.startsWith('"')
        ? item.insert.slice(0, colon + 1) + JSON.stringify(value)
        : item.insert;
    setOpen(false);
    onSelect(text.slice(0, text.length - fragment.length) + insert);
  };
  return (
    <details
      className="query-help query-suggestions"
      ref={details}
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      onBlur={(event) => {
        if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget))
          setOpen(false);
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          event.preventDefault();
          event.stopPropagation();
          setOpen(false);
          trigger.current?.focus();
        } else if (
          (event.key === "ArrowDown" || event.key === "ArrowUp") &&
          event.target === trigger.current
        ) {
          event.preventDefault();
          setOpen(true);
          list.current?.focus({ preventScroll: true });
        }
      }}
    >
      <summary ref={trigger} title={t("查询语法与建议", "Query syntax and suggestions")}>
        <SlidersHorizontal size={14} />
        <span>{t("检索语法", "Search syntax")}</span>
      </summary>
      {open && (
        <div className="query-suggestions-panel">
          <header className="query-suggestions-heading">
            <strong>{t("检索建议", "Search suggestions")}</strong>
            {!busy && !failed && items.length > 0 && (
              <span>{t(`${items.length} 条建议`, `${items.length} suggestions`)}</span>
            )}
          </header>
          <p className="query-suggestions-intro" id={descriptionId}>
            {t(
              "用 domain:、folder:、tag: 缩小范围，用 - 排除，用引号保留词组。",
              "Filter with domain:, folder: or tag:. Use - to exclude and quotes for phrases.",
            )}
          </p>
          <Command shouldFilter={false} loop label={t("检索建议", "Search suggestions")}>
            <Command.List
              ref={list}
              label={t("可插入的检索条件", "Suggested search filters")}
              aria-describedby={descriptionId}
              aria-busy={busy}
            >
              {items.map((item, index) => {
                const field = item.insert.replace(/^-/, "").split(":")[0];
                const Icon =
                  field === "folder"
                    ? Folder
                    : field === "tag"
                      ? Tags
                      : ["domain", "site", "host"].includes(field)
                        ? Globe2
                        : SlidersHorizontal;
                const detailId = `${descriptionId}-${index}`;
                return (
                  <Command.Item
                    key={item.insert}
                    value={item.insert}
                    aria-label={item.label}
                    aria-describedby={item.detail ? detailId : undefined}
                    onSelect={() => applySuggestion(item)}
                  >
                    <span className="query-suggestion-icon" aria-hidden="true">
                      <Icon size={16} />
                    </span>
                    <span className="query-suggestion-copy">
                      <span className="query-suggestion-label">{item.label}</span>
                      {item.detail && (
                        <span className="query-suggestion-detail" id={detailId}>
                          {item.detail}
                        </span>
                      )}
                    </span>
                    <CornerDownLeft
                      className="query-suggestion-enter"
                      size={14}
                      aria-hidden="true"
                    />
                  </Command.Item>
                );
              })}
            </Command.List>
            {busy && (
              <div className="query-suggestions-state" role="status">
                <LoaderCircle size={16} className="spin" aria-hidden="true" />
                <span>{t("正在查找建议…", "Finding suggestions…")}</span>
              </div>
            )}
            {failed && (
              <div className="query-suggestions-state query-suggestions-error" role="alert">
                <span>{t("暂时无法获取建议。", "Suggestions could not be loaded.")}</span>
                <button
                  className="secondary"
                  onClick={() => {
                    list.current?.focus({ preventScroll: true });
                    setRevision((value) => value + 1);
                  }}
                >
                  {t("重试", "Retry")}
                </button>
              </div>
            )}
            {!busy && !failed && !items.length && (
              <div className="query-suggestions-state" role="status">
                {t(
                  "没有匹配的建议，可以继续输入搜索。",
                  "No matching suggestions. Keep typing to search.",
                )}
              </div>
            )}
          </Command>
          <footer className="query-suggestions-footer" aria-hidden="true">
            <span>
              <kbd>↑</kbd>
              <kbd>↓</kbd> {t("选择", "Navigate")}
            </span>
            <span>
              <kbd>Enter</kbd> {t("插入", "Insert")}
            </span>
            <span>
              <kbd>Esc</kbd> {t("关闭", "Close")}
            </span>
          </footer>
        </div>
      )}
    </details>
  );
}

export function SearchAnswer({
  terms,
  available,
  onSelect,
}: {
  terms: string;
  available: boolean;
  onSelect: (id: number) => void;
}) {
  const t = useText();
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [request, setRequest] = useState<AbortController | null>(null);
  useEffect(() => () => request?.abort(), [request]);
  return (
    <details className="search-answer">
      <summary>
        <Sparkles size={14} />
        {t("综合回答", "Answer from this library")}
      </summary>
      <p>
        {t(
          "确认生成后，会把问题与最多 8 条命中的标题、网址和摘要发给已配置的模型。回答附带来源，可回到原文核对。",
          "Generating sends your question and up to 8 matching titles, URLs and excerpts to your configured models. Follow citations to check the source.",
        )}
      </p>
      <button
        className="secondary"
        disabled={!available || busy}
        onClick={async () => {
          const abort = new AbortController();
          setRequest(abort);
          setBusy(true);
          setError("");
          try {
            setAnswer(await post<Answer>("/synthesize", { q: terms, limit: 8 }, abort.signal));
          } catch (e) {
            if (!abort.signal.aborted) setError(String(e));
          } finally {
            if (!abort.signal.aborted) setBusy(false);
          }
        }}
      >
        {busy ? <LoaderCircle className="spin" /> : <Sparkles />}
        {t("确认并生成回答", "Confirm and generate answer")}
      </button>
      {!available && (
        <p className="hint">
          {t("请先在设置中配置模型并完成索引。", "Configure models and index your library first.")}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {answer && (
        <div aria-live="polite">
          {answer.degraded && (
            <p className="notice">
              {t(
                "模型未返回可用回答，以下仅摘录来源。",
                "The model did not return a usable answer. These are source excerpts.",
              )}
            </p>
          )}
          {answer.claims.map((claim, i) => (
            <p key={i}>
              {claim.text}{" "}
              {claim.sources.map((n) => (
                <button
                  className="citation"
                  key={n}
                  aria-label={t(`查看来源 ${n}`, `Read source ${n}`)}
                  onClick={() => {
                    const source = answer.sources.find((s) => s.n === n);
                    if (source) onSelect(source.bookmark_id);
                  }}
                >
                  [{n}]
                </button>
              ))}
            </p>
          ))}
          {answer.sources.map((source) => (
            <button
              className="related-item"
              key={source.n}
              onClick={() => onSelect(source.bookmark_id)}
            >
              [{source.n}] {source.title}
              {source.basis === "title" && <small>{t("仅基于标题", "Based on title only")}</small>}
            </button>
          ))}
          {!!answer.gaps.length && (
            <details>
              <summary>{t("证据局限", "Evidence limits")}</summary>
              <ul>
                {answer.gaps.map((gap) => (
                  <li key={gap}>{gap}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </details>
  );
}

export function SearchExplanation({
  hit,
}: {
  hit?: Bookmark & { context_reasons?: string[]; contributions?: Record<string, number> };
}) {
  const t = useText();
  if (!hit?.facets?.length) return null;
  return (
    <details className="query-help">
      <summary>{t("为什么命中这条书签", "Why this bookmark matched")}</summary>
      <p>
        {t("参与召回的线索", "Retrieval signals")}: {hit.facets.join(" · ")}
      </p>
      {hit.context_reasons?.map((reason) => (
        <p key={reason}>{reason}</p>
      ))}
      {hit.contributions && (
        <dl>
          {Object.entries(hit.contributions).map(([name, value]) => (
            <div key={name}>
              <dt>{name}</dt>
              <dd>{value.toFixed(4)}</dd>
            </div>
          ))}
        </dl>
      )}
    </details>
  );
}
