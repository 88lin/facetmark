from fastapi.testclient import TestClient

from facetmark import service
from facetmark.api import create_app
from facetmark.config import Settings


def test_sessions_can_be_organized_without_ai_and_keep_bookmarks(tmp_path, monkeypatch):
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))
    with TestClient(create_app(Settings(data_dir=tmp_path)), client=("127.0.0.1", 40000)) as client:
        state = client.app.state.fm
        client.headers["Authorization"] = "Bearer " + state.token
        service.import_content(state.conn, '''<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p>
<DT><A HREF="https://synthetic.invalid/one" ADD_DATE="1700000000">One</A>
<DT><A HREF="https://synthetic.invalid/two" ADD_DATE="1700000200">Two</A>
<DT><A HREF="https://synthetic.invalid/three" ADD_DATE="1700010000">Three</A>
</DL><p>''', settings=state.settings)
        before = [dict(row) for row in state.conn.execute("SELECT id,url,title,date_added FROM bookmark ORDER BY id")]
        revision = client.get("/admin/setup-status").json()["library_revision"]
        assert client.get("/sessions").json() == []
        response = client.post("/admin/sessions/rebuild", json={})
        assert response.status_code == 200, response.text
        assert response.json()["sessions"] == 1
        assert response.json()["assigned"] == 2
        session = client.get("/sessions").json()[0]
        assert session["size"] == 2
        assert client.get(f'/bookmarks?session={session["session_id"]}').json()["total"] == 2
        assert client.get("/admin/setup-status").json()["library_revision"] != revision
        assert before == [dict(row) for row in state.conn.execute("SELECT id,url,title,date_added FROM bookmark ORDER BY id")]
        assert state.model_users == 0
        assert not state.probe_results
        assert state.conn.execute("SELECT count(*) FROM edge WHERE kind='session'").fetchone()[0] == 2

        # A failed relation rebuild must roll back both tables and release the
        # write guard, so readers never see a half-rebuilt grouping.
        import pytest

        def fail_edges(conn):
            raise RuntimeError("synthetic relation failure")

        monkeypatch.setattr("facetmark.edges.build_session_edges", fail_edges)
        with pytest.raises(RuntimeError, match="synthetic relation failure"):
            client.post("/admin/sessions/rebuild", json={})
        assert client.get("/sessions").json()[0] == session
        assert state.conn.execute("SELECT count(*) FROM edge WHERE kind='session'").fetchone()[0] == 2
        assert state.model_users == 0


def test_sessions_do_not_rebuild_during_active_model_requests(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path)), client=("127.0.0.1", 40000)) as client:
        state = client.app.state.fm
        client.headers["Authorization"] = "Bearer " + state.token
        state.model_users = 1
        assert client.post("/admin/sessions/rebuild", json={}).status_code == 409
        assert state.model_users == 1
        state.model_users = 0
