# Desktop experience validation

## 2026-10-18: asset delivery, task scope, desktop lifecycle and collection polish

<!-- current-experience-evidence:start -->

Validated application/test source: `0993020882434593932d3d50ad5ad25594b0531f` (branch
`desktop/facetmark-experience`, PR #44). The commit raised here is the build
input for every run below; no independent visual review or user aesthetic
approval is claimed for this revision.

This pass fixes defects that made the desktop build feel broken rather than
unfinished:

| Defect | Correction |
| --- | --- |
| `/app` fell back to the legacy purple page | Missing frontend dependencies made `npm run build` fail silently. Installing them from the lockfile makes the React workbench the served page. |
| Blank page with 404s for hashed assets | `/app/static` froze its directory at startup while `index.html` resolved at request time. Both now resolve per request, so a build that lands after boot is served. |
| Partial-task resume re-expanded scope | `processing_item` rows are deleted when a job finishes, so resuming recomputed "current library". The snapshot id list is now persisted separately and replayed. |
| Renaming a folder discarded its summaries and vectors | `folder` was treated as enrichment input. Only `title` and `url` retire derived data now. |
| Bulk move/tag read every full record under the lock | Batch paths skip the per-row record fetch; browsing counts and `/bookmarks/facets` are merged/cached instead of repeated full scans. |
| Restart could leave the app invisible | The main window is created before the previous one is destroyed; a failed build returns to the splash with the reason. |
| Restart rejected while the sidecar reported an error | The `error` record releases the child handle immediately, and its message is not overwritten by the later generic "service stopped". |
| Window geometry, tray click and shortcut state | Size/position/maximized are remembered with an off-screen guard; a tray left click restores the window; a failed registration unchecks the menu item. |
| Blank flash and off-brand splash | The loading window has a background colour; the splash uses the product's white/lake-blue tokens and its own progress/retry states. |
| Pagination cleared the list and duplicated sessions | Paging keeps the current scope's rows; "load more" is guarded and de-duplicated. |
| Empty numeric setting stored `0`; auto-detection overwrote a typed model | Cleared numbers stay unset; a manual model edit survives late detection. |
| List view rules contradicted each other | One rule family now owns list layout; grid cards widen to a 310px minimum. |

Verification at this source:

| Evidence | Verified state |
| --- | --- |
| [Experience 39089551750](https://github.com/88lin/facetmark/actions/runs/39089551750) | **success**. `web`: backend lint and regression **2049 passed / 1 skipped**; behavior and render matrix **63 passed**; separate 200,000-record paging/scoped-selection browser test **1 passed**; wheel and sdist contain the workbench; visual evidence uploaded. `extension`, `docker` and real OpenCode CLI on Linux and Windows also passed. |
| [CI 39089554204](https://github.com/88lin/facetmark/actions/runs/39089554204) | **success**, all ten jobs: Linux and Windows × Python 3.10/3.12, wheel, webui, browser, extension, Karakeep plugin and image. |
| [Windows 39089551767](https://github.com/88lin/facetmark/actions/runs/39089551767) | **success**. Frozen service isolation, offline WebView2 install, installed-app launch checks and upload all passed. [Install evidence](https://github.com/88lin/facetmark/actions/runs/39089551767/artifacts/12122746412) is 153,657 bytes; the [unsigned x64 preview](https://github.com/88lin/facetmark/actions/runs/39089551767/artifacts/12122452198) is a 279,560,635-byte archive, not downloaded locally. |
| Local targeted checks | `ruff check src/facetmark` clean; `pytest tests/test_library.py tests/test_workbench.py tests/test_reading_jobs.py tests/test_admin.py tests/test_web.py` passed; a full local run reported 2015 passed / 35 skipped. `tsc --noEmit` and `vite build` passed. |
| Local browser subset | 19 of 22 targeted Playwright cases passed before the final build. One failure was a real IME regression introduced in this pass and fixed (`onChange` must not clear composition state). Two Settings cases fail only on a machine with Codex/Claude Code/OpenCode installed, because the demo auto-selects an agent and hides the API fields; CI without those CLIs passes the same cases. |

Two Rust compile failures were caught by this run and fixed before the passing
build: `is_registered` returns `bool` rather than a `Result`, and the shortcut
menu item handle was moved into the tray closure while still needed afterwards.

Scope limits: the browser and 200,000-record data are synthetic; CI ran on
Windows Server, not every Windows 10/11 machine; the installer is unsigned; the
local browser subset above is not the full 63-case matrix except where the
Experience run covers it. No fresh independent visual review was performed for
this revision, so the earlier `ship` verdict remains scoped to `4c6383a`.

<!-- current-experience-evidence:end -->

## Historical validation

All entries below describe earlier revisions. Their uses of “current” or “final”
are local to the dated entry and do not override the current status above.

## 2026-10-17: complete model choice, summary use and exact recovery (historical verified)

Validated application/test source: `4c6383ad0537bccb85ce32f76fc11fe3f9e139e8`.
Experience, all ten CI jobs and Windows installation checks passed at this source.
The fresh independent visual review returned **ship** for the complete reviewed
improvement scope. No user aesthetic approval is recorded.

The revision completes model discovery → selection → test/save → summary use,
separates Display from generation scope, and preserves the original target snapshot
for partial-task recovery. The final lifecycle correction keeps a hand-entered model
when failed initial Agent detection first succeeds; unresolved detection does not
establish a new Agent identity.

| Evidence | Verified state |
| --- | --- |
| Experience | [39002142092](https://github.com/88lin/facetmark/actions/runs/39002142092) **success**: 2049 Python passed / 1 skipped; 63 ordinary Playwright passed / 1 large-matrix case skipped; the separate 200,000-record browser job passed. TypeScript/Vite, wheel/sdist resources, Docker and extension checks passed. |
| CI | [39002144664](https://github.com/88lin/facetmark/actions/runs/39002144664) **success**: all ten jobs individually verified passed. |
| Real OpenCode | Linux and Windows passed catalog → specified model → summary through isolated synthetic HTTP services. |
| Targeted local checks | 42 Python tests passed, including application HTTP discovery, specified-model test/save/job execution and summary storage. `ruff check src tests scripts` passed. |
| Independent source review | Five material findings scored resolved after correction. This is distinct from the fresh rendered visual review. |
| Mechanical design scan | One pass across 14 changed UI targets returned `[]`. |
| Web visual provenance | [Artifact 12089977028](https://github.com/88lin/facetmark/actions/runs/39002142092/artifacts/12089977028): all **80 PNG SHA256 values** verified against the exact-source/run `provenance.json` in `.desktop-build/holistic-final-39002142092`. |
| Windows | [39002142193](https://github.com/88lin/facetmark/actions/runs/39002142193) **success**: offline WebView2 installation, backend isolation, installed-app behavior, reinstall, data-preserving uninstall and parent-exit cleanup passed. |
| Fresh visual review | **Ship**: 17 named captures independently inspected; all eight original findings resolved, with no remaining material findings in the reviewed scope. |

The root's final Web capture inspection covered desktop/mobile collections, searchable
models on desktop and the selected-model mobile state. The independent review's
broader 17-capture scope and completed disposition are recorded below.

Final density uses results viewport/list top, separately from the first card's
3px inset. The desktop and 390px mobile fixtures respectively measure list top
**208.39px / 256.08px** and first card **211.39px / 259.08px**. These satisfy the
list-top targets of 210px desktop and 270px mobile.

| Viewport width | Complete visible cards | Horizontal document overflow |
| --- | ---: | --- |
| 1440px | 8 | None |
| 1366px | 6 | None |
| 1280px | 3 | None |
| 1024px | 4 | None |
| 390px | 2 | None |

The synthetic 200,000-record benchmark measured first page **73.56ms** and deep
page **139.31ms**. The separate large-library browser pass validates the scoped
workflow on that fixture; it does not mean 200,000 real summaries were generated.

Windows evidence is [desktop-install-evidence 12089883505](https://github.com/88lin/facetmark/actions/runs/39002142193/artifacts/12089883505)
(**161,300 bytes**), stored in `.desktop-build/holistic-windows-39002142193`.
`installed-reader.json` identifies the exact validated source. The synthetic
installed-app flow imported bookmarks, searched, opened the original URL through
an actual Edge request and returned from Preview with the query preserved.
No page errors were recorded. `installed-collection.png` and
`installed-reader.png` were inspected at **1028 × 749px**.

The [unsigned preview installer artifact 12089928203](https://github.com/88lin/facetmark/actions/runs/39002142193/artifacts/12089928203)
is a **279,602,130-byte archive** containing a **279,375,572-byte installer**.
The large installer was not downloaded locally. Hosted Windows Server evidence
does not certify every Windows 10/11 environment.

**Fresh visual review verdict: ship.** All eight original findings are resolved,
with no remaining material findings in the reviewed scope. The reviewer independently
inspected **17 named captures**: five collection sizes, six model/connection states,
English dark settings, paused and partial tasks, import, and the installed collection
and preview. It checked source `4c6383a` against the `39002142092` manifest.
A generic reviewer substituted for the unavailable specialist role.

The reviewer visually inspected those 17 captures, not all 80 Web PNGs, and did not
run a browser. The 80-image hash verification and passing cloud browser/installation
jobs provide separate provenance and runtime evidence. The partial-task capture's
generic stage list is declared fixture content; actual scoped-resume backend tests
establish precise recovery behavior. This verdict supports the complete reviewed
improvement scope, not user aesthetic acceptance, personal model-account permissions
or certification of every Windows environment. No current evidence field remains pending.

Synthetic HTTP summaries verify that the selected model reaches the application
pipeline and stored result. They do not establish personal account access, model
quality or quota. Earlier runs below apply only to their recorded source.

<!-- current-experience-evidence:end -->

## Historical validation

All entries below describe earlier revisions. Their uses of “current” or “final”
are local to the dated entry and do not override the current status above.

### Intermediate runs for the 2026-10-17 refinement

These failures were superseded by the validated source above:

- `6ecd43b`: TypeScript failed because Setup lacked `onBack`.
- `027a0d6`, [Experience 39000193832](https://github.com/88lin/facetmark/actions/runs/39000193832):
  2048 Python passed / 1 skipped, 57 ordinary browser passed / 4 failed, with the
  separate 200,000-record browser pass. The failures concerned a scope fixture,
  provider selection, a route hash and stale task copy. Its 76 verified PNGs in
  `.desktop-build/holistic-39000193832` remain intermediate evidence.
- `eebe1fe`, [Experience 39001262530](https://github.com/88lin/facetmark/actions/runs/39001262530):
  61 ordinary browser passed / 2 failed. [CI 39001265145](https://github.com/88lin/facetmark/actions/runs/39001265145)
  had those browser failures and a Windows Python 3.10 child-fixture environment
  failure. The next revision preserves a manual model across first successful
  detection, reopens Display after outside dismissal in its fixture, and retains
  the system environment for the UTF-8 child fixture. Captures in
  `.desktop-build/holistic-39001262530` are intermediate, not final acceptance.

## 2026-10-14: OpenCode, reliable agent connections and compact settings (historical verified)

Application and test source: `0a1b8f042c7628cf32b7a09f26f6efc605ef8ea3`.
OpenCode joins Codex and Claude Code. Discovery reads PATH and common installation
locations, including current Windows registry PATH, and resolves npm wrappers
without a shell. The UI shows the actual automatic selection, preserves drafts
during retries, clears failed connection results and invalidates tests when the
resolved CLI changes. Summary and optional embedding settings have separate rows;
shared controls use 10px corners and support surfaces have quieter shadows.

- [Experience 38558317737](https://github.com/88lin/facetmark/actions/runs/38558317737):
  **2033 Python passed / 1 skipped**, **55 ordinary browser tests**, a separate
  **200,000-record browser test**, scale benchmark, frontend build, package
  resources, Docker and extension passed. Real **OpenCode 1.19.0** passed on both
  Windows and Linux against an isolated HTTP model fixture: Chinese stdin, valid
  JSON results, no exposed tools and unchanged source configuration were checked.
- [CI 38558328220](https://github.com/88lin/facetmark/actions/runs/38558328220):
  **all ten jobs passed**, including Linux/Windows with Python 3.10/3.12.
- [Windows 38558317904](https://github.com/88lin/facetmark/actions/runs/38558317904):
  offline installation, frozen-service isolation, installed-app interactions and
  lifecycle checks all passed at the same application source.
- [Visual artifact 11891212284](https://github.com/88lin/facetmark/actions/runs/38558317737/artifacts/11891212284):
  contains **76 PNG captures**. **Eight selected captures** were downloaded,
  visually inspected and SHA256-verified against the matching `provenance.json`;
  the other capture hashes were not independently checked. Small local evidence
  is in `.desktop-build/agent-final-38558317737`.

The two visual passes first identified redundant Settings headings and action
placement, then checked the corrected source. The final eight captures cover
desktop/mobile OpenCode settings, mobile connection errors, desktop/mobile
collections, English dark settings and paused mobile tasks. All five collection
viewport measurements have no horizontal document overflow. A browser assertion
requires Test and save to be fully visible at 1024×749; mobile Settings uses normal
vertical scrolling. The paused mobile task retains a fully visible Resume action.
The single mechanical design scan returned `[]`; it was not rerun. No independent
reviewer verdict or user aesthetic acceptance is claimed for this revision.

The final installed app imported the synthetic HTML file, searched its bookmarks,
opened an original link in Edge through `new_window` with no click-related page
errors, displayed the missing-body state and preserved the query after Preview
return. WebView2 was initially absent and installer networking was blocked.
Same-version reinstall, data-preserving uninstall and backend shutdown with its
parent passed. All three 1028×749 installed-app captures were opened and inspected;
`installed-reader.json` identifies the matching final application source.

- [Small installation evidence 11891104231](https://github.com/88lin/facetmark/actions/runs/38558317904/artifacts/11891104231):
  **164,390 bytes**, retrieved to `.desktop-build/agent-windows-38558317904`.
- [Unsigned Windows x64 preview](https://github.com/88lin/facetmark/actions/runs/38558317904/artifacts/11890914292):
  contains the **279,220,209-byte installer**. The large installer was not
  downloaded or executed locally.

OpenCode uses a temporary session database, isolated instructions, denied tools
and no external plugins while retaining its authentication store for OAuth refresh.
External authentication plugins and organization `wellknown` configuration require
the API integration; see [local-agent support](local-agents.md). Codex/Claude tests
use controlled subprocesses; OpenCode additionally uses real binaries. These tests
do not verify personal model accounts, quotas or real-summary quality. The large
library corpus is synthetic. No personal browser profiles or bookmarks were used.
Builds, browser/scale execution and installation run in Actions; local checks are
lightweight targeted Python/static checks and small evidence inspection. The
unsigned preview uses manual updates, hosted Windows Server results do not certify
all Windows 10/11 machines, and artifacts expire after 14 days. PR #44 remains a
draft with no merge, release or Pages deployment.

## 2026-10-13: collection actions and supporting workflows (historical verified)

Application and test source: `5ea56ab86e4822c1114f9288fbbaebadd5aeea1c`.
This refinement keeps the white/lake-blue identity and direct original links while
making sorting and editing accessible in the collection. Settings has four
keyboard-accessible categories with preserved form drafts; import validates export
types, supports same-file retry and returns to imported bookmarks. Desktop Preview
separates its return controls from the tabs. Tasks has state-specific descriptions,
current progress and recovery before new work, and distinct fetch/summary recovery.

- [Experience 38395130633](https://github.com/88lin/facetmark/actions/runs/38395130633):
  **51 ordinary browser tests**, **2021 Python passed / 1 skipped**, a separate
  **200,000-record browser test**, scale benchmark, frontend build, wheel/sdist
  resources, Docker and extension passed. The ordinary run skips the large test;
  the dedicated large-data run executes it successfully.
- [CI 38395139361](https://github.com/88lin/facetmark/actions/runs/38395139361):
  **all ten jobs passed**, including Linux/Windows with Python 3.10/3.12.
- [Windows 38395130294](https://github.com/88lin/facetmark/actions/runs/38395130294):
  offline installation with WebView2 initially absent and installer networking
  blocked, frozen-service isolation, installed-app navigation and lifecycle checks
  all passed.
- [Visual artifact 11811747380](https://github.com/88lin/facetmark/actions/runs/38395130633/artifacts/11811747380):
  **72 PNG captures**, every SHA256 verified against `provenance.json`; manifest
  source and run match the application above. Small local evidence is in
  `.desktop-build/refinement-verdict-38395130633`.

The first render pass exposed a disclosure wrapping issue that consumed collection
space; the correction kept the existing density thresholds. The subsequent review
inspected 11 desktop/mobile captures at `3947df9` across collection cards/lists,
settings, sync, extension, import, tasks and the English dark reader. It retained
two P2 task findings: paused/terminal captions claimed background work continued,
and current-task recovery followed new-work shortcuts on mobile. The final source
corrects both. Fresh paused/idle task captures were inspected, and the 390×844
browser assertion requires Resume to be fully visible and above the new actions.

The independent verdict pass scored **both P2 findings resolved**, with
**remaining: clear / disposition: ship**. This verdict covers those two fixes,
not whole-product aesthetic acceptance or real-model validation. A general
reviewer and documenter substituted for unavailable Impeccable specialist roles.
The single design detector scan returned `[]`; it was not rerun.

Current density measurements use 1,892 synthetic bookmarks and more than 240
folders. All five sizes have no horizontal document overflow. Counts exclude
partially visible cards and depend on the fixture's content.

| Viewport | List top | List height | Fully visible cards |
| --- | ---: | ---: | ---: |
| 1440×960 | 212.39px | 695.61px | 8 |
| 1366×768 | 212.39px | 503.61px | 3 |
| 1280×600 | 212.39px | 335.61px | 3 |
| 1024×749 | 212.39px | 484.61px | 4 |
| 390×844 | 320.08px | 471.92px | 1 |

The 200,000-record benchmark measured first page **51.39ms**, deep page **94.14ms**,
full keyword scope **86.09ms**, and durable snapshot **357.60ms**. Its snapshot
contains **199,998** items after two exclusions; pending reads are bounded to **64**.
The **3,259-byte tracemalloc peak** is extra Python allocation during that snapshot
operation, not process/database memory. These synthetic measurements do not show
200,000 real model generations or performance on a personal library.

The final installed app opened an original link in Edge via a successful native
`new_window` event with no click-related page errors. Import, keyword search,
missing-body reading state and query preservation after Preview return passed.
Same-version reinstall, data-preserving uninstall and backend shutdown with its
parent passed. The three 1028×749 installed-app captures were opened and inspected;
`installed-reader.json` identifies the final application source above.

- [Small installation evidence](https://github.com/88lin/facetmark/actions/runs/38395130294/artifacts/11811998316):
  176,528 bytes, retrieved to `.desktop-build/refinement-windows-38395130294`.
- [Unsigned Windows x64 preview](https://github.com/88lin/facetmark/actions/runs/38395130294/artifacts/11811918343):
  contains the 279,215,022-byte installer. The large installer was not downloaded
  or executed locally.

All builds, application/browser tests, scale benchmarks and installation execution
run in GitHub Actions. Local work is source/document editing, lightweight static
checks and small evidence inspection. No personal browser profiles or real
bookmarks were used. Real model accounts/services and cloud-drive transport remain
unverified. The Windows x64 preview is unsigned and uses manual updates; hosted
Windows Server checks do not certify all Windows 10/11 machines. Artifacts expire
after 14 days. PR #44 remains a draft with no merge, release or Pages deployment.

## 2026-10-12: original links, visible summaries and bounded collection processing (historical verified)

Final application/test source: `8bf3689e64b7a77222648f65dbe414a588d81731`.
Frontend and Python workflow fix: `3b04e0d534dae0dbf31e326d2e2dbec2c674d76c`.
Verified visual source: `da0b08eef38ba1a3284fa6dfe7fc57c558927c7e`; its only
application difference from that frontend revision is the desktop native-link
plugin configuration. The final source changes only desktop Rust and installation
scripts after the visual capture; frontend, Python source and tests match it.
Native title links open original pages; selection and Preview are independent. The
collection stylesheet is now imported and targets the actual main container.
Desktop and mobile lists show multiline summaries with measured clipping/expansion.
Scoped summary jobs use persistent target snapshots and bounded batches. Installed
Codex/Claude Code adapters reuse CLI settings; tests use synthetic subprocesses and
API fixtures, not a user's model account.

- [Experience 38200196817](https://github.com/88lin/facetmark/actions/runs/38200196817):
  **45 ordinary browser tests**, **2021 Python passed / 1 skipped**, separate
  **200,000-record browser acceptance**, scale benchmark, frontend build, package
  resources, Docker and extension passed. The ordinary browser matrix skips the
  large test, which runs separately against the actual synthetic database.
- [CI 38200198977](https://github.com/88lin/facetmark/actions/runs/38200198977):
  **all ten jobs passed**, including Linux/Windows × Python 3.10/3.12.
- [Visual artifact 11725421003](https://github.com/88lin/facetmark/actions/runs/38200196817/artifacts/11725421003):
  **65 screenshots**, with every capture hash matching the source manifest. The
  main desktop collection, mobile summaries/options, model settings and three
  reprocessing-confirmation captures were opened and checked. Four language/theme
  landing images retain the captured raster data and embedded source metadata;
  those matrix images include the optional reader. Small local evidence is in
  `.desktop-build/bookmark-native-38200196817`.

The 200,000 synthetic-record benchmark measured first page **72.81ms**, deep page
**135.64ms**, full keyword scope **111.63ms**, and durable snapshot **306.71ms**.
The snapshot contains **199,998** items after two exclusions; pending reads are
bounded to **64**. The **3,259-byte tracemalloc peak** measures extra Python
allocations during snapshot creation, not process/database memory. This is paging,
scope and bounded-processing evidence, not 200,000 real model generations or a
benchmark of the user's library.

The independent general reviewer originally inspected 12 valid screenshots and
requested one P2 correction: reprocessing must not claim completed items are
skipped. The new desktop/mobile captures and browser assertion show the count and
explanation switching **0 → 1,892 → 0**. The verdict pass returned **ship**, scoring
that one finding **resolved**. This is a fix-scoped verdict, not whole-product
approval or user aesthetic acceptance. The specialist was unavailable, so a
separate general reviewer fulfilled the contract. The single design detector pass
returned `[]`; it was not rerun.

Final-source confirmation:

- [Experience 38244640757](https://github.com/88lin/facetmark/actions/runs/38244640757):
  45 ordinary browser scenarios, the separate 200,000-record scenario, 2021 Python
  tests (1 skipped), frontend/package checks, Docker and extension passed.
- [CI 38244648319](https://github.com/88lin/facetmark/actions/runs/38244648319):
  all ten jobs passed.
- [Windows 38244640923](https://github.com/88lin/facetmark/actions/runs/38244640923):
  offline installation with WebView2 initially absent and installer networking
  blocked, frozen-service checks, actual installed import/search/original-link/
  preview-return flow, same-version reinstall, parent-process cleanup and uninstall
  data retention all passed.

The Windows evidence records `original_opened_in_system_browser: true`, an actual
Edge request to the disposable `/original` destination, no click-related WebView
errors, and a native `new_window` event with `error: null`. The workbench stays at
its original URL; Preview is separate and returning preserves the search query.
Three 1028 × 749 installed captures were opened and checked. The
[170,006-byte evidence artifact](https://github.com/88lin/facetmark/actions/runs/38244640923/artifacts/11746731014)
is saved under `.desktop-build/bookmark-final-windows-38244640923`.
The [unsigned Windows x64 preview](https://github.com/88lin/facetmark/actions/runs/38244640923/artifacts/11746416238)
contains a **279,196,220-byte installer**; the large package was not downloaded locally.

The earlier external-link failures exposed two injected JavaScript interceptors.
The opener plugin now disables its click script; `native_shell.rs` delegates the
official shell plugin's Rust initialization/event lifecycle without exposing its
legacy web script or IPC. Native navigation handlers open HTTP/HTTPS destinations.
The failure diagnostic's independent OS control cannot satisfy the app-click gate;
the final successful run used the real installed title click.

All builds, browser execution, scale benchmarks and installation tests run in
GitHub Actions. Local work is editing, lightweight checks and small evidence
retrieval. No real bookmarks or personal browser profiles were accessed. Real
model accounts/services, cloud-drive transport, Windows 10/11 hardware,
non-administrator behavior and cross-version upgrades remain unverified. The
unsigned x64 preview uses manual updates; artifacts expire after 14 days. PR #44
remains a draft with no merge, release or Pages deployment.

## 2026-10-11: readable typography and everyday collection flows (final cloud validation passed)

The user rejected the small, thin typography and asked for further visual and
functional refinement without more preference questions. Current source:
`bbd6cae273ccfa2dd44ee75542900f60f6cf7893`. Card/list titles share an 18px-equivalent
700-weight role, routine controls/categories use 14px, and source/date metadata uses
13px. Core sizes use rem; Chinese titles have normal tracking and explicit system
fallbacks. The compact header and collection toolbar remain. Context-aware creation,
organization/export defaults, page jumping, named filters and page-only deselection
address concrete friction in everyday library use.

Five added browser scenarios cover readable roles and 125% text scaling, last-page
navigation, cross-page selection, explicit Unfiled filters and a create/export flow
inside combined folder/tag filters. Final corrections keep category labels on one
line and mobile collection actions beside the 44px view toggle in both languages.
Secondary mobile actions retain their names and touch targets without redundant icons.

All final runs completed on 2026-10-10 and were rechecked on 2026-10-11 against
the application and browser-test source above:

- [Experience 38051851958](https://github.com/88lin/facetmark/actions/runs/38051851958):
  **42/42 browser tests**, **2003 Python passed / 1 skipped**, Ruff, TypeScript/Vite,
  wheel/sdist resources, Docker and extension passed.
- [CI 38051855595](https://github.com/88lin/facetmark/actions/runs/38051855595):
  **all ten jobs passed**, including Linux/Windows × Python 3.10/3.12.
- [Visual artifact 11670640239](https://github.com/88lin/facetmark/actions/runs/38051851958/artifacts/11670640239):
  **56 actual screenshots**, **14.32-second recording**, WEBM and typography/layout
  diagnostics. All 56 capture hashes match the source manifest. Local evidence:
  `.desktop-build/readability-38051851958`. Four landing images preserve captured
  raster chunks and embed this source/run. Measured text: titles 18px / weight 700,
  summaries 15px, sources 13px, categories/actions 14px, search 16px. The 125% text
  scaling test passed, including unbroken category labels and document overflow checks.
- [Windows 38051852075](https://github.com/88lin/facetmark/actions/runs/38051852075):
  offline installation with WebView2 initially absent and installer networking blocked,
  real installed WebView import/search/missing-body state/query-preserving return,
  same-version reinstall, uninstall data retention, parent-process cleanup and frozen
  service checks passed. Three installed 1028×749 screenshots and diagnostics were
  inspected; the reader evidence records `bbd6cae`.
  [Unsigned x64 preview](https://github.com/88lin/facetmark/actions/runs/38051852075/artifacts/11670495977)
  contains an installer of **279151591 bytes**; the package was not downloaded locally.
  [Small installation evidence](https://github.com/88lin/facetmark/actions/runs/38051852075/artifacts/11670785603)
  is saved at `.desktop-build/readability-windows-38051852075`.

Measured card view with 1892 synthetic bookmarks and 295 folders; fully visible
counts exclude partial cards:

| Viewport | List top | First card top | List height | Height share | Fully visible cards |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1440×960 | 164px | 167px | 744px | 77.5% | 16 |
| 1366×768 | 164px | 167px | 552px | 71.9% | 9 |
| 1280×600 | 164px | 167px | 384px | 64.0% | 6 |
| 1024×749 | 164px | 167px | 533px | 71.2% | 6 |
| 390×844 | 216.1px | 219.1px | 575.9px | 68.2% | 3 |

No tested viewport has horizontal document overflow. A fresh independent visual review
inspected 12 final captures and sampled the source, returning **ship** with no material
fixes. The specialized reviewer was unavailable, so a general reviewer fulfilled the
contract in a separate context. The targeted design detector returned no findings.
This review covers the current readability and collection-flow refinement; it does
not certify an external QUALITY BAR or constitute user aesthetic acceptance.

All builds, browser execution and installer checks run in Actions. Local work is
source editing, lightweight checks and small evidence retrieval. No real bookmarks or
personal browser profile was used. Real cloud-drive transport, external model services,
Windows 10/11 hardware, non-administrator behavior and cross-version upgrades remain
unverified. This unsigned preview uses manual updates; artifacts expire after 14 days.
PR #44 stays a draft, with no merge, release or Pages deployment.

## 2026-10-10: large-collection usability correction (historical)

The user rejected the previous collection layout: oversized upper controls left
only about half the window for bookmarks, and horizontal categories were
inconvenient with a mouse. Its historical review verdict is not current acceptance.

Current application and browser-test source: `09ab0332c5f9ec40627afc7f48f3da2ce0b8b36b`.
The correction adds compact upper controls, a complete searchable vertical
folder/tag/site directory, explicit category pagination and persistent card/list
choice. Search reaches the whole category directory, with exact matches before
prefixes and substrings, stable ordering and pages of 50. It fixes repeated-category/
query cancellation, real scroll/page/reader reset on scope changes and stale-result
selection/export during loading or failure. Repeated Enter and IME completion
settle correctly; opening and returning from the same result retain browsing context.

All final runs completed on 2026-10-09 against the source above:

- [Experience 37927920369](https://github.com/88lin/facetmark/actions/runs/37927920369):
  all three jobs passed, including **37/37 Playwright**, **2003 Python passed /
  1 skipped**, Ruff, TypeScript/Vite, wheel/sdist resources, Docker and extension.
- [CI 37927928123](https://github.com/88lin/facetmark/actions/runs/37927928123):
  **all ten jobs passed** across Linux/Windows × Python 3.10/3.12, browser,
  web UI, extension, Karakeep contract, wheel and Docker. The real MCP stdio
  check passed **22/22**.
- [Visual artifact 11615446805](https://github.com/88lin/facetmark/actions/runs/37927920369/artifacts/11615446805):
  **51 actual captures**, a **14.24-second H.264 recording**, WEBM, font/scroll
  diagnostics and exact source/run provenance. All 51 capture hashes were verified.
  Local evidence: `.desktop-build/collection-verified`. The four landing screenshots
  retain the source raster chunks and carry embedded origin metadata.
- [Windows 37927920467](https://github.com/88lin/facetmark/actions/runs/37927920467):
  all checks passed. Installation began with WebView2 absent and installer networking
  blocked. The installed WebView imported synthetic HTML, searched, displayed the
  correct missing-body reader state and preserved the query on return. Same-version
  reinstall, uninstall data retention, parent-process cleanup and isolated frozen
  service checks also passed. Three installed 1028×749 screenshots were inspected;
  diagnostics identify `09ab033`.
  [Unsigned x64 installer](https://github.com/88lin/facetmark/actions/runs/37927920467/artifacts/11615112516)
  and [small installed evidence](https://github.com/88lin/facetmark/actions/runs/37927920467/artifacts/11614867739)
  are available. The installer itself is **279209682 bytes** and was not downloaded.
  Valid local installed evidence is `.desktop-build/collection-windows-37927920467`;
  the older `.desktop-build/collection-windows` directory is mixed/stale and excluded.

Final CI Python matrix (all jobs passed; skips vary by platform/runtime):

| Platform | Python | Passed | Skipped |
| --- | --- | ---: | ---: |
| Linux | 3.10 | 2002 | 2 |
| Linux | 3.12 | 2003 | 1 |
| Windows | 3.10 | 1972 | 32 |
| Windows | 3.12 | 1973 | 31 |

The synthetic corpus contains **1892 bookmarks and 295 folders**, including long
names, and saved pages with and without body text. The six added browser scenarios
cover compact short-window layouts, complete category access by mouse and keyboard,
search beyond the former 200-category limit, card/list persistence, slow/repeated
queries, failed scopes, export safety and reading return context. Existing management,
sync, model, import, reading and theme/language tests remain in the 37-test suite.

Measured card view from `collection-density.json`; counts exclude partly visible cards:

| Viewport | List top | First card top | List height | Height share | Fully visible cards |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1440×960 | 160px | 163px | 748px | 77.9% | 16 |
| 1366×768 | 160px | 163px | 556px | 72.4% | 9 |
| 1280×600 | 160px | 163px | 388px | 64.7% | 6 |
| 1024×749 | 160px | 163px | 537px | 71.7% | 6 |
| 390×844 | 215.7px | 218.7px | 580.3px | 68.8% | 3 |

No tested viewport has horizontal document overflow. Desktop and mobile card/list,
category search/drawer, reader and language/theme captures were inspected. Measurements
describe this synthetic corpus and viewport set, not every title length or real library.

The first browser pass on `c4d5886` passed 34/37: exact category names were buried
after 50 substring matches. `09ab033` fixes relevance ordering and passes the same
assertions. That superseded run and `.desktop-build/collection-first-review` are not
final evidence. Local targeted backend verification passed 25 workbench tests and Ruff.
After the screenshot refresh, both lightweight landing image-reference checks passed.

The fresh independent rejection review identified six material issues: upper-space
budget, complete category access, repeated-request correctness, scope scroll/reader
reset, stale-result action safety, and realistic data/current documentation. The
final scored confirmation marked **all six resolved**, with **remaining clear** and
`disposition: ship`, limited to those six corrections. No material regressions from
the fix batch were observed. The reviewer directly inspected 12 original screenshots
(short desktop/mobile, category/list, keyboard, reader, dark, loading and failure),
provenance, density/scroll records, related source/tests, the Experience log and
Windows reader/lifecycle JSON. It did not run the application or tests itself.

The specialized review role was unavailable; the original confirmation and its
replacement initially failed on model rate limits. A general independent replacement
reviewer completed this confirmation after recovery. The verdict does not constitute
user aesthetic acceptance. No approved pixel comp or external QUALITY BAR was
supplied; GithubStarsManager is an interface reference only.

DESIGN.md, the surface contract, management instructions and screenshot provenance
track the corrected interface and final evidence. Documentation/image-only commits
after `09ab033` do not alter the tested application or test source.

Builds, browsers, packaging and installation ran in Actions. Local work was source
editing, lightweight checks and small evidence retrieval; no personal profile,
real bookmarks or local installer execution was used. Actual cloud-drive transport,
external model services and Windows 10/11 hardware remain outside verification.
The unsigned preview uses manual updates; hosted Windows Server checks do not
certify signing trust, ordinary non-administrator behavior, cross-version upgrades
or physical whole-machine disconnection. Artifacts expire after 14 days. The
[existing PR #44](https://github.com/88lin/facetmark/pull/44) stays a draft, without
main merge, release or Pages deployment. Earlier sections are historical.

## 2026-10-08: collection management, reading tasks and shared-folder sync (historical)

Application source: `33ff0df5340b31061434deb7e341c612e22feae1`.
Final browser/test source: `f757f33e00a0a3582e4b656865bddd51d3d4f445`.
The latter changes only a native-option test assertion; `frontend/src`, `src`,
`desktop` and `pyproject.toml` are identical. Subsequent documentation and image
metadata changes do not change the tested application.

The existing white/lake-blue collection and focused reader now support bookmark
creation/editing/deletion, bulk organization, exact-name folder/tag operations,
scoped JSON/HTML export, independent text-fetch/summary tasks and shared-folder
metadata synchronization. Task completion refreshes both the list and cached
reader, including when the application opens during an already-running task.

- [Experience 37774845284](https://github.com/88lin/facetmark/actions/runs/37774845284):
  all three jobs passed. TypeScript/Vite, **31/31 Playwright**, **1996 Python passed /
  1 skipped**, Ruff, wheel/sdist resources, Docker and extension checks passed.
- [CI 37774856968](https://github.com/88lin/facetmark/actions/runs/37774856968):
  **all ten jobs passed**, including Linux/Windows × Python 3.10/3.12, browser,
  web UI, extension, Karakeep contract, wheel and Docker. The real MCP stdio
  check passed **22/22**.
- [Visual artifact 11549727814](https://github.com/88lin/facetmark/actions/runs/37774845284/artifacts/11549727814):
  **42 actual captures**, a **13.64-second H.264 recording**, WEBM, font/scroll
  diagnostics and source/run provenance. All 42 screenshot SHA-256 hashes were
  verified locally. Evidence: `.desktop-build/library-verified`.
- [Windows 37773749998](https://github.com/88lin/facetmark/actions/runs/37773749998):
  passed on application source `33ff0df`. The offline installer, isolated frozen
  service, installed WebView import/search/reader return, same-version reinstall,
  uninstall data retention and parent-process cleanup all passed. Installation began
  with the runtime absent and installer networking blocked. Three installed
  1028×749 screenshots were inspected; the reader correctly reports missing body
  text for the synthetic HTML import. Diagnostics identify the same commit.
  [Unsigned x64 installer](https://github.com/88lin/facetmark/actions/runs/37773749998/artifacts/11548884372)
  and [small installed evidence](https://github.com/88lin/facetmark/actions/runs/37773749998/artifacts/11549224103)
  are available. The installer itself is **276907454 bytes** and was not downloaded.
  Local small evidence: `.desktop-build/library-windows`. No Windows rebuild was
  needed for the later test-only assertion change.

Final CI Python matrix counts (each job passed; skips vary by platform/runtime):

| Platform | Python | Passed | Skipped |
| --- | --- | ---: | ---: |
| Linux | 3.10 | 1995 | 2 |
| Linux | 3.12 | 1996 | 1 |
| Windows | 3.10 | 1965 | 32 |
| Windows | 3.12 | 1966 | 31 |

The 12 added browser tests cover literal folder/tag persistence, deletion consent
and cancellation, keyboard bulk selection, scoped downloads and exported body
text, taxonomy merges/removal, fetch versus summary prerequisites, send consent,
mobile modal focus/return, failed-save draft retention, task-completion refresh,
sync preview/apply/persistence, stale-preview rejection, concurrent versions,
duplicate-URL deletion, synchronization disabling and load-failure retry. Existing
search, reading, import, model and responsive regressions remain in the 31-test run.
Synchronization uses temporary synthetic libraries/folders; actual cloud-drive
transport and external model providers were not exercised.

A fresh independent review of the extension's desktop/mobile evidence found one
material issue: the tag placeholder had insufficient contrast. The corrected
`var(--muted)` placeholder measures **5.21:1** in both final-source captures; the
shortened hint and wrapping guidance remain visible at 390px. The reviewer returned
**ship** for this fix with no observed introduced regressions. A generic independent
agent followed the Impeccable contract because the specialized role was unavailable.
The verdict covers the scored fix, not user aesthetic acceptance, installation or
frame-by-frame video quality. No external QUALITY BAR or approved comp was supplied.
The successful-run collection, mobile editing and desktop conflict captures were
also inspected; application source matches the reviewed correction.

DESIGN.md preserves the existing tokens and sidecar, with scoped prose for destructive
actions, pill fields in management dialogs and contextual actions inside the reader.
The four landing workbench screenshots were refreshed from this successful run;
all retain identical source raster chunks with embedded origin metadata.

The [management guide](library-management.md) records operating limits: sync exchanges
only bookmark metadata through an existing shared folder; summaries require explicit
chat consent; JSON export can include reading data, but reimport restores metadata
only. Karakeep-linked records are protected. Management APIs require pairing, enabled
administration and a loopback caller. Automatic sync can propagate conflict-free
deletions after initial approval; incoming changes receive a local database backup.
Ordinary CRUD has no recycle bin, and there is no one-click restore or history
compaction. Capacity and recovery procedures are documented in the guide.

Local work remained limited to source editing, lightweight checks and small evidence.
Builds, browsers, packaging and installation run in Actions. No personal browser
profile was used, and the installer was not downloaded or run locally. The unsigned
preview uses manual updates. Hosted Windows Server does not certify Windows 10/11
hardware, ordinary non-administrator behavior, cross-version upgrades, physical
whole-machine disconnection or signing trust. Artifacts expire after 14 days.
The existing draft PR #44 remains the delivery target; no merge, release or Pages
deployment is included. Earlier sections below are historical.

## 2026-10-07: collection and focused-reading redesign (historical)

The latest user feedback called for stronger frontend design and component craft.
Application and test source: `0aa3e849ae06d6707fb1f52356eefe6bd774ff4a`.
This revision adds a distinct collection masthead, separate search row, real folder
shortcuts, three-column source-first cards, compact supporting index, bundled
Manrope, keyboard-operable cmdk suggestions and a real-heading reading outline.

- [Experience 37618229826](https://github.com/88lin/facetmark/actions/runs/37618229826):
  TypeScript/Vite, 19/19 Playwright, 1882 Python passed / 1 skipped,
  distribution resources, Docker and extension passed.
- [CI 37618237956](https://github.com/88lin/facetmark/actions/runs/37618237956): all ten jobs passed.
- [Visual artifact 11480239215](https://github.com/88lin/facetmark/actions/runs/37618229826/artifacts/11480239215):
  37 actual captures, 14.08-second H.264 recording, WEBM, scroll/font diagnostics
  and exact commit/run provenance. All 37 capture hashes match locally.
- [Windows 37618229866](https://github.com/88lin/facetmark/actions/runs/37618229866):
  offline installation with the runtime initially absent and installer networking
  blocked, installed WebView import/search/reader return, same-version reinstall,
  uninstall data retention, parent-process cleanup and frozen-service isolation passed.
  [Unsigned x64 installer](https://github.com/88lin/facetmark/actions/runs/37618229866/artifacts/11481542111)
  and [small installed evidence](https://github.com/88lin/facetmark/actions/runs/37618229866/artifacts/11481562146)
  are available. The installer is 276845762 bytes and was not downloaded locally.
  Three installed 1028×749 captures were inspected; diagnostics identify the same
  source and the truthful missing-body state for synthetic HTML imports.
- A fresh independent full finish review returned **ship** with no material fixes.
  A generic independent agent followed the Impeccable reviewer contract because
  the specialized role was unavailable. All required captures were valid. The
  review used screenshots/source/storyboard; direct animation timing was covered
  by cloud runtime checks rather than the reviewer's static inspection. No current
  external QUALITY BAR or approved comp was supplied, so that comparative ceiling
  is unverified. The user-pinned continuation did not claim a new concept election.

Browser coverage includes query-menu keyboard selection and insertion, Escape and
focus return, request failure/retry/loading, empty suggestions, whitespace/quote
escaping, real folder shortcuts, outline jumps, search/IME races, pagination,
reader selection, tab/scroll restoration, reversible focus, mobile modality,
reduced motion and Chinese/English/light/dark at 1440/1280/1024/390 widths.
The one static Impeccable detector pass returned `[]`.
The local visual batch includes seven contact sheets plus full-size collection,
split/focused/mobile readers, settings, query menus and the interaction storyboard.
The documentation comparison inspected five matching source captures. Four landing
images preserve identical PNG raster chunks with updated origin metadata.
Local work is limited to source editing, lightweight checks and small evidence;
all application runtime, packaging and installation checks run in Actions.
No personal browser profile or external model service was used.
Local evidence is `.desktop-build/collection-elevated` and
`.desktop-build/collection-elevated-windows`. Review does not imply user aesthetic
acceptance. Hosted Windows Server checks do not certify Windows 10/11 hardware,
cross-version upgrades, ordinary non-administrator behavior or signing trust.

## 2026-10-07: capsule controls and refined reading rhythm (historical)

The user found the previous delivery only slightly improved and explicitly required
capsule buttons plus more complete visual refinement. Current application and test
source: `1d006544740e2c2965530a503393ccf333674a05`.

- [Experience 37466126567](https://github.com/88lin/facetmark/actions/runs/37466126567):
  TypeScript/Vite, 14/14 Playwright, 1882 Python passed / 1 skipped, Python
  distribution resources, Docker and extension passed.
- [CI 37466133676](https://github.com/88lin/facetmark/actions/runs/37466133676): all ten jobs passed.
- [Visual artifact 11414603412](https://github.com/88lin/facetmark/actions/runs/37466126567/artifacts/11414603412):
  35 actual captures, a 13.68-second H.264 recording, WEBM, font/scroll diagnostics
  and source provenance. All 35 capture hashes were verified locally.
- [Windows 37466126767](https://github.com/88lin/facetmark/actions/runs/37466126767),
  attempt 2 on the same source: offline installation with the runtime absent and
  installer networking blocked, installed WebView import/search/reader return,
  same-version reinstall, uninstall data retention, parent-process cleanup and
  frozen-service isolation passed. The first attempt had failed after compilation
  while downloading Microsoft WebView2 (`Peer disconnected`); the retry resolved it.
  [Unsigned x64 installer](https://github.com/88lin/facetmark/actions/runs/37466126767/artifacts/11479497637)
  and [small installed evidence](https://github.com/88lin/facetmark/actions/runs/37466126767/artifacts/11478997809)
  are available. The installer itself is 276793305 bytes and was not downloaded locally.
- A fresh independent full visual review returned **ship**, with no material UI
  fixes listed, after opening all 12 required visual inputs and six contact sheets.
  A generic independent agent followed the Impeccable finish-review contract because
  the specialized role was unavailable. The current QUALITY BAR image and historical
  seed's raw roll were not available; both direction files disclose that provenance
  limit and identify the user's explicit pinned brief as authoritative.

Inspected captures cover the collection, split/focused reader, mobile/tablet reader,
Chinese/English, light/dark, import, models, tasks, keyboard focus and controlled
loading/empty/long-title/failure states. The new 390px settings capture also covers
the larger form controls. Review uses actual captures and the interaction storyboard,
not direct local browser use. Local evidence: `.desktop-build/capsule-first`.
The single Impeccable detector pass returned `[]`; it is not aesthetic acceptance.
DESIGN.md and its sidecar reflect the actual source. Four landing images use this
render with unchanged raster chunks and embedded origin; all four metadata scans pass.
Neither the independent review nor the automated checks claims user acceptance.
Source editing, lightweight checks and small evidence retrieval are the only local
operations. No personal browser profile or external model service was used.
Three actual installed WebView screenshots at 1028×749 were inspected from
`.desktop-build/capsule-windows`; its JSON identifies the same application commit.
The tested reader shows the truthful missing-body state for imported synthetic HTML.
Hosted Windows Server results do not certify Windows 10/11 hardware, cross-version
upgrades, ordinary non-administrator behavior or signing trust.

## 2026-10-06: white and lake-blue confirmation (historical)

The user explicitly selected pure white, lake blue, rounded panels and refined
controls after rejecting the grey-violet result. Shared UI and test revision:
`7a20776e6fa49bb55cab4e35bf43753477c76fef`. Later documentation/image metadata
commits do not change this application source. The older sections below are history.

| Check | Current evidence |
| --- | --- |
| Shared frontend and browser | [Experience 37459945939](https://github.com/88lin/facetmark/actions/runs/37459945939): TypeScript/Vite, 14/14 Playwright, 1882 Python passed / 1 skipped, wheel/sdist, Docker and extension passed |
| Full CI | [37459952441](https://github.com/88lin/facetmark/actions/runs/37459952441): all ten jobs passed |
| Installed Windows preview | [37459946022](https://github.com/88lin/facetmark/actions/runs/37459946022): build, frozen service, installed WebView, import/search/return and lifecycle checks passed |

[Visual artifact 11411617427](https://github.com/88lin/facetmark/actions/runs/37459945939/artifacts/11411617427)
contains 34 actual screenshots, a 13.2-second H.264 recording, WEBM, font/scroll
diagnostics and commit/hash provenance. Inspected scope: Chinese/English,
light/dark, 1440/1280/1024/390 widths, collection, selected reader, focused reading,
keyboard focus, import, models, tasks, long titles, loading, empty and failure states.
Recordings exercise search, reading, summary, focus expansion/reversal and rapid
selection. Tests preserve query, selected-row focus and list/reader scroll positions;
the recorded article position was 253px within a 254px extent and was restored.

One visual inspection batch found closed-navigation shadow leakage and uneven
collection metadata positions. Both were corrected together and confirmed in
the second capture batch. The independent review returned **ship** with both fixes
**resolved**; this verdict only scores those listed fixes. Review used screenshots,
source and an interaction storyboard, not direct playback or a live browser.
The unavailable specialized Impeccable roles were replaced by fresh generic agents
using its reviewer/documenter contracts. A single static detector pass returned `[]`.
No review or automated check claims user acceptance of the aesthetic.

First run `37456691191` passed browser/build checks but failed the historical landing
page consistency test: the committed English help used `&amp;`, while its generator
used `&`. Commit `85cc439` synchronized the generator; 137 targeted local checks
and all subsequent cloud checks passed. Screenshot capture now waits for the reading
drawer to settle, and disables CSS transitions in navigation evidence.

[Installed evidence 11413073197](https://github.com/88lin/facetmark/actions/runs/37459946022/artifacts/11413073197)
contains three inspected WebView screenshots and JSON diagnostics. At 1028×749,
the installed app imported synthetic HTML, searched, showed the truthful unsaved-body
state and returned to the collection with its query preserved. Same-version reinstall,
uninstall data retention, parent-process cleanup, port collision, Unicode paths,
authenticated identity and frozen-service isolation passed. The unsigned
[Windows x64 installer](https://github.com/88lin/facetmark/actions/runs/37459946022/artifacts/11412588346)
stays in Actions; it was not downloaded or run locally.

Local small evidence: `.desktop-build/lake-blue-final` and `.desktop-build/lake-blue-windows`.
Four landing screenshots use this final render with unchanged pixels and embedded origin.
Only source editing, lightweight checks and small evidence retrieval occurred locally.
Windows Server runners do not certify Windows 10/11 hardware, cross-version upgrades,
ordinary non-administrator behavior or signing trust. Real model services and personal
browser profiles were not used. No main merge, formal release or Pages deployment.

## 2026-10-06: structural rebuild after user rejection

The user rejected the appearance below as too ordinary and resembling an admin
tool. Its functional results remain historical evidence, not visual acceptance.
A fresh independent review returned **rebuild**. Revision `33bee64` introduces
top navigation, on-demand filters, a full collection index and a content-led
reader. [First render run 37407299839](https://github.com/88lin/facetmark/actions/runs/37407299839)
passed build/backend/distribution checks but only 8/14 browser tests: five
duplicate navigation-role matches and one obsolete fixed scroll-offset assertion.
The first screenshot batch exposed inconsistent collection alignment, clipped
row metadata, excess focused-reading chrome and an unclear narrow-reader return.
Consolidated correction `90f551b` addresses those findings and records actual
scroll extent. This is the current rendered application source.

### Confirmed shared frontend

[Experience 37410551657](https://github.com/88lin/facetmark/actions/runs/37410551657)
passed **14/14 Playwright tests**, **1882 Python tests / 1 skipped**, TypeScript/Vite,
wheel/sdist, extension and Docker checks on `d6597e9a488bf434afe3121cd5d68587c9b3140f`.
That revision changes only the test activation of the moving reader control;
application source is unchanged from `90f551b38bd1ee15833d40c97cf1e2cf93c082fd`.
[CI 37411031139](https://github.com/88lin/facetmark/actions/runs/37411031139)
passed all ten jobs on `d6597e9`, including Linux/Windows × Python 3.10/3.12.

The small [visual evidence artifact](https://github.com/88lin/facetmark/actions/runs/37410551657/artifacts/11389029798)
contains **33 actual captures**, MP4/WEBM, font measurements and source provenance.
Local evidence is `.desktop-build/collection-final`; landing assets copy its four
1440px language/theme captures without changing image pixels. All data is synthetic.

Inspected scope: Chinese/English and light/dark at 1440, 1280, 1024 and 390 widths;
unselected collection, selected article, focus reading, full-width narrow/mobile
reading, import, settings, tasks, long titles, loading, empty and controlled errors.
Runtime checks cover stale responses, real import persistence, model test/consent
boundaries, filter recovery, chapter navigation, tab scroll restoration, immediate
keyboard reversal, narrow-reader return, focus restoration and reduced motion.
`scroll-context.json` records a real article position of 247px within a 248px extent
and exact restoration. The same test then verifies a nonzero result-list position
across focus/restore/close, selected-row focus and unchanged query.

The failed confirmation `37409459848` and CI `37409462928` each passed 13/14 browser
tests. Their remaining failure was a forced coordinate click missing an animating
button, demonstrated by the captured Playwright trace: the second click left
`aria-pressed=false`, so Escape correctly closed the reader. `d6597e9` uses real
keyboard activation on that focusable button and asserts both transitions instead
of forcing stale coordinates. Product code was not changed to accommodate the test.

The fresh independent full rebuild review returned **ship** for the supplied
visual composition, states and interaction storyboard; all four structural
corrections were resolved. It read the final provenance and scroll diagnostics.
The reviewer did not directly play the MP4, so its verdict does not certify every
animation frame or Windows installation. Specialized Impeccable roles were
unavailable; fresh default agents used the shipped reviewer/documenter contracts.
This verdict is not user acceptance of the visual design.

DESIGN.md and `.impeccable/design.json` now describe the actual stylesheet order
and three collection/reading compositions. Shared forms remain in `styles.css`;
`workbench.css` owns composition overrides. No local build or browser ran.

### Windows confirmation

The `90f551b` desktop run built and installed the application, rendered setup,
imported synthetic HTML and opened the correct missing-body state. Its smoke
script then failed because it sought the old close-button label in the new
full-width narrow reader. Test-only `429e6e0` follows the visible “返回收藏”
action in that layout and captures the returned collection. The product source
is unchanged. [Windows run 37411693696](https://github.com/88lin/facetmark/actions/runs/37411693696)
passed on `429e6e0a57459be8dbaec459737153678ac83429`:

- Frozen-service isolation, no Python on child PATH, port conflict, Unicode path,
  static assets, keyword search, authenticated identity, single-instance data scope
  and graceful shutdown/data retention passed.
- Installed Tauri WebView at 1028×749 rendered setup, imported two synthetic
  bookmarks, searched, opened the truthful missing-body state and returned via
  “返回收藏” with the query intact. All three installed captures were inspected.
- Same-version reinstall, uninstall data retention and parent-process cleanup passed.

Small [installation evidence](https://github.com/88lin/facetmark/actions/runs/37411693696/artifacts/11390071119)
is saved in `.desktop-build/collection-windows-final`.
The [unsigned Windows x64 installer](https://github.com/88lin/facetmark/actions/runs/37411693696/artifacts/11390096074)
remains in Actions; it was not downloaded or executed locally. Hosted Windows
Server limitations below still apply.

Historical record from 2026-10-05. Branch: `desktop/facetmark-experience`.
This is an unsigned test-branch delivery. No main merge, production deployment or
formal release is part of this work. All browsers, installers, large downloads
and packaging run in GitHub Actions.

## Historical redesign rejected by the user: rendered UI `d618c52`

The shared frontend was redesigned around a source-first result index and a
continuous reader. [Experience run 37311576521](https://github.com/88lin/facetmark/actions/runs/37311576521)
passed **1882 Python tests / 1 skipped**, **14 Playwright tests**, TypeScript/Vite,
wheel/sdist resources, extension checks and Docker. [CI run 37311583781](https://github.com/88lin/facetmark/actions/runs/37311583781)
passed all ten jobs, including Linux/Windows × Python 3.10/3.12.

The **32 real captures** and MP4/WEBM are in the small `facetmark-visual-evidence`
artifact, ID `11345718546`. PNG metadata and `provenance.json` identify exact UI
commit `d618c524ec4f5b0590f867fdd11bea2765791c34`, run, dimensions and hashes.
The four landing workbench assets are from this confirmation batch. Locally
retrieved evidence is in `.desktop-build/redesign-confirmation`.

Checked scope:

- Chinese and English × light and dark × 1440, 1280, 1024 and 390 widths.
- Chinese desktop search with a selected bookmark and article body; six complete
  result rows at 1440×960; focused reading; narrow-window and mobile drawers.
- Import, settings, tasks, long title, loading, empty and controlled failure states.
- Delayed/stale body responses, immediate cached selection, chapter jumps,
  back-to-top, tab scroll restoration, rapid expansion/drawer reversal, focus
  return, keyboard navigation and reduced motion.
- Runtime font inspection: Noto Sans CJK SC on the Linux runner, reading text
  16px / 31.2px and source metadata 11px / 18px.

One initial batch was inspected, the material corrections were applied together,
and the confirmation batch was inspected. No generated mockups or personal data
were used. The independent reviewer's final verdict was **ship**, scoring all
seven original findings resolved after the nonzero result-list scroll proof
passed. This is a scoped correction review, not user acceptance of the visual design. Specialized
Impeccable reviewer/documenter roles were unavailable, so fresh default agents
used their shipped contracts.

Test-only commit `8da4e35` adds that nonzero list-position assertion. Its explicit
[follow-up Experience run 37312860101](https://github.com/88lin/facetmark/actions/runs/37312860101)
passed all **14 browser tests**, including that assertion, plus **1882 Python
tests / 1 skipped** and build/distribution/extension/Docker checks. It selects a
visible row in a scrolled list, opens/restores focused reading, closes the reader,
and requires the original list position within 1px, selected-row focus and the
unchanged query. The application source is unchanged from `d618c52`; automatic CI was
skipped for this test-only commit and this required browser run was dispatched
explicitly to avoid repeating the Windows installer matrix.

[Windows run 37311576569](https://github.com/88lin/facetmark/actions/runs/37311576569)
passed on the same UI source. The small `desktop-install-evidence` artifact
(ID `11346498949`) was retrieved and both installed WebView captures inspected:

- Frozen service runs without Python on the child PATH; port collision, Unicode
  path, bundled assets, keyword search, authenticated identity, per-directory
  single instance and graceful shutdown/data retention checks passed.
- The actual installed Tauri WebView rendered setup, imported two synthetic HTML
  bookmarks, searched them, opened the truthful missing-body state and retained
  the query after closing. `installed-reader.json` records the source commit.
- Same-version reinstall, uninstall data retention and parent-process cleanup passed.
- The unsigned Windows x64 installer is in `facetmark-windows-x64-preview`,
  artifact ID `11346484011`. It includes the frozen service and WebView2 offline
  installer; the large installer was not downloaded or run locally.

Local checks were limited to source formatting, Ruff, JSON/token validation,
diff checks, evidence inspection and metadata/pixel-identity checks. No local
browser, frontend build, desktop packaging or installation was performed.

## Redesign correction history

`673af75` initially failed dependency installation because Motion's transitive
framer-motion range was accidentally pinned. `3bf0c3f` restored that range;
direct dependencies remain pinned. Its first browser run passed 12/14 tests.
One exposed scroll anchoring interfering with explicit tab restoration; another
used a supposed empty query whose words matched the synthetic OR-search corpus.
`d618c52` disables browser anchoring for the explicitly managed reader and uses a
truly unmatched test query. It also installs ffmpeg in the cloud workflow for MP4
evidence, corrects the focus-mode grid seam and makes the reading drawer reversible.
These failed runs are not counted as the final passing evidence above.

## Historical shared Web baseline

[Experience run 37203068070](https://github.com/88lin/facetmark/actions/runs/37203068070)
passed on `3622848`: **1882 Python tests / 1 skipped**, **8 Playwright tests**,
TypeScript/Vite, wheel and sdist resource checks, extension build/tests and a
running non-root Docker container with a read-only filesystem.

The behavior checks cover real import persistence, stable paging, IME composition,
stale responses, separate model probes, explicit indexing consent, persistent tasks,
query suggestions, cited answers, mobile navigation focus and drawer focus return.
Model probes in browser tests use controlled responses; backend tests exercise the
real HTTP adapters without contacting external model services. Screenshots use
synthetic bookmarks.

Independent review scored four interaction fixes resolved: mobile navigation focus,
draft/tested status, filtered empty-state copy, and related/session failure recovery.
Its `ship` disposition covered those fixes. The user subsequently requested stronger
visual design; that earlier verdict does not certify the new visual revision.

Run `37204513115` on `cfb8d26` passed backend/build/distribution/Docker/extension checks
but failed one of eight browser tests: the import button locator matched both
navigation and a briefly visible initial empty-state action. Revision `de661c0`
scopes the locator to navigation and distinguishes initial loading from an empty
library. It also replaces the visual treatment with graphite navigation, an inset
paper workspace, larger reading typography and segmented preview tabs.

The revised UI passed [experience run 37258068972](https://github.com/88lin/facetmark/actions/runs/37258068972)
and [desktop run 37258068939](https://github.com/88lin/facetmark/actions/runs/37258068939)
on `de661c0`: 1882 Python tests / 1 skipped, eight Playwright tests, 22 valid Web
captures (including 1440/1280/1024/390 widths), and the installed React setup with
same-version reinstall, uninstall retention and parent cleanup. The user rejected
that visual treatment despite these functional passes.

The user explicitly selected a bright, precise direction inspired by Linear's
visual order. Commit `08c0b2e` removes the graphite frame and repeated rounded rows,
lightens navigation, compacts search controls and gives article text more space.
Its Web, Windows and CI runs later passed, but the user still requested the
substantial redesign documented above. Neither this historical pass nor the
older interaction review certifies the current visual revision.

PR [#44](https://github.com/88lin/facetmark/pull/44) also runs the complete CI matrix.
Its first run exposed a workflow mismatch: `uv build --wheel` produced only a wheel,
while `check_web_bundle.py` requires both wheel and sdist. Commit `372abaf` changes
the job to `uv build`. [CI run 37260520353](https://github.com/88lin/facetmark/actions/runs/37260520353)
then passed all ten jobs, including Python 3.10/3.12 on Linux/Windows, MCP stdio,
browser behavior, both distributions, extensions, integration contracts and Docker.

## Provider and data safety

Focused Python tests cover separate endpoints and credentials, measured embedding
dimensions, save/test/apply/index/search, explicit consent, backup/rebuild, session
scope, same-dimension cross-endpoint rejection in direct vector stages, and
interrupted tasks. These checks do not establish the reliability or output quality
of a user's chosen model service. Original personal browser profiles are not used.

## Verified Windows installation baseline

[Desktop run 37204513032](https://github.com/88lin/facetmark/actions/runs/37204513032)
completed successfully on `cfb8d26`. The small `desktop-install-evidence` artifact
was downloaded and inspected, including the actual installed-window screenshot.

- `frozen-service.json`: frozen=true; no Python on child PATH; port collision,
  Unicode path, static assets, keyword search, authenticated identity, per-data-directory
  single instance, graceful shutdown and data retention all passed.
- `installed-webview.json`: actual installed Tauri WebView, React root and setup
  flow rendered at the local service URL with a synthetic empty library.
- `installed-workbench.png`: shows the new React import setup in the installed app,
  before the later visual refinement.
- `lifecycle.json`: backend stopped with parent; same-version reinstall succeeded;
  uninstall retained data. The test uses one synthetic bookmark.
- The NSIS preview contains the frozen Python service and offline WebView2 installer.
  Only small evidence was retrieved locally; the installer was not downloaded.

Earlier CDP attachment failures were fixed by forwarding the arguments through the
Tauri WebView builder. Inspection arguments require all three hosted-CI switches:
`GITHUB_ACTIONS=true`, `RUNNER_ENVIRONMENT=github-hosted`,
`FACETMARK_CI_WEBVIEW_INSPECT=1`. A previous graceful-exit timeout led to stdout/stderr
drain and diagnostics improvements; subsequent runs passed, without claiming a
universally proven root cause for that earlier timeout.

## Remaining validation boundaries

- Hosted Windows Server is not coverage of Windows 10/11 user machines.
- Program-specific firewall rules do not prove physical whole-machine disconnection.
- Same-version repair is not cross-version upgrade coverage.
- The runner account does not prove ordinary non-administrator behavior.
- Preview binaries are unsigned; no SmartScreen or signing-trust claim is made.
- Actual external model services and original personal browser profiles are not used.
- Artifacts expire after 14 days; rerun the workflow when needed.
