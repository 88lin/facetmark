---
name: Facetmark tonal collection workbench
description: A Material-inspired collection workspace with a stable navigation rail, separate directory, bundled
  Latin and Chinese fonts, and visible interaction continuity.
colors:
  secondary-ink: '#585361'
  canvas: '#ffffff'
  desk: '#f5f2fa'
  rail: '#ece6f4'
  inset: '#f0edf5'
  ink: '#292431'
  muted: '#716a7d'
  rule: '#e4deeb'
  accent: '#7252ad'
  soft: '#f0e9fa'
  selected: '#e6daf6'
  selected-edge: '#b9a4d5'
  selection-neutral: '#e6daf6'
  on-accent: '#fff'
  danger: '#b13e52'
  overlay: '#24182d66'
  secondary-ink-dark: '#cec6d9'
  desk-dark: '#1b1821'
  canvas-dark: '#25212c'
  rail-dark: '#201b29'
  inset-dark: '#312b3b'
  ink-dark: '#f0eaf7'
  muted-dark: '#b3a9c0'
  rule-dark: '#3c3448'
  accent-dark: '#cfb4ff'
  soft-dark: '#382c4d'
  selected-dark: '#483463'
  selected-edge-dark: '#82649f'
  selection-neutral-dark: '#483463'
  on-accent-dark: '#302047'
  danger-dark: '#f7a0ae'
  overlay-dark: '#06070a99'
typography:
  workspace-title:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 1.5rem
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: -0.025em
  section-title:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 1.125rem
    fontWeight: 600
    lineHeight: 1.5
  collection-title:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 1rem
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: -0.015em
  collection-summary:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.9375rem
    fontWeight: 400
    lineHeight: 1.7
  body:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.6
  button:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.875rem
    fontWeight: 500
    lineHeight: 1.5
  field-label:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.875rem
    fontWeight: 600
    lineHeight: 1.6
  directory:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.45
  directory-selected:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.875rem
    fontWeight: 600
    lineHeight: 1.45
  navigation:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.75rem
    fontWeight: 500
    lineHeight: 1.35
  meta:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.8125rem
    fontWeight: 400
    lineHeight: 1.6
  caption:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.75rem
    fontWeight: 400
    lineHeight: 1.6
  article-title:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 36px
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: -0.025em
  reading:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 1.125rem
    fontWeight: 400
    lineHeight: 1.85
  navigation-active:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.75rem
    fontWeight: 600
    lineHeight: 1.35
rounded:
  small: 8px
  status: 9px
  control: 10px
  search: 14px
  card: 16px
  navigation: 18px
  reader: 20px
  sheet: 24px
  pill: 999px
  circle: 50%
spacing:
  compact: 8px
  control: 10px
  small: 12px
  grid-gap: 14px
  card-padding: 18px
  content: 20px
  section: 24px
  dialog-padding: 28px
  page-gutter: 36px
  reader-gutter: 44px
