# Facetmark — current redesign requirements

## Status — 2026-10-19

The user explicitly said: **“现在这种图标布局样式颜色等都不要。”**
The current visual system is rejected in full. This supersedes earlier partial
acceptance of the animated Orbit folder. No existing icon, mark treatment, palette,
font choice, sidebar arrangement, card grid or material is a retained visual requirement.

The user has authorized a whole-interface redesign and correction of the rules
that kept reintroducing the old result. This is sufficient to proceed with design
and implementation choices. Do not ask again whether to rebuild, restart a
preference interview or require a random concept tournament. Working choices can
be made and shown as concrete results; only the user can confer aesthetic approval.

## What the replacement must accomplish

Replace the composition, icon language, typography, colour, material and motion
as a coherent interface. Changing the accent, radius or a single animated icon on
the existing arrangement does not satisfy this request. Design a complete working
first viewport with its navigation, collection content and core actions before
extending that direction to settings, tasks and reading.

HeroUI, GithubStarsManager and FlClash remain references for quality, organization
and interaction. They do not prescribe a palette, exact layout, mandatory library
migration or an approved Facetmark design. The latest instruction removes the old
capsule implementation and bundled font choices as visual mandates; readability,
clear affordances and responsive operation remain required.

Use depth, light, texture, rounded forms and expressive animation where the new
direction benefits from them. Do not suppress them just because the surface is a
working application. Keep state and controls immediate, animations interruptible,
and reduced-motion alternatives useful. No universal radius range, neutral-shell
requirement or one-effect quota applies.

## Preserve behavior while replacing appearance

Preserve search/IME, server paging, exact folder selection, model discovery →
choice → test → save → execution, durable task snapshots/recovery, processing
consent, original links, keyboard focus, form behavior and read-only imports.
Icon artwork can change; the actual action and accessible name must remain clear.
The frontend surface brief specifies the main regression boundaries.

Replace obsolete CSS as each component migrates. Assign each style and animated
property a clear owner. Avoid blanket control selectors, document-wide press
effects and compatibility layers that obscure native behavior. A visual redesign
does not justify regression in an unrelated flow.

## Evidence and delivery

Use current source-matched cloud renders and interaction recordings with synthetic
data. Inspect the whole screen at desktop, short-window, narrow/mobile and light/dark
sizes. Verify relevant user journeys, not only screenshots of isolated components.
Tests establish technical behavior; image hashes establish provenance. Neither
establishes aesthetic approval. Report actual review scope and unresolved issues.

Local work remains limited to edits, lightweight static checks and small evidence
inspection. Build, browser, dependency installation, packaging and installed-app
checks run in GitHub Actions. Preserve personal data and real browser profiles.
No main merge, formal release or deployment is newly authorized by this brief.

## Design records

[DESIGN.md](../DESIGN.md) and [design.json](design.json) explicitly mark the
replacement as pending; they contain no inherited tokens or component specimens.
Record a concrete working direction when implementation begins, then document the
actual implemented system and evidence. Do not invent a completed replacement now.
The [rejected archive](history/2026-10-19-rejected-ui/README.md) is migration evidence
only and should not be loaded as the new design's starting specification.

## Current proposal

The user asked to start the planned complete main-interface proposal. Continue the
[workbench prototype](surfaces/workbench-prototype.md): top navigation, broad collection
canvas, teal actions, softly coloured collection destinations and on-demand directory.
This is a concrete working proposal for review, not aesthetic acceptance. The standalone
prototype does not yet migrate production settings, tasks or collection workflows.
