"""Representative, isolated collection content for the current cloud design review."""
from __future__ import annotations

import json

from facetmark.fetch.store import store_body

RECORDS = [
    ("中文界面的阅读节奏：从字阶、行距到长标题的完整排版实践", "sspai.example", "设计与体验 / 中文排版 / 界面规范 / 长标题与中英混排", ["中文排版", "阅读体验"],
     "中文界面需要把标题、正文与工具标签分开处理。通过真实长文案比较字阶和行距，再让次要信息退到合适的位置；留白的作用是建立阅读关系，而不是减少内容。"),
    ("Building local-first software：让数据、离线体验与恢复真正属于用户", "github.example", "开发工具 / 本地优先", ["Local-first", "SQLite"],
     "Local-first 的核心是明确的数据归属。本文整理离线读取、SQLite 迁移与任务恢复的设计边界，并给出能够逐步上线的实施顺序。"),
    ("设计里的细小反馈，怎样让连续操作更顺手？", "growth.design.example", "设计与体验 / 交互研究", ["微交互", "Motion"],
     "选中反馈及时到位；菜单从触发位置展开；处理结果留在原来的对象附近。用同一套运动节奏连接输入与结果，快速反向操作时从当前状态接续。"),
    ("Beyond the prompt — A practical guide to reliable AI workflows", "research.example", "人工智能 / 工作流", ["AI", "工作流"],
     "把发现、配置、测试、保存与执行分成不同状态。长期任务保留目标快照，重试只处理原任务中的失败项和未完成项。"),
    ("一份写给自己的知识整理指南：收藏以后，如何让一段思考再次被找到", "notes.example", "知识管理", ["知识管理", "方法"],
     "检索从具体问题开始。为收藏留下短而准确的线索，比反复建立更深的目录更有帮助。标题、来源与保存时的想法，应该一起出现在回到原文的路径上。本文还比较了专题目录、标签和摘要各自的职责，说明它们怎样避免重复，以及内容越来越多时如何保持可维护。"),
    ("CSS View Transitions：状态切换、快速反向与 prefers-reduced-motion", "developer.example", "开发工具 / 前端", ["CSS", "可访问性"], "页面切换中的对象保持连贯，输入仍应立即生效。"),
    ("从一张列表到完整工作区：搜索、筛选、批量选择和阅读怎样相互呼应", "design.example", "设计与体验 / 交互研究", ["产品设计", "信息架构"],
     "用稳定的位置表达不同的操作范围。搜索控制可见结果，管理作用于明确选择，摘要处理再经过范围预览与同意。阅读面板与列表共享同一个收藏 ID，关闭后回到原查询和焦点。"),
    ("把模型连接的失败说清楚：一套可以重新测试、保存和继续处理的状态设计", "engineering.example", "人工智能 / 工作流", ["状态设计", "失败恢复"],
     "没有通过的连接不能显示为已准备好。错误要指向具体阶段，并留下可以重试的入口。"),
    ("A small guide to generous, useful empty states", "design.example", "设计与体验", ["Empty states", "UX"], "Explain what belongs here, preserve the current query, and offer one useful way back."),
    ("摘要不是原文：在 AI 概括、正文摘录与原网页之间保留可核对的来源", "reading.example", "阅读笔记 / 来源核查", ["阅读", "AI 摘要"],
     "概括帮助判断一篇文章是否值得继续读，原文保留论证、条件与细节。基于标题推断的内容应明确标注，不能和基于正文的摘要混为一谈。"),
    ("Design tokens in practice — 颜色、状态与控件如何共用一套语义", "github.example", "开发工具 / 前端", ["Design tokens", "前端"],
     "展示色与可读文字分开配对，选中、错误、成功各有职责。换主题时一起检查导航、列表、输入、任务与阅读，而不只改变主按钮。"),
    ("SQLite WAL 与小型桌面应用的数据可靠性", "engineering.example", "开发工具 / 本地优先", ["SQLite", "数据"], "一份关于备份、并发读取与升级恢复的实用笔记。"),
]


def prepare(conn):
    """Change only the CI temporary database, after ordinary fixture indexing."""
    rows = conn.execute("SELECT id FROM bookmark ORDER BY date_added DESC,id DESC LIMIT 36").fetchall()
    for index, row in enumerate(rows):
        bookmark_id = row[0]
        title, host, folder, tags, summary = RECORDS[index % len(RECORDS)]
        # These authored fixture strings describe known hierarchy, rather than
        # attempting to decode an arbitrary stored user's folder name.
        folder_parts = folder.split(" / ")
        if index >= len(RECORDS):
            title += f" · 研究笔记 {index // len(RECORDS) + 1}"
        conn.execute("UPDATE bookmark SET title=?,url=?,domain=?,folder=?,folder_depth=?,tags=? WHERE id=?",
                     (title, f"https://{host}/synthetic-review/{index}", host, "/".join(folder_parts), len(folder_parts),
                      json.dumps(["demo", *tags], ensure_ascii=False), bookmark_id))
        conn.execute("UPDATE enrichment SET summary=?,basis='body' WHERE bookmark_id=?", (summary, bookmark_id))
        store_body(conn, bookmark_id, body=title + "\n\n" + summary + "\n\n"
                   "## 留下能找回来的线索\n\n收藏让一个页面有了再次被找到的机会。用具体的问题记录它为什么重要，"
                   "把标题、来源和保存时的想法留在一起。分类与标签不需要重复说明同一件事。\n\n"
                   "## 从摘要回到原文\n\n摘要帮助判断方向，原文保留论证与细节。阅读时可以在列表与正文之间切换，"
                   "而刚才的查询、当前对象和阅读位置仍留在原处。\n\n"
                   "把重点整理出来以后，试着追问它依赖哪些条件。下一次遇到相关问题，就可以沿着这条线索回到出处。\n\n"
                   "## 保持思考的上下文\n\nA useful collection connects a question to its source. Keep the result list in place "
                   "while reading, then return with the same question in mind.\n\n"
                   "这是为本轮界面验证编写的隔离合成资料，不包含真实用户书签。")
        if index in (3, 7, 16, 23):
            conn.execute("INSERT OR REPLACE INTO enrichment_failure(bookmark_id,error,updated_at) VALUES(?,?,?)",
                         (bookmark_id, "Synthetic previous connection timeout; retry is available.", 1792627200))
        elif index in (5, 10, 14, 19, 26):
            conn.execute("DELETE FROM enrichment WHERE bookmark_id=?", (bookmark_id,))
    conn.commit()
