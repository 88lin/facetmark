# Facetmark

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Tauri 2 desktop shell, Python sidecar, React + TypeScript + Vite + Tailwind CSS,
Radix primitives and Lucide icons. One interface ships in the desktop installer,
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

Preserve Facetmark's layered mark, compact navigation, rounded controls and
readable content. The user rejected a permanent three-column management layout,
oversized collection masthead, mouse-inaccessible categories, small/thin type and
reader-first workflow. Card and list views share readable title and description
hierarchy; searchable vertical categories support ordinary mouse use.

On 2026-10-18 the user rejected PR #44's loss of roundness, surface depth and
visual effects. A later explicit correction rejected Manrope and the lake-blue
palette and named GithubStarsManager and FlClash as optimization references.
This latest correction supersedes the earlier white/lake-blue commitment while
retaining rounded cards, capsule controls, soft shadows and purposeful motion.
On 2026-10-19 the user again rejected the palette, typography, layout and missing
everyday click transitions in the Windows installer, and explicitly requested a
whole-interface refactor using both references beyond their colors. The current
replacement uses a tonal Material navigation shell, an independently searchable
collection directory, bundled Inter and Noto Sans SC, and an interruptible shared
motion system for navigation, filtering, layouts, controls and overlays. This
supersedes the 2026-10-18 neutral/blue system; it is not aesthetic user approval.
Exact tokens belong in [DESIGN.md](DESIGN.md); composition
and interaction details belong in the [frontend surface brief](.impeccable/surfaces/frontend.md).

The reference projects inform compact, legible desktop controls and explicit
selection. Their source and images do not establish an approved Facetmark pixel
comp or acceptance of the current implementation. Do not introduce hand-drawn
borders or candy-colored dashboards.

## Evidence on Hand

On 2026-10-17 the user rejected the incomplete model-selection journey and repeated
isolated patches. Continue the comprehensive detection → model choice → test/save →
summary → recovery workflow within the established identity, without another
preference interview. The user has not approved the current aesthetics.

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
