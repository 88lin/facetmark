---
name: Facetmark collection workspace
description: Implemented pale-iris collection system; user visual review pending.
colors:
  accent: "#6544bb"
  canvas: "#ffffff"
  rail: "#eeebf8"
  ink: "#28243d"
  secondary-ink: "#605c76"
  rule: "#e7e4ef"
  inset: "#f5f4fa"
  selected: "#e9e0fb"
  soft: "#f0eafb"
  danger: "#b33b58"
  success: "#246c62"
  warning: "#88651e"
  accent-dark: "#c3a8ff"
  canvas-dark: "#211e2d"
  rail-dark: "#282238"
  ink-dark: "#f0ecfb"
  secondary-ink-dark: "#c3bdd9"
  rule-dark: "#3c354e"
  inset-dark: "#2b273b"
  selected-dark: "#413257"
  soft-dark: "#352b4c"
  danger-dark: "#ffa6bc"
  success-dark: "#9bd7c9"
  warning-dark: "#ebca8c"
typography:
  display:
    fontFamily: 'Facetmark Display, Facetmark CJK, Microsoft YaHei UI, sans-serif'
    fontSize: '2.125rem'
    fontWeight: 400
    lineHeight: '1.35'
    letterSpacing: '0'
  title:
    fontFamily: 'Segoe UI Variable Text, Segoe UI, Microsoft YaHei UI, PingFang SC, Facetmark CJK, sans-serif'
    fontSize: '1.125rem'
    fontWeight: 650
    lineHeight: '1.55'
    letterSpacing: '0'
  summary:
    fontSize: '0.9375rem'
    fontWeight: 400
    lineHeight: '1.75'
  label:
    fontSize: '0.8125rem'
rounded:
  control: '12px'
  search: '14px'
  reader: '20px'
  dialog: '24px'
  tag: '6px'
spacing:
  inline: '8px'
  group: '16px'
  panel: '24px'
components:
  add-bookmark:
    backgroundColor: '{colors.ink}'
    textColor: '{colors.canvas}'
    rounded: '{rounded.control}'
    height: '40px'
  search:
    backgroundColor: '{colors.inset}'
    textColor: '{colors.ink}'
    rounded: '{rounded.search}'
    padding: '9px 14px'
  tag:
    backgroundColor: '{colors.inset}'
    textColor: '{colors.secondary-ink}'
    rounded: '{rounded.tag}'
    padding: '2px 7px'
---

# Facetmark collection workspace

## Overview

Return to a saved idea without losing the collection context. This working system
uses soft iris navigation, blueberry text and a continuous content list; the small
coral fold in the mark supplies a separate brand detail. The 2026-10-23 replacement
is implemented in the production React application and is awaiting user visual review.
Prior capsule, teal and limestone/orange directions remain rejected.

## Colors

The frontmatter records light and dark token pairs from the current stylesheet.
Accent identifies selection and interaction; success, warning and danger retain
independent meanings. Quiet surfaces support dark text, and raised panels separate
protected operations from browsing. Site letter badges are decorative source cues.

## Typography

Bundled Smiley Sans is reserved for the collection heading; controls, record titles
and summaries use platform sans with bundled Noto Sans SC fallback. Chinese headings
use zero tracking. The display heading reduces to 30px on compact layouts; wide list
summaries use 1.7 line height. Source, tags and descriptions remain visible across
layouts. Small counts and provenance labels currently use 11px in some components;
that is an implementation detail, not a default for new body or action text.

## Layout

At 1440px a 248px unified navigation/directory faces the content workspace. The
collection contains title/search, independent add/manage/summary actions, status
and display controls, scrollable results and fixed paging. The default is a continuous
list; card view is optional. At 1120px and above the reader retains a 354px list index.
Below that it becomes a focus-managed layer; navigation becomes a drawer below 960px.

Below 720px the main actions stay above status, sorting, display and view controls.
The view toggle shares the sorting row to preserve useful space at 320px. Heights
up to 820px compact the rail; up to 650px compact navigation again and omit the
redundant directory footer. Utility targets reserve space while setup status loads.

## Elevation & Depth

The collection list uses separators; search is inset and dialogs/readers use soft,
offset shadows. A border plus shadow can clarify a surface without requiring all
records to become raised cards. The reader layer paints above application navigation,
while create/edit dialogs paint above the reader. Exact shadows remain in the sidecar.

## Shapes

The folded mark and folder face use small authored SVG geometry. Controls, search,
reader and protected dialogs use role-specific radii recorded above. Selected list
rows gain a soft rounded background; unselected rows share a continuous surface.

## Components

- Navigation and directory keep explicit accessible names, literal folder paths,
  bounded results and search. Short-window compaction preserves scrolling access.
- Original links, checkboxes, edit/summary actions and reader entry remain independent.
  Measured clipping controls expansion and is recalculated when locale labels change.
- Add, management IDs and summary scopes remain distinct. Cross-page selection and
  consent are retained; failed saves preserve drafts and retry writes the actual API.
- Local tab highlights and folder/checkbox feedback follow real state. Folder paths
  use matching points for continuous interpolation; checkbox fill and mark animate
  scale/opacity. Reduced-motion mode reaches the same usable endpoint.
- `workbench.css` owns composition, `reader-shell.css` owns reader layers/type,
  `search-tools.css` owns suggestions, and the other component styles own their controls.
  The existing HeroUI native event/form bridge remains unchanged in this round.

## Do's and Don'ts

- Preserve actual links, keyboard/form semantics, data ranges and return focus.
- Remove superseded styles at the owning component when changing a surface.
- Keep the supplied handbook's relationships as references, not approved templates.
- Do not treat tests, hashes or reviewer findings as user aesthetic acceptance.
- Do not generalize incidental small labels or screenshot fixtures into product rules.

Current-source validation, limitations and user review status are recorded in
[the round record](docs/collection-workspace-2026-10-23.md).
