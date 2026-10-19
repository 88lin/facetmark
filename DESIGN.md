---
name: Facetmark capsule workspace
description: A neutral collection canvas with one searchable sidebar, indigo selection, real HeroUI capsule controls
  and interruptible GSAP composition.
colors:
  secondary-ink: '#555d6b'
  canvas: '#ffffff'
  desk: '#f4f5f8'
  rail: '#fbfbfd'
  inset: '#f1f2f6'
  ink: '#232631'
  muted: '#687080'
  rule: '#e7e9ef'
  accent: '#5c4ddb'
  soft: '#efedff'
  selected: '#e9e5ff'
  selected-edge: '#c2bafa'
  selection-neutral: '#eeedf7'
  on-accent: '#fff'
  danger: '#b13e52'
  scrim: '#181b304f'
  secondary-ink-dark: '#c5c8d4'
  desk-dark: '#15161c'
  canvas-dark: '#202129'
  rail-dark: '#1a1b23'
  inset-dark: '#2a2b36'
  ink-dark: '#f0f1f6'
  muted-dark: '#a7adbd'
  rule-dark: '#333642'
  accent-dark: '#b3a6ff'
  soft-dark: '#302b47'
  selected-dark: '#3a3158'
  selected-edge-dark: '#756597'
  selection-neutral-dark: '#33303e'
  on-accent-dark: '#302047'
  danger-dark: '#f7a0ae'
  scrim-dark: '#06070a99'
typography:
  workspace-title:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 1.75rem
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: -0.015em
  section-title:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 1.125rem
    fontWeight: 550
    lineHeight: 1.5
  collection-title:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 1.125rem
    fontWeight: 550
    lineHeight: 1.5
    letterSpacing: -0.01em
  collection-summary:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.6875
  body:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.6
  button:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.9375rem
    fontWeight: 500
    lineHeight: 1.5
  field-label:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.9375rem
    fontWeight: 500
    lineHeight: 1.6
  directory:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.9375rem
    fontWeight: 400
    lineHeight: 1.45
  directory-selected:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.9375rem
    fontWeight: 500
    lineHeight: 1.45
  navigation:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.4
  navigation-active:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.4
  meta:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.8125rem
    fontWeight: 400
    lineHeight: 1.6
  caption:
    fontFamily: '"Facetmark Inter", "Facetmark CJK", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    fontSize: 0.8125rem
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
rounded:
  control: 9999px
  pill: 999px
  circle: 50%
  card: 22px
  menu: 24px
  panel: 28px
  reader: 20px
spacing:
  compact: 8px
  control: 10px
  small: 12px
  content: 16px
  card-padding: 22px
  section: 24px
  dialog-padding: 28px
  panel-top: 32px
  panel-gutter: 40px
  reader-gutter: 44px
components:
  button-primary:
    backgroundColor: '{colors.accent}'
    textColor: '{colors.on-accent}'
    typography: '{typography.button}'
    rounded: '{rounded.control}'
    padding: 10px 20px
    height: 44px
  button-secondary:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.button}'
    rounded: '{rounded.control}'
    padding: 9px 18px
    height: 44px
  button-text:
    textColor: '{colors.accent}'
    typography: '{typography.button}'
    rounded: '{rounded.control}'
    padding: 5px 10px
    height: 32px
  button-icon:
    textColor: '{colors.ink}'
    rounded: '{rounded.circle}'
    height: 36px
    width: 36px
  navigation-item:
    textColor: '{colors.secondary-ink}'
    typography: '{typography.navigation}'
    rounded: '{rounded.control}'
    padding: 8px 10px
    height: 40px
  navigation-item-active:
    backgroundColor: '{colors.selected}'
    textColor: '{colors.accent}'
    typography: '{typography.navigation-active}'
    rounded: '{rounded.control}'
    padding: 8px 10px
    height: 40px
  search-field:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.body}'
    rounded: '{rounded.control}'
    padding: 8px 16px
    height: 46px
  directory-option-selected:
    backgroundColor: '{colors.selected}'
    textColor: '{colors.accent}'
    typography: '{typography.directory-selected}'
    rounded: '{rounded.control}'
    padding: 9px 12px
    height: 40px
  filter-chip:
    backgroundColor: '{colors.soft}'
    textColor: '{colors.accent}'
    typography: '{typography.caption}'
    rounded: '{rounded.control}'
    padding: 4px 10px
    height: 30px
  collection-entry:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.collection-title}'
    rounded: '{rounded.card}'
    padding: 22px
  settings-tab-active:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.accent}'
    typography: '{typography.button}'
    rounded: '{rounded.control}'
    padding: 10px 16px
    height: 42px
  folder-picker-trigger:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.body}'
    rounded: '{rounded.control}'
    padding: 11px 18px
    height: 48px
  folder-picker-option-selected:
    backgroundColor: '{colors.selected}'
    textColor: '{colors.accent}'
    typography: '{typography.button}'
    rounded: '{rounded.control}'
    padding: 10px 16px
    height: 48px
  model-field:
    backgroundColor: '{colors.inset}'
    textColor: '{colors.ink}'
    typography: '{typography.body}'
    rounded: '{rounded.control}'
    padding: 11px 16px
    height: 46px
  support-surface:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    rounded: '{rounded.panel}'
    padding: 32px 40px 40px
    width: min(1120px, 100%)
  library-dialog:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    rounded: '{rounded.menu}'
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

