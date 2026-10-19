# UI and motion tools

Updated on 2026-10-19 for the replacement collection workbench. The rejected
10/18 appearance is superseded. [DESIGN.md](../DESIGN.md) owns the current visual
system; [the surface brief](../.impeccable/surfaces/frontend.md) owns acceptance.
This document records animation ownership and supporting dependencies from source.

The application uses a vertical rail, separate searchable directory and tonal
collection surfaces. Clicks, keyboard activation, selection changes, content
changes and overlays now have application-wide feedback. The existing reading
effects remain. Runtime dependencies are `motion` 12.23.24, `gsap` 3.13.0,
`@gsap/react` 2.1.2, `@radix-ui/react-dialog` 1.1.6 and `cmdk` 1.1.1.

## Fonts and search

The interface bundles Inter and Noto Sans SC variable WOFF2 subsets as
`Facetmark Inter` and `Facetmark CJK`. Both faces use weights 100–900 and
`font-display: swap`; Segoe UI and Microsoft YaHei UI provide fallback coverage.
The application serves the fonts locally. Sources, subset coverage, fontTools
version and adjacent OFL notices are documented in
[the font README](../frontend/src/assets/fonts/README.md).

`cmdk` provides the query suggestion list's arrow-key selection and Enter
activation in [SearchTools.tsx](../frontend/src/SearchTools.tsx). It uses the
existing API and main search input, with real descriptions, loading, retry and
no-match states. Filtering remains server-side (`shouldFilter={false}`), and
inserted field values containing whitespace are quoted. The MIT license ships in
[the cmdk notice](../frontend/public/licenses/cmdk.txt).

## Animation ownership

Keep one owner per animated property. Application state, focus and controls update
without waiting for motion. Static sidecar specimens illustrate appearance and
CSS states; they do not implement or verify the Motion, GSAP or WAAPI behavior.

| Interaction | Owner and source | Source parameters and behavior |
| --- | --- | --- |
| Navigation, directory, status, layout and settings selection | Motion `SelectionPill`, [InteractionMotion.tsx](../frontend/src/InteractionMotion.tsx) | Shared `layoutId` in separate groups; spring stiffness 430, damping 35. The control keeps its pressed/current/selected semantics. |
| Page, category type, settings panel and loaded result-context changes | WAAPI `useContentMotion`, [InteractionMotion.tsx](../frontend/src/InteractionMotion.tsx) | Existing container enters from opacity .45 and 12px x/y translation in 280ms, `cubic-bezier(.16,1,.3,1)`. Runs only after an actual value change, cancels the previous animation and skips initial mount. |
| Pointer and keyboard ink | React portal plus CSS, [InteractionMotion.tsx](../frontend/src/InteractionMotion.tsx) and [workbench.css](../frontend/src/workbench.css) | Primary pointer-down or nonrepeated Enter/Space creates a noninteractive clipped paint layer. At most six ink records; 520ms `cubic-bezier(.16,1,.3,1)`, scale 0 to 1 and opacity .18/.12/0. Disabled, inert, hidden and `data-no-ink` targets are skipped. |
| Control press and hover | CSS, [workbench.css](../frontend/src/workbench.css) | Ordinary buttons/summary press to .965; directory options to .98. Scale uses 160ms; background, color and shadow use 180ms. Focus rings remain visible. |
| Collection entry and card/list reflow | Motion, [BookmarkCard.tsx](../frontend/src/BookmarkCard.tsx) | `layout="position"`; entry starts at opacity 0 and y 8px. Opacity takes 220ms with 25ms spacing capped at 125ms; y takes 280ms. Reflow uses stiffness 400, damping 36. CSS card entry is disabled; CSS retains 200ms edge/background/shadow feedback. |
| Folder/model menus and library dialog/scrim | Motion presence, [overlay-motion.tsx](../frontend/src/overlay-motion.tsx) | Enter 280ms `cubic-bezier(.22,1,.36,1)`; dialog y 20px, menu y -8px, scale .97. Exit 160ms `cubic-bezier(.4,0,1,1)` with half travel and scale .985. Scrims animate opacity only. Closing content immediately becomes inert, aria-hidden and noninteractive. |
| Folder/model trigger and choice feedback | Motion, [FolderPicker.tsx](../frontend/src/FolderPicker.tsx) and [ModelPicker.tsx](../frontend/src/ModelPicker.tsx) | Trigger press .985 over 120ms; selected-label entry 180ms and chevron turn 200ms. Picker options also use Motion press scale .98; check their press treatment together with the global CSS scale rule. |
| Native disclosure menus and navigation drawer | CSS, [workbench.css](../frontend/src/workbench.css) | Manage/Display and related disclosure surfaces enter in 240ms from y -6px/scale .97; discrete opacity exit is 160ms where supported. Navigation drawer translation is 320ms; its scrim enters in 220ms. |
| Theme reveal | View Transition API plus WAAPI, [App.tsx](../frontend/src/App.tsx) | A circle grows from the clicked control to cover the viewport in 460ms, `cubic-bezier(.16,1,.3,1)`, on `::view-transition-new(root)`. Repeated changes skip the preceding transition. Unsupported browsers switch immediately. |
| Desktop reader focus and tab marker | GSAP, [App.tsx](../frontend/src/App.tsx) and [motion.ts](../frontend/src/motion.ts) | Focus translation uses 220ms; marker x/width uses 180ms. Both use `power3.out` and `overwrite: auto`; interrupted timelines/frames are cancelled and lifecycle cleanup is scoped through `useGSAP`. |
| Narrow reader presence | Motion with Radix Dialog, [App.tsx](../frontend/src/App.tsx) | Reader x transition 220ms `cubic-bezier(.22,1,.36,1)` and overlay opacity 180ms, with `AnimatePresence`. Preserve focus containment and return through rapid close/open. |
| Reading capsule, chapter label and progress | Motion, [scroll-progress.tsx](../frontend/src/components/ui/scroll-progress.tsx) | Capsule entry 240ms from opacity .65/y 10px/scale .97; label 180ms from opacity .45/y 5px/blur 3px. Progress spring stiffness 180, damping 35, mass .25 follows measured article scroll. |
| Outline paper plane | Motion, [reader-outline.tsx](../frontend/src/components/ui/reader-outline.tsx) | Spring stiffness 380, damping 32, mass .65; rotation clamped to ±18 degrees. Position follows the measured center of the active real heading and is remeasured on resize or label wrapping. |

