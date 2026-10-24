import { CapsuleButton } from "./ui/controls";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Cloud, MessageCircle, Monitor, Puzzle } from "lucide-react";
import { type Setup } from "./api";
import { Models, ExtensionSettings, UpdateSettings } from "./Settings";
import { SyncSettings } from "./SyncSettings";
import { useText } from "./locale";
import { SelectionPill, useContentMotion } from "./InteractionMotion";

export function SettingsWorkspace({ setup, refresh, onChanged, onBack, onSummarize }: {
  setup: Setup | null; refresh: () => Promise<void>;
  onChanged: (deleted?: number[]) => Promise<void>; onBack: () => void;
  onSummarize: () => void;
}) {
  const t = useText();
  const routeSection = () => {
    const section = location.hash.split("/")[1];
    return ["models", "sync", "extension", "desktop"].includes(section) ? section : "models";
  };
  const [active, setActive] = useState(routeSection);
  const switchSection = (id: string) => {
    setActive(id);
    if (location.hash.startsWith("#settings"))
      history.replaceState(null, "", location.pathname + location.search + "#settings/" + id);
  };
  useEffect(() => {
    const route = () => { if (location.hash.startsWith("#settings/")) setActive(routeSection()); };
    window.addEventListener("hashchange", route);
    return () => window.removeEventListener("hashchange", route);
  }, []);
  const root = useRef<HTMLDivElement>(null);
  useContentMotion(root, active, ".settings-panel:not([hidden])", "x");
  const sections = [
    { id: "models", label: t("AI 连接", "AI connections"), compact: t("AI 连接", "AI"), Icon: MessageCircle },
    { id: "sync", label: t("设备同步", "Device sync"), compact: t("同步", "Sync"), Icon: Cloud },
    { id: "extension", label: t("浏览器扩展", "Browser extension"), compact: t("扩展", "Extension"), Icon: Puzzle },
    { id: "desktop", label: t("桌面与更新", "Desktop & updates"), compact: t("桌面", "Desktop"), Icon: Monitor },
  ];
  return <div className="settings-workspace" ref={root}>
    <header className="page-heading settings-heading">
      <h1>{t("设置", "Settings")}</h1>
      <CapsuleButton className="text-button support-back" onClick={onBack}><ArrowLeft size={16}/>{t("返回收藏", "Back to collection")}</CapsuleButton>
      <p>{t("按需连接服务，关键词搜索无需配置。", "Connect services as needed. Keyword search works without setup.")}</p>
    </header>
    <div className="settings-tabs" role="tablist" aria-label={t("设置分类", "Settings categories")}>
      {sections.map(({ id, label, compact, Icon }, index) => <CapsuleButton key={id} type="button" role="tab" aria-label={label}
        id={`settings-tab-${id}`} aria-controls={`settings-panel-${id}`} aria-selected={active === id}
        tabIndex={active === id ? 0 : -1} onClick={() => switchSection(id)}
        onKeyDown={event => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
          event.preventDefault();
          const next = event.key === "Home" ? 0 : event.key === "End" ? sections.length - 1 :
            (index + (event.key === "ArrowRight" ? 1 : -1) + sections.length) % sections.length;
          switchSection(sections[next].id);
          document.getElementById(`settings-tab-${sections[next].id}`)?.focus();
        }}><SelectionPill active={active === id} group="settings-section" /><Icon size={17}/><span className="settings-label-long" aria-hidden="true">{label}</span><span className="settings-label-compact" aria-hidden="true">{compact}</span></CapsuleButton>)}
    </div>
    {/* Keep forms mounted so switching categories preserves unsaved drafts and test results. */}
    {sections.map(({ id }) => <div key={id} role="tabpanel" id={`settings-panel-${id}`}
      aria-labelledby={`settings-tab-${id}`} hidden={active !== id} tabIndex={0} className="settings-panel">
      {id === "models" ? <Models setup={setup} refresh={refresh} showHeading={false} onSummarize={onSummarize}/> :
        id === "sync" ? <SyncSettings onChanged={onChanged}/> :
        id === "extension" ? <ExtensionSettings/> : <>
          <UpdateSettings/>
          <p className="credits">{t("界面组件致谢：", "Interface credits: ")}<a href="https://heroui.com" target="_blank" rel="noreferrer">HeroUI</a> · <a href="https://rareui.com" target="_blank" rel="noreferrer">Rare UI</a></p>
        </>}
    </div>)}
  </div>;
}
