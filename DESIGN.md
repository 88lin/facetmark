---
name: "Facetmark workbench"
description: "An open search and reading desk in porcelain white, graphite and plum."
colors:
  canvas: "#ffffff"
  rail: "#f7f7fa"
  inset: "#f5f5f8"
  ink: "#282831"
  muted: "#696977"
  rule: "#e9e8ef"
  accent: "#7255c1"
  soft: "#f1edf9"
  on-accent: "#fff"
  danger: "#ad3448"
  overlay: "#20202b55"
  canvas-dark: "#202027"
  rail-dark: "#1b1b22"
  inset-dark: "#282830"
  ink-dark: "#eeeef3"
  muted-dark: "#aba9b8"
  rule-dark: "#35343f"
  accent-dark: "#b7a0ec"
  soft-dark: "#30293f"
  on-accent-dark: "#241b35"
  danger-dark: "#f7a0ae"
  overlay-dark: "#09091099"
typography:
  headline:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "26px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-0.02em"
  section:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-0.02em"
  subheading:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-0.02em"
  workspace-title:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0"
  article-title:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-0.025em"
  article-section:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.65
    letterSpacing: "-0.02em"
  body:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "14px"
    lineHeight: 1.6
  result-title:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.6
  result-summary:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "12px"
    lineHeight: 1.7
  result-meta:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "11px"
    lineHeight: "18px"
  reading:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "16px"
    lineHeight: 1.95
  button:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "13px"
    fontWeight: 550
    lineHeight: 1.5
  search:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "14px"
    lineHeight: 1.6
  tab:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "12px"
    lineHeight: 1.6
  label:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "12px"
    lineHeight: 1.6
  caption:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "11px"
    lineHeight: 1.6
  micro:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "10px"
    lineHeight: 1.6
  diagnostic:
    fontFamily: "ui-monospace, Consolas, monospace"
    fontSize: "11px"
    lineHeight: 1.6
rounded:
  hint: "4px"
  facet: "5px"
  control: "6px"
  search: "7px"
  popover: "8px"
  session: "10px"
  panel: "12px"
spacing:
  micro: "4px"
  tight: "6px"
  compact: "8px"
  small: "12px"
  medium: "16px"
  content: "20px"
  section: "24px"
  gutter: "28px"
  large: "32px"
  title-top: "36px"
  reader-gutter: "48px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-secondary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
  button-text:
    textColor: "{colors.accent}"
    typography: "{typography.label}"
    padding: "5px 0"
  button-icon:
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    width: "32px"
    height: "32px"
  search-field:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.ink}"
    typography: "{typography.search}"
    rounded: "{rounded.search}"
    padding: "5px 12px"
    height: "40px"
  navigation-active:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "9px 12px"
  filter-chip:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.accent}"
    typography: "{typography.caption}"
    rounded: "{rounded.hint}"
    padding: "3px 8px"
  settings-panel:
    textColor: "{colors.ink}"
    padding: "24px 0"
  apply-panel:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "24px"
  result-selected:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.ink}"
    padding: "12px 24px"
  preview-tabs:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.muted}"
    typography: "{typography.tab}"
    padding: "0 24px"
    height: "47px"
---

# Design System: Facetmark workbench

## Overview

**Creative North Star: "Shared workbench — Operate / Read"**

Facetmark is an index beside an open reading desk. Porcelain white working surfaces, faint violet-grey navigation, graphite text and plum selection marks make finding a saved thought and reading its source feel continuous. Small controls and ruled rows establish precision; generous prose establishes a different pace for reading.

The workbench keeps Facetmark’s layered mark and independent identity. Its brightness and order continue the approved direction, while the settled implementation uses source-first rows and a stable reader. The shared React interface serves the Tauri desktop shell, Python distribution and Docker image, with local Chinese and English typography and matching light/dark semantic roles.

**Key Characteristics:**

- White working surfaces and pale navigation, separated by fine rules.
- Source, title, excerpt and folder form a compact result hierarchy.
- Fixed reader controls frame an independently scrolling article.
- Focus reading expands within the same workspace; narrow windows use a modal drawer.
- Plum marks actions and selection; restrained motion preserves context.

