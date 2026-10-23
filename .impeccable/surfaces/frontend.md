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

The user rejected pale-iris revision 46cf2f3 on 2026-10-23 in full. Capsule buttons,
sophisticated motion and rich material are explicit requirements. This replacement
is implemented for cloud review; aesthetic acceptance is pending.

Long-term reference: the supplied design handbook, S17–S20 and its latest feedback
record. Source-inspected relationships inform the work; no reference is a template.

## Direction contract

THESIS: A personal collection with a clear reading surface and tactile controls.
Actual saved content carries the composition.

OWN-WORLD: Mist-blue surroundings, porcelain cards, deep ink navigation and electric
blue primary actions. Frosted directory and toolbar layers establish depth; capsule
controls have molded edges and moving highlights. Inter and Noto Sans SC provide
firm, upright type with distinct display, title and description scales.

STORY: Enter through floating navigation, choose an exact directory, search or scan
the collection. Read beside a retained index. Selection and summary scopes remain
visible and separate through paging and failure recovery.

FIRST VIEWPORT: At 1440px an 88px top band holds identity, capsule navigation and
utilities. A 244px frosted directory faces the rounded collection surface. Title
and capsule search lead to actions/status and reading cards in an adaptive grid
(three columns at 1440px, two at 1280px, one in narrow windows).
Source medallions, mixed-language titles and summaries stay visible. Short windows
compact the chrome; narrow screens retain focus-managed directory and reader layers.

FORM: Delegated code-led replacement based on explicit feedback and inspected
S17/S19 source relationships. No generated mock comp or concept tournament.

SIGNATURE: Local light follows the pointer on a record without moving its hit area;
the source medallion settles on hover. Selection highlights spring between states.
Cards rearrange continuously, folders unfold when selected and dialogs spring into
protected focus. Reduced motion retains each usable endpoint.

FINISH: Inspect source-matched cloud renders and video, obtain a fresh finish review
and document the actual implementation. None confers user aesthetic approval.

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
