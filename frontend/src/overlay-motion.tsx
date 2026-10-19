import { forwardRef } from "react";
import { motion, useIsPresent, type HTMLMotionProps } from "motion/react";
import { useReducedMotion } from "./useReducedMotion";

type OverlayMotionProps = HTMLMotionProps<"div"> & {
  kind?: "dialog" | "menu" | "scrim";
};

/** Presence owns only the visual exit. Closing controls become inert immediately. */
export const OverlayMotion = forwardRef<HTMLDivElement, OverlayMotionProps>(function OverlayMotion(
  { kind = "menu", style, inert, ...props }, ref,
) {
  const present = useIsPresent();
  const reduced = useReducedMotion();
  const distance = kind === "dialog" ? 20 : kind === "menu" ? -8 : 0;
  const scale = kind === "scrim" ? 1 : 0.97;
  return <motion.div {...props} ref={ref}
    data-overlay-phase={present ? "open" : "closing"}
    inert={inert || !present} aria-hidden={present ? props["aria-hidden"] : true}
    initial={reduced ? false : { opacity: 0, y: distance, scale }}
    animate={{ opacity: 1, y: 0, scale: 1, transition: { duration: reduced ? 0 : 0.28, ease: [0.22, 1, 0.36, 1] } }}
    exit={{ opacity: 0, y: reduced ? 0 : distance * 0.5, scale: reduced || kind === "scrim" ? 1 : 0.985,
      transition: { duration: reduced ? 0 : 0.16, ease: [0.4, 0, 1, 1] } }}
    style={{ transformOrigin: kind === "menu" ? "top center" : "center", ...style,
      pointerEvents: present ? style?.pointerEvents : "none" }} />;
});
