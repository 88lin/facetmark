import {useCallback, useEffect, useRef, useState} from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import {ArrowDown, ArrowLeft, ArrowRight, Bookmark as BookmarkIcon, Check, ChevronRight, Clock3, ExternalLink, FileText, Folder, Globe2, Import, Layers3, LoaderCircle, Menu, Moon, PanelRightClose, Search, Settings2, Sparkles, Sun, Tags, WifiOff, X} from 'lucide-react';
import {api, ApiError, post, query, safeUrl, setToken, type Bookmark, type Job, type Page, type Setup} from './api';
import {Locale, useText, type Language} from './locale';
import SetupFlow, {Importer} from './Setup';
import {ExtensionSettings, Models} from './Settings';
import {Tasks} from './Tasks';

type View = 'library'|'sessions'|'tasks'|'settings'|'setup'|'import';
type Facet = {value:string;count:number};
type Filters = {folder?:string;tag?:string;domain?:string;session?:number};
type Session = {session_id:number;label:string;started_at:number;size:number};
const remember = (key:string, value?:string) => { try {if(value!==undefined)localStorage.setItem(key,value);return localStorage.getItem(key);} catch{return null;} };

export default function App() {
  const [language,setLanguage] = useState<Language>(()=>remember('fm-language')==='en'?'en':'zh');
  const [theme,setTheme] = useState(()=>remember('fm-theme') || 'light');
  useEffect(()=>{document.documentElement.lang=language==='zh'?'zh-CN':'en';remember('fm-language',language);},[language]);
  useEffect(()=>{document.documentElement.dataset.theme=theme;remember('fm-theme',theme);},[theme]);
  return <Locale.Provider value={language}><Workbench language={language} theme={theme} setLanguage={setLanguage} setTheme={setTheme}/></Locale.Provider>;
}

