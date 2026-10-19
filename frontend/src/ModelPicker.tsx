import { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, LoaderCircle, RefreshCw, Search } from "lucide-react";
import { post } from "./api";
import { useText } from "./locale";
import { OverlayMotion } from "./overlay-motion";
import { useReducedMotion } from "./useReducedMotion";

type Choice = { id: string; label: string; source: string };
type Catalog = { agent?: string; models: Choice[]; default_model: string; warning: string };

export function ModelPicker({ name, value, onChange, payload, identity, agent, disabled, autoLoad = false }: {
  name: string; value: string; onChange: (value: string) => void;
  payload: Record<string, unknown>; identity: string; agent?: string; disabled: boolean;
  autoLoad?: boolean;
}) {
  const t = useText();
  const reduced = useReducedMotion();
  const id = useId();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(0);
  const [manual, setManual] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const filter = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const abort = useRef<AbortController | null>(null);
  const latestPayload = useRef(payload);
  latestPayload.current = payload;

  async function load() {
    abort.current?.abort();
    const request = new AbortController();
    abort.current = request;
    setBusy(true);
    setError("");
    try {
      const data = await post<Catalog>("/admin/settings/models", latestPayload.current, request.signal);
      if (agent && data.agent && data.agent !== agent)
        throw new Error(t("检测到的 Agent 已变化，请重新检测后读取模型。", "The detected agent changed. Detect agents again to read its models."));
      if (!request.signal.aborted) setCatalog(data);
    } catch (e) {
      if (!request.signal.aborted) setError(String(e));
    } finally {
      if (!request.signal.aborted) setBusy(false);
    }
  }
  useEffect(() => {
    abort.current?.abort();
    setCatalog(null); setError(""); setOpen(false); setSearch(""); setBusy(false);
    return () => abort.current?.abort();
    // Identity includes provider, credential draft and resolved installation path.
    // Editing a model does not refetch its own catalog.
  }, [identity]);
  useEffect(() => {
    if (autoLoad && !disabled) void load();
  }, [identity, autoLoad, disabled]);
  useEffect(() => {
    if (!open) return;
    filter.current?.focus();
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !container.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);

  const choices = [
    ...(agent ? [{ id: "", label: catalog?.default_model
      ? t(`沿用默认 · ${catalog.default_model}`, `Default · ${catalog.default_model}`)
      : t("沿用 Agent 默认模型", "Use agent default"), source: "default" }] : []),
    ...(catalog?.models || []),
  ].filter(choice => `${choice.id} ${choice.label}`.toLowerCase().includes(search.toLowerCase()));
  const shown = choices.slice(0, 100);
  const choose = (model: string) => { onChange(model); setManual(false); setOpen(false); trigger.current?.focus(); };
  const label = agent ? t("摘要模型", "Summary model") : t("模型名称", "Model name");
  const selected = catalog?.models.find(choice => choice.id === value);
  return <div className="model-picker" ref={container}
    onBlur={event => { if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <div className="model-picker-label"><label id={`${id}-label`} htmlFor={manual || !agent ? `${id}-input` : `${id}-trigger`}>{label}</label>
      <button type="button" className="text-button" disabled={disabled || busy} onClick={load}>
        {busy ? <LoaderCircle size={14} className="spin"/> : <RefreshCw size={14}/>}
        {busy ? t("读取模型…", "Loading models…") : t("刷新模型", "Refresh models")}
      </button>
    </div>
    <div className="model-picker-anchor">
    <div className={`model-picker-control ${!agent ? "is-editable" : ""}`}>
    {!agent && <input id={`${id}-input`} name={name} value={value} aria-label={t("自定义模型名称", "Custom model name")}
      disabled={disabled} spellCheck={false} autoComplete="off" placeholder={t("输入模型名称，或从右侧目录选择", "Enter a model name or browse the catalog")}
      onChange={event => onChange(event.target.value)}/>}
    <motion.button ref={trigger} id={`${id}-trigger`} type="button" className="model-picker-trigger" disabled={disabled}
      whileTap={reduced || disabled ? undefined : { scale: 0.985 }} transition={{ duration: 0.12 }}
      aria-haspopup="listbox" aria-expanded={open} aria-controls={`${id}-list`} aria-labelledby={`${id}-label ${id}-value`}
      onClick={() => { setSearch(""); setActive(0); setOpen(!open); if (!catalog && !busy && !agent) void load(); }}>
      <motion.span key={value} id={`${id}-value`} className={!agent ? "sr-only" : undefined}
        initial={reduced ? false : { opacity: 0.65, y: 3 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduced ? 0 : 0.18 }}>{agent && value ? selected?.label || value : agent
        ? catalog?.default_model ? t(`默认 · ${catalog.default_model}`, `Default · ${catalog.default_model}`) : t("沿用 Agent 默认模型", "Use agent default")
        : t("从服务中选择模型", "Choose from service models")}</motion.span><motion.span aria-hidden="true" style={{ display: "flex" }}
          animate={{ rotate: open ? 180 : 0 }} transition={{ duration: reduced ? 0 : 0.2 }}><ChevronDown size={16}/></motion.span>
    </motion.button>
    </div>
    <AnimatePresence>
    {open && <OverlayMotion key="model-menu" className="model-picker-menu" onKeyDown={event => {
      if (event.nativeEvent.isComposing) return;
      if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); setOpen(false); trigger.current?.focus(); }
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault(); setActive(index => Math.max(0, Math.min(shown.length - 1, index + (event.key === "ArrowDown" ? 1 : -1))));
      }
      if (event.key === "Enter" && event.target === filter.current && shown[active]) { event.preventDefault(); choose(shown[active].id); }
    }}>
      <div className="model-picker-search"><Search size={16}/><input ref={filter} type="search" value={search}
        role="combobox" aria-expanded="true" aria-controls={`${id}-list`} aria-autocomplete="list"
        aria-activedescendant={shown[active] ? `${id}-option-${active}` : undefined}
        aria-label={t("搜索模型", "Search models")} placeholder={t("搜索模型名称…", "Search model names…")}
        onChange={event => { setSearch(event.target.value); setActive(0); }}/></div>
      <div ref={list} id={`${id}-list`} role="listbox" aria-label={label} className="model-picker-list">
        {shown.map((choice, index) => <motion.button key={choice.id} type="button" role="option" tabIndex={-1} id={`${id}-option-${index}`}
          whileTap={reduced ? undefined : { scale: 0.98 }}
          animate={{ backgroundColor: value === choice.id ? "var(--selected)" : active === index ? "var(--inset)" : "rgba(0, 0, 0, 0)" }}
          transition={{ duration: reduced ? 0 : 0.18 }}
          aria-selected={value === choice.id} className={active === index ? "is-active" : ""}
          ref={element => { if (index === active && element && list.current) {
            const bounds = element.getBoundingClientRect();
            const viewport = list.current.getBoundingClientRect();
            if (bounds.top < viewport.top) list.current.scrollTop -= viewport.top - bounds.top;
            else if (bounds.bottom > viewport.bottom) list.current.scrollTop += bounds.bottom - viewport.bottom;
          } }}
          onMouseDown={event => event.preventDefault()} onMouseEnter={() => setActive(index)} onClick={() => choose(choice.id)}>
          <strong>{choice.label}</strong>{choice.label !== choice.id && choice.id && <small>{choice.id}</small>}
        </motion.button>)}
      </div>
      {!shown.length && <p className="hint">{busy ? t("正在读取模型目录…", "Reading the model catalog…") : t("没有匹配模型，可手动输入完整名称。", "No matching model. Enter its full name below.")}</p>}
      {choices.length > shown.length && <p className="hint">{t(`共 ${choices.length} 个匹配，输入名称缩小范围。`, `${choices.length} matches. Type to narrow the list.`)}</p>}
      <button className="text-button model-manual" type="button" onClick={() => { setManual(true); setOpen(false); requestAnimationFrame(() => document.getElementById(`${id}-input`)?.focus()); }}>{t("手动输入模型名称", "Enter a model name")}</button>
    </OverlayMotion>}
    </AnimatePresence>
    </div>
    {manual && agent && <input id={`${id}-input`} name={name} value={value} aria-label={t("自定义模型名称", "Custom model name")}
      disabled={disabled} spellCheck={false} autoComplete="off" placeholder={agent === "opencode" ? "provider/model" : t("输入完整模型名称", "Enter the full model name")}
      onChange={event => onChange(event.target.value)}/>}
    {agent && !manual && <button className="text-button model-manual" type="button" disabled={disabled} onClick={() => setManual(true)}>{t("手动输入", "Enter manually")}</button>}
    {error && <p className="error" role="alert">{error}</p>}
    {!error && catalog?.warning && <p className="hint" role="status">{catalog.warning === "cached_catalog"
      ? t("正在使用本机缓存的模型目录；可刷新或手动输入。", "Using the local model cache. Refresh or enter a name manually.")
      : catalog.warning === "configured_catalog" ? t("已列出配置中的模型；也可手动输入其他模型。", "Showing configured models. Other models can be entered manually.")
      : t("暂未读到模型目录，可沿用默认或手动输入后测试。", "No model catalog returned. Use the default or enter a name and test it.")}</p>}
    {catalog && !catalog.warning && <p className="hint model-catalog-note">{agent === "claude"
      ? t("模型别名与本机配置；实际访问权限以连接测试为准。", "Model aliases and local settings. Test to verify access.")
      : t(`已发现 ${catalog.models.length} 个模型，选择后测试连接。`, `${catalog.models.length} models found. Test your selection to verify access.`)}</p>}
  </div>;
}
