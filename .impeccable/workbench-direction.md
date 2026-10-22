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

## Latest feedback: prototype rejected

The 2026-10-19 teal collection prototype was also rejected: “你这个更加难看了”.
The user challenged repeated screenshot-led changes and asked to inspect code.
Its top navigation, pastel tiles, typography and card composition are not accepted
replacement requirements. Do not continue polishing or promote this proposal.
Read [the source audit](../docs/redesign-source-audit.md) before further implementation.
Reference implementations must be examined at known commits; cloud renders can
verify the resulting implementation, but cannot substitute for that source analysis.


## Current collection round — 2026-10-23

The user rejected the incumbent PR #44 screen and requested another whole-direction
replacement. The 2026-10-21 limestone/orange production collection is historical
implementation evidence, not a retained visual brief. Its d40471f checks do not
validate this round. No part of that direction was retained by the latest feedback.

The supplied startup prompt and design handbook govern the product and reference
method. The user has now rejected pale-iris revision 46cf2f3 across palette, fonts,
layout and styling. It is archived, not retained.

## Latest direction — capsule controls and expressive material

User: “按钮等这些要圆角胶囊，高级感的动画，动效，视觉效果拉满…全面的优化和细节打磨”.

Replace the composition with floating top capsule navigation, an independent frosted
directory and a layered collection worktable. Use mist-blue ambient light, porcelain
content, deep ink and electric-blue actions. Inter and Noto Sans SC replace slanted
display type; weight, proportion and spacing carry hierarchy. Capsules have molded
edges, specular hover sweeps and stable hit areas. Record cards have local pointer
light, source medallions and soft elevation.

Default to cards with an optional horizontal list. Preserve saved preferences, actual
content and original links/scopes. Reader transitions, tab highlights, folder opening,
layout rearrangement and spring dialogs form one interruptible motion language.
Reduced motion retains endpoints. This working implementation is not user-approved;
old green runs do not validate the replacement.
