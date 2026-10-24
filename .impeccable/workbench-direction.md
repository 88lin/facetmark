# Facetmark — current workspace refinement

## Latest feedback — 2026-10-24

Latest user assessment: “还不算好看，能用的样子而已”. The current overall appearance
needs further visual refinement. Earlier acknowledgement of progress is historical;
it does not approve or freeze the current composition, typography, palette or material.
The user requests fixes to capsule geometry, black click
states, animation continuity, nested folders, folder artwork and unfinished
startup surfaces. No new refinement is marked user-approved before review.
PR #44 is merged under explicit user authorization. The new follow-up fixes
workspace height, full-width settings, reader typography, blank-card preview,
header search, native startup and the tray menu. Commit/push and cloud verification
are authorized for a new PR; do not auto-merge it or publish a release.
New issue #52 covers retry while a failed sidecar is still exiting; its gate and
immediate installed retry regression are part of PR #51. The installed icon
has pixel-matched technical evidence, with no individual visual approval.

The user requires the long-term handbook to contain only general methods and
reference research. All project directions, implementation, screenshots, bugs,
runs, commits and user assessments belong exclusively in this repository.
[Project reference/feedback record](../docs/design-reference-project-record.md)
contains the migrated project material and latest review.

## Visual and interaction direction

Impeccable owns one system. Use the supplied startup prompt and handbook, including
P04 navigation context, P08 icon/behavior separation, P15 interrupted motion and
P16 ownership. oil-ui and Taste are selected methods; S17-S20 remain source-backed
references. Do not restart a direction tournament or restore a rejected skin.

The following describes the current implementation, not an approved visual identity.
Blue carries action and selection; ink carries text. Top navigation uses a blue
plate, while category/settings segments use porcelain and blue material. Capsules
fill their assigned grid space. Their moving plates animate actual dimensions
and position; the button's text and hit area remain stationary. Local highlights,
folder layers and existing card/reader depth must remain coherent across themes.

Preserve high-frequency input. Transitions resume from the current painted state,
closing branches immediately become inert and reduced motion keeps usable endpoints.
Folder disclosure has its own arrow; selecting a folder retains the exact stored
path. Keep long labels readable, ancestors visible and complete paths available.
Use existing import depth to reconstruct `/` paths; preserve literal slash names
and ambiguous legacy paths as complete identities. Bound directory labels to two
lines and provide full-path disclosure, so long names retain readable capsule rows.

Carry the identity through the native splash, React boot, pairing, import and setup.
Keep retry beside failure, preserve drafts on return and show completion from real
setup facts. Do not let late responses overwrite current state or duplicate actions.

## Current layout and native follow-up

Use one 64px desktop header, with search above the collection. The fixed directory
spans both rows; remove the brand/title blocks from the collection header and
duplicate folder labels. Keep 280px minimum cards and compact 16px padding, while
preserving varied synthetic titles/summaries and visible record operations.
The reading index keeps source, title, status and actions, with room for consecutive
preview switching. Its selected card owns full-row visibility after layout motion;
closing restores collection scroll and the real opener's focus. Article body is
17px/1.8 (16px mobile); titles are 29px (25px
mobile, 32px focus). Progress is a 48px in-flow footer only on saved body text.

Settings span the available page. Heading/return share a row; four mobile tabs use
compact labels, full accessible names and complete capsule widths. Tabs retain
internal focus padding; model/folder
menus use native manual popovers, escape scroll clipping, clamp to the viewport,
flip above the anchor when needed and become inert during exit. Keep form/focus
ancestry, IME, drafts and keyboard behavior.

A shared folded-F SVG and offline font faces connect React, native startup and
the packaged tray window. Tray actions read real native plugin state; toggles are
single-flight, errors preserve the previous state, and Escape/focus loss dismiss
the menu. “Check updates” opens the desktop/update settings tab. Native tray
commands are restricted to the packaged tray page, with physical monitor-aware
placement. Cloud synthetic opening is identified separately from a real right-click.

## Product and implementation boundaries

Preserve search/IME, server paging, exact folder selection, cross-page management
and summary scopes, original links, native form/keyboard behavior, model discovery
→ choice → test → save → execution, durable task recovery and processing consent.
Use isolated synthetic content with long Chinese titles, mixed text and varied summaries.

Assign styles and animated properties to their component owners. Remove superseded
rules rather than layering global overrides. A control-library default cannot
choose application state colors or break focus, Enter/Space or form behavior.

## Evidence and records

Local work is limited to source edits, lightweight static checks and small evidence
inspection. Builds, browsers, package installation, packaging and installed-app
checks run in GitHub Actions. Do not access real browser profiles. This brief does
not add commit, push, merge or release authorization.

Inspect the current full screen, short windows, narrow layouts, both themes,
Chinese/English, relevant actions, failure recovery and intermediate motion in the
allowed environment. Native splash HTML with a synthetic bridge is distinct from
installed Windows evidence. Old green checks do not verify the current source.

[Current follow-up](../docs/workspace-layout-2026-10-24.md),
[DESIGN.md](../DESIGN.md), [sidecar](design.json) and
[frontend brief](surfaces/frontend.md) describe the same revision and review state.
The repository handbook is a snapshot of general master v0.18. Update project
feedback and implementation in separate repository files; do not write them back
to the long-term master.
Rejected pale-iris, limestone, pale-green and Orbit-era treatments remain historical
migration references only. The latest feedback controls the next iteration.
