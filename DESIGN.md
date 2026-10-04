---
name: Facetmark workbench
description: A paper-white, graphite and purple search and reading workbench.
colors:
  canvas: "#fff"
  rail: "#f5f5f7"
  inset: "#f8f8fa"
  ink: "#242429"
  muted: "#65656f"
  rule: "#dedee5"
  accent: "#6541c7"
  soft: "#eee8fb"
  on-accent: "#fff"
  danger: "#a4293b"
  overlay: "#17171c66"
  canvas-dark: "#202024"
  rail-dark: "#19191d"
  inset-dark: "#29292f"
  ink-dark: "#f1f1f4"
  muted-dark: "#b1b1bc"
  rule-dark: "#42424b"
  accent-dark: "#b79cf5"
  soft-dark: "#352b4c"
  on-accent-dark: "#20172f"
  danger-dark: "#ffacb8"
  overlay-dark: "#09090d99"
typography:
  headline:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "26px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.025em"
  section:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.025em"
  subheading:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.025em"
  body:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "14px"
    lineHeight: 1.6
  result-title:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.5
  reading:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "14px"
    lineHeight: 1.9
  button:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "13px"
    fontWeight: 550
    lineHeight: 1.5
  label:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "12px"
    lineHeight: 1.6
  caption:
    fontFamily: '"Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
    fontSize: "11px"
    lineHeight: 1.6
rounded:
  hint: "4px"
  chip: "5px"
  field: "6px"
  button: "7px"
  search: "8px"
  panel: "12px"
spacing:
  micro: "4px"
  tight: "6px"
  compact: "8px"
  small: "12px"
  medium: "16px"
  section: "24px"
  gutter: "28px"
  large: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "9px 15px"
  button-secondary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "9px 15px"
  button-text:
    textColor: "{colors.accent}"
    typography: "{typography.label}"
    padding: "5px 0"
  button-icon:
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    width: "30px"
    height: "30px"
  search-field:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.ink}"
    rounded: "{rounded.search}"
    padding: "10px 12px"
  navigation-active:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.button}"
    padding: "9px 12px"
  filter-chip:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.accent}"
    typography: "{typography.caption}"
    rounded: "{rounded.chip}"
    padding: "3px 8px"
  settings-panel:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "24px"
  result-selected:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.ink}"
    padding: "19px 14px"
  preview-tabs:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    padding: "0 30px"
---

# Design System: Facetmark workbench

## Overview

**Creative North Star: "Facetmark workbench"**

Facetmark is a restrained search and reading workbench: paper-white surfaces, graphite text and a single purple accent keep a personal bookmark library readable. This is the user-confirmed replacement for the legacy sketch interface. The implemented React interface is the visual authority and is shared by the Tauri 2 desktop shell, Python distribution and Docker image.

The recurring signature is a ruled result list beside a quiet reading surface, with query and collection context retained while inspecting a page. Density supports repeated scanning; Chinese and English use the same locally available UI font stack. The system uses tonal separation, simple outlines and useful state changes rather than decorative illustration.

**Key Characteristics:**

- Paper-white and graphite foundations with purple for action, selection and focus.
- Compact navigation and results paired with more generous reading rhythm.
- Light and dark themes, bilingual labels and local CJK font fallbacks.
- Responsive drawers preserve access to search, filters and reading.

This document refreshes the existing approved direction from `frontend/src/styles.css` and the shared React components. It records implementation values; it does not establish a new visual concept.

## Colors

The palette feels like a clean working page: neutral structure, graphite information and restrained purple emphasis. Frontmatter values are normative; the CSS custom properties with the same base names provide the live theme roles.

### Primary

- **Workbench Purple** (`accent`): primary actions, links, selection and keyboard focus.
- **Purple Wash** (`soft`): selected rows, active navigation, filter chips and informational notices.
- **On Purple** (`on-accent`): readable primary-button text.

### Neutral

