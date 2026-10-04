import {useState} from 'react';
import {Check, Circle, LoaderCircle, Pause, Play, RefreshCw} from 'lucide-react';
import {post, type Job, type Setup} from './api';
import {useText} from './locale';

export function Tasks({job, setup, refresh}: {job: Job; setup: Setup|null; refresh: () => Promise<void>}) {
  const t = useText(); const [consent,setConsent] = useState(false); const [fetchPages,setFetchPages] = useState(true); const [busy,setBusy] = useState(false); const [error,setError] = useState('');
  const names: Record<string,string> = {fetch:t('读取网页正文','Fetch page text'),enrich:t('生成摘要与意图','Generate summaries and intents'),embed_content:t('构建正文向量','Embed page content'),filter_intents:t('筛选检索意图','Filter search intents'),embed_intents:t('构建意图向量','Embed search intents'),sessions:t('整理浏览批次','Reconstruct saving sessions'),edges:t('连接相关书签','Connect related bookmarks')};
  const states: Record<string,string> = {idle:t('尚未开始','Not started'),running:t('正在建立索引','Indexing your library'),done:t('索引任务已完成','Indexing completed'),partial:t('索引部分完成','Indexing partially completed'),failed:t('索引未完成','Indexing failed'),cancelled:t('任务已取消','Task cancelled'),interrupted:t('上次任务被中断','Previous task was interrupted')};
  async function action(path: string, body: unknown) {setBusy(true);setError('');try {await post(path,body);await refresh();} catch(e) {setError(String(e));} finally {setBusy(false);} }
  const canIndex = setup?.demo || (setup?.channels.chat.tested && setup?.channels.embed.tested && !setup?.pending_apply && setup?.vector_compatible);
  return <section className="tasks"><div className="section-heading"><h2>{states[job.state] || job.state}</h2><p>{t('任务在后台继续，切换页面不会中断。', 'Work continues in the background when you switch views.')}</p></div>
    {['interrupted','failed','cancelled','partial'].includes(job.state) && <p className="notice">{t('可以再次运行。未变化且已经完成的内容会被指纹检查跳过。', 'Run again to resume. Fingerprints skip completed, unchanged content.')}</p>}
    <ol className="stages">{(job.planned || Object.keys(names)).map(name => <li key={name} className={job.current === name ? 'current' : ''}>{job.done?.includes(name) ? <Check/> : job.current === name ? <LoaderCircle className="spin"/> : <Circle/>}<span>{names[name] || name}</span>{job.done?.includes(name) && <small>{t('完成','Done')}</small>}</li>)}</ol>
    {job.state === 'running' ? <div><p role="status">{job.cancel_requested ? t('已请求取消，将在当前阶段结束后停止。','Cancellation requested. Stopping after the current stage.') : t('正在处理当前阶段，所需时间取决于页面和模型服务。','Processing this stage. Time depends on the pages and model service.')}</p><button className="secondary" disabled={busy || job.cancel_requested} onClick={() => action('/admin/job/cancel',{})}><Pause/>{t('取消任务','Cancel task')}</button></div> : <div className="index-consent">
      <h3>{t('开始前，确认处理范围', 'Confirm what will be processed')}</h3>
      <p>{t('索引会将非隐私排除书签的标题、网址、已提取正文和生成的检索意图发送至你配置的聊天与向量服务。使用云端服务时，这些内容会离开本机。', 'Indexing sends titles, URLs, extracted page text and generated search intents from non-excluded bookmarks to your configured chat and embedding services. With cloud services, this content leaves your device.')}</p>
      <label className="check"><input type="checkbox" checked={fetchPages} onChange={e=>setFetchPages(e.target.checked)}/>{t('先访问原网页，提取正文', 'Fetch original pages first')}</label>
      <label className="check"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>{t('我已了解并确认开始处理', 'I understand and confirm processing')}</label>
      {!canIndex && <p className="hint">{t('请先保存、测试并应用两条模型连接。也可以继续使用关键词检索。', 'Save, test and apply both model connections first. Keyword search remains available.')}</p>}
      <button className="primary" disabled={!consent || !canIndex || busy} onClick={()=>action('/admin/index',{fetch:fetchPages,confirmed:true})}>{job.state === 'idle' ? <Play/> : <RefreshCw/>}{t('开始索引','Start indexing')}</button>
    </div>}
    {(error || job.error) && <p className="error" role="alert">{error || job.error}</p>}
    <details className="advanced"><summary>{t('任务日志与索引诊断','Task log and index diagnostics')}</summary><pre>{job.log?.join('\n') || t('暂无日志','No log yet')}</pre><pre>{JSON.stringify(setup?.stats,null,2)}</pre></details>
  </section>;
}
