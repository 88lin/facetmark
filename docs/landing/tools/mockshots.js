/* Render the real extension UI (extension/src/popup.html + options.html, real
   popup.css) against mock data, so the landing page shows the actual layout
   rather than a drawing.  No real library is used: putting somebody's browsing
   history on a public page is not on.

   v3: each capture is written straight to assets at its own aspect ratio and at
   full content height.  The previous version padded every capture onto one
   520x700 canvas, which left the short options page as a small card floating in
   a field of stale band colour.  The .shot CSS frame supplies the border,
   radius and background, so the image does not need to fake one. */
const { chromium } = require('playwright');
const path = require('path');
const ROOT = path.resolve(__dirname, '..', '..', '..');
const SRC = 'file://' + path.join(ROOT, 'extension', 'src') + '/';
const OUT = path.join(ROOT, 'docs', 'landing', 'assets');

const HITS = [
  {
    t: '\u7b7e\u5230\u811a\u672c\uff1a\u81ea\u52a8\u6253\u5361\u7684\u51e0\u79cd\u59ff\u52bf',
    m: 'juejin.cn \u00b7 \u5de5\u5177', chips: ['about', 'asked as'],
    s: '\u7528 headless \u6d4f\u89c8\u5668\u5b9a\u65f6\u89e6\u53d1\u7b7e\u5230\u63a5\u53e3\uff0c\u6ce8\u610f cookie \u8fc7\u671f\u2026\u2026',
  },
  {
    t: 'How I automate check-ins with cron',
    m: 'example.dev', chips: ['words'],
    s: 'A small systemd timer plus a curl one-liner is enough\u2026',
  },
  {
    t: '\u8001\u65e7\u7684\u7b7e\u5230\u9875\u9762\uff08\u5df2\u6253\u4e0d\u5f00\uff09',
    m: 'dead.example', chips: ['substring'], cold: true,
    s: '\u5b58\u6863\u524d\u7684\u5feb\u7167\uff1a\u6bcf\u65e5\u7b7e\u5230\u9886\u79ef\u5206\u2026\u2026',
  },
];
const NEAR = [
  { t: '\u6d4f\u89c8\u5668\u81ea\u52a8\u5316\u4e66\u5355', m: 'books.example' },
  { t: 'cron \u8868\u8fbe\u5f0f\u901f\u67e5', m: 'cheatsheet.dev' },
];

async function fullHeightShot(page, width, path) {
  const h = await page.evaluate(
    () => Math.ceil(document.documentElement.getBoundingClientRect().height));
  await page.setViewportSize({ width, height: h });
  await page.waitForTimeout(180);
  await page.screenshot({ path });
  return h;
}

(async () => {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });

  for (const theme of ['light', 'dark']) {
    const ctx = await browser.newContext({
      viewport: { width: 420, height: 620 }, deviceScaleFactor: 2, colorScheme: theme,
    });
    const page = await ctx.newPage();
    await page.goto(SRC + 'popup.html', { waitUntil: 'load' });
    await page.evaluate(({ hits, near }) => {
      document.getElementById('q').value =
        '\u4e0a\u6b21\u5b58\u7684\u90a3\u4e2a\u7b7e\u5230\u811a\u672c';
      document.getElementById('status').textContent =
        '3 results \u00b7 212 ms \u00b7 episodic + content';
      const ul = document.getElementById('results');
      const row = (h, nb) => {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = '#'; a.className = nb ? 'hit neighbour' : 'hit';
        const t = document.createElement('div'); t.className = 'title'; t.textContent = h.t;
        a.appendChild(t);
        const m = document.createElement('div'); m.className = 'meta';
        m.appendChild(document.createTextNode(h.m));
        for (const c of h.chips || (nb ? ['linked'] : [])) {
          const s = document.createElement('span'); s.className = 'chip'; s.textContent = c;
          m.appendChild(s);
        }
        a.appendChild(m);
        if (h.cold) { const b = document.createElement('span'); b.className = 'badge'; b.textContent = 'cold'; m.appendChild(b); }
        if (h.s) { const sn = document.createElement('div'); sn.className = 'snippet'; sn.textContent = h.s; a.appendChild(sn); }
        li.appendChild(a); return li;
      };
      for (const h of hits) ul.appendChild(row(h, false));
      const g = document.createElement('li'); g.className = 'group';
      g.textContent = 'saved around these \u00b7 ' + near.length; ul.appendChild(g);
      for (const h of near) ul.appendChild(row(h, true));
      document.getElementById('queue').textContent = '3 pages queued';
    }, { hits: HITS, near: NEAR });
    await page.waitForTimeout(250);
    const h = await fullHeightShot(page, 420,
      `${OUT}/popup-mock${theme === 'dark' ? '-dark' : ''}.png`);
    console.log(`popup-${theme}  420x${h}`);
    await ctx.close();
  }

  /* the options page is short and wide; it keeps its own ratio.  options.html
     loads the same popup.css, which has a real prefers-color-scheme block,
     so the dark twin is the actual page, not a recolour. */
  for (const theme of ['light', 'dark']) {
    const ctx = await browser.newContext({
      viewport: { width: 560, height: 560 }, deviceScaleFactor: 2, colorScheme: theme,
    });
    const page = await ctx.newPage();
    await page.goto(SRC + 'options.html', { waitUntil: 'load' });
    await page.evaluate(() => {
      document.getElementById('endpoint').value = 'http://127.0.0.1:8787';
      document.getElementById('token').value = 'fm_7b41c0e9a2d84f13b6e5c07a9d2f8341';
      document.getElementById('channelB').checked = true;
      const s = document.getElementById('state');
      s.className = 'ok';
      s.textContent = 'saved \u00b7 server reachable \u00b7 2,376 pages indexed';
    });
    await page.waitForTimeout(250);
    const oh = await fullHeightShot(
      page, 560, `${OUT}/options${theme === 'dark' ? '-dark' : ''}.png`);
    console.log(`options-${theme}  560x${oh}`);
    await ctx.close();
  }

  await browser.close();
})();
