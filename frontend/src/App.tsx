import { useCallback, useEffect, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Bookmark as BookmarkIcon,
  Check,
  ChevronRight,
  Clock3,
  ExternalLink,
  FileText,
  Folder,
  Globe2,
  Import,
  Layers3,
  LoaderCircle,
  Menu,
  Moon,
  PanelRightClose,
  Search,
  Settings2,
  Sparkles,
  Sun,
  Tags,
  WifiOff,
  X,
} from "lucide-react";
import {
  api,
  ApiError,
  post,
  query,
  safeUrl,
  setToken,
  type Bookmark,
  type Job,
  type Page,
  type Setup,
} from "./api";
import { Locale, useText, type Language } from "./locale";
import SetupFlow, { Importer } from "./Setup";
import { ExtensionSettings, Models, UpdateSettings } from "./Settings";
import { Tasks } from "./Tasks";
import { QuerySuggestions, SearchAnswer } from "./SearchTools";
import Reader, { Skeleton } from "./Reader";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { motionTiming } from "./motion";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

type View = "library" | "sessions" | "tasks" | "settings" | "setup" | "import";
type Facet = { value: string; count: number };
type Filters = { folder?: string; tag?: string; domain?: string; session?: number };
type Session = { session_id: number; label: string; started_at: number; size: number };
const remember = (key: string, value?: string) => {
  try {
    if (value !== undefined) localStorage.setItem(key, value);
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};

export default function App() {
  const [language, setLanguage] = useState<Language>(() =>
    remember("fm-language") === "en" ? "en" : "zh",
  );
  const [theme, setTheme] = useState(() => remember("fm-theme") || "light");
  useEffect(() => {
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
    remember("fm-language", language);
  }, [language]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    remember("fm-theme", theme);
  }, [theme]);
  return (
    <Locale.Provider value={language}>
      <Workbench language={language} theme={theme} setLanguage={setLanguage} setTheme={setTheme} />
    </Locale.Provider>
  );
}

function SavedDate({ seconds, language }: { seconds?: number | null; language: Language }) {
  if (seconds == null) return null;
  const date = new Date(seconds * 1000);
  if (!Number.isFinite(date.getTime())) return null;
  return (
    <time dateTime={date.toISOString()}>
      {date.toLocaleDateString(language === "zh" ? "zh-CN" : "en", {
        month: "short",
        day: "numeric",
      })}
    </time>
  );
}

