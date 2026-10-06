---
name: Facetmark collection and reader
description: A personal collection of white rounded cards on a pale blue workspace, with lake-blue selection and a generous
  reader.
colors:
  canvas: '#ffffff'
  desk: '#edf4f8'
  inset: '#f3f8fb'
  ink: '#193549'
  muted: '#526d7e'
  rule: '#dce8ee'
  accent: '#087293'
  soft: '#e0f2f8'
  selected: '#ddf1f8'
  selected-edge: '#8dc7dc'
  on-accent: '#fff'
  danger: '#ad3448'
  overlay: '#16374a55'
  canvas-dark: '#1b303e'
  desk-dark: '#101e28'
  inset-dark: '#243b49'
  ink-dark: '#e4f0f5'
  muted-dark: '#a6becc'
  rule-dark: '#345060'
  accent-dark: '#70cde9'
  soft-dark: '#203f50'
  selected-dark: '#204758'
  selected-edge-dark: '#407e98'
  on-accent-dark: '#0c2b3b'
  danger-dark: '#f7a0ae'
  overlay-dark: '#06151f99'
typography:
  collection-heading:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 27px
    lineHeight: 1.35
    fontWeight: 650
    letterSpacing: -0.025em
  page-title:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 30px
    lineHeight: 1.5
    fontWeight: 600
    letterSpacing: -0.02em
  article-title:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 30px
    lineHeight: 1.4
    fontWeight: 650
    letterSpacing: -0.025em
  article-title-focus:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 34px
    lineHeight: 1.4
    fontWeight: 650
    letterSpacing: -0.025em
  article-section:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 18px
    lineHeight: 1.65
    fontWeight: 600
    letterSpacing: -0.02em
  collection-title:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 18px
    lineHeight: 1.55
    fontWeight: 600
  index-title:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 16px
    lineHeight: 1.55
    fontWeight: 600
  collection-summary:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 14px
    lineHeight: 1.7
  index-summary:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 13px
    lineHeight: 1.7
  body:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 14px
    lineHeight: 1.6
  reading:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 16px
    lineHeight: 1.85
  button:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 13px
    lineHeight: 1.5
    fontWeight: 550
  search:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 15px
    lineHeight: 1.6
  tab:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 13px
    lineHeight: 1.6
  label:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 12px
    lineHeight: 1.6
  caption:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 11px
    lineHeight: 1.6
  diagnostic:
    fontFamily: ui-monospace, Consolas, monospace
    fontSize: 11px
    lineHeight: 1.6
rounded:
  hint: 7px
  facet: 8px
  segment: 9px
  control: 10px
  brand: 11px
  panel: 12px
  navigation: 13px
  search: 14px
  entry: 16px
  sheet: 20px
spacing:
  micro: 4px
  tight: 6px
  compact: 8px
  small: 12px
  medium: 16px
  card-row: 18px
  content: 20px
  section: 24px
  gutter: 28px
  large: 32px
  frame: 36px
  reader-gutter: 46px
components:
  button-primary:
    backgroundColor: '{colors.accent}'
    textColor: '{colors.on-accent}'
    typography: '{typography.button}'
    rounded: '{rounded.control}'
    padding: 10px 16px
  button-secondary:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.button}'
    rounded: '{rounded.control}'
    padding: 9px 14px
  button-text:
    textColor: '{colors.accent}'
    typography: '{typography.label}'
    padding: 5px 0
  button-icon:
    textColor: '{colors.ink}'
    rounded: '{rounded.control}'
    width: 32px
    height: 32px
  reader-back:
    textColor: '{colors.muted}'
    typography: '{typography.tab}'
  search-field:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.search}'
    rounded: '{rounded.search}'
    padding: 7px 15px
    height: 50px
  header-navigation-active:
    textColor: '{colors.accent}'
    typography: '{typography.tab}'
    padding: 8px 16px
    backgroundColor: '{colors.canvas}'
    rounded: '{rounded.segment}'
  filter-chip:
    backgroundColor: '{colors.soft}'
    textColor: '{colors.accent}'
    typography: '{typography.label}'
    rounded: '{rounded.facet}'
    padding: 5px 9px
  collection-entry:
    textColor: '{colors.ink}'
    typography: '{typography.collection-title}'
    padding: 24px
    backgroundColor: '{colors.canvas}'
    rounded: '{rounded.entry}'
  result-selected:
    backgroundColor: '{colors.selected}'
    textColor: '{colors.ink}'
    rounded: '{rounded.entry}'
    padding: 18px 20px
    typography: '{typography.index-title}'
  reading-sheet:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    rounded: '{rounded.sheet}'
  preview-tabs:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.muted}'
    typography: '{typography.tab}'
    padding: 0 18px
    height: 60px
  apply-panel:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    rounded: '{rounded.panel}'
    padding: 24px
  model-field:
    backgroundColor: '{colors.inset}'
    textColor: '{colors.ink}'
    rounded: '{rounded.control}'
    padding: 11px 12px
  reader-tab-active:
    backgroundColor: '{colors.soft}'
    textColor: '{colors.accent}'
    typography: '{typography.tab}'
    rounded: '{rounded.segment}'
    padding: 0 12px
    height: 34px
