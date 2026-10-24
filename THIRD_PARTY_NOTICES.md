# Third-party UI components and fonts

Facetmark uses cmdk 1.1.1 by Paco Coursey under the MIT license. The complete
notice is distributed at `licenses/cmdk.txt` in the shared web application.

Facetmark bundles Inter Variable (Latin) and Noto Sans SC Variable (Chinese)
as local WOFF2 subsets, retaining variable weights and layout features. Sources:
https://github.com/google/fonts/tree/main/ofl/inter and
https://github.com/google/fonts/tree/main/ofl/notosanssc. Both use the SIL Open
Font License 1.1; their complete copyright and license notices ship at
`licenses/Inter-OFL.txt` and `licenses/NotoSansSC-OFL.txt`. Subsetting details are
recorded in `frontend/src/assets/fonts/README.md` in the source repository.

Facetmark uses an adapted ScrollProgress component from [Rare UI](https://rareui.com),
source: https://github.com/swamimalode07/rare-ui/blob/main/components/ui/scroll-progress.tsx.
The adaptation retains Motion for the scroll indicator, uses a native section picker,
and is distributed only as part of the Facetmark application.

Facetmark also uses ReaderOutline, adapted from the Rare UI RailToc component:
https://github.com/swamimalode07/rare-ui/blob/b4de46efe4eb2613e22bb8134b482ed4e0c7736a/public/r/rail-toc.json.
This adaptation retains its container-relative heading tracking and section
navigation, replaces the animated paper plane with a quiet active-section rail,
and is distributed only as part of the Facetmark application. The following
copyright, attribution requirement, and license conditions cover both adaptations.

+MIT + Commons Clause License Condition v1.0 + Attribution

Copyright (c) 2026 Swami Malode

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, and distribute the Software as part of an
application, website, or product, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

Attribution Requirement

Any project that ships any part of the Software must credit Rare UI with a
visible link to https://rareui.com, placed where a visitor or user can find it,
such as a site footer, an about page, a credits screen or a README. The credit
and the copyright notice above must not be removed from the source you copied.

Commons Clause Restriction

You may use this Software, including for any commercial purpose, so long as you
do not sell, sublicense, or redistribute the components themselves, whether
alone, in a bundle, or as a ported version.

No Warranty

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
