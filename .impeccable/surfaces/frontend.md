---
version: 1
slug: frontend
primary_target: frontend
related_targets:
- frontend/src/App.tsx
- frontend/src/navigation.ts
- frontend/src/Settings.tsx
- frontend/src/SettingsWorkspace.tsx
- frontend/src/settings-maintenance.css
- frontend/src/ModelPicker.tsx
- frontend/src/ReasoningSettings.tsx
- frontend/src/SavingSessions.tsx
- frontend/src/saving-sessions.css
- frontend/src/ActivityTimeline.tsx
- frontend/src/activity-timeline.css
- frontend/src/reasoning.ts
- frontend/src/reasoning-settings.css
- frontend/src/SummaryPreferences.tsx
- frontend/src/summary-preferences.css
- frontend/src/useSummaryGeneration.ts
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

2026-11-18 product-quality review confirmed five navigation/editing/focus failures
on unchanged production UI in Actions 44232486636. Two independent assessments
also identified narrow collection density, empty-note prominence, unbounded import
rows, hidden settings categories and excess chat status height. Repairs retain the
existing capsule/material system with component-owned styles: page/category history,
in-memory form continuity, visibility-aware polling, deliberate search focus,
compact reading entry and full-content disclosures. Intermediate visual review
also tightened the remaining metadata rows: narrow summary status uses compact
visible copy with its complete accessible text, and only the truly empty note
entry shares the reader toolbar through its own Portal. The note editor, saved
content and recovery stay in the reading flow. Source 3809060 passed the
focused navigation/settings regression; narrow reader action wrapping and tested
draft continuity checks then extended the final scope. Final source-matched
rendering, interaction and installed results are recorded in PR #70's Actions and
acceptance description. The baseline detector returned no
findings despite the usability defects; no local browser/overlay ran, per the user
restriction. Work and evidence boundaries are in
docs/product-quality-review-2026-11-18.md. Passing checks will not imply user
aesthetic approval or a product with no remaining issues.

2026-11-16 continuation follows the personal local-first product. Enrollment is
reference material only. Current work and source-specific checks are tracked in
docs/full-product-repair-2026-11-16.md. Import previews and receipts, named model
connections, per-conversation choices, draft recovery and readable fetch failures
use the existing capsule controls and component-owned styles. Chat status can
scroll independently so short-window input remains reachable. Unconfigured chat
retains editable drafts while sending remains gated by the real connection state.
The user authorized per-module PRs and merges after verification; formal releases
remain separate. The overall visual direction still has no user aesthetic approval.

2026-11-17 workspace refinement preserves usable keyword results when semantic
ranking fails and provides an explicit retry beside that stage. Paging waits for
the same ranking snapshot; selection and reading stay available after the keyword
first paint. Narrow reader controls use compact visible copy with full accessible
names and a single-line position. Narrow chat places the connection label and
native selector on one row. Current source and cloud verification are recorded in
docs/full-product-repair-2026-11-16.md; static checks do not approve the visuals.

2026-10-28 continuation: narrow saving sessions place icon/count above a full-width
title; month cells use short month/day ranges and retain full accessible dates.
Tested model drafts save without repeating the test, and saved connections expose
their existing state. Cloud evidence and unresolved features are tracked in
docs/handoff-usability-2026-10-26.md. The visual direction remains unapproved.

Latest 2026-10-26 feedback: the product is still unusable. The current repair covers
saved connection reuse, direct thinking effort selection, a visible select-all
capsule, content-sized saving sessions, ordinary mouse scrolling, metadata-only
session organization and local reading text size. Code, remaining reference gaps
and verification limits are in docs/githubstarsmanager-gap-audit-2026-10-26.md.
Application/capture dad2966 passed the four current cloud workflows. The review
matched 163 source fingerprints and 8 downloaded image hashes; 320px month cards
retain the count and date, and long session titles use the available row width.
Browser and installed checks establish their tested scope, with no user aesthetic
approval. The older authorization and successful runs below are historical.

Latest 2026-10-25 request: remove site classification and repeated summary-selection/
consent UI, combine summary and body into Read, generate target-language titles and
summaries with editable defaults, expose Agent thinking settings, and remove the
tray's transparent outer frame. The first 1696889 cloud run passed frontend build
and real OpenCode checks while exposing regression failures. Follow-up adds cited
chat, selected discussions, processing limits, MCP, timeline/health, import outcomes,
site imports and portable reading/chat restoration. These surfaces preserve compact
entry points, component-owned CSS, keyboard semantics and the existing toolbar.
Application/capture 81f310a passed all four cloud workflows; 157 source blob
fingerprints and 9 downloaded media/record fingerprints match. Representative
collection/chat/settings/import and native tray captures were inspected. This is
technical evidence, not user acceptance of the aesthetics. Work is in
docs/desktop-completion-2026-10-25.md; commit/push/PR decisions follow session
authorization. The user has now confirmed this batch's commit, push, new PR and
cloud verification; delivery is in progress. No automatic merge or release.