This refresh records the shared frontend at UI revision `d618c52`. Source inspection and cloud browser diagnostics agree on the design values below. Experience run `37311576521` completed with 14 tests and 32 captures. Windows installation and the additional nonzero list-scroll assertion passed separately; exact evidence and boundaries are in `docs/desktop-validation.md`. These checks are not user screenshot approval. Product constraints and synthetic-data capture rules remain in PRODUCT.md.

## Colors

Frontmatter values are normative. Base names map directly to the CSS custom properties; each `-dark` entry supplies the corresponding role under the dark theme.

### Primary

- **Plum** (`accent`): primary buttons, links, active navigation, tab indicator, focus rings and reading progress.
- **Faint Violet** (`soft`): selected rows, active navigation, filter chips, notices and text selection.
- **On Plum** (`on-accent`): primary-button text.

### Neutral

- **Porcelain White** (`canvas`): the main workspace, reader, fields and outlined panels.
- **Violet-grey Navigation** (`rail`): the light navigation surface.
- **Inset Paper** (`inset`): the resting search field, row hover, disabled fields, skeletons and diagnostic/error surfaces.
- **Graphite** (`ink`): headings, result titles and body text.
- **Secondary Graphite** (`muted`): excerpts, metadata, hints and inactive controls.
- **Fine Rule** (`rule`): structural seams, borders, scrollbars and navigation hover.
- **Modal Scrim** (`overlay`): modal drawer and mobile navigation backdrops.

### Status and themes

**Error Red** (`danger`) accompanies visible failure text and recovery controls. The dark theme uses graphite surfaces, pale text and lighter plum while retaining all role assignments. Text selection uses Faint Violet with Plum text; inputs use a Plum caret. The sidecar’s generated tonal ramps are swatch previews, not additional runtime colors.

**The One Accent Rule.** Use plum for actions, focus and selected-state details. Keep result titles graphite, including selected rows, and reserve the danger role for failures.

## Typography

**Body and interface font:** the declared local stack in frontmatter. The interface requires no remote font download. Diagnostic output uses the separate monospace stack; there is no promotional display-face token. In the confirmed cloud browser sample, CDP resolved Chinese text to Noto Sans CJK SC (Fontations); computed reading, article-title and result-metadata styles matched the frontmatter roles. This verifies that browser environment, not the installed fonts on every supported platform.

### Hierarchy

- **Interface headings:** the headline, section and subheading roles describe base headings. Base Chinese headings have zero letter spacing; scoped workspace and article rules take precedence. Model headings use (18px) with the base heading weight/leading.
- **Workspace and results:** the workspace heading and result title use their compact roles. Result titles clamp to two lines. Excerpts clamp to one line on desktop and two below the drawer breakpoint. The source/domain and saved date appear before the title; the date uses (10px) and tabular numerals. Folder metadata follows the excerpt.
- **Article:** the title uses the article-title role. Its scoped tracking remains (-0.025em), including Chinese. Body text uses the reading role, with paragraph spacing (1.5em). The article container has a maximum width (780px), inclusive of its horizontal content gutters. Explicit Markdown headings use the article-section role; arbitrary short paragraphs do not become headings.
- **Controls and metadata:** button, search, tab, label, caption and micro roles separate actions from secondary information. Model fields use (13px / 1.5); placeholder text uses (12px). Counts, dates, pagination and reading percentages use tabular numerals.
- **Responsive reading:** compact desktop article titles use (26px). On mobile, article/page titles use (23px), article body uses (15px) with its existing leading, and section/import headings use (19px). Result titles retain their desktop size.

**The Reading Rhythm Rule.** Keep controls and source metadata compact while giving article text generous leading and paragraph space. Wrap Chinese text, long titles and URLs without widening the workspace.

## Layout

The shell fills the dynamic viewport (`100dvh`) with a minimum height (400px), no outer frame and no inset workspace margin. At the standard desktop width, navigation is (208px), the result index is (424px), and the reader occupies the remaining space. The main grid has a shared search toolbar (72px) above its two content columns. The navigation brand aligns to the same top seam.

