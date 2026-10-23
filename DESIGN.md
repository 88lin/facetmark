---
name: "Facetmark collection workspace"
description: "Mist-blue workspace refinement after positive feedback; current changes await cloud verification and user review."
colors:
  secondary-ink: "#526379"
  canvas: "#ffffff"
  desk: "#e9eff5"
  rail: "#f3f7fc"
  inset: "#edf3f9"
  ink: "#162b43"
  muted: "#62748a"
  rule: "#d9e3ef"
  accent: "#235fe5"
  accent-hover: "#164bc2"
  soft: "#e8f0ff"
  selected: "#deebff"
  selected-edge: "#8baef3"
  selection-neutral: "#e7eef7"
  glass: "#ffffffb3"
  glass-edge: "#ffffffd9"
  light: "#ffffff"
  ambient-blue: "#83b9fa50"
  ambient-mint: "#b6e4e748"
  on-accent: "#fff"
  danger: "#b73754"
  danger-soft: "#fff0f3"
  success: "#237564"
  success-soft: "#eaf5f1"
  warning: "#88651e"
  warning-soft: "#fff5dc"
  brand-detail: "#7ac5ff"
  scrim: "#172a4861"
  secondary-ink-dark: "#b7c8df"
  canvas-dark: "#152236"
  desk-dark: "#0c1420"
  rail-dark: "#152438"
  inset-dark: "#1c2e46"
  ink-dark: "#eff6ff"
  muted-dark: "#9dafc8"
  rule-dark: "#304561"
  accent-dark: "#92bcff"
  accent-hover-dark: "#b3d1ff"
  soft-dark: "#213c61"
  selected-dark: "#294b78"
  selected-edge-dark: "#688cbd"
  selection-neutral-dark: "#233a54"
  glass-dark: "#142237c9"
  glass-edge-dark: "#7195bf33"
  light-dark: "#cce2ff"
  ambient-blue-dark: "#2869b529"
  ambient-mint-dark: "#326c7930"
  on-accent-dark: "#10223d"
  danger-dark: "#ffa6bc"
  danger-soft-dark: "#412635"
  success-dark: "#9bd7c9"
  success-soft-dark: "#233c38"
  warning-dark: "#ebca8c"
  warning-soft-dark: "#3c3221"
  brand-detail-dark: "#89d9f9"
  scrim-dark: "#06070a99"
typography:
  display:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", sans-serif"
    fontSize: "2rem"
    fontWeight: 750
    lineHeight: 1.35
    letterSpacing: "0"
  title:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "1.1875rem"
    fontWeight: 680
    lineHeight: 1.6
    letterSpacing: "0"
  body:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  summary:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.8
  control:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.5
  source:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.6
  tag:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
  reader-title:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "36px"
    fontWeight: 600
    lineHeight: 1.4
  reading:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.85
rounded:
  control: "999px"
  pill: "999px"
  card: "25px"
  card-compact: "20px"
  directory: "28px"
  workspace: "32px"
  reader: "26px"
  dialog: "32px"
  tag: "7px"
  source-symbol: "13px"
  checkbox: "6px"
spacing:
  inline: "8px"
  group: "16px"
  card-gap: "18px"
  card: "23px"
  workspace: "28px"
  dialog: "30px"
  compact-card: "16px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "10px 20px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
    textColor: "{colors.on-accent}"
  add-bookmark:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
    height: "40px"
  button-secondary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "9px 18px"
    height: "44px"
  button-text:
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "5px 10px"
    height: "32px"
  search:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "11px 16px"
    height: "50px"
  form-input:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
    height: "44px"
  navigation-active:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.pill}"
    padding: "9px 19px"
    height: "40px"
  directory-entry:
    textColor: "{colors.secondary-ink}"
    rounded: "{rounded.pill}"
    padding: "9px"
    height: "44px"
  tag:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.secondary-ink}"
    typography: "{typography.tag}"
    rounded: "{rounded.tag}"
    padding: "3px 8px"
  bookmark-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "{spacing.card}"
---

# Design System: Facetmark collection workspace

## Overview

