import { CapsuleButton } from "./ui/controls";
import { useCallback, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Bookmark as BookmarkIcon,
  Check,
  Clock3,
  Folder,
  Import,
  Layers3,
  LayoutGrid,
  List,
  LoaderCircle,
  Menu,
  Moon,
  Search,
  Settings2,
  Sun,
  WifiOff,
  X,
} from "lucide-react";
import {
  api,
  ApiError,
  post,
  query,
  setToken,
  type Bookmark,
  type Job,
  type Page,
  type Setup,
} from "./api";
import { Locale, useText, type Language } from "./locale";
import SetupFlow, { Importer } from "./Setup";
import { SettingsWorkspace } from "./SettingsWorkspace";
import { Tasks } from "./Tasks";
import { BookmarkCard } from "./BookmarkCard";
import { CollectionTools } from "./CollectionTools";
import type { CollectionScope } from "./api";
import { LibraryDialog, LibraryToolbar, type LibraryAction } from "./LibraryTools";
import { FacetBrowser } from "./FacetBrowser";
import { QuerySuggestions, SearchAnswer } from "./SearchTools";
import Reader, { Skeleton } from "./Reader";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { motionTiming } from "./motion";
import { AnimatePresence, motion } from "motion/react";
import { useReducedMotion } from "./useReducedMotion";
import { InteractionFeedback, SelectionPill, useContentMotion } from "./InteractionMotion";

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
  const themeTransition = useRef<ViewTransition | null>(null);
  const changeTheme = (control: HTMLElement) => {
    const next = theme === "light" ? "dark" : "light";
    themeTransition.current?.skipTransition();
    if (reduceMotion || !document.startViewTransition) { setTheme(next); return; }
    const box = control.getBoundingClientRect();
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    const transition = document.startViewTransition(() => flushSync(() => setTheme(next)));
    themeTransition.current = transition;
    transition.ready.then(() => {
      if (themeTransition.current !== transition || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      document.documentElement.animate({ clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
        { duration: 460, easing: "cubic-bezier(.16,1,.3,1)", pseudoElement: "::view-transition-new(root)" });
    }).catch(() => {});
  };
  useEffect(() => { if (reduceMotion) themeTransition.current?.skipTransition(); }, [reduceMotion]);
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
  const [loadedScope, setLoadedScope] = useState("");
  const [collectionLayout, setCollectionLayout] = useState(() => remember("fm-collection-layout") === "list" ? "list" : "grid");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [libraryAction, setLibraryAction] = useState<LibraryAction | null>(null);
  const [batchMode, setBatchMode] = useState(false);
  const [summaryStatus, setSummaryStatus] = useState<CollectionScope["status"]>("all");
  const [searchMode, setSearchMode] = useState("keyword");
  const [collectionSort, setCollectionSort] = useState("newest");
  const [summaryDisplay, setSummaryDisplay] = useState<"summary" | "original">("summary");
  const [allMatching, setAllMatching] = useState(false);
  const [excludedIds, setExcludedIds] = useState<number[]>([]);
  const collectionScope: CollectionScope = { ...filters, q: search, status: summaryStatus, exclude_ids: excludedIds };
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [libraryNotice, setLibraryNotice] = useState("");
  const libraryRevision = useRef<string | undefined>(undefined);
  const refreshId = useRef(0);
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
  useContentMotion(workspace, view, view === "library" ? ".results-column" : ".page-scroll", "x");
  useContentMotion(list, loadedContext);
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
    const id = ++refreshId.current;
    try {
      const data = await api<Record<string, Facet[]>>("/bookmarks/facets");
      if (id !== refreshId.current) return;
      setFacets(data);
      setConnectionError("");
      try {
        const [status, task] = await Promise.all([
          api<Setup>("/admin/setup-status"),
          api<Job>("/admin/job"),
        ]);
        if (id !== refreshId.current) return;
        setSetup(status);
        setJob(task);
        if (libraryRevision.current === undefined) {
          libraryRevision.current = status.library_revision;
        } else if (status.library_revision !== libraryRevision.current) {
          invalidateLibrary();
          libraryRevision.current = status.library_revision;
        }
        setAdminAvailable(true);
        if (firstRefresh.current) {
          firstRefresh.current = false;
          if (!status.bookmarks && !remember("fm-setup-skipped")) setView("setup");
        }
      } catch (e) {
        if (id !== refreshId.current) return;
        if (e instanceof ApiError && e.status === 403) setAdminAvailable(false);
        else throw e;
      }
    } catch (e) {
      if (id !== refreshId.current) return;
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
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      await refresh();
      if (!cancelled) timer = setTimeout(poll, 4000);
    };
    void poll();
    return () => { cancelled = true; clearTimeout(timer); };
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
  const resultScope = JSON.stringify([search, filterKey, summaryStatus, collectionSort, searchMode]);
  const resultContext = JSON.stringify([search, offset, filterKey, summaryStatus, collectionSort, searchMode]);
  // Paging keeps the current scope, so the previous rows stay on screen until
  // the next page arrives. A new query changes the scope and clears them.
  const page =
    loadedContext === resultContext || (loadedScope === resultScope && loadedPage)
      ? loadedPage
      : null;
  const scopePending = loading || !page || Boolean(error);
  const activeFilters = Object.entries(filters).filter(([, value]) => value !== undefined);
  const pageSize = page?.limit || 30;
  const currentPage = Math.floor(offset / pageSize) + 1;
  const paginationPage = page;
  const pageCount = Math.max(1, Math.ceil((paginationPage?.total || 0) / pageSize));
  useEffect(() => setPageInput(String(currentPage)), [currentPage, filterKey, search]);
  useEffect(() => {
    setSelectedIds([]);
    setBatchMode(false);
    setAllMatching(false);
    setExcludedIds([]);
  }, [search, filterKey, summaryStatus, searchMode]);
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
        if (offset > 0 && offset >= data.total) {
          setOffset(Math.max(0, Math.ceil(data.total / 30) - 1) * 30);
          return;
        }
        setPage(data);
        setLoadedContext(resultContext);
        setLoadedScope(resultScope);
        if (data.depth) setDepth(data.depth);
        setLoading(false);
      }
    };
    setLoading(true);
    setError("");
    const timer = setTimeout(
      async () => {
        try {
          if (search.trim() && searchMode === "semantic" && semantic) {
            const fast = await api<Page>(`/quick?${query({ q: searchTerms, offset, limit: 30, depth })}`, { signal: abort.signal });
            update(fast);
            update(await post<Page>("/search", { q: searchTerms, offset, limit: 30, depth: depth ?? fast.depth }, abort.signal));
            return;
          }
          update(await api<Page>(`/bookmarks?${query({ ...filters, q: search, status: summaryStatus, sort: collectionSort, offset, limit: 30 })}`, {
            signal: abort.signal,
          }));
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
  }, [paired, view, search, offset, filterKey, summaryStatus, collectionSort, searchMode, semantic, requestRevision]);
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
      list.current?.querySelectorAll<HTMLButtonElement>(".bookmark-preview")[selectedPosition + step];
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
      <InteractionFeedback />
      <header className="app-header" inert={navOpen} aria-hidden={navOpen}>
        <CapsuleButton
          className="icon-button nav-trigger"
          aria-label={t("打开导航", "Open navigation")}
          onClick={() => setNavOpen(true)}
        >
          <Menu />
        </CapsuleButton>
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
          <CapsuleButton
            className={view === "library" ? "active" : ""}
            onClick={() => {
              openView("library");
              setFilters({});
              changeQuery("");
            }}
          >
            <SelectionPill active={view === "library"} group="app-navigation" />
            <BookmarkIcon size={22} aria-hidden="true" />
            <span>{t("全部书签", "All bookmarks")}</span>
          </CapsuleButton>
          <CapsuleButton
            className={view === "sessions" ? "active" : ""}
            onClick={() => openView("sessions")}
          >
            <SelectionPill active={view === "sessions"} group="app-navigation" />
            <Clock3 size={22} aria-hidden="true" />
            <span>{t("浏览批次", "Saving sessions")}</span>
          </CapsuleButton>
        </nav>
        {paired && view === "library" && <aside className="collection-sidebar" aria-label={t("收藏目录", "Collection directory")}>
          <FacetBrowser filters={filters} enabled={!navOpen} revision={requestRevision} onSelect={selectFilter}
            onManage={adminAvailable && job.state !== "running" ? () => setLibraryAction({ kind: "taxonomy" }) : undefined} />
        </aside>}
        <div className="header-utilities">
          {setup?.demo && <span className="demo-label">{t("合成演示数据", "Synthetic demo")}</span>}
          <div className="utility-cluster">
            {adminAvailable && (
              <>
                <CapsuleButton
                  className="icon-button utility-label"
                  aria-label={t("任务", "Tasks")}
                  aria-pressed={view === "tasks"}
                  title={t("任务", "Tasks")}
                  onClick={() => openView("tasks")}
                >
                  <SelectionPill active={view === "tasks"} group="app-navigation" />
                  {job.state === "running" ? <LoaderCircle className="spin" /> : <Layers3 />}
                  <span>{t("任务", "Tasks")}</span>
                </CapsuleButton>
                <CapsuleButton
                  className="icon-button utility-label"
                  aria-label={t("设置", "Settings")}
                  aria-pressed={view === "settings"}
                  title={t("设置", "Settings")}
                  onClick={() => openView("settings")}
                >
                  <SelectionPill active={view === "settings"} group="app-navigation" />
                  <Settings2 />
                  <span>{t("设置", "Settings")}</span>
                </CapsuleButton>
              </>
            )}
            <CapsuleButton
              className="icon-button"
              aria-label={t("切换主题", "Toggle theme")}
              onClick={event => changeTheme(event.currentTarget)}
            >
              {theme === "light" ? <Moon /> : <Sun />}
            </CapsuleButton>
            <CapsuleButton
              className="language"
              aria-label={t("切换语言", "Switch language")}
              onClick={() => setLanguage(language === "zh" ? "en" : "zh")}
            >
              {language === "zh" ? "EN" : "中文"}
            </CapsuleButton>
          </div>
          {adminAvailable && (
            <CapsuleButton className="header-import" onClick={() => openView("import")}>
              <Import size={16} />
              <span>{t("导入书签", "Import bookmarks")}</span>
            </CapsuleButton>
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
          <CapsuleButton
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
          </CapsuleButton>
          <CapsuleButton
            className={view === "sessions" ? "active" : ""}
            onClick={() => openView("sessions")}
          >
            <Clock3 />
            {t("浏览批次", "Saving sessions")}
          </CapsuleButton>
        </nav>
        <div className="facet-nav">
          {/* The collection sidebar below repeats this directory at ≥960px.
              Mount only while the drawer is open so both copies do not fetch. */}
          {navOpen && <FacetBrowser filters={filters} enabled={paired && navOpen} revision={requestRevision} onSelect={selectFilter}
            onManage={adminAvailable && job.state !== "running" ? () => { setNavOpen(false); setLibraryAction({ kind: "taxonomy" }); } : undefined} />}
        </div>
        <div className="sidebar-bottom">
          {adminAvailable && (
            <>
              <CapsuleButton
                className={view === "import" ? "active" : ""}
                onClick={() => openView("import")}
              >
                <Import />
                {t("导入书签", "Import bookmarks")}
              </CapsuleButton>
              <CapsuleButton
                className={view === "tasks" ? "active" : ""}
                onClick={() => openView("tasks")}
              >
                {job.state === "running" ? <LoaderCircle className="spin" /> : <Layers3 />}
                {t("任务", "Tasks")}
                {job.state === "running" && <span className="activity-dot" />}
              </CapsuleButton>
              <CapsuleButton
                className={view === "settings" ? "active" : ""}
                onClick={() => openView("settings")}
              >
                <Settings2 />
                {t("设置", "Settings")}
              </CapsuleButton>
            </>
          )}
          <div className="appearance">
            <CapsuleButton
              className="icon-button"
              aria-label={t("切换主题", "Toggle theme")}
              onClick={event => changeTheme(event.currentTarget)}
            >
              {theme === "light" ? <Moon /> : <Sun />}
            </CapsuleButton>
            <CapsuleButton
              className="language"
              aria-label={t("切换语言", "Switch language")}
              onClick={() => setLanguage(language === "zh" ? "en" : "zh")}
            >
              {language === "zh" ? "EN" : "中文"}
            </CapsuleButton>
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
        className={`main-workspace ${paired && view === "library" ? "with-preview" : ""} ${selected !== null ? "has-selection" : "browse-mode"} ${collectionLayout === "list" ? "list-mode" : ""} ${focusReading && view === "library" ? "focus-mode" : ""}`}
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
            <CapsuleButton
              className="secondary"
              onClick={() => {
                if (paired) {
                  refresh();
                  setRequestRevision((v) => v + 1);
                } else boot();
              }}
            >
              {t("重新连接", "Reconnect")}
            </CapsuleButton>
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
            <CapsuleButton
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
            </CapsuleButton>
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
                <h1 title={filters.folder}>
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
                    onBlur={() => { composing.current = false; }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.nativeEvent.isComposing && !composing.current)
                        changeQuery(input, true);
                    }}
                  />
                  {input ? (
                    <CapsuleButton
                      className="icon-button"
                      aria-label={t("清空搜索", "Clear search")}
                      onClick={() => changeQuery("")}
                    >
                      <X size={16} />
                    </CapsuleButton>
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
                <CapsuleButton
                  className="filter-trigger"
                  onClick={() => setNavOpen(true)}
                  aria-label={t("筛选收藏", "Filter collection")}
                  aria-describedby={activeFilters.length ? "active-filter-count" : undefined}
                >
                  <Folder size={17} />
                  <span>{t("分类", "Categories")}</span>
                  {activeFilters.length > 0 && <>
                    <span className="filter-indicator" aria-hidden="true">{activeFilters.length}</span>
                    <span id="active-filter-count" className="sr-only">{t(`已启用 ${activeFilters.length} 项筛选`, `${activeFilters.length} active filters`)}</span>
                  </>}
                </CapsuleButton>
              </div>
            </header>
            <section className="results-column" inert={focusReading}>
              <header className="search-header">
                {adminAvailable && selected === null && <LibraryToolbar
                  batch={batchMode && !allMatching} ids={selectedIds} pageIds={items.map(item => item.bookmark_id)}
                  disabled={job.state === "running"} pending={scopePending}
                  onBatch={value => { setBatchMode(value); setSelectedIds([]); setAllMatching(false); setExcludedIds([]); }}
                  onIds={setSelectedIds} onAction={setLibraryAction}
                  onSummarize={() => setLibraryAction({ kind: "process", mode: "summarize",
                    // Keyword mode has a server scope, so the dialog can preview
                    // and exclude across pages without shipping every ID. The
                    // counts shown beside the button then match what starts.
                    ...(search.trim() && searchMode === "semantic" && semantic ? { ids: items.map(item => item.bookmark_id) }
                      : { scope: collectionScope, scopeLabel: t("当前筛选结果", "Current matching results") }) })}
                />}
                {selected === null && !(search.trim() && searchMode === "semantic" && semantic) && <CollectionTools scope={collectionScope} page={page} display={summaryDisplay} onDisplay={setSummaryDisplay}
                  sort={collectionSort} onSort={value => { setCollectionSort(value); setOffset(0); }}
                  onStatus={value => { setSummaryStatus(value); setOffset(0); }} disabled={scopePending}
                  selecting={batchMode} allMatching={allMatching} selectedCount={allMatching ? Math.max(0, (page?.total || 0) - excludedIds.length) : selectedIds.length}
                  onAll={() => { setAllMatching(true); setBatchMode(false); setExcludedIds([]); setSelectedIds([]); }}
                  onClear={() => { setAllMatching(false); setBatchMode(false); setExcludedIds([]); setSelectedIds([]); }}
                  onSummarizeSelection={() => setLibraryAction({ kind: "process", mode: "summarize", ...(allMatching ? { scope: collectionScope, scopeLabel: t("跨页所选收藏", "Selection across pages") } : { ids: selectedIds }) })}
                  job={job} refresh={refresh} admin={adminAvailable}/>}
                <div className="search-controls">
                  <div className="search-meta">
                    {semantic && <select className="search-mode-select" aria-label={t("检索方式", "Search mode")} value={searchMode}
                      onChange={event => { setSearchMode(event.target.value); setOffset(0); setDepth(undefined); }}>
                      <option value="keyword">{t("关键词", "Keyword")}</option>
                      <option value="semantic" disabled={!semantic}>{t("语义检索", "Semantic search")}</option>
                    </select>}
                    <span className="collection-hint">
                      {search
                        ? searchMode === "semantic" && semantic ? t("语义检索结果", "Semantic results") : t("全部关键词匹配", "All keyword matches")
                        : t("直接打开原网页 · 摘要就地浏览", "Open original pages · Read summaries here")}
                    </span>
                    {selected === null && <div className="collection-view-switch" role="group" aria-label={t("收藏显示方式", "Collection layout")}>
                      {[{ value: "grid", label: t("卡片视图", "Card view"), Icon: LayoutGrid },
                        { value: "list", label: t("列表视图", "List view"), Icon: List }].map(({ value, label, Icon }) =>
                        <CapsuleButton key={value} type="button" aria-label={label} title={label} aria-pressed={collectionLayout === value}
                          onClick={() => { setCollectionLayout(value); remember("fm-collection-layout", value); }}><SelectionPill active={collectionLayout === value} group="collection-layout" /><Icon size={16} /></CapsuleButton>)}
                      <CapsuleButton className="collection-view-toggle" type="button"
                        aria-label={collectionLayout === "grid" ? t("列表视图", "List view") : t("卡片视图", "Card view")}
                        title={collectionLayout === "grid" ? t("列表视图", "List view") : t("卡片视图", "Card view")}
                        onClick={() => {
                          const value = collectionLayout === "grid" ? "list" : "grid";
                          setCollectionLayout(value); remember("fm-collection-layout", value);
                        }}>{collectionLayout === "grid" ? <List size={16} /> : <LayoutGrid size={16} />}</CapsuleButton>
                    </div>}
                  </div>
                </div>
                {activeFilters.length > 0 && (
                  <div className="filter-chips" aria-label={t("当前筛选", "Active filters")}>
                    {activeFilters.map(([key, value]) => (
                        <CapsuleButton
                          key={key}
                          title={`${filterName(key)}: ${value === "" ? t("未分类", "Unfiled") : value}`}
                          aria-label={t(`移除${filterName(key)}筛选：${value === "" ? "未分类" : value}`, `Remove ${filterName(key)} filter: ${value === "" ? "Unfiled" : value}`)}
                          onClick={() => selectFilter(key as keyof Filters, undefined)}
                        >
                          <span className="filter-kind">{filterName(key)}</span>
                          <span className="filter-value">{value === "" ? t("未分类", "Unfiled") : value}</span>
                          <X size={14} aria-hidden="true" />
                        </CapsuleButton>
                      ))}
                    <CapsuleButton className="clear-filters" onClick={clearFilters}>{t("清除筛选", "Clear filters")}</CapsuleButton>
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
                  <CapsuleButton className="text-button" onClick={() => setRequestRevision((v) => v + 1)}>
                    {t("重试", "Retry")}
                  </CapsuleButton>
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
                      <CapsuleButton
                        className="secondary"
                        onClick={() => {
                          setFilters({});
                          changeQuery("");
                          setOffset(0);
                        }}
                      >
                        {t("清除条件，查看全部", "Clear filters and show all")}
                      </CapsuleButton>
                    )}
                    {!hasSearchContext && adminAvailable && (
                      <CapsuleButton className="primary" onClick={() => openView("import")}>
                        <Import />
                        {t("导入书签", "Import bookmarks")}
                      </CapsuleButton>
                    )}
                  </div>
                ) : (
                  items.map((record, index) => <BookmarkCard key={record.bookmark_id} record={record} entranceOrder={index}
                    selected={selected === record.bookmark_id}
                    checked={allMatching ? !excludedIds.includes(record.bookmark_id) : selectedIds.includes(record.bookmark_id)}
                    disabled={scopePending} display={summaryDisplay}
                    onEdit={adminAvailable && job.state !== "running" ? () => setLibraryAction({ kind: "edit", record }) : undefined}
                    onCheck={() => {
                      if (allMatching) setExcludedIds(ids => ids.includes(record.bookmark_id) ? ids.filter(id => id !== record.bookmark_id) : [...ids, record.bookmark_id].slice(0, 10000));
                      else { setBatchMode(true); setSelectedIds(ids => ids.includes(record.bookmark_id) ? ids.filter(id => id !== record.bookmark_id) : [...ids, record.bookmark_id].slice(0, 1000)); }
                    }}
                    onPreview={button => select(record.bookmark_id, button)}
                    onSummarize={adminAvailable ? () => setLibraryAction({ kind: "process", mode: "summarize", ids: [record.bookmark_id] }) : undefined}
                  />)
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
                    <CapsuleButton type="submit" disabled={scopePending}>{t("跳转", "Go")}</CapsuleButton>
                  </form>}
                  <CapsuleButton
                    className="icon-button"
                    disabled={!page?.offset || loading}
                    aria-label={t("上一页", "Previous page")}
                    onClick={() => paginate(Math.max(0, (page?.offset || 0) - (page?.limit || 30)))}
                  >
                    <ArrowLeft />
                  </CapsuleButton>
                  <CapsuleButton
                    className="icon-button"
                    disabled={!page?.has_more || loading || page.depth_capped}
                    aria-label={t("下一页", "Next page")}
                    onClick={() => paginate((page?.offset || 0) + (page?.limit || 30))}
                  >
                    <ArrowRight />
                  </CapsuleButton>
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
                  <CapsuleButton className="text-button" onClick={() => openView("setup")}>
                    {t("打开完整向导", "Open setup guide")}
                    <ArrowRight size={14} />
                  </CapsuleButton>
                </header>
                <Importer refresh={refresh} onDone={() => openView("library")} />
              </>
            ) : view === "settings" ? (
              <SettingsWorkspace setup={setup} refresh={refresh} onChanged={libraryChanged} onBack={() => openView("library")} onSummarize={() => setLibraryAction({ kind: "process", mode: "summarize", scope: collectionScope, scopeLabel: t("当前收藏范围", "Current collection scope") })} />
            ) : view === "tasks" ? (
              <>
                <header className="page-heading">
                  <div><h1>{t("任务与诊断", "Tasks and diagnostics")}</h1><p>{t("查看进度，继续处理未完成的收藏。", "Follow progress and resume unfinished work.")}</p></div>
                  <CapsuleButton className="text-button support-back" onClick={() => openView("library")}><ArrowLeft size={16}/>{t("返回收藏", "Back to collection")}</CapsuleButton>
                </header>
                <Tasks job={job} setup={setup} refresh={refresh} onBack={() => openView("library")} onProcess={(mode) => setLibraryAction({ kind: "process", mode })} />
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
                    <CapsuleButton className="secondary" onClick={() => setSessionsRevision((v) => v + 1)}>
                      {t("重试浏览批次", "Retry saving sessions")}
                    </CapsuleButton>
                  </div>
                )}
                {sessionsLoading ? (
                  <p role="status">{t("正在读取浏览批次…", "Loading saving sessions…")}</p>
                ) : sessions.length ? (
                  sessions.map((session) => (
                    <CapsuleButton
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
                    </CapsuleButton>
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
                  <CapsuleButton
                    className="secondary"
                    disabled={sessionsLoading}
                    onClick={async () => {
                      if (sessionsLoading) return;
                      setSessionsLoading(true);
                      try {
                        const more = await api<Session[]>(
                          `/sessions?limit=40&offset=${sessions.length}`,
                        );
                        setSessions((s) => {
                          const seen = new Set(s.map((row) => row.session_id));
                          return [...s, ...more.filter((row) => !seen.has(row.session_id))];
                        });
                        setSessionsMore(more.length === 40);
                      } catch (e) {
                        setSessionsError(String(e));
                      } finally {
                        setSessionsLoading(false);
                      }
                    }}
                  >
                    {sessionsLoading ? <LoaderCircle className="spin" /> : <ArrowDown />}
                    {t("加载更多", "Load more")}
                  </CapsuleButton>
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
        onJobStarted={async () => { await refresh(); setRequestRevision(v => v + 1); }}
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
      <CapsuleButton
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
      </CapsuleButton>
      <pre role="status">{message}</pre>
    </details>
  );
}