function Workbench({language,theme,setLanguage,setTheme}: {language:Language;theme:string;setLanguage:(l:Language)=>void;setTheme:(t:string)=>void}) {
  const t=useText();const [paired,setPaired]=useState(false);const [pairingRequired,setPairingRequired]=useState(false);const [manualToken,setManualToken]=useState('');
  const [view,setView]=useState<View>('library');const [navOpen,setNavOpen]=useState(false);const [setup,setSetup]=useState<Setup|null>(null);const [job,setJob]=useState<Job>({state:'idle'});const [adminAvailable,setAdminAvailable]=useState(true);
  const [facets,setFacets]=useState<Record<string,Facet[]>>({});const [filters,setFilters]=useState<Filters>({});
  const [input,setInput]=useState('');const [search,setSearch]=useState('');const [offset,setOffset]=useState(0);const [depth,setDepth]=useState<number>();
  const [page,setPage]=useState<Page|null>(null);const [loading,setLoading]=useState(false);const [error,setError]=useState('');const [connectionError,setConnectionError]=useState('');
  const [selected,setSelected]=useState<number|null>(null);const [preview,setPreview]=useState<Bookmark|null>(null);const [previewError,setPreviewError]=useState('');
  const [related,setRelated]=useState<Bookmark[]>([]);const [drawer,setDrawer]=useState(()=>matchMedia('(max-width: 1119px)').matches);const [previewTab,setPreviewTab]=useState('body');
  const [sessions,setSessions]=useState<Session[]>([]);const [sessionsMore,setSessionsMore]=useState(false);
  const searchInput=useRef<HTMLInputElement>(null);const composing=useRef(false);const firstRefresh=useRef(true);const list=useRef<HTMLDivElement>(null);const lastRow=useRef<HTMLButtonElement|null>(null);
  const requestId=useRef(0);const previewId=useRef(0);const abortRef=useRef<AbortController|null>(null);
  const openView=(next:View)=>{setView(next);setNavOpen(false);};
  const closePreview=useCallback(()=>{setSelected(null);requestAnimationFrame(()=>lastRow.current?.focus());},[]);
  const refresh=useCallback(async()=>{
    try {
      const data=await api<Record<string,Facet[]>>('/bookmarks/facets');setFacets(data);setConnectionError('');
      try {const [status,task]=await Promise.all([api<Setup>('/admin/setup-status'),api<Job>('/admin/job')]);setSetup(status);setJob(task);setAdminAvailable(true);
        if(firstRefresh.current){firstRefresh.current=false;if(!status.bookmarks&&!remember('fm-setup-skipped'))setView('setup');}
      } catch(e){if(e instanceof ApiError&&e.status===403)setAdminAvailable(false);else throw e;}
    }catch(e){setConnectionError(String(e));}
  },[]);
  const boot=useCallback(async()=>{try{const data=await api<{paired:boolean;token:string}>('/app/boot');if(data.paired){setToken(data.token);setPaired(true);setPairingRequired(false);}else setPairingRequired(true);setConnectionError('');}catch(e){setConnectionError(String(e));}},[]);
  useEffect(()=>{boot();},[boot]);
  useEffect(()=>{if(!paired)return;refresh();const timer=setInterval(refresh,4000);return()=>clearInterval(timer);},[paired,refresh]);
  useEffect(()=>{const media=matchMedia('(max-width: 1119px)');const update=()=>setDrawer(media.matches);media.addEventListener('change',update);return()=>media.removeEventListener('change',update);},[]);
  useEffect(()=>{const handler=(event:KeyboardEvent)=>{
    if(event.isComposing)return;
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();setView('library');setNavOpen(false);requestAnimationFrame(()=>searchInput.current?.focus());}
    if(event.key==='Escape'&&selected!==null&&!drawer){event.preventDefault();closePreview();}
  };window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler);},[selected,drawer,closePreview]);
  function changeQuery(value:string){setInput(value);abortRef.current?.abort();requestId.current++;if(!composing.current){setSearch(value);setOffset(0);setDepth(undefined);}}
  const filterKey=JSON.stringify(filters);
  const semantic=Boolean(setup&&!setup.demo&&setup.channels.embed.configured&&setup.has_vectors&&setup.vector_compatible&&!setup.pending_apply);
  useEffect(()=>{
    if(!paired||view!=='library')return;
    const id=++requestId.current;const abort=new AbortController();abortRef.current=abort;
    const update=(data:Page)=>{if(id===requestId.current&&!abort.signal.aborted){setPage(data);if(data.depth)setDepth(data.depth);setLoading(false);}};
    setLoading(true);setError('');
    const timer=setTimeout(async()=>{try{
      if(!search.trim()){update(await api<Page>(`/bookmarks?${query({...filters,offset,limit:30})}`,{signal:abort.signal}));return;}
      const terms=[search,...Object.entries(filters).filter(([key])=>key!=='session').map(([key,value])=>`${key}:${JSON.stringify(value)}`)].join(' ');
      const fast=await api<Page>(`/quick?${query({q:terms,offset,limit:30,depth})}`,{signal:abort.signal});update(fast);
      if(semantic){const full=await post<Page>('/search',{q:terms,offset,limit:30,depth:depth??fast.depth},abort.signal);update(full);}
    }catch(e){if(id===requestId.current&&!abort.signal.aborted){setError(String(e));setLoading(false);}}},search?240:0);
    return()=>{clearTimeout(timer);abort.abort();};
    // Depth is the returned ranking snapshot; updating it must not restart page one.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[paired,view,search,offset,filterKey,semantic]);
  useEffect(()=>{if(selected===null){setPreview(null);return;}const id=++previewId.current;const abort=new AbortController();setPreview(null);setRelated([]);setPreviewError('');
    api<Bookmark>(`/bookmark/${selected}?body=true`,{signal:abort.signal}).then(record=>{if(id===previewId.current)setPreview(record);}).catch(e=>{if(!abort.signal.aborted)setPreviewError(String(e));});
    api<Bookmark[]>(`/bookmark/${selected}/related`,{signal:abort.signal}).then(records=>{if(id===previewId.current)setRelated(records);}).catch(()=>{});
    return()=>abort.abort();
  },[selected]);
  useEffect(()=>{if(view!=='sessions'||!paired)return;api<Session[]>('/sessions?limit=40').then(data=>{setSessions(data);setSessionsMore(data.length===40);}).catch(e=>setError(String(e)));},[view,paired]);
  const items=page?.items||page?.hits||[];
  function selectFilter(key:keyof Filters,value:string|number|undefined){abortRef.current?.abort();requestId.current++;setFilters(old=>({...old,[key]:value}));setOffset(0);setDepth(undefined);setView('library');setNavOpen(false);}
  function paginate(next:number){setOffset(next);list.current?.scrollTo({top:0});}
  const select=(id:number,button?:HTMLButtonElement)=>{if(button)lastRow.current=button;setSelected(id);};
  const previewContent=<>
    <header className="preview-heading"><span><FileText size={16}/>{t('阅读预览','Reading preview')}</span><button className="icon-button" title={t('关闭预览','Close preview')} aria-label={t('关闭预览','Close preview')} onClick={closePreview}><PanelRightClose/></button></header>
    {previewError?<div className="empty"><p className="error" role="alert">{previewError}</p><button className="secondary" onClick={()=>{const id=selected;setSelected(null);setTimeout(()=>setSelected(id),0);}}>{t('重试','Retry')}</button></div>:!preview?<div className="empty">{selected?<><LoaderCircle className="spin"/><p>{t('正在读取…','Loading page…')}</p></>:<><FileText size={32}/><h2>{t('留在此处，读得更深','Read without losing your place')}</h2><p>{t('选择一条书签，在这里查看正文、摘要和相关内容。','Select a bookmark to read its text, summary and related pages here.')}</p><span className="key-hint">↑ ↓ {t('浏览列表','navigate results')}</span></>}</div>:<div className="preview-scroll">
      <div className="preview-title"><span className="domain">{preview.domain}</span><h1>{preview.title||preview.url}</h1><p className="quiet">{preview.folder||t('未分类','Unfiled')}{preview.date_added?` · ${new Date(preview.date_added*1000).toLocaleDateString(language==='zh'?'zh-CN':'en')}`:''}</p>
        {safeUrl(preview.url)&&<a className="external-link" href={safeUrl(preview.url)} target="_blank" rel="noreferrer" onClick={()=>{post('/open',{bookmark_id:preview.bookmark_id,query:search}).catch(()=>{});}}>{t('打开原网页','Open original')}<ExternalLink size={14}/></a>}
      </div>
      <div className="preview-tabs" role="tablist" aria-label={t('预览内容','Preview content')}>{[['body',t('正文','Page text')],['summary',t('AI 摘要','AI summary')],['related',t('相关书签','Related')]].map(([id,label])=><button role="tab" aria-selected={previewTab===id} key={id} onClick={()=>setPreviewTab(id)}>{label}</button>)}</div>
      <div role="tabpanel" className="reading">{previewTab==='body'?preview.body_text?<div className="body-text">{preview.body_text}</div>:<div className="reading-empty"><h3>{t('正文还未保存','Page text is not saved yet')}</h3><p>{t('仍可用标题和网址搜索。可在任务中提取正文，或直接打开原网页。','Search still works on titles and URLs. Fetch text from Tasks, or open the original page.')}</p></div>:previewTab==='summary'?<>
        <div className="summary-label"><Sparkles size={16}/>{preview.indexed?.summary_basis==='title'?t('基于标题推断','Inferred from title'):t('基于已保存内容','From saved content')}</div>
        <p>{preview.indexed?.enriched_by?preview.summary:t('尚未生成 AI 摘要。配置模型后，在任务中开始索引。','No AI summary yet. Configure models and start indexing from Tasks.')}</p>
        {!!preview.key_points?.length&&<ul>{preview.key_points.map(point=><li key={point}>{point}</li>)}</ul>}
        {!!preview.intent_queries?.length&&<><h3>{t('这些问题也能找到它','Questions that lead here')}</h3>{preview.intent_queries.map(q=><button className="suggested-query" key={q} onClick={()=>{changeQuery(q);setView('library');if(drawer)closePreview();}}>{q}<ArrowRight size={14}/></button>)}</>}
      </>:related.length?related.map(record=><button className="related-item" key={record.bookmark_id} onClick={()=>select(record.bookmark_id)}><span>{record.title||record.url}</span><small>{record.domain}</small></button>):<p className="quiet">{t('暂无相关书签。完成索引后，关联会在这里出现。','No related pages yet. Connections appear here after indexing.')}</p>}</div>
      {!!preview.tags?.length&&<div className="preview-tags"><Tags size={14}/>{preview.tags.map(tag=><button key={tag} onClick={()=>{selectFilter('tag',tag);if(drawer)closePreview();}}>{tag}</button>)}</div>}
      {preview.privacy_skipped&&<p className="notice">{t('此书签已从云端处理和正文抓取中排除。','This bookmark is excluded from model processing and fetching.')}</p>}
    </div>}
  </>;
  return <div className="app-shell">
    <aside className={`sidebar ${navOpen?'is-open':''}`}>
      <a className="brand" href="/app" onClick={e=>{e.preventDefault();openView('library');}}><Layers3 size={25}/><span>Facetmark</span></a>
      <button className="nav-search" onClick={()=>{openView('library');requestAnimationFrame(()=>searchInput.current?.focus());}}><Search/>{t('搜索收藏','Search library')}<kbd>Ctrl K</kbd></button>
      <nav className="main-nav" aria-label={t('工作区','Workspace')}>
        <button className={view==='library'?'active':''} onClick={()=>{openView('library');setFilters({});changeQuery('');}}><BookmarkIcon/>{t('全部书签','All bookmarks')}<span className="count">{setup?.bookmarks??'—'}</span></button>
        <button className={view==='sessions'?'active':''} onClick={()=>openView('sessions')}><Clock3/>{t('浏览批次','Saving sessions')}</button>
      </nav>
      <div className="facet-nav">{[['folders','folder',t('文件夹','Folders'),Folder],['tags','tag',t('标签','Tags'),Tags],['domains','domain',t('站点','Sites'),Globe2]].map(([group,field,label,Icon])=>{
        const Glyph=Icon as typeof Folder;return <details open={group==='folders'} key={String(group)}><summary><Glyph size={15}/>{String(label)}<ChevronRight size={14}/></summary>{facets[String(group)]?.length?facets[String(group)].map(facet=><button key={facet.value} title={facet.value} className={filters[field as keyof Filters]===facet.value?'active':''} onClick={()=>selectFilter(field as keyof Filters,facet.value)}><span>{facet.value}</span><small>{facet.count}</small></button>):<p className="hint">{t('导入后显示','Available after import')}</p>}</details>;
      })}</div>
      <div className="sidebar-bottom">{adminAvailable&&<><button className={view==='import'?'active':''} onClick={()=>openView('import')}><Import/>{t('导入书签','Import bookmarks')}</button><button className={view==='tasks'?'active':''} onClick={()=>openView('tasks')}>{job.state==='running'?<LoaderCircle className="spin"/>:<Layers3/>}{t('任务','Tasks')}{job.state==='running'&&<span className="activity-dot"/>}</button><button className={view==='settings'?'active':''} onClick={()=>openView('settings')}><Settings2/>{t('设置','Settings')}</button></>}
        <div className="appearance"><button className="icon-button" aria-label={t('切换主题','Toggle theme')} onClick={()=>setTheme(theme==='light'?'dark':'light')}>{theme==='light'?<Moon/>:<Sun/>}</button><button className="language" aria-label="Switch language" onClick={()=>setLanguage(language==='zh'?'en':'zh')}>{language==='zh'?'EN':'中文'}</button><span className="local-status">{connectionError?<WifiOff size={13}/>:<Check size={13}/>} {t('本地书库','Local library')}</span></div>
      </div>
    </aside>
    {navOpen&&<button className="nav-scrim" aria-label={t('关闭导航','Close navigation')} onClick={()=>setNavOpen(false)}/>}
    <main className={`main-workspace ${view==='library'?'with-preview':''}`}>
      <div className="mobile-toolbar"><button className="icon-button" aria-label={t('打开导航','Open navigation')} onClick={()=>setNavOpen(true)}><Menu/></button><strong>Facetmark</strong><button className="icon-button" aria-label={t('搜索','Search')} onClick={()=>{openView('library');searchInput.current?.focus();}}><Search/></button></div>
      {connectionError&&<div className="connection-error" role="alert"><WifiOff size={16}/><span>{t('服务连接中断。请确认 Facetmark 正在运行。','Connection lost. Check that Facetmark is running.')} <small>{connectionError}</small></span><button className="secondary" onClick={()=>paired?refresh():boot()}>{t('重新连接','Reconnect')}</button></div>}
      {pairingRequired&&!paired?<section className="pairing-screen"><h1>{t('连接你的书库','Connect your library')}</h1><p>{t('请输入服务生成的配对令牌。远程访问不会自动提供令牌。','Enter the pairing token generated by your service. Remote access does not disclose it automatically.')}</p><label className="field">{t('配对令牌','Pairing token')}<input type="password" value={manualToken} onChange={e=>setManualToken(e.target.value)}/></label><button className="primary" onClick={async()=>{setToken(manualToken);try{await api('/stats');setPaired(true);setManualToken('');}catch(e){setConnectionError(String(e));}}}>{t('连接','Connect')}</button></section>:!paired?<div className="empty"><LoaderCircle className="spin"/><p>{t('正在打开书库…','Opening your library…')}</p></div>:view==='library'?<>
        <section className="results-column"><header className="search-header"><div className="workspace-heading"><h1>{search?t('搜索结果','Search results'):t('全部书签','All bookmarks')}</h1>{setup?.demo&&<span className="demo-label">{t('演示数据','Demo data')}</span>}</div>
          <div className="search-box"><Search size={20}/><input ref={searchInput} aria-label={t('搜索书签','Search bookmarks')} placeholder={t('你想找回什么？','What would you like to find again?')} value={input} onChange={e=>changeQuery(e.target.value)} onCompositionStart={()=>{composing.current=true;abortRef.current?.abort();requestId.current++;}} onCompositionEnd={e=>{composing.current=false;changeQuery(e.currentTarget.value);}} onKeyDown={e=>{if(e.key==='Enter'&&!e.nativeEvent.isComposing&&!composing.current)changeQuery(input);}}/>{input?<button className="icon-button" aria-label={t('清空搜索','Clear search')} onClick={()=>changeQuery('')}><X size={16}/></button>:<kbd>Ctrl K</kbd>}</div>
          <div className="search-meta"><span>{search?(semantic?t('关键词 + 语义检索','Keyword + semantic search'):t('关键词检索','Keyword search')):t('按收藏时间排列','Recently saved first')}</span><span>{page?.total??'—'}{page?.depth_capped?'+':''} {t('条','items')}</span></div>
          {Object.entries(filters).some(([,v])=>v!==undefined)&&<div className="filter-chips">{Object.entries(filters).filter(([,value])=>value!==undefined).map(([key,value])=><button key={key} onClick={()=>selectFilter(key as keyof Filters,undefined)}>{key==='session'?t('批次','Session'):''} {value}<X size={12}/></button>)}</div>}
        </header>
        {error&&<div className="error search-error" role="alert">{error}<button className="text-button" onClick={()=>{setSearch('');setTimeout(()=>setSearch(input),0);}}>{t('重试','Retry')}</button></div>}
        <div className="result-list" ref={list} aria-label={t('书签列表','Bookmark results')} aria-busy={loading}>
          {loading&&!items.length?<div className="empty"><LoaderCircle className="spin"/>{t('正在检索…','Searching…')}</div>:!items.length?<div className="empty"><BookmarkIcon size={36}/><h2>{search?t('换一点线索试试','Try another clue'):t('收藏，从这里汇合','Your collection starts here')}</h2><p>{search?t('试试标题中的词、网址，或减少筛选条件。','Try words from the title, a URL, or fewer filters.'):t('导入浏览器书签，就能开始关键词检索。','Import your browser bookmarks to start searching by keyword.')}</p>{!search&&adminAvailable&&<button className="primary" onClick={()=>openView('import')}><Import/>{t('导入书签','Import bookmarks')}</button>}</div>:items.map((record,index)=><button className={`result-row ${selected===record.bookmark_id?'selected':''}`} key={record.bookmark_id} onClick={e=>select(record.bookmark_id,e.currentTarget)} onKeyDown={e=>{if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const next=items[index+(e.key==='ArrowDown'?1:-1)];const button=list.current?.querySelectorAll<HTMLButtonElement>('.result-row')[index+(e.key==='ArrowDown'?1:-1)];if(next&&button){select(next.bookmark_id,button);button.focus();}}}} aria-pressed={selected===record.bookmark_id}>
            <span className="site-letter" aria-hidden="true">{(record.domain||record.title||'F').slice(0,1).toUpperCase()}</span><span className="result-copy"><span className="result-title">{record.title||record.url}</span><span className="result-summary">{record.snippet||record.summary||record.url}</span><span className="result-meta"><span>{record.domain}</span>{record.folder&&<span><Folder size={11}/>{record.folder}</span>}</span></span><ChevronRight className="row-chevron" size={15}/>
          </button>)}
        </div>
        <footer className="results-footer"><span>{page&&page.total>0?`${page.offset+1}–${page.offset+items.length}`:t('你的收藏，只在你的书库','Your collection, in your library')}</span><div><button className="icon-button" disabled={!page?.offset||loading} aria-label={t('上一页','Previous page')} onClick={()=>paginate(Math.max(0,(page?.offset||0)-(page?.limit||30)))}><ArrowLeft/></button><button className="icon-button" disabled={!page?.has_more||loading||page.depth_capped} aria-label={t('下一页','Next page')} onClick={()=>paginate((page?.offset||0)+(page?.limit||30))}><ArrowRight/></button></div></footer>
        </section>
        {!drawer&&<aside className="preview-pane">{previewContent}</aside>}
        {drawer&&<Dialog.Root open={selected!==null} onOpenChange={open=>{if(!open)closePreview();}}><Dialog.Portal><Dialog.Overlay className="drawer-overlay"/><Dialog.Content className="preview-drawer" aria-describedby={undefined} onCloseAutoFocus={e=>{e.preventDefault();lastRow.current?.focus();}}><Dialog.Title className="sr-only">{t('书签预览','Bookmark preview')}</Dialog.Title>{previewContent}</Dialog.Content></Dialog.Portal></Dialog.Root>}
      </>:<div className="page-scroll">
        {view==='setup'?<SetupFlow setup={setup} job={job} refresh={refresh} onDone={()=>{remember('fm-setup-skipped','1');openView('library');}}/>:view==='import'?<><header className="page-heading"><h1>{t('导入书签','Import bookmarks')}</h1><button className="text-button" onClick={()=>openView('setup')}>{t('打开完整向导','Open setup guide')}<ArrowRight size={14}/></button></header><Importer refresh={refresh}/></>:view==='settings'?<><header className="page-heading"><h1>{t('设置','Settings')}</h1><span className="quiet">{t('配置属于你的检索方式','Make retrieval your own')}</span></header><Models setup={setup} refresh={refresh}/><ExtensionSettings/><section className="desktop-note"><h2>{t('桌面与更新','Desktop and updates')}</h2><p>{t('开机启动、全局快捷键与退出位于系统托盘菜单。关闭窗口后任务继续运行。', 'Launch at login, global shortcut and Quit are in the system tray menu. Tasks continue after the window closes.')}</p><a href="https://github.com/88lin/facetmark/actions/workflows/desktop.yml" target="_blank" rel="noreferrer">{t('查看最新未签名测试构建','View latest unsigned preview build')}<ExternalLink size={14}/></a></section></>:view==='tasks'?<><header className="page-heading"><h1>{t('任务与诊断','Tasks and diagnostics')}</h1></header><Tasks job={job} setup={setup} refresh={refresh}/><HealthTools/></>:<><header className="page-heading"><div><h1>{t('浏览批次','Saving sessions')}</h1><p>{t('沿着收藏时的上下文，重新发现相关页面。','Rediscover pages through the context in which you saved them.')}</p></div><Clock3/></header>{sessions.length?sessions.map(session=><button className="session-row" key={session.session_id} onClick={()=>{setFilters({session:session.session_id});changeQuery('');openView('library');}}><Clock3/><span><strong>{session.label||new Date(session.started_at*1000).toLocaleDateString(language==='zh'?'zh-CN':'en')}</strong><small>{session.size} {t('条书签','bookmarks')}</small></span><ArrowRight/></button>):<div className="empty"><Clock3 size={32}/><h2>{t('还没有浏览批次','No saving sessions yet')}</h2><p>{t('索引完成后，保存时间相近的书签会在这里汇合。','After indexing, bookmarks saved together appear here.')}</p></div>}{sessionsMore&&<button className="secondary" onClick={async()=>{try{const more=await api<Session[]>(`/sessions?limit=40&offset=${sessions.length}`);setSessions(s=>[...s,...more]);setSessionsMore(more.length===40);}catch(e){setError(String(e));}}}>{t('加载更多','Load more')}<ArrowDown/></button>}</>}
      </div>}
    </main>
  </div>;
}

function HealthTools(){const t=useText();const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);return <details className="health-tools"><summary>{t('链接健康检查','Link health check')}</summary><p>{t('点击后会访问最多 20 个原始网址以检查可用性，不会删除书签。','This visits up to 20 original URLs to check availability. Bookmarks are preserved.')}</p><button className="secondary" disabled={busy} onClick={async()=>{setBusy(true);try{setMessage(JSON.stringify(await post('/link-health/check',{limit:20})));}catch(e){setMessage(String(e));}finally{setBusy(false);}}}>{t('确认并检查链接','Confirm and check links')}</button><pre role="status">{message}</pre></details>;}