**Creative North Star: "The Layered Collection Table"**

An upright, tactile collection system uses mist-blue surroundings, porcelain reading surfaces and deep ink, with electric-blue actions. Translucent navigation and directory layers, rounded cards and molded capsule controls carry the current implementation's visual character. This is a working implementation description, not a user-approved visual identity.

On 2026-10-24 the user described PR #44's mist-blue workspace as a substantial improvement and requested comprehensive refinement. Keep its composition, typography and material direction while fixing malformed selected capsules, black control states, interrupted motion, nested-folder access and unfinished startup flows. This feedback does not approve every individual visual choice or the new refinements.

The current changes are local source edits awaiting cloud rendering and operation checks. Earlier application revision 04ecc11 and capture-only revision 7d2abd0 passed their recorded cloud checks; those runs are the historical baseline, not verification of this diff. The [current round record](docs/collection-workspace-polish-2026-10-24.md) records the implemented changes and actual check scope.

The active product and behavior requirements remain in [PRODUCT.md](PRODUCT.md)
and the [frontend surface brief](.impeccable/surfaces/frontend.md). The frontmatter
records current source values. Component heights represent their observed minimum
heights unless the control has a fixed dimension.

**Key Characteristics:**

- Mist-blue ambient light, translucent supporting layers and opaque content surfaces.
- Bundled Inter and Noto Sans SC with upright headings and readable mixed-language records.
- Capsule controls, layered cards and motion tied to actual navigation, selection and reading state.
- Independent original links, record actions and scope controls remain visible.

## Colors

Electric blue carries actions; mist-blue layers and deep ink carry the workspace.
Frontmatter keys match the CSS custom-property names, with a `-dark` suffix for
the corresponding dark-theme value.

### Primary

- **Electric blue** (`accent`, `accent-hover`, `on-accent`): primary actions,
  active accents and their legible foreground. Add bookmark uses this blue.
- **Selection blue** (`soft`, `selected`, `selected-edge`): active controls,
  chosen records and their boundaries. Main navigation uses a blue filled plate;
  category and settings plates use porcelain-to-blue material.

### Secondary

- **Sky detail** (`brand-detail`): the bookmark mark, layered folder face and
  local card light. It does not replace a semantic processing status.
- **Semantic status pairs** (`success`, `warning`, `danger` and their
  `-soft` surfaces): completed work, attention and failure/destructive states.

### Neutral

- **Porcelain** (`canvas`): cards, search, dialogs and reading content.
- **Mist desk and rail** (`desk`, `rail`, `inset`): the ambient workspace,
  navigation drawer and inset control groups.
- **Deep ink** (`ink`, `secondary-ink`, `muted`): primary text, explanations
  and tertiary metadata. Pressed control surfaces use their semantic blue or
  porcelain roles; ink is not the navigation selection fill.
- **Glass and light** (`glass`, `glass-edge`, `light`): translucent support
  surfaces and their top edges. `ambient-blue` and `ambient-mint` form the
  two workspace radial gradients; `scrim` protects modal context.
- **Boundaries** (`rule`, `selection-neutral`): dividers and quiet state surfaces.

**The Content Surface Rule.** Keep reading text on an opaque content surface; ambient gradients and frosted layers belong to the surrounding workspace and controls.

## Typography

**Display Font:** bundled Inter and Noto Sans SC through the `Facetmark Latin`
and `Facetmark CJK` aliases.

**Body Font:** the same bundled pair, with Segoe UI, Microsoft YaHei UI and
sans-serif fallbacks. Smiley Sans is a retained historical asset and is not the
active interface font.

**Character:** firm, upright headings sit above quieter source and description
text. Collection and record headings keep neutral letter spacing, including Chinese.

### Hierarchy

- **Display:** the frontmatter display role is the collection heading; it becomes
  30px below 1300px and 26px below 720px. Desktop windows at or below 650px
  high also use the 26px heading.
- **Title:** the title role is the default card link, capped at two lines with the
  full title available on its native link. It becomes 17px / 1.65 on mobile and
  15px in the retained reading index.
