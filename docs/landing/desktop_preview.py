"""Preview copy shared by both generated language editions."""


def extend(content):
    zh = content['code'] == 'zh'
    title = 'Windows 桌面预览' if zh else 'Windows desktop preview'
    body = ('测试分支提供 Tauri 2 桌面应用和共享 React 收藏检索与阅读界面。分别配置聊天与向量模型，'
            '先测试连接，再确认索引；无需 Key 也能使用关键词检索。原始浏览器书签只读。' if zh else
            'The test branch adds a Tauri 2 desktop app and a shared React workbench. Configure chat and embeddings independently, '
            'test both, then confirm indexing. Keyword search works without keys. Original browser bookmarks are read-only.')
    download = '<a href="https://github.com/88lin/facetmark/actions/workflows/desktop.yml">' + ('下载未签名测试构建' if zh else 'Download unsigned preview builds') + '</a>'
    note = ('从最新成功运行下载 facetmark-windows-x64-preview。安装包含 Python 后端与 WebView2 离线安装器；不带大模型。'
            '这是测试安装包，可能出现 SmartScreen 提示，尚未正式发布。' if zh else
            'Download facetmark-windows-x64-preview from the latest successful run. The installer includes the Python backend and offline WebView2, '
            'without large models. This is an unsigned test package, may trigger SmartScreen, and is not a production release.')
    blocks = [('p', body), ('p', download), ('callout', '', title, '<p>' + note + '</p>')]
    content['quickstart']['sections'].insert(0, ('desktop-preview', title, blocks))
    content['webui']['sections'].insert(0, ('desktop-preview', title, blocks))
    content['index']['cta'].insert(0, (title, 'https://github.com/88lin/facetmark/actions/workflows/desktop.yml', True))
    content['index']['desktop_preview'] = (title, body, download, note)
    def say(chinese, english):
        return chinese if zh else english

    light = f"assets/workbench-{content['code']}-light.png"
    dark = f"assets/workbench-{content['code']}-dark.png"
    alt = say('Facetmark 收藏阅读界面：辅助索引与正文并排，使用合成书签。', 'React workbench with results beside reading preview. Synthetic bookmarks.')
    caption = say('保留检索上下文，继续阅读 · 合成演示书库', 'Keep your search context while reading · Synthetic demo library')
    content['index']['app_shot'] = (light, alt, caption)
    content['index']['app_shot_dark'] = (dark, alt)
    replacements = {
        'firstrun': [('steps', [
            say('导入 HTML 或 JSON 副本，也可主动查找并选择本机 Chromium 来源。', 'Import an HTML or JSON copy, or explicitly discover and select a local Chromium source.'),
            say('分别填写聊天和向量服务，独立测试，检查实测维度，再保存与应用。免 Key 仅允许显式本机服务。', 'Configure chat and embeddings independently, test both, check measured dimensions, then save and apply. Keyless access is limited to explicitly configured loopback services.'),
            say('确认数据发送范围后开始索引；可以跳过 AI，直接用关键词检索。任务显示阶段和真实失败，可取消或重试。', 'Confirm what is sent before indexing. You can skip AI and search by keyword. Tasks show stages and actual failures, with cancellation and retry.'),
        ])],
        'tabs': [('table', [say('入口', 'View'), say('用途', 'Purpose')], [
            [say('全部书签', 'All bookmarks'), say('真实分页，文件夹／标签／站点筛选；输入词语或查询语法开始搜索。', 'Paginated browsing with folder, tag and site filters; search with words or query syntax.')],
            [say('阅读预览', 'Reading preview'), say('正文、AI 摘要和相关书签。打开原网页使用系统浏览器，预览不丢失搜索条件。', 'Page text, AI summary and related pages. Originals open externally; preview preserves your query.')],
            [say('综合回答', 'Answer from this library'), say('位于搜索结果上方，确认后发送问题与最多 8 条来源摘要，回答附编号引用与证据局限。', 'Above search results. Confirmation sends the question and up to 8 source excerpts; answers carry numbered citations and evidence limits.')],
            [say('浏览批次', 'Saving sessions'), say('选择收藏时段，以批次范围继续检索。', 'Select a saving session and search within it.')],
            [say('任务与设置', 'Tasks and settings'), say('索引、取消、诊断、双模型连接、扩展配对和手动检查更新。', 'Indexing, cancellation, diagnostics, independent models, extension pairing and manual update checks.')],
        ])],
        'read': [('shot', light, alt, caption, dark, alt), ('p', say('从收藏索引中打开文章，搜索条件和列表位置会保留。桌面可展开专注阅读；窄窗口以全屏阅读打开，点击“返回收藏”继续查找。展开“收藏信息与检索线索”查看来源信息；排名不是事实核查。', 'Open an article from the collection while keeping your query and list position. Expand focused reading on desktop; narrow windows use full-screen reading with a “Back to collection” action. Expand “Saved details &amp; search context” for source information; ranking is not fact checking.'))],
        'keys': [('table', [say('操作', 'Action'), say('结果', 'Result')], [
            ['Ctrl+K', say('聚焦搜索；支持中文输入法组合输入。', 'Focus search; IME composition is preserved.')],
            ['↑ / ↓', say('在结果列表中选择相邻书签。', 'Select adjacent bookmarks in the result list.')],
            ['Escape', say('关闭预览或手机导航并还原焦点，保留查询。', 'Close preview or mobile navigation, restore focus and retain the query.')],
            [say('语言／主题', 'Language / theme'), say('在中英文、明暗模式间切换，保存到当前设备。', 'Switch Chinese/English and light/dark; preferences persist on this device.')],
        ])],
        'trouble': [('p', say('无结果时清除筛选或换一个标题词。没有 Key 时仍可用关键词检索。连接失败可重试；相关书签与批次请求失败会单独提示。远程访问不开放管理接口，请使用 loopback 或 SSH 转发。', 'Clear filters or try another title word when nothing matches. Keyword search works without keys. Connection, related-page and session failures have retry actions. Remote access does not expose administration; use loopback or SSH forwarding.'))],
    }
    content['webui']['sections'] = [(key, heading, replacements.get(key, rows)) for key, heading, rows in content['webui']['sections']]
    # The quickstart's legacy screenshot must not imply obsolete tab behavior.
    for index, (key, heading, rows) in enumerate(content['quickstart']['sections']):
        content['quickstart']['sections'][index] = (key, heading, [
            ('shot', light, alt, caption, dark, alt) if row[0] == 'shot' and 'app-search' in row[1] else row
            for row in rows
        ])
