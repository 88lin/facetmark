---
name: "Facetmark collection workspace"
description: "Implemented workspace with source-matched cloud evidence; the user assesses current appearance as usable but not good-looking. Visual quality requires further refinement. Project material stays in this repository."
colors:
  secondary-ink: "#526379"
  canvas: "#ffffff"
  desk: "#e9eff5"
  rail: "#f3f7fc"
  inset: "#edf3f9"
  ink: "#162b43"
  muted: "#62748a"
  rule: "#d9e3ef"
  accent: "#235fe5"
  accent-hover: "#164bc2"
  soft: "#e8f0ff"
  selected: "#deebff"
  selected-edge: "#8baef3"
  selection-neutral: "#e7eef7"
  glass: "#ffffffb3"
  glass-edge: "#ffffffd9"
  light: "#ffffff"
  ambient-blue: "#83b9fa50"
  ambient-mint: "#b6e4e748"
  on-accent: "#fff"
  danger: "#b73754"
  danger-soft: "#fff0f3"
  success: "#237564"
  success-soft: "#eaf5f1"
  warning: "#88651e"
  warning-soft: "#fff5dc"
  brand-detail: "#7ac5ff"
  scrim: "#172a4861"
  secondary-ink-dark: "#b7c8df"
  canvas-dark: "#152236"
  desk-dark: "#0c1420"
  rail-dark: "#152438"
  inset-dark: "#1c2e46"
  ink-dark: "#eff6ff"
  muted-dark: "#9dafc8"
  rule-dark: "#304561"
  accent-dark: "#92bcff"
  accent-hover-dark: "#b3d1ff"
  soft-dark: "#213c61"
  selected-dark: "#294b78"
  selected-edge-dark: "#688cbd"
  selection-neutral-dark: "#233a54"
  glass-dark: "#142237c9"
  glass-edge-dark: "#7195bf33"
  light-dark: "#cce2ff"
  ambient-blue-dark: "#2869b529"
  ambient-mint-dark: "#326c7930"
  on-accent-dark: "#10223d"
  danger-dark: "#ffa6bc"
  danger-soft-dark: "#412635"
  success-dark: "#9bd7c9"
  success-soft-dark: "#233c38"
  warning-dark: "#ebca8c"
  warning-soft-dark: "#3c3221"
  brand-detail-dark: "#89d9f9"
  scrim-dark: "#06070a99"
typography:
  display:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", sans-serif"
    fontSize: "2rem"
    fontWeight: 750
    lineHeight: 1.35
    letterSpacing: "0"
  title:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "1.125rem"
    fontWeight: 680
    lineHeight: 1.6
    letterSpacing: "0"
  body:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  summary:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.8
  control:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.5
  source:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.6
  tag:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
  reader-title:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "1.8125rem"
    fontWeight: 600
    lineHeight: 1.4
  reading:
    fontFamily: "\"Facetmark Latin\", \"Facetmark CJK\", \"Segoe UI\", \"Microsoft YaHei UI\", sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.8
rounded:
  control: "999px"
  pill: "999px"
  card: "22px"
  card-compact: "20px"
  directory: "24px"
  workspace: "28px"
  reader: "24px"
  dialog: "32px"
  tag: "7px"
  source-symbol: "11px"
  checkbox: "6px"
spacing:
  inline: "8px"
  group: "16px"
  card-gap: "12px"
  card: "16px"
  workspace: "20px"
  dialog: "30px"
  compact-card: "16px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "10px 20px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
    textColor: "{colors.on-accent}"
  add-bookmark:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
    height: "40px"
  button-secondary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "9px 18px"
    height: "44px"
  button-text:
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "5px 10px"
    height: "32px"
  search:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "8px 13px"
    height: "44px"
  form-input:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
    height: "44px"
  navigation-active:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.pill}"
    padding: "8px 13px"
    height: "38px"
  directory-entry:
    textColor: "{colors.secondary-ink}"
    rounded: "{rounded.pill}"
    padding: "9px"
    height: "44px"
  tag:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.secondary-ink}"
    typography: "{typography.tag}"
    rounded: "{rounded.tag}"
    padding: "3px 8px"
  bookmark-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "{spacing.card}"
---

# Design System: Facetmark collection workspace

## Current state

The implemented system uses mist-blue surroundings, porcelain content surfaces,
deep ink text, electric-blue actions and shaped capsule controls. It is a working
baseline. The user described it as usable but not good-looking and requested more
refinement. No current palette, typography, layout, icon or new detail is marked
user-approved.

