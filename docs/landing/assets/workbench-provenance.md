# Workbench screenshot provenance

These are actual Facetmark shared React `/app` screenshots, captured by Playwright
on a disposable GitHub Actions runner. They use repository synthetic bookmarks and
controlled API fixtures. No personal bookmarks, browser profiles or generated UI
mockups were used.

- [Capture run 38200196817](https://github.com/88lin/facetmark/actions/runs/38200196817)
- Capture source: `da0b08eef38ba1a3284fa6dfe7fc57c558927c7e`
- [Visual artifact 11725421003](https://github.com/88lin/facetmark/actions/runs/38200196817/artifacts/11725421003)

The collection now has direct original-page title links, separate selection and
Preview controls, multiline summaries in cards and lists, and expansion when text
is actually clipped. A compact status row and an expandable display/batch panel
support scoped summary processing. The white/lake-blue palette, readable type and
searchable vertical categories follow the user's chosen direction.

| Website asset | Source artifact file |
| --- | --- |
| workbench-en-light.png | en-light-1440.png |
| workbench-en-dark.png | en-dark-1440.png |
| workbench-zh-light.png | zh-light-1440.png |
| workbench-zh-dark.png | zh-dark-1440.png |

These four 1440 × 960 matrix captures include the optional reader alongside the
collection. `collection-1366x768.png` in the artifact shows the main collection
without the reader. The four copied PNGs retain identical raster chunks; embedded
metadata records the source commit, run and synthetic-data origin. All **65 capture
hashes** match `provenance.json`. Small local evidence is kept under
`.desktop-build/bookmark-native-38200196817`.

The run passed 45 ordinary browser scenarios plus the separate 200,000-record
browser test. The artifact includes desktop/mobile summaries and display options,
reprocessing confirmation, agent settings, category search, management and sync,
theme/language/viewport variants, and interaction recordings. Fixture screenshots
do not establish real model-account connectivity or installed Windows behavior.

The collection density captures use 1,892 synthetic bookmarks and 295 folders.
At 1366 × 768 the first card starts at 213.4px; the collection viewport is 505.6px
high. Multiline summaries make cards taller than in the previous one-line design.
All five density viewports report no horizontal document overflow; see
`collection-density.json` for the full measurements.

The independent reviewer scored the sole reprocessing-copy finding **resolved**
using the new desktop/mobile screenshots: the count and explanation change with
the reprocessing checkbox. That verdict covers this fix only. Windows validation
is tracked separately in `docs/desktop-validation.md`.

These files replace the prior workbench captures. Eighteen untouched legacy landing
rasters are outside this refresh and retain their existing metadata. No landing
deployment is part of this update.
