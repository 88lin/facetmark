import { CapsuleButton } from "./ui/controls";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Cloud, Link2, MessageCircle, Monitor, Puzzle } from "lucide-react";
import { type Setup } from "./api";
import { Models, ExtensionSettings, UpdateSettings } from "./Settings";
import { SyncSettings } from "./SyncSettings";
import { McpSettings } from "./McpSettings";
import { useText } from "./locale";
import { SelectionPill, useContentMotion } from "./InteractionMotion";
import type { SettingsSection } from "./navigation";

export function SettingsWorkspace({ active, section, onSection, setup, refresh, onChanged, onBack, onSummarize }: {
  active: boolean; section: SettingsSection; onSection: (section: SettingsSection) => void;
  setup: Setup | null; refresh: () => Promise<void>;
  onChanged: (deleted?: number[]) => Promise<void>; onBack: () => void;
  onSummarize: () => void;
}) {
  const t = useText();
  const [visited, setVisited] = useState<ReadonlySet<SettingsSection>>(() => new Set([section]));
  useEffect(() => {
    if (active) setVisited(current => current.has(section) ? current : new Set([...current, section]));
  }, [active, section]);
  const root = useRef<HTMLDivElement>(null);
  useContentMotion(root, section, ".settings-panel:not([hidden])", "x");
  const sections = [
    { id: "models", label: t("AI 连接", "AI connections"), compact: t("AI 连接", "AI"), Icon: MessageCircle },
    { id: "sync", label: t("设备同步", "Device sync"), compact: t("同步", "Sync"), Icon: Cloud },
    { id: "extension", label: t("浏览器扩展", "Browser extension"), compact: t("扩展", "Add-on"), Icon: Puzzle },
    { id: "mcp", label: t("MCP 与接入", "MCP & integrations"), compact: "MCP", Icon: Link2 },
    { id: "desktop", label: t("桌面与更新", "Desktop & updates"), compact: t("桌面", "Desktop"), Icon: Monitor },
  ] as const;
  return <div className="settings-workspace" ref={root}>
    <header className="page-heading settings-heading">
      <h1>{t("设置", "Settings")}</h1>
      <CapsuleButton className="text-button support-back" onClick={onBack}><ArrowLeft size={16}/>{t("返回收藏", "Back to collection")}</CapsuleButton>
      <p>{t("按需连接服务，关键词搜索无需配置。", "Connect services as needed. Keyword search works without setup.")}</p>
    </header>
    <div className="settings-tabs mcp-settings-tabs" role="tablist" aria-label={t("设置分类", "Settings categories")}>
      {sections.map(({ id, label, compact, Icon }, index) => <CapsuleButton key={id} type="button" role="tab" aria-label={label}
        id={`settings-tab-${id}`} aria-controls={`settings-panel-${id}`} aria-selected={section === id}
        tabIndex={section === id ? 0 : -1} onClick={() => onSection(id)}
        onKeyDown={event => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
          event.preventDefault();
          const next = event.key === "Home" ? 0 : event.key === "End" ? sections.length - 1 :
            (index + (event.key === "ArrowRight" ? 1 : -1) + sections.length) % sections.length;
          onSection(sections[next].id);
          const target = document.getElementById(`settings-tab-${sections[next].id}`);
          target?.focus();
          target?.scrollIntoView({ block: "nearest", inline: "nearest" });
        }}><SelectionPill active={section === id} group="settings-section" /><Icon size={17}/><span className="settings-label-long" aria-hidden="true">{label}</span><span className="settings-label-compact" aria-hidden="true">{compact}</span></CapsuleButton>)}
    </div>
    {/* Mount a category when first visited, then keep its drafts and results.
        Hidden integration panels suspend their polling. */}
    {sections.map(({ id }) => <div key={id} role="tabpanel" id={`settings-panel-${id}`}
      aria-labelledby={`settings-tab-${id}`} hidden={!active || section !== id} tabIndex={0} className="settings-panel">
      {(visited.has(id) || active && section === id) && (id === "models" ? <Models active={active && section === id} setup={setup} refresh={refresh} showHeading={false} onSummarize={onSummarize}/> :
        id === "sync" ? <SyncSettings active={active && section === id} onChanged={onChanged}/> :
        id === "extension" ? <ExtensionSettings active={active && section === id}/> : id === "mcp" ? <McpSettings active={active && section === id}/> : <>
          <UpdateSettings/>
          <p className="credits">{t("界面组件致谢：", "Interface credits: ")}<a href="https://heroui.com" target="_blank" rel="noreferrer">HeroUI</a> · <a href="https://rareui.com" target="_blank" rel="noreferrer">Rare UI</a></p>
        </>)}
    </div>)}
  </div>;
}
