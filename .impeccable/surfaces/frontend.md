---
version: 1
slug: "frontend"
primary_target: "frontend"
related_targets: ["frontend/src/App.tsx", "frontend/src/Reader.tsx", "frontend/src/workbench.css", "frontend/src/styles.css"]
---

# Shared collection and reader — Operate / Read

## Direction contract: rebuild after user rejection

USER EVIDENCE: The user rejected the d618c52 screenshots: “整体太普通，像后台管理工具”. The earlier seven-fix review is historical and does not certify this direction. Fresh independent review returned rebuild across the shell, content index, reader, focus and narrow-window composition.

THESIS: Saved content is the workspace. An open, bounded two-column collection becomes a supporting index beside a full article when selected. Navigation never permanently occupies a vertical column.

OWN-WORLD: Facetmark layered mark, porcelain article surface, faint violet-grey desk, graphite text and restrained plum interaction. Typography and content proportions carry the identity, without glass, generated imagery or decorative motion.

FIRST VIEWPORT: 72px horizontal app header, 88px search-and-collection toolbar, then content. No selection: bounded two-column index, titles and meaningful excerpts first. Selection: 360px supporting index and a dominant white reading sheet, 28px gutter between them. Reader controls share one 54px row; source/title/body share one reading axis. Tags and match details are disclosed on demand. Ordinary desktop prose begins around 350px rather than behind multiple stacked toolbars.

PATH: Search, scan content, select, read, optionally expand, restore. Preserve query, filters, page, selected row and focus. Collection and reading layouts have their own saved list position; switching back restores the original collection position. Result content is immediately interactive, with no row stagger. The unselected toolbar and collection share 1160px bounds. Focused reading hides the search row and utilities, reduces the app header to 56px, and starts the reader 16px below it. Narrow windows use full-viewport reading with a visible “返回收藏 / Back to collection” action, previous/next controls, and a separate tab row.

REACH: The same top frame contains import, tasks, model settings and saving sessions. All existing consent, probe, indexing, pagination, keyboard and desktop behaviors remain. Both themes and languages use the same components.

FORM: User-directed code-led rebuild, informed by original seed db981777 and the new independent rejection review. No approved mockup exists. The user delegated design decisions and clarified that the administration-tool silhouette is the defect; no new color/radius preference round is required.

VERIFY: GitHub Actions only for build/browser/package. Synthetic data only. First capture batch, consolidated corrections, then confirmation. Judge whole silhouette and content priority against the rejected screenshots, not only CSS consistency. Fresh review and source-derived documentation are required before delivery. Current composition source: frontend/src/workbench.css; shared component foundations: frontend/src/styles.css.
