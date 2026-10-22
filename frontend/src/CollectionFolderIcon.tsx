import { motion } from "motion/react";
import { useReducedMotion } from "./useReducedMotion";
import "./collection-folder-icon.css";

/** Layered folder geometry; the face opens only with the represented state. */
export function CollectionFolderIcon({ active = false, size = 20 }: { active?: boolean; size?: number }) {
  const reduced = useReducedMotion();
  // Matching commands and point counts allow interpolation through every frame.
  const front = active ? "M6 10L21 10Q22 10 21.7 11L19.6 19Q19.4 20 18.4 20L4 20Q3 20 3.2 19L5 11Q5.2 10 6 10Z" : "M4 10L20 10Q21 10 21 11L21 19Q21 20 20 20L4 20Q3 20 3 19L3 11Q3 10 4 10Z";
  return <svg className="collection-folder-icon" data-open={active} width={size} height={size}
    viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"
    aria-hidden="true" focusable="false">
    <path className="collection-folder-back" d="M3 18V6a2 2 0 0 1 2-2H9l2 2h8a2 2 0 0 1 2 2v10H3Z"/>
    <path className="collection-folder-paper" d="M6 8h12v9H6z"/>
    {reduced ? <path className="collection-folder-front" d={front}/> :
      <motion.path className="collection-folder-front" initial={false} animate={{ d: front }}
        transition={{ duration: 0.2, ease: [0.2, 0.7, 0.3, 1] }}/>}
  </svg>;
}
