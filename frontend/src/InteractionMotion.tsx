import { useRef, type RefObject } from "react";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { motion } from "motion/react";
import { useReducedMotion } from "./useReducedMotion";

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
