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

Import → configure two channels → test independently → confirm indexing → search.
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

## Evidence on Hand

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