---

# Design System: Facetmark collection and reader

## Overview

**Creative North Star: "Shared collection and reader — Operate / Read"**

Facetmark presents saved pages as a personal collection: white rounded cards on a pale blue workspace, deep blue ink, and lake-blue actions. A selected card becomes a clear blue anchor beside a generous white reader. The layered Facetmark mark remains the identity.

Navigation and filters support the content; focus reading removes competing chrome. Local Chinese/English font fallbacks, semantic dark-theme equivalents, visible keyboard focus and reduced motion carry the same system across desktop and Web.

**Key Characteristics:**

- White cards remain distinct from the pale blue workspace.
- Lake-blue selection marks the active page without hiding the surrounding collection.
- Titles and excerpts lead; source initials and saved dates support recognition.
- Rounded controls, segmented selections and ambient shadows give surfaces clear boundaries.
- Reading modes preserve context; narrow reading provides a visible return action.

This refresh records source inspection of `frontend/src/styles.css`, followed by its overrides in `frontend/src/workbench.css`, as imported by `frontend/src/main.tsx`, plus the collection, reader and motion components. It replaces the user-rejected grey-violet treatment. Cloud evidence for 7a20776 and the two-fix visual confirmation are recorded in docs/desktop-validation.md; neither automated checks nor independent review imply user acceptance.

## Colors

Frontmatter is normative. Base names map to runtime custom properties; each `-dark` token is the same semantic role in dark mode. Sidecar tonal ramps are preview swatches, not extra runtime tokens.

### Primary

- **Lake Blue** (`accent`): actions, links, selected titles, active navigation/tab text, focus and reading progress.
- **Lake Mist** (`soft`): tab selection, filter chips, notices, pressed controls and text selection.
- **Selected Water / Selected Edge** (`selected`, `selected-edge`): active collection fill and inset outline; the edge also marks hover and the import target.
- **On Lake Blue** (`on-accent`): text and mark strokes on filled primary actions.

### Neutral

- **Pure White** (`canvas`): header, cards, search, reader and support surfaces. Dark mode maps this role to blue charcoal.
- **Pale Blue Workspace** (`desk`): space around the collection and reader; also the focused header.
- **Cool Inset** (`inset`): navigation tray, model inputs, reader-action backgrounds, skeletons, diagnostics and shared hover.
- **Deep Blue Ink / Muted Blue Ink** (`ink`, `muted`): primary text and subordinate excerpts, metadata and controls.
- **Cool Rule / Navigation Scrim** (`rule`, `overlay`): thin outlines and separators; the scrim belongs to temporary navigation. The full-width reader overlay is transparent.

Error Red (`danger`) accompanies explicit failure and recovery. Dark mode uses pale lake-blue accents and blue selected surfaces over a deeper workspace; roles and hierarchy remain consistent.

**The Lake-blue Selection Rule.** Keep ordinary collection cards white. Use the selected fill, inset edge and lake-blue title together for the active page; reserve danger color for failures.

## Typography

Use the local interface/reading font stack in frontmatter. Diagnostic output alone uses monospace. This operational interface has no decorative display face.

- **Headings:** collection-heading introduces the library; page-title serves support views. Article-title becomes article-title-focus during focus reading. Chinese base headings remove tracking, while the more specific collection/article rules retain their declared tracking.
- **Collection:** collection-title and collection-summary become the smaller index-title and index-summary beside the article. Both title and excerpt clamp to two lines. Visual order is title, excerpt, source/date, then selected folder context; current DOM order still places metadata first and is not a recommended reading-order pattern.
- **Reading:** reading uses generous leading, paragraph space (1.25em), and explicit section headings with margins (28px above, 10px below). Counts, saved dates, pagination and percentages use tabular numerals.
- **Compact overrides:** article titles are (28px) at 1120–1300px; collection headings are (24px) below 1120px. At most 719px: collection/support heading (26px), article title (25px), card title (17px), excerpt (13px), search (14px), tabs (12px), and prose (16px). These are context overrides, not a separate scale.

**The Reading Rhythm Rule.** Let titles and excerpts lead the collection, then let article text set the reading pace. Wrap Chinese text, long titles and URLs without widening the workspace.

## Layout

