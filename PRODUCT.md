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

Latest user instruction (2026-10-23): **“之前做了100轮都做的很难看，现在重新做吧”**。
The incumbent PR #44 collection screen is rejected again. Build one complete
collection workspace and its related states using the supplied startup prompt and
`E:\design\design-reference-handbook.md` (v0.11 at this round's start). Impeccable
owns the working system; S17–S20 are permitted references for improvement, not
approved Facetmark components. The earlier 2026-10-19 instruction remains relevant:
**“现在这种图标布局样式颜色等都不要。”**
The whole current visual system is rejected: icons and mark treatment, composition,
layout, styling, palette and typography are open for replacement. This supersedes
all earlier partial visual acceptance, including the Orbit folder glyph and the
old capsule/neutral/indigo implementation. No current visual asset or token is pinned.

The user has already delegated a whole-interface redesign and authorized correction
of conflicting rules. Do not restart a preference interview, ask whether to rebuild
again or make a random concept tournament a prerequisite. Establish a concrete
working direction, implement it and show actual results. Existing product behavior,
data protection, accessible controls and readable Chinese/English remain required.

Replace composition, icons, typography, colour, material and motion together.
Another accent swap, radius adjustment or isolated animated icon does not satisfy
the request. Rounded forms, depth, light, texture and expressive transitions are
available when they support the replacement direction and remain usable. The
Operate mode does not force a neutral shell, small radii or sparse effects.

HeroUI, GithubStarsManager and FlClash remain quality and interaction references,
not approved Facetmark mockups or compulsory component replacements. Preserve
library/license obligations for code that remains; choose visual treatments from
the current brief, not from dependency defaults.

The [current redesign requirements](.impeccable/workbench-direction.md) are the
active visual brief; the [frontend surface brief](.impeccable/surfaces/frontend.md)
records behavior and verification boundaries. DESIGN.md and its sidecar record the current
collection implementation and its actual validation status; the 2026-10-21 limestone/orange
direction is rejected, and its green cloud checks certify only that historical revision. Rejected specifications
are archived under `.impeccable/history/` for migration, not design authority.

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
