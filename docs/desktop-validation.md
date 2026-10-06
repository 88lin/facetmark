# Desktop experience validation

Updated 2026-10-05. Branch: `desktop/facetmark-experience`.
This is an unsigned test-branch delivery. No main merge, production deployment or
formal release is part of this work. All browsers, installers, large downloads
and packaging run in GitHub Actions.

## Current redesign: rendered UI `d618c52`

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
