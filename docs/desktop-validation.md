# Desktop experience validation

This is a test-branch delivery, not a signed release or a Windows 10/11 certification.
Branch: `desktop/facetmark-experience`. No main merge or production deployment is part
of this work. All browsers, installers, large downloads and packaging run in GitHub Actions.

## Verified Web baseline

[Experience run 37202035095](https://github.com/88lin/facetmark/actions/runs/37202035095)
passed on `302461a`: backend regression, TypeScript/Vite build, six Playwright behavior
tests, Chinese/English × light/dark × desktop/narrow captures, Python wheel resources,
extension build/tests and a running non-root Docker container with a read-only filesystem.

The browser tests cover real import persistence, paging, IME composition, stale responses,
separate model probes, explicit indexing consent, persistent tasks, query suggestions,
cited answers, and drawer focus restoration. Screenshot data is synthetic.

The subsequent review found four material interaction issues: mobile navigation focus,
draft/tested configuration status, filtered empty-state copy, and related/session request
failure recovery. Commit `3622848` addresses these and adds cloud assertions and captures.
The [complete follow-up run 37203068070](https://github.com/88lin/facetmark/actions/runs/37203068070)
passed: **1882 Python tests / 1 skipped**, **8 Playwright tests**, wheel and sdist resource
verification, Docker and extension checks. The independent reviewer scored all four
listed fixes resolved, with `disposition: ship` at that scope. This is a verdict on those
fixes, not an independent installer certification. Fourteen valid screenshots include
the language/theme/viewport matrix, model settings, and the five fix-state captures.

## Provider and data safety

Focused Python tests exercise real HTTP provider adapters with controlled HTTP responses,
without external model calls: separate endpoints and credentials, measured embedding
dimensions, save/test/apply/index/search, explicit consent, backup/rebuild, session scope,
same-dimension cross-endpoint rejection in direct vector stages, and interrupted tasks.
These checks do not establish the reliability or quality of a user's chosen model service.

## Windows installation evidence

The earlier run `37199345919` built the installer and passed frozen-service isolation;
the installed backend and WebView processes started, but CDP attachment failed. It is
not an installed React rendering pass. Run `37202035132` built the installer but failed
the frozen-service graceful-exit timeout. Shutdown diagnostics are added in `3622848`.

Run `37203068124` passed frozen-service isolation and graceful shutdown. Its runner
capture shows the installed Tauri app rendering the new React setup flow. The automatic
DOM gate still failed because the WebView process command line lacked the requested
CDP argument; waiting longer did not fix it. The next build passes that argument through
Tauri's supported WebView builder only under the explicit hosted-CI inspection switch.

The Windows workflow separates small `desktop-install-evidence` from the large
`facetmark-windows-x64-preview`. Review evidence can be retrieved without downloading
an installer to the developer's machine. A passing run must demonstrate installed
React content, retained synthetic data, same-version repair, uninstall retention and
backend cleanup, in addition to build success.

## Limits that remain after a passing smoke

- Hosted Windows Server is not coverage of Windows 10/11 user machines.
- Program-specific firewall rules do not prove physical whole-machine disconnection.
- Same-version repair is not cross-version upgrade coverage.
- The runner's account does not prove behavior under an ordinary non-administrator account.
- Preview binaries are unsigned; no SmartScreen or signing-trust claim is made.
- Actual external model services and original personal browser profiles are not used in CI.
- Artifacts expire after 14 days; rerun the workflow when needed.