- **Body and controls:** body is the base text scale; the control role belongs to
  shared primary/secondary buttons. Collection actions use a local 14px desktop
  and 13px mobile scale.
- **Summary:** the summary role uses two lines and a 72ch maximum in a card,
  at 15px on desktop, 14px on mobile and 13px in the reading index.
  Measured clipping exposes expansion; expanded text has no line clamp. When
  expansion is available, text and its control occupy separate normal-flow grid
  columns with an 8px gap.
- **Source and tag:** domain labels use the source role. Status, tags and folder paths
  use readable 13px metadata; dates and summary-basis captions remain 11px.
  Numeric counts use tabular figures.
- **Reading:** the reading role controls article body text. Reader titles use the
  reader-title role and grow to 38px in focus mode.

## Layout

The collection surface uses an 88px top navigation band above a 244px directory
and a flexible rounded worktable, with a 20px column gap. The workspace has 28px
horizontal padding and a 120px title/search band. The card grid fills available
width with a 340px minimum card width and an 18px gap. Grid view is the default
when no saved preference exists; list view remains a saved option.

At 1660px and above, the directory/index become 264px/340px, horizontal shell
padding becomes 30px and the card minimum becomes 360px. Below 1300px,
directory/index widths become 218px/280px and workspace padding becomes 22px.
At 1120px and above, reading keeps an index beside the reader; below that,
reading uses the full-viewport focus-managed drawer. Below 960px, top navigation
and the fixed directory are replaced by the navigation drawer.

Below 720px, the shell has a 58px top row, cards and list records share a compact
single-column treatment, and title/search stack. Main actions take one row, status
takes the next, and sorting/options/view share a third. Record actions and major
directory controls use their mobile touch dimensions. The directory remains a
separately scrollable bounded list rather than expanding the entire page. Below
360px, status uses four equal columns with each count below its label. The toolbar
compacts to an 8px gap and 12px top / 10px bottom padding.

On desktop widths, heights at or below 820px reduce the top row to 76px and the
toolbar to 98px. At or below 650px these become 68px and 72px, toolbar vertical
padding becomes 6px, the collection heading becomes 26px and the directory footer
is hidden. In this short desktop state, cards use 16px padding and an 8px gap,
source medallions are 32px square and record footers use 8px top padding.
Directory headings and search spacing compact at 700px height on widths of at
least 720px. Settings/tasks use the full content span. Paging stays outside the
collection's scrolling region.

## Elevation & Depth

Depth combines two ambient radial gradients, translucent support layers, opaque
cards, inset top highlights and offset soft shadows. Main navigation blurs at
18px, the directory at 24px, navigation scrims at 8px and library dialog scrims
at 10px. These are source-defined treatments awaiting current cloud inspection.

### Shadow Vocabulary

- **Card:** `--card-shadow` defines resting record depth and changes with theme.
- **Sheet:** `--sheet-shadow` lifts the reader, dialogs and raised menus; its
  light theme includes a top inset highlight.
- **Local controls:** primary actions, selected navigation and source medallions
  have component-specific highlights and shallow shadows. Card hover introduces
  a separate, broader shadow and pointer light without a card translation.

The exact shadow values and dark variants are in the sidecar's extensions,
extracted from the current stylesheet.

**The Motion Ownership Rule.** Assign each animated property to its existing component or motion controller; local hover light must not translate the whole record hit area.

## Shapes

Capsules are an explicit user requirement for buttons, search, segmented controls
and single-line form fields. Frontmatter records the active capsule radius.
Larger containers use their own geometry: cards, compact records, directory,
workspace, reader and dialog are separate radius roles. Tags remain small rounded
labels; source initials sit in softly rounded medallions. Checkbox frames retain
their compact square form and native checkbox semantics.

## Components

### Buttons

Shared capsule buttons keep the HeroUI/native event adapter. Primary actions use
electric blue, a top highlight and a specular sweep; secondary actions use porcelain
with an outlined, shallow raised edge; text actions keep their accent foreground.
Collection Add has a local blue treatment, while Summarize has a pale outlined
treatment. The source-owned variants determine their sizes and states.

