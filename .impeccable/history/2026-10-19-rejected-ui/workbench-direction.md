# Facetmark capsule workspace — Operate

> Superseded on 2026-10-19. The user rejected this full design and all three
> subsequent Prism Light / Spectrum Dark / Orbit studies. Only Orbit's sculpted
> folder glyph is retained, conditional on animation. The notes below document
> the rejected baseline, not visual authority for the replacement interface.

## Current direction — 2026-10-19, after the second rejection

USER EVIDENCE: The user rejected the lavender/10px-control replacement, repeated that buttons must be rounded capsules, described the typography and sparse motion as ugly and rigid, and authorized a full rebuild. They added HeroUI as a concrete reference and explicitly requested the installed GSAP capabilities. Earlier tests and reviews are historical technical evidence, never aesthetic approval.

THESIS: A fluid collection workspace with one unified sidebar, a spacious content canvas, tactile capsule controls and continuous navigation. Main navigation and searchable categories share one column, leaving the collection itself room to breathe.

OWN-WORLD: HeroUI component quality; white and softly shaded neutral surfaces; crisp indigo accents; full capsule buttons and rounded floating menus. Icon controls are circles. Large content surfaces keep proportional rounded corners. Avoid a blanket purple wash, tiny low-contrast labels and default-looking controls.

TYPE: Inter and Noto Sans SC remain deliberately bundled. Page titles 28/36/600, item titles 18/27/550, summaries 16/27/400, controls 15/22/500 and metadata 13/20/400. Chinese tracking is zero. No 10px/11px metadata overrides; paragraph rhythm and grouping carry the hierarchy.

FORM: Repeated user references override the earlier random seed `seed:18a549514c513706`. HeroUI now leads component construction; GithubStarsManager informs collection organization; FlClash informs selection continuity and layered transitions. They are references, not approved Facetmark mockups.

MOTION: HeroUI owns button press/focus. GSAP composes interruptible page and section timelines. Motion owns moving selection capsules, card reflow and overlay presence. Reader glass progress and chapter-plane effects remain. Never let two engines animate the same property on the same element. State and focus remain immediate; repeated switching preserves the final choice; live reduced-motion preferences are honored.

FUNCTION: Preserve search/IME, paging, folder selection, model choice/test/save, task snapshots, consent, keyboard focus, native links and read-only imports. Redesign does not authorize regressions. Test complete user journeys and repair the underlying interaction when a control behaves incorrectly.

FINISH: Builds, browsers and installation run in GitHub Actions with synthetic data. Inspect desktop, short-window, mobile, light/dark and installed Windows captures, plus real continuous click recordings. Static captures wait for geometry and fonts to settle. A fresh full independent review is required after this rejection; technical checks do not establish aesthetic acceptance.

## Historical technical evidence

`082e36d53a19acc1553a5ea3ce8482fe5d526826` passed cloud checks, but its appearance was explicitly rejected. Its screenshots are anti-reference for this rebuild, and its review must not be reused as a current ship verdict.