[useReducedMotion.ts](../frontend/src/useReducedMotion.ts) subscribes to live
`matchMedia` changes through `useSyncExternalStore`. Reduced motion removes ink,
press scale, spatial entry/reflow, theme reveal and reader travel. Indicators and
progress resolve immediately while selected state and all controls remain usable.
A preference change also cancels the current content/theme transition. Verify the
preference changing while the application is open, as well as initial reduced mode.

[reader-shell.css](../frontend/src/reader-shell.css) owns reading internals.
[workbench.css](../frontend/src/workbench.css) is imported last and owns the final
application composition and responsive placement. Check that final cascade when
changing dimensions or animation ownership.

## Adapted Rare UI reader

`frontend/components.json` registers `@rare-ui`; TypeScript and Vite resolve `@/`
to `frontend/src`. Add registry components only for a concrete component need,
after inspecting their imports, dependencies and notices. Adapt copied source to
Facetmark's tokens and Vite application; keep the owner of each animated property
explicit.

The adapted **ScrollProgress** is a floating glass capsule with a native chapter
selector, animated chapter label and back-to-top control. It measures actual saved
article scroll; it does not infer that the user has read the text. Glass is confined
to this bounded surface: canvas at 82%, rule at 72%, `blur(16px) saturate(1.3)`.
An opaque fallback and reduced-transparency override remain. Article bottom
clearance keeps the final paragraph above the controls.

The wide focused reader adapts **RailToc** from the fixed upstream revision
[`b4de46e…/public/r/rail-toc.json`](https://github.com/swamimalode07/rare-ui/blob/b4de46efe4eb2613e22bb8134b482ed4e0c7736a/public/r/rail-toc.json).
It uses actual saved-text headings, scrolls the article container and restores
tracking after keyboard paging. It appears only when more than one real heading
is available; narrow layouts retain the capsule's native selector. Reduced motion
positions the plane directly.

Rare UI uses **MIT + Commons Clause + attribution**. Preserve the adapted-source
copyright headers, complete notices and visible Rare UI credit in Settings. The
license restricts selling or redistributing the components as a component library
or bundle. The complete terms are in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)
and [the shipped notice](../frontend/public/third-party-notices.txt); see also
[the upstream license](https://github.com/swamimalode07/rare-ui/blob/main/LICENSE).

## Verification status

The source recorded for this replacement pass is
`ac90d24805e346ba974a197da72a59cdac11231f`. Initial runs are
[Experience 39193153703](https://github.com/88lin/facetmark/actions/runs/39193153703),
[Windows 39193153702](https://github.com/88lin/facetmark/actions/runs/39193153702) and
[CI 39193157986](https://github.com/88lin/facetmark/actions/runs/39193157986). A complete
final verification set, fresh capture/interaction review and visual acceptance
remain pending.
Use [PR #44 checks](https://github.com/88lin/facetmark/pull/44/checks) for current
source and outcomes. Earlier results remain in [validation history](desktop-validation.md).

The authored browser cases are
[interaction-motion.spec.ts](../frontend/tests/interaction-motion.spec.ts),
[visual-restoration.spec.ts](../frontend/tests/visual-restoration.spec.ts) and
[redesign.spec.ts](../frontend/tests/redesign.spec.ts). They cover everyday switching,
reader controls, rapid changes, drafts/focus, keyboard operation and reduced motion.
Their presence is not evidence that this replacement revision passed. Review the
built application's still captures and actual interaction sequences, including
installed Windows, both themes and narrow layouts. Source inspection, dependency
availability and historical run success do not establish current visual approval.
