# Workbench screenshot provenance

These images are screenshots of Facetmark's actual React application, rendered
by Playwright on a disposable GitHub Actions runner. They are not generated
mockups. The corpus is synthetic, authored in `scripts/experience_server.py`,
and contains no personal bookmarks.

Source: https://github.com/88lin/facetmark/actions/runs/37311576521

UI commit: `d618c524ec4f5b0590f867fdd11bea2765791c34`

This is the confirmation batch of the 2026-10-05 redesign. The browser suite
passed 14 tests. Later documentation and result-list scroll assertions do not
change the rendered frontend source.

| Website asset | Source artifact file |
| --- | --- |
| workbench-en-light.png | frontend/screenshots/en-light-1440.png |
| workbench-en-dark.png | frontend/screenshots/en-dark-1440.png |
| workbench-zh-light.png | frontend/screenshots/zh-light-1440.png |
| workbench-zh-dark.png | frontend/screenshots/zh-dark-1440.png |

Viewport: 1440 × 960. Artifact: `facetmark-visual-evidence` (ID `11345718546`).
Each PNG embeds the source commit/run and synthetic-data origin. The artifact's
`provenance.json` records dimensions and SHA-256 hashes; it also contains the
recorded `facetmark-reading.mp4` / `.webm` interaction, narrow windows, dark
theme, long-title/loading/empty/failure cases and platform-font diagnostics.

Rendered pixels are unchanged from the small artifact; the website copies also
embed the same origin in Impeccable's provenance field. No mockup image, personal
bookmark, browser profile or generated task/service state was used.
