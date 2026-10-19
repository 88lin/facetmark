# UI and motion tools

Updated on 2026-10-19 for the capsule workspace rebuild after the user rejected
`082e36d`. The application now combines navigation and searchable categories in
one sidebar, with neutral surfaces, indigo accents and complete capsule controls.
[The workbench contract](../.impeccable/workbench-direction.md) owns the direction;
[DESIGN.md](../DESIGN.md) and [the surface brief](../.impeccable/surfaces/frontend.md)
record the implementation and acceptance scope.

## Controls, fonts and search

The actual runtime dependencies include `@heroui/react` and `@heroui/styles`
3.2.6, `gsap` 3.13.0, `@gsap/react` 2.1.2, `motion` 12.23.24,
`@radix-ui/react-dialog` 1.1.6 and `cmdk` 1.1.1. [styles.css](../frontend/src/styles.css)
uses HeroUI's official granular imports: base, default theme, utilities, variants,
`components/button.css` and `components/input.css`. This retains real controls
while excluding unused component styles. Source-matched build evidence is recorded
in [desktop validation](desktop-validation.md). Application overrides remain in
[workbench.css](../frontend/src/workbench.css).

The shipped [HeroUI license](../frontend/public/licenses/HeroUI.txt) records Apache
2.0 terms; Settings now credits HeroUI alongside Rare UI. Preserve the license and
visible attribution when maintaining the integration.

[CapsuleButton](../frontend/src/ui/controls.tsx) wraps the real HeroUI Button,
which supplies press/focus state. Its native button preserves the actual click
currentTarget for anchored controls. Application keyboard commands run first;
HeroUI receives only unprevented key events. A ref records whether HeroUI then
prevented the Enter/Space default. For a keyboard press on `type="button"`, the
wrapper supplies one real DOM click only when that ref requires it, and clears
the flag after use/keyup. Submit/reset retain browser form activation.

This conditional bridge addresses missing Windows keyboard actions without adding
a second Enter click when macOS retains native activation. Verify both activation
and exact click counts; source logic alone is not a platform pass. Handled listbox
commands must not submit the surrounding form. Disabled/pending controls reject
activation. Shared root application actions use this wrapper; the scrim and adapted
reader controls retain their specific implementations. Folder/model search uses
HeroUI Input.

The interface bundles Inter and Noto Sans SC variable WOFF2 subsets as
`Facetmark Inter` and `Facetmark CJK`, weights 100–900 with `font-display: swap`.
Segoe UI and Microsoft YaHei UI provide fallback coverage. No font CDN is needed.
Sources, subsets and OFL notices are in [the font README](../frontend/src/assets/fonts/README.md).

`cmdk` supplies query-suggestion keyboard behavior in
[SearchTools.tsx](../frontend/src/SearchTools.tsx), using the existing API and main
search input. Loading, retry, descriptions and no-match feedback remain. Filtering
is server-side (`shouldFilter={false}`); field values with whitespace are quoted.
The MIT notice ships in [cmdk.txt](../frontend/public/licenses/cmdk.txt).

## Animation ownership

Keep one engine per animated property on an element. State, data, focus and native
activation update immediately. Static sidecar examples show appearance and native
fallback CSS states; they neither load nor verify HeroUI, GSAP or Motion.

