import { useContext, useId, useState } from "react";
import { ChevronDown, RotateCcw, Save, Sparkles } from "lucide-react";
import { Locale, useText, type Language } from "./locale";
import { CapsuleButton } from "./ui/controls";
import "./summary-preferences.css";

export function SummaryPreferences({ preference, prompt, defaults, disabled, languageLocked, promptLocked,
  dirty, onChange, onSave }: {
  preference: string; prompt: string; defaults: Partial<Record<Language, string>>;
  disabled: boolean; languageLocked: boolean; promptLocked: boolean; dirty: boolean;
  onChange: (key: "summary_language" | "summary_prompt", value: string) => void;
  onSave: () => void;
}) {
  const language = useContext(Locale), t = useText(), id = useId();
  const target = preference === "en" ? "en" : preference === "zh" ? "zh" : language;
  const builtIn = defaults[target] || "";
  const custom = Boolean(prompt.trim());
  const [editing, setEditing] = useState(false), [text, setText] = useState("");
  return <section className="summary-preferences" aria-labelledby={id}>
    <div className="summary-preferences-heading">
      <div>
        <h3 id={id}><Sparkles size={18}/>{t("标题与摘要", "Titles and summaries")}</h3>
        <p>{t("每次生成一起更新标题、摘要和要点，原文保留采集时的语言。",
          "Generate a title, summary and key points together. Saved source text keeps its original language.")}</p>
      </div>
      <label className="field">{t("目标语言", "Target language")}
        <select name="summary_language" aria-label={t("摘要目标语言", "Summary target language")}
          value={preference || "auto"} disabled={disabled || languageLocked}
          onChange={event => onChange("summary_language", event.target.value)}>
          <option value="auto">{t("跟随界面 · 中文", "Follow interface · English")}</option>
          <option value="zh">简体中文</option>
          <option value="en">English</option>
        </select>
      </label>
    </div>
    <details className="summary-prompt-editor">
      <summary>{t("摘要提示词", "Summary prompt")}
        <span>{custom ? t("自定义", "Custom") : t("内置默认", "Built-in default")}</span>
        <ChevronDown size={15} aria-hidden="true"/>
      </summary>
      <div className="summary-prompt-content">
        <label htmlFor={id + "-prompt"}>{t("生成要求", "Writing instructions")}</label>
        <textarea id={id + "-prompt"} name="summary_prompt" aria-label={t("摘要提示词", "Summary prompt")}
          value={editing ? text : custom ? prompt : builtIn} rows={7} maxLength={10000}
          disabled={disabled || promptLocked || !builtIn} spellCheck={false}
          onFocus={() => { setText(custom ? prompt : builtIn); setEditing(true); }}
          onBlur={() => setEditing(false)}
          onChange={event => { setText(event.target.value); onChange("summary_prompt", event.target.value); }}/>
        <div className="summary-prompt-actions">
          <p>{t("可修改长度、重点和写作风格。标题、摘要和要点始终遵循目标语言。",
            "Customize length, focus and style. Titles, summaries and key points follow the target language.")}</p>
          <CapsuleButton type="button" className="text-button" disabled={disabled || promptLocked || !custom}
            onClick={() => { setEditing(false); onChange("summary_prompt", ""); }}><RotateCcw size={14}/>{t("恢复默认", "Restore default")}</CapsuleButton>
        </div>
      </div>
    </details>
    <div className="summary-preferences-footer">
      <span>{dirty ? t("尚未保存", "Unsaved changes") : t("已保存的设置用于下一次生成", "Saved settings apply to the next generation")}</span>
      <CapsuleButton type="button" className="secondary" disabled={disabled || !dirty} onClick={onSave}>
        <Save size={15}/>{t("保存摘要设置", "Save summary settings")}
      </CapsuleButton>
    </div>
  </section>;
}