components:
  button-primary:
    backgroundColor: '{colors.accent}'
    textColor: '{colors.on-accent}'
    typography: '{typography.button}'
    rounded: '{rounded.control}'
    padding: 10px 20px
    height: 40px
  button-secondary:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.button}'
    rounded: '{rounded.control}'
    padding: 9px 18px
    height: 40px
  button-text:
    textColor: '{colors.accent}'
    typography: '{typography.button}'
    rounded: '{rounded.small}'
    padding: 5px 10px
    height: 32px
  button-icon:
    textColor: '{colors.ink}'
    rounded: '{rounded.circle}'
    width: 36px
    height: 36px
  navigation-item:
    textColor: '{colors.secondary-ink}'
    typography: '{typography.navigation}'
    rounded: '{rounded.navigation}'
    padding: 10px 4px
    height: 66px
  navigation-item-active:
    backgroundColor: '{colors.selected}'
    textColor: '{colors.accent}'
    typography: '{typography.navigation-active}'
    rounded: '{rounded.navigation}'
    padding: 10px 4px
    height: 66px
  search-field:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.body}'
    rounded: '{rounded.search}'
    padding: 8px 14px
    height: 44px
  directory-option-selected:
    backgroundColor: '{colors.selected}'
    textColor: '{colors.accent}'
    typography: '{typography.directory-selected}'
    rounded: '{rounded.control}'
    padding: 9px 10px
    height: 40px
  filter-chip:
    backgroundColor: '{colors.soft}'
    textColor: '{colors.accent}'
    typography: '{typography.caption}'
    rounded: '{rounded.small}'
    padding: 4px 10px
    height: 30px
  collection-entry:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.collection-title}'
    rounded: '{rounded.card}'
    padding: 18px
  settings-tab-active:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.accent}'
    typography: '{typography.button}'
    rounded: '{rounded.control}'
    padding: 10px 16px
    height: 42px
  folder-picker-trigger:
    backgroundColor: '{colors.inset}'
    textColor: '{colors.ink}'
    typography: '{typography.directory}'
    rounded: '{rounded.control}'
    padding: 11px 14px
    height: 48px
  folder-picker-option-selected:
    backgroundColor: '{colors.selection-neutral}'
    textColor: '{colors.ink}'
    typography: '{typography.directory-selected}'
    rounded: '{rounded.control}'
    padding: 10px 12px
    height: 48px
  model-field:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.body}'
    rounded: '{rounded.control}'
    padding: 9px 12px
    height: 44px
  support-surface:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    rounded: '{rounded.sheet}'
    padding: 28px 36px 36px
    width: min(1080px, 100%)
  library-dialog:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    rounded: '{rounded.sheet}'
    padding: 28px
    width: min(560px, calc(100vw - 32px))
  reading-sheet:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    rounded: '{rounded.reader}'
  reading-position-surface:
    textColor: '{colors.secondary-ink}'
    rounded: '{rounded.pill}'
    padding: 8px 12px 10px 18px
    height: 56px
---

# Design System: Facetmark tonal collection workbench

## Overview

**Creative North Star: "Tonal collection workbench"**

Facetmark uses a stable application rail, a separate collection directory and a
flexible content area. Pale lavender surfaces, white content cards, deep plum text
and violet selection create a Material-inspired hierarchy. Bundled Inter and Noto
Sans SC keep Latin and Chinese text consistent across desktop and Web.

The 2026-10-19 replacement changes composition, typography, component shape and
interaction feedback together. It supersedes the rejected 10/18 blue-grey system.
Navigation, classification, settings tabs, content changes and overlays now show
visible continuity; original links, processing scope and saved task state retain
their independent semantics. The reference projects informed the implementation,
not a user-approved pixel comp.

**Key Characteristics:**

- Stable application navigation and a separate searchable collection directory.
- Tonal surfaces with violet selected state and readable plum text.
- Local Latin and Chinese variable fonts; compact titles and visible summaries.
- Small rounded controls, rounded cards and larger modal surfaces.
- Immediate actions with bounded press, ink, selection and content feedback.
- Live reduced-motion handling, keyboard access and truthful application state.

