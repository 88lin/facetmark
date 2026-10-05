/**
 * Adapted from Rare UI ScrollProgress (https://rareui.com).
 * Copyright (c) 2026 Swami Malode.
 * MIT + Commons Clause + Attribution; full notice: /THIRD_PARTY_NOTICES.md.
 * Facetmark adaptation: in-panel rail, actual scroll progress, native section
 * picker, no floating glass surface, blur, stagger, or synthetic progress.
 */
import { useEffect, useRef, useState, type RefObject } from "react";
import { motion, useReducedMotion, useScroll, useSpring } from "motion/react";
import { List, ArrowUp } from "lucide-react";
import { useText } from "../../locale";

export type ScrollProgressSection = { id: string; label: string };
export function ScrollProgress({
  containerRef,
  sections,
  contentKey,
  showProgress = true,
}: {
  containerRef: RefObject<HTMLDivElement | null>;
  sections: ScrollProgressSection[];
  contentKey: string;
  showProgress?: boolean;
}) {
  const t = useText();
  const reduceMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({ container: containerRef });
  const progress = useSpring(scrollYProgress, { stiffness: 180, damping: 35, mass: 0.25 });
  const [activeId, setActiveId] = useState("");
  const [percent, setPercent] = useState(0);
  const picker = useRef<HTMLSelectElement>(null);
  useEffect(() => {
    const scroller = containerRef.current;
    if (!scroller) return;
    const update = () => {
      const extent = scroller.scrollHeight - scroller.clientHeight;
      const ratio = extent > 0 ? Math.min(1, scroller.scrollTop / extent) : 1;
      scrollYProgress.set(ratio);
      setPercent(Math.round(ratio * 100));
      const anchor = scroller.getBoundingClientRect().top + 100;
      const active = [...sections].reverse().find(({ id }) => {
        const top = document.getElementById(id)?.getBoundingClientRect().top;
        return top !== undefined && top <= anchor;
      });
      setActiveId(active?.id ?? sections[0]?.id ?? "");
    };
    update();
    scroller.addEventListener("scroll", update, { passive: true });
    const ro = new ResizeObserver(update);
    ro.observe(scroller);
    if (scroller.firstElementChild) ro.observe(scroller.firstElementChild);
    return () => {
      scroller.removeEventListener("scroll", update);
      ro.disconnect();
    };
  }, [containerRef, sections, contentKey, scrollYProgress]);
  return (
    <footer className="reading-position">
      {showProgress && (
        <div className="reading-progress-track" aria-hidden="true">
          <motion.div style={{ scaleX: reduceMotion ? scrollYProgress : progress }} />
        </div>
      )}
      {showProgress && sections.length > 1 ? (
        <label className="section-picker">
          <List size={14} />
          <select
            ref={picker}
            aria-label={t("跳转到章节", "Jump to section")}
            value={activeId}
            onChange={(e) =>
              document.getElementById(e.target.value)?.scrollIntoView({
                behavior: reduceMotion ? "auto" : "smooth",
                block: "start",
              })
            }
          >
            {sections.map((section) => (
              <option key={section.id} value={section.id}>
                {section.label}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <span>
          {showProgress ? t("阅读位置", "Reading position") : t("阅读预览", "Reading preview")}
        </span>
      )}
      <span
        className="reading-percent"
        aria-label={showProgress ? t("滚动位置", "Scroll position") : undefined}
      >
        {showProgress ? `${percent}%` : ""}
      </span>
      <button
        className="icon-button"
        title={t("回到顶部", "Back to top")}
        aria-label={t("回到顶部", "Back to top")}
        onClick={() =>
          containerRef.current?.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" })
        }
      >
        <ArrowUp size={14} />
      </button>
    </footer>
  );
}
