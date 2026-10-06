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
Cloud processing requires consent describing the titles, URLs and extracted
content sent to the configured services. Vector-space changes require backup
and explicit rebuild. Tasks survive navigation and report interruptions.
Never modify the original browser profile or library. All desktop packaging,
large downloads and installation tests run in GitHub Actions. No automatic
main merge or production release. Existing CLI and integration contracts remain.

## Brand Commitments

Independent Facetmark identity. Paper white and graphite with purple accents.
The user rejected the permanent three-column management layout on 2026-10-06:
collection content and reading must lead, with navigation and filters secondary.
GithubStarsManager is engineering background only,
not a visual reference. No hand-drawn borders or candy-colored dashboards.

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
