"""Preview copy shared by both generated language editions."""


def extend(content):
    zh = content['code'] == 'zh'
    title = 'Windows 桌面预览' if zh else 'Windows desktop preview'
    body = ('测试分支提供 Tauri 2 桌面应用和共享 React 三栏检索工作台。分别配置聊天与向量模型，'
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
