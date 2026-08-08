// Element builders.
//
// Nothing here writes innerHTML, and nothing that imports this module does
// either. Titles, snippets, folder names and summaries come out of the user's
// own library, which is a browser bookmark export: it contains whatever HTML
// the pages it was scraped from contained. `textContent` everywhere is not
// defensive style, it is the reason this page cannot be made to execute a
// bookmark.
//
// The shapes -- pill, card, progress track, stacked bar, fact grid -- are the
// ones `app.css` styles. Building them in one place is what keeps six views
// from each inventing a slightly different pill.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = String(text);
  return n;
}

export function clear(node) {
  node?.replaceChildren();
  return node;
}

/** A read-only tag. `tone` is one of vec, lex, edge, ok, warn, bad, mute. */
export function pill(tone, text, title) {
  const n = el("span", tone ? `pill ${tone}` : "pill", text);
  if (title) n.title = title;
  return n;
}

/** A clickable filter pill. Pressed state is `aria-pressed`, not a class. */
export function togglePill(text, pressed, onClick, count) {
  const b = el("button", "pill act");
  b.type = "button";
  b.setAttribute("aria-pressed", pressed ? "true" : "false");
  b.appendChild(document.createTextNode(text));
  if (count !== undefined && count !== null) b.appendChild(el("span", "n", count));
  b.addEventListener("click", onClick);
  return b;
}

export function btn(text, cls, onClick) {
  const b = el("button", cls ? `btn ${cls}` : "btn", text);
  b.type = "button";
  if (onClick) b.addEventListener("click", onClick);
  return b;
}

export function card(cls) {
  return el("div", cls ? `card ${cls}` : "card");
}

/** A card with a heading and, optionally, a line of explanation under it. */
export function block(title, lede) {
  const sec = el("section", "block");
  sec.appendChild(el("h2", null, title));
  if (lede) sec.appendChild(el("p", "lede", lede));
  return sec;
}

/**
 * A definition grid. Rows are `{label, value, zero, tone}`; a zero row is
 * dimmed rather than dropped, because "0 failed" is worth reading.
 */
export function facts(rows) {
  const dl = el("dl", "facts");
  for (const r of rows) {
    if (r.value === undefined || r.value === null) continue;
    const row = el("div", r.zero ? "zero" : null);
    row.appendChild(el("dt", null, r.label));
    const dd = el("dd", r.tone ? `t-${r.tone}` : null, r.value);
    row.appendChild(dd);
    dl.appendChild(row);
  }
  return dl;
}

/** Label, thin track, right-aligned reading. `frac` is already 0-100. */
export function barRow(label, frac, reading, gold) {
  const row = el("div", "bar-row");
  row.appendChild(el("span", "lab", label));
  const track = el("div", "track");
  const fill = el("i", gold ? "gold" : null);
  fill.style.width = `${Math.max(0, Math.min(100, frac))}%`;
  track.appendChild(fill);
  row.appendChild(track);
  row.appendChild(el("span", "val", reading));
  return row;
}

/** One bar, many verdicts. `bands` is `[{cls, pct}]` from derive.healthBands. */
export function stackBar(bands) {
  const bar = el("div", "stack");
  for (const b of bands) {
    const seg = el("i", b.cls);
    seg.style.width = `${b.pct}%`;
    bar.appendChild(seg);
  }
  return bar;
}

/** A big coloured numeral over a caption. `tone` is gold, pop or ink. */
export function numberCard(value, label, tone) {
  const n = el("div", tone ? `num ${tone}` : "num");
  n.appendChild(el("b", null, value));
  n.appendChild(el("span", null, label));
  return n;
}

export function numbers(cards) {
  const wrap = el("div", "numbers");
  for (const c of cards) wrap.appendChild(c);
  return wrap;
}

/** Placeholder cards, sized like the thing that is coming. */
export function skeleton(n = 5) {
  const wrap = el("div", "skel");
  for (let i = 0; i < n; i++) wrap.appendChild(el("div"));
  return wrap;
}

/** An external link that opens in a new tab, with the usual opener guard. */
export function link(href, cls, text) {
  const a = el("a", cls, text);
  a.href = href;
  a.target = "_blank";
  a.rel = "noopener";
  return a;
}
