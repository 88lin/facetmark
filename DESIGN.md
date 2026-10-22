---
name: Facetmark collection workspace
description: Pale-iris collection workspace; current implementation awaiting cloud verification and user review.
---

# Facetmark collection workspace

The 2026-10-23 round replaces the rejected PR #44 collection direction. This is
an implemented working choice, awaiting current-source cloud verification and
user visual review. Historical d40471f checks apply only to the rejected revision.

## Composition and material

A 248px pale-iris column combines navigation and the searchable directory. The
white collection workspace has a title/search band, separate add/manage/summary
actions, status and display controls, a continuous reading list and fixed paging.
Sources, titles, excerpts, tags and entry actions align across records. Card view
is optional. The right reader retains a narrow collection index at 1120px and
above; below that it uses a focus-managed drawer. Navigation becomes a drawer
below 960px. Short windows compact utility controls to preserve directory space.

Light: navigation `#eeebf8`, surface `#ffffff`, text `#28243d`, secondary text
`#605c76`, accent `#6544bb`. Dark: navigation `#282238`, surface `#211e2d`, text
`#f0ecfb`, secondary text `#c3bdd9`, accent `#c3a8ff`. Semantic success, warning and
failure colors are separate from the accent. A coral fold marks the brand.
Subtle inset search and raised overlays distinguish content and actions.

Smiley Sans is bundled under OFL and used only for the collection heading
(34px/400, 30px on compact layouts). Body and controls use platform sans with
bundled Noto Sans SC fallback. Record titles use 18px/650, summaries 15px/1.75.
Chinese headings have no negative letter spacing. Radius follows component role:
12px standard controls, 14px search, 20px reader, 10px local selection tabs.

## Ownership and interaction

- `workbench.css`: application navigation, directory placement, collection geometry,
  search, footer, responsive layouts and focus-mode geometry.
- `bookmark-card.css`: source badge, native original links, summaries, status,
  tags, checkboxes and local record actions. Metadata remains visible.
- `facet-browser.css`: bounded searchable directory; literal API paths stay exact.
- `collection-tools.css` / `library-tools.css`: distinct status, processing scope,
  cross-page selection, management and create/edit flows.
- `reader-shell.css`: reading typography, controls and progress positioning.
- `ui/controls.tsx`: existing HeroUI native event/form bridge; unchanged this round.

Local selection highlights, checkbox fills, folder fronts and reader transitions
follow real state and support rapid reversal. Reduced motion reaches the same
usable endpoint. Styles superseded by this round are removed at their owner.

## References and verification

The supplied handbook v0.11 and S17/S18 source snapshots inform soft-surface/dark-ink
pairing and Chinese display/body hierarchy. S20 informs semantic color roles;
oil-ui/Taste contribute selected interaction and composition methods. None is an
approved Facetmark template. See [round record](docs/collection-workspace-2026-10-23.md).

Cloud review uses a temporary synthetic SQLite library, current-source captures and
an interaction recording. Current results are pending; local checks are lightweight
source/static checks only. No real browser profile is used. User review is pending.
