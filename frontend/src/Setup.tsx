import { useRef, useState } from "react";
import { ArrowRight, Check, FolderOpen, Upload } from "lucide-react";
import { api, post, type Job, type Setup } from "./api";
import { Models } from "./Settings";
import { Tasks } from "./Tasks";
import { useText } from "./locale";

export function Importer({ refresh }: { refresh: () => Promise<void> }) {
  const t = useText();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [sources, setSources] = useState<{ id: string; browser: string; profile: string }[] | null>(
    null,
  );
  async function run(work: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = (await work()) as { inserted?: number; updated?: number };
      await refresh();
      setMessage(
        `${t("导入完成", "Import complete")} · ${t("新增", "Added")} ${result.inserted ?? 0} · ${t("更新", "Updated")} ${result.updated ?? 0}`,
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function upload(file?: File) {
    if (!file || busy) return;
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
        className="dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          upload(e.dataTransfer.files[0]);
        }}
      >
        <Upload size={28} />
        <h3>{t("将书签文件拖到这里", "Drop your bookmark file here")}</h3>
        <p>HTML / JSON · {t("最大 64 MB", "Up to 64 MB")}</p>
        <input
          ref={input}
          type="file"
          accept=".html,.htm,.json"
          hidden
          onChange={(e) => upload(e.target.files?.[0])}
        />
        <button className="primary" disabled={busy} onClick={() => input.current?.click()}>
          <FolderOpen />
          {busy ? t("正在导入…", "Importing…") : t("选择文件", "Choose a file")}
        </button>
      </div>
      <button
        className="text-button"
        disabled={busy}
        onClick={async () => {
          setError("");
          try {
            const data = await api<{ sources: { id: string; browser: string; profile: string }[] }>(
              "/admin/import/sources",
            );
            setSources(data.sources);
          } catch (e) {
            setError(String(e));
          }
        }}
      >
        {t("查找本机 Chromium 浏览器的书签来源", "Find local Chromium bookmark sources")}
      </button>
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
              <button
                disabled={busy}
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
              </button>
            ))
          )}
        </div>
      )}
      {message && (
        <p className="notice" role="status">
          <Check size={16} />
          {message}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
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
  const labels = [
    t("导入书签", "Import"),
    t("连接模型", "Models"),
    t("建立索引", "Index"),
    t("开始检索", "Search"),
  ];
  return (
    <div className="setup-flow">
      <header className="page-heading">
        <div>
          <h1>{t("让收藏，再次有用", "Make your saved pages useful again")}</h1>
          <p>
            {t("几步准备，建立属于你的检索空间。", "A few steps to your own searchable library.")}
          </p>
        </div>
        <button className="text-button" onClick={onDone}>
          {t("先用关键词检索", "Use keyword search for now")}
        </button>
      </header>
      <nav className="setup-steps" aria-label={t("设置步骤", "Setup steps")}>
        {labels.map((label, index) => (
          <button
            key={label}
            aria-current={step === index ? "step" : undefined}
            disabled={index > step + 1 || (index > 0 && !setup?.bookmarks)}
            onClick={() => setStep(index)}
          >
            <span>{index < step ? <Check size={14} /> : index + 1}</span>
            {label}
          </button>
        ))}
      </nav>
      {step === 0 ? (
        <Importer refresh={refresh} />
      ) : step === 1 ? (
        <Models setup={setup} refresh={refresh} />
      ) : step === 2 ? (
        <Tasks setup={setup} job={job} refresh={refresh} onProcess={onProcess} />
      ) : (
        <section className="ready">
          <Check size={32} />
          <h2>{t("从你记得的一点开始", "Start with the detail you remember")}</h2>
          <p>
            {t(
              "一个词、一段描述，或保存时所在的文件夹。检索结果与正文会并排呈现。",
              "A word, a description, or the folder you saved it in. Results and page text stay side by side.",
            )}
          </p>
          <button className="primary" onClick={onDone}>
            {t("进入工作台", "Open workbench")}
            <ArrowRight />
          </button>
        </section>
      )}
      {step < 3 && (
        <footer className="setup-footer">
          <span>
            {setup?.bookmarks ?? 0} {t("条书签已在库中", "bookmarks in your library")}
          </span>
          <button
            className="secondary"
            disabled={step === 0 && !setup?.bookmarks}
            onClick={() => setStep(step + 1)}
          >
            {step === 1
              ? t("继续查看索引确认", "Continue to index confirmation")
              : t("下一步", "Continue")}
            <ArrowRight />
          </button>
        </footer>
      )}
    </div>
  );
}