The dynamic-viewport shell (`100dvh`, minimum height 400px) places a horizontal header (72px) above a centered workspace (maximum 1480px, side padding 36px, bottom padding 24px). The temporary navigation/filter drawer is (300px) wide and closed/inert by default. It never consumes a permanent collection column.

The toolbar (88px) places the collection heading beside search (maximum 520px), search help and Filters. Before selection, toolbar and collection are bounded by (1160px); cards form two equal columns with a column gap (20px), row gap (18px), padding (24px), and minimum height (166px). Each two-column grid row sizes to its content; cards fill that row (height 100%). Their content column stretches with a minimum height (118px), and source/date metadata uses automatic top margin plus top padding (12px) to share a baseline across the pair. The scrollable list includes padding (3px 4px 12px) above its separate pagination footer (46px).

After selection, the desktop index is (360px) beside a gap (24px) and flexible reader. Index cards use padding (18px 20px) and bottom spacing (10px). The collection stays mounted. The reader appears only after selection; it does not reserve an empty welcome column.

Desktop reader actions share the tab strip (60px). Article width is capped at (820px), including gutters; title padding is (26px 46px 0) and body padding is (14px 46px 44px). The article scrolls between fixed tabs and a reading-position footer (42px).

Focus reading hides navigation, utilities, search and results, reduces the header to (56px), and places the same pane at workspace insets (16px top, 36px sides, 24px bottom). Article width becomes (800px) with title top space (35px). Hidden results are inert.

Support pages share a centered white surface (maximum 1050px), top margin (28px), and padding (36px 48px 48px). Model channels are two ruled, unboxed columns with a gap (48px). Scoped apply, consent, stage and saving-session panels retain their own boundaries.

| Viewport | Source-defined exceptions |
| --- | --- |
| At least 1600px | Index (390px), reader gutter (56px). |
| 1120–1300px | Index (330px), reader gutter (36px), workspace sides (28px), selected-layout gap (22px), search basis (430px); reader count hides. |
| 720–1119px | Workspace sides (28px), toolbar (100px); collection columns use (18px) gaps. Browsing retains (24px) card padding; the selected collection uses (20px 16px). Article opens as a full-width modal with a (52px) Back to collection/actions row and (48px) tab strip. Header menu appears, language/demo text hide. Support padding (32px); model columns stack with (16px) gaps. |
| At most 719px | Header (60px), workspace sides (18px), navigation/utilities in drawer. Toolbar has a heading row and search/help/filter row; search height (45px). Cards remain rounded and content-sized in one column with padding (20px) and spacing (12px); card height becomes auto and the content-column minimum height becomes 0. Article gutter (24px), body top padding (22px). Support top margin (16px), padding (24px 20px); form actions stack. |

The modal reader fills the viewport with square outer edges and no sheet shadow. Its tab strip remains (48px) even on mobile due to selector specificity. Mobile search hides the shortcut hint; search help fits `min(340px, calc(100vw - 36px))`. The import target keeps its later workbench padding (48px 24px) on mobile.

## Elevation & Depth

Ambient shadows distinguish white cards and reader surfaces from the pale blue workspace. Fine rules still separate reader controls, forms and status regions. There is no backdrop blur.

- **Resting card / active header segment:** `var(--card-shadow)`; light `0 3px 12px #244e6710`, dark `0 3px 14px #00000020`.
- **Reader / support surface:** `var(--sheet-shadow)`; light `0 12px 36px #244e6712`, dark `0 12px 36px #00000028`.
- **Card hover / selection:** `inset 0 0 0 1px var(--selected-edge)`.
- **Open temporary navigation:** `8px 0 40px #16374a24`; the closed drawer has no shadow, so it leaves no edge on the workspace.
- **Floating search help:** `0 12px 36px #244e6718`, plus a fine border.

Keyboard focus uses an accent outline (2px, offset 3px); result-card focus has inset offset (-3px). Search focuses through an accent border while retaining its white fill.

**The Bounded Depth Rule.** Use ambient shadows for resting cards and reading surfaces. Hover and selection replace the card shadow with a thin inset edge; do not add a lift transform.

## Shapes

Rounded collection cards and import targets use the entry radius (16px); desktop readers and support surfaces use sheet (20px); shared buttons, fields, notices and saving-session rows use control (10px). Mobile cards retain their shape. The modal reader is an intentional square-edged, full-viewport exception.

Smaller patterns retain their own radii: search (14px), header navigation tray (13px), selected segments (9px), brand tile (11px), filter chips (8px), and source initials/shortcut hints (7px). Apply, consent and stage panels remain (12px); search-help popovers remain (8px). Navigation has only its right corners rounded (20px).

Lucide SVGs provide stroke icons and the layered brand mark, which sits in a lake-blue tile. Collection source initials are small (23px) badges; they are text identity hints, not action icons. Trailing result chevrons and the former selected-edge stripe remain hidden.

