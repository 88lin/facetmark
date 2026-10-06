---
name: "Facetmark collection and reader"
description: "A content-led collection on a violet-grey desk, with porcelain reading surfaces and plum interactions."
colors:
  canvas: "#ffffff"
  desk: "#f5f4f7"
  inset: "#f5f5f8"
  ink: "#272330"
  muted: "#6d6678"
  rule: "#e7e3ed"
  accent: "#7050b5"
  soft: "#eee8f7"
  on-accent: "#fff"
  danger: "#ad3448"
  overlay: "#20202b55"
  canvas-dark: "#28252f"
  desk-dark: "#1c1a20"
  inset-dark: "#282830"
  ink-dark: "#f0edf5"
  muted-dark: "#b0a8bd"
  rule-dark: "#3e3749"
  accent-dark: "#c0a4ef"
  soft-dark: "#393044"
  on-accent-dark: "#241b35"
  danger-dark: "#f7a0ae"
  overlay-dark: "#09091099"
typography:
  collection-heading:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "27px"
    lineHeight: 1.35
    fontWeight: 650
    letterSpacing: "-0.025em"
  page-title:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "30px"
    lineHeight: 1.5
    fontWeight: 600
    letterSpacing: "-0.02em"
  article-title:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "30px"
    lineHeight: 1.4
    fontWeight: 650
    letterSpacing: "-0.025em"
  article-title-focus:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "34px"
    lineHeight: 1.4
    fontWeight: 650
    letterSpacing: "-0.025em"
  article-section:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "18px"
    lineHeight: 1.65
    fontWeight: 600
    letterSpacing: "-0.02em"
  collection-title:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "19px"
    lineHeight: 1.55
    fontWeight: 600
  index-title:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "16px"
    lineHeight: 1.55
    fontWeight: 600
  collection-summary:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "14px"
    lineHeight: 1.7
  index-summary:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "13px"
    lineHeight: 1.7
  body:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "14px"
    lineHeight: 1.6
  reading:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "16px"
    lineHeight: 1.85
  button:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "13px"
    lineHeight: 1.5
    fontWeight: 550
  search:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "15px"
    lineHeight: 1.6
  tab:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "13px"
    lineHeight: 1.6
  label:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "12px"
    lineHeight: 1.6
  caption:
    fontFamily: "\"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", \"Noto Sans CJK SC\", sans-serif"
    fontSize: "11px"
    lineHeight: 1.6
  diagnostic:
    fontFamily: "ui-monospace, Consolas, monospace"
    fontSize: "11px"
    lineHeight: 1.6
rounded:
  hint: "4px"
  facet: "5px"
  control: "6px"
  popover: "8px"
  entry: "10px"
  sheet: "12px"
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
  frame: "36px"
  reader-gutter: "46px"
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
  reader-back:
    textColor: "{colors.muted}"
    typography: "{typography.tab}"
  search-field:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.search}"
    rounded: "{rounded.entry}"
    padding: "7px 15px"
    height: "48px"
  header-navigation-active:
    textColor: "{colors.ink}"
    typography: "{typography.tab}"
    padding: "0"
  filter-chip:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.accent}"
    typography: "{typography.label}"
    rounded: "{rounded.facet}"
    padding: "5px 9px"
  collection-entry:
    textColor: "{colors.ink}"
    typography: "{typography.collection-title}"
    padding: "23px 16px 24px"
  result-selected:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.entry}"
    padding: "19px 20px"
  reading-sheet:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sheet}"
  preview-tabs:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.muted}"
    typography: "{typography.tab}"
    padding: "0 26px"
    height: "54px"
  apply-panel:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sheet}"
    padding: "24px"
  model-field:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "11px 12px"
---

# Design System: Facetmark collection and reader

## Overview

**Creative North Star: "Shared collection and reader — Operate / Read"**

Facetmark puts saved content on a quiet violet-grey desk. A bounded collection gives titles and excerpts room to invite recognition; selecting an entry makes that collection a supporting index beside a porcelain reading sheet. Graphite text and restrained plum interactions retain Facetmark’s independent identity and layered mark.

The interface changes proportion with the task. Navigation lives in a horizontal header, filters open on demand, and focused reading removes competing chrome. The same components serve the desktop and Web interface in Chinese or English, using local font fallbacks and corresponding light/dark semantic roles.

**Key Characteristics:**

- Title and excerpt lead the collection; source and saved date support them.
- An open two-column collection becomes a subordinate index beside the article.
- Porcelain sheets sit on a violet-grey desk with fine rules and restrained soft depth.
- Reader tabs and actions stay outside the article scroller; details are disclosed on demand.
- Focus reading hides navigation, utilities, search and results; narrow reading has a text return control.

