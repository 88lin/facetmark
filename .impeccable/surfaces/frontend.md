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

CATEGORIES: Folders, tags and sites share a searchable directory. Real counts, wrapping long names, a native vertical scrollbar, mouse-wheel access, keyboard focus and explicit pagination of 50 make all categories reachable. The search reaches beyond the former 200-category overview limit and ranks exact matches first, followed by prefixes and other literal substring matches, with stable alphabetical ordering within each group. Loading, empty and failure/retry states are visible. Category changes reset the real results scroll/page and close old reading content. Repeated selection cannot strand a cancelled request.

RESULT STATES: New queries/categories are associated with their exact loaded result context. Old rows cannot appear selectable or exportable under a new category while loading or after failure. Repeated Enter and IME completion reliably settle. Preserve query, category, page, real list position and focus when opening/returning from a result. Persist card/list preference across reloads.

READING: Selection hides the category directory and introduces the existing supporting index and dominant reader. Keep 36px/38px article titles, 17px prose and 1.9 desktop leading. Controls stay outside the article scroller; the 170px chapter rail uses only real headings during wide focused reading. Retain keyboard navigation, reduced motion, visible narrow return and contextual bookmark actions.

SUPPORT: Keep protected Radix editing/deletion dialogs, explicit consent, named inputs, visible failures and focus return. Preserve model configured/tested/indexed/applied distinctions, fetch versus summarize tasks and metadata-only sync with explicit conflicts and confirmation. Check Chinese/English and light/dark states.

REFERENCE: GithubStarsManager was inspected at 6d1dd80700b0ee717f79a5da7d0137f32afc91b7 (MIT), including category/sidebar, search/list controls and two repository screenshots. It is an interface comparison supplied by the user, not an approved pixel comp. No copied code or reference raster ships. Its useful directory/control arrangement is adapted to Facetmark's existing visual identity.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

VERIFY: Use synthetic data and GitHub Actions for builds, browsers, packaging and installation. Local work is source editing, lightweight checks and small evidence retrieval. Verify short windows, many/long categories, mouse and keyboard operation, slow/repeated queries, failed new scopes, scoped export safety, card/list persistence and reader return context. Associate evidence with exact source, perform one batched inspection and a bounded independent confirmation. Never use personal browser profiles or actual bookmarks.

EVIDENCE: Documentation confirmed on 2026-10-10; cloud validation ran on 2026-10-09 against application and browser-test source 09ab0332c5f9ec40627afc7f48f3da2ce0b8b36b. `.desktop-build/collection-verified/provenance.json` identifies 51 captures and a 14.24-second reading recording, using 1892 synthetic bookmarks and 295 folders. The current collection-1366x768, collection-390x844 and collection-category-search captures were inspected for this documentation pass.

MEASUREMENTS: `.desktop-build/collection-verified/collection-density.json` records 1366×768: first card y=163, list height 556px (72.4%), 9 complete cards; 1280×600: y=163, height 388px (64.7%), 6 cards; 390×844: y=218.6875, height 580.3125px (68.8%), 3 cards. The 1440×960 and 1024×749 views show 16 and 6 complete cards respectively. None of the five measured views has horizontal document overflow. These are initial unfiltered-view measurements, not minimums for every search or content state.

VALIDATION: [Experience 37927920369](https://github.com/88lin/facetmark/actions/runs/37927920369) passed 37 browser tests and 2003 Python tests, with 1 Python skip. [CI 37927928123](https://github.com/88lin/facetmark/actions/runs/37927928123) passed all 10 jobs, including MCP 22/22. [Windows 37927920467](https://github.com/88lin/facetmark/actions/runs/37927920467) passed offline installation, actual WebView rendering, same-version reinstall, retained user data and process cleanup; its small evidence bundle is `.desktop-build/collection-windows-37927920467`. Hosted Windows Server smoke does not certify Windows 10/11.

REVIEW STATUS: The rejection review returned fix with six items: top-space budget, complete category access, repeated-request correctness, scroll/reader scope reset, stale-result action safety and realistic data/documentation. Implementation, cloud validation and this bounded documentation confirmation are complete. Final independent confirmation returned `disposition: ship`: all six fixes are resolved, remaining findings are clear, and no material regression was identified within that scope. The original reviewer and an earlier replacement were rate-limited; a general independent substitute completed the confirmation because the dedicated role was unavailable. It inspected 12 raw captures, provenance, density and scroll evidence, relevant source/tests, the Experience log and Windows JSON without running the application or tests itself. This verdict covers the six fixes and does not imply the user's visual approval. Earlier collection-management evidence (application 33ff0df5340b31061434deb7e341c612e22feae1, tests f757f33e00a0a3582e4b656865bddd51d3d4f445, Experience 37774845284) and its historical `ship` describe the rejected layout only.
