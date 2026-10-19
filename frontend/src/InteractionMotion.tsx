import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";
import { motion } from "motion/react";
import { useReducedMotion } from "./useReducedMotion";

export function SelectionPill({ active, group }: { active: boolean; group: string }) {
  const reduced = useReducedMotion();
  return active ? <motion.i aria-hidden="true" className="selection-pill"
    layoutId={group} transition={reduced ? { duration: 0 } : { type: "spring", stiffness: 430, damping: 35 }} /> : null;
}

/** Content changes animate in their existing container; state and focus never wait. */
export function useContentMotion<T extends HTMLElement>(ref: RefObject<T | null>, value: string,
  selector?: string, axis: "x" | "y" = "y") {
  const previous = useRef(value);
  const animation = useRef<Animation | null>(null);
  const reduced = useReducedMotion();
  useLayoutEffect(() => {
    animation.current?.cancel();
    const changed = previous.current !== value;
    previous.current = value;
    if (!changed || reduced) return;
    const element = selector ? ref.current?.querySelector<HTMLElement>(selector) : ref.current;
    if (!element) return;
    animation.current = element.animate([
      { opacity: 0.45, transform: `translate${axis}(12px)` },
      { opacity: 1, transform: `translate${axis}(0)` },
    ], { duration: 280, easing: "cubic-bezier(.16,1,.3,1)" });
    return () => animation.current?.cancel();
  }, [ref, value, selector, axis, reduced]);
}

type Ink = { id: number; left: number; top: number; width: number; height: number;
  radius: string; color: string; x: number; y: number; diameter: number };

/** The ink is a noninteractive paint layer, leaving every real hit target stable. */
export function InteractionFeedback() {
  const reduced = useReducedMotion();
  const [inks, setInks] = useState<Ink[]>([]);
  const nextId = useRef(0);
  useEffect(() => {
    if (reduced) { setInks([]); return; }
    function paint(target: EventTarget | null, point?: { x: number; y: number }) {
      if (!(target instanceof Element)) return;
      const control = target.closest<HTMLElement>("button, summary, .result-title");
      if (!control || control.closest('[inert], [aria-hidden="true"]') ||
        control.matches(':disabled, [aria-disabled="true"], [data-no-ink]')) return;
      const rect = control.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const style = getComputedStyle(control);
      const ink: Ink = { id: nextId.current++, left: rect.left, top: rect.top,
        width: rect.width, height: rect.height, radius: style.borderRadius, color: style.color,
        x: point ? point.x - rect.left : rect.width / 2,
        y: point ? point.y - rect.top : rect.height / 2,
        diameter: Math.hypot(rect.width, rect.height) * 2 };
      setInks(old => [...old.slice(-5), ink]);
    }
    const pointer = (event: PointerEvent) => { if (event.button === 0) paint(event.target, { x: event.clientX, y: event.clientY }); };
    const keyboard = (event: KeyboardEvent) => { if (!event.repeat && (event.key === "Enter" || event.key === " ")) paint(event.target); };
    document.addEventListener("pointerdown", pointer, true);
    document.addEventListener("keydown", keyboard, true);
    return () => { document.removeEventListener("pointerdown", pointer, true); document.removeEventListener("keydown", keyboard, true); };
  }, [reduced]);
  return createPortal(<div className="interaction-paint" aria-hidden="true">
    {inks.map(ink => <span className="interaction-clip" key={ink.id} style={{ left: ink.left, top: ink.top,
      width: ink.width, height: ink.height, borderRadius: ink.radius, color: ink.color }}>
      <span className="interaction-ink" onAnimationEnd={() => setInks(old => old.filter(item => item.id !== ink.id))}
        style={{ width: ink.diameter, height: ink.diameter, left: ink.x - ink.diameter / 2, top: ink.y - ink.diameter / 2 }} />
    </span>)}
  </div>, document.body);
}
