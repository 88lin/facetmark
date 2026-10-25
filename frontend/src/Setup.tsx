import { CapsuleButton } from "./ui/controls";
import { useRef, useState } from "react";
import { AlertCircle, ArrowRight, Check, FolderOpen, LoaderCircle, RotateCcw, Upload } from "lucide-react";
import { ApiError, api, post, type Job, type Setup } from "./api";
import { Models } from "./Settings";
import { Tasks } from "./Tasks";
import { useText } from "./locale";
import { SelectionPill, useContentMotion } from "./InteractionMotion";
import { SiteImport } from "./SiteImport";
import "./setup.css";

type ImportReport = {
  parsed?: number; total_parsed?: number; inserted?: number; updated?: number;
  merged_duplicates?: number; privacy_skipped?: number; non_indexable?: number;
  missing_dates?: number; folders?: number; max_depth?: number; skipped?: number; errors?: number; warnings?: string[];
  restored_bodies?: number; restored_summaries?: number; restored_conversations?: number; restored_messages?: number;
};
const importCount = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.trunc(value)) : 0;

export function Importer({ refresh, onDone }: { refresh: () => Promise<void>; onDone?: () => void }) {
  const t = useText();
  const input = useRef<HTMLInputElement>(null);
  const inFlight = useRef(false);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [error, setError] = useState("");
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const lastWork = useRef<(() => Promise<unknown>) | null>(null);
  const [finding, setFinding] = useState(false);
  const findingInFlight = useRef(false);
  const [dragging, setDragging] = useState(false);
  const [sources, setSources] = useState<{ id: string; browser: string; profile: string }[] | null>(
    null,
  );
  async function run(work: () => Promise<unknown>) {
    if (inFlight.current || findingInFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    setReport(null); setNeedsRefresh(false); lastWork.current = work;
    let received = false;
    try {
      const result = (await work()) as ImportReport;
      received = true; setReport(result);
      await refresh();
    } catch (e) {
      setNeedsRefresh(received);
      setError(received ? t("导入结果已保存，但收藏列表未能刷新。请重新读取列表。", "Import results were saved, but the collection could not refresh. Reload the collection.")
        : e instanceof ApiError ? e.message : t("导入服务暂时不可用，请重试。", "The import service is temporarily unavailable. Please retry."));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  async function upload(file?: File) {
    if (!file || inFlight.current || findingInFlight.current) return;
    setReport(null); setNeedsRefresh(false); lastWork.current = null;
    if (!/\.(html?|json)$/i.test(file.name)) {
      setError(t("请选择 HTML 或 JSON 书签导出文件。", "Choose an HTML or JSON bookmark export."));
      return;
    }
    if (file.size > 64 * 1024 * 1024) {
      setError(t("请选择不超过 64 MB 的导出文件。", "Choose an export up to 64 MB."));
      return;
    }
    await run(() =>
      api("/admin/import", {
        method: "POST",
        body: file,
        headers: { "x-filename": encodeURIComponent(file.name) },
      }),
    );
  }
  async function retry() {
    if (!needsRefresh) { if (lastWork.current) await run(lastWork.current); return; }
    if (inFlight.current || findingInFlight.current) return;
    inFlight.current = true; setBusy(true); setError("");
    try { await refresh(); setNeedsRefresh(false); }
    catch { setError(t("收藏列表仍未能刷新，请重新读取。", "The collection still could not refresh. Please reload it.")); }
    finally { inFlight.current = false; setBusy(false); }
  }
  const parsed = importCount(report?.parsed ?? report?.total_parsed);
  const changed = importCount(report?.inserted) + importCount(report?.updated);
  const restored = ["restored_bodies", "restored_summaries", "restored_conversations", "restored_messages"] as const;
  const hasRestored = restored.some(key => importCount(report?.[key]) > 0);
  const warnings = (report?.warnings || []).filter(value => typeof value === "string" && value.trim()).map(value => value.trim().slice(0, 1200));
  const partial = importCount(report?.skipped) > 0 || importCount(report?.errors) > 0
    || parsed > changed + importCount(report?.merged_duplicates);
  const outcome = !changed && !hasRestored ? "empty" : partial ? "partial" : warnings.length || importCount(report?.missing_dates)
    || importCount(report?.privacy_skipped) || importCount(report?.non_indexable) ? "review" : "complete";
  const outcomeTitle = outcome === "empty" ? t("没有新增或更新的收藏", "No bookmarks were added or updated")
    : outcome === "partial" ? t("导入结束，部分内容未能导入", "Import finished with some content not imported")
      : outcome === "review" ? t("导入完成，有事项需要留意", "Import complete with details to review")
        : hasRestored && !changed ? t("备份内容已恢复", "Backup content restored") : t("导入完成", "Import complete");
  const metrics = [
    ["parsed", t("解析条目", "Parsed entries"), parsed], ["inserted", t("新增收藏", "Added bookmarks"), importCount(report?.inserted)],
    ["updated", t("更新收藏", "Updated bookmarks"), importCount(report?.updated)],
    ["merged_duplicates", t("合并重复", "Merged duplicates"), importCount(report?.merged_duplicates)],
    ["privacy_skipped", t("隐私排除", "Privacy exclusions"), importCount(report?.privacy_skipped)],
    ["non_indexable", t("不参与索引", "Not indexable"), importCount(report?.non_indexable)],
    ["missing_dates", t("缺少保存时间", "Missing save dates"), importCount(report?.missing_dates)],
    ...(report?.folders !== undefined ? [["folders", t("文件夹", "Folders"), importCount(report.folders)] as const] : []),
    ...(report?.max_depth !== undefined ? [["max_depth", t("最大层级", "Maximum folder depth"), importCount(report.max_depth)] as const] : []),
    ...(report?.skipped !== undefined ? [["skipped", t("跳过条目", "Skipped entries"), importCount(report.skipped)] as const] : []),
    ...(report?.errors !== undefined ? [["errors", t("处理失败", "Failed entries"), importCount(report.errors)] as const] : []),
  ] as const;
  return (
    <section className="importer">
      <h2>{t("把收藏带回来", "Bring your bookmarks together")}</h2>
      <p>
        {t(
          "从浏览器导出的 HTML 或 JSON 开始。只读取副本，原书签保持原样。",
          "Start with an HTML or JSON browser export. Facetmark reads a copy and preserves your original bookmarks.",
        )}
      </p>
      <div
        className={`dropzone ${dragging ? "is-dragging" : ""}`}
        aria-busy={busy || finding}
        onDragOver={(e) => { e.preventDefault(); if (!busy && !finding) setDragging(true); }}
        onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragging(false); }}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(e.dataTransfer.files[0]);
        }}
      >
        <span className="dropzone-symbol" aria-hidden="true"><Upload size={28} /></span>
        <h3>{t("将书签文件拖到这里", "Drop your bookmark file here")}</h3>
        <p>HTML / JSON · {t("最大 64 MB", "Up to 64 MB")}</p>
        <input
          ref={input}
          type="file"
          accept=".html,.htm,.json"
          hidden
          onChange={(e) => { const file = e.target.files?.[0]; e.target.value = ""; upload(file); }}
        />
        <CapsuleButton type="button" className="primary" disabled={busy || finding} onClick={() => input.current?.click()}>
          {busy ? <LoaderCircle className="spin"/> : <FolderOpen />}
          {busy ? t("正在导入…", "Importing…") : t("选择文件", "Choose a file")}
        </CapsuleButton>
      </div>
      <details className="import-help">
        <summary>{t("如何导出浏览器书签？", "How do I export my bookmarks?")}</summary>
        <p>{t("在 Chrome 或 Edge 中打开书签管理器，选择菜单中的「导出书签」，再将保存的 HTML 文件拖到这里。也可导入 Facetmark 导出的 JSON。", "Open the bookmark manager in Chrome or Edge, choose Export bookmarks from its menu, then drop the saved HTML file here. Facetmark JSON exports are also supported.")}</p>
      </details>
      <CapsuleButton
        type="button"
        className="text-button"
        disabled={busy || finding}
        onClick={async () => {
          if (inFlight.current || findingInFlight.current) return;
          findingInFlight.current = true;
          setError(""); setReport(null); setNeedsRefresh(false); lastWork.current = null; setSources(null); setDragging(false);
          setFinding(true);
          try {
            const data = await api<{ sources: { id: string; browser: string; profile: string }[] }>(
              "/admin/import/sources",
            );
            setSources(data.sources);
          } catch (e) {
            setError(t("未能读取书签来源，请重新查找或选择导出文件。", "Bookmark sources could not be read. Search again or choose an export file."));
          } finally {
            findingInFlight.current = false;
            setFinding(false);
          }
        }}
      >
        {finding ? t("正在查找书签来源…", "Finding bookmark sources…") : t("查找本机 Chromium 浏览器的书签来源", "Find local Chromium bookmark sources")}
      </CapsuleButton>
      {sources && (
        <div className="source-list">
          {sources.length === 0 ? (
            <p>
              {t(
                "没有发现可读取来源，请使用导出文件。",
                "No readable sources found. Use a browser export.",
              )}
            </p>
          ) : (
            sources.map((source) => (
              <CapsuleButton
                type="button"
                disabled={busy || finding}
                className="source"
                key={source.id}
                onClick={() => run(() => post("/admin/import/source", { source_id: source.id }))}
              >
                <FolderOpen />
                <span>
                  {source.browser}
                  <small>{source.profile}</small>
                </span>
                <span>{t("导入此来源", "Import this source")}</span>
              </CapsuleButton>
            ))
          )}
        </div>
      )}
      {report && (
        <div className="import-result" data-outcome={outcome}>
          <p className="import-result-heading" role="status">{outcome === "complete" ? <Check size={18}/> : <AlertCircle size={18}/>}<strong>{outcomeTitle}</strong></p>
          <dl className="import-metrics">{metrics.map(([key, label, count]) => <div key={key} data-metric={key}><dt>{label}</dt><dd>{count}</dd></div>)}</dl>
          {hasRestored && <div className="import-restored"><h3>{t("从备份恢复的内容", "Content restored from backup")}</h3>
            <dl className="import-metrics">{restored.map((key, index) => <div key={key} data-metric={key}>
              <dt>{[t("保存正文", "Saved page text"), t("AI 摘要", "AI summaries"), t("对话", "Conversations"), t("对话消息", "Chat messages")][index]}</dt><dd>{importCount(report[key])}</dd>
            </div>)}</dl><p>{t("恢复缺失内容，保留书库中已有的正文与摘要。", "Missing content was restored. Existing page text and summaries were kept.")}</p>
          </div>}
          {warnings.length > 0 && <details className="import-warnings" open><summary>{t("导入提醒", "Import notes")} · {warnings.length}</summary>
            <ul>{warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></details>}
          {outcome === "empty" ? <p>{t("没有可新增的有效内容。请检查导出范围，或选择另一个文件。", "There was no new content to add. Check the export scope or choose another file.")}</p>
            : <p>{t("已保存的收藏可以继续搜索和整理；隐私排除与不支持检索的条目不会发送给 AI。", "Saved bookmarks can be searched and organized. Privacy-excluded and non-indexable entries are not sent to AI.")}</p>}
          {onDone && outcome !== "empty" && <CapsuleButton type="button" className="primary" disabled={busy || needsRefresh} onClick={onDone}>{t("查看已导入的收藏", "View imported bookmarks")}<ArrowRight size={16}/></CapsuleButton>}
        </div>
      )}
      {error && <div className="import-error" role="alert"><p className="error">{error}</p>
        {lastWork.current && <CapsuleButton type="button" className="secondary" disabled={busy || finding} onClick={() => void retry()}><RotateCcw size={15}/>{needsRefresh ? t("重新读取收藏", "Reload collection") : t("重试导入", "Retry import")}</CapsuleButton>}
      </div>}
      <SiteImport refresh={refresh} onDone={onDone}/>
    </section>
  );
}