# Design System: Facetmark capsule workspace

## Overview

**Creative North Star: "Fluid capsule workspace"**

Facetmark combines application navigation and searchable categories in one sidebar,
leaving a spacious content canvas for the collection. Neutral white and softly
shaded surfaces carry readable text; indigo identifies actions, focus and selection.
Complete capsule controls, circular icon actions and rounded content surfaces make
the interface tactile without tinting the entire workspace.

This direction follows the user's second 2026-10-19 rejection. The lavender/10px
replacement at `082e36d` is superseded. HeroUI now leads real control construction,
GSAP composes page and section transitions, and Motion retains shared selection,
card reflow and overlay presence. GithubStarsManager informs collection organization;
FlClash informs selection continuity. These are references, not approved mockups.

**Key Characteristics:**

- One sidebar for navigation, searchable categories and supporting utilities.
- Neutral content surfaces with focused indigo action and selection states.
- Bundled Inter and Noto Sans SC with a readable 28/18/16/15/13 type hierarchy.
- Full capsule controls, circular icon buttons and proportional rounded panels.
- HeroUI control states and interruptible, layered GSAP content transitions.
- Immediate state and focus, native semantics and live reduced-motion support.

This document records source `50f89dfc2c454318dca3d4a393717cb3aa2e1a07` and the
subsequent accent-contrast and folder-parent layout corrections in the working tree.
The final correction revision, fresh cloud evidence and independent visual/motion
review remain pending. Historical passes do not establish current acceptance.
Component specimens are source-derived illustrations, not rendered or approval evidence.
The [workbench contract](.impeccable/workbench-direction.md) is the direction authority;
[the surface brief](.impeccable/surfaces/frontend.md) defines acceptance scope.

## Colors

The frontmatter is normative. Base names describe light mode and `-dark` names
its dark counterpart. Sidecar ramps are generated preview swatches, not runtime
palette additions.

### Primary

- **Indigo Action** (`accent`, `on-accent`): primary actions, links, focus and current
  destinations. Dark mode uses a lighter indigo with a dark foreground.
- **Soft Indigo** (`soft`): local hover or supporting emphasis.
- **Selected Indigo** (`selected`, `selected-edge`): shared selection capsules,
  picker choice and selected boundaries. `selection-neutral` remains a separate,
  quieter compatibility token; it is not the primary selected fill.

### Neutral

- **Canvas / Mist Workspace / Sidebar White** (`canvas`, `desk`, `rail`): content,
  surrounding workspace and unified navigation surface.
- **Inset** (`inset`): search groups, fields and recessed control backgrounds.
- **Graphite / Secondary Ink / Muted Ink** (`ink`, `secondary-ink`, `muted`): titles,
  descriptions and supporting metadata.
- **Rule / Scrim** (`rule`, `scrim`): subtle boundaries and modal separation.

`danger` remains reserved for errors and destructive operations.

**The Local Accent Rule.** Keep the workspace neutral. Apply indigo to a meaningful
action, focus or selected state; do not restore the rejected blanket lavender wash.

## Typography

The local `Facetmark Inter` and `Facetmark CJK` aliases load Inter and Noto Sans SC
variable WOFF2 files. Both support weights 100–900 with `font-display: swap`; Segoe
UI and Microsoft YaHei UI provide fallback coverage. Font loading requires no CDN.
Sources, subset coverage and OFL notices are in [the font README](frontend/src/assets/fonts/README.md).

- **Page title:** 28px/600 with 1.3 leading. Compact desktop collection titles use
  24px; mobile collection titles use 20px and support-page headings use 24px.
- **Item and section titles:** 18px/550 with 1.5 leading. Collection titles retain
  two lines in both card and list layouts, including mobile.
- **Summary:** 16px/400 with 27px leading; three collapsed lines on desktop and two
  on mobile. Actual clipping determines whether expansion is offered.
