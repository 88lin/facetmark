---
name: Facetmark collection and reader
description: A white and lake-blue collection with compact controls, a searchable category directory, source-first cards and a focused
  article rail.
colors:
  canvas: '#ffffff'
  desk: '#f5f9fb'
  inset: '#f3f8fb'
  ink: '#1c303b'
  muted: '#566b78'
  rule: '#e1eaf0'
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
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 22px
    lineHeight: 1.35
    fontWeight: 650
    letterSpacing: -0.035em
  page-title:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 32px
    lineHeight: 1.5
    fontWeight: 600
    letterSpacing: -0.02em
  article-title:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 36px
    lineHeight: 1.4
    fontWeight: 650
    letterSpacing: -0.025em
  article-title-focus:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 38px
    lineHeight: 1.4
    fontWeight: 650
    letterSpacing: -0.025em
  article-section:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 21px
    lineHeight: 1.65
    fontWeight: 600
    letterSpacing: -0.02em
  collection-title:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 16px
    lineHeight: 1.5
    fontWeight: 650
  index-title:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 15px
    lineHeight: 1.6
    fontWeight: 650
  collection-summary:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 13px
    lineHeight: 1.6
  index-summary:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 12px
    lineHeight: 1.7
  body:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 14px
    lineHeight: 1.6
  reading:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 17px
    lineHeight: 1.9
  button:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 13px
    lineHeight: 1.5
    fontWeight: 600
  search:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 14px
    lineHeight: 1.6
  tab:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 13px
    lineHeight: 1.6
  label:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 12px
    lineHeight: 1.6
  caption:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 11px
    lineHeight: 1.6
  diagnostic:
    fontFamily: ui-monospace, Consolas, monospace
    fontSize: 11px
    lineHeight: 1.6
  workspace-heading:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 22px
    fontWeight: 650
    lineHeight: 1.35
    letterSpacing: -0.025em
  index-search:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 15px
    lineHeight: 1.6
  outline:
    fontFamily: '"Manrope", "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.65
rounded:
  micro: 4px
  hint: 7px
  field: 10px
  brand: 11px
  panel: 12px
  popover: 14px
  entry: 16px
  sheet: 20px
  pill: 999px
  circle: 50%
spacing:
  micro: 4px
  tight: 6px
  compact: 8px
  small: 12px
  medium: 16px
  content: 20px
  card-padding: 14px
  section: 24px
  gutter: 28px
  large: 32px
  frame: 36px
  reader-top: 40px
  reader-gutter: 46px
components:
  button-primary:
    backgroundColor: '{colors.accent}'
    textColor: '{colors.on-accent}'
    typography: '{typography.button}'
    rounded: '{rounded.pill}'
    padding: 10px 20px
    height: 40px
  button-secondary:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.button}'
    rounded: '{rounded.pill}'
    padding: 9px 18px
    height: 40px
  button-text:
    textColor: '{colors.accent}'
    typography: '{typography.label}'
    padding: 5px 10px
    rounded: '{rounded.pill}'
    height: 32px
  button-icon:
    textColor: '{colors.ink}'
    rounded: '{rounded.circle}'
    width: 36px
    height: 36px
  reader-back:
    textColor: '{colors.muted}'
    typography: '{typography.tab}'
    rounded: '{rounded.pill}'
    padding: 6px 12px
    height: 40px
  search-field:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.search}'
    rounded: '{rounded.pill}'
    padding: 6px 14px
    height: 40px
  header-navigation-active:
    textColor: '{colors.accent}'
    typography: '{typography.tab}'
    padding: 8px 17px
    backgroundColor: '{colors.soft}'
    rounded: '{rounded.pill}'
  filter-chip:
    backgroundColor: '{colors.soft}'
    textColor: '{colors.accent}'
    typography: '{typography.label}'
    rounded: '{rounded.pill}'
    padding: 5px 12px
    height: 32px
  collection-entry:
    textColor: '{colors.ink}'
    typography: '{typography.collection-title}'
    padding: 14px
    backgroundColor: '{colors.canvas}'
    rounded: '{rounded.panel}'
  result-selected:
    backgroundColor: '{colors.selected}'
    textColor: '{colors.ink}'
    rounded: '{rounded.panel}'
    padding: 16px 14px
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
    height: 56px
  apply-panel:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    rounded: '{rounded.panel}'
    padding: 24px
  model-field:
    backgroundColor: '{colors.inset}'
    textColor: '{colors.ink}'
    rounded: '{rounded.field}'
    padding: 12px 14px
    height: 46px
  reader-tab-active:
    backgroundColor: '{colors.soft}'
    textColor: '{colors.accent}'
    typography: '{typography.tab}'
    rounded: '{rounded.pill}'
    padding: 0 13px
    height: 36px
  model-channels:
    textColor: '{colors.ink}'
    typography: '{typography.body}'
  search-field-index:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.index-search}'
    rounded: '{rounded.pill}'
    padding: 7px 18px
    height: 40px
  category-option-active:
    backgroundColor: '{colors.selected}'
    textColor: '{colors.accent}'
    typography: '{typography.label}'
    rounded: 8px
    padding: 8px 10px
    height: 36px
  query-suggestion-active:
    backgroundColor: '{colors.soft}'
    textColor: '{colors.accent}'
    rounded: '{rounded.field}'
    padding: 10px
    height: 58px
  reader-outline:
    textColor: '{colors.muted}'
    typography: '{typography.outline}'
    width: 170px
    padding: 3px 7px 7px 3px
  reader-outline-link:
    textColor: '{colors.muted}'
    typography: '{typography.outline}'
    rounded: '{rounded.micro}'
    padding: 8px 4px 8px 16px
    height: 36px
