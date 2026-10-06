# Workbench screenshot provenance

These images are screenshots of Facetmark's actual React application, rendered
by Playwright on a disposable GitHub Actions runner. They are not generated
mockups. The corpus is synthetic, authored in `scripts/experience_server.py`,
and contains no personal bookmarks.

Source: https://github.com/88lin/facetmark/actions/runs/37410551657

Capture commit: `d6597e9a488bf434afe3121cd5d68587c9b3140f`

Application source: `90f551b38bd1ee15833d40c97cf1e2cf93c082fd`

This is the confirmation batch of the 2026-10-06 structural rebuild after the
user rejected the previous permanent-column composition. The browser suite
passed 14 tests. The capture revision changes only test activation of a moving
control; later documentation and desktop smoke changes leave UI source unchanged.

| Website asset | Source artifact file |
| --- | --- |
| workbench-en-light.png | frontend/screenshots/en-light-1440.png |
| workbench-en-dark.png | frontend/screenshots/en-dark-1440.png |
| workbench-zh-light.png | frontend/screenshots/zh-light-1440.png |
| workbench-zh-dark.png | frontend/screenshots/zh-dark-1440.png |

Viewport: 1440 × 960. Artifact: `facetmark-visual-evidence` (ID `11389029798`).
Each PNG embeds the source commit/run and synthetic-data origin. The artifact's
`provenance.json` records dimensions and SHA-256 hashes; it also contains the
recorded `facetmark-reading.mp4` / `.webm` interaction, narrow windows, dark
theme, long-title/loading/empty/failure cases and platform-font diagnostics.

Rendered pixels are unchanged from the small artifact; the website copies also
embed the same origin in Impeccable's provenance field. No mockup image, personal
bookmark, browser profile or generated task/service state was used.
