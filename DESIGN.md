# Facetmark workbench

The user-confirmed direction replaces the legacy sketch interface. Mode: Operate.
This implementation is code-led; no generated mock is its visual authority.

## First viewport and interaction

A 216 px navigation rail, a flexible search/result column and a 36% reading pane.
The search field is fixed above a compact, ruled list. Results use a clear title,
two-line excerpt and quiet domain/folder metadata. Selecting a result reveals
its text beside the list while preserving query, filters, pagination and scroll.
The distinctive interaction is reading through a collection without leaving it.
Below 1120 px, preview becomes an accessible drawer; below 720 px navigation
collapses into a compact toolbar with the filter controls still available.

## Tokens

Light: canvas #ffffff, rail #f5f5f7, inset #f8f8fa, text #242429,
secondary #65656f, rule #dedee5, accent #6541c7, accent soft #eee8fb.
Dark: canvas #202024, rail #19191d, inset #29292f, text #f1f1f4,
secondary #b1b1bc, rule #42424b, accent #b79cf5, accent soft #352b4c.
Danger: #a4293b / #ffacb8. Primary button ink is white / #20172f.

Typography: local system UI, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif.
Body 14 px / 1.6; results 15 px / 1.5; reading 15 px / 1.9, maximum 72 ch.
Page heading 26 px, section heading 18 px. Tabular numbers for counts.
Spacing: 4, 8, 12, 16, 24, 32 px. Controls 8 px radius; panels 12 px.
Lucide outline icons at 18 px, stroke 1.7. Decoration never competes with text.

## States and motion

Purple denotes selection, primary actions and keyboard focus. Busy tasks use
indeterminate activity and named stages, never an estimated percentage.
Errors remain next to their recovery action. Empty library, no matches, missing
body and unconfigured models have different copy. Drawer enters in 160 ms;
reduced-motion removes it. Selection, caret and scrollbars use the same tokens.

## Verification

CI exercises both languages/themes, mobile and desktop, import, independent
connection probes, setup consent, paging, IME composition, stale responses and
keyboard focus. Screenshots use only synthetic demo data. No browser or desktop
installer is launched on the developer's machine.
