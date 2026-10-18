---
version: 1
slug: "frontend"
primary_target: "frontend"
related_targets:
  - "frontend/src/App.tsx"
  - "frontend/src/Settings.tsx"
  - "frontend/src/SettingsWorkspace.tsx"
  - "frontend/src/ModelPicker.tsx"
  - "frontend/src/Setup.tsx"
  - "frontend/src/CollectionTools.tsx"
  - "frontend/src/LibraryTools.tsx"
  - "frontend/src/BookmarkCard.tsx"
  - "frontend/src/FacetBrowser.tsx"
  - "frontend/src/FolderPicker.tsx"
  - "frontend/src/folder-picker.css"
  - "frontend/src/Tasks.tsx"
  - "frontend/src/Reader.tsx"
  - "frontend/src/styles.css"
  - "frontend/src/workbench.css"
  - "frontend/src/collection-tools.css"
  - "frontend/src/support.css"
---

# Collection, connection settings and exact task recovery — Operate

## Current refinement — 2026-10-18

Implement the complete discovery → model selection → test/save → scoped summary →
recovery journey. The latest user correction rejects Manrope and the lake-blue
palette and names GithubStarsManager and FlClash as references. Use neutral
light/dark surfaces, system typography, 16px/600 collection titles, 15px descriptions
and 14px controls. Global body and principal inputs remain 16px. Preserve the
previously restored capsule actions/navigation, 16px collection cards, 20px support
surfaces and soft shadows; form fields retain a separate 12px radius. Folder
selection uses neutral fill plus a blue check; actions and focus use blue.
The authoritative direction is [workbench-direction.md](../workbench-direction.md),
with visual tokens in [DESIGN.md](../../DESIGN.md).

Restore the Rare UI reading effects as well as shape: a floating glass progress
capsule, animated chapter label and a paper plane following the actual current
heading. Collection entries use a short bounded stagger. Preserve native keyboard
controls, actual scroll measurements, rapid reversal and reduced-motion behavior.

## Collection composition

The first action row contains Add, Manage and Summarize plus the card/list choice.
Manage exposes maintenance commands in a compact menu. The next row contains
summary-status counts, visible sorting and Display. Display switches Summaries /
Excerpts only; processing scope belongs in the summary dialog.

The desktop category directory remains searchable and vertically scrollable.
Narrow windows use a filter drawer. An Organize folders and tags action sits beside the
directory heading. Add, edit and move dialogs use the searchable FolderPicker:
50-item pages from the complete directory, separate search drafts, exact selection,
explicit Unfiled and new-folder choices, and local loading/no-match/retry states.
Typing never commits a path. New folders are created when the bookmark is saved.
Arrow keys, Home/End, Escape, button activation and focus return remain available.
Original links, selection, direct editing and
Preview stay independent. Multiline content remains visible in both collection views;
expansion responds to actual clipping. Cross-page selection appears only while
selecting or when a selection exists, and it names its summary-processing scope.

Acceptance targets: results viewport/list top at or before 210px on desktop and 270px on mobile,
two complete cards at 390 × 844, no horizontal document overflow, and at least 44px
main mobile actions. Previous measurements are historical; the restored styling
still needs fresh browser validation in GitHub Actions.

## Connection settings composition

Use a full-width summary section followed by a separate optional embedding section.
Each has purpose and status, a two-column field grid, its full-width model picker,
test/save actions and local feedback. At 720px and below, the grid becomes one column.
Keep the primary test/save action in the first 390 × 844 Agent settings viewport.
Timeout and installation paths follow the actions in a disclosure.

The four settings categories use keyboard-operable capsule tabs with selected fill. Inactive panels
stay mounted and hidden, preserving drafts and results. The tab row scrolls
horizontally on narrow screens. Settings, Tasks and preview provide explicit return.

## Model states and transitions

- Detection identifies executable availability and the actual automatic Agent.
  Detection failure and no installation are different states.
- The picker is visible beside essential configuration, with search, configured
  default, model ID, manual input and refresh. The API variant combines an editable
  model input and catalog arrow in one field. Agent catalogs can be live, cached,
  configured or aliases; each must explain its limits. API catalogs do not establish
  model access either.
- Changing the actual installation or connection identity clears stale catalogs.
  Agent changes preserve independent model drafts. A changed model invalidates its
  test; draft editing does not immediately rewrite saved settings.
- Test connection reports the tested model. Test and save persists only after a
  successful test. A failed save remains visibly unsaved. The optional embedding
  channel keeps independent state.
- A saved chat connection offers Start generating summaries. The next dialog still
  requires scope review and content-processing consent.

Search, arrow navigation, Enter selection, Escape dismissal, outside/Tab dismissal
and return focus belong to the picker/menu contract. Loading, no match, unavailable
catalog, stale identity and connection/save failures remain actionable.

## Processing and recovery

The dialog previews scope and eligible count, explains reprocessing, and requires
a saved tested connection plus consent. A changed library invalidates the preview.
Selections use either explicit IDs or server scope with exclusions; they do not
silently change management/export targets.

Partial, failed, paused, cancelled and interrupted non-index tasks can retain a
durable snapshot. Resume/retry carries the original task ID and snapshot, preserves
completed entries and retries only its failed/unfinished targets. Distinguish this
from deliberately starting a new task for all failed bookmarks in current filters.

Tasks places scope, state, progress, relevant errors and recovery above new-work
shortcuts. Only running describes background execution. Saved recovery must remain
visible in the first mobile viewport.

## Verification and boundaries

Use [PR #44 checks](https://github.com/88lin/facetmark/pull/44/checks) for the
latest pushed source and Actions outcomes. At historical source `3a9c49a`, run
[39127258266](https://github.com/88lin/facetmark/actions/runs/39127258266) built and
rendered the UI: 66 browser tests passed, including folder creation, editing, bulk
moves and keyboard cases; three reader-motion cases failed on the footer's
last-chapter label and live reduced-motion behavior. Six captures matched provenance.
Independent visual review found typography, palette, depth and folder layout
consistent with the direction, with no new visual fixes; the reader mismatch
remained. Reader corrections were pushed at `29ed015`; their verification is
recorded in the linked checks, not inferred from the initial run or review.

GithubStarsManager `repo.png` and FlClash `preview.png` remain external references,
not Facetmark evidence. Sidecar specimens are source-derived examples. All results
below remain scoped to their named historical revisions; no user aesthetic approval
is implied.

At source `0993020882434593932d3d50ad5ad25594b0531f`, Experience 39089551750,
all ten CI jobs and Windows installation checks passed. That revision fixes
delivery and state defects rather than changing the visual contract: the served
page is the React build again, pagination keeps the current rows, list-view rules
no longer contradict each other, the grid uses a 310px minimum card, mobile row
actions meet 44px, and that revision's splash used its then-current white/lake-blue tokens. The
current record lives in [desktop validation](../../docs/desktop-validation.md).

The `ship` verdict below belongs to `4c6383ad0537bccb85ce32f76fc11fe3f9e139e8`
only; no fresh independent visual review or user aesthetic approval is claimed
for the newer revision. At that earlier source, all 80 final Web PNG hashes match
provenance, five source-review corrections are resolved, and the independent
review inspected 15 Web captures and two installed captures: all eight original
findings resolved, no remaining material findings in the reviewed scope. A generic
reviewer substituted for the unavailable specialist; it did not inspect all 80
Web captures or run a browser. Prior passes apply only to their recorded
revisions. Use synthetic data and isolated HTTP model fixtures, never personal
libraries or browser profiles.
