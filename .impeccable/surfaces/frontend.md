---
version: 1
slug: "frontend"
primary_target: "frontend"
related_targets:
    [
        "frontend/src/App.tsx",
        "frontend/src/Reader.tsx",
        "frontend/src/workbench.css",
        "frontend/src/styles.css",
        "frontend/src/SearchTools.tsx",
        "frontend/src/Settings.tsx",
        "frontend/src/components/ui/reader-outline.tsx",
    ]
---

# Facetmark collection and reader — Operate / Read

## Direction contract

USER EVIDENCE: The user selected “纯白＋湖蓝：清亮、干净，圆角面板与精致控件”, then required “按钮这些用圆角胶囊呀，其他样式还需要美化”. The latest rejection is “还能再美化一下吗？优秀的前端设计，现在不是有很多技能，组件库什么的吗？就不能做到更好看吗”. This revision must improve composition, typography, information hierarchy and useful interaction across the collection and reader. White, lake blue and true pill controls remain authoritative. Earlier reviews and ship verdicts describe earlier revisions only.

THESIS: Make saved writing inviting to rediscover. A clear collection masthead, generous search field and recognizable sources give the library a distinct reading identity. Selecting a page makes its article the primary surface while keeping a compact route back to the collection.

OWN-WORLD: Pure white surfaces, a pale blue workspace, deep blue ink and lake-blue interaction accents. Keep true capsule controls (999px radius), circular icon buttons, 16px collection cards and a 20px reader surface. Primary lake-blue capsules, secondary outlined or soft capsules and quiet text actions express different priorities. Bundle Manrope offline for Latin text and retain local Chinese font fallbacks. Source initials, real excerpts and metadata carry the visual detail; avoid decorative imagery, gradients and a permanent management sidebar. Principal desktop actions remain 40–42px; primary mobile targets remain at least 44px.

STORY: Search, scan, open, read and return without losing query, position or focus. Persistent search and the cmdk command menu serve the existing collection actions. Folder shortcuts come from actual folder data. The interruptible focus expansion remains the signature transition; moving pill tab selection connects the reading modes. In focused reading, a quiet section rail offers direct access to actual article headings.

FIRST VIEWPORT: A compact white application header retains the layered lake-blue mark and filled navigation selection. The collection opens with a 38px masthead and contextual count, followed by a separate 58px pill search field and useful folder shortcuts. Content-sized white cards show source before a 19px title, optional excerpt and supporting metadata. Use three columns from 1360px, two at intermediate widths and one on mobile; preserve natural card heights with 20px horizontal and 16px vertical gutters on desktop. Selection contracts the collection to a supporting 312px index at the standard desktop width, with breakpoint adjustments, beside the dominant reader. The selected card uses a clear pale-blue state. Preserve search and collection position when entering and leaving reading.

READING: The standard desktop article title is 36px, increasing to 38px in focused mode; body text is 17px with 1.9 line-height and generous paragraph spacing. Keep the article measure bounded and its controls outside the article scroller. Saved details and search context remain available on demand. In focused body reading, show the 170px sticky chapter rail only at wide desktop widths and only when more than one real heading exists. Use quiet 12px wrapping labels, a lake-blue current-section marker and container-local scrolling. The Rare UI RailToc adaptation keeps real heading tracking and reduced-motion behavior; it introduces no generated headings or reading progress. Narrow reading retains its visible return action and native section picker.

SUPPORT: Settings present the chat and embedding channels as distinct, aligned forms. Essential fields lead directly into each channel's test action and result; optional settings follow those tests. Preserve the difference between configured, tested, indexed and applied states. Keep loading, empty, failure, unavailable-content and recovery states legible in Chinese and English, light and dark themes.

FORM: This is a user-directed continuation of the pinned white/lake-blue world with a materially stronger hierarchy and reading composition. No new concept election is claimed. Reuse Manrope, cmdk, Motion and the attributed Rare UI adaptation where each serves a concrete user action, and retain their applicable notices. Component provenance does not establish visual quality; the assembled product still requires a current-source review.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

VERIFY: Use only the synthetic corpus and cloud build/browser/packaging workflow. Associate captures and test results with the exact source revision. Check the collection hierarchy, natural card heights, real folder shortcuts, command search, normal and focused reading, outline click and keyboard tracking, return-context preservation, model-test ordering, narrow layouts, both themes and edge states in one batched inspection. Consolidate corrections before a bounded confirmation pass. Do not use personal browser data or a local application runtime. This contract records the required checks, not completed test results.

EVIDENCE: Source 0aa3e849ae06d6707fb1f52356eefe6bd774ff4a passed cloud Experience 37618229826 (19 browser tests, 1882 Python / 1 skipped, build and distribution), CI 37618237956 and Windows installation 37618229866. The source-matched 37-capture batch and installed screenshots were inspected. A fresh generic independent reviewer following the Impeccable contract returned ship with no material fixes; no external QUALITY BAR or comp was supplied, so that comparative ceiling remains unverified. DESIGN.md and its sidecar were matched to actual renders. Four shipping workbench screenshots carry source metadata with unchanged raster chunks. These checks do not imply user aesthetic acceptance.

## Collection management extension, 2026-10-08

Preserve the white/lake-blue system and collection-first composition. Add a compact
collection toolbar with creation, selection, organization and export. Protected
editing and destructive actions use Radix dialogs with named inputs, visible
errors, explicit deletion consent and focus restoration to the collection or
reader. Forms retain capsule controls; mobile targets are at least 44px. Reading
actions stay near their content, and the tasks page distinguishes fetching from
chat-only summaries. Shared-folder synchronization lives in Settings with a
change-count table, side-by-side versions, explicit conflict choices and a final
apply confirmation. Disabled, pending and stale-preview states remain actionable.
This is an extension of the accepted system, with no replacement visual world.
EVIDENCE: Application source `33ff0df5340b31061434deb7e341c612e22feae1` is unchanged
in test-only `f757f33e00a0a3582e4b656865bddd51d3d4f445`. Experience `37774845284`
passed 31 browser tests, 1996 Python / 1 skipped, builds and distributions. Its
42-capture artifact `11549727814` has verified hashes and a 13.64-second recording.
The extension review found one material tag-placeholder contrast issue; its
correction measures 5.21:1 at desktop and 390px, with guidance fully visible.
The independent generic reviewer following the Impeccable contract returned ship
for that fix, with no introduced regressions observed. No external QUALITY BAR or
approved comp was provided; this is not user aesthetic acceptance. DESIGN.md retains
its existing tokens and sidecar with scoped extension prose. Four shipping
screenshots preserve source raster chunks and carry current origin metadata.
The preceding evidence applies to the earlier collection design only.
