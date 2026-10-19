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

Latest user evidence (2026-10-19, after `bed41ee`): the user rejected the capsule
workspace screenshots as visually flat, monotonous and lifeless, explicitly saying
that changing the accent colour cannot fix the composition. The neutral surfaces
and repeated card treatment below are a superseded design, not an approved brand
commitment. The next direction must address material, light, content hierarchy and
spatial continuity together, with fresh visual studies before implementation.
Capsule controls, readable Chinese, direct folder selection, the referenced
products' quality bar and functional safety remain required. The user has already
delegated broad redesign choices; do not restart a preference interview.

The user subsequently rejected all three Prism Light / Spectrum Dark / Orbit
studies. Only Orbit's sculpted folder glyph may be retained, conditional on real
animation. This is not acceptance of Orbit's composition, palette, dock, cards or
reader. The folder component joins the real directory and picker; the whole
interface still needs a replacement direction and visual review. Do not expand
this component preference into approval of an entire material treatment.

Preserve Facetmark's layered mark, direct access to original pages, readable
Chinese/English content and tactile rounded controls. Card and list views share
a clear title/description hierarchy. Searchable categories remain usable with a
mouse, while preview stays an optional inspection tool.

On 2026-10-19 the user explicitly rejected the lavender surfaces, 10px controls,
typography and sparse motion of revision `082e36d`, after earlier rejections of
PR #44's visual direction. They required full capsule buttons, added HeroUI as a
concrete reference, requested the installed GSAP capabilities and authorized a
whole-interface rebuild. This instruction supersedes the earlier palette,
separate rail/directory composition and random concept seed.

The superseded implementation was a fluid capsule workspace: one sidebar combining
application navigation and searchable categories, a spacious neutral content
canvas, indigo accents, complete capsule controls, circular icon buttons and
proportionately rounded content panels. Inter and Noto Sans SC remain bundled.
HeroUI supplies real controls and their interaction states; GSAP composes
interruptible page and section motion. Keep focus, native button/link semantics,
search drafts and actual data state independent of decorative motion.

HeroUI leads component construction, GithubStarsManager informs collection
organization, and FlClash informs selection continuity and layered transitions.
These sources are references, not approved Facetmark mockups. Do not restore the
rejected lavender wash, compact rail beside a second category column, rigid
controls or undersized content typography. Fresh verification and independent
review are required; no current user aesthetic approval is recorded.

Exact baseline tokens belong in [DESIGN.md](DESIGN.md). Historical direction is in
[the workbench contract](.impeccable/workbench-direction.md); composition and
interaction acceptance belong in [the frontend surface brief](.impeccable/surfaces/frontend.md).

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
