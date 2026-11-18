import { useCallback, useSyncExternalStore } from "react";

const serverSnapshot = () => false;

// Use the same live subscription as reduced motion so resizing does not leave
// hidden controls or recreate the state owned by the collection and reader.
export function useMediaQuery(query: string) {
  const subscribe = useCallback((onChange: () => void) => {
    const media = window.matchMedia(query);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [query]);
  const getSnapshot = useCallback(() => typeof window !== "undefined" && window.matchMedia(query).matches, [query]);
  return useSyncExternalStore(subscribe, getSnapshot, serverSnapshot);
}