Overall 2026-10-24 assessment: “还不算好看，能用的样子而已”. The overall appearance
needs improvement. Earlier acknowledgement of progress does not approve or freeze
the current identity, layout, type, colors or material; no individual choice is
newly approved. Final application/capture f1c67fe passed all four workflows with verified
rendered/installed evidence and actual capsule frame bounds. 04ecc11 / 7d2abd0
and the earlier 831dcfd round remain revision-specific history.
The preceding follow-up is in docs/workspace-layout-2026-10-24.md. PR #44 is merged;
its follow-up authorization and results are historical. Application/capture 8af69ae
passed collection 21/21, browser 97/2
(passed/skipped), all 10 CI jobs and the complete installed Windows workflow.
The gallery has 88 PNGs; all 79 sources and 26 selected media/record hashes match.
The installed tray's strict layout is 347px clientHeight / 347px scrollHeight in
both themes. Native toggles, focus dismissal, real OS shortcut, workspace restore,
quit, immediate retry and reinstall/uninstall pass. The retry occurs while the
old service and lock remain alive, then a new owned service passes 12 health checks.
Hosted-CI uses a synthetic tray-opening trigger; actual notification-icon right
click and physical Windows 10/11 or additional-DPI certification are not claimed.
Those runs and failures apply only to the preceding application/capture revision.
Every visual detail remains pending
user review; these technical results do not freeze the design.

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
the collection. Read the AI overview followed by saved text beside a retained index.
The existing toolbar's checkbox/count and Generate action retain selection scope
through paging and failure recovery.

FIRST VIEWPORT: At 1440px a 64px header holds capsule navigation, shared search
and utilities above the collection. A 252px directory spans the entire window
height; duplicate brand/title blocks are removed. Compact actions/status lead
directly to a 280px-minimum card grid (three columns at 1440px/1280px, two at
1024px, one on mobile). The retained desktop reader index is 264px. A narrow modal
reader keeps the background collection's layout, total height and scroll position
unchanged. Settings use the full workspace width. Source, mixed-language titles and
varied summaries remain visible.

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
Searchable access to the full folder/tag directory, parent paths, counts and
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
Per-Agent model and thinking drafts stay independent. Provider/installation/credential
or inherited-default changes invalidate stale catalogs and tests; changing the model
or effort requires a fresh test. Empty effort inherits the client/model default;
OpenCode exposes available variants. Endpoint thinking controls preserve unrelated
advanced JSON options and explain format compatibility.
A failed save remains visibly unsaved. Once preference saving succeeds, a later
settings/status read failure preserves that acknowledgement and offers a read-only
recovery action. Processing changes share the parent action gate and preserve
unrelated model drafts. Extension status belongs to the visible category, keeps
the last confirmed connection fact after read failures, and never overlaps slow
reads. Pairing copies remain available. Update checks show their in-flight state,
bounded error details and separate release/CI download links. These recovery styles
belong to settings-maintenance.css and retain native keyboard semantics.

The native select-all checkbox and one Generate button occupy the existing action
toolbar; individual selection does not add a row or enter bulk management. Generation
starts directly after an internal count/revision check. No repeated model-consent or
force checkbox is required. Selections reprocess completed records; no selection
handles eligible pending/failed/changed entries in the current scope. Zero eligible
items cannot start. Library or prompt changes invalidate stale previews. Management/export scope remains
separate from processing scope. Resume/retry uses the original durable target
snapshot, language and writing instructions, preserves completed entries and only
handles its unfinished/failed entries.

Summary language follows the UI by default or an explicit Chinese/English choice.
An expandable editor exposes the actual built-in writing instructions, accepts custom
text and restores defaults. Its save action does not retest chat. Generated titles,
summaries and key points use the target language; original titles/text remain saved.
Language/prompt changes make old derived content eligible for regeneration.

## Controls, reading and motion behavior

Preserve click currentTarget, Enter/Space activation, form submission, labels,
disabled/pending state, focus containment/return and caller preventDefault semantics.
If a library adapter changes, verify these contracts before applying it everywhere.
Each element/property has one animation owner. Closing overlays must stop accepting
input immediately; rapid reversal and live reduced-motion changes remain safe.

Reader layouts may change. Body text is 17px/1.8 (16px mobile), titles are
29px/700 (25px mobile, 32px focus). The compact index hides duplicate excerpts,
tags and folder paths while retaining source, title, status and actions.
Only a visible desktop index may reveal the selected whole card. Hidden, inert or
aria-hidden lists never auto-scroll; focus-mode reversal restores the settled index.
Read combines the AI overview/key points and saved source text. Original title and
retrieval questions remain in expandable details. Missing-body inference and source
labels remain explicit; failed regeneration retains the previous derived content.
Read also has an independent personal-note section, with an inline editor, exact
local drafts, full text disclosure, original-save confirmation and explicit review
of another window's saved version. Note controls remain usable without a model and
own their CSS in reader-notes.css. Older import text is disclosed separately.
Only reading with saved body text has an in-flow progress footer; related/empty states
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
keyboard roving focus and bounded monitor-aware geometry. Select a full monitor's
bounds before clamping to its work area and applying that monitor's DPI. Reused
windows replay one interruptible entrance on every open, with a static reduced-motion
endpoint. Native menu actions
are restricted to that local page. Construct it hidden and unfocused; request
focus only on visible opening and keep native blur dismissal. Placement keeps
the complete physical outer frame within the work area: measure
outer/client offsets at the target DPI before passing a client size to set_size.
The opaque menu fills the client viewport. Remove transparent outer padding and
native shadow while preserving the inner menu and rounded-corner alpha.
Cloud HTML fixtures remain separately labeled. Actual physical-frame restoration, quiet
geometry persistence and sidecar cleanup require installed verification.

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
