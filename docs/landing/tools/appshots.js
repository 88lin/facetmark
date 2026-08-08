/* Render the real web UI (src/facetmark/web) against invented data.

   The same rule as mockshots.js applies and is the reason this file exists at
   all: no real library is ever loaded, because putting somebody's browsing
   history on a public page is not on.

   Where mockshots.js builds rows by hand in `page.evaluate`, this one runs the
   actual `app.js` and lets it render.  Every request the page makes -- the HTML
   shell, the stylesheet, the ES modules, `strings.json`, `/app/boot`, `/quick`,
   `/search`, `/stats` -- is intercepted and fulfilled here, the static ones
   from disk and the API ones from the fixtures below.  Nothing listens on a
   port, no database is opened, and the screenshot therefore cannot drift from
   the shipped CSS or the shipped render path.  It can drift from the *server*,
   which is what the web contract test in tests/test_web.py is for.

   Eight files: {search, library} x {en, zh} x {light, dark}.  The Chinese pages
   get their own captures because the UI itself is translated -- a Chinese
   quickstart illustrated with an English screenshot is the thing this whole
   change was meant to fix.

   Usage:  node docs/landing/tools/appshots.js
*/
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const WEB = path.join(ROOT, 'src', 'facetmark', 'web');
const OUT = path.join(ROOT, 'docs', 'landing', 'assets');
// Tall enough for the whole library census. Rendered on the site inside a
// 780px reading column, so height costs page scroll, not legibility.
const MAX_H = 2600;

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
};

// ------------------------------------------------------------------ fixtures

// Shapes follow SearchResponse.as_dict() / SearchHit.as_dict() / library_stats().
// Values are invented. `took_ms` is a per-stage breakdown, `vectors` is a pair,
// and `via_kind` appears only on expansion rows -- all three are places where a
// plausible-looking but wrong shape would render as blank rather than as an
// error, so they are worth getting right here.

const hit = (o) => ({
  bookmark_id: o.id, url: o.url, title: o.title, score: o.score,
  base_score: o.score, facets: o.facets, ranks: {}, context_boost: 0,
  context_reasons: [], cold: !!o.cold, folder: o.folder, domain: o.domain,
  date_added: o.added, snippet: o.snippet, utility: 0.5,
  content_type: 'article', topics: [],
  ...(o.via ? { via: o.via, via_kind: o.viaKind } : {}),
});

const DAY = 86400;
const NOW = Math.floor(Date.parse('2026-02-11T10:00:00Z') / 1000);

const EN_HITS = [
  hit({
    id: 1, url: 'https://www.sqlite.org/vtab.html',
    title: 'The Virtual Table Mechanism Of SQLite',
    domain: 'sqlite.org', folder: 'reading/storage', score: 0.94,
    facets: ['content', 'lex_seg'], added: NOW - 41 * DAY,
    snippet: 'A virtual table is an object registered with an open SQLite database connection that behaves like a table but calls callback methods instead of reading a B-tree.',
  }),
  hit({
    id: 2, url: 'https://github.com/asg017/sqlite-vec',
    title: 'sqlite-vec: a vector search extension that runs anywhere',
    domain: 'github.com', folder: 'reading/storage', score: 0.88,
    facets: ['content'], added: NOW - 12 * DAY,
    snippet: 'No dependencies, written in C, stores vectors in ordinary tables. Works in the browser, on the edge, and inside your existing database file.',
  }),
  hit({
    id: 3, url: 'https://example.dev/notes/embeddings-on-disk',
    title: 'Keeping embeddings next to the rows they describe',
    domain: 'example.dev', folder: 'reading/storage', score: 0.71,
    facets: ['content', 'intent'], added: NOW - 200 * DAY,
    snippet: 'Two files means two things to back up and two things to get out of sync. One file means neither.',
  }),
  hit({
    id: 4, url: 'https://old.example.net/faiss-quickstart',
    title: 'FAISS quickstart (2019)', cold: true,
    domain: 'old.example.net', folder: 'archive', score: 0.44,
    facets: ['lex_tri'], added: NOW - 1600 * DAY,
    snippet: 'Build an index, add your vectors, search. Requires a separate process and a separate copy of the data.',
  }),
];