This authorized refresh records the current source after the rejected permanent-column design. `frontend/src/main.tsx` loads `workbench.css` after `styles.css`: the former owns composition and overrides; the latter supplies shared forms, reader internals and semantic states. Source inspection is the evidence for this document. The corrected composition was confirmed in cloud run 37410551657 and independently reviewed against the user request. Earlier first-batch captures are historical; neither validation nor this document implies user acceptance.

## Colors

Frontmatter is normative. Base names map to the used CSS custom properties; each `-dark` token supplies the same role in the dark theme. The retained but visually superseded navigation-color variable is not a new surface prescription.

### Primary

- **Plum** (`accent`): actions, links, header underline, active tabs, selected index titles, focus and measured reading position.
- **Faint Violet** (`soft`): filter chips, pressed controls, notices and text selection.
- **On Plum** (`on-accent`): primary-button text.

### Neutral

- **Porcelain** (`canvas`): header, search, article sheet, selected index entry, support pages and form fields.
- **Violet-grey Desk** (`desk`): the shell and collection background, focus header and import drop target.
- **Inset Paper** (`inset`): shared control hover, disabled fields, skeletons and diagnostic/error surfaces.
- **Graphite** (`ink`): titles, prose and active header labels.
- **Secondary Graphite** (`muted`): excerpts, source metadata, hints and inactive controls.
- **Fine Rule** (`rule`): collection dividers, field outlines, tab/footer seams and scrollbar color.
- **Navigation Scrim** (`overlay`): temporary navigation backdrop. The narrow reader itself fills the viewport and uses a transparent overlay.

### Status and themes

**Error Red** (`danger`) accompanies explicit failures and recovery controls. Dark mode uses a deeper desk beneath a lighter article surface, pale type and lighter plum; it preserves the same hierarchy. Text selection uses Faint Violet with Plum text, and fields use a Plum caret. Sidecar tonal ramps are generated swatch previews, not additional runtime palette tokens.

**The Interaction Plum Rule.** Use plum for actions, keyboard focus, active tabs and the selected index title. Keep unselected titles graphite and reserve the danger role for failure text and recovery context.

## Typography

**Interface and reading font:** the local stack in frontmatter, with Chinese fallbacks and no remote font dependency. Diagnostic output has its own monospace role. The system does not introduce a decorative display font.

### Hierarchy

- **Collection and page headings:** the collection-heading role introduces the library above search; support pages use page-title. Smaller result counts and the list label remain subordinate.
- **Collection entries:** collection-title and collection-summary apply before selection; index-title and index-summary apply beside the article. Both titles and excerpts clamp to two lines. Visual order is title, excerpt, domain/date, then selected folder context. The current DOM still lists metadata before the title; this document does not make that implementation detail a reading-order rule.
- **Article:** article-title leads the sheet, and article-title-focus enlarges it in focus mode. Saved details use caption type behind a disclosure. Reading uses generous leading with paragraph space (1.25em); explicit Markdown sections use article-section and margins (28px above, 10px below).
- **Controls and secondary information:** actions, tabs, fields and labels use their specific roles. Collection domain metadata is (12px / 18px) with (11px) dates; index metadata is (11px / 18px) with (10px) dates. Counts, dates, pagination and percentages use tabular numerals.
- **Language:** base Chinese headings remove tracking; the more specific collection and article heading rules retain their declared tracking. Font availability remains platform-dependent. Do not infer font rendering in Windows or a browser from CSS declarations alone.

At compact desktop widths, article titles become (28px). Below the drawer breakpoint, the collection heading is (24px). On mobile it is (26px), support-page titles are (26px), article titles are (25px), result titles are (17px), summaries are (13px), search is (14px), and article prose remains (16px). Mobile tabs use (12px). These are context overrides, not a second visual system.

**The Reading Rhythm Rule.** Give titles and excerpts room in the collection, then let article text set the reading pace. Wrap Chinese text, long titles and URLs without widening the workspace.

## Layout

The shell fills the dynamic viewport (`100dvh`) with a minimum height (400px). A horizontal header (72px) contains identity, collection/session navigation and compact utilities. Navigation never consumes a permanent vertical column. The on-demand navigation/filter drawer is (300px), fixed at the left edge, and closed/inert by default.

The main workspace is centered within a maximum width (1480px), with side padding (36px) and bottom space (24px). A search-and-collection toolbar (88px) spans the content. Its title block sits left, an outlined search field is capped at (520px), and search help plus Filters sit alongside it.

### Collection and selected reading

Before selection, the toolbar and results are bounded by (1160px). Entries form two equal columns with a gap (52px), content-sized rows and fine lower rules. Collection entries use their frontmatter padding and a minimum height (122px); text determines additional height. The list scrolls independently above its pagination footer (46px).

