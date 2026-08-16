# Asset generators

Everything in `../assets/` is generated. These scripts are how.

They are not part of the build (`build.py` needs nothing but Python), and CI
never runs them — the PNGs are committed. They exist so the assets can be
regenerated instead of being redrawn by hand, and so it is checkable that no
real browsing history ever ends up on a public page.

    # the extension frames still need node
    npm i playwright && npx playwright install chromium
    node tools/mockshots.js            # popup-mock.png, popup-mock-dark.png, options.png

    # the rest are Python; run them from the repository root
    pip install playwright && python -m playwright install chromium
    python docs/landing/tools/appshots.py   # app-{search,library}[-zh][-dark].png
    python docs/landing/tools/ogcard.py     # og-en.png, og-zh.png

| script | output | notes |
|---|---|---|
| `mockshots.js` | the three extension frames | loads the real `extension/src/popup.html` and `options.html` against mock data, captured at full content height and native aspect ratio |
| `appshots.py` | the eight `/app` frames | boots the real server on an offline `facetmark demo` corpus and photographs it at 1440px |
| `ogcard.py` | the two 1200×630 link previews | reads its colours from `style.css` and its words from `content_{en,zh}.py`, so the card cannot drift from the page it advertises |
| `shot.js` | — | generic "screenshot this file at exactly W×H"; kept for one-off captures |

`appshots.py` used to be `appshots.js`, and the swap is worth explaining
because it reverses a decision this file used to argue for. The node version
answered every request the page made -- `/app/boot`, `/quick`, `/search`,
`/stats` -- out of a table of invented JSON, on the grounds that no database
should be in the loop. The trouble is that a fixture table is a second copy of
the server's response shapes, and a second copy drifts: the picture then shows
whatever that table says rather than whatever the server says.

`facetmark demo` removes the reason for the fixtures. It builds a synthetic
sixty-page library offline, deterministically, with no API key and no network
call — so the real server can be booted and photographed without a single real
page ever being fetched. The rule that has always governed this directory is
unchanged, and the frames are now produced by the shipped renderer against the
shipped routes.

`mockshots.js` stays in node and stays fixture-driven, because the extension
popup genuinely has no server to boot: it loads `popup.html` from `file://`
and builds its rows by hand inside `page.evaluate`.

The popup mock data is invented. It has to be: putting a real library on a
public page is not on. The layout, class names and label strings are the real
ones from `extension/src/popup.ts`, so the frames stay honest about what the
extension looks like — and the captions on the page say they are previews.

Neither generator is a test. What stops the shipped pages from regressing is
`scripts/browser_check.py`, which drives the same demo corpus in the same
browser and asserts geometry, focus, contrast and console silence; it runs in
CI as the `browser` job.
