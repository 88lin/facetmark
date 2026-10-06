# Desktop experience validation

## 2026-10-06: white and lake-blue confirmation (current)

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
