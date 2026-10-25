/**
 * Adapted from Rare UI ScrollProgress (https://rareui.com).
 * Copyright (c) 2026 Swami Malode.
 * MIT + Commons Clause + Attribution; full notice: /THIRD_PARTY_NOTICES.md.
 * Facetmark adaptation: unobtrusive footer, actual scroll progress and an
 * animated chapter label over a keyboard-accessible native section picker.
 */
import { useEffect, useRef, useState, type RefObject } from "react";
import { motion, useScroll, useSpring } from "motion/react";
import { List, ArrowUp } from "lucide-react";
import { useText } from "../../locale";
import { CapsuleButton } from "../../ui/controls";
import { useReducedMotion } from "../../useReducedMotion";
import { SECTION_SELECTED, selectReaderSection, scrollToReaderSection } from "./reader-section";

export type ScrollProgressSection = { id: string; label: string };
export function ScrollProgress({
  containerRef,
  sections,
  contentKey,
}: {
  containerRef: RefObject<HTMLDivElement | null>;
  sections: ScrollProgressSection[];
  contentKey: string;
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
    const sectionElement = (id: string) => {
      const element = scroller.querySelector<HTMLElement>(`#${CSS.escape(id)}`);
      return element && (id === "reader-start" || element.closest(".body-text")) ? element : null;
    };
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
        const top = sectionElement(id)?.getBoundingClientRect().top;
        return top !== undefined && top <= anchor;
      });
      setActiveId(extent > 0 && scroller.scrollTop >= extent - 1
        ? sections.at(-1)?.id ?? "" : active?.id ?? sections[0]?.id ?? "");
    };
    const release = () => { pinned.current = null; };
    const onSectionSelected = (event: Event) => {
      const id = (event as CustomEvent<string>).detail;
      if (sections.some(section => section.id === id)) { pinned.current = id; setActiveId(id); }
    };
    const measure = () => {
      const heading = pinned.current && sectionElement(pinned.current);
      if (heading) scrollToReaderSection(scroller, heading, "instant");
      update();
    };
    update();
    scroller.addEventListener("scroll", update, { passive: true });
    scroller.addEventListener(SECTION_SELECTED, onSectionSelected);
    scroller.addEventListener("wheel", release, { passive: true });
    scroller.addEventListener("touchstart", release, { passive: true });
    document.addEventListener("keydown", release);
    document.addEventListener("pointerdown", release);
    const ro = new ResizeObserver(measure);
    ro.observe(scroller);
    if (scroller.firstElementChild) ro.observe(scroller.firstElementChild);
    return () => {
      scroller.removeEventListener("scroll", update);
      scroller.removeEventListener(SECTION_SELECTED, onSectionSelected);
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
        initial={reduceMotion ? false : { opacity: 0.65 }}
        animate={{ opacity: 1 }}
        transition={{ duration: reduceMotion ? 0 : 0.24, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="reading-progress-track" aria-hidden="true">
          <motion.div style={{ scaleX: reduceMotion ? scrollYProgress : progress }} />
        </div>
        {sections.length > 1 ? (
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
                if (!scroller || !heading || !sections.some(section => section.id === e.target.value)
                  || (e.target.value !== "reader-start" && !heading.closest(".body-text"))) return;
                selectReaderSection(scroller, e.target.value);
                scrollToReaderSection(scroller, heading, reduceMotion ? "instant" : "smooth");
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
          <span className="reading-position-label">
            {t("阅读位置", "Reading position")}
          </span>
        )}
        <span
          className="reading-percent"
          aria-label={t("滚动位置", "Scroll position")}
        >
          {`${percent}%`}
        </span>
        <CapsuleButton
          type="button" className="icon-button reading-top"
          title={t("回到顶部", "Back to top")}
          aria-label={t("回到顶部", "Back to top")}
          onClick={() => {
            const scroller = containerRef.current;
            if (!scroller) return;
            selectReaderSection(scroller, sections[0]?.id ?? "");
            scroller.scrollTo({ top: 0, behavior: reduceMotion ? "instant" : "smooth" });
          }}
        >
          <ArrowUp size={14} />
        </CapsuleButton>
      </motion.div>
    </footer>
  );
}
