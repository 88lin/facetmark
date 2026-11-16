/** Compare JSON request values after the browser's storage serialization. */
export function sameRequest(left: unknown, right: unknown): boolean {
  function canonical(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(canonical);
    if (value && typeof value === "object") {
      const fields = value as Record<string, unknown>;
      return Object.fromEntries(Object.keys(fields).filter(key => fields[key] !== undefined).sort()
        .map(key => [key, canonical(fields[key])]));
    }
    return value;
  }
  return JSON.stringify(canonical(left)) === JSON.stringify(canonical(right));
}
