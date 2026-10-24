/** Geometry for the app identity; not a page illustration or an action icon. */
export function FacetmarkMark() {
  return <span className="brand-mark" aria-hidden="true">
    <svg viewBox="0 0 40 40" fill="none">
      <path d="M7 10a5 5 0 0 1 5-5h17a4 4 0 0 1 4 4v22a4 4 0 0 1-4 4H12a5 5 0 0 1-5-5Z" fill="var(--brand-detail)" opacity=".55"/>
      <g className="mark-front">
        <path d="M10 6a4 4 0 0 1 4-4h14a4 4 0 0 1 4 4v29l-11-6-11 6Z" fill="currentColor"/>
        <path d="M14 3h14a3 3 0 0 1 3 3v9L11 24V6a3 3 0 0 1 3-3Z" fill="var(--brand-detail)" opacity=".45"/>
        <path d="M17 12h9M17 17h6" stroke="var(--canvas)" strokeWidth="2.5" strokeLinecap="round"/>
      </g>
    </svg>
  </span>;
}
