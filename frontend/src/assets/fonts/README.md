# Bundled interface fonts

- `inter-latin.woff2`: Inter variable, from Google Fonts' `ofl/inter/Inter[opsz,wght].ttf`.
  Latin, Latin extended, punctuation, currency and arrow subsets; OFL license beside it.
- `noto-sans-sc.woff2`: Noto Sans SC variable, derived from the installed upstream
  `NotoSansSC-VF.ttf`. Includes basic/extended CJK, compatibility ideographs,
  Bopomofo, punctuation and full-width forms. OFL license beside it.
- `smiley-sans.woff2`: Smiley Sans v2.0.1, unmodified
  `SmileySans-Oblique.ttf.woff2` from atelier-anchor's official release archive.
  https://github.com/atelier-anchor/smiley-sans/releases/tag/v2.0.1
  OFL license beside it. Used only by the collection heading, not controls or body.

Both files were compressed with fontTools 4.62.1 `subset --flavor=woff2`, retaining
all layout features and variable weights. The CSS family names are local aliases.
The application serves these from its own bundle and needs no font CDN or installed
Chinese font. Other Unicode ranges can use the declared platform fallbacks.