Hover sweeps move over 650ms with the shared CSS easing; opacity arrives in 180ms.
HeroUI owns pressed and focus state. The adapter's CSS keeps the button hit area
stationary; pressing changes its material and inset shadow. Focus uses the visible
accent outline; disabled/pending behavior stays with the actual control. The sidecar
contains separate primary, Add, secondary and text visual specimens.

### Inputs / Fields

The main search is a porcelain capsule with a shallow inset and outer shadow.
Focus changes the edge and adds a soft accent ring. Its mobile font grows to
16px and minimum height becomes 44px. Form fields use the inset surface, capsule
geometry and the actual label/form behavior. Directory search has its own compact
desktop dimensions and 44px mobile treatment.

### Navigation

Top navigation sits inside a frosted capsule; its active segment is blue with an
on-accent label. The shared highlight animates real dimensions and translation
over 340ms, without scale projection of rounded corners. Grid segments explicitly
fill their assigned width. Directory entries use capsule rows, exact folder/tag/site
labels, counts and selected blue surfaces. The mobile
navigation drawer uses the rail surface and a separate scrim. Its width is the
smaller of 380px and the viewport minus 20px, with 16px padding and a 12px gap.
Main navigation uses two columns in a 1.2:1 ratio; bottom utilities use three
columns in a 1.6:1:1 ratio, with appearance controls spanning the full row. Drawer
navigation and utility buttons retain a 44px minimum height. The layered folder
face interpolates matching SVG paths over 240ms; its paper moves with selection
or disclosure. Fine-pointer hover detail is disabled under reduced motion.

The folder tree pages direct children using the stored `folder_depth` and the
importers' `/` display separator. API-created slash names remain literal; ambiguous
legacy depth/path combinations remain complete exact entries rather than guessed trees.
Disclosure and exact selection have separate buttons; ancestors without direct
bookmarks can expand. Row counts exclude descendants. Labels wrap to two lines
within the bounded sidebar, and the selected path has a complete-text disclosure. Loaded
branches and their pages survive closing and category changes; library revisions
invalidate them. Arrow keys move through visible rows and their ancestors.

### Chips

Record tags use compact inset labels with their own small radius. Filter-removal
chips and editable tags are interactive capsules; they are not the same component
as the passive record tag.

### Cards / Containers

Bookmark cards present source, native title/original links, expandable text, status,
tags, folder and actions as separate elements. Domain initials choose one of four
source medallion colors; they are not page thumbnails. The card's local pointer
light responds only to a mouse and is removed for reduced motion. Hover settles
the source medallion over 400ms. Selected records retain an explicit edge and tint.
List mode reuses the record with compact padding and a horizontal desktop layout.
Its action column uses max-content width; the preview control does not shrink or
wrap its label. Expandable descriptions use a minmax(0, 1fr) text column and an
auto-sized control column with an 8px gap, preserving both reading width and the
control's hit area.

The card layout controller uses a spring (stiffness 340, damping 32). Its entrance
moves 12px over 380ms with 260ms opacity and a small capped opacity stagger. Native
selection uses a 160ms fill scale; the checkmark uses opacity/scale, not stroke
drawing. Cloud interaction captures include intermediate states, rapid reversals
and reduced-motion endpoints. These samples do not certify full-session frame
pacing on every target device.

### Reader, overlays and shared motion

The reader keeps collection context on wide screens and becomes a 220ms horizontal
drawer below the reading breakpoint. Shared selected segments use an interruptible
340ms GSAP `power3.out` transition of actual width, height and position. The last
painted bounds are scoped to the application, and responsive changes update the
endpoint immediately. Dialog/menu overlays use a spring
(stiffness 380, damping 30), 200ms entering opacity and 160ms exits; their exit
wrapper immediately becomes inert. Content/category/page transitions retain the
existing interruptible GSAP controller. Reduced motion skips spatial entrances,
layout springs and local sweeps while preserving the usable state.

### Startup and first use

The native splash, React boot waiting/error screen, pairing form and setup/import
path use the same mist, porcelain, blue and bookmark geometry. The native splash
uses local platform fonts before the service and bundled application fonts are
available. Its 500×360 window keeps long errors scrollable and retry reachable.
Waiting is set before restart; a native error received during the promise stays
visible. Reduced motion removes the loading track's movement.

