import { useRef } from "react";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP);
export const motionTiming = { duration: 0.22, ease: "power3.out", overwrite: "auto" as const };

// A single reusable tween per indicator. A second click continues from its
// current position; it never queues a stale entrance or hides the tab content.
export function useTabIndicator(value: string) {
  const ref = useRef<HTMLDivElement>(null);
  const { contextSafe } = useGSAP({ scope: ref });
  useGSAP(
    () => {
      const root = ref.current;
      if (!root) return;
      const update = contextSafe(() => {
        const active = root.querySelector<HTMLElement>('[aria-selected="true"]');
        const marker = root.querySelector<HTMLElement>(".tab-indicator");
        if (!active || !marker) return;
        gsap.to(marker, {
          ...motionTiming,
          x: active.offsetLeft,
          width: active.offsetWidth,
          duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 0.18,
        });
      });
      update();
      const resize = new ResizeObserver(update);
      resize.observe(root);
      return () => resize.disconnect();
    },
    { dependencies: [value], scope: ref },
  );
  return ref;
}
