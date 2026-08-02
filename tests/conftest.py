from __future__ import annotations

import sqlite3

import pytest

from facetmark.config import Settings
from facetmark.db import open_db

# ---------------------------------------------------------------------------
# Bookmark file fixtures.
#
# The Netscape sample deliberately reproduces the awkward properties measured on
# a real 1697-entry export: Unix-second ADD_DATE, inline base64 favicons, CJK
# folder and title text, nesting, a <DD> note, a duplicate that only differs by
# tracking parameters, and a non-http scheme.
# ---------------------------------------------------------------------------

NETSCAPE_SAMPLE = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3 ADD_DATE="1646926493" LAST_MODIFIED="1784671225" PERSONAL_TOOLBAR_FOLDER="true">收藏夹栏</H3>
    <DL><p>
        <DT><H3 ADD_DATE="1647184809" LAST_MODIFIED="1779176434">study</H3>
        <DL><p>
            <DT><A HREF="https://example.com/crdt-guide" ADD_DATE="1690391875" ICON="data:image/png;base64,iVBORw0KGgoAAAA">用 Automerge 做协同编辑的 CRDT 实践</A>
            <DD>当时在选型，这篇讲得最清楚
            <DT><A HREF="https://example.com/crdt-guide?utm_source=twitter&amp;fbclid=abc" ADD_DATE="1690391999">CRDT 实践（重复）</A>
            <DT><A HREF="https://docs.example.org/fts5#tokenizers" ADD_DATE="1690392100">SQLite FTS5 中文分词</A>
        </DL><p>
        <DT><H3 ADD_DATE="1664035514">工具</H3>
        <DL><p>
            <DT><A HREF="https://github.com/pola-rs/polars#readme" ADD_DATE="1700000000">polars</A>
            <DT><A HREF="data:text/html,hello" ADD_DATE="1700000100">a data url</A>
        </DL><p>
        <DT><A HREF="https://example.net/sibling" ADD_DATE="1710000000">和子文件夹同级的书签</A>
    </DL><p>
    <DT><A HREF="http://www.plain.example/no-folder/" ADD_DATE="1600000000">顶层书签</A>
</DL><p>
"""

# Same three URLs, WebKit microseconds, Chromium JSON layout.
CHROME_SAMPLE = """{
  "checksum": "x",
  "roots": {
    "bookmark_bar": {
      "children": [
        {"date_added": "13300000000000000", "name": "用 Automerge 做协同编辑的 CRDT 实践",
         "type": "url", "url": "https://example.com/crdt-guide"},
        {"children": [
            {"date_added": "13300000060000000", "name": "SQLite FTS5 中文分词",
             "type": "url", "url": "https://docs.example.org/fts5#tokenizers"}
         ],
         "name": "study", "type": "folder"}
      ],
      "name": "Bookmarks bar", "type": "folder"
    },
    "other": {
      "children": [
        {"date_added": "13300000120000000", "name": "polars",
         "type": "url", "url": "https://github.com/pola-rs/polars#readme"}
      ],
      "name": "Other bookmarks", "type": "folder"
    }
  },
  "version": 1
}
"""


@pytest.fixture()
def netscape_sample() -> str:
    return NETSCAPE_SAMPLE


@pytest.fixture()
def chrome_sample() -> str:
    return CHROME_SAMPLE


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = open_db(":memory:")
    yield c
    c.close()


@pytest.fixture()
def settings(tmp_path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        use_mock_provider=True,
        embed_dim=32,
        embed_model="mock-embed",
        chat_model="mock-chat",
        health_enable_external=False,
    )


@pytest.fixture()
def mock_settings(tmp_path) -> Settings:
    """Offline settings shared by the enrichment and retrieval suites.

    embed_dim is 64 rather than the production default: large enough that the
    mock's feature hashing does not collide constantly, small enough that a
    few hundred vectors cost nothing.
    """
    return Settings(
        data_dir=tmp_path,
        use_mock_provider=True,
        embed_dim=64,
        embed_model="mock-embed",
        chat_model="mock-chat",
        health_enable_external=False,
    )
