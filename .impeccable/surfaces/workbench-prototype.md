---
version: 1
slug: workbench-prototype
primary_target: frontend/design/workbench
related_targets:
- scripts/design_preview.py
---

# Facetmark collection prototype

Status: REJECTED by the user during the current 2026-10-19 session ("你这个更加难看了").
The user requires source-level analysis of this project and reference implementations.
The direction below is rejected-prototype history, not authority for the next design.
See docs/redesign-source-audit.md. This prototype remains outside the application.
The user asked to begin the planned complete main-interface proposal on 2026-10-19.
This surface uses six synthetic bookmarks and existing field semantics. It does not
change a database, call an AI service, or claim working model settings or task execution.

## Direction contract

THESIS: A personal collection with a broad, content-first desktop canvas and a
searchable directory that opens when needed. Navigation and actions form a compact
top edge; the user can scan useful saved content without a permanent sidebar.

OWN-WORLD: Mineral white and graphite with deep teal actions, translucent turquoise,
apricot and blue collection tabs, crisp two-tone vector emblems, layered surfaces,
soft directional shadows and individually shaped controls. Chinese text leads.

STORY: Find a collection, scan title and truthful summary provenance, open the
original or enter reading, then return to the same item. Explicit selection exposes
bulk actions. Synthetic values are disclosed in the preview.

FIRST VIEWPORT: Horizontal product navigation, large collection title and search,
four small collection destinations, then a single toolbar above a three-column
collection at 1440px. Each bookmark has a large site monogram, title, excerpt and
quiet persistent reading action. Mobile has a two-column collection strip and
one-column content with usable search and no permanent directory pane.

FORM: Direct route from the user's latest brief and the proposed 2026-10-19 plan;
seed: none (not run). Code-led interactive prototype, cloud-rendered screenshots.
There is no approved image comp. Existing rejected images are migration evidence only.

FINISH: Deliver inspected desktop light/dark, narrow-screen and reading/directory/
selection state renders plus a real interaction recording. Record implementation
and validation limits honestly; this prototype does not complete application migration.

## Interaction and evidence boundaries

Use native links, checkboxes, buttons and dialogs. Preserve separate original-link
and preview actions. Search, local folder/status filters, selection, view switching,
theme switching and reader navigation work on the fixture. Mutation and processing
dialogs say when they only demonstrate an interface and cannot change saved data.
Do not invent thumbnails, favicon retrieval, browser history, pinning or read state.

Cloud-only Playwright runs with synthetic content, a temporary server, isolated
browser contexts, external network blocking and source-hash provenance. No local
browser, package installation or build. Record both UI quality findings and the
limited functional scope; green checks do not imply aesthetic acceptance.
