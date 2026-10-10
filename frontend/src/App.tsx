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
  Import,
  Layers3,
  LayoutGrid,
  List,
  LoaderCircle,
  Menu,
  Moon,
  PanelRightClose,
  Search,
  Settings2,
  Sparkles,
  Sun,
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
import { LibraryDialog, LibraryToolbar, type LibraryAction } from "./LibraryTools";
import { SyncSettings } from "./SyncSettings";
import { FacetBrowser } from "./FacetBrowser";
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
  const [pageInput, setPageInput] = useState("1");
  const [depth, setDepth] = useState<number>();
  const [loadedPage, setPage] = useState<Page | null>(null);
  const [loadedContext, setLoadedContext] = useState("");
  const [collectionLayout, setCollectionLayout] = useState(() => remember("fm-collection-layout") === "list" ? "list" : "grid");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [libraryAction, setLibraryAction] = useState<LibraryAction | null>(null);
  const [batchMode, setBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [libraryNotice, setLibraryNotice] = useState("");
  const libraryRevision = useRef<string | undefined>(undefined);
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
  const splitScroll = useRef(0);
  const { contextSafe } = useGSAP({ scope: workspace });
  const toggleFocus = contextSafe(() => {
    const pane = readerPane.current;
    if (!pane) return;
    const before = pane.getBoundingClientRect();
    if (!focusReading)
      splitScroll.current = pane.querySelector<HTMLElement>(".preview-scroll")?.scrollTop ?? 0;
    if (focusFrame.current !== null) cancelAnimationFrame(focusFrame.current);
    const next = !focusReading;
    setFocusReading(next);
    // React commits layout before the next frame; do not queue a delayed entrance.
    focusFrame.current = requestAnimationFrame(
      contextSafe(() => {
        if (!readerPane.current) return;
        focusTimeline.current?.kill();
        gsap.set(readerPane.current, { x: 0, y: 0 });
        const after = readerPane.current.getBoundingClientRect();
        if (!next)
          readerPane.current
            .querySelector<HTMLElement>(".preview-scroll")
            ?.scrollTo({ top: splitScroll.current });
        if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
          gsap.set(readerPane.current, { clearProps: "transform" });
          return;
        }
        focusTimeline.current = gsap
          .timeline({ defaults: motionTiming })
          .fromTo(
            readerPane.current,
            { x: before.left - after.left, y: before.top - after.top },
            { x: 0, y: 0, clearProps: "transform" },
          );
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
  const invalidateLibrary = useCallback(() => {
    readerCache.current.clear();
    setRequestRevision((value) => value + 1);
    setPreviewRevision((value) => value + 1);
    setSessionsRevision((value) => value + 1);
    setDepth(undefined);
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
        if (libraryRevision.current === undefined) {
          libraryRevision.current = status.library_revision;
        } else if (task.state !== "running" && status.library_revision !== libraryRevision.current) {
          invalidateLibrary();
          libraryRevision.current = status.library_revision;
        }
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
  }, [invalidateLibrary]);
  async function libraryChanged(deleted?: number[]) {
    if (selected !== null && deleted?.includes(selected)) closePreview();
    setSelectedIds([]);
    setBatchMode(false);
    invalidateLibrary();
    await refresh();
    setLibraryNotice(t("收藏已更新", "Collection updated"));
  }
  useEffect(() => {
    if (!libraryNotice) return;
    const timer = setTimeout(() => setLibraryNotice(""), 5000);
    return () => clearTimeout(timer);
  }, [libraryNotice]);
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
      if (event.isComposing || libraryAction) return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setFocusReading(false);
        setView("library");
        setNavOpen(false);
        requestAnimationFrame(() => searchInput.current?.focus());
      }
      if (event.key === "Escape" && selected !== null && !drawer && !event.defaultPrevented) {
        event.preventDefault();
        if (focusReading) {
          setFocusReading(false);
          requestAnimationFrame(() =>
            readerPane.current
              ?.querySelector<HTMLElement>(".preview-scroll")
              ?.scrollTo({ top: splitScroll.current }),
          );
        } else closePreview();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selected, drawer, closePreview, focusReading, libraryAction]);
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
  function changeQuery(value: string, force = false) {
    setInput(value);
    if (composing.current) return;
    if (value === search && offset === 0 && !force) return;
    browseScroll.current = 0;
    list.current?.scrollTo({ top: 0 });
    setSelected(null);
    setFocusReading(false);
    abortRef.current?.abort();
    requestId.current++;
    setSearch(value);
    setOffset(0);
    setDepth(undefined);
    if (force) setRequestRevision(value => value + 1);
  }
  const filterKey = JSON.stringify(filters);
  const resultContext = JSON.stringify([search, offset, filterKey]);
  const page = loadedContext === resultContext ? loadedPage : null;
  const scopePending = loading || !page || Boolean(error);
  const activeFilters = Object.entries(filters).filter(([, value]) => value !== undefined);
  const pageSize = page?.limit || 30;
  const currentPage = Math.floor(offset / pageSize) + 1;
  const sameLoadedScope = loadedContext === JSON.stringify([search, loadedPage?.offset, filterKey]);
  const paginationPage = page || (sameLoadedScope ? loadedPage : null);
  const pageCount = Math.max(1, Math.ceil((paginationPage?.total || 0) / pageSize));
  useEffect(() => setPageInput(String(currentPage)), [currentPage, filterKey, search]);
  useEffect(() => {
    setSelectedIds([]);
    setBatchMode(false);
  }, [search, filterKey]);
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
        if (!search.trim() && offset > 0 && offset >= data.total) {
          setOffset(Math.max(0, Math.ceil(data.total / 30) - 1) * 30);
          return;
        }
        setPage(data);
        setLoadedContext(resultContext);
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
        if (!abort.signal.aborted && e instanceof ApiError && e.status === 404) {
          closePreview();
          setLibraryNotice(t("这条收藏已被移除", "This bookmark was removed"));
          return;
        }
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
    setView("library");
    setNavOpen(false);
    setSelected(null);
    setFocusReading(false);
    // Re-selecting a category must not abort the request already loading it.
    if (filters[key] === value && offset === 0) return;
    browseScroll.current = 0;
    list.current?.scrollTo({ top: 0 });
    abortRef.current?.abort();
    requestId.current++;
    setFilters((old) => ({ ...old, [key]: value }));
    setOffset(0);
    setDepth(undefined);
  }
  function paginate(next: number) {
    if (next === offset) return;
    abortRef.current?.abort();
    requestId.current++;
    setSelected(null);
    setFocusReading(false);
    browseScroll.current = 0;
    setOffset(next);
    list.current?.scrollTo({ top: 0 });
  }
  function clearFilters() {
    if (!activeFilters.length) return;
    abortRef.current?.abort();
    requestId.current++;
    setSelected(null);
    setFocusReading(false);
    setFilters({});
    setOffset(0);
    setDepth(undefined);
    browseScroll.current = 0;
    list.current?.scrollTo({ top: 0 });
  }
  function filterName(key: string) {
    return key === "folder" ? t("文件夹", "Folder") : key === "tag" ? t("标签", "Tag") :
      key === "domain" ? t("站点", "Site") : t("批次", "Session");
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
      onAction={adminAvailable ? setLibraryAction : undefined}
      running={job.state === "running"}
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
      <header className="app-header" inert={navOpen} aria-hidden={navOpen}>
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
            <BookmarkIcon size={15} aria-hidden="true" />
            {t("全部书签", "All bookmarks")}
          </button>
          <button
            className={view === "sessions" ? "active" : ""}
            onClick={() => openView("sessions")}
          >
            <Clock3 size={15} aria-hidden="true" />
            {t("浏览批次", "Saving sessions")}
          </button>
        </nav>
        <div className="header-utilities">
          {setup?.demo && <span className="demo-label">{t("合成演示数据", "Synthetic demo")}</span>}
          <div className="utility-cluster">
            {adminAvailable && (
              <>
                <button
                  className="icon-button"
                  aria-label={t("任务", "Tasks")}
                  aria-pressed={view === "tasks"}
                  title={t("任务", "Tasks")}
                  onClick={() => openView("tasks")}
                >
                  {job.state === "running" ? <LoaderCircle className="spin" /> : <Layers3 />}
                </button>
                <button
                  className="icon-button"
                  aria-label={t("设置", "Settings")}
                  aria-pressed={view === "settings"}
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
          </div>
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
        aria-hidden={!navOpen}
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
          <FacetBrowser filters={filters} enabled={paired && navOpen} revision={requestRevision} onSelect={selectFilter} />
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
        aria-hidden={navOpen}
        className={`main-workspace ${view === "library" ? "with-preview" : ""} ${selected !== null ? "has-selection" : "browse-mode"} ${collectionLayout === "list" ? "list-mode" : ""} ${focusReading && view === "library" ? "focus-mode" : ""}`}
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
                  {search.trim() ? t("搜索结果", "Search results") :
                    filters.folder !== undefined ? filters.folder || t("未分类", "Unfiled") :
                    filters.tag || filters.domain || (filters.session !== undefined ? t("浏览批次", "Saving session") : t("我的收藏", "Your collection"))}
                </h1>
                <span>
                  <span className="result-count" aria-live="polite">{loading || !page ? "…" : page.total}{page?.depth_capped ? "+" : ""}</span> {t("条收藏", "saved pages")}
                </span>
              </div>
              <div className="workspace-search">
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
                      changeQuery(e.currentTarget.value, true);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.nativeEvent.isComposing && !composing.current)
                        changeQuery(input, true);
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
                  aria-describedby={activeFilters.length ? "active-filter-count" : undefined}
                >
                  <Settings2 size={17} />
                  <span>{t("筛选", "Filters")}</span>
                  {activeFilters.length > 0 && <>
                    <span className="filter-indicator" aria-hidden="true">{activeFilters.length}</span>
                    <span id="active-filter-count" className="sr-only">{t(`已启用 ${activeFilters.length} 项筛选`, `${activeFilters.length} active filters`)}</span>
                  </>}
                </button>
              </div>
            </header>
            <aside className="collection-sidebar" hidden={selected !== null}>
              <FacetBrowser filters={filters} enabled={selected === null && !navOpen} revision={requestRevision} onSelect={selectFilter} />
            </aside>
            <section className="results-column" inert={focusReading}>
              <header className="search-header">
                {adminAvailable && selected === null && <LibraryToolbar
                  batch={batchMode} ids={selectedIds} pageIds={items.map(item => item.bookmark_id)}
                  disabled={job.state === "running"} pending={scopePending}
                  onBatch={value => { setBatchMode(value); setSelectedIds([]); }}
                  onIds={setSelectedIds} onAction={setLibraryAction}
                />}
                <div className="search-controls">
                  <div className="search-meta">
                    <span>
                      {search
                        ? semantic
                          ? t("关键词 + 语义检索", "Keyword + semantic search")
                          : t("关键词检索", "Keyword search")
                        : t("按收藏时间排列", "Recently saved first")}
                    </span>
                    {selected === null && <div className="collection-view-switch" role="group" aria-label={t("收藏显示方式", "Collection layout")}>
                      {[{ value: "grid", label: t("卡片视图", "Card view"), Icon: LayoutGrid },
                        { value: "list", label: t("列表视图", "List view"), Icon: List }].map(({ value, label, Icon }) =>
                        <button key={value} type="button" aria-label={label} title={label} aria-pressed={collectionLayout === value}
                          onClick={() => { setCollectionLayout(value); remember("fm-collection-layout", value); }}><Icon size={16} /></button>)}
                    </div>}
                  </div>
                </div>
                {activeFilters.length > 0 && (
                  <div className="filter-chips" aria-label={t("当前筛选", "Active filters")}>
                    {activeFilters.map(([key, value]) => (
                        <button
                          key={key}
                          title={`${filterName(key)}: ${value === "" ? t("未分类", "Unfiled") : value}`}
                          aria-label={t(`移除${filterName(key)}筛选：${value === "" ? "未分类" : value}`, `Remove ${filterName(key)} filter: ${value === "" ? "Unfiled" : value}`)}
                          onClick={() => selectFilter(key as keyof Filters, undefined)}
                        >
                          <span className="filter-kind">{filterName(key)}</span>
                          <span className="filter-value">{value === "" ? t("未分类", "Unfiled") : value}</span>
                          <X size={14} aria-hidden="true" />
                        </button>
                      ))}
                    <button className="clear-filters" onClick={clearFilters}>{t("清除筛选", "Clear filters")}</button>
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
                      className={`result-row ${selected === record.bookmark_id ? "selected" : ""} ${batchMode && selectedIds.includes(record.bookmark_id) ? "batch-selected" : ""}`}
                      key={record.bookmark_id}
                      disabled={scopePending}
                      onClick={(e) => {
                        if (batchMode) setSelectedIds((ids) => ids.includes(record.bookmark_id)
                          ? ids.filter((id) => id !== record.bookmark_id)
                          : [...ids, record.bookmark_id].slice(0, 1000));
                        else select(record.bookmark_id, e.currentTarget);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                          e.preventDefault();
                          const next = items[index + (e.key === "ArrowDown" ? 1 : -1)];
                          const button =
                            list.current?.querySelectorAll<HTMLButtonElement>(".result-row")[
                              index + (e.key === "ArrowDown" ? 1 : -1)
                            ];
                          if (next && button) {
                            if (!batchMode) select(next.bookmark_id, button);
                            button.focus();
                          }
                        }
                      }}
                      aria-pressed={batchMode ? selectedIds.includes(record.bookmark_id) : selected === record.bookmark_id}
                    >
                      <span className="result-copy">
                        <span className="result-source">
                          {batchMode && <span className="batch-check" aria-hidden="true">{selectedIds.includes(record.bookmark_id) && <Check size={13}/>}</span>}
                          <span className="site-letter" aria-hidden="true">
                            {(record.domain || record.title || "F").slice(0, 1).toUpperCase()}
                          </span>
                          <span className="source-domain">{record.domain}</span>
                          {selected === record.bookmark_id ? (
                            <span className="reading-label">{t("正在阅读", "Reading")}</span>
                          ) : (
                            <ArrowRight className="result-open" size={16} aria-hidden="true" />
                          )}
                        </span>
                        <span className="result-title" title={record.title || record.url}>{record.title || record.url}</span>
                        {(record.snippet || record.summary) &&
                          (record.snippet || record.summary) !== record.title && (
                            <span className="result-summary">
                              {record.snippet || record.summary}
                            </span>
                          )}
                        <span className="result-meta">
                          <span className="result-folder">
                            <Folder size={12} />
                            <span>{record.folder || t("未分类", "Unfiled")}</span>
                          </span>
                          <SavedDate seconds={record.date_added} language={language} />
                        </span>
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
                  {selected === null && pageCount > 1 && !paginationPage?.depth_capped && <form className="page-jump"
                    onSubmit={event => {
                      event.preventDefault();
                      const target = Number(pageInput);
                      if (!scopePending && Number.isInteger(target) && target >= 1 && target <= pageCount)
                        paginate((target - 1) * pageSize);
                    }}>
                    <input type="number" min={1} max={pageCount} required inputMode="numeric"
                      aria-label={t("跳转页码", "Page to jump to")} value={pageInput} disabled={scopePending}
                      onChange={event => setPageInput(event.target.value)} />
                    <span aria-label={t(`共 ${pageCount} 页`, `${pageCount} pages`)}>/ {pageCount}</span>
                    <button type="submit" disabled={scopePending}>{t("跳转", "Go")}</button>
                  </form>}
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
                  if (!open && !libraryAction) closePreview();
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
                onProcess={(mode) => setLibraryAction({ kind: "process", mode })}
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
                <SyncSettings onChanged={libraryChanged} />
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
                <Tasks job={job} setup={setup} refresh={refresh} onProcess={(mode) => setLibraryAction({ kind: "process", mode })} />
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
      {libraryNotice && <div className="library-toast" role="status"><Check size={16}/>{libraryNotice}</div>}
      {libraryAction && <LibraryDialog
        key={`${libraryAction.kind}-${libraryAction.kind === "edit" ? libraryAction.record.bookmark_id : ""}`}
        action={libraryAction}
        onClose={() => setLibraryAction(null)}
        onChanged={libraryChanged}
        onJobStarted={async () => { await refresh(); setFocusReading(false); openView("tasks"); }}
        facets={facets}
        setup={setup}
        running={job.state === "running"}
        pageIds={items.map((item) => item.bookmark_id)}
        selectedIds={selectedIds}
        filters={filters}
        searching={Boolean(search.trim())}
      />}
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