The toolbar uses horizontal padding (28px), gap (20px), a location label, an inset search field capped at (680px), and compact search help. The input height comes from the search-field token. The result header uses padding (22px 24px 15px); filters wrap beneath the count and search context. The result list scrolls independently without outer card padding, above a footer (48px). Standard result-row padding comes from the result-selected token.

The reader has a heading/action bar (51px), a fixed tab strip, an independent article scroller and a bottom position bar (48px). The article is centered; title padding is (36px 48px 24px) and reading padding is (28px 48px 44px) at standard desktop widths. The shared reader gutter also aligns context, search explanations and privacy notices. Focus reading covers the index within the main workspace below the toolbar; navigation and search remain present, and the covered result list is inert.

Content pages use padding (44px clamp(24px, 5vw, 72px) 64px). Page headings, settings and tasks have a maximum width (1040px). Model channels use two equal columns with a gap (48px), each beginning with a fine top rule.

| Viewport | Implemented layout |
| --- | --- |
| At least 1600px | Navigation (224px), result index (460px), reader gutter (56px). |
| 1301–1599px | Standard navigation (208px), index (424px), reader gutter (48px). |
| 1120–1300px | Navigation (188px), index (374px), reader gutter (32px); toolbar gap (14px) and horizontal padding (24px); row padding (12px 22px). |
| At most 1119px | Reader becomes a right modal drawer, width `min(650px, 94vw)`; results fill the remaining workspace. Row padding (18px 28px); excerpts allow two lines. Model channels stack with gap (16px). |
| At most 719px | Navigation becomes an off-canvas rail (250px) with a mobile toolbar (52px). Search toolbar height (68px), horizontal padding (18px); result padding (17px 22px). Reader drawer fills the viewport width with gutter (24px). Page padding becomes (28px 22px 40px). |

The location label hides below (1120px); the toolbar demo label hides in compact desktop and mobile layouts. The mobile search shortcut hint hides; saved dates remain in source metadata. Page headings and form actions stack on mobile. Search help fits the viewport using `min(340px, calc(100vw - 36px))`.

## Elevation & Depth

The shell, rows and reader stay flat. Pale navigation, inset fields and one-pixel rules define structure. Floating search help alone uses a subtle shadow (`0 12px 36px #17132112`), plus a fine border; drawers use a scrim and stacking order. There is no blur or raised result-card treatment.

Keyboard focus uses an accent outline (2px, offset 3px); result rows inset that outline with offset (-3px). Search focus changes its container border to Plum and its fill to Porcelain White.

**The Flat Surfaces Rule.** Use pale tone and fine rules for structural separation. Reserve the small shadow for floating search help and the scrim for modal depth.

## Shapes

Structural columns, result rows and model sections have square edges. Small radii distinguish controls: hints, result source initials and chips use the hint radius; facet controls and article source initials use the facet radius; buttons, fields and navigation use the control radius. Search and floating help have their own radii.

Session rows and import drop targets use the session radius; apply, consent and stage panels use the panel radius. These scoped panels remain part of the system even though the primary workbench is unboxed. Import targets use dashed rules. Circular step numbers and activity dots are functional status shapes. Lucide SVGs supply small stroke icons; domain initials remain text within compact source markers.

## Components

### Buttons and fields

Primary and secondary buttons use their frontmatter padding, a minimum height (36px), icon gap (8px) and (16px) icons. Primary hover applies `brightness(0.94)`; secondary hover uses Inset Paper. Text buttons underline on hover. Icon buttons use the compact square token, an inset hover fill and Faint Violet when pressed. Disabled buttons use opacity (0.42).

Search rests on Inset Paper and changes border/fill on focus. Model fields are outlined on Porcelain White, with padding (11px 12px) and the control radius. Disabled fields use muted text and Inset Paper. Search clearing remains inside the field; Ctrl/Cmd+K returns to the library and focuses search.

### Navigation and chips

Main navigation uses muted text, (13px) labels, (16px) icons, a minimum height (38px) and the active token. Hover uses Fine Rule; active navigation uses Faint Violet, Plum and weight (600). Facet rows are smaller, use their own radius and show counts separately. Mobile navigation traps focus while open, makes background content inert, closes on Escape and restores focus; the closed off-canvas rail is inert.

