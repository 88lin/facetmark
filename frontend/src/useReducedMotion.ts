import { useSyncExternalStore } from "react";

const preference = "(prefers-reduced-motion: reduce)";
const getSnapshot = () => typeof window !== "undefined" && window.matchMedia(preference).matches;
const serverSnapshot = () => true;
function subscribe(onChange: () => void) {
  const media = window.matchMedia(preference);
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

// Motion 12's hook snapshots the preference only at mount. The reader must
// also stop spring/scroll animations when the user changes it while reading.
export function useReducedMotion() {
  return useSyncExternalStore(subscribe, getSnapshot, serverSnapshot);
}
