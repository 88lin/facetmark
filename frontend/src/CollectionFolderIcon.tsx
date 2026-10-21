import { motion } from "motion/react";
import { useReducedMotion } from "./useReducedMotion";
import "./collection-folder-icon.css";

/** A single ink folder; its front opens when the represented path is active. */
export function CollectionFolderIcon({ active = false, size = 20 }: { active?: boolean; size?: number }) {
  const reduced = useReducedMotion();
  const front = active ? "M5 10.5H22L19 19H3L5 10.5Z" : "M3 9H20L20 19H3L3 9Z";
  return <svg className="collection-folder-icon" data-open={active} width={size} height={size}
    viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
    aria-hidden="true" focusable="false">
    <path d="M3 17.5V6a1.5 1.5 0 0 1 1.5-1.5H9l2 2h7.5A1.5 1.5 0 0 1 20 8v2.5"/>
    {reduced ? <path className="collection-folder-front" d={front}/> :
      <motion.path className="collection-folder-front" initial={false} animate={{ d: front }}
        transition={{ duration: 0.2, ease: [0.2, 0.7, 0.3, 1] }}/>}
  </svg>;
}