After selection, the desktop layout becomes an index (360px), gutter (28px) and flexible article sheet. The index stays mounted; its selected entry is a soft, rounded white surface with a plum title. The article does not reserve an empty welcome column before selection.

The desktop reader places actions at the upper right of the same (54px) strip as the tabs. Source, title, disclosed details and body share the reader gutter. The article is centered within (820px), including its inner gutters. Standard title padding is (26px 46px 0); body padding is (14px 46px 44px). The article scroller sits between the fixed tab strip and the reading-position footer (42px).

Focus mode reduces the header to (56px), hides header navigation/utilities, search and results, and places the sheet inside the workspace at (16px top, 36px sides, 24px bottom). The article width becomes (800px), title top space (35px), and the title uses the focus role. Hidden results are also inert. The brand and reader controls remain available.

### Support views

Import, setup, tasks, settings and saving sessions retain the same header. Their white content surface is centered within (1050px), with top margin (28px), padding (36px 48px 48px) and the sheet radius. Model channels remain two unboxed columns with a gap (48px) and a top rule. Scoped apply, consent, stage and session panels preserve their separate purposes.

| Viewport | Composition overrides |
| --- | --- |
| At least 1600px | Index (390px), reader gutter (56px). The outer workspace remains bounded. |
| 1301–1599px | Standard index (360px), reader gutter (46px), outer sides (36px). |
| 1120–1300px | Index (330px), reader gutter (36px), outer sides (28px), selected-layout gap (22px), search basis (430px), article title (28px). Reader count hides. |
| 720–1119px | Results retain two columns with gap (28px). A selected article uses a full-width, full-height modal reader; its top row (52px) has Back to collection and previous/next, followed by tabs (48px). The collection toolbar is (100px). Header navigation remains; a menu button exposes the drawer, and language/demo text hide. Support padding becomes (32px); model channels stack with gap (16px). |
| At most 719px | Header (60px) shows menu and brand; navigation/utilities move into the drawer. Workspace sides are (18px). The toolbar becomes a two-row grid with a heading/count row and search/help/filter row; search height is (45px). Results become one ruled column with padding (19px 5px). Full-width reading uses a (24px) article gutter, (25px) title and (16px) prose. Support margin becomes (16px), padding (24px 20px). |

The full-width reader uses a visible text return control, not a gray remainder beside a partial-width sheet. Its tab-strip height remains (48px) on mobile because the drawer-specific selector takes precedence. Mobile search hides the shortcut hint, and search help fits within `min(340px, calc(100vw - 36px))`. Shared mobile form actions and page headings stack.

## Elevation & Depth

The desk and porcelain surfaces establish depth before shadows. Unselected collection entries stay transparent with lower rules. Selected entries, article sheets and the temporary navigation drawer use restrained ambient shadows; the system is not flat-only.

### Shadow vocabulary

- **Selected entry:** `0 4px 16px #20142e08`.
- **Article sheet:** `0 8px 36px #20142e0c`.
- **Temporary navigation:** `8px 0 40px #16102014`.
- **Floating search help:** `0 12px 36px #17132112`, with a fine border.

There is no backdrop blur. Keyboard focus uses an accent outline (2px, offset 3px); result rows use an inset offset (-3px). Search focus changes its border to Plum while retaining Porcelain fill.

**The Quiet Depth Rule.** Use soft depth to separate the selected entry, article sheet and temporary navigation. Keep the unselected collection open and ruled, with no decorative floating effect.

## Shapes

The main collection remains open and ruled. Its unselected entries have square edges; selected index entries and search use the entry radius, while the article and support surface use the sheet radius. The current selection has no left-edge stripe.

Shared buttons, model fields and notices use the control radius. Filter chips use the facet radius; shortcut hints and article tags use the hint radius. The outlined header import action and search help use the popover radius. Import drop targets and saving-session rows use the entry radius. Consent, apply and stage panels retain the sheet radius.

Lucide SVGs supply stroke icons; the header retains Facetmark’s layered mark. Domain-initial badges and trailing result chevrons are hidden in the current collection. Hashtag prefixes in disclosed article tags identify tags rather than substitute for action icons.

## Components

### Buttons and fields

Primary and secondary buttons retain their frontmatter padding, minimum height (36px), icon gap (8px) and icon size (16px). Primary hover uses `brightness(0.94)`; secondary and icon hover use Inset Paper. Text actions underline on hover. Pressed icon buttons use Faint Violet and Plum; disabled buttons use opacity (0.42).

Search is an outlined Porcelain field at rest, with a Plum focus border and internal clear action. Ctrl/Cmd+K returns to the library, leaves focus reading and focuses search. Model fields use a fine outline and their own padding; disabled fields use muted type and Inset Paper. Password fields retain the separate saved/replace/clear state language.

### Horizontal navigation and on-demand filters

