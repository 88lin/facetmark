"""Synthetic scale data shared by cloud benchmarks and browser acceptance."""
from __future__ import annotations


def populate(conn, total=200_000):
    start = conn.execute("SELECT COALESCE(max(id),0) FROM bookmark").fetchone()[0]
    conn.execute("BEGIN")
    try:
        conn.executemany(
            "INSERT INTO bookmark(id,url,url_norm,url_hash,title,folder,host,domain,date_added,created_at,updated_at,tags) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            ((i, f"https://scale.example/{i}", f"https://scale.example/{i}", f"scale-{i}",
              f"{'needle' if i % 10 == 0 else 'reference'} synthetic bookmark {i}",
              f"Scale/{i % 4096:04}", "scale.example", "scale.example", 1700000000 - i,
              1700000000 - i, 1700000000 - i, '["scale"]') for i in range(start + 1, total + 1)),
        )
        for table in ("fts_seg", "fts_tri"):
            conn.execute(f"INSERT INTO {table}(rowid,title,body,summary,extra) "
                         "SELECT id,title,'','','scale' FROM bookmark WHERE id>?", (start,))
        conn.execute("INSERT INTO enrichment(bookmark_id,summary,source_hash,basis) "
                     "SELECT id,'A synthetic title-based summary for scale validation.',fm_title_hash(title,url),'title' "
                     "FROM bookmark WHERE id>? AND id%5=0", (start,))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