- **Paper White** (`canvas`): the main collection surface and form fields.
- **Quiet Rail** (`rail`): persistent navigation.
- **Reading Paper** (`inset`): reading surface, search input and quiet inset panels.
- **Graphite** (`ink`): titles and primary information.
- **Secondary Graphite** (`muted`): excerpts, domains, labels and supporting explanations.
- **Paper Rule** (`rule`): fine separators, outlines and subdued hover backgrounds.
- **Modal Scrim** (`overlay`): translucent backdrop behind navigation and preview drawers.

### Status and themes

- **Error Red** (`danger`): failures paired with explanatory text and a recovery action.
- The `-dark` entries map to the same CSS role under `:root[data-theme="dark"]`. Dark surfaces are graphite, text becomes pale, and the accent becomes a lighter purple. No additional accent family is introduced.
- Selection uses Purple Wash with Workbench Purple text. Input carets use Workbench Purple; thin scrollbars use Paper Rule.

**The One Accent Rule.** Use purple for primary actions, links, selected items and focus. Use graphite and muted neutrals for the collection itself; reserve danger color for failures.

## Typography

**Body and interface font:** "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif.

The shared local stack is a confirmed product requirement for offline delivery and Chinese/English reading. Headings remain functional interface type; there is no separate promotional display face. The font stack contains local fallbacks and does not depend on a font download.

### Hierarchy

- **Page headline:** the frontmatter headline role; the library heading is more compact (23px), and preview titles use a reading-oriented size and leading (24px / 1.55).
- **Section and subheading:** the frontmatter section and subheading roles; headings share medium emphasis and slightly tightened letter spacing.
- **Result title:** the result-title role, with a two-line clamp. Selected titles use the accent.
- **Body:** the body role for the general interface. Excerpts are quieter (12px / 1.7), with a two-line clamp.
- **Reading:** the reading role with a maximum measure (72ch). At wide desktop sizes the type increases (15px); narrow drawers remove the maximum measure.
- **Labels and captions:** the label and caption roles for form labels, tabs, domains and secondary context. Result metadata uses a smaller supporting size (10px).
- **Numeric detail:** counts and pagination use tabular numerals. Diagnostic output uses local monospace (`ui-monospace, Consolas, monospace`).

**The Reading Rhythm Rule.** Keep result titles and excerpts compact while giving page text a relaxed line height. Allow Chinese text, long titles and URLs to wrap without forcing the workbench wider.

## Layout

The shell fills the dynamic viewport (`100dvh`) with a minimum height (400px). Navigation, results and preview form the three-column desktop workbench. The navigation rail is fixed-width (216px); the remaining workspace uses `minmax(360px, 1fr) minmax(330px, 39%)`. A search header remains above an independently scrolling result list, and a fixed pagination footer remains below it. Preview content scrolls separately.

The result list uses ruled rows rather than elevated cards. Standard row padding is (19px 14px), while the search header and reading surface use more generous gutters. Reused spacing primitives are in the frontmatter; responsive content pages use fluid horizontal padding (`clamp(24px, 4vw, 64px)`). Settings and task sections are constrained (1040px).

- **Wide desktop (at least 1600px):** rail width increases (236px); the workspace grid becomes `minmax(440px, 1fr) minmax(400px, 42%)`. Rows gain vertical space (22px), excerpts increase (13px), and reading text increases (15px).
- **Narrow desktop/tablet (at most 1119px):** the reading pane becomes a right-hand modal drawer, width `min(540px, 92vw)`. Model settings stack into one column.
- **Mobile (at most 719px):** navigation becomes an off-canvas rail (250px) opened from a compact toolbar (52px). Search and result gutters contract, the search shortcut hint and row chevron are hidden, and page headings stack. Filters remain accessible through navigation and the active-filter chips.

## Elevation & Depth

The implementation is flat at rest and uses no box shadows. Paper, rail and inset tones establish hierarchy; thin rules separate columns, rows, fields and tabs. Drawers use the modal scrim and stacking order. Focus is expressed by an accent outline (2px with a 3px offset), while the search container uses its own accent border and outline.

**The Flat Surfaces Rule.** Separate resting surfaces with tone and thin rules. Modal depth comes from a scrim and stacking order, not card shadows.

## Shapes