---

# Design System: Facetmark collection and reader

## Overview

**Creative North Star: "Shared collection and reader — Operate / Read"**

Facetmark keeps saved writing easy to find and comfortable to read. A compact title/count and pill search share the desktop toolbar. A searchable vertical category directory sits beside the actual bookmarks. Source-first white cards or a denser list use the available width, while the layered Facetmark mark and lake-blue interactions retain the identity.

Selecting a bookmark replaces the category directory with a compact supporting index and makes the article the primary surface. The reader keeps its bounded text measure, quiet chapter rail and return context. Bundled Manrope, local Chinese fallbacks, dark-theme roles, keyboard access and reduced motion carry the system across desktop and Web.

**Key Characteristics:**

- A compact toolbar leaves the majority of a short desktop window available for bookmarks.
- Complete folders, tags and sites are searchable and vertically scrollable with a mouse; loading more is explicit.
- Source-first cards and a persistent list alternative support different browsing densities.
- Lake-blue selection, pill controls and circular icon actions clarify state and priority.
- The bounded reader retains query, filters, page, collection position and return focus.
- Changing search/category clears the old reading context and prevents selection or export of stale results.

The previous large-masthead layout and its historical `ship` verdict were rejected by the user. This contract supersedes those layout rules. The user-supplied interface reference is [GithubStarsManager](https://github.com/AmintaCCCP/GithubStarsManager), inspected at `6d1dd80700b0ee717f79a5da7d0137f32afc91b7`; only its compact controls and accessible category organization inform this revision. It is an interface reference, not an approved pixel comp. No reference code or screenshots ship in Facetmark.

This documentation was confirmed on 2026-10-10 against source `09ab0332c5f9ec40627afc7f48f3da2ce0b8b36b` and the synthetic-only cloud evidence captured on 2026-10-09. `.desktop-build/collection-verified/provenance.json` records 51 captures and the 14.24-second reading recording from [Experience 37927920369](https://github.com/88lin/facetmark/actions/runs/37927920369). The current desktop collection, mobile collection and exact-category-search captures match the compact toolbar, source-first cards and vertical directory described here. Cloud validation has passed. The final independent confirmation returned `disposition: ship`, with all six requested fixes resolved and no material regression identified in that scope. The original reviewer and an earlier replacement were rate-limited; a general independent substitute completed the confirmation because the dedicated role was unavailable. This verdict covers those six fixes and does not imply the user's visual approval. Earlier captures do not verify this revision.


## Colors

Frontmatter is normative. Base names map to runtime custom properties; each `-dark` token is the same semantic role in dark mode. Sidecar tonal ramps are preview swatches, not extra runtime tokens.

### Primary

- **Lake Blue** (`accent`): actions, links, selected titles, active navigation/tab text, focus and reading position.
- **Lake Mist** (`soft`): active header navigation and reader tabs, source badges, chips, notices, pressed controls and text selection.
- **Selected Water / Selected Edge** (`selected`, `selected-edge`): active index fill and border; the edge also marks card hover, folder selection and the import target.
- **On Lake Blue** (`on-accent`): text and mark strokes on filled primary actions.

### Neutral

- **Pure White** (`canvas`): header, open cards, search, reader and support surfaces; blue charcoal in dark mode.
- **Pale Blue Workspace** (`desk`): surrounding workspace, transparent index rows and focused header.
- **Cool Inset** (`inset`): navigation tray, fields, reader actions, skeletons, diagnostics and shared hover.
- **Deep Blue Ink / Muted Blue Ink** (`ink`, `muted`): titles/prose and subordinate excerpts, metadata and controls.
- **Cool Rule / Navigation Scrim** (`rule`, `overlay`): fine borders/seams and temporary navigation backdrop. The full-width reader overlay is transparent.

Error Red (`danger`) accompanies explicit failures, recovery and destructive-action warnings. Dark mode retains hierarchy with pale blue accents over deeper surfaces.

**The Lake-blue Selection Rule.** Use white bordered cards in the open collection, then a quiet supporting index with a blue selected entry. Pair selected fill, border and title color; reserve danger color for failures and destructive actions.

## Typography

Manrope is bundled at `frontend/src/assets/Manrope-variable.ttf` for offline Latin typography, with normal weights (200–800) and `font-display: swap`. The frontmatter stack includes local Segoe UI and Chinese fallbacks. Diagnostic output alone uses monospace; platform font rendering is not guaranteed by declarations alone.

- **Headings:** collection-heading is the compact current collection/category heading; workspace-heading introduces selected reading; page-title serves support pages. Article-title enlarges to article-title-focus. Chinese base headings remove tracking; more specific collection/article rules retain their declared tracking.
- **Cards/index:** visual and DOM order is source, title, optional excerpt, then folder/date metadata. Open titles/excerpts clamp to two lines; the compact index keeps a two-line title and one-line excerpt.
- **Reading:** paragraphs use lower space (1.25em); explicit section headings use margins (34px above, 12px below). Counts, dates, pagination and percentages use tabular numerals.
- **Responsive type:** the collection heading remains (22px) across breakpoints, card title (16px) and excerpt (13px). Search is (14px) on desktop and (15px) on mobile. List view uses (15px) titles and (12px) single-line excerpts, with source and metadata in a second desktop column; mobile uses a single column without an excerpt. Standard article title is (32px) at 1120–1300px. At most 719px: article title (27px), tabs (12px), prose (17px / 1.85). Selected-index title/excerpt remain (15px / 12px).

**The Reading Rhythm Rule.** Let a recognizable source introduce each saved page, then use title and excerpt to invite reading. Give the article a bounded measure and wrap Chinese text, long titles and URLs.

## Layout

The dynamic-viewport shell (`100dvh`, minimum height 400px) places a white header (56px) above a full-width workspace (sides 24px, bottom 12px). Identity/navigation sit left; utilities/import sit right. Temporary navigation is (300px) wide, closed/inert with no shadow until opened.

The desktop toolbar is (60px) high. Current title and result count share its left side; the (40px) pill search and filter controls share the right. A compact action row above the results contains creation, selection, organization, export and the card/list switch. Filter chips appear only when active. There is no duplicate collection/result masthead or horizontal folder strip.

From (960px), an independently scrolling category directory (208px) sits left of the results with a (20px) gutter. Folders, tags and sites have explicit type controls, a search input, counts and a visible Load more action in pages of 50. Search applies to the entire directory, including entries beyond the former 200-item ceiling; exact matches appear first, then prefixes and other literal matches, with stable alphabetical ordering within each group. Long names wrap and retain a native title. The directory has a visible native vertical scrollbar, mouse-wheel scrolling and keyboard-focusable buttons. Below (960px), the same directory is in the filter drawer.

Cards use `repeat(auto-fill, minmax(270px, 1fr))`, (12px) gaps, padding (14px), corners (12px) and content-driven row height. A row aligns its cards without a fixed minimum height or compulsory excerpt. The independently scrolling result list uses padding (3px 4px 8px) above a pagination footer (40px). List view replaces the card grid with ruled rows and persists across reloads.

The final synthetic collection contains 1892 bookmarks and 295 folders. `collection-density.json` in the evidence directory records the following initial unfiltered view; the percentages describe available result-list height, while the last column counts complete cards. All five captures have no horizontal document overflow.

| Viewport | First card top | Result-list height | Viewport share | Complete cards |
| --- | --- | --- | --- | --- |
| 1440 × 960 | 163px | 748px | 77.9% | 16 |
| 1366 × 768 | 163px | 556px | 72.4% | 9 |
| 1280 × 600 | 163px | 388px | 64.7% | 6 |
| 1024 × 749 | 163px | 537px | 71.7% | 6 |
| 390 × 844 | 218.6875px | 580.3125px | 68.8% | 3 |

Selection hides the category directory and contracts the desktop index to (312px), beside a gutter (24px) and flexible reader. Index entries use padding (16px 14px), lower spacing (6px), panel corners and transparent default fill/border; selection restores a blue fill/edge. The toolbar remains (60px), search/control-group basis (680px), search height (40px). No empty reader column is reserved. Opening/returning preserve the real list scroll; choosing a different category/query resets scroll and pagination and closes the old reader.

Reader tabs/actions share a strip (56px). Article width is capped at (780px), including gutters; title padding is (40px 46px 0), body padding (24px 46px 44px), and position footer height (48px). Source lower space is (16px); title lower margin is (14px). Controls remain outside the article scroller.

Focus hides competing chrome, retains the (56px) header, and places the same pane at workspace insets (16px top, 36px sides, 24px bottom). Title top space becomes (35px); hidden results are inert. Focused body reading with more than one real heading shows the outline at widths at least (1120px): grid `minmax(0, 780px) 170px`, gap (32px), maximum width (1080px), horizontal padding (28px), and article gutters (24px). The outline begins at margin-top (40px) and sticks (28px) below the scroller top.

Support pages use maximum width (1050px), top margin (28px), padding (32px 40px 40px), and heading spacing (24px). Desktop model channels are two unboxed ruled columns with gap (40px), each following its own form height. Essential fields lead directly into test action/result, then options. No subgrid or blank row aligns a shorter form's test to the longer form.

| Viewport | Source-defined exceptions |
| --- | --- |
| At least 1600px | Index (328px), reader gutter (56px); collection grid uses all available width. |
| 1120–1300px | Index (292px), reader gutter (36px), workspace sides (28px), selected gap (22px), search-group basis (620px); reader count hides. |
| 960–1119px | Category directory remains visible; workspace sides (20px). Reading opens the full-width modal. |
| 720–959px | Category directory is in the filter drawer; workspace sides (20px), header sides (20px), import is an icon-only (42px) circle. |
| 720–1119px | Browse horizontal gaps (18px); selected collection behind modal has (18px) gaps. Full-width reader return/actions row (60px), tabs (56px), no sheet shadow. Support padding (32px); model columns stack with gap (16px). |
| At most 719px | Header (56px), workspace sides (12px), bottom (8px), navigation/utilities in drawer. Toolbar padding (12px 0), gap (10px), title then search; search controls `minmax(0, 1fr) 44px 68px`, search height (44px). One card column, padding (14px), corners (12px). Article gutter (24px), body top space (20px), reader footer (52px). Support margin-top (16px), padding (24px 20px); form actions stack. |

The square-edged modal reader fills the viewport. Its tab strip remains (56px) on mobile; tablet pills are (36px), mobile pills (44px). Mobile search hides the shortcut hint. Import retains padding (48px 24px). Main mobile controls reach at least (44px); article tags and suggestion-menu retry retain compact exceptions.

## Elevation & Depth

Collection cards are flat, separated by white fill and a fine border. Hover changes their border; compact index hover becomes white. Elevation belongs to larger reading/support surfaces and temporary overlays. There is no backdrop blur.

- **Empty collection / active utility toggle:** `var(--card-shadow)`; light `0 2px 8px #244e6709, 0 8px 24px #244e6706`, dark `0 3px 14px #00000020`.
- **Reader / support surface:** `var(--sheet-shadow)`; light `0 12px 36px #244e6712`, dark `0 12px 36px #00000028`.
- **Open navigation:** `8px 0 40px #16374a24`; closed navigation has no shadow.
- **Query suggestions:** `0 12px 36px color-mix(in srgb, var(--ink) 16%, transparent)`.

Focus uses a blue outline (2px, offset 3px); result cards use inset offset (-3px), fields (2px), cmdk list (-2px), and chapter links (1px). Search changes its border while retaining white fill.

**The Bounded Depth Rule.** Keep collection cards flat and outlined. Use soft elevation for the reader, support surfaces and temporary overlays; hover changes state without lifting the card.

## Shapes

Open cards and compact index entries use (12px) corners, import targets (16px), reader/support surfaces (20px). Buttons, search, header navigation, reader tabs, category-type controls, filter chips and article tags have true pill ends (999px); category options use (8px) corners, and icon-only actions are circular (50%). Source badges are rounded tiles: (24px) with (8px) corners in cards, (22px) with (7px) corners in the index.

Fields, notices, diagnostics and session rows retain (10px); brand tile (11px); apply/consent/stage panels (12px). Query popup corners are (14px), suggestion rows (10px), category icons circular (30px), and keyboard hints (4px). Chapter links use (4px) corners and a current marker (2px by 16px). The modal reader remains a square full-viewport exception.

Collection-management dialogs extend this system with pill-shaped inputs and selects,
20px dialog corners, the existing semantic colors and an explicit muted placeholder.
These scoped form shapes do not replace the incumbent model-setting field tokens.

Lucide SVGs provide stroke icons and the layered brand mark. Source initials identify pages. The open arrow appears on hover/keyboard focus; selected entries show Reading in its place. No selection-edge stripe or decorative imagery is introduced.

## Components

### Buttons, navigation and fields

Primary/secondary form pills use minimum height (40px); collection-toolbar pills use (36px) with (6px 12px) padding and (12px) labels. All main mobile actions remain at least (44px). Form pills use weight (600), gap (8px), icons (16px) and frontmatter padding. Import/Filters use minimum height (42px); general icon circles (36px), pagination (38px). Primary/import hover uses `brightness(0.94)`; secondary uses Lake Mist, blue text and Selected Edge. Text pills use Lake Mist hover and minimum height (32px). Disabled buttons use opacity (0.42).

Header navigation has tray padding/gap (4px), segment padding (8px 17px), minimum height (36px). Active navigation uses Lake Mist, blue text and weight (700), with no underline/shadow. The utility group is transparent with white raised active toggles. Filters open temporary modal navigation at every width with keyboard handling and return focus.

Model inputs are at least (46px) high, with label gap (9px), model-field spacing (16px), shared-field spacing elsewhere (20px). Cool Inset becomes white on focus with an accent border/outline; disabled type is muted. Reader Focus is a labeled pill with Lake Mist pressed state. Main mobile actions, navigation/filter/folder targets, return, checkbox labels, setup steps and section selector are at least (44px); icon, pagination and search clear are (44px) circles.

### Search and complete category navigation

Ctrl/Cmd+K accesses persistent search. Browsing and selected reading both use a (40px) desktop search capsule. Category selection uses the searchable vertical directory described above, with selected blue fill and explicit counts. All folders clears the folder dimension while preserving other active dimensions, which remain visible as removable filter chips.

Query/category/page changes associate results with their exact context. During a new request or its failure, rows from the old context are not exposed for selection, bulk actions or scoped export. Repeating the active category preserves its in-flight request; repeated Enter and IME completion start a replacement search when needed. Category loading, no-match and failure/retry states are separate. Query changes reset list/page/reader; opening and returning from the same result preserve them.

The query trigger is a (40px) circle, (44px) on mobile. Its cmdk-powered popup opens below at offset (10px), width `min(368px, calc(100vw - 36px))`, padding (16px 8px 0), and popup corners. Suggestion rows have minimum height (58px), padding (10px), category icon, label/detail and selected Enter cue. Lake Mist identifies selection. The list scrolls within `min(348px, 48dvh)`; mobile popup right offset is (-76px).

The menu uses at most six returned suggestions, preserves syntax and quotes multiword values. Opening focuses the list; arrows/Enter use cmdk selection, Escape returns to the trigger, and leaving closes the menu. Loading, empty and failure content remain distinct; retry is a compact contextual action (minimum 32px). This is a search-suggestion menu, not a global action launcher.

### Collection and reader

Cards begin with a (24px) source badge/domain, then title, optional excerpt and quiet folder/date metadata. Content gap is (6px); metadata margin-top (4px), with no extra footer rule or padding. Open arrows transition from x (-4px)/opacity (0) to visible on hover/focus. Selection exposes `aria-pressed` and Reading. Index content gap is (6px), with smaller typography and no footer rule. ArrowUp/ArrowDown selects adjacent entries; opening/returning preserve query, filters, page, position and originating focus.

Reader tab pills are (36px) with padding (0 13px), gap (4px), and a moving marker at top (10px). Mobile pills/marker are (44px), marker top (6px). One active tab stop, arrow/Home/End navigation and linked panels preserve keyboard access. Previous/next, Focus and close share the desktop strip; narrow reading exposes Back to collection.

The original-page link is an inset pill above the title; saved folder/tags/search context use an on-demand pill disclosure with rotating chevron. Body, summary and related content retain distinct loading/missing/failure states. Tab positions persist per bookmark and reset on a new one. Exact duplicated first-title paragraphs are omitted; only explicit Markdown headings become sections.

The Rare UI RailToc adaptation appears only for successfully loaded, focused body reading with more than one actual heading, at desktop widths. The sticky (170px) rail has wrapping (12px) labels, minimum link height (36px), a fine vertical rule and blue current marker. Clicks scroll only the article container with offset (28px). Real heading measurements, font readiness and resize updates drive tracking; the rail scrolls internally to keep the active link visible. Preserve its attribution in THIRD_PARTY_NOTICES.md.

The separate position footer measures actual saved-body scroll extent and retains its native section picker; unavailable body/other tabs have no fabricated percentage. Focus preserves the pane and prior split-view article position. Escape restores split view before closing; Radix supplies narrow-reader modality/focus handling.

### Support panels and motion

Each model channel renders essential fields, its test/result, then optional settings. Deep-ink headings use blue role icons. Tests have margin-top (12px) with no separator; options have margin-top (22px), padding-top (12px), and a fine upper rule. Checkbox labels are at least (40px) with (17px) controls, (44px) labels on mobile. Setup steps remain pills; apply/consent/stage panels outlined; import uses a dashed edge on Lake Mist. Configured, tested, indexed and applied states remain distinct.

CSS owns general icon/search changes (150ms), suggestions and chapter-link/marker changes (160ms), primary/secondary/card/header/folder/disclosure states (180ms), and navigation translation (220ms), using `cubic-bezier(0.22, 1, 0.36, 1)`. The card arrow animates opacity/translation; cards have no entrance stagger or lift. Busy spinners rotate over (1.1s linear).

GSAP owns tab-marker x/width (180ms, `power3.out`, overwrite `auto`) and interruptible focus-pane x/y (220ms), clearing transforms on completion. Motion owns modal-reader x (220ms), transparent-overlay opacity (180ms), and measured progress scale with spring stiffness (180), damping (35), mass (0.25). Reduced motion disables CSS transitions/animations, makes GSAP/drawer changes immediate, uses direct progress and automatic scrolling, including chapter navigation.

## Do's and Don'ts

### Do:

- Do prioritize visible bookmarks with a compact toolbar and complete, mouse-accessible category directory.
- Do preserve source-first card order and content-driven row heights without compulsory excerpt space.
- Do use true pill controls and circular icon actions while retaining card, reader and field exceptions.
- Do keep the index subordinate and preserve query, filters, pagination, collection position and return focus.
- Do keep persistent reader navigation and progress controls outside the article scroller and show the focus rail only for real headings. Contextual bookmark editing and processing actions follow the article information inside the scroller.
- Do place each model test after essential fields, with options below.
- Do provide a visible Back to collection control in the full-width narrow reader.
- Do preserve semantic themes, keyboard access, reduced motion and distinct recovery states.

### Don't:

- Don't restore the rejected grey-violet palette or permanent three-column management shell.
- Don't impose fixed card heights, hide category access in horizontal gestures, or fill missing excerpts with decorative content.
- Don't apply the open collection's card treatment to every supporting index row.
- Don't replace Facetmark identity with hand-drawn borders, gradients or a candy-colored dashboard.
- Don't let GSAP, Motion and CSS animate the same property on the same element.
- Don't invent folder categories, headings, reading percentages or successful task states.