Header navigation uses muted (13px) labels. The active item uses Graphite, weight (650), and a Plum underline (3px high, 13px above the header bottom); it is not a filled navigation pill. The header import action is outlined with padding (8px 13px). Its hover uses Faint Violet.

Filters open the navigation drawer at every width. Drawer navigation retains its compact filled active state, icon labels and facet counts. Opening it makes the header/main inert, traps focus, closes on Escape and returns focus; closed navigation is inert and hidden from assistive technology.

Removable filter chips use the frontmatter token. Article tags are lightweight text with a hashtag prefix, revealed inside saved details; their hover adds Faint Violet and Plum. Clicking a tag applies the corresponding filter.

### Collection entries

A result is a full-width button whose visual hierarchy is title, two-line excerpt, then source/date. Its content gap is (7px). Hover mixes Porcelain at (65%) with transparency. Selection changes the compact index entry to Porcelain with soft depth and a Plum title; folder context and the Reading label appear when present. The accessible pressed state identifies the selected entry.

ArrowUp/ArrowDown selects and focuses adjacent entries. Opening an entry stores the collection scroll position and brings the selected index entry into view. Returning restores collection position and the originating row’s focus. Query, filters and page remain intact; pagination resets the collection scroll position. Empty collection, no matches and retrieval failures keep distinct explanations and actions.

### Reader

Desktop previous/next, focus and close actions occupy the tab row. The narrow reader replaces focus/close icons with a visible **Back to collection** control while retaining previous/next. Tabs have one active tab stop, ArrowLeft/ArrowRight and Home/End navigation, a linked panel and a moving underline (2px). The original-page link is the article’s source label above its title.

Saved folder, tags and search explanations live behind **Saved details & search context**. Body, AI summary and related content keep their own loading, missing-content and error states. Changing tabs preserves each tab’s scroll position for the current bookmark; changing bookmarks resets them. Only explicit Markdown headings form section targets, and an exact duplicated first title paragraph is omitted.

The position rail measures the actual saved-body scroll extent, with a section picker only when explicit sections exist. It shows progress only for successfully loaded saved body text; non-scrollable text is complete. Other tabs retain the rail without a fabricated percentage. Focus expands the same pane and saves the prior split-view article position. Escape restores split view first, then closes the preview. Radix supplies narrow-reader modality and focus restoration.

### Support panels

Model channels remain ruled columns with independent status and test controls. Apply, consent and indexing stages use thin outlined panels. The import target is a dashed region on the Desk with padding (48px 24px); this later rule also governs mobile. Saving-session rows use a fine outline, the entry radius and Inset Paper hover.

Configured, tested, indexed and applied states stay separate. Failures pair semantic color with readable status and recovery actions. Synthetic demo identification and privacy exclusions remain functional notices, never ornamental headings.

### Motion

CSS owns shared control transitions (150ms), facet-chevron rotation (180ms) and navigation translation (220ms), using `cubic-bezier(0.22, 1, 0.36, 1)`. Busy spinners rotate linearly over (1.1s). Collection entries are immediately interactive with no staggered entrance.

GSAP owns tab-indicator position/width (180ms, `power3.out`, overwrite `auto`) and focus-pane translation on both axes (220ms with the same ease). A new focus action kills the prior timeline and uses current geometry; completed motion clears the transform.

Motion owns narrow-reader translation (220ms, easing [0.22, 1, 0.36, 1]), transparent-overlay opacity (180ms), and progress scale. The progress spring uses stiffness (180), damping (35), mass (0.25). Owners do not share animated properties on one element. Reduced motion removes CSS transitions/animations, makes GSAP/drawer changes immediate, uses direct progress and changes programmatic scrolling to automatic behavior.

## Do's and Don'ts

### Do:

- **Do** lead collection entries with a visible title and meaningful excerpt.
- **Do** let selection change the collection into a supporting index beside the article.
- **Do** keep reader tabs and actions outside the article scroller and disclose saved details on demand.
- **Do** preserve query, filters, pagination, collection position and originating-row focus when returning from reading.
- **Do** make focus reading remove competing navigation and search chrome.
- **Do** provide a visible Back to collection control in the full-width narrow reader.
- **Do** bind both themes to semantic roles and retain local Chinese/English font fallbacks.
- **Do** preserve visible focus, keyboard selection, reduced motion and distinct recovery states.

### Don't:

- **Don't** restore the rejected permanent three-column management shell.
- **Don't** make operational status, filters or maintenance controls dominate the collection.
- **Don't** reintroduce source avatars, a selection-edge stripe or source-first visual ordering into collection entries.
- **Don't** replace the independent Facetmark identity with hand-drawn borders, glass or a candy-colored dashboard.
- **Don't** let GSAP, Motion and CSS animate the same property on the same element.
- **Don't** invent reading percentages, section headings or successful task states.