Corners are gently rounded for controls and inset panels, while list rows and structural divisions remain straight. The radius roles in frontmatter distinguish small keyboard hints, chips, fields, buttons, search containers and larger panels. Fields and panels use thin outlines (1px); active preview tabs use an accent underline (2px).

Lucide outline icons support labels with a consistent stroke (1.7). Action icons generally measure (18px), icon-only buttons use (17px) glyphs inside compact square controls, and empty/import states may use larger icons. Letter tiles represent source domains; they are content identifiers rather than decorative glyph icons.

## Components

### Buttons

Compact and plainly labeled. Primary buttons use purple with the matching on-accent text, secondary buttons use a canvas fill and a thin rule, and text buttons expose lighter actions. Primary hover darkens through brightness (0.94); secondary hover uses the inset surface; text-button hover adds an underline. Icon-only controls use a rule-colored hover fill and an accessible label. All controls retain visible keyboard focus; disabled buttons reduce opacity (0.48) and use a not-allowed cursor.

### Search and fields

The search container pairs an outline icon with a borderless input on the inset surface. Focus applies to the whole container. A keyboard hint advertises the search shortcut on larger windows. Settings fields use canvas fills, thin rules and the field radius; disabled fields use muted text over the inset surface. Long pasted values must not expand the grid.

### Navigation and chips

Navigation uses compact rows, outline icons and tabular counts. Active navigation is Purple Wash with accent text and stronger weight; hover uses the rule tone. Expandable facets expose a small rotating chevron. Active-filter chips use Purple Wash and a remove affordance; preview tags use a quiet outline and can start a filtered search.

On mobile, the open navigation is modal: background content is inert, keyboard focus stays inside, Escape closes it, and closing restores the previous focus. The closed rail is inert so hidden links are not reachable by Tab.

### Settings and inset panels

Model settings form a shared outlined container with a divider between channel panels, stacking vertically when space is limited. Each channel shows configuration and test state beside its own controls. Import, indexing consent and apply panels use the same panel radius and quiet inset surface. Failure text is adjacent to its affected operation; status and error regions retain their semantic announcements.

### Search results and reading preview

Each result is a full-width button with a source letter tile, title, two-line excerpt, domain/folder metadata and a chevron when space permits. Hover uses the inset surface; selection uses Purple Wash with an accent title and a pressed state. Arrow keys browse results, and closing a preview returns focus to the originating result.

The reading surface keeps page text, AI summary and related pages in a tab interface. The active tab uses accent text and an underline; left/right arrows and Home/End move through tabs with a single active tab stop. The preview is persistent beside results on desktop and a Radix modal drawer below the narrow-desktop breakpoint. Escape and the close button dismiss it without resetting the search context.

Empty library, no matches, missing extracted text and recoverable loading failures have different explanations and actions. AI-derived content identifies its source basis when only a title is available. Busy work uses a spinner and named stages rather than an invented percentage.

### Motion

Motion signals state only. The preview drawer enters from a small horizontal offset (24px) over a short interval (160ms) using `cubic-bezier(0.16, 1, 0.3, 1)`. Facet chevrons turn over (140ms); busy indicators rotate linearly (1.1s). Reduced-motion preference disables animation and transitions and restores automatic scrolling behavior.

## Do's and Don'ts

### Do:

- **Do** preserve query, filters, pagination and result context while opening and closing a reading preview.
- **Do** use the same semantic color roles in light and dark themes.
- **Do** keep Chinese and English labels readable with local CJK font fallbacks and text wrapping.
- **Do** preserve visible focus, keyboard tab navigation and focus return when a drawer closes.
- **Do** distinguish empty libraries, no matches, missing page text, loading and recoverable failures.
- **Do** use synthetic data and a visible demo label for presentation captures.

### Don't:

- **Don't** reintroduce hand-drawn borders or candy-colored dashboard surfaces.
- **Don't** turn collection rows into a grid of raised decorative cards.
- **Don't** require remotely loaded fonts or imagery for the workbench to function.
- **Don't** communicate selection, progress or failure through color alone.
- **Don't** display an estimated progress percentage when only the active stage is known.
