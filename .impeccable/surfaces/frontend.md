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
---

# Facetmark frontend — Operate

## Direction status

The user rejected PR #44's incumbent collection screen and requested a complete
replacement on 2026-10-23. The limestone/orange collection, earlier capsule UI,
Orbit-folder exception and teal prototype have no visual authority. The current
round is implementation in progress; user visual review is pending.

Long-term reference: `E:\design\design-reference-handbook.md`, v0.11, sections
1, 5, 6.2 and 7. Its historical project claims were checked against PR #44 at
`eda094d3a7ba40a46dd47d67988d109ee335723d`. S17–S20 inform relationships, not
approved components. The supplied startup prompt is the task authority.

## Direction contract

THESIS: A collection for returning to ideas. A continuous reading list gives
Chinese titles and useful excerpts the main visual weight, with navigation and
processing scopes fixed around it. Uniform dashboard tiles do not organize it.

OWN-WORLD: Pale iris navigation, blueberry ink, soft white content and a coral
brand detail. A compact folded-bookmark mark, gently molded controls and shallow
raised overlays distinguish navigation, collection and protected operations.
Smiley Sans is restricted to the collection heading; body and controls use the
bundled CJK sans and platform fallbacks.

STORY: Choose a directory or search a remembered phrase, scan sources and text,
open an original or inspect the saved page. Select continuously across pages;
management IDs and summary scopes remain distinct and explicit.

FIRST VIEWPORT: At 1440px, a 248px unified left navigation/directory faces a broad
white reading workspace. Title/count and search occupy its top band; add/manage/
summary actions, status tabs and view controls sit above records. Source badges,
Chinese titles, excerpts, tags and actions share stable alignments. A selected
record opens a right reader beside the retained index. At narrow widths navigation
opens as a drawer and reading becomes a focus-managed layer.

FORM: Direct, delegated working choice based on the current brief and inspected
S17/S18 source snapshots. Operate, code-led. seed: none (not run).

SIGNATURE: A shared selection highlight slides within each local tab group;
record selection and the fixed action strip echo the same real selection.
Reader opening preserves the index and animates the incoming pane. Interruptible
160–320ms motion follows state; reduced motion reaches the same visible endpoint.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish
review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## Collection and navigation behavior

Keep Add / Manage / Summarize distinct from summary status, sorting and display.
Original links, selection, editing, summary actions and preview remain independent.
Descriptions must remain readable; measured clipping determines expansion.
Searchable access to the full folder/tag/site directory, parent paths, counts and
pagination must remain available at narrow and short viewport sizes.

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

Reader layouts may change. Keep actual heading navigation, article progress,
chapter selection and an unobscured final paragraph. Resizing and closing preview
must preserve meaningful reading/search context. Existing glass/plane artwork and
layout are not mandatory; their underlying progress and navigation behavior is.

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
