import { useEffect, useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import { post, type Bookmark } from "./api";
import { useText } from "./locale";

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
  const fragment = text.match(/(?:^|\s)(-?\w+:(?:"[^"]*"|[^\s]*)|[^\s]+)$/)?.[1] || "";
  useEffect(() => {
    if (!open) return;
    const abort = new AbortController();
    setItems([]);
    post<{ suggestions: Suggestion[] }>(
      "/suggest/query",
      { text: fragment, limit: 6 },
      abort.signal,
    )
      .then((data) => setItems(data.suggestions))
      .catch(() => {});
    return () => abort.abort();
  }, [open, fragment]);
  return (
    <details className="query-help" onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>{t("查询语法与建议", "Query syntax and suggestions")}</summary>
      <p>
        {t(
          "用 domain:、folder:、tag: 缩小范围，用 - 排除，用引号保留词组。",
          "Use domain:, folder:, tag: to filter, - to exclude, and quotes for phrases.",
        )}
      </p>
      <div>
        {items.map((item) => (
          <button
            className="secondary"
            key={item.insert}
            onClick={() => {
              const colon = item.insert.indexOf(":");
              const value = item.insert.slice(colon + 1);
              const insert =
                colon >= 0 && /\s/.test(value) && !value.startsWith('"')
                  ? item.insert.slice(0, colon + 1) + JSON.stringify(value)
                  : item.insert;
              onSelect(text.slice(0, text.length - fragment.length) + insert);
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
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