const EN_NEAR = [
  hit({
    id: 51, url: 'https://www.sqlite.org/fts5.html', title: 'SQLite FTS5',
    domain: 'sqlite.org', folder: 'reading/storage', score: 0.4,
    facets: [], added: NOW - 41 * DAY, via: 1, viaKind: 'session',
    snippet: 'Full-text search over ordinary content, with a trigram tokenizer for substring and CJK matching.',
  }),
  hit({
    id: 52, url: 'https://example.dev/notes/rrf', title: 'Reciprocal rank fusion, briefly',
    domain: 'example.dev', folder: 'reading/retrieval', score: 0.37,
    facets: [], added: NOW - 40 * DAY, via: 1, viaKind: 'semantic',
    snippet: 'Sum 1/(k + rank) across the lists you have. No score calibration, no tuning.',
  }),
];

const ZH_HITS = [
  hit({
    id: 1, url: 'https://www.sqlite.org/vtab.html',
    title: 'SQLite \u865a\u62df\u8868\u673a\u5236\uff08\u5b98\u65b9\u6587\u6863\uff09',
    domain: 'sqlite.org', folder: '\u9605\u8bfb/\u5b58\u50a8', score: 0.94,
    facets: ['content', 'lex_seg'], added: NOW - 41 * DAY,
    snippet: '\u865a\u62df\u8868\u770b\u8d77\u6765\u50cf\u4e00\u5f20\u666e\u901a\u8868\uff0c\u4f46\u8bfb\u5199\u8d70\u7684\u662f\u4f60\u6ce8\u518c\u7684\u56de\u8c03\uff0c\u800c\u4e0d\u662f B-tree\u3002',
  }),
  hit({
    id: 2, url: 'https://github.com/asg017/sqlite-vec',
    title: 'sqlite-vec\uff1a\u628a\u5411\u91cf\u641c\u7d22\u585e\u8fdb SQLite \u6587\u4ef6\u91cc',
    domain: 'github.com', folder: '\u9605\u8bfb/\u5b58\u50a8', score: 0.88,
    facets: ['content'], added: NOW - 12 * DAY,
    snippet: '\u7eaf C \u5199\u7684\uff0c\u6ca1\u6709\u4f9d\u8d56\uff0c\u5411\u91cf\u5c31\u5b58\u5728\u666e\u901a\u8868\u91cc\u3002\u6d4f\u89c8\u5668\u91cc\u4e5f\u80fd\u8dd1\u3002',
  }),
  hit({
    id: 3, url: 'https://example.dev/notes/embeddings-on-disk',
    title: '\u628a embedding \u548c\u5b83\u63cf\u8ff0\u7684\u90a3\u884c\u653e\u5728\u4e00\u8d77',
    domain: 'example.dev', folder: '\u9605\u8bfb/\u5b58\u50a8', score: 0.71,
    facets: ['content', 'intent'], added: NOW - 200 * DAY,
    snippet: '\u4e24\u4e2a\u6587\u4ef6\u5c31\u662f\u4e24\u4efd\u8981\u5907\u4efd\u3001\u4e24\u4efd\u4f1a\u4e0d\u540c\u6b65\u7684\u4e1c\u897f\u3002\u4e00\u4e2a\u6587\u4ef6\u4e24\u6837\u90fd\u6ca1\u6709\u3002',
  }),
  hit({
    id: 4, url: 'https://old.example.net/faiss-quickstart',
    title: 'FAISS \u5165\u95e8\uff082019 \u5e74\u5b58\u7684\uff09', cold: true,
    domain: 'old.example.net', folder: '\u5f52\u6863', score: 0.44,
    facets: ['lex_tri'], added: NOW - 1600 * DAY,
    snippet: '\u5efa\u7d22\u5f15\u3001\u52a0\u5411\u91cf\u3001\u641c\u3002\u8981\u53e6\u8d77\u4e00\u4e2a\u8fdb\u7a0b\uff0c\u6570\u636e\u4e5f\u8981\u518d\u5b58\u4e00\u4efd\u3002',
  }),
];