- **Controls and directory:** the main role is 15px, regular for directory names
  and 500 for actions/selected names. Navigation uses a local 14px role, 13px on
  compact desktop; current destinations use 600.
- **Metadata:** 13px regular text with tabular counts where applicable. Use spacing
  and grouping for hierarchy instead of shrinking content metadata to 10–11px.
- **Reader:** article titles 36px/600, 38px in focused composition and 27px narrow;
  article prose 18px/1.85, reducing to 17px on mobile.

Chinese headings and collection titles remove negative tracking. Labels remain
mixed-case as written; do not force uppercase or synthetic condensed typography.

**The Shared Reading Scale Rule.** Preserve the same title and summary hierarchy
when changing card/list layout. Metadata supports the description; it never takes
its place or justifies reducing the readable content scale.

## Layout

The desktop shell has 12px outer padding and a 12px gap. A single 244px sidebar
contains the brand, application navigation, searchable category list and utilities.
At widths 960–1300px it is 224px; at 1600px and above it is 260px. The collection
occupies the remaining canvas. The category list is part of this sidebar, not a
second permanent column beside a narrow rail.

A 76px workspace row aligns the destination title and 46px capsule search. Below
it, maintenance actions, layout choice, status/sort/display and removable filters
keep separate responsibilities. The grid starts at a 280px minimum card width
with 16px gaps, changes to 268px on compact desktop and 320px on wide desktop.
List mode uses 10px gaps and a 240px metadata/action area. Card padding is 22px;
list padding is 16px 20px. Result and directory scrollers remain bounded.

Below 960px the sidebar becomes a 56px horizontal header and the directory opens
in the focus-managed drawer. Below 720px the title/search stack, results become
one column, cards retain 22px corners with 16px padding and principal actions use
44px targets. Short desktop windows compact sidebar spacing and navigation heights.
Keep full directory access and utilities reachable at those sizes.

Opening desktop preview adds a 304px collection index beside the reader; wide
layouts use 332px. The unified sidebar retains its location. Focus mode expands
the reader within the content area. At widths below 1120px preview uses the modal
composition; mobile preview fills the viewport. The real article scroller and
clearance above the floating reading control remain intact.

Support pages use a canvas panel up to 1120px wide with 32px 40px 40px padding.
Below 960px padding becomes 24px; below 720px it is 18px 14px 28px with 24px corners.
Connection fields remain grouped with their test/save controls and feedback.

## Elevation & Depth

Use a light card shadow for content and support panels, stronger local elevation
for menus, dialogs and the reader, and soft action shadows for primary/secondary
capsules. Selected collection cards keep the canvas fill with an accent boundary
and inset ring. Hover strengthens the edge and elevation. Exact shadows and
material values live in the sidecar. The reading capsule alone keeps its bounded
glass effect with an opaque fallback and reduced-transparency override.

**The Immediate State Rule.** State, data and focus never wait for an animation.
One engine owns each animated property on an element. Closing overlays become
inert and noninteractive while their visual exit finishes.

## Shapes

Buttons, disclosure summaries, single-line inputs, native selects and segmented
choices use complete capsule ends (9999px). Square icon controls become circles.
Checkboxes/radios keep their native forms; textareas and floating menus use 24px
corners. Cards use 22px, the unified sidebar and support panels 28px, library dialogs
24px and the reader sheet 20px. The reading capsule retains its 999px pill token.

The final application cascade enforces capsule controls even when earlier
component rules contain smaller radii. Preserve proportional surface corners
instead of applying a pill outline to large content panels.

## Components

### HeroUI controls and inputs

`@heroui/react` and `@heroui/styles` are pinned to 3.2.6. Official granular imports
load base, default theme, utilities, variants and Button/Input styles, keeping the
real controls without unrelated component styles. Final bundle size and build
time remain subject to the new cloud build.

The shared `CapsuleButton` wraps HeroUI Button; folder/model search uses HeroUI
Input. HeroUI supplies press/focus state. The wrapper retains a native button and
its click `currentTarget`. Application key handlers run first; unhandled keys then
reach HeroUI. A ref records whether HeroUI prevented the Enter/Space default, and
only that case supplements a keyboard press with one real DOM click for
`type="button"`. Submit/reset keep browser form activation. This conditional bridge
preserves platforms where Enter already produces a native click. Pending/disabled
controls block activation; verify click counts, keyboard behavior and submission.

The shipped [HeroUI notice](frontend/public/licenses/HeroUI.txt) contains Apache 2.0
terms, and Settings credits HeroUI alongside Rare UI. Retain both the notice and
visible credit when changing the integration.