| Interaction | Owner and source | Current source behavior |
| --- | --- | --- |
| Button press/focus | HeroUI through [controls.tsx](../frontend/src/ui/controls.tsx) | HeroUI owns its controls' pressed/focus state; `.fm-button` transform transitions use 250ms with the smooth/ease fallback. Native CSS scale excludes `.button` and `data-overlay-motion`; remaining fallback press is .96, category .98 over 160ms. The global reduced-motion `.fm-button` rule removes press transform in the app and portaled dialogs. |
| Selection continuity | Motion `SelectionPill`, [InteractionMotion.tsx](../frontend/src/InteractionMotion.tsx) | Separate shared layout groups; spring stiffness 480, damping 29, mass .8. Semantic pressed/current/selected state remains on the control. |
| Page arrival | GSAP `useContentMotion`, [InteractionMotion.tsx](../frontend/src/InteractionMotion.tsx) | Ordered destination direction; 340ms, 18px travel, initial opacity .76/blur .7px. Collection results instead use 24px travel at the content label. |
| Heading/body composition | Same GSAP timeline | `heading` starts at 0; `content` at 40ms. Collection heading: 280ms, 18px, opacity .82/blur .5px. Supporting inner bodies: 340ms, 6px, opacity .78/blur .5px. |
| Settings section | Same GSAP hook | Ordered models/sync/extension/desktop direction; 320ms, 20px, opacity .66/blur 1px. The section hook owns the panel; page arrival owns its inner body. |
| Category, pagination and filter changes | Same GSAP hook | Category: 280ms/18px/.72/.65px blur. Offset-only pagination: 340ms/22px/.72/.7px blur with forward/back direction. Query/filter refocus: 250ms/8px/.8/.7px blur. |
| Pointer/keyboard ink | React portal plus [interaction-motion.css](../frontend/src/interaction-motion.css) | Noninteractive clipped paint for primary pointer-down or nonrepeated Enter/Space; at most six records. Capsule ink is 480ms, `cubic-bezier(.22,1,.36,1)`, scale .025 to 1 and opacity .26/.19/0. Each record retains its originating control: a bounded frame check discards it when that control disconnects, becomes inactive/hidden, or moves with navigation. Scroll/resize clears ink; 600ms expiry bounds interrupted animations. Structural navigation scrims never produce ink or press scaling. |
| Collection entry/reflow | Motion, [BookmarkCard.tsx](../frontend/src/BookmarkCard.tsx) | Position layout spring 400/36. Entry opacity 220ms with 25ms spacing capped at 125ms; y 8px to 0 over 280ms. CSS entry stays disabled. CSS hover owns border/background 220ms and shadow 260ms. |
| Folder/model menus and library dialog | Motion presence, [overlay-motion.tsx](../frontend/src/overlay-motion.tsx) | Enter 280ms `cubic-bezier(.22,1,.36,1)`; dialog y 20px, menu y -8px, scale .97. Exit 160ms `cubic-bezier(.4,0,1,1)`, half travel and scale .985. Scrims change opacity only. Closing content immediately becomes inert, aria-hidden and noninteractive. |
| Picker labels/chevrons | Motion plus local CSS | Selected label 180ms from opacity .65/y 3px; model chevron 200ms, folder chevron 220ms. HeroUI owns trigger/option press. |
| Native disclosure menus and drawer | CSS, [workbench.css](../frontend/src/workbench.css) | Details menus enter in 240ms from y -6px/scale .97; discrete opacity exit 160ms where supported. Navigation drawer translation 320ms, scrim 220ms. |
| Theme reveal | View Transition plus WAAPI, [App.tsx](../frontend/src/App.tsx) | Viewport-covering circle from the clicked control, 460ms `cubic-bezier(.16,1,.3,1)`. The application restores `view-transition-name: root` after HeroUI base styles so the root snapshot exists. Repeated changes skip the preceding transition; unsupported/reduced mode switches immediately. |
| Reader focus/tab marker | GSAP, [App.tsx](../frontend/src/App.tsx) and [motion.ts](../frontend/src/motion.ts) | Focus translation 220ms; tab-marker x/width 180ms; `power3.out`, `overwrite: auto`, scoped interruption/cleanup. |
| Narrow reader presence | Motion with Radix Dialog | Reader translation 220ms, scrim opacity 180ms; preserve focus containment and return through rapid close/open. |
| Reading capsule/progress | Motion, [scroll-progress.tsx](../frontend/src/components/ui/scroll-progress.tsx) | Capsule entry 240ms; chapter label 180ms with y/blur. Actual article-scroll progress spring stiffness 180, damping 35, mass .25. |
| Outline plane | Motion, [reader-outline.tsx](../frontend/src/components/ui/reader-outline.tsx) | Measured active-heading position; spring 380/32/mass .65, rotation clamp ±18 degrees; remeasure on resize/wrapped labels. |