const ZH_NEAR = [
  hit({
    id: 51, url: 'https://www.sqlite.org/fts5.html',
    title: 'SQLite FTS5\uff1a\u5168\u6587\u68c0\u7d22',
    domain: 'sqlite.org', folder: '\u9605\u8bfb/\u5b58\u50a8', score: 0.4,
    facets: [], added: NOW - 41 * DAY, via: 1, viaKind: 'session',
    snippet: '\u4e09\u5143\u7ec4\u5206\u8bcd\u5668\u8ba9\u5b50\u4e32\u548c\u4e2d\u6587\u67e5\u8be2\u4e5f\u80fd\u547d\u4e2d\u3002',
  }),
  hit({
    id: 52, url: 'https://example.dev/notes/rrf',
    title: '\u5012\u6570\u6392\u540d\u878d\u5408\uff08RRF\uff09\u7b80\u8bf4',
    domain: 'example.dev', folder: '\u9605\u8bfb/\u68c0\u7d22', score: 0.37,
    facets: [], added: NOW - 40 * DAY, via: 1, viaKind: 'semantic',
    snippet: '\u628a\u624b\u5934\u51e0\u4e2a\u699c\u5355\u7684 1/(k + \u540d\u6b21) \u52a0\u8d77\u6765\u3002\u4e0d\u7528\u5bf9\u5206\u6570\u505a\u6807\u5b9a\u3002',
  }),
];

const searchBody = (q, hits, near) => ({
  query: q, hits, expanded: near,
  understanding: { labels: ['episodic', 'content'], intent: 'recall' },
  config: 'full',
  facet_sizes: { content: 50, lex_seg: 50 },
  facet_confidence: { content: 0.81 },
  context: {}, rescued: [], reranker: null,
  took_ms: { understand: 4, retrieve: 118, fuse: 3, expand: 9 },
  limit: 20, offset: 0, depth: 50, total: 137,
  has_more: true, depth_capped: false,
});

const STATS = {
  bookmarks: 1284, indexable: 1197, privacy_skipped: 87, with_body: 1102,
  enriched: 964, intent_kept: 731, sessions: 213, edges: 4416, domains: 468,
  vectors: [1102, 731], content_vectors_stale: 12,
  queue: { pending: 41, leased: 2, done: 1102, failed: 9 }, queue_waiting: 41,
  edges_by_kind: {
    session: 1902, semantic: 1488, supersession: 96,
    anchor_sibling: 214, same_domain: 716,
  },
  health: {
    alive: 1043, gone: 21, soft_gone: 7, drifted: 14,
    restricted: 5, unreachable: 3, unchecked: 191,
  },
  cold_layer: {
    cold: 148, servable_cold: 121, unservable_cold: 27, never_opened: 806,
    older_than_cutoff: 402, old_and_never_opened: 311, health_unchecked: 191,
  },
};

// -------------------------------------------------------------------- wiring

function staticFile(urlPath) {
  // "/app" is the shell; "/app/static/x" is a file under web/static.
  if (urlPath === '/app') return path.join(WEB, 'index.html');
  const m = urlPath.match(/^\/app\/static\/(.+)$/);
  if (!m) return null;
  const p = path.join(WEB, 'static', m[1]);
  return p.startsWith(path.join(WEB, 'static')) && fs.existsSync(p) ? p : null;
}

