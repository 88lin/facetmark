---
version: 1
slug: frontend
primary_target: frontend
related_targets:
- frontend/src/App.tsx
- frontend/src/Settings.tsx
- frontend/src/SettingsWorkspace.tsx
- frontend/src/ModelPicker.tsx
- frontend/src/Setup.tsx
- frontend/src/CollectionTools.tsx
- frontend/src/LibraryTools.tsx
- frontend/src/BookmarkCard.tsx
- frontend/src/FacetBrowser.tsx
- frontend/src/FolderPicker.tsx
- frontend/src/folder-picker.css
- frontend/src/Tasks.tsx
- frontend/src/Reader.tsx
- frontend/src/styles.css
- frontend/src/workbench.css
- frontend/src/collection-tools.css
- frontend/src/support.css
- frontend/src/InteractionMotion.tsx
- frontend/src/overlay-motion.tsx
- frontend/src/reader-shell.css
- frontend/src/useReducedMotion.ts
- frontend/src/ui/controls.tsx
- frontend/src/bookmark-card.css
- frontend/src/facet-browser.css
- frontend/src/CollectionFolderIcon.tsx
- frontend/src/collection-folder-icon.css
- frontend/src/ui/controls.css
- frontend/src/FolderTree.tsx
- frontend/src/folder-tree.css
- frontend/src/startup.css
- frontend/src/setup.css
- desktop/splash/index.html
- desktop/splash/loading.js
- desktop/splash/mark.svg
- desktop/splash/native-ui.css
- desktop/splash/tray.html
- desktop/splash/tray.js
- desktop/src-tauri/src/tray_menu.rs
- frontend/src/AnchoredMenu.tsx
---

# Facetmark frontend — Operate

## Direction status

Latest 2026-10-24 assessment: “还不算好看，能用的样子而已”. The overall appearance
needs improvement. Earlier acknowledgement of progress does not approve or freeze
the current identity, layout, type, colors or material; no individual choice is
newly approved. Final application/capture f1c67fe passed all four workflows with verified
rendered/installed evidence and actual capsule frame bounds. 04ecc11 / 7d2abd0
and the earlier 831dcfd round remain revision-specific history.
Current follow-up is in docs/workspace-layout-2026-10-24.md. PR #44 is merged;
commit/push and cloud checks are authorized for a new PR, without automatic merge
or release. This source revision awaits cloud rendering and user review.

Long-term reference: general handbook v0.18. D04 / D05 history and latest D06
assessment belong in docs/design-reference-project-record.md in this repository.
The master does not contain this product's designs, implementation or runtime results.
Impeccable owns one system; oil-ui / Taste and S17-S20 supply selected relationships.

The user additionally requested open-issue repairs and a replacement desktop app
icon, and authorized commit/push plus cloud verification. f1c67fe passed all four
workflows, with 12/12 collection, 88 browser cases/2 skips and one separate 200k
case. Its 59 PNGs, 7 action groups, 64 source hashes and 63 media/record hashes
are verified. The installed 32px folded-F icon matches the ICO pixels exactly.
Full light/dark pages, 390px reflow, short-window typography, nested folders,
startup/setup, system selection colors and icon spacing were inspected. The
broader experience package has 45 source, 94 PNG and 3 MP4 hashes verified.
Actual 96-DPI installed geometry/retry passes; 240 changing move/resize calls
produce one idle write and close flushes the final outer frame. 18 Web and 24
installed interactions report no page errors or unexpected writes. 150% DPI and
monitor removal remain pure geometry scope. Overall visual quality requires
refinement after user review; individual new icon/detail approval remains pending.

The lifecycle-only 2b4ecdb run was 11/12: frame height still fell to 10.16px.
Browser DOMRect getters were lost through an object spread, independently of
cleanup timing. Final code copies left/top/width/height explicitly and stops
paint sampling before reversion. Two cleanup orders each pass 60 switches with
non-enumerable getters and four negative controls. All 61 real category frames
remain 32px high and 66.65625–67.000015px wide; scale remains 1. Storyboards and
frame data were inspected; full MP4 playback/all-device frame-rate testing was not.

## Direction contract

This contract describes the implemented version and its behavior. Visual form remains
open to improvement under the latest assessment; it is not a frozen or approved preset.

THESIS: A personal collection with a clear reading surface and tactile controls.
Actual saved content carries the composition.

OWN-WORLD: Mist-blue surroundings, porcelain cards, deep ink text, blue navigation plates and electric
blue primary actions. Frosted directory and toolbar layers establish depth; capsule
controls have molded edges and moving highlights. Inter and Noto Sans SC provide
firm, upright type with distinct display, title and description scales.

STORY: Enter through floating navigation, choose an exact directory, search or scan
the collection. Read beside a retained index. Selection and summary scopes remain
visible and separate through paging and failure recovery.

FIRST VIEWPORT: At 1440px a 64px header holds capsule navigation, shared search
and utilities above the collection. A 252px directory spans the entire window
height; duplicate brand/title blocks are removed. Compact actions/status lead
directly to a 280px-minimum card grid (three columns at 1440px/1280px, two at
1024px, one on mobile). The retained reader index is 264px. Settings use the full
workspace width. Source, mixed-language titles and varied summaries remain visible.