Primary actions use indigo/on-accent; secondary actions use a canvas capsule and
fine boundary; text actions use a quiet transparent capsule. Main controls use
15px/500 labels and the 44px shared height. Source-specific toolbar and navigation
controls retain their documented compact heights. Native fallback CSS press scaling
excludes HeroUI `.button` elements and `data-overlay-motion` controls. The global `.fm-button` reduced-motion rule also removes press transform from
portaled dialog controls when the preference changes.

### Unified sidebar and selection

Application destinations stack as full-width capsules in the desktop sidebar.
Utility actions use 40px circular icons with accessible labels and tooltips. Category
types use text-only segmented capsules so English labels fit the compact sidebar.
These controls share the sidebar with search and the vertically scrollable category
list; the narrow header remains horizontal.
Directory options retain full accessible paths, pagination, counts and explicit
selected state. Parent paths occupy their own line beneath folder leaf names. Selection capsules use independent Motion layout groups so each
control group moves its own indicator. Semantic current/pressed/selected state
belongs to the actual control.

### Collection cards and list rows

Source, title, visible description, folder and actions form the content hierarchy.
A 13px provenance label leads the summary; the accessible expansion action sits as
an icon in the card footer and still depends on measured clipping. Original links stay native anchors; selection, editing, summary actions and Preview
remain independent. Selected/batch-selected cards preserve their canvas background.
Motion owns card entry and position reflow; CSS owns hover borders and shadows.
Measured clipping controls expansion, and changes to data context must preserve
correct selection, focus and paging semantics.

### Folder/model choice and settings

Folder and model pickers use capsule triggers, 24px floating panels and capsule
search/options. Selected options use indigo text, selected fill and an inset edge.
Folder pages load 50 items; model rendering starts at 100 items with explicit more.
Search drafts do not commit a folder/model choice. Unfiled, defaults, manual entry,
new paths, loading, retry and unavailable choices remain explicit.

Settings use capsule tabs with a moving selected surface. Hidden panels stay
mounted to preserve drafts and results. Keep Agent identity, catalog source,
selected model, tested state, saved state and actual summary use distinct. Optional
embedding has its own state. Scope review and content-processing consent stay in
the processing dialog; task recovery retains its original durable snapshot.

### Content and control motion

`InteractionMotion.tsx` uses GSAP 3.13.0 with `@gsap/react` 2.1.2. Named heading and
content timeline positions separate their arrival by 40ms. Page, settings-section,
category, pagination and filter changes use different directional recipes; rapid
reversal resumes from captured painted values. `useGSAP` scopes cleanup, removes
temporary transform/opacity/filter/will-change values and responds to live reduced
motion. Settings page arrival targets the inner body while the section hook owns
the panel, avoiding a shared transform owner.

Motion 12.23.24 owns selection capsules (stiffness 480, damping 29, mass .8),
card position/entry and overlay presence. The portal ink is a noninteractive paint
layer, cleared on scrolling or resize; its higher-specificity CSS uses a 480ms
capsule ripple. Theme reveal remains an interruptible 460ms circular View Transition
from the activating control, with immediate fallback. The application explicitly
restores `view-transition-name: root` after HeroUI base styles so the root snapshot
remains available to the circle reveal. Detailed values are in the
sidecar and [UI motion tools](docs/ui-motion-tools.md); static specimens do not
implement those runtime engines.

### Reading

The reader retains the Rare UI-derived glass progress capsule, native chapter
selector and measured paper-plane outline. Progress and headings come from saved
article content. GSAP owns reader focus translation and tab-marker geometry;
Motion owns reader presence, progress and outline springs. Retain final-text
clearance, container-local scrolling and focus return. Rare UI notices and visible
attribution remain required by the shipped license.

## Do's and Don'ts

### Do:

- Do keep application navigation and searchable categories in one sidebar.
- Do use complete capsules for controls and circles for icon-only actions.
- Do preserve the bundled fonts and shared 28/18/16/15/13 content hierarchy.
- Do retain native links, button/form semantics and explicit selection states.
- Do keep search drafts, Agent drafts, task snapshots and processing consent intact.
- Do give each animated property one owner and clean up interrupted timelines.
- Do verify rapid switching, keyboard activation and live reduced motion.
- Do inspect fresh Web and installed Windows captures and continuous interactions.

### Don't:

- Don't restore the rejected lavender wash, 10px controls or split rail/category layout.
- Don't reduce readable metadata to 10–11px or make summaries visually secondary to it.
- Don't let a control library change native click, keyboard or form behavior unnoticed.
- Don't make data or focus wait for decorative motion.
- Don't infer account access, saved configuration or completed work from discovery alone.
- Don't reuse historical green runs, specimens or reviewer verdicts as current visual approval.