## Components

### Buttons and fields

Primary/secondary actions use minimum height (36px), icon gap (8px), icons (16px) and their frontmatter padding. Filled primary/import actions darken via `brightness(0.94)` on hover. Secondary and general icon buttons use Cool Inset hover; text actions underline. Disabled buttons use opacity (0.42).

Search uses a thin outline and its own taller rounded container, with an internal clear action and Ctrl/Cmd+K access. Model fields use Cool Inset at rest and when disabled; disabled type becomes muted. Field focus retains the global visible outline. Reader action buttons use Cool Inset at rest and Lake Mist/Lake Blue on hover; their more specific resting background also overrides the shared pressed fill, while the pressed text stays blue.

### Navigation and chips

Header navigation is a segmented tray with padding (4px), gap (4px), and segment padding (8px 16px). The active segment is white with lake-blue text, weight (650), and card shadow; it has no underline. Inactive hover uses Lake Mist. The filled import action uses padding (10px 15px).

Filters open the drawer at every width. Drawer navigation keeps icons, facet counts and a filled active state. Opening it makes header/main inert and provides modal keyboard handling; closing returns focus. Filter chips use the frontmatter variant. Disclosed article tags remain lightweight hashtag text; their hover uses Lake Mist and Lake Blue.

### Collection cards

The full-card button places title, two-line excerpt, source initial/domain/date and selected folder context on a content gap (7px). Hover mixes white (70%) with Lake Mist and uses the inset selected edge. Selection uses Selected Water, the same edge, a blue title, and a Reading label when folder context exists. `aria-pressed` exposes selection.

ArrowUp/ArrowDown selects adjacent cards. Opening and returning preserve query, filters, page, collection position and originating focus. Empty collection, no matches and retrieval failures retain distinct explanations and actions.

### Reader

Reader tabs are rounded segments (34px high), with a moving Lake Mist background and blue selected label. The strip uses gap (4px); the marker is (13px) from the desktop top and (7px) in the modal reader. ArrowLeft/ArrowRight and Home/End move within one active tab stop and a linked panel. Previous/next, focus and close share the desktop strip; narrow reading exposes Back to collection and previous/next.

The original-page link sits above the title. Saved folder, tags and search explanations are disclosed under Saved details & search context. Body, AI summary and related content keep distinct loading, missing and failure states. Tab scroll positions are retained for the current bookmark and reset for a new one. Explicit Markdown headings define sections; exact duplicated first-title paragraphs are omitted.

The position rail measures saved-body scroll extent and shows a section picker only with multiple explicit sections. It displays no invented progress for other tabs or failed/missing body text. Focus expansion retains the same pane and restores the prior split-view article position. Escape restores split view before closing the preview; Radix supplies modal focus handling on narrow screens.

### Support panels and motion

Model channels retain independent states/tests and blue headings. Apply, consent and stage panels stay outlined; import uses a dashed selected-edge outline on Lake Mist. Saving-session rows use Cool Inset hover. Configured, tested, indexed and applied states remain separate.

CSS owns shared control transitions (150ms), card/header-segment and facet-chevron transitions (180ms), and navigation translation (220ms), using `cubic-bezier(0.22, 1, 0.36, 1)`. Busy spinners rotate linearly over (1.1s). Cards have no staggered entrance.

GSAP owns tab-marker position/width (180ms, `power3.out`, overwrite `auto`) and focus-pane translation on both axes (220ms). A new focus action kills the old timeline, measures current geometry and clears the transform on completion. Motion owns modal-reader translation (220ms, easing [0.22, 1, 0.36, 1]), transparent-overlay opacity (180ms), and progress scale with spring stiffness (180), damping (35), mass (0.25). Reduced motion disables CSS transitions/animations, makes GSAP/drawer changes immediate, uses direct progress and automatic programmatic scrolling.

## Do's and Don'ts

### Do:

- Do preserve white cards, pale blue workspace and the distinct blue selected card.
- Do use the shared card, reader and control radii while retaining documented component exceptions.
- Do keep source initials subordinate to titles and excerpts.
- Do preserve query, filters, pagination, collection position and originating-row focus when returning from reading.
- Do keep reader tabs and actions outside the article scroller and disclose saved details on demand.
- Do provide a visible Back to collection control in the full-width narrow reader.
- Do bind both themes to semantic roles and preserve keyboard access, reduced motion and distinct recovery states.

### Don't:

- Don't restore the rejected grey-violet palette or permanent three-column management shell.
- Don't turn white collection cards into transparent ruled rows, including on mobile.
- Don't replace the independent Facetmark identity with hand-drawn borders, gradients or a candy-colored dashboard.
- Don't let GSAP, Motion and CSS animate the same property on the same element.
- Don't invent reading percentages, section headings or successful task states.
