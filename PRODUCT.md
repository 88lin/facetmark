# Facetmark

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Tauri 2 desktop shell, Python sidecar, React + TypeScript + Vite + Tailwind CSS,
HeroUI/React Aria controls, Radix dialog primitives, Motion/GSAP and Lucide icons. One interface ships in the desktop installer,
Python distribution and Docker image.

## Users and Purpose

People retrieving and maintaining their own bookmark collections, including large
Chinese libraries. Find a remembered page, open the original website, read a useful
summary or excerpt, and process a chosen part of the collection without losing context.
Saved-page preview is a secondary inspection tool.

## Operating Context

Windows 10/11 x64 is the first desktop target. Browser exports are imported read-only;
local source discovery requires an explicit action and source selection. Keyword
search and organization work without AI.

Summaries may use an installed Codex, Claude Code or OpenCode client with its existing
sign-in, or an OpenAI-compatible endpoint. Agent detection, model discovery, model
selection, successful testing, saving and actual summary use are distinct steps.
An installed client or a returned catalog does not establish account access. Chat
and optional embeddings can use different services. Existing loopback services can
be explicitly configured without a key. Mock providers are restricted to demo/test use.

## Capabilities and Constraints

Import → search and organize → choose and test a summary connection → review scope
and processing consent → generate and inspect summaries → recover the exact failed
or unfinished task entries. The selected model must remain consistent across
discovery, test, save and execution; model changes require a fresh connection test.

The collection supports manual create/edit, tags and folders, confirmed deletion,
JSON/HTML export, direct original links and independent page-fetch or summary tasks.
JSON exports retain saved reading data; reimport restores bookmark metadata.
Cross-page summary selection and server-scoped tasks support large libraries without
sending every target ID from the browser. Management and export retain their own
explicit selection or collection scopes.

A saved task retains its target snapshot. Resume or retry reuses that snapshot,
keeps completed entries and retries failed or unfinished entries. It must not expand
to unrelated failures elsewhere in the library. Tasks survive navigation and
distinguish running, pausing, paused, interrupted, partial, failed, cancelled and done.

Shared-folder sync exchanges metadata through a user-owned folder with preview,
conflict choices and a local backup before incoming changes. Automatic sync requires
an initial reviewed apply and pauses for conflicts. Content processing requires
consent describing the titles, URLs and extracted content sent to the configured
service. Vector-space changes require backup and explicit rebuild.

Never modify the original browser profile or library. Desktop packaging, large
downloads, builds, browser execution and installation tests run in GitHub Actions.
No automatic main merge or production release. Existing CLI and integration
contracts remain.

## Brand Commitments

On 2026-10-24 the user described PR #44's mist-blue workspace as a substantial
improvement and asked for comprehensive refinement. Keep the current composition,
upright Inter / Noto Sans SC typography and layered material direction while
improving the full arrival and operation path. This is permission to refine the
incumbent identity; it does not approve every token, component or new change.

Capsule controls, rich material and continuous, interruptible motion remain
explicit requirements. Fix elliptical selected states, black control fills,
unsteady click transitions, inaccessible nested folders and unfinished startup,
pairing and setup surfaces. Preserve stable hit areas, native controls, readable
Chinese/English, exact data scopes and high-frequency operation.

The supplied startup prompt and long-term design handbook govern the reference
method. Impeccable owns one working system; oil-ui and Taste provide selected
methods rather than competing skins or complete review workflows. S17-S20 remain
permitted references for improvement, without making their components Facetmark
requirements. Current handbook version and feedback are recorded in the
[current round](docs/collection-workspace-polish-2026-10-24.md).

Earlier pale-iris 46cf2f3, limestone/orange, pale-green and Orbit-era designs were
rejected. They remain migration evidence in `.impeccable/history/` and historical
round records. The latest positive assessment of the mist-blue version takes
precedence; do not restart a whole-direction redesign or preference interview.

The [active work requirements](.impeccable/workbench-direction.md) and
[frontend surface brief](.impeccable/surfaces/frontend.md) describe this refinement.
DESIGN.md and its sidecar describe actual source values and verification status.
Current local edits await source-matched cloud rendering and user review. Older
cloud checks establish their recorded revision and scope only.

## Evidence on Hand

On 2026-10-17 the user rejected the incomplete model-selection journey and repeated
isolated patches. Continue the comprehensive detection → model choice → test/save →
summary → recovery workflow while replacing the rejected appearance, without
another preference interview. The user has not approved the current aesthetics.

Current source-matched verification and the visual review disposition are recorded once in
[desktop validation](docs/desktop-validation.md). Historical green runs and scoped
review verdicts establish only their recorded revision and scope; they do not
accept the current implementation. Synthetic corpus, catalog and model fixtures
must be identified as such. Never show personal bookmarks in evidence.
Hosted Windows Server installation smoke is not Windows 10/11 certification.

## Product Principles

- Keep original access and collection operations direct.
- Preserve search and task context across navigation.
- Separate discovered, configured, tested, saved, indexed and applied states.
- Put the relevant failure and recovery beside the operation that produced it.
- Ship usable offline assets; end users do not need Node.

## Accessibility & Inclusion

Chinese and English, light and dark, local Chinese font fallbacks, readable weights,
keyboard search and model selection, reduced motion, narrow-window preview and mobile Web.
