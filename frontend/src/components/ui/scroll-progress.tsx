/**
 * Adapted from Rare UI ScrollProgress (https://rareui.com).
 * Copyright (c) 2026 Swami Malode.
 * MIT + Commons Clause + Attribution; full notice: /THIRD_PARTY_NOTICES.md.
 * Facetmark adaptation: floating glass capsule, actual scroll progress and an
 * animated chapter label over a keyboard-accessible native section picker.
 */
import { useEffect, useRef, useState, type RefObject } from "react";
import { motion, useScroll, useSpring } from "motion/react";
import { List, ArrowUp } from "lucide-react";
import { useText } from "../../locale";
import { useReducedMotion } from "../../useReducedMotion";

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
  const pinned = useRef<string | null>(null);
  const sectionLabel = sections.find(({ id }) => id === activeId)?.label ?? sections[0]?.label;
  useEffect(() => {
    const scroller = containerRef.current;
    if (!scroller) return;
    pinned.current = null;
    const update = () => {
      const extent = scroller.scrollHeight - scroller.clientHeight;
      const ratio = extent > 0 ? Math.min(1, scroller.scrollTop / extent) : 1;
      scrollYProgress.set(ratio);
      setPercent(Math.round(ratio * 100));
      // A short final section cannot always reach the top anchor. Preserve an
      // explicit chapter choice through its smooth scroll until new user input.
      if (pinned.current !== null) { setActiveId(pinned.current); return; }
      const anchor = scroller.getBoundingClientRect().top + 100;
      const active = [...sections].reverse().find(({ id }) => {
        const top = document.getElementById(id)?.getBoundingClientRect().top;
        return top !== undefined && top <= anchor;
      });
      setActiveId(extent > 0 && scroller.scrollTop >= extent - 1
        ? sections.at(-1)?.id ?? "" : active?.id ?? sections[0]?.id ?? "");
    };
    const release = () => { pinned.current = null; };
    update();
    scroller.addEventListener("scroll", update, { passive: true });
    scroller.addEventListener("wheel", release, { passive: true });
    scroller.addEventListener("touchstart", release, { passive: true });
    document.addEventListener("keydown", release);
    document.addEventListener("pointerdown", release);
    const ro = new ResizeObserver(update);
    ro.observe(scroller);
    if (scroller.firstElementChild) ro.observe(scroller.firstElementChild);
    return () => {
      scroller.removeEventListener("scroll", update);
      scroller.removeEventListener("wheel", release);
      scroller.removeEventListener("touchstart", release);
      document.removeEventListener("keydown", release);
      document.removeEventListener("pointerdown", release);
      ro.disconnect();
    };
  }, [containerRef, sections, contentKey, scrollYProgress]);
  return (
    <footer className="reading-position">
      <motion.div
        className="reading-position-surface"
        initial={reduceMotion ? false : { opacity: 0.65, y: 10, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: reduceMotion ? 0 : 0.24, ease: [0.22, 1, 0.36, 1] }}
      >
        {showProgress && (
          <div className="reading-progress-track" aria-hidden="true">
            <motion.div style={{ scaleX: reduceMotion ? scrollYProgress : progress }} />
          </div>
        )}
        {showProgress && sections.length > 1 ? (
          <label className="section-picker">
            <List size={16} aria-hidden="true" />
            <span className="section-picker-copy" aria-hidden="true">
              <motion.span
                key={`${contentKey}-${activeId}`}
                initial={reduceMotion ? false : { opacity: 0.45, y: 5, filter: "blur(3px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: reduceMotion ? 0 : 0.18, ease: [0.22, 1, 0.36, 1] }}
              >
                {sectionLabel}
              </motion.span>
            </span>
            <select
              ref={picker}
              aria-label={t("跳转到章节", "Jump to section")}
              value={activeId}
              onChange={(e) => {
                const scroller = containerRef.current;
                const heading = scroller?.querySelector<HTMLElement>(`#${CSS.escape(e.target.value)}`);
                if (!scroller || !heading) return;
                pinned.current = e.target.value;
                setActiveId(e.target.value);
                scroller.scrollTo({
                  top: heading.getBoundingClientRect().top - scroller.getBoundingClientRect().top
                    - scroller.clientTop + scroller.scrollTop - 28,
                  behavior: reduceMotion ? "auto" : "smooth",
                });
              }}
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
          onClick={() => {
            pinned.current = null;
            containerRef.current?.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
          }}
        >
          <ArrowUp size={14} />
        </button>
      </motion.div>
    </footer>
  );
}