This follow-up removes excess chrome, gives the directory and bookmarks more
height, corrects reading hierarchy and carries the shared folded-F mark into native
startup and the real tray menu. Current source awaits cloud evidence and user
review. PR #44 is merged; this round belongs in a new PR. The previous f1c67fe
verification is a historical baseline, not validation of these edits.

[Product facts](PRODUCT.md), [active direction](.impeccable/workbench-direction.md),
[surface brief](.impeccable/surfaces/frontend.md) and
[round record](docs/workspace-layout-2026-10-24.md) describe the same task.
General handbook v0.18 contains only methods and reference research. Project
choices, feedback, screenshots and evidence stay in this repository.

## Color and material

Frontmatter keys match the shipped theme variables, with a `-dark` suffix for
dark variants. Electric blue identifies actions and selection; deep ink carries
text. Porcelain is the opaque card/article surface. Mist desk, rail and inset
surfaces establish the surrounding layers. Glass and its light edge lift navigation,
directory, dialogs and the worktable. Semantic success/warning/danger pairs retain
their data meanings; they are not decorative source categories.

Depth uses offset soft shadows, inset highlights and local pointer light. The
navigation and directory use 18px and 24px blur respectively. The content itself
remains opaque. Card hover changes light and shadow without translating its hit
area. Pressed controls keep their semantic blue/porcelain material and stable bounds.

Selection, caret, focus, scrolling and tabular figures use the theme roles.
Forced colors retain system Highlight boundaries and native operation.

## Typography

Bundled variable Inter and Noto Sans SC use the `Facetmark Latin` and
`Facetmark CJK` aliases, with Segoe UI/Microsoft YaHei UI and sans-serif fallback.
The same offline font files are staged for native startup and tray packaging.
Smiley Sans is a historical asset, not the active interface font.

- Card titles: 18px/680, 1.6 line height, two lines; 17px on mobile.
- Card summaries: 15px/1.8, two lines; 14px on mobile. Measured overflow exposes
  expansion in a separate 8px-gapped column. Expanded text has no clamp.
- Source, status, tags and folder paths: 13px; dates and summary-basis captions: 11px.
- Reading index: 16px title, 28px source medallion and compact status/actions.
  Duplicate summaries, tags and folder paths are hidden in this context.
- Article title: 29px/700, 1.45 line height; 32px in focus mode and 25px mobile.
- Article body: 17px/1.8, 16px mobile; h2: 21px/700, h3: 19px/650.
  Mobile h2/h3 are 20px/18px. These reading roles use rem units.
- Shared controls: 15px/600; local navigation/actions retain their own smaller,
  source-defined type and hit areas.

The collection scope h1 remains available to assistive technology without a
duplicate visible display block. It is not a decorative heading above the results.

## Layout

Desktop shell: 64px header, 252px directory, 16px gap, 10px top and 16px side/bottom
padding. The directory spans both grid rows. Above the collection, the header
contains navigation, shared search and utilities; the repeated brand and title/search
band are removed. The directory's category controls share one row, the folders
entry uses its icon with an accessible name, and the tree scrolls independently.

The collection uses 12px top / 20px horizontal padding, a compact actions/status
area, a 280px-minimum grid with 12px gaps and a separate paging footer.
Card padding is 16px, internal gap 9px and radius 22px.
Grid is the unsaved default; list remains a persisted alternative.

At 1660px the directory/index are 280px/288px, shell sides 20px, workspace sides
24px and card minimum 320px. Below 1300px the directory/index are 232px/248px;
navigation/utility text compacts. Below 1120px reading uses the full-viewport,
focus-managed drawer. Below 960px the fixed directory and desktop navigation
become one drawer opened by the filter control beside search. Below 720px the
header is 56px and actions, status and display controls reflow into separate rows.
Very short narrow windows allow the whole worktable to scroll while maintaining a
160px result region. The directory remains independently bounded.

Settings use the whole available page width. At 1280px and above the chat and
embedding channels share two columns; a 1px divider separates them.
Four settings tabs fill a padded grid, using compact labels in one row on mobile.
Full accessible names remain. Heading and return action share a row. Focus is not
cropped by an overflow strip. Form fields, tasks, importer and desktop settings no
longer have page-wide centering caps. Reading text retains its measure cap.

## Controls and menus

Shared capsule buttons keep the HeroUI/native adapter for click, Enter/Space,
focus and form semantics. Their corners and hit areas remain stable during press.
Selected segment plates animate actual bounds over 340ms with GSAP `power3.out`;
they do not scale rounded geometry. Last-painted bounds are captured before
teardown reversion, including non-enumerable DOMRect getters.