function Workbench({
  language,
  theme,
  setLanguage,
  setTheme,
}: {
  language: Language;
  theme: string;
  setLanguage: (l: Language) => void;
  setTheme: (t: string) => void;
}) {
  const t = useText();
  const reduceMotion = useReducedMotion();
  const [paired, setPaired] = useState(false);
  const [pairingRequired, setPairingRequired] = useState(false);
  const [manualToken, setManualToken] = useState("");
  const [view, setView] = useState<View>("library");
  const [navOpen, setNavOpen] = useState(false);
  const [setup, setSetup] = useState<Setup | null>(null);
  const [job, setJob] = useState<Job>({ state: "idle" });
  const [adminAvailable, setAdminAvailable] = useState(true);
  const [facets, setFacets] = useState<Record<string, Facet[]>>({});
  const [filters, setFilters] = useState<Filters>({});
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [depth, setDepth] = useState<number>();
  const [page, setPage] = useState<Page | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [preview, setPreview] = useState<Bookmark | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [related, setRelated] = useState<Bookmark[]>([]);
  const [drawer, setDrawer] = useState(() => matchMedia("(max-width: 1119px)").matches);
  const [previewTab, setPreviewTab] = useState("body");
  const [focusReading, setFocusReading] = useState(false);
  const workspace = useRef<HTMLElement>(null);
  const readerPane = useRef<HTMLElement>(null);
  const readerCache = useRef(new Map<number, Bookmark>());
  const focusTimeline = useRef<gsap.core.Timeline | null>(null);
  const focusFrame = useRef<number | null>(null);
  const { contextSafe } = useGSAP({ scope: workspace });
  const toggleFocus = contextSafe(() => {
    const pane = readerPane.current;
    if (!pane) return;
    const before = pane.getBoundingClientRect().left;
    if (focusFrame.current !== null) cancelAnimationFrame(focusFrame.current);
    const next = !focusReading;
    setFocusReading(next);
    // React commits layout before the next frame; do not queue a delayed entrance.
    focusFrame.current = requestAnimationFrame(
      contextSafe(() => {
        if (!readerPane.current) return;
        focusTimeline.current?.kill();
        gsap.set(readerPane.current, { x: 0 });
        const after = readerPane.current.getBoundingClientRect().left;
        if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
          gsap.set(readerPane.current, { clearProps: "transform" });
          return;
        }
        focusTimeline.current = gsap
          .timeline({ defaults: motionTiming })
          .fromTo(readerPane.current, { x: before - after }, { x: 0, clearProps: "transform" });
      }),
    );
  });
  useEffect(
    () => () => {
      if (focusFrame.current !== null) cancelAnimationFrame(focusFrame.current);
    },
    [],
  );
  const [relatedLoading, setRelatedLoading] = useState(false);
  const [relatedError, setRelatedError] = useState("");
  const [previewRevision, setPreviewRevision] = useState(0);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState("");
  const [sessionsRevision, setSessionsRevision] = useState(0);
  const sidebar = useRef<HTMLElement>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsMore, setSessionsMore] = useState(false);
  const searchInput = useRef<HTMLInputElement>(null);
  const composing = useRef(false);
  const firstRefresh = useRef(true);
  const list = useRef<HTMLDivElement>(null);
  const browseScroll = useRef(0);
  const lastRow = useRef<HTMLButtonElement | null>(null);
  const [requestRevision, setRequestRevision] = useState(0);
  const requestId = useRef(0);
  const previewId = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const openView = (next: View) => {
    setView(next);
    setNavOpen(false);
  };
  const closePreview = useCallback(() => {
    setSelected(null);
    setFocusReading(false);
    requestAnimationFrame(() => {
      if (list.current) list.current.scrollTop = browseScroll.current;
      if (lastRow.current?.isConnected) lastRow.current.focus({ preventScroll: true });
      else searchInput.current?.focus();
    });
  }, []);
  const refresh = useCallback(async () => {
    try {
      const data = await api<Record<string, Facet[]>>("/bookmarks/facets");
      setFacets(data);
      setConnectionError("");
      try {
        const [status, task] = await Promise.all([
          api<Setup>("/admin/setup-status"),
          api<Job>("/admin/job"),
        ]);
        setSetup(status);
        setJob(task);
        setAdminAvailable(true);
        if (firstRefresh.current) {
          firstRefresh.current = false;
          if (!status.bookmarks && !remember("fm-setup-skipped")) setView("setup");
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 403) setAdminAvailable(false);
        else throw e;
      }
    } catch (e) {
      setConnectionError(String(e));
    }
  }, []);
  const boot = useCallback(async () => {
    try {
      const data = await api<{ paired: boolean; token: string }>("/app/boot");
      if (data.paired) {
        setToken(data.token);
        setPaired(true);
        setPairingRequired(false);
      } else setPairingRequired(true);
      setConnectionError("");
    } catch (e) {
      setConnectionError(String(e));
    }
  }, []);
  useEffect(() => {
    boot();
  }, [boot]);
  useEffect(() => {
    const route = () => {
      if (location.hash === "#settings") setView("settings");
    };
    route();
    window.addEventListener("hashchange", route);
    return () => window.removeEventListener("hashchange", route);
  }, []);
  useEffect(() => {
    if (!paired) return;
    refresh();
    const timer = setInterval(refresh, 4000);
    return () => clearInterval(timer);
  }, [paired, refresh]);
  useEffect(() => {
    const media = matchMedia("(max-width: 1119px)");
    const update = () => {
      setDrawer(media.matches);
      if (media.matches) setFocusReading(false);
    };
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.isComposing) return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setFocusReading(false);
        setView("library");
        setNavOpen(false);
        requestAnimationFrame(() => searchInput.current?.focus());
      }
      if (event.key === "Escape" && selected !== null && !drawer && !event.defaultPrevented) {
        event.preventDefault();
        if (focusReading) setFocusReading(false);
        else closePreview();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selected, drawer, closePreview, focusReading]);
  useEffect(() => {
    if (!navOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    const focusables = () =>
      Array.from(
        sidebar.current?.querySelectorAll<HTMLElement>(
          'a[href],button:not(:disabled),summary,input:not(:disabled),[tabindex="0"]',
        ) || [],
      ).filter((el) => el.offsetParent !== null);
    focusables()[0]?.focus();
    const trap = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setNavOpen(false);
      } else if (e.key === "Tab") {
        const elements = focusables();
        const index = elements.indexOf(document.activeElement as HTMLElement);
        if (!elements.length) {
          e.preventDefault();
          return;
        }
        if (e.shiftKey && index <= 0) {
          e.preventDefault();
          elements.at(-1)?.focus();
        } else if (!e.shiftKey && (index < 0 || index === elements.length - 1)) {
          e.preventDefault();
          elements[0]?.focus();
        }
      }
    };
    document.addEventListener("keydown", trap, true);
    return () => {
      document.removeEventListener("keydown", trap, true);
      previous?.focus();
    };
  }, [navOpen]);
  function changeQuery(value: string) {
    browseScroll.current = 0;
    setFocusReading(false);
    setInput(value);
    abortRef.current?.abort();
    requestId.current++;
    if (!composing.current) {
      setSearch(value);
      setOffset(0);
      setDepth(undefined);
    }
  }
  const filterKey = JSON.stringify(filters);
  const hasSearchContext = Boolean(
    search.trim() ||
      Object.values(filters).some((value) => value !== undefined) ||
      (setup?.bookmarks || 0) > 0,
  );
  const searchTerms = [
    search,
    ...Object.entries(filters)
      .filter(([, value]) => value !== undefined)
      .map(([key, value]) => `${key}:${JSON.stringify(value)}`),
  ].join(" ");
  const semantic = Boolean(
    setup &&
      !setup.demo &&
      setup.channels.embed.configured &&
      setup.has_vectors &&
      setup.vector_compatible &&
      !setup.pending_apply,
  );
  useEffect(() => {
    if (!paired || view !== "library") return;
    const id = ++requestId.current;
    const abort = new AbortController();
    abortRef.current = abort;
    const update = (data: Page) => {
      if (id === requestId.current && !abort.signal.aborted) {
        setPage(data);
        if (data.depth) setDepth(data.depth);
        setLoading(false);
      }
    };
    setLoading(true);
    setError("");
    const timer = setTimeout(
      async () => {
        try {
          if (!search.trim()) {
            update(
              await api<Page>(`/bookmarks?${query({ ...filters, offset, limit: 30 })}`, {
                signal: abort.signal,
              }),
            );
            return;
          }
          const terms = searchTerms;
          const fast = await api<Page>(`/quick?${query({ q: terms, offset, limit: 30, depth })}`, {
            signal: abort.signal,
          });
          update(fast);
          if (semantic) {
            const full = await post<Page>(
              "/search",
              { q: terms, offset, limit: 30, depth: depth ?? fast.depth },
              abort.signal,
            );
            update(full);
          }
        } catch (e) {
          if (id === requestId.current && !abort.signal.aborted) {
            setError(String(e));
            setLoading(false);
          }
        }
      },
      search ? 240 : 0,
    );
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
    // Depth is the returned ranking snapshot; updating it must not restart page one.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paired, view, search, offset, filterKey, semantic, requestRevision]);
  useEffect(() => {
    if (selected === null) {
      setPreview(null);
      return;
    }
    const id = ++previewId.current;
    const abort = new AbortController();
    setPreview(readerCache.current.get(selected) || null);
    setRelated([]);
    setPreviewError("");
    setRelatedError("");
    setRelatedLoading(true);
    api<Bookmark>(`/bookmark/${selected}?body=true`, { signal: abort.signal })
      .then((record) => {
        if (id === previewId.current && !abort.signal.aborted) {
          readerCache.current.set(record.bookmark_id, record);
          if (readerCache.current.size > 24)
            readerCache.current.delete(readerCache.current.keys().next().value!);
          setPreview(record);
        }
      })
      .catch((e) => {
        if (!abort.signal.aborted) setPreviewError(String(e));
      });
    api<Bookmark[]>(`/bookmark/${selected}/related`, { signal: abort.signal })
      .then((records) => {
        if (id === previewId.current) setRelated(records);
      })
      .catch((e) => {
        if (!abort.signal.aborted) setRelatedError(String(e));
      })
      .finally(() => {
        if (!abort.signal.aborted) setRelatedLoading(false);
      });
    return () => abort.abort();
  }, [selected, previewRevision]);
  useEffect(() => {
    if (view !== "sessions" || !paired) return;
    const abort = new AbortController();
    setSessionsError("");
    setSessionsLoading(true);
    api<Session[]>("/sessions?limit=40", { signal: abort.signal })
      .then((data) => {
        setSessions(data);
        setSessionsMore(data.length === 40);
      })
      .catch((e) => {
        if (!abort.signal.aborted) setSessionsError(String(e));
      })
      .finally(() => {
        if (!abort.signal.aborted) setSessionsLoading(false);
      });
    return () => abort.abort();
  }, [view, paired, sessionsRevision]);
  const items = page?.items || page?.hits || [];
  function selectFilter(key: keyof Filters, value: string | number | undefined) {
    browseScroll.current = 0;
    setFocusReading(false);
    abortRef.current?.abort();
    requestId.current++;
    setFilters((old) => ({ ...old, [key]: value }));
    setOffset(0);
    setDepth(undefined);
    setView("library");
    setNavOpen(false);
  }
  function paginate(next: number) {
    browseScroll.current = 0;
    setOffset(next);
    list.current?.scrollTo({ top: 0 });
  }
  const select = (id: number, button?: HTMLButtonElement) => {
    if (selected === null) browseScroll.current = list.current?.scrollTop ?? 0;
    if (button) lastRow.current = button;
    setPreview(readerCache.current.get(id) || null);
    setPreviewError("");
    setPreviewTab("body");
    setSelected(id);
    if (!drawer && selected === null)
      requestAnimationFrame(() => lastRow.current?.scrollIntoView({ block: "nearest" }));
  };
  const selectedPosition = items.findIndex((item) => item.bookmark_id === selected);
  const moveSelection = (step: number) => {
    const next = items[selectedPosition + step];
    const button =
      list.current?.querySelectorAll<HTMLButtonElement>(".result-row")[selectedPosition + step];
    if (next) {
      select(next.bookmark_id, button);
      button?.scrollIntoView({ block: "nearest" });
    }
  };
  const previewContent = (
    <Reader
      record={preview}
      selected={selected}
      pending={selected !== null && !preview && !previewError}
      error={previewError}
      related={related}
      relatedLoading={relatedLoading}
      relatedError={relatedError}
      tab={previewTab}
      setTab={setPreviewTab}
      hit={items.find((item) => item.bookmark_id === selected)}
      search={search}
      language={language}
      onClose={closePreview}
      onRetry={() => setPreviewRevision((v) => v + 1)}
      onSelect={(id) => select(id)}
      onQuery={(q) => {
        changeQuery(q);
        if (drawer) closePreview();
      }}
      onTag={(tag) => {
        selectFilter("tag", tag);
        if (drawer) closePreview();
      }}
      focus={focusReading}
      onFocus={toggleFocus}
      canFocus={!drawer}
      position={selectedPosition}
      total={items.length}
      onPrevious={selectedPosition > 0 ? () => moveSelection(-1) : undefined}
      onNext={
        selectedPosition >= 0 && selectedPosition < items.length - 1
          ? () => moveSelection(1)
          : undefined
      }
    />
  );
  return (
    <div className={`app-shell ${focusReading ? "is-reading-focused" : ""}`}>
      <header className="app-header" inert={navOpen}>
        <button
          className="icon-button nav-trigger"
          aria-label={t("打开导航", "Open navigation")}
          onClick={() => setNavOpen(true)}
        >
          <Menu />
        </button>
        <a
          className="brand app-brand"
          href="/app"
          onClick={(event) => {
            event.preventDefault();
            openView("library");
          }}
        >
          <span className="brand-mark">
            <Layers3 size={25} />
          </span>
          <span>Facetmark</span>
        </a>
        <nav className="header-navigation" aria-label={t("主要导航", "Main navigation")}>
          <button
            className={view === "library" ? "active" : ""}
            onClick={() => {
              openView("library");
              setFilters({});
              changeQuery("");
            }}
          >
            {t("全部书签", "All bookmarks")}
          </button>
          <button
            className={view === "sessions" ? "active" : ""}
            onClick={() => openView("sessions")}
          >
            {t("浏览批次", "Saving sessions")}
          </button>
        </nav>
        <div className="header-utilities">
          {setup?.demo && <span className="demo-label">{t("合成演示数据", "Synthetic demo")}</span>}
          {adminAvailable && (
            <>
              <button
                className="icon-button"
                aria-label={t("任务", "Tasks")}
                title={t("任务", "Tasks")}
                onClick={() => openView("tasks")}
              >
                {job.state === "running" ? <LoaderCircle className="spin" /> : <Layers3 />}
              </button>
              <button
                className="icon-button"
                aria-label={t("设置", "Settings")}
                title={t("设置", "Settings")}
                onClick={() => openView("settings")}
              >
                <Settings2 />
              </button>
            </>
          )}
          <button
            className="icon-button"
            aria-label={t("切换主题", "Toggle theme")}
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? <Moon /> : <Sun />}
          </button>
          <button
            className="language"
            aria-label="Switch language"
            onClick={() => setLanguage(language === "zh" ? "en" : "zh")}
          >
            {language === "zh" ? "EN" : "中文"}
          </button>
          {adminAvailable && (
            <button className="header-import" onClick={() => openView("import")}>
              <Import size={16} />
              {t("导入书签", "Import bookmarks")}
            </button>
          )}
        </div>
      </header>
      <aside
        ref={sidebar}
        inert={!navOpen}
        role={navOpen ? "dialog" : undefined}
        aria-modal={navOpen ? true : undefined}
        aria-label={t("导航", "Navigation")}
        className={`sidebar ${navOpen ? "is-open" : ""}`}
      >
        <a
          className="brand"
          href="/app"
          onClick={(e) => {
            e.preventDefault();
            openView("library");
          }}
        >
          <span className="brand-mark">
            <Layers3 size={24} />
          </span>
          <span>Facetmark</span>
        </a>
        <div className="nav-section-label">{t("书库与筛选", "Library & filters")}</div>
        <nav className="main-nav" aria-label={t("工作区", "Workspace")}>
          <button
            className={
              view === "library" && !Object.values(filters).some((v) => v !== undefined)
                ? "active"
                : ""
            }
            onClick={() => {
              openView("library");
              setFilters({});
              changeQuery("");
            }}
          >
            <BookmarkIcon />
            {t("全部书签", "All bookmarks")}
            <span className="count">{setup?.bookmarks ?? "—"}</span>
          </button>
          <button
            className={view === "sessions" ? "active" : ""}
            onClick={() => openView("sessions")}
          >
            <Clock3 />
            {t("浏览批次", "Saving sessions")}
          </button>
        </nav>
        <div className="facet-nav">
          {[
            ["folders", "folder", t("文件夹", "Folders"), Folder],
            ["tags", "tag", t("标签", "Tags"), Tags],
            ["domains", "domain", t("站点", "Sites"), Globe2],
          ].map(([group, field, label, Icon]) => {
            const Glyph = Icon as typeof Folder;
            return (
              <details open={group === "folders"} key={String(group)}>
                <summary>
                  <Glyph size={15} />
                  {String(label)}
                  <ChevronRight size={14} />
                </summary>
                {facets[String(group)]?.length ? (
                  facets[String(group)].map((facet) => (
                    <button
                      key={facet.value}
                      title={facet.value}
                      className={filters[field as keyof Filters] === facet.value ? "active" : ""}
                      onClick={() => selectFilter(field as keyof Filters, facet.value)}
                    >
                      <span>
                        {field === "folder" && <Folder size={13} />}
                        {facet.value}
                      </span>
                      <small>{facet.count}</small>
                    </button>
                  ))
                ) : (
                  <p className="hint">{t("导入后显示", "Available after import")}</p>
                )}
              </details>
            );
          })}
        </div>
        <div className="sidebar-bottom">
          {adminAvailable && (
            <>
              <button
                className={view === "import" ? "active" : ""}
                onClick={() => openView("import")}
              >
                <Import />
                {t("导入书签", "Import bookmarks")}
              </button>
              <button
                className={view === "tasks" ? "active" : ""}
                onClick={() => openView("tasks")}
              >
                {job.state === "running" ? <LoaderCircle className="spin" /> : <Layers3 />}
                {t("任务", "Tasks")}
                {job.state === "running" && <span className="activity-dot" />}
              </button>
              <button
                className={view === "settings" ? "active" : ""}
                onClick={() => openView("settings")}
              >
                <Settings2 />
                {t("设置", "Settings")}
              </button>
            </>
          )}
          <div className="appearance">
            <button
              className="icon-button"
              aria-label={t("切换主题", "Toggle theme")}
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            >
              {theme === "light" ? <Moon /> : <Sun />}
            </button>
            <button
              className="language"
              aria-label="Switch language"
              onClick={() => setLanguage(language === "zh" ? "en" : "zh")}
            >
              {language === "zh" ? "EN" : "中文"}
            </button>
            <span className="local-status">
              {connectionError ? (
                <WifiOff size={13} />
              ) : paired ? (
                <Check size={13} />
              ) : (
                <LoaderCircle size={13} className="spin" />
              )}
              {connectionError
                ? t("连接中断", "Disconnected")
                : paired
                  ? t("书库已连接", "Connected")
                  : t("连接中", "Connecting")}
            </span>
          </div>
        </div>
      </aside>
      {navOpen && (
        <button
          className="nav-scrim"
          aria-label={t("关闭导航", "Close navigation")}
          onClick={() => setNavOpen(false)}
        />
      )}
      <main
        ref={workspace}
        inert={navOpen}
        className={`main-workspace ${view === "library" ? "with-preview" : ""} ${selected !== null ? "has-selection" : "browse-mode"} ${focusReading && view === "library" ? "focus-mode" : ""}`}
      >
        {connectionError && (
          <div className="connection-error" role="alert">
            <WifiOff size={16} />
            <span>
              {t(
                "服务连接中断。请确认 Facetmark 正在运行。",
                "Connection lost. Check that Facetmark is running.",
              )}{" "}
              <small>{connectionError}</small>
            </span>
            <button
              className="secondary"
              onClick={() => {
                if (paired) {
                  refresh();
                  setRequestRevision((v) => v + 1);
                } else boot();
              }}
            >
              {t("重新连接", "Reconnect")}
            </button>
          </div>
        )}
        {pairingRequired && !paired ? (
          <section className="pairing-screen">
            <h1>{t("连接你的书库", "Connect your library")}</h1>
            <p>
              {t(
                "请输入服务生成的配对令牌。远程访问不会自动提供令牌。",
                "Enter the pairing token generated by your service. Remote access does not disclose it automatically.",
              )}
            </p>
            <label className="field">
              {t("配对令牌", "Pairing token")}
              <input
                type="password"
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value)}
              />
            </label>
            <button
              className="primary"
              onClick={async () => {
                setToken(manualToken);
                try {
                  await api("/stats");
                  setPaired(true);
                  setManualToken("");
                } catch (e) {
                  setConnectionError(String(e));
                }
              }}
            >
              {t("连接", "Connect")}
            </button>
          </section>
        ) : !paired ? (
          <div className="empty">
            <LoaderCircle className="spin" />
            <p>{t("正在打开书库…", "Opening your library…")}</p>
          </div>
        ) : view === "library" ? (
          <>
            <header className="workspace-toolbar">
              <div className="toolbar-location">
                <h1>
                  {search ? t("搜索收藏", "Find a saved page") : t("我的收藏", "Your collection")}
                </h1>
                <span>
                  {setup?.bookmarks ?? "—"} {t("条收藏", "saved pages")}
                </span>
              </div>
              <div className="search-box">
                <Search size={20} />
                <input
                  ref={searchInput}
                  aria-label={t("搜索书签", "Search bookmarks")}
                  placeholder={t("你想找回什么？", "What would you like to find again?")}
                  value={input}
                  onChange={(e) => changeQuery(e.target.value)}
                  onCompositionStart={() => {
                    composing.current = true;
                    abortRef.current?.abort();
                    requestId.current++;
                  }}
                  onCompositionEnd={(e) => {
                    composing.current = false;
                    changeQuery(e.currentTarget.value);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.nativeEvent.isComposing && !composing.current)
                      changeQuery(input);
                  }}
                />
                {input ? (
                  <button
                    className="icon-button"
                    aria-label={t("清空搜索", "Clear search")}
                    onClick={() => changeQuery("")}
                  >
                    <X size={16} />
                  </button>
                ) : (
                  <kbd>Ctrl K</kbd>
                )}
              </div>

              <div className="query-tool">
                {" "}
                <QuerySuggestions
                  text={search}
                  onSelect={(value) => {
                    changeQuery(value);
                    searchInput.current?.focus();
                  }}
                />
              </div>
              <button
                className="filter-trigger"
                onClick={() => setNavOpen(true)}
                aria-label={t("筛选收藏", "Filter collection")}
              >
                <Settings2 size={17} />
                <span>{t("筛选", "Filters")}</span>
              </button>
            </header>
            <section className="results-column" inert={focusReading}>
              <header className="search-header">
                <div className="workspace-heading">
                  <h1>
                    {search ? t("搜索结果", "Search results") : t("全部书签", "All bookmarks")}
                  </h1>
                  <span className="result-count" aria-live="polite">
                    {loading ? <LoaderCircle size={13} className="spin" /> : (page?.total ?? "—")}
                    {page?.depth_capped ? "+" : ""}
                  </span>
                </div>
                <div className="search-controls">
                  <div className="search-meta">
                    <span>
                      {search
                        ? semantic
                          ? t("关键词 + 语义检索", "Keyword + semantic search")
                          : t("关键词检索", "Keyword search")
                        : t("按收藏时间排列", "Recently saved first")}
                    </span>
                    <span className="list-key-hint">
                      <kbd>↑</kbd>
                      <kbd>↓</kbd>
                      {t("选择", "Navigate")}
                    </span>
                  </div>
                </div>
                {Object.entries(filters).some(([, v]) => v !== undefined) && (
                  <div className="filter-chips">
                    {Object.entries(filters)
                      .filter(([, value]) => value !== undefined)
                      .map(([key, value]) => (
                        <button
                          key={key}
                          onClick={() => selectFilter(key as keyof Filters, undefined)}
                        >
                          {key === "session" ? t("批次", "Session") : ""} {value}
                          <X size={12} />
                        </button>
                      ))}
                  </div>
                )}
              </header>
              {error && (
                <div className="error search-error" role="alert">
                  <strong>
                    {t(
                      "搜索暂时不可用，请稍后重试。",
                      "Search is temporarily unavailable. Please retry.",
                    )}
                  </strong>
                  <p className="error-detail">{error}</p>
                  <button className="text-button" onClick={() => setRequestRevision((v) => v + 1)}>
                    {t("重试", "Retry")}
                  </button>
                </div>
              )}
              <div
                className="result-list"
                ref={list}
                aria-label={t("书签列表", "Bookmark results")}
                aria-busy={loading}
              >
                {search.trim() && (
                  <SearchAnswer
                    key={searchTerms}
                    terms={searchTerms}
                    available={Boolean(
                      setup?.demo || (semantic && setup?.channels.chat.configured),
                    )}
                    onSelect={(id) => select(id)}
                  />
                )}
                {error && !items.length ? null : (loading || !page) && !items.length ? (
                  <>
                    <span role="status" className="sr-only">
                      {t("正在检索…", "Searching…")}
                    </span>
                    <Skeleton rows />
                  </>
                ) : !items.length ? (
                  <div className="empty">
                    <BookmarkIcon size={36} />
                    <h2>
                      {hasSearchContext
                        ? t("换一点线索试试", "Try another clue")
                        : t("收藏，从这里汇合", "Your collection starts here")}
                    </h2>
                    <p>
                      {hasSearchContext
                        ? t(
                            "试试标题中的词、网址，或减少筛选条件。",
                            "Try words from the title, a URL, or fewer filters.",
                          )
                        : t(
                            "导入浏览器书签，就能开始关键词检索。",
                            "Import your browser bookmarks to start searching by keyword.",
                          )}
                    </p>
                    {hasSearchContext && (
                      <button
                        className="secondary"
                        onClick={() => {
                          setFilters({});
                          changeQuery("");
                          setOffset(0);
                        }}
                      >
                        {t("清除条件，查看全部", "Clear filters and show all")}
                      </button>
                    )}
                    {!hasSearchContext && adminAvailable && (
                      <button className="primary" onClick={() => openView("import")}>
                        <Import />
                        {t("导入书签", "Import bookmarks")}
                      </button>
                    )}
                  </div>
                ) : (
                  items.map((record, index) => (
                    <button
                      data-bookmark-id={record.bookmark_id}
                      className={`result-row ${selected === record.bookmark_id ? "selected" : ""}`}
                      key={record.bookmark_id}
                      onClick={(e) => select(record.bookmark_id, e.currentTarget)}
                      onKeyDown={(e) => {
                        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                          e.preventDefault();
                          const next = items[index + (e.key === "ArrowDown" ? 1 : -1)];
                          const button =
                            list.current?.querySelectorAll<HTMLButtonElement>(".result-row")[
                              index + (e.key === "ArrowDown" ? 1 : -1)
                            ];
                          if (next && button) {
                            select(next.bookmark_id, button);
                            button.focus();
                          }
                        }
                      }}
                      aria-pressed={selected === record.bookmark_id}
                    >
                      <span className="result-copy">
                        <span className="result-meta">
                          <span>
                            <span className="site-letter" aria-hidden="true">
                              {(record.domain || record.title || "F").slice(0, 1).toUpperCase()}
                            </span>
                            {record.domain}
                          </span>
                          <SavedDate seconds={record.date_added} language={language} />
                        </span>
                        <span className="result-title">{record.title || record.url}</span>
                        {(record.snippet || record.summary) &&
                          (record.snippet || record.summary) !== record.title && (
                            <span className="result-summary">
                              {record.snippet || record.summary}
                            </span>
                          )}
                        {record.folder && (
                          <span className="result-folder">
                            <Folder size={11} />
                            {record.folder}
                            {selected === record.bookmark_id && (
                              <span className="reading-label">{t("正在阅读", "Reading")}</span>
                            )}
                          </span>
                        )}
                      </span>
                      <ChevronRight className="row-chevron" size={15} />
                    </button>
                  ))
                )}
              </div>
              <footer className="results-footer">
                <span>
                  {page && page.total > 0
                    ? `${page.offset + 1}–${page.offset + items.length}`
                    : t("你的收藏，只在你的书库", "Your collection, in your library")}
                </span>
                <div>
                  <button
                    className="icon-button"
                    disabled={!page?.offset || loading}
                    aria-label={t("上一页", "Previous page")}
                    onClick={() => paginate(Math.max(0, (page?.offset || 0) - (page?.limit || 30)))}
                  >
                    <ArrowLeft />
                  </button>
                  <button
                    className="icon-button"
                    disabled={!page?.has_more || loading || page.depth_capped}
                    aria-label={t("下一页", "Next page")}
                    onClick={() => paginate((page?.offset || 0) + (page?.limit || 30))}
                  >
                    <ArrowRight />
                  </button>
                </div>
              </footer>
            </section>
            {!drawer && selected !== null && (
              <aside ref={readerPane} className="preview-pane">
                {previewContent}
              </aside>
            )}
            {drawer && (
              <Dialog.Root
                open={selected !== null}
                onOpenChange={(open) => {
                  if (!open) closePreview();
                }}
              >
                <Dialog.Portal forceMount>
                  <AnimatePresence initial={false}>
                    {selected !== null && (
                      <Dialog.Overlay forceMount asChild key="overlay">
                        <motion.div
                          className="drawer-overlay"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          transition={{ duration: reduceMotion ? 0 : 0.18 }}
                        />
                      </Dialog.Overlay>
                    )}
                    {selected !== null && (
                      <Dialog.Content
                        forceMount
                        asChild
                        key="reader"
                        aria-describedby={undefined}
                        onCloseAutoFocus={(e) => {
                          e.preventDefault();
                          lastRow.current?.focus({ preventScroll: true });
                        }}
                      >
                        <motion.div
                          className="preview-drawer"
                          initial={{ x: reduceMotion ? 0 : "100%" }}
                          animate={{ x: 0 }}
                          exit={{ x: reduceMotion ? 0 : "100%" }}
                          transition={{
                            duration: reduceMotion ? 0 : 0.22,
                            ease: [0.22, 1, 0.36, 1],
                          }}
                        >
                          <Dialog.Title className="sr-only">
                            {t("书签预览", "Bookmark preview")}
                          </Dialog.Title>
                          {previewContent}
                        </motion.div>
                      </Dialog.Content>
                    )}
                  </AnimatePresence>
                </Dialog.Portal>
              </Dialog.Root>
            )}
          </>
        ) : (
          <div className="page-scroll">
            {view === "setup" ? (
              <SetupFlow
                setup={setup}
                job={job}
                refresh={refresh}
                onDone={() => {
                  remember("fm-setup-skipped", "1");
                  openView("library");
                }}
              />
            ) : view === "import" ? (
              <>
                <header className="page-heading">
                  <h1>{t("导入书签", "Import bookmarks")}</h1>
                  <button className="text-button" onClick={() => openView("setup")}>
                    {t("打开完整向导", "Open setup guide")}
                    <ArrowRight size={14} />
                  </button>
                </header>
                <Importer refresh={refresh} />
              </>
            ) : view === "settings" ? (
              <>
                <header className="page-heading">
                  <h1>{t("设置", "Settings")}</h1>
                  <span className="quiet">
                    {t("配置属于你的检索方式", "Make retrieval your own")}
                  </span>
                </header>
                <Models setup={setup} refresh={refresh} />
                <ExtensionSettings />
                <UpdateSettings />
                <p className="credits">
                  {t("界面组件致谢：", "Interface credits: ")}
                  <a href="https://rareui.com" target="_blank" rel="noreferrer">
                    Rare UI
                  </a>
                </p>
              </>
            ) : view === "tasks" ? (
              <>
                <header className="page-heading">
                  <h1>{t("任务与诊断", "Tasks and diagnostics")}</h1>
                </header>
                <Tasks job={job} setup={setup} refresh={refresh} />
                <HealthTools />
              </>
            ) : (
              <>
                <header className="page-heading">
                  <div>
                    <h1>{t("浏览批次", "Saving sessions")}</h1>
                    <p>
                      {t(
                        "沿着收藏时的上下文，重新发现相关页面。",
                        "Rediscover pages through the context in which you saved them.",
                      )}
                    </p>
                  </div>
                  <Clock3 />
                </header>
                {sessionsError && (
                  <div role="alert">
                    <h3>{t("暂时无法读取浏览批次", "Saving sessions could not be loaded")}</h3>
                    <p className="error">{sessionsError}</p>
                    <button className="secondary" onClick={() => setSessionsRevision((v) => v + 1)}>
                      {t("重试浏览批次", "Retry saving sessions")}
                    </button>
                  </div>
                )}
                {sessionsLoading ? (
                  <p role="status">{t("正在读取浏览批次…", "Loading saving sessions…")}</p>
                ) : sessions.length ? (
                  sessions.map((session) => (
                    <button
                      className="session-row"
                      key={session.session_id}
                      onClick={() => {
                        setFilters({ session: session.session_id });
                        changeQuery("");
                        openView("library");
                      }}
                    >
                      <Clock3 />
                      <span>
                        <strong>
                          {session.label ||
                            new Date(session.started_at * 1000).toLocaleDateString(
                              language === "zh" ? "zh-CN" : "en",
                            )}
                        </strong>
                        <small>
                          {session.size} {t("条书签", "bookmarks")}
                        </small>
                      </span>
                      <ArrowRight />
                    </button>
                  ))
                ) : (
                  !sessionsError && (
                    <div className="empty">
                      <Clock3 size={32} />
                      <h2>{t("还没有浏览批次", "No saving sessions yet")}</h2>
                      <p>
                        {t(
                          "索引完成后，保存时间相近的书签会在这里汇合。",
                          "After indexing, bookmarks saved together appear here.",
                        )}
                      </p>
                    </div>
                  )
                )}
                {sessionsMore && (
                  <button
                    className="secondary"
                    onClick={async () => {
                      try {
                        const more = await api<Session[]>(
                          `/sessions?limit=40&offset=${sessions.length}`,
                        );
                        setSessions((s) => [...s, ...more]);
                        setSessionsMore(more.length === 40);
                      } catch (e) {
                        setSessionsError(String(e));
                      }
                    }}
                  >
                    {t("加载更多", "Load more")}
                    <ArrowDown />
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function HealthTools() {
  const t = useText();
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <details className="health-tools">
      <summary>{t("链接健康检查", "Link health check")}</summary>
      <p>
        {t(
          "点击后会访问最多 20 个原始网址以检查可用性，不会删除书签。",
          "This visits up to 20 original URLs to check availability. Bookmarks are preserved.",
        )}
      </p>
      <button
        className="secondary"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            setMessage(JSON.stringify(await post("/link-health/check", { limit: 20 })));
          } catch (e) {
            setMessage(String(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        {t("确认并检查链接", "Confirm and check links")}
      </button>
      <pre role="status">{message}</pre>
    </details>
  );
}
