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
- frontend/src/interaction-motion.css
---

# Facetmark frontend — Operate

## Direction status

**Replacement pending. The current icons, layout, styling and colours are rejected
in full, including the earlier folder-glyph exception.** The sole active visual
brief is [the current redesign requirements](../workbench-direction.md); the product
contract is [PRODUCT.md](../../PRODUCT.md). Existing screenshots, code and the
history directory describe the rejected implementation, not a desired appearance.

The user has delegated the redesign. Choose and implement a coherent replacement
without restarting settled preference questions. A full working first viewport
must establish a different composition and interaction treatment before expansion
to the other routes. There is no prescribed sidebar width, grid, palette, icon set,
font family, control radius or number of effects in this pending brief.

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