GSAP recipes use `power3.out` and `overwrite: auto`. The hook remembers painted
x/y/opacity/filter values before context cleanup, so rapid reversal resumes from
the current paint instead of replaying an unrelated entrance. It skips initial
mount and unchanged contexts, scopes work with `useGSAP`, and clears temporary
transform/opacity/filter/will-change when complete.

[useReducedMotion.ts](../frontend/src/useReducedMotion.ts) subscribes to live
`matchMedia` changes through `useSyncExternalStore`. Reduced motion cancels content
travel, suppresses ink and press transform, resolves selection/reflow immediately,
skips the theme reveal and removes reader travel while retaining state and controls.
The `.fm-button` reduction rule is not limited to `.app-shell`, so portaled menus
and dialogs are covered. Verify changes made while the application is already open.

## Collection and reader details

The summary's provenance is a 13px inline label before its body. Measured clipping
still determines expansion; the accessible Show full text / Collapse action now
uses an icon in the card footer. Original links, selection and Preview remain
independent. These semantics must survive capsule-control migration and motion.

The Rare UI-derived reader retains the glass progress capsule, native chapter
selector, animated heading label and back-to-top control. Progress measures saved
article scroll rather than claiming reading completion. Glass is bounded to this
surface: canvas 82%, rule 72%, `blur(16px) saturate(1.3)`, with opaque and reduced-
transparency fallbacks. Keep final-paragraph clearance above the control.

RailToc derives from fixed upstream revision
[`b4de46e…/public/r/rail-toc.json`](https://github.com/swamimalode07/rare-ui/blob/b4de46efe4eb2613e22bb8134b482ed4e0c7736a/public/r/rail-toc.json).
It uses real headings and scrolls the article container. The wide focused outline
requires more than one heading; narrower readers keep the native selector.
Rare UI uses **MIT + Commons Clause + attribution**. Preserve source headers,
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md),
[the shipped notice](../frontend/public/third-party-notices.txt) and the visible
Settings credit. Refer to the complete notice for its resale/redistribution terms.

## Verification status

Source inspection covers `ba47b54302daafb91f1dade1249429a89297fc08` and subsequent
working-tree HeroUI stylesheet/theme integration corrections. The final correction
revision, fresh cloud results, installed-Windows capture review and a full independent
visual/motion verdict remain pending. No user aesthetic approval is recorded. Use [PR #44 checks](https://github.com/88lin/facetmark/pull/44/checks)
for current outcomes and [desktop validation](desktop-validation.md) for the bounded
evidence record. The rejected `082e36d` results cannot certify this replacement.

[visual-layout.ts](../frontend/tests/visual-layout.ts) waits for fonts and settled
geometry/opacity/transform/filter, including active GSAP markers, before static
capture. It requires 250ms stability and fails after 5 seconds. Disabling browser
CSS animations alone does not settle JavaScript-driven Motion/GSAP. The main
[redesign matrix](../frontend/tests/redesign.spec.ts) uses this helper; installed
capture logic also waits for fonts and the expected result state.

[capsule-controls.spec.ts](../frontend/tests/capsule-controls.spec.ts) adds exact
keyboard click/submission counts, portal reduced-motion coverage and the root theme
reveal regression. [interaction-motion.spec.ts](../frontend/tests/interaction-motion.spec.ts),
[visual-restoration.spec.ts](../frontend/tests/visual-restoration.spec.ts) and the
redesign matrix define relevant browser coverage. Authored tests and source checks
are not passing runtime evidence. Inspect fresh desktop/short-window/mobile,
light/dark and installed captures, plus continuous keyboard/click/reversal sequences.
Use synthetic data and isolated fixtures; preserve original browser profiles.