This source-derived system was recorded against `ac90d24805e346ba974a197da72a59cdac11231f`.
Cloud checks and a fresh visual/motion review are pending for the replacement.
The sidecar contains source specimens, not screenshots or approval evidence.
See [the surface brief](.impeccable/surfaces/frontend.md) for acceptance scope and
[PR #44 checks](https://github.com/88lin/facetmark/pull/44/checks) for run status.

## Colors

The frontmatter is normative; base names are light-theme roles and `-dark` names
are their dark-theme counterparts. Sidecar ramps are generated preview swatches,
not extra runtime tokens.

### Primary

- **Violet Action** (`accent`, `on-accent`): explicit actions, links, active navigation
  and focus; dark mode uses a brighter violet with a dark on-accent foreground.
- **Soft Violet** (`soft`): hover and quiet supporting emphasis.
- **Selected Violet** (`selected`, `selected-edge`): moving selection surfaces,
  directory state and boundaries. The compatibility name `selection-neutral` maps
  to this same tonal selection family; it no longer describes a neutral-grey fill.

### Neutral

- **Canvas / Lavender Workspace / Tonal Rail** (`canvas`, `desk`, `rail`): content,
  surrounding workspace and navigation/group surfaces respectively.
- **Inset** (`inset`): secondary fields and recessed content.
- **Plum Ink / Secondary Ink / Muted Ink** (`ink`, `secondary-ink`, `muted`): title,
  summary and metadata hierarchy. Dark counterparts retain the same roles.
- **Rule / Scrim** (`rule`, `overlay`): boundaries and modal separation.

`danger` remains reserved for failures and destructive operations.

**The Tonal Selection Rule.** Keep ordinary content on its canvas. Selection is
expressed through a moving tonal surface, an explicit mark or an accent boundary;
text and semantics must identify the same selected item.

## Typography

Use the bundled `Facetmark Inter` and `Facetmark CJK` families, backed by Inter and
Noto Sans SC variable WOFF2 files. Segoe UI and Microsoft YaHei UI are fallback
coverage. The font files use `font-display: swap`, support weights 100–900 and
require no external font service. Sources, subsets and OFL notices are recorded in
[the font README](frontend/src/assets/fonts/README.md).

- **Workspace titles:** the 24px/600 title role; compact desktop uses 22px and
  mobile collection headings use 20px. Support-page headings remain 24px.
- **Collection titles:** 16px/600 in both card and list views, with two visible
  lines; Chinese titles remove negative tracking.
- **Summaries:** 15px/400 with 1.7 leading and three collapsed lines. At widths up
  to 719px, use 1.65 leading and two lines; measured expansion reveals the rest.
- **Controls:** 14px/500 for main actions; labels use 600 when needed. Principal
  inputs and global body retain 16px. Navigation labels are 12px below their icons.
- **Metadata:** 13px and 12px roles; small directory counts and parent paths have
  local 11px treatments. Counts use tabular numerals where observed.
- **Reader:** article titles use 36px/600, focused titles 38px; body prose uses
  18px with 1.85 leading, reducing to 17px on mobile. Narrow article titles use 27px.

**The Shared Collection Scale Rule.** Card/list switching preserves the title and
summary hierarchy. Expansion depends on measured clipping, not a guessed character
count; smaller metadata must not replace the visible summary.

## Layout

The desktop rail is 96px wide. The collection directory is 13.5rem beside the
results, with a 24px gutter. An 80px workspace row holds the title and 44px search.
The next rows contain maintenance actions, card/list switching, summary status,
sorting and display preferences. Filters remain a separate removable-chip row.

At widths 960–1300px, the rail becomes 84px, the directory 200px and the gutter
18px. At 1600px and above, directory/index widths become 232px/332px. Below 960px,
the rail becomes a 56px horizontal header and the directory moves to the existing
focus-managed drawer. Below 720px, title and search stack, header utilities move
out of the first row, and principal actions retain at least 44px height.

Cards use an auto-fill grid with a 288px minimum and 14px gaps; compact desktop
uses 270px and wide desktop 310px. List view uses one column with 10px gaps and a
210px metadata/action area. Mobile uses a single content column. Default card
padding is 18px; list padding is 16px 20px; mobile cards use 14px. Card heights follow
content. Results and the complete directory have independent bounded scrollers.

Support pages use a canvas surface up to 1080px wide with a 24px top margin and
28px 36px 36px padding. At 719px and below they use an 8px top margin, 18px corners
and 18px 14px 28px padding. Connection fields retain two columns until their
responsive breakpoint, then one; model choice and feedback span the section.

Opening a desktop preview replaces the directory with a compact index beside the
reader. Its header is 56px and tabs 48px. Focus mode expands the reader inside the
workspace while retaining application navigation. Narrow preview is a modal;
mobile preview fills the viewport. The floating reading control reserves clearance
below the article. Its outline is available beside the wide focused reader only.

## Elevation & Depth

Tonal separation provides the resting hierarchy. Cards carry the small card shadow,
and hover strengthens the edge and soft elevation. Selected and batch-selected
cards keep canvas fill with an accent border and inset ring. Support pages are flat
canvas surfaces; reader, menus and dialogs use the sheet shadow. The reading capsule
alone retains its bounded glass treatment with an opaque fallback. Exact shadows,
material values and animation parameters live in the sidecar.

**The Stable Target Rule.** Feedback may animate a paint layer, indicator or content
container, but focus, selection and data changes never wait for animation. Closing
overlays become inert and noninteractive while their visual exit completes.

## Shapes

The shared control radius is 10px, with 8–9px smaller tabs/chips/status controls,
14px search fields and menus, 16px cards, 18px rail targets, 24px support/dialog
surfaces and a 20px reader. Folder-picker panels use 16px corners. Circular icon
actions remain component-specific. The 999px pill token remains for the reading
capsule and reader tabs; it is not the default shape for all application controls.

## Components

### Navigation and selection groups

Rail items stack a 22px icon and 12px label inside a 66px target. Low-height desktop
windows compact the targets to 54px. Selected items use a shared Motion selection
surface. The same pattern connects directory types/options, summary status,
card/list controls and settings tabs, with separate layout groups per control set.
The semantic pressed/current/selected state belongs to the actual control.

### Buttons, chips and search

Primary and secondary buttons use 10px corners and 14px/500 labels. Collection
maintenance controls use 38px height with 8px 12px padding; mobile uses 44px.
Text actions and filter chips use smaller corners. Search uses a 44px white field,
14px corners and a fine focus boundary. Category search remains local to the
directory. Query suggestions keep loading, retry, no-match and keyboard behavior.

CSS press feedback scales ordinary buttons to .965 and directory options to .98;
a noninteractive ink layer acknowledges primary-pointer and Enter/Space actions.
Disabled or inert targets do not produce ink. Focus rings remain visible.

### Collection cards and list rows

Source identity, title, description, folder and actions form a stable sequence.
Original links, checkboxes, direct editing, summary actions and Preview remain
independent. Selected cards use an edge/ring rather than a full tinted body.
Motion owns card position reflow and bounded entry; CSS owns hover and border state.

### Folder and model pickers

Folder triggers are 48px high; their 16px panel contains search and a bounded
option list. Options use 10px corners, tonal selection, a check and an inset edge;
leaf names lead with parent paths beneath. The complete directory loads in 50-item
pages. Typing changes only the search draft; choosing an exact folder commits the
field. Unfiled and new folders are explicit choices. New paths are created on save.
Arrow keys, Home/End, Escape, native button activation and focus return remain.

Model choice remains next to essential configuration, test/save and actionable
feedback. Preserve Agent defaults, catalog provenance, manual entry, refresh,
per-Agent drafts and independent embedding state. A catalog does not prove access;
a passed test does not prove a failed save persisted. Both picker menus use the
shared overlay entrance/exit treatment, and closing content becomes inert.

### Dialogs, settings and task recovery

Library dialogs use a 24px surface, 28px padding and width bounded to 560px. Settings
use rounded tabs with a moving selected surface and an animated incoming panel;
hidden panels remain mounted to preserve drafts. Scope review and consent remain
in the processing dialog. Task recovery retains its original snapshot and completed
entries; displayed scope and state must match the operation. Feedback stays next
to its initiating control.

### Reading and application motion

The reader retains the Rare UI-derived glass position capsule, native chapter
selector, animated chapter label and measured paper-plane outline. Progress and
headings derive from saved article content. GSAP continues to own reader focus
translation and tab-marker geometry. Motion owns reader presence, progress and
outline springs. These effects remain part of the reader rather than the sole
interaction feedback in the application.

`InteractionMotion.tsx` owns shared selection surfaces and WAAPI content entry
for navigation, classification and loaded result contexts. Theme changes use an
interruptible circular View Transition from the clicked control, with immediate
fallback when unsupported or reduced motion is active. `OverlayMotion` owns menu,
dialog and scrim presence; native details menus retain their CSS path. Live reduced
motion disables ink, travel and reflow while preserving state and all controls.
Detailed ownership and timings are in [UI motion tools](docs/ui-motion-tools.md).

## Do's and Don'ts

### Do:

- Do keep the navigation rail, directory and content responsibilities distinct.
- Do use the bundled Latin and Chinese font families and shared collection scale.
- Do retain explicit pressed/current/selected semantics beside visual feedback.
- Do preserve full directory pagination, exact folder choice and separate search drafts.
- Do keep original links, checkboxes, editing and optional preview independent.
- Do preserve processing consent, exact task snapshots and truthful recovery state.
- Do keep animations interruptible and respect the live reduced-motion preference.
- Do verify both static composition and actual click sequences in GitHub Actions.

### Don't:

- Don't restore the rejected 10/18 composition, blue-grey palette or system-font-only direction.
- Don't apply the reader's pill shape to every navigation, input and action.
- Don't make content, focus or data updates wait for a decorative transition.
- Don't let CSS, GSAP, Motion or WAAPI own the same animated property on the same element.
- Don't broaden a task-specific retry or mistake model discovery for successful access.
- Don't present reference screenshots, source specimens or historical runs as current visual approval.
