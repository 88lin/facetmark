# Facetmark tonal collection workbench — Operate

## Current direction contract — 2026-10-19 replacement

USER EVIDENCE: The user rejected PR #44's existing appearance and its lack of click/switch motion, and explicitly requested a real reconstruction using GithubStarsManager and FlClash. This replaces the 10/18 visual direction. Historical technical passes and screenshot reviews are not aesthetic acceptance of this replacement.

THESIS: Stable application navigation, a separate collection directory and readable content. Selecting a destination, folder, status, layout or settings section has visible continuity while focus and data update immediately. Preview remains optional; original links remain direct.

OWN-WORLD: Lavender/plum Material tonal surfaces with violet actions and selection; bundled Inter plus Noto Sans SC. Desktop uses a 96px rail, 13.5rem directory and 80px title/search row, becoming 84px/200px on compact desktop. Below 960px the rail becomes a horizontal header and directory uses the existing drawer. Shared controls use 10px corners, cards 16px, support/dialog surfaces 24px; the reader retains its own capsule and 20px sheet. Collection titles are 16px/600 and descriptions 15px. DESIGN.md frontmatter is the token authority; workbench.css owns final application layout overrides and reader-shell.css owns reading internals.

COLLECTION: Separate maintenance actions from summary status, sort and Display. Cards and list rows preserve source/title/description/folder/action hierarchy, independent original links and preview, and actual-clipping expansion. Directory modes, local search, counts, paths and full pagination remain operable. Exact FolderPicker selection is distinct from search drafts; Unfiled and new paths are explicit. Preserve server paging and scoped selection for large libraries.

SETTINGS AND TASKS: Keep model discovery, catalog provenance, explicit choice, test, save and actual use distinct. Preserve independent Agent drafts and optional embedding. Place essential model fields and feedback before advanced settings. Processing requires scope review and consent; task recovery uses the original snapshot and preserves completed entries. State, failures and recovery appear before new-work shortcuts.

MOTION: SelectionPill uses shared Motion layout surfaces. useContentMotion uses WAAPI for bounded container entry after navigation, classification and loaded-context changes. Ink is a noninteractive paint layer. Motion owns card position reflow and entry; OverlayMotion owns dialog/menu/scrim presence and immediate inertness on close. CSS owns press/hover state and native details-menu feedback. Theme uses an interruptible circular View Transition with immediate fallback. GSAP keeps reader focus translation and tab-marker geometry; Motion keeps reader presence, progress and the outline plane. No property has two animation owners. Live reduced motion removes spatial effects and ink without removing controls or state.

REFERENCE: [GithubStarsManager](https://github.com/AmintaCCCP/GithubStarsManager) informs the separated directory/search/results composition, compact source-first cards, explicit category selection and press/menu feedback. [FlClash](https://github.com/chen08209/FlClash) informs the rail, tonal Material surfaces and selection continuity. This is an independent adaptation; reference images are not approved Facetmark mockups, and reference behavior is not evidence that the application passes.

FORM: Concept seed `seed:18a549514c513706` assigned candidate 4; the user's repeatedly supplied references pin the competitor-informed canon and override the random direction. This provenance records the implementation choice, not user aesthetic approval.

FINISH: Review the built composition and real interaction sequences, including installed Windows, both themes, narrow layouts, rapid reversal, keyboard operation and live reduced motion. Preserve source-matched screenshot provenance. Do not infer visual acceptance from source checks, reference images or historical results.

## Verification status

The source recorded for this pass is `ac90d24805e346ba974a197da72a59cdac11231f`.
Initial runs are [Experience 39193153703](https://github.com/88lin/facetmark/actions/runs/39193153703),
[Windows 39193153702](https://github.com/88lin/facetmark/actions/runs/39193153702) and
[CI 39193157986](https://github.com/88lin/facetmark/actions/runs/39193157986). A complete
final verification set, fresh capture review and visual approval remain pending.
Use [PR #44 checks](https://github.com/88lin/facetmark/pull/44/checks) for the latest
source and outcomes; the [surface brief](surfaces/frontend.md) owns acceptance scope.
Earlier runs and verdicts remain in [validation history](../docs/desktop-validation.md).
