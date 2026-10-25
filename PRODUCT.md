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

Import → search and organize → choose, test and save a summary connection → select
bookmarks or use the current scope → generate titles, summaries and key points → recover the exact failed
or unfinished task entries. The selected model must remain consistent across
discovery, test, save and execution; model or thinking-setting changes require a fresh
connection test. An empty thinking choice inherits the service or client default;
detected agents expose available model effort levels or variants and known defaults.

The collection supports manual create/edit, tags and folders, confirmed deletion,
JSON/HTML export, direct original links and independent page-fetch or summary tasks.
Version 2 full JSON restores missing saved reading content and conversations as well
as bookmark metadata; existing local content takes precedence. Keys, vectors,
browser state, configuration and task logs are excluded from portable JSON.
Cross-page summary selection and server-scoped tasks support large libraries without
sending every target ID from the browser. Management and export retain their own
explicit selection or collection scopes.

Durable AI chat covers the collection, one saved page or 1–12 selected pages. Sources
are verified and linked; replies continue across navigation and support Stop, retry
and regeneration while retaining earlier complete answers. MCP offers the existing
stdio tools and an optional desktop HTTP connection with a separate token and real
protocol self-check. Search, read and save capabilities are distinct.

Processing settings expose actual concurrency, per-host spacing, total HTTP attempts
and a shared endpoint/account minute budget. Same-process Agent calls share a quota
across summary/chat providers; independent processes are not globally limited.
The desktop also exposes the original site crawler as a bounded background import,
a saving timeline and link-health maintenance. Python local SentenceTransformer
support is optional; the frozen desktop reports its absence and offers a tested
HTTP embedding endpoint instead.

The directory groups by folders and tags. Site identity remains record metadata,
without a separate site category. One select-all checkbox and Generate button occupy
the existing toolbar; selecting records does not introduce another row. Explicit
selections regenerate completed records; without a selection, Generate handles
eligible pending, failed or changed records in the current scope.

AI titles are stored separately from original bookmark titles and used for display
and search. A single reading panel presents the overview and key points before saved
source text. Target language follows the UI by default, with explicit Chinese/English
choices. Built-in writing instructions can be edited and restored; saving these
preferences does not require another connection test. Language or instruction
changes make old summaries eligible for regeneration. Failed generation preserves
previous derived content and the original title and source text.

A saved task retains its target snapshot. Resume or retry reuses that snapshot,
keeps completed entries and retries failed or unfinished entries. It must not expand
to unrelated failures elsewhere in the library; it retains its original language and
writing instructions. Tasks survive navigation and
distinguish running, pausing, paused, interrupted, partial, failed, cancelled and done.

Shared-folder sync exchanges metadata through a user-owned folder with preview,
conflict choices and a local backup before incoming changes. Automatic sync requires
an initial reviewed apply and pauses for conflicts. Choosing Generate authorizes
sending the selected metadata and saved text to the tested chat connection; do not
repeat that action with a consent or reprocessing checkbox. Connection settings
describe what is sent. Vector-space changes require backup and explicit rebuild.

Never modify the original browser profile or library. Desktop packaging, large
downloads, builds, browser execution and installation tests run in GitHub Actions.
No automatic main merge or production release. Existing CLI and integration
contracts remain.

## Brand Commitments

The overall 2026-10-24 assessment is “还不算好看，能用的样子而已”. On 2026-10-25
the user requested simpler collection/reading/summary workflows and removal of the
tray's transparent outer frame while preserving its interior.
The user acknowledged earlier progress, then requested comprehensive improvement
and specific space/typography repairs. The mist-blue implementation is a working
baseline; its composition, fonts, color and material are open to refinement.
No current identity, new icon or individual detail is marked user-approved.

Capsule controls, refined material and continuous, interruptible motion remain
explicit requirements. Give the collection and folder tree most of the window.
Search belongs in the shared header; eliminate duplicate collection headings.
Settings use the available workspace width and must not clip selected controls
or menus. Saved-text preview has a quieter body scale and a distinct title scale.
Blank record areas may open preview, preserving original links, text selection,
check boxes and independent actions. Reading progress exists only for saved body
text and must not obscure the final paragraph. Startup and the real tray menu
share the application's folded-F mark, font assets and state colors.
The tray's opaque surface fills its client viewport; alpha is reserved for rounded
corners, with no padded transparent surround or native window shadow.

Impeccable owns a single system. The supplied startup prompt and general handbook
v0.18 govern reference methods; oil-ui, Taste and S17-S20 supply selected,
source-checked relationships. Earlier pale-iris 46cf2f3, limestone/orange,
pale-green and Orbit-era appearances remain rejected migration evidence.
The active work requirements and frontend surface brief follow the latest feedback.

All product choices, implementation, screenshots, bugs, runs and user assessments
remain in this repository. Do not write project material to
`E:\design\design-reference-handbook.md` or its general snapshot.
PR #44 was merged with the user's authorization; this follow-up belongs in a new
PR. Commit, push and cloud validation follow current session authorization; this
document adds none. Do not automatically merge a new PR or publish a release.
Application/capture 8af69ae passed checks for the preceding layout/native revision.
The initial 1696889 cloud run found regressions. Application/capture 81f310a passed
CI, collection, experience and Windows installation checks for the completed feature
batch; exact evidence and limits are recorded in desktop-completion-2026-10-25.md.
The current aesthetics still await user review.
Older checks establish only their own revisions.

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
The initial source changes and current verification are recorded in
[the summary/reading follow-up](docs/summary-reading-reasoning-2026-10-25.md).
The broader suitability review and desktop completion are recorded in
[the current feature completion](docs/desktop-completion-2026-10-25.md).

## Product Principles

- Keep original access and collection operations direct.
- Preserve search and task context across navigation.
- Separate discovered, configured, tested, saved, indexed and applied states.
- Put the relevant failure and recovery beside the operation that produced it.
- Ship usable offline assets; end users do not need Node.

## Accessibility & Inclusion

Chinese and English, light and dark, local Chinese font fallbacks, readable weights,
keyboard search and model selection, reduced motion, narrow-window preview and mobile Web.
