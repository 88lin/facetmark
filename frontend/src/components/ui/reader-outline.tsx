/**
 * Adapted from Rare UI RailToc (https://rareui.com).
 * Source: https://github.com/swamimalode07/rare-ui/blob/b4de46efe4eb2613e22bb8134b482ed4e0c7736a/public/r/rail-toc.json
 * Copyright (c) 2026 Swami Malode.
 * MIT + Commons Clause + Attribution; full notice: /THIRD_PARTY_NOTICES.md.
 * Facetmark adaptation: real article headings, container-local scrolling,
 * and a quiet current-section rail in place of the animated paper plane.
 */
import { useEffect, useRef, useState, type RefObject } from "react";
import { useReducedMotion } from "motion/react";
import { useText } from "../../locale";
import "./reader-outline.css";

export type ReaderOutlineSection = { id: string; label: string };

const ANCHOR_OFFSET = 28;
const HEADING_SELECTOR = "h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]";

export function ReaderOutline({
  containerRef,
  sections,
  contentKey,
}: {
  containerRef: RefObject<HTMLDivElement | null>;
  sections: ReaderOutlineSection[];
  contentKey: string;
}) {
  const t = useText();
  const reduceMotion = useReducedMotion();
  const navRef = useRef<HTMLElement>(null);
  const headingsRef = useRef(new Map<string, HTMLElement>());
  const pinned = useRef<string | null>(null);
  const userScrolled = useRef(false);
  const [activeId, setActiveId] = useState("");

  useEffect(() => {
    const scroller = containerRef.current;
    const nav = navRef.current;
    if (!scroller || !nav) return;

    const available = new Map(
      Array.from(
        scroller.querySelectorAll<HTMLElement>(HEADING_SELECTOR),
        (heading) => [heading.id, heading] as const,
      ),
    );
    const headings = sections.flatMap(({ id }) => {
      const element = available.get(id);
      return element ? [{ id, element }] : [];
    });
    headingsRef.current = available;
    pinned.current = null;
    userScrolled.current = false;
    let frame: number | null = null;
    let disposed = false;

    const sync = () => {
      frame = null;
      if (disposed) return;
      if (pinned.current !== null) {
        setActiveId(pinned.current);
        return;
      }

      const scrollTop = Math.max(0, scroller.scrollTop);
      const viewHeight = scroller.clientHeight;
      const extent = Math.max(0, scroller.scrollHeight - viewHeight);
      const remaining = Math.max(0, extent - scrollTop);
      const line = Math.min(ANCHOR_OFFSET, scrollTop);
      // RailToc's end-of-article anchor makes short final sections reachable.
      // Scale its sweep from zero so a short article still starts at its first heading.
      const sweep = extent > 0 ? Math.min(1, scrollTop / extent) : 0;
      const anchor = line + Math.max(0, viewHeight - line - remaining) * sweep;
      const origin = scroller.getBoundingClientRect().top + scroller.clientTop;
      let current = headings[0]?.id ?? "";
      for (const heading of headings) {
        if (heading.element.getBoundingClientRect().top - origin <= anchor + 1) {
          current = heading.id;
        }
      }
      setActiveId(current);
    };

    const schedule = () => {
      if (!disposed && frame === null) frame = requestAnimationFrame(sync);
    };
    const measure = () => {
      nav.style.setProperty(
        "--reader-outline-available-height",
        `${Math.max(0, scroller.clientHeight - ANCHOR_OFFSET * 2)}px`,
      );
      schedule();
    };
    const onIntent = (event: Event) => {
      // Scrolling the outline itself must not move the article's current marker.
      // Keyboard paging can reach the article while an outline button has focus.
      if (event.type !== "keydown" && event.target instanceof Node && nav.contains(event.target))
        return;
      userScrolled.current = true;
    };
    const onScroll = () => {
      if (userScrolled.current) pinned.current = null;
      schedule();
    };

    const document = scroller.ownerDocument;
    scroller.addEventListener("scroll", onScroll, { passive: true });
    scroller.addEventListener("wheel", onIntent, { passive: true });
    scroller.addEventListener("touchstart", onIntent, { passive: true });
    // Reader toolbar controls live outside the scroller. Their pointer/keyboard
    // activation also releases a clicked heading when they scroll the article.
    document.addEventListener("pointerdown", onIntent);
    document.addEventListener("keydown", onIntent);
    window.addEventListener("resize", measure);
    const observer = new ResizeObserver(measure);
    observer.observe(scroller);
    if (scroller.firstElementChild) observer.observe(scroller.firstElementChild);
    const article = headings[0]?.element.closest("article");
    if (article && article !== scroller.firstElementChild) observer.observe(article);
    document.fonts?.ready
      .then(() => {
        if (!disposed) measure();
      })
      .catch(() => {});
    measure();

    return () => {
      disposed = true;
      if (frame !== null) cancelAnimationFrame(frame);
      observer.disconnect();
      scroller.removeEventListener("scroll", onScroll);
      scroller.removeEventListener("wheel", onIntent);
      scroller.removeEventListener("touchstart", onIntent);
      document.removeEventListener("pointerdown", onIntent);
      document.removeEventListener("keydown", onIntent);
      window.removeEventListener("resize", measure);
      headingsRef.current = new Map();
    };
  }, [containerRef, sections, contentKey]);

  useEffect(() => {
    const nav = navRef.current;
    const current = nav?.querySelector<HTMLElement>('[aria-current="location"]');
    if (!nav || !current || !nav.clientHeight) return;
    const navBounds = nav.getBoundingClientRect();
    const rowBounds = current.getBoundingClientRect();
    const above = rowBounds.top - navBounds.top - 4;
    const below = rowBounds.bottom - navBounds.bottom + 4;
    if (above < 0) nav.scrollTop += above;
    else if (below > 0) nav.scrollTop += below;
  }, [activeId]);

  const select = (id: string) => {
    const scroller = containerRef.current;
    const heading = headingsRef.current.get(id);
    if (!scroller || !heading || !scroller.contains(heading)) return;
    pinned.current = id;
    userScrolled.current = false;
    setActiveId(id);
    const top =
      heading.getBoundingClientRect().top -
      scroller.getBoundingClientRect().top -
      scroller.clientTop +
      scroller.scrollTop -
      ANCHOR_OFFSET;
    scroller.scrollTo({
      top: Math.max(0, Math.min(top, scroller.scrollHeight - scroller.clientHeight)),
      behavior: reduceMotion ? "auto" : "smooth",
    });
  };

  return (
    <nav ref={navRef} className="reader-outline" aria-label={t("文章目录", "Table of contents")}>
      <p className="reader-outline-title">{t("文章目录", "Table of contents")}</p>
      <ul className="reader-outline-list" role="list">
        {sections.map((section) => (
          <li className="reader-outline-item" key={section.id}>
            <button
              type="button"
              className="reader-outline-link"
              aria-controls={section.id}
              aria-current={section.id === activeId ? "location" : undefined}
              onClick={() => select(section.id)}
            >
              {section.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
