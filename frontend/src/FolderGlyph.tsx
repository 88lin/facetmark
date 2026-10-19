import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { useReducedMotion } from "./useReducedMotion";
import "./folder-glyph.css";

gsap.registerPlugin(useGSAP);

export type FolderGlyphTone = "amber" | "sky" | "lilac" | "sage";
type FolderGlyphProps = { tone?: FolderGlyphTone; active?: boolean };

/** Exact folder paths keep their color across sorting, filtering and both pickers. */
export function folderTone(value: string): FolderGlyphTone {
  if (!value) return "amber";
  const path = value.normalize("NFC");
  let hash = 2166136261;
  for (let index = 0; index < path.length; index++) {
    hash = Math.imul(hash ^ path.charCodeAt(index), 16777619);
  }
  hash ^= hash >>> 16;
  return (["amber", "sky", "lilac", "sage"] as const)[(hash >>> 0) % 4];
}

/** Decorative only. The containing button retains its size, input and press behavior. */
export function FolderGlyph({ tone = "amber", active = false }: FolderGlyphProps) {
  const glyph = useRef<HTMLSpanElement>(null);
  const selected = useRef(active);
  const setSelection = useRef<(value: boolean) => void>(() => {});
  const reduced = useReducedMotion();

  useGSAP((_context, contextSafe) => {
    const root = glyph.current;
    const button = root?.closest<HTMLButtonElement>("button");
    if (!root || !button || reduced || !contextSafe) return;
    const paper = root.querySelector<HTMLElement>(".folder-glyph__paper")!;
    const front = root.querySelector<HTMLElement>(".folder-glyph__front")!;
    const shine = root.querySelector<HTMLElement>(".folder-glyph__shine")!;
    const cover = [front, shine];
    let hovered = false;
    let focused = button.matches(":focus-visible");
    let sequence: gsap.core.Timeline | null = null;

    const available = () => root.isConnected && button.isConnected && !document.hidden &&
      !button.disabled && !button.closest('[inert], [hidden], [aria-hidden="true"], [aria-disabled="true"]');
    const pose = () => {
      const engaged = hovered || focused;
      return { angle: engaged ? -25 : selected.current ? -14 : 0,
        paper: engaged ? -24 : selected.current ? -12 : 0,
        shine: engaged ? 0.54 : selected.current ? 0.36 : 0.18 };
    };
    const initial = pose();
    // Own an initial pose before active's CSS fallback changes on the next render.
    gsap.set(cover, { rotationX: initial.angle });
    gsap.set(paper, { y: 0, yPercent: initial.paper });
    gsap.set(shine, { opacity: initial.shine });
    const guard = () => { if (!available()) stop(); };
    const coverTo = gsap.quickTo(cover, "rotationX", { duration: 0.28, ease: "power3.out", onUpdate: guard });
    const paperTo = gsap.quickTo(paper, "yPercent", { duration: 0.26, ease: "power3.out", onUpdate: guard });
    const shineTo = gsap.quickTo(shine, "opacity", { duration: 0.18, ease: "power2.out", onUpdate: guard });
    const pause = () => {
      sequence?.kill();
      sequence = null;
      coverTo.tween.pause();
      paperTo.tween.pause();
      shineTo.tween.pause();
    };
    const stop = contextSafe(() => {
      pause();
      hovered = false;
      focused = false;
      // Paused/disconnected controls retain a static selected/rest pose only.
      const current = pose();
      gsap.set(cover, { rotationX: current.angle });
      gsap.set(paper, { yPercent: current.paper });
      gsap.set(shine, { opacity: current.shine });
    });
    const settle = () => {
      if (!available()) { stop(); return; }
      sequence?.kill();
      sequence = null;
      const current = pose();
      // quickTo retargets the painted position, including an interrupted selection.
      coverTo(current.angle, Number(gsap.getProperty(front, "rotationX")));
      paperTo(current.paper, Number(gsap.getProperty(paper, "yPercent")));
      shineTo(current.shine, Number(gsap.getProperty(shine, "opacity")));
    };
    const select = contextSafe((value: boolean) => {
      if (!value || !available()) { settle(); return; }
      pause();
      const current = pose();
      sequence = gsap.timeline({ defaults: { ease: "power3.out" }, onUpdate: guard,
        onComplete: () => { sequence = null; } });
      sequence.addLabel("open", 0).addLabel("hold", 0.15).addLabel("settle", 0.2)
        .to(cover, { rotationX: -31, duration: 0.15 }, "open")
        .to(paper, { yPercent: -28, duration: 0.17 }, "open+=0.02")
        .to(shine, { opacity: 0.64, duration: 0.13 }, "open")
        .to(cover, { rotationX: current.angle, duration: 0.19 }, "settle")
        .to(paper, { yPercent: current.paper, duration: 0.19 }, "settle")
        .to(shine, { opacity: current.shine, duration: 0.16 }, "settle");
    });
    setSelection.current = select;
    const enter = () => { hovered = true; settle(); };
    const leave = () => { hovered = false; settle(); };
    const focusIn = () => { focused = button.matches(":focus-visible"); settle(); };
    const focusOut = (event: FocusEvent) => {
      if (event.relatedTarget instanceof Node && button.contains(event.relatedTarget)) return;
      focused = false;
      settle();
    };
    const hidden = () => { if (document.hidden) stop(); };
    const changes = new MutationObserver(() => { if (!available()) stop(); });
    // Attribute changes stop immediately; the running-tween guard also covers an
    // ancestor becoming inert or a subtree being removed, without a global observer.
    changes.observe(button, { attributes: true,
      attributeFilter: ["disabled", "inert", "hidden", "aria-hidden", "aria-disabled"] });
    button.addEventListener("pointerenter", enter);
    button.addEventListener("pointerleave", leave);
    button.addEventListener("pointercancel", leave);
    button.addEventListener("focusin", focusIn);
    button.addEventListener("focusout", focusOut);
    window.addEventListener("blur", stop);
    document.addEventListener("visibilitychange", hidden);
    return () => {
      setSelection.current = () => {};
      changes.disconnect();
      button.removeEventListener("pointerenter", enter);
      button.removeEventListener("pointerleave", leave);
      button.removeEventListener("pointercancel", leave);
      button.removeEventListener("focusin", focusIn);
      button.removeEventListener("focusout", focusOut);
      window.removeEventListener("blur", stop);
      document.removeEventListener("visibilitychange", hidden);
      pause();
    };
  }, { scope: glyph, dependencies: [reduced], revertOnUpdate: true });

  useLayoutEffect(() => {
    const changed = selected.current !== active;
    selected.current = active;
    if (changed) setSelection.current(active);
  }, [active]);

  return <span ref={glyph} className="folder-glyph" data-tone={tone} data-active={active} aria-hidden="true">
    <span className="folder-glyph__back" />
    <span className="folder-glyph__paper" />
    <span className="folder-glyph__front" />
    <span className="folder-glyph__shine" />
  </span>;
}
