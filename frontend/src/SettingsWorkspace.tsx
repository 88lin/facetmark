import { useState } from "react";
import { ArrowLeft, Cloud, MessageCircle, Monitor, Puzzle } from "lucide-react";
import { type Setup } from "./api";
import { Models, ExtensionSettings, UpdateSettings } from "./Settings";
import { SyncSettings } from "./SyncSettings";
import { useText } from "./locale";

export function SettingsWorkspace({ setup, refresh, onChanged, onBack }: {
  setup: Setup | null; refresh: () => Promise<void>;
  onChanged: (deleted?: number[]) => Promise<void>; onBack: () => void;
}) {
  const t = useText();
  const [active, setActive] = useState("models");
  const sections = [
    { id: "models", label: t("AI 连接", "AI connections"), Icon: MessageCircle },
    { id: "sync", label: t("设备同步", "Device sync"), Icon: Cloud },
    { id: "extension", label: t("浏览器扩展", "Browser extension"), Icon: Puzzle },
    { id: "desktop", label: t("桌面与更新", "Desktop & updates"), Icon: Monitor },
  ];
  return <div className="settings-workspace">
    <header className="page-heading">
      <div><h1>{t("设置", "Settings")}</h1><p>{t("按需连接服务，关键词搜索无需配置。", "Connect services as needed. Keyword search works without setup.")}</p></div>
      <button className="text-button support-back" onClick={onBack}><ArrowLeft size={16}/>{t("返回收藏", "Back to collection")}</button>
    </header>
    <div className="settings-tabs" role="tablist" aria-label={t("设置分类", "Settings categories")}>
      {sections.map(({ id, label, Icon }, index) => <button key={id} type="button" role="tab"
        id={`settings-tab-${id}`} aria-controls={`settings-panel-${id}`} aria-selected={active === id}
        tabIndex={active === id ? 0 : -1} onClick={() => setActive(id)}
        onKeyDown={event => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
          event.preventDefault();
          const next = event.key === "Home" ? 0 : event.key === "End" ? sections.length - 1 :
            (index + (event.key === "ArrowRight" ? 1 : -1) + sections.length) % sections.length;
          setActive(sections[next].id);
          document.getElementById(`settings-tab-${sections[next].id}`)?.focus();
        }}><Icon size={17}/><span>{label}</span></button>)}
    </div>
    {/* Keep forms mounted so switching categories preserves unsaved drafts and test results. */}
    {sections.map(({ id }) => <div key={id} role="tabpanel" id={`settings-panel-${id}`}
      aria-labelledby={`settings-tab-${id}`} hidden={active !== id} tabIndex={0} className="settings-panel">
      {id === "models" ? <Models setup={setup} refresh={refresh} showHeading={false}/> :
        id === "sync" ? <SyncSettings onChanged={onChanged}/> :
        id === "extension" ? <ExtensionSettings/> : <>
          <UpdateSettings/>
          <p className="credits">{t("界面组件致谢：", "Interface credits: ")}<a href="https://rareui.com" target="_blank" rel="noreferrer">Rare UI</a></p>
        </>}
    </div>)}
  </div>;
}
