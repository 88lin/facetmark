---
version: 1
slug: "frontend"
primary_target: "frontend"
related_targets:
    [
        "frontend/src/App.tsx",
        "frontend/src/FacetBrowser.tsx",
        "frontend/src/Reader.tsx",
        "frontend/src/workbench.css",
        "frontend/src/styles.css",
        "frontend/src/SearchTools.tsx",
        "frontend/src/Settings.tsx",
        "frontend/src/components/ui/reader-outline.tsx",
    ]
---

# Facetmark collection and reader — Operate / Read

## Direction contract

USER EVIDENCE: White/lake blue and true capsule controls remain selected. The latest rejection is that the My collection / 1892 saved pages area leaves only half the window for useful bookmarks, with many bugs. The user specifically reports that categories require horizontal touchpad gestures and are inconvenient with an ordinary mouse. The supplied comparison is GithubStarsManager. Prior `ship` verdicts are historical and do not authorize the rejected layout.

THESIS: Make a large personal collection easy to scan, navigate and read. Put actual saved pages near the top and use a complete vertical category directory that works with mouse, keyboard and touch.

OWN-WORLD: Pure white, pale blue workspace, deep blue ink, lake-blue interactions, capsule controls and circular icon actions remain. Cards use 12px corners, the reader 20px. Keep offline Manrope and local Chinese fallbacks. Source, title, excerpt and metadata provide the detail. Main mobile targets remain at least 44px; compact collection actions are 36px on desktop.

FIRST VIEWPORT: A 56px app header and 60px desktop collection toolbar contain the 22px title/count and 40px search. A 208px category directory appears from 960px, beside an auto-fill grid of at least 270px cards with 12px gaps and 14px padding. Below 960px categories are in the filter drawer. Creation, selection, organization, export and card/list switching share a compact action row. Mobile title/search stack with 12px outer space. The initial collection must leave at least 63% of a short desktop viewport, and 58% of the tested mobile viewport, for the scrolling bookmark list. Test 1366×768, 1280×600 and 390×844 with 1892 synthetic records.

CATEGORIES: Folders, tags and sites share a searchable directory. Real counts, wrapping long names, a native vertical scrollbar, mouse-wheel access, keyboard focus and explicit pagination of 50 make all categories reachable. The search reaches beyond the former 200-category overview limit. Loading, empty and failure/retry states are visible. Category changes reset the real results scroll/page and close old reading content. Repeated selection cannot strand a cancelled request.

RESULT STATES: New queries/categories are associated with their exact loaded result context. Old rows cannot appear selectable or exportable under a new category while loading or after failure. Repeated Enter and IME completion reliably settle. Preserve query, category, page, real list position and focus when opening/returning from a result. Persist card/list preference across reloads.

READING: Selection hides the category directory and introduces the existing supporting index and dominant reader. Keep 36px/38px article titles, 17px prose and 1.9 desktop leading. Controls stay outside the article scroller; the 170px chapter rail uses only real headings during wide focused reading. Retain keyboard navigation, reduced motion, visible narrow return and contextual bookmark actions.

SUPPORT: Keep protected Radix editing/deletion dialogs, explicit consent, named inputs, visible failures and focus return. Preserve model configured/tested/indexed/applied distinctions, fetch versus summarize tasks and metadata-only sync with explicit conflicts and confirmation. Check Chinese/English and light/dark states.

REFERENCE: GithubStarsManager was inspected at 6d1dd80700b0ee717f79a5da7d0137f32afc91b7 (MIT), including category/sidebar, search/list controls and two repository screenshots. It is an interface comparison supplied by the user, not an approved pixel comp. No copied code or reference raster ships. Its useful directory/control arrangement is adapted to Facetmark's existing visual identity.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

VERIFY: Use synthetic data and GitHub Actions for builds, browsers, packaging and installation. Local work is source editing, lightweight checks and small evidence retrieval. Verify short windows, many/long categories, mouse and keyboard operation, slow/repeated queries, failed new scopes, scoped export safety, card/list persistence and reader return context. Associate evidence with exact source, perform one batched inspection and a bounded independent confirmation. Never use personal browser profiles or actual bookmarks.

EVIDENCE: Implementation and cloud validation are in progress. The fresh rejection review returned fix with six items: top-space budget, complete category access, repeated-request correctness, scroll/reader scope reset, stale-result action safety and realistic data/documentation. Earlier collection-management evidence (application 33ff0df5340b31061434deb7e341c612e22feae1, tests f757f33e00a0a3582e4b656865bddd51d3d4f445, Experience 37774845284) describes the rejected layout only.
