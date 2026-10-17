# UI and motion tools

Updated on 2026-10-07 for the collection and focused-reading redesign. Impeccable owns
the visual system. Runtime dependencies are selected for specific interactions:
`gsap` 3.13.0, `@gsap/react` 2.1.2 and `motion` 12.23.24.

The collection now uses a larger masthead, a separate search row, real folder
shortcuts and source-first cards. The supporting index contracts when a page opens.
The GSAP tab indicator remains a capsule selection behind icon-labeled tabs;
its existing interruptible position/width tween is preserved. CSS provides pill
actions, circular icon buttons, natural card heights and the stronger reading scale.
Each model channel's test follows its own fields, before optional settings.

`cmdk` 1.1.1 provides the query suggestion list's arrow-key selection and Enter
activation, using the existing API and main search input. Suggestions include
real descriptions, loading, retry and empty states. Filtering stays server-side
(`shouldFilter={false}`); whitespace in inserted field values is quoted.
The MIT license ships at `frontend/public/licenses/cmdk.txt`.

Manrope is bundled as an unmodified variable font for Latin/interface text,
followed by the existing local Chinese fallback stack. Its source is
`google/fonts/ofl/manrope/Manrope[wght].ttf`, blob
`75274da58537d6123b14f2cd0c355ad4681fc2b3`; SIL OFL 1.1 is distributed at
`frontend/public/licenses/Manrope-OFL.txt`. Font loading needs no external service.
Current validation evidence is recorded in `docs/desktop-validation.md`.

## Rare UI

`frontend/components.json` registers `@rare-ui` for this React/Vite application.
The TypeScript and Vite `@/` aliases both resolve to `frontend/src`.

After selecting a component for a concrete design, run from `frontend`:

```powershell
npx -y shadcn@latest add @rare-ui/component-name
```

Replace `component-name` with a verified name from
[the component catalog](https://rareui.com/components). Registry components and
their dependencies are added on demand. Facetmark now adapts **ScrollProgress**
in `frontend/src/components/ui/scroll-progress.tsx`: a quiet reading-position
footer with a native chapter selector and back-to-top button. It reads actual
scroll position and does not claim that the user has read the article. The
upstream glass treatment, floating pill and staggered text are omitted.
The wide focused reader also adapts **RailToc** in
`frontend/src/components/ui/reader-outline.tsx`, from the fixed upstream registry
revision `b4de46efe4eb2613e22bb8134b482ed4e0c7736a/public/r/rail-toc.json`.
It tracks actual saved-text headings, scrolls only the article container and
restores scroll tracking after keyboard paging. It appears only when more than
one real heading is available. A sticky text rail replaces the original animated
paper-plane treatment; narrower layouts retain the existing chapter selector.
The configured `utils` alias is the future destination for the
component registry's utility dependency, not an existing application import.
Do not install the upstream Next.js demo application into this Vite project.

Inspect component dependencies and imports before adding them. Preserve the
existing design tokens and adapt copied components to the workbench. Components
using Motion can keep Motion; GSAP skills do not require converting them.

Rare UI uses **MIT + Commons Clause + attribution**, not unrestricted MIT.
When shipping a component, retain its copyright/license notices and add a visible
Rare UI link in the application credits or project README. The license prohibits
selling or redistributing the components as a component library or bundle.
See [the upstream license](https://github.com/swamimalode07/rare-ui/blob/main/LICENSE).
The adapted source retains its copyright header. The complete notice ships in
`THIRD_PARTY_NOTICES.md` and `frontend/public/third-party-notices.txt`; Settings
includes a visible Rare UI credit.

## GSAP skills

The user's global tool installation contains the eight official GSAP skills.
The redesign used core, React, timeline and performance guidance. GSAP owns the
interruptible desktop reader expansion and tab indicator in `App.tsx` and
`motion.ts`. Timelines and queued frames are cancelled before reversal; unmount
cleanup is scoped through `useGSAP`.
The new focus composition removes the search row and reduces the app header;
the pane transition accounts for both horizontal and vertical displacement.

Motion owns the Radix reading drawer's horizontal position and overlay opacity,
plus the adapted Rare UI scroll indicator. The drawer uses `AnimatePresence`
so rapid close/open continues from its current position. No property on the
same element is controlled by both engines. CSS handles ordinary hover, focus
and color feedback; result rows appear without staggered entrances.

Use the core skill and the relevant specialist skill as needed. Generic visual
redesign continues through Impeccable. Simple transitions can use CSS, and
existing animation engines should be preserved. Respect reduced-motion settings
and clean up animations on navigation or component unmount.
The common panel/indicator rhythm is 180–220 ms with an ease-out curve. Reduced
motion removes travel; content and controls never wait for an animation.

## Oil Motion

Oil Motion is available globally for converting generated or existing videos and
frame sequences into interactive web assets. It is intended for subject motion,
product transformations and scene transitions. Ordinary workbench panels and
button feedback do not require this media pipeline.
It was therefore **not used** for this redesign; no generated images, video,
paid generation calls or credential changes were needed.

Local media processing has a separate Python environment and uses the installed
FFmpeg tools. AI image/video generation requires a ZenMux key configured through
the skill's local credential page at first use; installation does not call the
generation service.

The machine-specific entry points and maintenance commands are documented at
`C:\Users\Computer\.agents\external\UI-MOTION-TOOLS.md`.

## Verification

`frontend/tests/redesign.spec.ts` exercises rapid selection, delayed responses,
tab scroll restoration, expansion reversal, drawer focus return, reduced motion,
chapter jumps and explicit loading/error states. Collection/toolbar alignment,
natural result-row height and visible narrow-reader
return are also checked. GitHub Actions creates the
screenshots and short recording from the actual shared frontend. The small
`facetmark-visual-evidence` artifact includes PNG source metadata, capture hashes,
font diagnostics, contact sheets and MP4/WEBM. See `desktop-validation.md` for
the exact validated revision and results; tools being available is not evidence
that their interactions passed.
