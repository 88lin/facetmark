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

FINISH: The direction and implementation are updated for this revision. A fresh finish review and source-matched cloud verification are still required before assigning a new ship verdict. Historical reviews and captures remain historical; they are not evidence that the latest revision has passed. Keep DESIGN.md, the surface contract and shipping asset provenance consistent with the final reviewed result.

VERIFY: Use only the synthetic corpus and cloud build/browser/packaging workflow. Associate captures and test results with the exact source revision. Check the collection hierarchy, natural card heights, real folder shortcuts, command search, normal and focused reading, outline click and keyboard tracking, return-context preservation, model-test ordering, narrow layouts, both themes and edge states in one batched inspection. Consolidate corrections before a bounded confirmation pass. Do not use personal browser data or a local application runtime. This contract records the required checks, not completed test results.
