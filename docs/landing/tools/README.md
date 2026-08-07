# Asset generators

Everything in `../assets/` is generated. These scripts are how.

They are not part of the build (`build.py` needs nothing but Python), and CI
never runs them — the PNGs are committed. They exist so the assets can be
regenerated instead of being redrawn by hand, and so it is checkable that no
real browsing history ever ends up on a public page.

    npm i playwright && npx playwright install chromium

    node tools/mockshots.js      # popup-mock.png, popup-mock-dark.png, options.png
    python3 tools/ogcard.py      # og-en.png, og-zh.png

Run both from `docs/landing/`.

| script | output | notes |
|---|---|---|
| `mockshots.js` | the three extension frames | loads the real `extension/src/popup.html` and `options.html` against mock data, captured at full content height and native aspect ratio |
| `ogcard.py` | the two 1200×630 link previews | reads its colours from `style.css` and its words from `content_{en,zh}.py`, so the card cannot drift from the page it advertises |
| `shot.js` | — | generic "screenshot this file at exactly W×H", used by `ogcard.py` |

The popup mock data is invented. It has to be: putting a real library on a
public page is not on. The layout, class names and label strings are the real
ones from `extension/src/popup.ts`, so the frames stay honest about what the
extension looks like — and the captions on the page say they are previews.
