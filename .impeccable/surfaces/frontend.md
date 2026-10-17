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
  - "frontend/src/Tasks.tsx"
  - "frontend/src/Reader.tsx"
  - "frontend/src/styles.css"
  - "frontend/src/workbench.css"
  - "frontend/src/collection-tools.css"
  - "frontend/src/support.css"
---

# Collection, connection settings and exact task recovery — Operate

## Current refinement — 2026-10-17

Implement the complete discovery → model selection → test/save → scoped summary →
recovery journey. The user rejected repeated isolated edits. Preserve white/lake blue,
18px/700 collection titles and 15px descriptions. Shared controls use 7px corners;
navigation and support sections are unboxed. The authoritative direction is
[workbench-direction.md](../workbench-direction.md), with visual tokens in
[DESIGN.md](../../DESIGN.md).

## Collection composition

The first action row contains Add, Manage and Summarize plus the card/list choice.
Manage exposes maintenance commands in a compact menu. The next row contains
summary-status counts, visible sorting and Display. Display switches Summaries /
Excerpts only; processing scope belongs in the summary dialog.

The desktop category directory remains searchable and vertically scrollable.
Narrow windows use a filter drawer. Original links, selection, direct editing and
Preview stay independent. Multiline content remains visible in both collection views;
expansion responds to actual clipping. Cross-page selection appears only while
selecting or when a selection exists, and it names its summary-processing scope.

Acceptance targets: results viewport/list top at or before 210px on desktop and 270px on mobile,
two complete cards at 390 × 844, no horizontal document overflow, and at least 44px
main mobile actions. Exact-source measurements meet these targets; see the validation record for list-top and first-card values.

## Connection settings composition

Use a full-width summary section followed by a separate optional embedding section.
Each has purpose and status, a two-column field grid, its full-width model picker,
test/save actions and local feedback. At 720px and below, the grid becomes one column.
Keep the primary test/save action in the first 390 × 844 Agent settings viewport.
Timeout and installation paths follow the actions in a disclosure.

The four settings categories use keyboard-operable underlined tabs. Inactive panels
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

At source `4c6383ad0537bccb85ce32f76fc11fe3f9e139e8`, Experience, all ten CI jobs
and Windows installation checks passed. All 80 final Web PNG hashes match provenance;
density and installed-app behavior are verified in
[desktop validation](../../docs/desktop-validation.md). Five source-review corrections
are resolved. The fresh independent review inspected 15 Web captures and two installed
captures and returned **ship**: all eight original findings resolved, no remaining
material findings in the reviewed scope. A generic reviewer substituted for the
unavailable specialist; it did not inspect all 80 Web captures or run a browser.
This verdict supports the complete reviewed improvement scope, not user aesthetic
approval, personal-account permissions or all-Windows certification. Prior passes
apply only to their recorded revisions. Use synthetic data and isolated HTTP model fixtures,
never personal libraries or browser profiles.