async function handle(route, request) {
  const url = new URL(request.url());
  const p = url.pathname;

  const file = staticFile(p);
  if (file) {
    return route.fulfill({
      status: 200,
      contentType: TYPES[path.extname(file)] ?? 'application/octet-stream',
      body: fs.readFileSync(file),
    });
  }

  const json = (body) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });

  if (p === '/app/boot') {
    return json({ version: '1.6.1', paired: true, token: 'shot', reason: '' });
  }
  if (p === '/stats') return json(STATS);
  if (p === '/open') return json({ ok: true });
  if (p === '/quick' || p === '/search') {
    const zh = /[\u4e00-\u9fff]/.test(url.searchParams.get('q') ?? request.postData() ?? '');
    const [hits, near] = zh ? [ZH_HITS, ZH_NEAR] : [EN_HITS, EN_NEAR];
    const q = url.searchParams.get('q') ?? (JSON.parse(request.postData() || '{}').q || '');
    // /quick is lexical only: no expansion group, and no facet beyond the
    // lexical ones, which is what makes the first paint visibly cheaper.
    if (p === '/quick') return json(searchBody(q, hits.slice(0, 3), []));
    return json(searchBody(q, hits, near));
  }
  return route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
}

const QUERIES = {
  en: 'that sqlite thing about storing vectors',
  zh: '\u4e0a\u6b21\u770b\u7684\u90a3\u4e2a sqlite \u5b58\u5411\u91cf\u7684',
};

async function shoot(browser, { view, lang, theme }) {
  const ctx = await browser.newContext({
    viewport: { width: 1180, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: theme,
    locale: lang === 'zh' ? 'zh-CN' : 'en-US',
  });
  await ctx.route('**/*', handle);
  await ctx.addInitScript(
    ([l, th]) => {
      localStorage.setItem('fm-lang', l);
      localStorage.setItem('fm-theme', th);
    },
    [lang, theme],
  );

  const page = await ctx.newPage();
  const q = view === 'search' ? `?q=${encodeURIComponent(QUERIES[lang])}` : '';
  await page.goto(`http://facetmark.test/app${q}#/${view}`, { waitUntil: 'load' });

  // Wait for the thing the shot is of, not for a timeout: the search view is
  // done when the ranked list has replaced the lexical first paint, and the
  // library view when the stat groups have rendered.
  const target = view === 'search' ? '#results li:nth-child(4)' : '#stats .stat-group:nth-of-type(3)';
  await page.waitForSelector(target, { timeout: 15000 });
  await page.waitForTimeout(400); // the 180ms row fade

  // Fit the viewport to the content instead of using fullPage: fullPage
  // re-paints the sticky header at every viewport boundary, so a tall page
  // comes out with the header stamped through the middle of it.
  //
  // Measure the NATURAL height, not the painted one. The shell is a flex
  // column with `min-height: 100vh` and `main { flex: 1 }`, so a page shorter
  // than the window has main stretched to fill it -- measuring that gives back
  // the window height and bakes the stretch into the picture as a gap above
  // the footer. Releasing the stretch for the length of one measurement is the
  // same page seen through a differently sized window, not a different page.
  const h = await page.evaluate(() => {
    const main = document.querySelector('main');
    const min = document.body.style.minHeight;
    const flex = main.style.flex;
    document.body.style.minHeight = '0';
    main.style.flex = 'none';
    const natural = Math.ceil(document.documentElement.scrollHeight);
    document.body.style.minHeight = min;
    main.style.flex = flex;
    return natural;
  });
  // The cap is a tripwire, not a crop: a shot that hits it is truncated
  // mid-content, which is worse than a tall figure. The library view is a
  // census of nine stat groups and is legitimately long.
  if (h > MAX_H) console.warn(`  ! content is ${h}px, capped at ${MAX_H} -- the shot will be cut`);
  await page.setViewportSize({ width: 1180, height: Math.min(h, MAX_H) });
  await page.waitForTimeout(200);

  const name = `app-${view}${lang === 'zh' ? '-zh' : ''}${theme === 'dark' ? '-dark' : ''}.png`;
  await page.screenshot({ path: path.join(OUT, name) });
  await ctx.close();
  return name;
}

(async () => {
  const browser = await chromium.launch();
  for (const view of ['search', 'library']) {
    for (const lang of ['en', 'zh']) {
      for (const theme of ['light', 'dark']) {
        const name = await shoot(browser, { view, lang, theme });
        const kb = fs.statSync(path.join(OUT, name)).size / 1024;
        console.log(`  ${name.padEnd(28)} ${kb.toFixed(0)} KB`);
      }
    }
  }
  await browser.close();
})();