FORM: Code-led improvement from the current mist-blue implementation under the
latest usability and appearance feedback. Source-inspected S17/S19 relationships
remain supporting references. Current choices are not frozen or approved.

SIGNATURE: Local light follows the pointer on a record without moving its hit area;
the source medallion settles on hover. Selection plates move through their actual dimensions without scaling corners.
Cards rearrange continuously, folders disclose their children and dialogs spring into
protected focus. Reduced motion retains each usable endpoint.

FINISH: Inspect source-matched cloud renders, intermediate motion and relevant
operations. Report actual coverage and remaining defects; user review stays separate.

## Collection and navigation behavior

Keep Add / Manage / Summarize distinct from summary status, sorting and display.
Original links, selection, editing, summary actions and preview remain independent.
Blank card areas open preview through the existing button's focus-return path.
Modifier clicks, text selection and interactive descendants retain their own actions.
Descriptions must remain readable; measured clipping determines expansion.
Searchable access to the full folder/tag/site directory, parent paths, counts and
pagination must remain available at narrow and short viewport sizes.
The sidebar now uses a bounded direct-child folder tree. Disclosure never changes
selection; counts exclude descendants. Virtual ancestors expand, full-path search
remains available, and loaded branches survive closing/category changes until a
library revision invalidates them. Arrow keys traverse visible rows and ancestors.
Recover hierarchy from stored depth and the importers' `/` display path. A literal
slash name or ambiguous legacy path remains one exact entry; do not infer ancestors
from separators alone. Two-line rows keep capsule proportions; path details reveal
the complete name and recoverable ancestry.

Add/edit/move retain the shared complete folder-selection flow: bounded pages,
exact choice, separate search draft, explicit unfiled/new-folder states, retry and
keyboard navigation. Create a path only on save. Model choices remain bounded
with explicit access to additional results. Preserve server paging and scoped
selection for large collections; stale results must not drive actions after context
changes. Preserve IME input, final query and relevant scroll/focus context.

## Model settings and task recovery

Summary and optional embedding channels remain independently configurable. Preserve
drafts and results across settings navigation. Discovery, catalog availability,
model selection, successful test, persisted save and execution are separate states.
Per-Agent drafts stay independent. Provider/installation/credential changes
invalidate stale catalogs and tests; changing the model requires a fresh test.
A failed save remains visibly unsaved.

Processing requires scope review and consent. Zero eligible items cannot start.
Library changes invalidate stale scope previews. Management/export scope remains
separate from processing scope. Resume/retry uses the original durable target
snapshot, preserves completed entries and only handles its unfinished/failed entries.

## Controls, reading and motion behavior

Preserve click currentTarget, Enter/Space activation, form submission, labels,
disabled/pending state, focus containment/return and caller preventDefault semantics.
If a library adapter changes, verify these contracts before applying it everywhere.
Each element/property has one animation owner. Closing overlays must stop accepting
input immediately; rapid reversal and live reduced-motion changes remain safe.

Reader layouts may change. Body text is 17px/1.8 (16px mobile), titles are
29px/700 (25px mobile, 32px focus). The compact index hides duplicate excerpts,
tags and folder paths while retaining source, title, status and actions.
Only saved body text has an in-flow progress footer; summary/related/empty states
do not show an idle “reading preview” box.
 Keep actual heading navigation, article progress,
chapter selection and an unobscured final paragraph. Resizing and closing preview
must preserve meaningful reading/search context. Existing glass/plane artwork and
layout are not mandatory; their underlying progress and navigation behavior is.

## Startup and first use

The native splash and React boot/pairing/setup/import path share the identity and
material roles. A restart failure received during its promise must remain visible.
Native retry supports Enter/Space and long error reading. Pairing uses a native
form, retains failed token drafts and blocks duplicate submissions. Visited setup
panels stay mounted; completion comes from actual setup facts, not visitation.
Source discovery and import remain explicit read-only actions on selected sources.
Browser-rendered splash HTML with a synthetic bridge does not certify installation.
The package/window/tray icon uses a porcelain tile and authored folded blue F;
the same folded-F SVG is used for the React identity, native startup and tray. The icon is generated only
in CI, with light/dark size evidence. The installed local 32px icon was read-only
extracted and matched to the previous installed cloud image (0 different pixels).
A packaged native tray WebView uses the same fonts/mark, real native settings,
keyboard roving focus and bounded monitor-aware geometry. Native menu actions
are restricted to that local page; cloud HTML fixtures remain separately labeled. Native physical-frame restoration, quiet
geometry persistence and sidecar cleanup are separately verified after installation.

## Implementation and verification

Give components ownership of styles and motion. Remove migrated definitions rather
than stacking overrides over obsolete ones. Avoid blanket radii on all controls
and global event effects that leak across routes or portals.

Validate the replacement's full screen and relevant journeys in the cloud, including
desktop, short windows, mobile, Chinese/English and light/dark operation. Use synthetic
data and source-matched images/recordings. Do not run builds, browser automation,
package installation or desktop installation locally or touch real browser profiles.

[Desktop validation](../../docs/desktop-validation.md) records the existing
technical baseline. It does not approve the appearance. Update DESIGN.md and the
sidecar from the actual new implementation; do not restore the historical tokens
or claim a new visual acceptance from old tests or component-only review.
