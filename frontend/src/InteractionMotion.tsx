import { useEffect, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { motion } from "motion/react";
import { useReducedMotion } from "./useReducedMotion";
import "./interaction-motion.css";

gsap.registerPlugin(useGSAP);

export function SelectionPill({ active, group }: { active: boolean; group: string }) {
  const reduced = useReducedMotion();
  return active ? <motion.i aria-hidden="true" className="selection-pill"
    layoutId={group} transition={reduced ? { duration: 0 } : {
      type: "spring", stiffness: 480, damping: 29, mass: 0.8,
    }} /> : null;
}

type MotionPaint = { x: number; y: number; opacity: number; filter: string };
type ContentRecipe = {
  kind: "page" | "section" | "category" | "pagination" | "filter";
  axis: "x" | "y"; direction: number; distance: number; duration: number;
  opacity: number; blur: number;
};

function orderedDirection(previous: string, value: string, order: string[]) {
  const from = order.indexOf(previous);
  const to = order.indexOf(value);
  return from >= 0 && to >= 0 && to < from ? -1 : 1;
}

function contentRecipe(element: HTMLElement, previous: string, value: string, axis: "x" | "y"): ContentRecipe {
  if (element.matches(".page-scroll, .results-column")) return {
    kind: "page", axis, direction: orderedDirection(previous, value, ["library", "sessions", "tasks", "settings", "import", "setup"]),
    distance: 18, duration: 0.34, opacity: 0.76, blur: 0.7,
  };
  if (element.matches(".settings-panel")) return {
    kind: "section", axis, direction: orderedDirection(previous, value, ["models", "sync", "extension", "desktop"]),
    distance: 20, duration: 0.32, opacity: 0.66, blur: 1,
  };
  if (element.matches(".facet-options")) return {
    kind: "category", axis, direction: orderedDirection(previous, value, ["folders", "tags", "domains"]),
    distance: 18, duration: 0.28, opacity: 0.72, blur: 0.65,
  };
  // Offset is distinct from query/filter scope: pages travel, filters refocus.
  try {
    const before: unknown = JSON.parse(previous);
    const after: unknown = JSON.parse(value);
    if (Array.isArray(before) && Array.isArray(after) &&
      typeof before[1] === "number" && typeof after[1] === "number" && before[1] !== after[1] &&
      before.every((part, index) => index === 1 || part === after[index])) return {
      kind: "pagination", axis, direction: after[1] > before[1] ? 1 : -1,
      distance: 22, duration: 0.34, opacity: 0.72, blur: 0.7,
    };
  } catch { /* The first load and non-result contexts have no previous JSON. */ }
  return { kind: "filter", axis, direction: 1, distance: 8, duration: 0.25, opacity: 0.8, blur: 0.7 };
}

/** Existing containers change immediately. Only their painted arrival is sequenced. */
export function useContentMotion<T extends HTMLElement>(ref: RefObject<T | null>, value: string,
  selector?: string, axis: "x" | "y" = "y") {
  const previous = useRef(value);
  // Keep the last painted values through context cleanup, so a rapid reversal
  // resumes from the current position rather than jumping to a fresh entrance.
  const interrupted = useRef<Map<HTMLElement, MotionPaint> | null>(null);
  const reduced = useReducedMotion();
  useGSAP(() => {
    const before = previous.current;
    previous.current = value;
    const lastPaint = interrupted.current;
    interrupted.current = null;
    if (before === value || reduced) return;
    const element = selector ? ref.current?.querySelector<HTMLElement>(selector) : ref.current;
    if (!element) return;
    const recipe = contentRecipe(element, before, value, axis);
    const targets: HTMLElement[] = [element];
    const follow: HTMLElement[] = [];
    let heading: HTMLElement | null = null;
    if (recipe.kind === "page") {
      if (element.matches(".results-column")) {
        heading = ref.current?.querySelector<HTMLElement>(".workspace-toolbar") || null;
      } else {
        const settings = element.querySelector<HTMLElement>(":scope > .settings-workspace");
        if (settings) {
          // The settings hook owns the panel; this hook owns its inner body.
          const body = settings.querySelector<HTMLElement>(".settings-panel:not([hidden]) > :first-child");
          if (body) follow.push(body);
        } else {
          follow.push(...[...element.children].filter((child): child is HTMLElement =>
            child instanceof HTMLElement && !child.matches(".page-heading, [hidden], button"),
          ).slice(0, 2));
        }
      }
    }
    targets.push(...follow);
    if (heading) targets.push(heading);
    const paint = new Map<HTMLElement, MotionPaint>();
    interrupted.current = paint;
    element.dataset.contentMotion = recipe.kind;
    const timeline = gsap.timeline({
      defaults: { ease: "power3.out", overwrite: "auto" },
      onUpdate: () => {
        for (const target of targets) paint.set(target, {
          x: Number(gsap.getProperty(target, "x")), y: Number(gsap.getProperty(target, "y")),
          opacity: Number(gsap.getProperty(target, "opacity")), filter: String(gsap.getProperty(target, "filter")),
        });
      },
      onComplete: () => {
        if (interrupted.current === paint) interrupted.current = null;
        delete element.dataset.contentMotion;
        gsap.set(targets, { clearProps: "transform,opacity,filter,willChange" });
      },
    });
    const arrive = (target: HTMLElement, distance: number, duration: number, position: string,
      opacity = recipe.opacity, blur = recipe.blur) => {
      const start = lastPaint?.get(target) || {
        x: recipe.axis === "x" ? distance * recipe.direction : 0,
        y: recipe.axis === "y" ? distance * recipe.direction : 0,
        opacity, filter: `blur(${blur}px)`,
      };
      gsap.set(target, { willChange: "transform,opacity,filter" });
      timeline.fromTo(target, start, { x: 0, y: 0, opacity: 1, filter: "blur(0px)", duration }, position);
    };
    timeline.addLabel("heading", 0).addLabel("content", 0.04);
    arrive(element, heading ? 24 : recipe.distance, recipe.duration, heading ? "content" : "heading");
    if (heading) arrive(heading, 18, 0.28, "heading", 0.82, 0.5);
    follow.forEach(target => arrive(target, 6, 0.34, "content", 0.78, 0.5));
    return () => { delete element.dataset.contentMotion; };
  }, { scope: ref, dependencies: [value, selector, axis, reduced], revertOnUpdate: true });
}

type Ink = { id: number; target: HTMLElement; createdAt: number; left: number; top: number; width: number; height: number;
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
      const ink: Ink = { id: nextId.current++, target: control, createdAt: performance.now(), left: rect.left, top: rect.top,
        width: rect.width, height: rect.height, radius: style.borderRadius, color: style.color,
        x: point ? point.x - rect.left : rect.width / 2,
        y: point ? point.y - rect.top : rect.height / 2,
        diameter: Math.hypot(rect.width, rect.height) * 2 };
      setInks(old => [...old.slice(-5), ink]);
    }
    const pointer = (event: PointerEvent) => { if (event.button === 0) paint(event.target, { x: event.clientX, y: event.clientY }); };
    const keyboard = (event: KeyboardEvent) => { if (!event.repeat && (event.key === "Enter" || event.key === " ")) paint(event.target); };
    const clear = () => setInks([]);
    document.addEventListener("pointerdown", pointer, true);
    document.addEventListener("keydown", keyboard, true);
    document.addEventListener("scroll", clear, true);
    window.addEventListener("resize", clear);
    return () => {
      document.removeEventListener("pointerdown", pointer, true);
      document.removeEventListener("keydown", keyboard, true);
      document.removeEventListener("scroll", clear, true);
      window.removeEventListener("resize", clear);
    };
  }, [reduced]);
  useEffect(() => {
    if (!inks.length) return;
    let frame = 0;
    // The portal must never paint feedback over the next surface. Inspect only
    // the few live presses, and stop as soon as their short animation ends.
    const inspect = () => {
      const expired = new Set<number>();
      for (const ink of inks) {
        const target = ink.target;
        if (!target.isConnected || target.closest('[inert], [hidden], [aria-hidden="true"], [data-overlay-phase="closing"]') ||
          performance.now() - ink.createdAt > 600) {
          expired.add(ink.id);
          continue;
        }
        const rect = target.getBoundingClientRect();
        const style = getComputedStyle(target);
        // Tolerate a button's press scale, but cancel when navigation or layout
        // moves its surface away from the captured coordinates.
        if (!rect.width || !rect.height || style.visibility !== "visible" ||
          Math.abs(rect.left + rect.width / 2 - ink.left - ink.width / 2) > 8 ||
          Math.abs(rect.top + rect.height / 2 - ink.top - ink.height / 2) > 8 ||
          Math.abs(rect.width - ink.width) > Math.max(16, ink.width * 0.1) ||
          Math.abs(rect.height - ink.height) > Math.max(16, ink.height * 0.1)) expired.add(ink.id);
      }
      if (expired.size) setInks(current => current.filter(ink => !expired.has(ink.id)));
      else frame = requestAnimationFrame(inspect);
    };
    frame = requestAnimationFrame(inspect);
    return () => cancelAnimationFrame(frame);
  }, [inks]);
  return createPortal(<div className="interaction-paint" aria-hidden="true">
    {inks.map(ink => <span className="interaction-clip" key={ink.id} style={{ left: ink.left, top: ink.top,
      width: ink.width, height: ink.height, borderRadius: ink.radius, color: ink.color }}>
      <span className="interaction-ink" onAnimationEnd={() => setInks(old => old.filter(item => item.id !== ink.id))}
        style={{ width: ink.diameter, height: ink.diameter, left: ink.x - ink.diameter / 2, top: ink.y - ink.diameter / 2 }} />
    </span>)}
  </div>, document.body);
}
