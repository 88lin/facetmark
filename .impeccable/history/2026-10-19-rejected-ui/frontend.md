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

# Capsule collection workspace, settings and task recovery — Operate

## Direction contract — 2026-10-19, after the second rejection

THESIS: One unified sidebar for application navigation and searchable categories,
with a spacious content canvas. The user explicitly rejected the lavender/10px
replacement at `082e36d`, required full capsule controls and authorized a rebuild
using HeroUI and GSAP. The [workbench contract](../workbench-direction.md) is the
current direction authority; historical visual contracts are superseded.

OWN-WORLD: White and softly shaded neutral surfaces, graphite text and local indigo
actions/selection. Inter and Noto Sans SC stay bundled. Complete capsule controls,
circular icon buttons, 22px cards, 28px sidebar/support panels and 24px menus give
controls and surfaces distinct proportions. Page/item/summary/control/metadata
roles use 28/18/16/15/13px, with responsive heading exceptions in DESIGN.md.

STORY: Select a collection, scan useful descriptions, open the original or preview,
and organize chosen entries. Navigation and categories share one place. Search
queries, IME composition, selected entries, model configuration and task snapshots
keep their actual functional meaning during transitions.

FIRST VIEWPORT: A 244px unified sidebar, 12px shell padding and gap, and a flexible
collection canvas. Main destinations stack as full-width capsules; utilities use
40px circles with accessible labels/tooltips. Category-type segments keep text labels
without redundant icons. Compact desktop uses 224px; wide desktop 260px. A 76px title/search
row precedes maintenance and status controls. Below 960px navigation becomes a 56px
header and categories use the existing focus-managed drawer. Below 720px title and
search stack, cards use one column and principal actions retain 44px targets.

FORM: HeroUI leads actual component construction. GithubStarsManager informs
collection organization; FlClash informs selected-state continuity and layered
transitions. Repeated user instructions override the earlier random concept seed.
The references are not approved Facetmark mockups. [DESIGN.md](../../DESIGN.md)
owns implementation tokens and [the sidecar](../design.json) carries source specimens.

MOTION: HeroUI owns button press/focus states. GSAP composes directional page,
settings-section, category, pagination and filter timelines in existing containers.
Named heading/content positions and interrupted paint state preserve continuity.
Motion owns selection capsules, card entry/reflow and overlay presence. The theme
uses an interruptible circular View Transition; reader effects remain. State and
focus update immediately. Live reduced motion removes travel while retaining controls.

FINISH: Fresh cloud builds, browser/installation checks, settled-font captures,
continuous click recordings and a full independent review are required after this
rejection. No historical ship verdict establishes current acceptance; user aesthetic
approval is not recorded.

## Collection and unified sidebar

Keep Add / Manage / Summarize separate from summary status, sorting and Display.
Display changes summaries/excerpts; processing scope and consent stay in the dialog.
Card/list changes retain 18px titles and 16px descriptions. Original links,
checkboxes, editing, summary actions and Preview are independent. Expansion uses
measured clipping through a footer icon with an explicit accessible name; summary
provenance is a 13px inline label. Missing/failed content has a specific next action.

Application destinations and the searchable folder/tag/site directory share one
sidebar. Preserve vertical scrolling, full accessible paths, counts and complete
pagination. Organize folders/tags remains directly available. On short desktop
windows every utility and category stays reachable; on narrow screens the drawer
keeps focus containment, Escape and focus return.

Add/edit/move use the shared FolderPicker: 50-item pages, exact choice, separate
search draft, explicit Unfiled/new-folder choices, local loading/retry and keyboard
navigation. A new path is created only on save. Model choices begin with a bounded
100-item rendered page and explicit more rather than an unbounded option surface.
Preserve searchable access to the complete catalog.

Maintain server paging and scoped selection for 200,000-record libraries. Context
changes clear incompatible selection, stale results cannot drive scoped actions,
and rapid navigation preserves the final query, selected state and scroll context.
Check the 390px collection and short-window desktop composition; earlier density
measurements do not certify this rebuilt layout.

## Model settings and task recovery

Summary and optional embedding channels retain independent full-width sections
with purpose/status, essential fields, model choice, test/save and nearby feedback.
Settings use capsule tabs and preserve mounted hidden panels so switching does not
lose drafts or results. Narrow screens use one field column. Advanced paths and
timeouts follow the essential actions.

Discovery identifies the actual Agent. Catalog source, configured default, manual
entry and retry remain visible. Per-Agent drafts stay independent; provider,
installation or credential changes invalidate stale catalogs/tests. A model change
requires a fresh test. Catalog discovery, successful test, persisted save and actual
summary use remain separate states. A failed save stays visibly unsaved.

Processing requires scope review and content consent. Zero eligible items disables
Start; library changes invalidate scope previews. Explicit IDs or server scope with
exclusions identify targets without changing management/export scope. Pause completes
the current batch; resume/retry uses the original durable snapshot, keeps completed
entries and handles only the snapshot's unfinished/failed targets. Tasks presents
scope, truthful state and recovery before new-work shortcuts.

## Native controls, reading and motion acceptance

Exercise the real HeroUI wrapper in native click, Enter/Space, implicit submission,
label activation, disabled/pending state and form flows. Anchored actions must receive
the actual button currentTarget; keyboard handlers and caller preventDefault remain
meaningful. HeroUI press must not stack with fallback CSS or another engine.

Check application destination, directory type/choice, status, card/list, settings
and pagination in continuous sequences, including rapid reversal and delayed data.
GSAP cleanup must remove temporary styles without losing the final visible content.
Verify overlay closing immediately removes interaction/focus eligibility, while
visual exit completes; check theme reversal and a live reduced-motion change.
Static screenshots alone cannot establish these behaviors. Detailed motion ownership
and capture-settling rules are in [UI motion tools](../../docs/ui-motion-tools.md).

Desktop preview uses an independent article surface beside a compact result index;
focus mode expands within the content area. Narrow preview contains focus and returns
to its initiating control. Retain real-heading navigation, actual article progress,
the glass capsule, native selector and spring outline plane. Resize, long labels,
rapid chapter choice and reduced motion must leave the final paragraph unobscured
and the selected chapter correct.

## Evidence status and references

This pass records rebuild base `1f2a4ce8037c41c7dc279954cecc1a8de527ba0d` and the
subsequent working-tree navigation-fit corrections, after rejected
`082e36d53a19acc1553a5ea3ce8482fe5d526826`. The final correction revision, complete
cloud run set, fresh captures/recordings and independent reviewer verdict are pending. No user
aesthetic approval is claimed. Source specimens illustrate appearance and CSS
states; they are not HeroUI/GSAP runtime tests or rendered evidence.

Use [PR #44 checks](https://github.com/88lin/facetmark/pull/44/checks) for current
source/results and [desktop validation](../../docs/desktop-validation.md) for the
recorded evidence and historical boundaries. Tests and captures use synthetic
libraries and isolated fixtures, never original browser profiles or personal data.

[HeroUI](https://www.heroui.com/) leads control quality and actual library use.
[GithubStarsManager](https://github.com/AmintaCCCP/GithubStarsManager) informs
collection organization. [FlClash](https://github.com/chen08209/FlClash) informs
selection continuity and layered transitions. Reference source/images do not prove
Facetmark implementation correctness or user acceptance.
