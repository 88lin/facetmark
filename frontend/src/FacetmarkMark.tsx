/** Geometry for the app identity; not a page illustration or an action icon. */
export function FacetmarkMark() {
  return <span className="brand-mark" aria-hidden="true">
    <svg viewBox="0 0 40 40" fill="none">
      <path d="M11 9c0-1.1.9-2 2-2h14v26l-8-5-8 5V9Z" fill="currentColor"/>
      <path d="M19 7h8v8h-8V7Z" fill="var(--brand-detail)"/>
      <path d="M15 17h8M15 21h6" stroke="var(--rail)" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  </span>;
}
