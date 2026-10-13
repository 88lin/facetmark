# Facetmark

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Tauri 2 desktop shell, Python sidecar, React + TypeScript + Vite + Tailwind CSS,
Radix primitives and Lucide icons. One interface is shipped in the desktop
installer, Python distribution and Docker image.

## Users and Purpose

People retrieving pages from their own bookmark collections, including Chinese
libraries. Find a remembered page, inspect its content, and recover the context
of a saving session without losing the result list.

## Operating Context

Windows 10/11 x64 is the first desktop target. Browser exports are imported
read-only; discovery requires an explicit user action and selecting a source.
Chat and embeddings may use different OpenAI-compatible services. Existing
loopback services can be explicitly configured without a key. Keyword search
works without AI. Mock providers are restricted to explicit demo/test operation.

## Capabilities and Constraints

Import → search and organize. Configure and independently test AI channels when
needed, then confirm summary processing or optional semantic indexing.
The collection also supports manual create/edit, tags and folder organization,
confirmed deletion and bulk actions, JSON/HTML export, and independent page-fetch
or chat-only summary tasks. JSON keeps saved reading data; reimport restores
bookmark metadata. Shared-folder sync exchanges metadata through a user-owned
folder with preview, conflict selection and local backup before incoming changes.
Automatic sync requires an initial reviewed apply and pauses for conflicts.
Cloud processing requires consent describing the titles, URLs and extracted
content sent to the configured services. Vector-space changes require backup
and explicit rebuild. Tasks survive navigation and report interruptions.
Never modify the original browser profile or library. All desktop packaging,
large downloads and installation tests run in GitHub Actions. No automatic
main merge or production release. Existing CLI and integration contracts remain.

## Brand Commitments

Independent Facetmark identity. The user explicitly chose pure white and lake blue
with clear rounded panels and refined controls on 2026-10-06, superseding the
rejected flat grey-violet treatment. Keep the recognizable layered brand mark.
The user rejected the permanent three-column management layout on 2026-10-06.
On 2026-10-09 they rejected the oversized collection masthead and mouse-inaccessible
horizontal categories, and explicitly supplied GithubStarsManager as an interface
reference. This supersedes the earlier engineering-only reference restriction.
Use compact controls and searchable, vertically scrollable categories for large
libraries. Categories sit beside browsing and yield to the reader when a page opens;
do not permanently divide reading into three columns. No hand-drawn borders or
candy-colored dashboards.

On 2026-10-10 the user rejected the resulting type as too small and thin and asked
for further visual and functional refinement without more preference questions.
Keep the useful browsing area while improving text size, weight and hierarchy.
Card/list switching must not shrink titles; category names and routine controls
must be comfortably readable. Carry the user's current category into collection
actions, make active filters explicit, and support efficient navigation in large libraries.

## Evidence on Hand

On 2026-10-11 the user rejected the current result as unusable for a 200,000-bookmark
library. A bookmark title must open its original website directly; saved reading is
an explicit secondary action. Summaries must be visible, expandable and filterable
in the collection, with obvious scoped bulk processing and failed-item retry.
Adopt the concrete collection workflows in GithubStarsManager rather than treating
it as a cosmetic reference. Detect and use installed local coding agents following
open-design's runtime-adapter approach, without requiring duplicated chat API setup.
Keep custom API connections available and fix their actual test/save/use path.
Large-library validation must exercise 200,000 synthetic records, bounded requests
and bounded processing concurrency. Earlier visual ship verdicts do not accept this
rejected interaction model. Do not ask the user to supply another preference list.

On 2026-10-13 the user rejected the current PR #44 experience across its surfaces
and twice requested continued refinement. Preserve the white/lake-blue identity,
readable titles, direct original links and secondary preview. Settings must expose
AI connections, sync, extension and desktop updates without losing unsaved drafts
when switching categories. Keep sorting visible, offer direct bookmark editing,
and distinguish task idleness, failure, cancellation, pause and saved-task recovery.
Only running tasks may claim to continue in the background. Current progress,
Pause/Resume/Cancel and current errors take priority over starting new work; the
mobile saved-task Resume action must be fully visible in the first viewport.
Import should validate exports, allow retrying the same file and return directly
to the imported collection. At source `5ea56ab86e4822c1114f9288fbbaebadd5aeea1c`,
[Experience 38395130633](https://github.com/88lin/facetmark/actions/runs/38395130633) passed 51 ordinary browser tests, the independent
200,000-record browser test and 2021 Python tests with 1 skip. All 72 captured PNG
hashes and the source/run manifest match the current visual artifact. The final
mobile paused-task capture and assertions confirm saved-progress wording and a
fully visible Resume action before new-work shortcuts. CI 38395139361 passed all
10 jobs. The follow-up marked both P2 findings resolved with no remaining findings
in its scope and disposition ship; it covers task-state truthfulness and recovery
placement/mobile visibility, not full-product aesthetic acceptance or real-model
success. [Windows 38395130294](https://github.com/88lin/facetmark/actions/runs/38395130294) passed all jobs at the same source. Installed-desktop
evidence confirms the original link opened in Edge without page errors, Preview
return preserved the query, runtime installation and backend readiness worked,
and reinstall, data-preserving uninstall and parent-exit cleanup passed. The
installer is unsigned; hosted Windows Server evidence does not certify every
Windows 10/11 environment. Historical passes remain evidence only for their
recorded revisions.

Synthetic demo corpus in the repository. CI captures must identify demo data.
Installer smoke on hosted Windows Server is not Windows 10/11 certification.
Real user bookmarks must never appear in presentation captures.

## Product Principles

- Keep search context while inspecting a page.
- Separate configured, tested, indexed and applied states.
- Make failure and recovery visible without inventing progress.
- Ship usable offline assets; end users do not need Node.

## Accessibility & Inclusion

Chinese and English, light and dark, local Chinese font stacks, keyboard search
and selection, reduced motion, narrow-window preview drawer and mobile Web.