Boot, pairing, import and source discovery use immediate in-flight guards. Pairing
retains a failed token draft and submits through a native form. Visited setup
panels remain mounted, preserving model drafts; step completion reflects actual
import, tested connection and compatible-index facts. Connection errors have a
bounded panel rather than stretching between competing top/bottom offsets.

### Ownership and evidence

`styles.css` owns theme/font primitives; `ui/controls.css` owns shared button
paint; `workbench.css` owns shell/search/responsive geometry;
`bookmark-card.css` owns record paint; `facet-browser.css` owns the directory;
`folder-tree.css` owns nested disclosure; `collection-folder-icon.css` owns folder
material; `startup.css` and `setup.css` own arrival and first-use surfaces;
`library-tools.css` and `collection-tools.css` own their action/scoping flows;
`reader-shell.css` owns reading surfaces. Motion controllers keep their existing
property ownership.

The sidecar's self-contained HTML/CSS specimens reproduce visual states with inline
SVG and token fallbacks. They do not reproduce React, HeroUI, GSAP, Motion,
backend behavior or focus management. Generated tonal ramps are panel previews,
not additional shipped theme colors.

**The Evidence Boundary Rule.** Describe source and runtime evidence at their actual scope. A passing test or a design record never establishes user visual acceptance.

## Do's and Don'ts

### Do:

- **Do** use the current paired light and dark tokens and component-owned capsule styles.
- **Do** preserve native links, keyboard activation, form behavior, focus return and explicit action scopes.
- **Do** keep long Chinese and English content readable, with measured summary expansion and independent directory scrolling.
- **Do** remove replaced styles at their owner and keep reduced-motion states usable.
- **Do** review the new source in cloud renders and recordings with isolated synthetic data.

### Don't:

- **Don't** restore rejected pale-iris, limestone or pale-green layouts and tokens from historical records.
- **Don't** use a blanket button/input appearance rule or a document-wide event patch to create local effects.
- **Don't** merge record hover movement with the layout controller or hide metadata until hover.
- **Don't** treat old evidence, generated tonal ramps or static component specimens as current runtime or aesthetic approval.

Current verification is limited to source and small synthetic evidence checks;
the first pushed revision 87456ff produced 53 source-matched collection captures
and a main interaction recording. The focused collection suite passed 8 of 10
cases; CI browser failures also exposed hidden-tree locator ambiguity. Those
locators and the reduced-motion transform residue are corrected in the follow-up,
which still requires new cloud rendering and installed Windows verification.
The collection workflow now includes folder disclosure, capsule geometry,
startup/pairing and draft-recovery checks. Native splash captures use a synthetic
restart bridge and are distinguished from installed-app evidence. See the
[current round](docs/collection-workspace-polish-2026-10-24.md) and
[historical baseline](docs/collection-workspace-2026-10-23.md).

### Short windows, system colors and native identity

At 683×384, the title/search share a row, tools wrap compactly and the workbench
can scroll as a whole while retaining at least 160px of results. Forced colors
use a system Highlight outline for preview/batch selection, and the preview
control uses HighlightText on Highlight. Native checkbox operation remains intact.

The desktop application icon replaces the earlier bookmark asset with an authored
blue folded F on a porcelain tile. Edge light, facet planes and soft depth retain
the workbench's material roles at 16–256px. The CI asset script owns its PNG/ICO;
default window, tray and package identities consume those same assets. The UI
collection mark remains the bookmark geometry. The new desktop icon awaits render
inspection and user review.

Native persistence retains the existing physical outer-frame preference shape.
Restoration moves to the target work area, measures physical decoration and applies
an explicit physical inner size. Geometry events update memory; one worker writes
after 900ms of quiet, and close/quit flush the final state. Minimized mode retains
the last non-minimized maximized state. Startup failure after ready clears its child
before exposing Retry. Actual current-DPI installed checks are separate from pure
synthetic 100%/150% and removed-monitor regression cases.
