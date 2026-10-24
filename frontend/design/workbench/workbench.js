/* Isolated, in-memory fixtures. No backend, storage or remote assets. */
'use strict';

const icons = {
  collection: '<rect x="3" y="3" width="7" height="7" rx="2" fill="currentColor" opacity=".22"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2" fill="currentColor" opacity=".22"/>',
  tasks: '<rect x="5" y="4" width="14" height="17" rx="3" fill="currentColor" opacity=".15"/><path d="M9 3h6v4H9zM8 12l2 2 5-5M9 18h6"/>',
  settings: '<path d="M4 7h16M4 17h16"/><rect x="7" y="4" width="4" height="6" rx="2" fill="currentColor"/><rect x="14" y="14" width="4" height="6" rx="2" fill="currentColor" opacity=".5"/>',
  moon: '<path d="M20 14A8.5 8.5 0 0 1 10 4a8.5 8.5 0 1 0 10 10Z" fill="currentColor" opacity=".18"/><path d="M20 14A8.5 8.5 0 0 1 10 4a8.5 8.5 0 1 0 10 10Z"/>',
  sun: '<circle cx="12" cy="12" r="4" fill="currentColor" opacity=".3"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  arrow: '<path d="M5 19 19 5M7 5h12v12"/>',
  folder: '<path d="M3 8V6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" fill="currentColor" opacity=".2"/><path d="M3 9h18M3 9v9a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9M3 9V6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2"/>',
  chevron: '<path d="m7 10 5 5 5-5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  sort: '<path d="M8 4v16m-3-3 3 3 3-3M14 6h6m-6 6h4m-4 6h2"/>',
  grid: '<rect x="4" y="4" width="6" height="6" rx="1.5"/><rect x="14" y="4" width="6" height="6" rx="1.5"/><rect x="4" y="14" width="6" height="6" rx="1.5"/><rect x="14" y="14" width="6" height="6" rx="1.5"/>',
  list: '<path d="M9 5h11M9 12h11M9 19h11"/><path d="M4 5h.1M4 12h.1M4 19h.1" stroke-width="3"/>',
  bookmark: '<path d="M6 4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v17l-6-4-6 4Z" fill="currentColor" opacity=".18"/><path d="M6 4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v17l-6-4-6 4Z"/>',
  spark: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z" fill="currentColor" opacity=".2"/><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>',
  import: '<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>',
  back: '<path d="m10 5-7 7 7 7M3 12h18"/>',
  external: '<path d="M14 3h7v7m0-7L10 14M10 4H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-5"/>',
  read: '<path d="M3 5c4-2 7-1 9 1 2-2 5-3 9-1v14c-4-2-7-1-9 1-2-2-5-3-9-1Z" fill="currentColor" opacity=".15"/><path d="M12 6v14M3 5c4-2 7-1 9 1 2-2 5-3 9-1v14c-4-2-7-1-9 1-2-2-5-3-9-1Z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  warning: '<path d="m12 3 10 18H2Z" fill="currentColor" opacity=".15"/><path d="m12 3 10 18H2Zm0 6v5m0 3h.01"/>',
};
const emblems = {
  all: '<rect x="18" y="15" width="39" height="51" rx="8" fill="currentColor" opacity=".22" transform="rotate(-13 37 40)"/><path d="M42 12h31a7 7 0 0 1 7 7v48L58 55 35 67V19a7 7 0 0 1 7-7Z" fill="currentColor" opacity=".68"/><path d="M47 29h21M47 39h14" stroke="var(--tile-bg,#fff)" stroke-width="3" stroke-linecap="round"/>',
  design: '<rect x="16" y="15" width="51" height="49" rx="10" fill="currentColor" opacity=".18" transform="rotate(-10 40 40)"/><rect x="29" y="22" width="51" height="43" rx="9" fill="currentColor" opacity=".38"/><circle cx="45" cy="39" r="7" fill="currentColor" opacity=".85"/><path d="m35 57 17-14 20 14" fill="currentColor" opacity=".65"/>',
  code: '<rect x="14" y="17" width="68" height="47" rx="11" fill="currentColor" opacity=".18"/><path d="m37 32-11 9 11 9m23-18 11 9-11 9m-6-21-9 25" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity=".7"/>',
  reading: '<path d="M16 20q16-7 32 3 16-10 32-3v43q-16-7-32 3-16-10-32-3Z" fill="currentColor" opacity=".25"/><path d="M48 23v43M25 32l14 3M25 42l14 3m18-10 14-3m-14 13 14-3" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" opacity=".65"/>',
};
const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
const escapeHTML = value => String(value).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.bookmark}</svg>`;
function hydrateIcons(scope = document) {
  $$('[data-icon]', scope).forEach(node => { node.innerHTML = icon(node.dataset.icon); });
  $$('[data-emblem]', scope).forEach(node => { node.innerHTML = `<svg viewBox="0 0 96 80" aria-hidden="true">${emblems[node.dataset.emblem] || emblems.all}</svg>`; });
}

const bookmarks = [
  {id:101,title:'让导航退后一步，让内容走到眼前',url:'https://design.example.com/navigation',domain:'design.example.com',mark:'D',folder:'设计 / 界面',category:'设计',tone:'peach',tag:'界面设计',status:'done',date:'2026-10-19',summary:'导航的意义，是让人知道自己在哪里、能去哪里。把高频入口留在视线内，把次要选项收进合适的层级，给内容更多空间。',body:['人进入一个收藏工具，通常带着一个很具体的念头：找回昨天看到的文章，或翻翻自己积累的设计参考。界面应该帮助这个念头顺畅地发生。','导航不需要占据整个画面的重心。稳定的搜索位置、清楚的目录路径和始终可见的原文入口，比增加更多入口更有用。','收起目录后，筛选条件仍需要被看见。阅读返回时，搜索、滚动位置和选中的条目也应该保持原样。']},
  {id:102,title:'好的微交互，是恰到好处的回应',url:'https://notes.example.com/micro-interactions',domain:'notes.example.com',mark:'N',folder:'设计 / 界面',category:'设计',tone:'blue',tag:'交互细节',status:'done',date:'2026-10-18',summary:'从按下按钮到打开阅读，动效应解释变化的来源与去向。及时的状态反馈、可打断的过渡，以及减少动态效果的替代方案同样重要。',body:['一次轻巧的按压反馈，告诉人操作已经被接收。一个从选中内容展开的阅读面板，帮助人理解自己进入了哪个空间。','不要为了播放完动画让用户等待。连续点击、快速返回或切换显示方式时，界面应始终服从最新的操作。','减少动态效果不是减少信息。可以停止位移与缩放，保留清楚的选中、焦点和状态提示。']},
  {id:103,title:'从一张椅子开始，观察日常的形状',url:'https://studio.example.com/everyday-forms',domain:'studio.example.com',mark:'S',folder:'设计 / 灵感',category:'设计',tone:'lilac',tag:'灵感收集',status:'pending',date:'2026-10-17',summary:'还没有生成摘要。已保存的正文摘录可以先读，也可以直接打开原网页。',body:['观察身边物件的边缘、连接与比例，会发现很多不曾注意的设计。椅背的弧度回应身体，扶手的位置回应动作。','把这些观察保存下来，比较它们为什么让人感到轻巧、稳定或亲近。设计的素材往往就藏在日常。']},
  {id:104,title:'用 CSS Grid 构建随内容生长的布局',url:'https://code.example.com/css-grid',domain:'code.example.com',mark:'C',folder:'开发 / 前端',category:'开发',tone:'blue',tag:'CSS · 布局',status:'done',date:'2026-10-16',summary:'网格应该适应内容，而不是让内容迁就固定宽度。结合 minmax、合适的断点与真实长文本，建立从桌面到窄屏都可靠的布局。',body:['先观察内容的自然尺寸，再决定列的数量。长标题、站点名称和可访问的操作目标，都是布局的真实约束。','紧凑视图可以提高扫描效率，但不能为了省空间隐藏选择控件和原文入口。无论窗口宽度如何，核心操作都应该可以到达。']},
  {id:105,title:'收藏之后，如何让知识重新流动？',url:'https://read.example.com/knowledge',domain:'read.example.com',mark:'R',folder:'阅读 / 知识管理',category:'阅读',tone:'rose',tag:'阅读笔记',status:'pending',date:'2026-10-15',summary:'还没有生成摘要。比起不断积累，给旧收藏留一次重新阅读的机会。',body:['收藏是一个开始，不是阅读的终点。重新遇见一条旧收藏时，试着问：当时为什么留下它？它和现在的问题有什么关系？','不必为每篇文章建立复杂的分类。保留足够的线索，让搜索能找回它，再在需要时认真阅读。']},
  {id:106,title:'给信息留白，也给自己留一点余地',url:'https://journal.example.com/space',domain:'journal.example.com',mark:'J',folder:'',category:'',tone:'grey',tag:'待整理',status:'failed',date:'2026-10-14',summary:'上次摘要生成未完成：示例连接超时。已保存的正文仍可阅读，原网页也可以直接访问。',body:['信息并不是越多越好。适当的间隔让标题、摘要与操作各自有位置，也让眼睛有时间找到重点。','这条合成收藏演示了失败状态：失败的只是摘要生成，已经保存的内容和原网页链接仍然存在。']},
];
const state = {category:'all',folder:null,status:'all',query:'',sort:'newest',view:'grid',selected:new Set()};
const folders = ['设计 / 界面','设计 / 灵感','开发 / 前端','阅读 / 知识管理',''];
const statusLabel = {done:'AI 摘要',pending:'待生成摘要',failed:'生成失败'};
const statusIcon = {done:'spark',pending:'clock',failed:'warning'};
const announce = message => { $('#live-status').textContent = message; };
let composing = false;

function matchingRows(includeStatus = true) {
  const query = state.query.trim().toLocaleLowerCase();
  return bookmarks.filter(row =>
    (state.category === 'all' || row.category === state.category) &&
    (state.folder === null || row.folder === state.folder) &&
    (!includeStatus || state.status === 'all' || row.status === state.status) &&
    (!query || [row.title,row.domain,row.summary,row.folder,row.tag,...row.body].join(' ').toLocaleLowerCase().includes(query))
  ).sort((a,b) => state.sort === 'title' ? a.title.localeCompare(b.title,'zh-CN') : state.sort === 'domain' ? a.domain.localeCompare(b.domain) : state.sort === 'oldest' ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));
}

function card(row) {
  return `<article class="bookmark-card tone-${row.tone}${state.selected.has(row.id) ? ' is-selected' : ''}" data-bookmark="${row.id}">
    <div class="card-header"><span class="site-monogram" aria-hidden="true">${row.mark}</span><div class="source-copy"><span class="source-domain">${row.domain}</span><time datetime="${row.date}">${row.date.replaceAll('-','.')} 收藏</time></div><label class="bookmark-select"><input type="checkbox" data-select="${row.id}" aria-label="选择：${escapeHTML(row.title)}" ${state.selected.has(row.id) ? 'checked' : ''}></label></div>
    <div class="card-body"><a class="bookmark-title" href="${row.url}" target="_blank" rel="noopener noreferrer">${row.title}</a><p class="bookmark-description">${row.summary}</p><div class="card-metadata"><span class="summary-state ${row.status}">${icon(statusIcon[row.status])}${statusLabel[row.status]}</span><span class="card-tag">${row.tag}</span></div></div>
    <div class="card-footer"><span class="card-folder" title="${row.folder || '未分类'}">${icon('folder')}<span>${row.folder || '未分类'}</span></span><div class="card-buttons"><button class="card-preview" data-preview="${row.id}" aria-label="阅读：${escapeHTML(row.title)}">${icon('read')}阅读</button><a class="card-external" href="${row.url}" target="_blank" rel="noopener noreferrer" aria-label="打开原网页：${escapeHTML(row.title)}" title="打开原网页">${icon('external')}</a></div></div>
  </article>`;
}

function updateSelection() {
  const count = state.selected.size;
  $('#selection-bar').hidden = count === 0;
  $('#selection-count').textContent = count;
  $$('[data-select]').forEach(input => {
    input.checked = state.selected.has(Number(input.dataset.select));
    input.closest('.bookmark-card').classList.toggle('is-selected', input.checked);
  });
}

function render() {
  const rows = matchingRows();
  const scope = matchingRows(false);
  $('#bookmark-grid').innerHTML = rows.map(card).join('');
  $('#bookmark-grid').classList.toggle('list-view', state.view === 'list');
  $('#result-count').textContent = rows.length;
  $('#collection-title').textContent = state.folder !== null ? (state.folder || '未分类') : state.category === 'all' ? '全部收藏' : state.category;
  $('#empty-results').hidden = rows.length > 0;
  $('#pagination-label').textContent = `共 ${rows.length} 条收藏，已全部显示`;
  $('#clear-filters').hidden = state.category === 'all' && state.folder === null && state.status === 'all' && !state.query;
  $('#search-clear').hidden = !$('#search-input').value;
  $('#search-shortcut').hidden = Boolean($('#search-input').value);
  $$('[data-category]').forEach(button => {
    const active = state.folder === null && button.dataset.category === state.category;
    button.classList.toggle('is-current',active);
    button.setAttribute('aria-pressed',String(active));
  });
  $$('[data-status]').forEach(button => {
    const active = button.dataset.status === state.status;
    button.classList.toggle('active',active);
    button.setAttribute('aria-pressed',String(active));
    $('[data-count]',button).textContent = button.dataset.status === 'all' ? scope.length : scope.filter(row => row.status === button.dataset.status).length;
  });
  updateSelection();
  announce(`显示 ${rows.length} 条收藏${state.selected.size ? `，共已选择 ${state.selected.size} 条` : ''}`);
}

function clearFilters() {
  Object.assign(state,{category:'all',folder:null,status:'all',query:''});
  $('#search-input').value = '';
  render();
}

function renderFolders() {
  const query = $('#folder-search').value.trim().toLocaleLowerCase();
  const visible = folders.filter(folder => (folder || '未分类').toLocaleLowerCase().includes(query));
  $('#directory-items').innerHTML = visible.map(folder => `<button class="directory-item${state.folder === folder ? ' active' : ''}" data-folder="${folder}" aria-pressed="${state.folder === folder}">${icon('folder')}<span>${folder ? folder.split(' / ').at(-1) : '未分类'}<small>${folder || '没有指定目录'}</small></span><span class="folder-count">${bookmarks.filter(row => row.folder === folder).length}</span></button>`).join('') || '<p class="directory-empty">没有匹配的目录，试试更短的名称。</p>';
  $('.directory-note').textContent = `显示 ${visible.length} / ${folders.length} 个目录，包含未分类`;
}

function closeDirectory(restoreFocus = false) {
  $('#directory-popover').hidden = true;
  $('#directory-toggle').setAttribute('aria-expanded','false');
  if (restoreFocus) $('#directory-toggle').focus({preventScroll:true});
}

function setupDialog(dialog, closeButton) {
  let returnTarget;
  closeButton.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    if (returnTarget?.isConnected) returnTarget.focus({preventScroll:true});
  });
  return opener => {
    returnTarget = opener || document.activeElement;
    closeDirectory();
    if (!dialog.open) dialog.showModal();
  };
}
const showReader = setupDialog($('#reader-dialog'),$('#reader-close'));
const showAction = setupDialog($('#action-dialog'),$('#action-close'));

function openReader(id, opener) {
  const row = bookmarks.find(row => row.id === id);
  if (!row) return;
  $('#reader-title').textContent = row.title;
  $('#reader-context').textContent = row.folder || '未分类';
  $('#reader-original').href = row.url;
  $('#reader-source').innerHTML = `<span class="site-monogram" aria-hidden="true">${row.mark}</span><span>${row.domain}</span>`;
  $('#reader-meta').textContent = `${row.date.replaceAll('-','.')} 收藏 · ${row.tag}`;
  $('#reader-summary-label').textContent = statusLabel[row.status];
  $('#reader-summary-text').textContent = row.summary;
  $('#reader-body').innerHTML = row.body.map(text => `<p>${text}</p>`).join('');
  $('.reader-article').scrollTop = 0;
  $$('.reader-outline a').forEach((link,index) => link.classList.toggle('active',index === 0));
  showReader(opener);
}

function action(title, content, opener) {
  $('#action-title').textContent = title;
  $('#action-content').innerHTML = content;
  hydrateIcons($('#action-content'));
  showAction(opener);
}
const disclosure = '<p class="action-disclosure">这是交互原型，使用合成收藏。操作不会改动你的收藏，也不会连接模型服务。</p>';
const selectedNames = () => `<ul class="action-list">${bookmarks.filter(row => state.selected.has(row.id)).map(row => `<li>${row.title}</li>`).join('')}</ul>`;

$('#bookmark-grid').addEventListener('change',event => {
  const input = event.target.closest('[data-select]');
  if (!input) return;
  const id = Number(input.dataset.select);
  if (input.checked) state.selected.add(id); else state.selected.delete(id);
  updateSelection();
  announce(`已选择 ${state.selected.size} 条收藏`);
});
$('#bookmark-grid').addEventListener('click',event => {
  const button = event.target.closest('[data-preview]');
  if (button) openReader(Number(button.dataset.preview),button);
});
$('#search-input').addEventListener('compositionstart',() => { composing = true; });
$('#search-input').addEventListener('compositionend',() => { composing = false; state.query = $('#search-input').value; render(); });
$('#search-input').addEventListener('input',event => {
  if (composing || event.isComposing) return;
  state.query = event.target.value;
  render();
});
$('#search-form').addEventListener('submit',event => {
  event.preventDefault();
  if (!composing) { state.query = $('#search-input').value; render(); }
});
$('#search-clear').addEventListener('click',() => { state.query = ''; $('#search-input').value = ''; render(); $('#search-input').focus(); });
$('#clear-filters').addEventListener('click',() => { clearFilters(); $('#search-input').focus(); });
$('#empty-clear').addEventListener('click',() => { clearFilters(); $('#search-input').focus(); });
$$('[data-category]').forEach(button => button.addEventListener('click',() => {
  state.category = button.dataset.category; state.folder = null; render();
}));
$$('[data-status]').forEach(button => button.addEventListener('click',() => { state.status = button.dataset.status; render(); }));
$('#sort-order').addEventListener('change',event => { state.sort = event.target.value; render(); });
for (const view of ['grid','list']) {
  $(`#view-${view}`).addEventListener('click',() => {
    state.view = view;
    for (const name of ['grid','list']) {
      $(`#view-${name}`).classList.toggle('active',view === name);
      $(`#view-${name}`).setAttribute('aria-pressed',String(view === name));
    }
    render();
  });
}
$('#theme-toggle').addEventListener('click',() => {
  const dark = document.documentElement.dataset.theme !== 'dark';
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  $('#theme-toggle').setAttribute('aria-label',dark ? '切换为亮色' : '切换为深色');
  $('#theme-toggle').innerHTML = icon(dark ? 'sun' : 'moon');
});
$('#directory-toggle').addEventListener('click',() => {
  if (!$('#directory-popover').hidden) { closeDirectory(); return; }
  renderFolders();
  $('#directory-popover').hidden = false;
  $('#directory-toggle').setAttribute('aria-expanded','true');
  $('#folder-search').focus();
});
$('#directory-close').addEventListener('click',() => closeDirectory(true));
$('#folder-search').addEventListener('input',renderFolders);
$('#directory-items').addEventListener('click',event => {
  const button = event.target.closest('[data-folder]');
  if (!button) return;
  state.folder = button.dataset.folder; state.category = 'all'; render(); closeDirectory(true);
});
document.addEventListener('pointerdown',event => {
  if (!event.target.closest('.directory-anchor')) closeDirectory();
});
document.addEventListener('keydown',event => {
  if (event.isComposing) return;
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k' && !document.querySelector('dialog[open]')) {
    event.preventDefault(); closeDirectory(); $('#search-input').focus();
  }
  if (event.key === 'Escape' && !$('#directory-popover').hidden) { event.preventDefault(); closeDirectory(true); }
});
$('#clear-selection').addEventListener('click',() => {
  const first = $('[data-select]:checked');
  state.selected.clear(); updateSelection(); announce('已清空选择');
  (first || $('#search-input')).focus({preventScroll:true});
});
$$('.reader-outline a').forEach(link => link.addEventListener('click',event => {
  event.preventDefault();
  const target = $(link.getAttribute('href'));
  $('.reader-article').scrollTo({top:target.offsetTop - $('.reader-article').offsetTop - 24,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  $$('.reader-outline a').forEach(item => item.classList.toggle('active',item === link));
}));
$('#add-bookmark').addEventListener('click',event => {
  action('新增收藏',`${disclosure}<form id="demo-add"><label>网页地址<input type="url" name="url" placeholder="https://example.com/article" required></label><label>标题<input name="title" placeholder="给这条收藏起个名字" required maxlength="200"></label><label>收藏目录<select name="folder">${folders.map(folder => `<option>${folder || '未分类'}</option>`).join('')}</select></label><button class="button primary" type="submit">检查填写内容</button><p class="action-feedback" role="status"></p></form>`,event.currentTarget);
  $('#demo-add').addEventListener('submit',event => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const url = new URL(data.get('url'));
    $('.action-feedback').textContent = !['https:','http:'].includes(url.protocol) ? '请输入以 https:// 或 http:// 开头的网页地址。' : `填写有效：“${data.get('title')}”。原型不保存此收藏。`;
  });
});
$('#selection-summary').addEventListener('click',event => {
  action('生成摘要',`<p>范围：明确选择的 ${state.selected.size} 条收藏，包含当前筛选之外的选择。</p>${selectedNames()}<p>正式应用会在确认前展示服务与模型，并说明发送的标题、网址和提取正文。模型选择、测试与保存会在下一阶段接入。</p>${disclosure}`,event.currentTarget);
});
$('#selection-move').addEventListener('click',event => {
  action('移动所选收藏',`<p>选择 ${state.selected.size} 条收藏的目标目录。</p>${selectedNames()}<form id="demo-move"><label>目标目录<select>${folders.map(folder => `<option>${folder || '未分类'}</option>`).join('')}</select></label>${disclosure}<button class="button primary" type="submit">预览移动范围</button><p class="action-feedback" role="status"></p></form>`,event.currentTarget);
  $('#demo-move').addEventListener('submit',event => { event.preventDefault(); $('.action-feedback').textContent = `将 ${state.selected.size} 条所选收藏移至“${$('#demo-move select').value}”。原型未执行移动。`; });
});
$('#selection-export').addEventListener('click',event => {
  action('导出所选收藏',`<p>范围：${state.selected.size} 条所选合成收藏。可以下载 JSON，检查原型中的实际字段。</p>${disclosure}<button class="button primary" id="download-demo">下载合成收藏 JSON</button><p class="action-feedback" role="status"></p>`,event.currentTarget);
  $('#download-demo').addEventListener('click',() => {
    const payload = {kind:'Facetmark synthetic design fixture, not a production backup',bookmarks:bookmarks.filter(row => state.selected.has(row.id))};
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'facetmark-synthetic-selection.json'; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url),1000);
    $('.action-feedback').textContent = '已生成所选合成收藏的 JSON 文件。';
  });
});
$$('[data-route]').forEach(button => button.addEventListener('click',() => {
  if (button.dataset.route === 'collection') { closeDirectory(); $('#collection').focus({preventScroll:true}); return; }
  if (button.dataset.route === 'tasks') action('任务',`<div class="task-empty"><span data-icon="tasks"></span><h3>这份原型没有运行中的任务</h3><p>正式应用会展示每次任务的范围、进度与恢复入口。当前只演示收藏主界面的交互。</p></div>${disclosure}`,button);
  else action('设置',`<div class="settings-row"><span data-icon="spark"></span><span>摘要连接<small>发现模型 → 选择 → 测试 → 保存</small></span><span class="settings-badge">待接入</span></div><div class="settings-row"><span data-icon="folder"></span><span>导入与同步<small>保留只读导入与变更预览</small></span><span class="settings-badge">待接入</span></div>${disclosure}`,button);
}));
hydrateIcons();
render();
