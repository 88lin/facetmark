---
name: Facetmark collection workspace
description: Production collection rebuild; implemented working direction awaiting user review.
---

# Facetmark collection workspace

The collection screen is rebuilt in the real React application. This is an
implemented working direction, not user aesthetic approval. The old purple
capsule UI, Orbit folders and teal standalone prototype remain rejected. The
current review boundary is the complete collection screen and its reading return
flow; settings/task interiors retain their functional implementation.

## Composition and material

A horizontal application bar separates navigation from a full-height directory.
The directory sits on a warm limestone desk; the collection occupies a raised
white sheet with a title/search band, action and status controls, independently
scrolling results, and a stable pagination footer. A selected item opens beside
the result index on wide screens and in the existing focus-managed drawer below
1120px. Below 960px, the directory moves into the navigation drawer.

Light: desk `#f1efeb`, surface `#ffffff`, text `#28282c`, secondary text `#55534f`,
accent `#b94726`. Dark: desk `#191a1d`, surface `#252628`, text `#f2eee7`, secondary
text `#d0c9bf`, accent `#ffac8c`. Components use semantic tokens for both themes.
Cards have 18px corners, the collection sheet 24px, controls 10px, small metadata
labels 5px. These are role-specific values, not blanket button/input overrides.

The UI font follows Windows Segoe UI Variable/Segoe UI, Microsoft YaHei UI,
PingFang SC and bundled Noto Sans SC fallbacks. Chinese does not inherit Latin
negative tracking. Collection titles use 27px/650, bookmark titles 19px/650,
summary text 15px/1.75, metadata at least 13px. Short windows reduce surrounding
chrome rather than remove record metadata.

## Ownership and interaction

- `workbench.css`: application bar, directory placement, collection grid, search,
  footer, responsive layout and reader pane geometry.
- `BookmarkCard.tsx` / `bookmark-card.css`: original links, measured summary
  expansion, summary status, all tags, path, selection and entry actions.
- `FacetBrowser.tsx` / `facet-browser.css`: real paged folder/tag/domain controls;
  displayed leaf names keep their full literal API path.
- `CollectionFolderIcon.tsx` / `collection-folder-icon.css`: restrained folder
  front morph driven by actual active/open state in directory and folder picker.
- `ui/controls.tsx` / `ui/controls.css`: native event/form bridge and semantic
  HeroUI tokens. HeroUI owns pressed state and press transform.
- `reader-shell.css`: reading typography and controls. Existing App refs retain
  result scroll position and return focus.

The document-wide ink portal and old FolderGlyph are removed. Bookmark mount and
layout animations use stable bookmark IDs; checkbox fill/check drawing are local
decorations over a stable native input. Each target update interrupts its previous
animation. Reduced-motion preference updates immediately apply without movement.

## Source references

[Source audit](docs/redesign-source-audit.md) records the pinned HeroUI, FlClash,
GithubStarsManager and Bencho implementations. Bencho supplies motion mechanisms,
not app data or an additional dependency. Its showcase resets, mobile keyboard
suppression and incomplete focus behavior are excluded. No Bencho component code
or branded assets were copied.

## Verification status

Local CSS/TSX syntax and diff checks are separate from full type checking and
runtime behavior. Builds, browser testing and Windows installation run only in
GitHub Actions against isolated synthetic data. Current run IDs and source hashes
are recorded in [desktop validation](docs/desktop-validation.md) after completion.
Technical passes establish their listed scope; the user has not accepted this
visual direction.