ModelPicker and FolderPicker own their paint in `folder-picker.css`.
AnchoredMenu uses native manual popovers to escape scroll/animation clipping while
retaining DOM, form and focus ancestry. It measures visual viewport and scroll
ancestors, clamps horizontal bounds, flips vertically when needed and closes when
the anchor is hidden. Exit controls become inert immediately; the top layer is
released after the overlay exit. Engines without popovers use an inline fallback.
Search, selection, catalog loading, drafts, Escape and focus return remain intact.

FolderTree reconstructs recoverable importer hierarchy from depth and stored path;
literal slash names and ambiguous legacy identities remain exact entries.
Disclosure and selection are separate buttons. Counts exclude descendants.
Loaded branches/pages survive closing and category switching until library revision.
Long labels wrap to two lines and a path disclosure exposes the full identity.
The layered folder SVG interpolates matching paths over 240ms with reduced-motion
endpoints; clipped tree wrappers use inset focus outlines.

## Cards and reading

Native original links and independent selection/edit/process controls remain.
Blank card areas open preview through the real preview button's focus-return path.
Modifier clicks, non-left buttons, text selection and interactive descendants retain
their own actions. The card owns whole-row index visibility and corrects final bounds
after layout animation; hidden/inert lists never scroll. Close restores the collection
scroll position and returns focus to the actual record opener.

Reading retains a compact index on wide screens and previous/next/close operations.
Only a saved, successful body-text tab has a 48px in-flow progress footer.
Summary, related, pending, failed and empty-text states do not show a placeholder
“reading preview” box. The footer holds real progress, chapter selection and a
36px capsule return-to-top button (40px mobile); it does not cover the last paragraph.
Article width is 740px; native source access remains visible.

Cards retain the interruptible layout spring (340/32) and source-owned opacity/
position entrances. Folder/disclosure, reader, menu and dialog transitions have
separate owners. Overlay exits use 160ms and immediately stop accepting input.
Reduced motion skips spatial entrances, springs and hover sweeps while preserving
clear state changes and operation.

## Startup and tray

A shared authored `desktop/splash/mark.svg` uses the same folded-F geometry as
the generated desktop icon. React, native startup and tray consume that mark.
The package/window/tray PNG/ICO remains generated by `scripts/desktop_assets.py`
in CI. The locally installed 32px icon was read-only extracted and compared against
the installed f1c67fe cloud image: all 1024 pixels matched. This checks the installed
asset; it does not certify every Windows icon-cache rendering.

Native startup has a single identity/status panel, bounded readable errors, a
progress track and an immediate retry control. Restart waits for the previous
sidecar's actual Terminated event; a consumed child handle cannot release it. A late
native error during the promise remains visible. React boot, pairing, setup and
import retain their drafts, real completion facts and single-flight guards.

The old OS-styled tray menu is replaced by a packaged local WebView with the same
font, mark, material and blue state vocabulary. It offers open workspace, launch at
login, global shortcut, desktop/update settings and quit. Check states come from the
real native plugins; single-flight actions preserve old state on error. Arrow/Home/
End/Tab roving focus, Escape and native focus loss dismiss correctly.
Monitor-aware placement uses physical coordinates, target DPI and work-area bounds.
Rust restricts tray commands to the packaged tray page's label and URL.
Synthetic cloud opening is separately identified when the hosted notification area
cannot expose an actual right-click.

## Ownership and verification

`styles.css`: fonts/theme; `ui/controls.css`: shared control paint;
`workbench.css`: shell/search/responsive geometry; `bookmark-card.css`: records;
`facet-browser.css`/`folder-tree.css`: directory and disclosure;
`folder-picker.css`/`AnchoredMenu.tsx`: picker paint and placement;
`reader-shell.css`: reading; `startup.css`/`setup.css`: React arrival;
`desktop/splash/native-ui.css`: native startup/tray paint;
`desktop/src-tauri/src/tray_menu.rs`: privileged native actions.

Sidecar specimens show static source-defined visual states. They do not reproduce
React, native APIs, focus management or motion controllers, and are not runtime
evidence. Tonal ramps are preview aids, not new shipped tokens.

Local checks cover syntax, whitespace and isolated source behavior only. All
dependency installs, builds, browsers, packaging and installed-app checks run in
GitHub Actions with isolated synthetic data. Record exact current runs in
[the follow-up](docs/workspace-layout-2026-10-24.md). Historical verification,
technical passing status and user aesthetic acceptance remain separate.
