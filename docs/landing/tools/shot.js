/* Screenshot one local HTML file at an exact pixel size.
   usage: node shot.js <html-path> <png-path> <width> <height> [scale]

   Kept generic so both ogcard.py and any future fixed-size asset can use it.
   Requires playwright to be resolvable from this directory or any parent. */
const { chromium } = require('playwright');

const [, , src, out, w, h, scale] = process.argv;
if (!src || !out || !w || !h) {
  console.error('usage: node shot.js <html> <png> <width> <height> [scale]');
  process.exit(2);
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: Number(w), height: Number(h) },
    deviceScaleFactor: Number(scale || 1),
  });
  const page = await ctx.newPage();
  await page.goto('file://' + src, { waitUntil: 'load' });
  await page.waitForTimeout(250);
  await page.screenshot({ path: out });
  await browser.close();
  console.log(`${out}  ${w}x${h}@${scale || 1}`);
})();
