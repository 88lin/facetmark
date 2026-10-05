"""CI-only synthetic corpus, isolated from every real user data directory."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import uvicorn

from facetmark import service
from facetmark.api import create_app
from facetmark.config import Settings
from facetmark.db import open_db
from facetmark.fetch.store import store_body


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Run browser and large runtime validation in GitHub Actions only")
    with tempfile.TemporaryDirectory(prefix="facetmark-experience-") as temporary:
        os.environ["FACETMARK_DATA_DIR"] = temporary
        settings = Settings(
            data_dir=Path(temporary),
            use_mock_provider=True,
            embed_dim=32,
            chat_model="demo",
            embed_model="demo",
            host="127.0.0.1",
            port=8791,
        )
        conn = open_db(settings.db_path)
        titles = [
            (
                "把知识整理成可以再次找到的线索",
                "notes.example",
                "知识管理",
                "检索不是收集更多，而是在需要的时候，沿着一个线索找回原来的思考。",
            ),
            (
                "Designing interfaces for focused work",
                "design.example",
                "设计与体验",
                "A quiet interface makes room for the work. Keep navigation stable and let the content lead.",
            ),
            (
                "从关键词到语义：理解向量检索",
                "research.example",
                "人工智能",
                "向量检索将文本映射到一个语义空间。模型与维度必须一致，检索结果才有意义。",
            ),
            (
                "SQLite：小而可靠的本地数据层",
                "engineering.example",
                "开发工具",
                "本地优先的应用把可用性建立在一个简单的基础上：属于用户的数据与清晰的边界。",
            ),
            (
                "The craft of useful empty states",
                "design.example",
                "设计与体验",
                "An empty state should explain what belongs here and give the reader one useful next action.",
            ),
            (
                "如何在阅读中建立问题意识",
                "reading.example",
                "阅读笔记",
                "记住一个结论不如记住它回答的问题。阅读时留下自己的问题，也就留下了下一次检索的入口。",
            ),
            (
                "A practical guide to local-first software",
                "engineering.example",
                "开发工具",
                "Ownership, offline access and predictable recovery are the foundation of local-first software.",
            ),
            (
                "让复杂工作流保持清晰",
                "notes.example",
                "知识管理",
                "把配置、测试和执行分开表达。进度没有精确数据时，显示正在完成的工作，而不是编造数字。",
            ),
        ]
        for index in range(72):
            title, host, folder, text = titles[index % len(titles)]
            suffix = f" · {index // len(titles) + 1}" if index >= len(titles) else ""
            record = service.save_bookmark(
                conn,
                f"https://{host}/library/{index}",
                title=title + suffix,
                folder=folder,
                tags=["demo", folder],
                date_added=1790985600 - index * 450,
                settings=settings,
            )
            body = (
                title
                + "\n\n"
                + text
                + "\n\n"
                + "收藏一个页面很容易，真正困难的是在需要时重新找到它。标题、来源和保存时的问题，构成了回到那段思考的路径。\n\n"
                + "## 留下能找回来的线索\n\n记录一个具体的问题，把标题、标签和保存时的上下文放在一起。下一次回来时，这些线索会比模糊的印象更有用。\n\n"
                + "文件夹回答它属于哪里，标签记录它与什么有关，而一句自己的问题，往往能解释为什么当时值得收藏。三者并不需要重复。\n\n"
                + "## 从摘要回到原文\n\n摘要帮助你判断方向，原文保留论证与细节。把两者放在同一处，阅读就不必打断检索。\n\n"
                + "读到一个有用的段落时，试着追问：它解决了什么问题？这个结论依赖哪些条件？哪些细节值得回到原网页继续核对？\n\n"
                + "## 保持思考的上下文\n\n在结果之间切换时，让问题留在原处。你可以继续比较下一条收藏，也可以展开当前文章，读完后再回到刚才的位置。\n\n"
                + "A useful collection connects a question to its source. Keep the result list in place while inspecting the evidence, then return with the same question in mind.\n\n"
                + "这是为界面验证编写的合成示例，不含真实书签。This is synthetic content for interface verification."
            )
            store_body(conn, record["bookmark_id"], body=body)
        asyncio.run(service.index_all(conn, settings=settings, fetch=False))
        conn.close()
        uvicorn.run(
            create_app(settings), host=settings.host, port=settings.port, log_level="warning"
        )


if __name__ == "__main__":
    main()
