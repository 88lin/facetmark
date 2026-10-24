import { useLayoutEffect, useRef, type RefObject } from "react";
import { useIsPresent } from "motion/react";
import { OverlayMotion } from "./overlay-motion";
import type { ComponentProps } from "react";

type AnchoredMenuProps = ComponentProps<typeof OverlayMotion> & {
  anchor: RefObject<HTMLElement | null>;
  onDismiss: () => void;
};

/** A native top-layer menu keeps form and focus ancestry while escaping scroll
 * clipping. Older engines fall back to an inline, scrollable picker. */
export function AnchoredMenu({ anchor, onDismiss, className, style, ...props }: AnchoredMenuProps) {
  const panel = useRef<HTMLDivElement>(null);
  const dismiss = useRef(onDismiss);
  dismiss.current = onDismiss;
  const present = useIsPresent();
  const isPresent = useRef(present);
  isPresent.current = present;

  useLayoutEffect(() => {
    const element = panel.current;
    const trigger = anchor.current;
    if (!element || !trigger) return;
    if (typeof element.showPopover !== "function") {
      element.removeAttribute("popover");
      element.dataset.floating = "false";
      return;
    }
    element.showPopover();
    let frame = 0;
    const position = () => {
      if (!isPresent.current) return;
      const box = trigger.getBoundingClientRect();
      const viewport = window.visualViewport;
      const left = viewport?.offsetLeft ?? 0, top = viewport?.offsetTop ?? 0;
      const width = viewport?.width ?? window.innerWidth, height = viewport?.height ?? window.innerHeight;
      if (!trigger.isConnected || trigger.closest("[hidden], [inert]") || !box.width ||
          box.bottom <= top || box.top >= top + height) {
        dismiss.current();
        return;
      }
      // An anchor can still be in the window but have scrolled out of its page.
      for (let parent = trigger.parentElement; parent; parent = parent.parentElement) {
        const overflow = getComputedStyle(parent).overflowY;
        if (!["auto", "scroll", "hidden", "clip"].includes(overflow)) continue;
        const bounds = parent.getBoundingClientRect();
        if (box.bottom <= bounds.top || box.top >= bounds.bottom) { dismiss.current(); return; }
      }
      const margin = 8, gap = 6;
      const menuWidth = Math.max(0, Math.min(Math.max(box.width, 280), width - margin * 2));
      element.style.width = `${menuWidth}px`;
      // Measure untransformed dimensions; entrance motion never changes placement.
      const below = top + height - margin - box.bottom - gap;
      const above = box.top - top - margin - gap;
      const placeAbove = below < Math.min(element.scrollHeight, 240) && above > below;
      const available = Math.max(0, Math.min(height - margin * 2, placeAbove ? above : below));
      element.style.maxHeight = `${available}px`;
      element.style.left = `${Math.max(left + margin, Math.min(box.left, left + width - margin - menuWidth))}px`;
      element.style.top = `${placeAbove ? Math.max(top + margin, box.top - gap - element.offsetHeight) : box.bottom + gap}px`;
      element.style.setProperty("--picker-origin", placeAbove ? "bottom center" : "top center");
    };
    const schedule = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(position); };
    position();
    const resize = new ResizeObserver(schedule);
    resize.observe(trigger); resize.observe(element);
    const mutation = new MutationObserver(schedule);
    for (let parent = trigger.parentElement; parent; parent = parent.parentElement)
      mutation.observe(parent, { attributes: true, attributeFilter: ["hidden", "inert"] });
    document.addEventListener("scroll", schedule, true);
    window.addEventListener("resize", schedule);
    window.visualViewport?.addEventListener("resize", schedule);
    window.visualViewport?.addEventListener("scroll", schedule);
    return () => {
      cancelAnimationFrame(frame); resize.disconnect(); mutation.disconnect();
      document.removeEventListener("scroll", schedule, true);
      window.removeEventListener("resize", schedule);
      window.visualViewport?.removeEventListener("resize", schedule);
      window.visualViewport?.removeEventListener("scroll", schedule);
      if (element.matches(":popover-open")) element.hidePopover();
    };
  }, [anchor]);

  return <OverlayMotion {...props} ref={panel} popover="manual"
    className={`fm-picker-popover ${className ?? ""}`}
    style={{ ...style, transformOrigin: "var(--picker-origin, top center)" }} />;
}
