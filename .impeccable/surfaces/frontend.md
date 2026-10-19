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
---

# Collection workbench, connection settings and task recovery — Operate

## Direction contract — 2026-10-19 replacement

THESIS: A desktop collection app with stable application navigation and a separate
searchable directory. The user rejected the earlier PR #44 appearance and the lack
of click/switch feedback. This replacement changes the entire working composition;
the former 10/18 visual contract is superseded.

OWN-WORLD: FlClash-informed tonal Material surfaces: lavender workspace and rail,
white content surfaces, plum text and violet selection. Bundled Inter and Noto Sans
SC establish Latin/Chinese consistency. GithubStarsManager informs the distinct
directory, compact search/management rows and source/title/description/action
hierarchy. The implementation uses 10px controls, 16px cards and 24px support/dialog
surfaces, with reader-specific shape exceptions in DESIGN.md.

STORY: Pick a collection, scan useful summaries, open the original or preview,
and organize selected entries. Navigation keeps its place. Search drafts, selected
items, model configuration, task snapshots and original browser data retain their
existing contracts.

FIRST VIEWPORT: A 96px vertical rail, a separate 13.5rem directory and flexible
results. Title and search occupy an 80px workspace row; maintenance and status
controls sit immediately above results. Compact desktop uses an 84px rail and 200px
directory. Titles are 16px/600 and descriptions 15px. Below 960px, navigation becomes
a 56px header and categories move into the focus-managed drawer; mobile stacks title
and search and keeps principal actions at least 44px high.

FORM: Concept seed `seed:18a549514c513706` assigned candidate 4. The user's repeated
GithubStarsManager and FlClash references pin the competitor-informed canon and
override that random direction. They are structural and behavioral references,
not approved Facetmark mockups or aesthetic approval. Exact implementation tokens
live in [DESIGN.md](../../DESIGN.md).

MOTION: Shared selection surfaces connect successive choices; bounded ink responds
to clicks and keyboard activation; content transitions follow navigation and filter
results; card/list changes animate positions; overlays enter and exit. Theme changes
reveal the new palette from the clicked control. Existing reading effects remain.
State and focus update immediately. Live reduced motion disables spatial effects.

FINISH: Verify composition and actual interaction sequences on the built application,
including installed Windows. A source-matched capture set and fresh visual review
are required before claiming completion or user acceptance.

## Collection and directory

Keep Add / Manage / Summarize distinct from summary status, sort and Display.
Display changes summaries/excerpts; processing scope and consent belong in the
processing dialog. The card/list selector changes layout while preserving the
same title/summary hierarchy. Original links, checkboxes, editing and Preview are
independent. Summary expansion uses actual clipping; loading, missing text and
failed summaries have specific next actions.

The directory provides folder/tag/site modes, local search, vertical scrolling,
counts, full paths and explicit pagination. Organize folders and tags is directly
available. Add/edit/move use the shared FolderPicker: 50-item pages, exact choice,
separate search draft, explicit Unfiled/new-folder choices, local loading/retry,
keyboard navigation and focus return. A new folder is created only on save.

Maintain server-side paging and scoped selection for 200,000-record libraries.
Context changes clear incompatible selection; stale result contexts cannot drive
scoped actions. Card reflow, filter changes and rapid repeated choices must preserve
scroll position, focus and the final selected state. On mobile, confirm readable
content, no horizontal document overflow and unobscured action targets; prior
first-viewport measurements do not certify this replacement composition.

## Connection settings and processing

Summary and optional embedding channels use separate full-width sections with
purpose/status, essential fields, model choice, test/save and adjacent feedback.
Fields become one column on narrow screens. Settings tabs remain mounted while
hidden so their animated switch preserves drafts and results. Advanced paths and
timeouts follow the main actions.

Discovery identifies the actual available Agent. Catalog source, configured default,
manual model entry and retry remain visible. Per-Agent drafts stay independent;
installation/provider/credential changes invalidate stale catalogs or tests. Model
changes require a fresh test. Test connection is separate from Test and save; save
failure remains visibly unsaved. Successful chat saving offers summary generation,
whose dialog still requires scope review and content-processing consent.

Zero eligible items disables Start. Library changes invalidate scope previews.
Explicit IDs or server scope with exclusions define processing targets without
changing management/export scope. Pause finishes the current batch. Resume/retry
uses the original durable snapshot, keeps completed entries and retries only its
unfinished/failed targets. Tasks presents scope, truthful state, progress, errors
and recovery before new-work shortcuts. Settings and Tasks provide return controls.

## Reading and motion acceptance

Desktop preview pairs a compact index with an independent reading surface. Focus
mode expands it without removing application navigation. Narrow preview contains
focus and restores the initiating control. Retain real-heading navigation, measured
saved-body scroll progress, the glass capsule, native chapter selection and the
spring outline plane. The final paragraph and current chapter must remain correct
through resize, rapid selection and a live reduced-motion preference change.

Check navigation pill movement, directory/status/layout/settings switches, content
entry, keyboard ink, theme reversal, menu/dialog close and immediate inertness.
Check model and folder search during fast open/close and delayed responses. A still
screenshot cannot establish these behaviors. [UI motion tools](../../docs/ui-motion-tools.md)
records animation ownership and timing.

## Verification and references

This source-derived pass targets `ac90d24805e346ba974a197da72a59cdac11231f`.
Initial replacement runs are [Experience](https://github.com/88lin/facetmark/actions/runs/39193153703),
[Windows](https://github.com/88lin/facetmark/actions/runs/39193153702) and
[CI](https://github.com/88lin/facetmark/actions/runs/39193157986). A complete final
verification set and fresh visual review remain pending. These links record the
initial source snapshot; use [PR #44 checks](https://github.com/88lin/facetmark/pull/44/checks)
for current source and outcomes. The sidecar examples are source specimens, not
rendered proof or visual approval.
Earlier results belong only to [validation history](../../docs/desktop-validation.md).

[GithubStarsManager](https://github.com/AmintaCCCP/GithubStarsManager) contributes
separated browsing regions, compact content hierarchy, explicit category selection
and local press/menu feedback. [FlClash](https://github.com/chen08209/FlClash)
contributes the application rail, tonal surface hierarchy and Material selection
continuity. Reference images establish neither implementation correctness nor user
acceptance. Use synthetic libraries and isolated fixtures; never personal browser
profiles or bookmarks for verification.