Filter chips use the frontmatter token and a remove icon. Article tags use Inset Paper, padding (2px 7px), (10px) text and the hint radius; hover changes them to Faint Violet and Plum. Tags act as search filters.

### Model columns and scoped panels

Model channels remain unboxed columns with a top rule, independent status/test controls and aligned fields. Headers separate from fields by (26px); fields have a bottom margin (19px). Apply, consent and stage surfaces retain thin outlined panels. Import targets use Inset Paper and dashed borders with padding (44px 28px), reduced to (32px 18px) on mobile. Apply and consent padding becomes (18px) on mobile. Notices and errors include readable explanations; configured, tested, indexed and applied states remain distinct.

### Source-first results

A result is a full-width button: source initial/domain and date, title, excerpt, then optional folder context. The row gap is (5px). Hover uses Inset Paper. Selection uses Faint Violet, a one-pixel Plum mark inset vertically (16px), an accented source initial and `aria-pressed`; selected titles stay Graphite. The reading label appears with folder metadata for the selected row. Trailing chevrons remain hidden.

ArrowUp/ArrowDown selects and focuses adjacent results. Opening a result keeps the list and search context; closing restores focus to the originating row. Empty libraries, no matches and retrieval failures have separate explanations and actions.

### Coherent reader

The heading holds previous/next, focus-reading and close controls. Tabs and the original-page link stay above the article scroller; the active tab uses Plum text, weight (600) and a moving two-pixel underline. Tabs use a single active tab stop, ArrowLeft/ArrowRight and Home/End navigation, with a linked tab panel.

Source, saved date, title, folder and tags precede the content. The reader has separate body, AI-summary and related-bookmark states, with distinct loading, missing-content and error messages. Switching tabs saves each tab’s scroll position for the current bookmark; selecting another bookmark resets those positions. Only explicit Markdown headings create section targets, and a duplicated first title paragraph is omitted.

The bottom rail reports the actual scrollable article position, with a section picker only when explicit sections exist and a back-to-top action. Progress is shown only for successfully loaded saved body text; a non-scrollable body reports complete. AI summary and related views retain the rail without a synthetic percentage.

Desktop focus reading expands the same pane while retaining the mounted result list. Escape first restores split view; a subsequent Escape closes the preview. At the drawer breakpoint, Radix supplies modal reader behavior and focus restoration.

### Motion

Motion is scoped to functional continuity. CSS handles control/background changes (150ms), facet-chevron rotation (180ms) and mobile-navigation translation (220ms), using the shared ease `cubic-bezier(0.22, 1, 0.36, 1)`. Busy spinners rotate linearly over (1.1s).

GSAP owns the tab indicator’s horizontal position/width (180ms, `power3.out`, overwrite `auto`) and the desktop focus pane’s horizontal transform (220ms with the same ease and overwrite policy). Repeated focus changes kill the previous timeline and continue from the current geometry; completed focus motion clears the transform.

Motion owns drawer translation (220ms, easing [0.22, 1, 0.36, 1]), drawer-overlay opacity (180ms), and the reading-progress scale. Its progress spring uses stiffness (180), damping (35) and mass (0.25). These owners do not share animated properties on the same element. Reduced motion removes CSS animation/transition, makes GSAP/drawer changes immediate, uses the direct progress value and switches programmatic scrolling to automatic behavior.

## Do's and Don'ts

### Do:

- **Do** keep the light workspace white, the navigation pale and structural edges straight.
- **Do** preserve the source-first result order and graphite selected titles.
- **Do** keep reader actions and tabs outside the article scroller.
- **Do** preserve query, filters, pagination and list position when expanding and restoring reading.
- **Do** bind both themes to the same semantic roles and retain local Chinese/English font fallbacks.
- **Do** provide visible focus, keyboard navigation, reduced motion and distinct recovery states.
- **Do** show measured reading position only when saved body text is available.

### Don't:

- **Don't** turn the result list into raised cards, large source avatars or a candy-colored dashboard.
- **Don't** reintroduce a dark navigation frame in the light theme, an inset rounded workspace shell or hand-drawn borders.
- **Don't** add promotional labels to the compact search toolbar.
- **Don't** let GSAP, Motion and CSS animate the same property on the same element.
- **Don't** invent reading percentages, inferred section headings or successful task states.