export default function SetupFlow({
  setup,
  job,
  refresh,
  onDone,
  onProcess,
}: {
  setup: Setup | null;
  job: Job;
  refresh: () => Promise<void>;
  onDone: () => void;
  onProcess: (mode: "fetch" | "summarize") => void;
}) {
  const t = useText();
  const [step, setStep] = useState(0);
  const [visited, setVisited] = useState(() => new Set([0]));
  const root = useRef<HTMLDivElement>(null);
  useContentMotion(root, String(step), ".setup-panel:not([hidden])", "x");
  const completed = [Boolean(setup?.bookmarks),
    Boolean(setup?.channels.chat.configured && setup.channels.chat.tested && !setup.pending_apply),
    Boolean(setup?.has_vectors && setup.vector_compatible && !setup.pending_apply), false];
  function goTo(next: number) { setVisited(previous => new Set([...previous, next])); setStep(next); }
  const labels = [
    t("导入书签", "Import"),
    t("连接模型", "Models"),
    t("建立索引", "Index"),
    t("开始检索", "Search"),
  ];
  return (
    <div className="setup-flow" ref={root}>
      <header className="page-heading">
        <div>
          <h1>{t("让收藏，再次有用", "Make your saved pages useful again")}</h1>
          <p>
            {t("导入即可查找和整理，AI 连接与索引可以稍后准备。", "Import to start searching and organizing. AI connections and indexing can wait.")}
          </p>
        </div>
        <CapsuleButton type="button" className="text-button" onClick={onDone}>
          {t("先用关键词检索", "Use keyword search for now")}
        </CapsuleButton>
      </header>
      <nav className="setup-steps" aria-label={t("设置步骤", "Setup steps")}>
        {labels.map((label, index) => (
          <CapsuleButton
            type="button"
            key={label}
            aria-current={step === index ? "step" : undefined}
            disabled={index > step + 1 && !visited.has(index)}
            onClick={() => goTo(index)}
          >
            <SelectionPill active={step === index} group="setup-step" />
            <span className="setup-step-number">{completed[index] ? <Check size={14} /> : index + 1}</span>
            <span className="setup-step-label">{label}</span>
          </CapsuleButton>
        ))}
      </nav>
      {visited.has(0) && <div className="setup-panel" hidden={step !== 0}><Importer refresh={refresh} onDone={onDone} /></div>}
      {visited.has(1) && <div className="setup-panel" hidden={step !== 1}>
        <Models setup={setup} refresh={refresh} onSummarize={() => onProcess("summarize")} />
      </div>}
      {visited.has(2) && <div className="setup-panel" hidden={step !== 2}>
        <Tasks setup={setup} job={job} refresh={refresh} onProcess={onProcess} onBack={onDone} />
      </div>}
      {visited.has(3) && <div className="setup-panel" hidden={step !== 3}>
        <section className="ready">
          <Check size={32} />
          <h2>{t("从你记得的一点开始", "Start with the detail you remember")}</h2>
          <p>
            {t(
              "一个词、一段描述，或保存时所在的文件夹。检索结果与正文会并排呈现。",
              "A word, a description, or the folder you saved it in. Results and page text stay side by side.",
            )}
          </p>
          <CapsuleButton type="button" className="primary" onClick={onDone}>
            {t("进入工作台", "Open workbench")}
            <ArrowRight />
          </CapsuleButton>
        </section>
      </div>}
      {step < 3 && (
        <footer className="setup-footer">
          <span>
            {setup?.bookmarks ?? 0} {t("条书签已在库中", "bookmarks in your library")}
          </span>
          <CapsuleButton
            type="button"
            className="secondary"
            disabled={step === 0 && !setup?.bookmarks}
            onClick={() => goTo(step + 1)}
          >
            {step === 1
              ? t("继续查看索引确认", "Continue to index confirmation")
              : t("下一步", "Continue")}
            <ArrowRight />
          </CapsuleButton>
        </footer>
      )}
    </div>
  );
}
