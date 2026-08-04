"""Cross-language wire contract: replay what the TypeScript plugin actually sends.

The gap this closes is the one the plugin's own header comment named: the Python
routes are pinned by Python tests, the TypeScript signatures are pinned by `tsc`,
and *nothing asserted that the JSON one side emits is the JSON the other side
parses*. Two type systems agreeing about a shape they each describe separately is
not the same as one program agreeing with another.

``integrations/karakeep/contract/capture.ts`` drives the real ``FacetmarkProvider``
with a recording ``fetch`` and writes every request to ``wire.json``. This module
replays those bytes through the real FastAPI app and writes the responses back to
``replies.json`` for the TypeScript side to parse. Each half consumes an artifact
the *other* half produced, and neither needs the other's runtime: CI's Python job
runs this file without Node, and CI's plugin job runs `--check` without Python.

What it can and cannot catch. It catches a field the plugin sends that the Python
model silently drops, a serialisation the parser rejects, a response missing a
field karakeep's `SearchResponse` declares required, and any drift in either
direction -- because the drift shows up as a diff in a committed file. It does
*not* catch anything about a live karakeep instance: no plugin registration, no
real HTTP stack, no concurrency, no auth against a real deployment. This is a
format contract, not an integration test, and the docs say so.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from facetmark.api import (
    KarakeepAddRequest,
    KarakeepDeleteRequest,
    KarakeepSearchRequest,
    create_app,
)
from facetmark.config import Settings

CONTRACT = Path(__file__).resolve().parents[1] / "integrations" / "karakeep" / "contract"
WIRE = CONTRACT / "wire.json"
REPLIES = CONTRACT / "replies.json"

REGENERATE = os.environ.get("FACETMARK_UPDATE_CONTRACT") == "1"

# Which request model each path parses. `/karakeep/clear` is deliberately absent:
# the plugin sends no body there, and that is itself part of the contract.
MODELS = {
    "/karakeep/documents": KarakeepAddRequest,
    "/karakeep/documents/delete": KarakeepDeleteRequest,
    "/karakeep/search": KarakeepSearchRequest,
}

# `SearchIndexClient` has exactly four methods. If the plugin grows a fifth and
# nobody re-runs the capture, this set stops matching and the test below says so.
EXPECTED_PATHS = {
    "/karakeep/documents",
    "/karakeep/documents/delete",
    "/karakeep/search",
    "/karakeep/clear",
}


def _wire() -> dict:
    return json.loads(WIRE.read_text(encoding="utf-8"))


def _calls() -> list[dict]:
    return _wire()["calls"]


def _by_label(label: str) -> dict:
    for call in _calls():
        if call["label"] == label:
            return call
    raise AssertionError(f"wire.json has no call labelled {label!r}; re-run the capture")


def _docs(label: str = "addDocuments") -> list[dict]:
    return _by_label(label)["body"]["documents"]


def _doc(doc_id: str) -> dict:
    for d in _docs():
        if d["id"] == doc_id:
            return d
    raise AssertionError(f"wire.json has no document {doc_id!r}")


@pytest.fixture()
def kk(tmp_path):
    """A live app plus the helper that replays a captured call verbatim."""
    st = Settings(data_dir=tmp_path / "fm", use_mock_provider=True)
    app = create_app(st)
    with TestClient(app) as client:
        token = client.app.state.fm.token

        def replay(call: dict):
            # The plugin's own headers, with only the redacted bearer swapped for
            # this app's real pairing token. Case is left exactly as captured:
            # the plugin sends lowercase `authorization`, and that has to work.
            headers = {
                k: (f"Bearer {token}" if k == "authorization" else v)
                for k, v in call["headers"].items()
            }
            body = call["body"]
            kw = {} if body is None else {"json": body}
            return client.request(call["method"], call["path"], headers=headers, **kw)

        client.replay = replay  # type: ignore[attr-defined]
        yield client


def _normalise(payload):
    """Zero out the fields that legitimately differ run to run.

    Only wall-clock timings qualify. Counts, ids and engine names are part of the
    contract and are compared as-is; if one of them moves, the diff should fail.
    """
    if isinstance(payload, dict):
        return {
            k: (0.0 if k in {"processingTimeMs", "elapsed_ms"} else _normalise(v))
            for k, v in payload.items()
        }
    if isinstance(payload, list):
        return [_normalise(v) for v in payload]
    return payload


# ---------------------------------------------------------------------------
# the captured requests, replayed
# ---------------------------------------------------------------------------


class TestCapturedRequests:
    def test_the_capture_covers_all_four_client_methods(self):
        assert {c["path"] for c in _calls()} == EXPECTED_PATHS

    def test_the_capture_leaked_no_real_token(self):
        for call in _calls():
            assert call["headers"]["authorization"] == "Bearer <token>"

    def test_every_captured_call_is_accepted_in_the_order_the_plugin_makes_them(self, kk):
        # Sequential on purpose: the deletes and the searches run against whatever
        # the adds left behind, which is how karakeep drives it.
        for call in _calls():
            r = kk.replay(call)
            assert r.status_code == 200, f"{call['label']}: {r.status_code} {r.text}"

    @pytest.mark.parametrize("label", [c["label"] for c in _calls()])
    def test_each_call_is_accepted_on_its_own(self, kk, label):
        r = kk.replay(_by_label(label))
        assert r.status_code == 200, r.text

    def test_no_key_the_plugin_sends_is_silently_dropped(self):
        # Pydantic ignores unknown keys by default, so a field the plugin starts
        # sending would vanish without a single test failing. This is the check
        # that a shape mismatch cannot pass quietly.
        for call in _calls():
            body = call["body"]
            if body is None:
                continue
            model = MODELS[call["path"]]
            unknown = set(body) - set(model.model_fields)
            assert not unknown, f"{call['label']} sends {sorted(unknown)}, the model has no such field"

    def test_the_bodyless_clear_post_is_not_a_validation_error(self, kk):
        clear = _by_label("clearIndex")
        assert clear["body"] is None
        # The plugin still sets `content-type: application/json` on a request with
        # no body at all. A route that declared a required body would 422 here.
        assert clear["headers"]["content-type"] == "application/json"
        assert kk.replay(clear).status_code == 200

    def test_the_lowercase_authorization_header_is_accepted(self, kk):
        for call in _calls():
            assert "authorization" in call["headers"]
            assert "Authorization" not in call["headers"]
        assert kk.replay(_by_label("search_minimal")).status_code == 200


# ---------------------------------------------------------------------------
# the serialisations that only exist on the TypeScript side
# ---------------------------------------------------------------------------


class TestSerialisation:
    def test_typescript_dates_arrive_as_iso_strings_and_are_accepted(self, kk):
        full = _doc("kk-full")
        # `datePublished` and `dateModified` are `z.date()` upstream. What actually
        # crosses the wire is whatever `JSON.stringify` made of a `Date`, and the
        # Python model never sees a date object.
        for field in ("createdAt", "datePublished", "dateModified"):
            assert isinstance(full[field], str), f"{field} is {type(full[field]).__name__}"
            assert full[field].endswith("Z")
        assert full["datePublished"] == "2025-06-01T00:00:00.000Z"
        assert kk.replay(_by_label("addDocuments")).status_code == 200

    def test_a_document_with_only_the_required_fields_is_stored(self, kk):
        assert set(_doc("kk-min")) == {"id", "userId", "tags"}
        r = kk.replay(_by_label("addDocuments_retry_unbatched"))
        assert r.status_code == 200
        body = r.json()
        assert body["received"] == 1
        # No url and no content: it still has to become a row, because karakeep
        # will ask for it back by id.
        assert body["stored"] + body["updated"] == 1

    def test_explicit_nulls_are_not_confused_with_absent_fields(self, kk):
        nulls = _doc("kk-nulls")
        assert nulls["url"] is None and nulls["title"] is None and nulls["content"] is None
        assert nulls["createdAt"] is None
        assert kk.replay(_by_label("addDocuments")).status_code == 200

    def test_a_non_ascii_tag_survives_the_round_trip(self, kk):
        assert _doc("kk-nulls")["tags"] == ["单个中文标签"]
        assert kk.replay(_by_label("addDocuments")).status_code == 200

    def test_both_filter_query_variants_are_understood(self, kk):
        filt = _by_label("search_full")["body"]["filter"]
        assert {f["type"] for f in filt} == {"eq", "in"}
        assert {f["field"] for f in filt} == {"userId", "id"}
        # `eq` carries `value`, `in` carries `values`. A parser that reads only
        # one of the two keys would drop half the filter and quietly widen it.
        assert "value" in next(f for f in filt if f["type"] == "eq")
        assert "values" in next(f for f in filt if f["type"] == "in")

    def test_the_plugin_fills_the_defaults_rather_than_omitting_them(self):
        minimal = _by_label("search_minimal")["body"]
        assert set(minimal) == {"query", "filter", "limit", "offset", "sort"}
        assert minimal["limit"] == 20 and minimal["offset"] == 0
        assert minimal["filter"] == [] and minimal["sort"] == []
        # `config` is ours, not karakeep's; the plugin never sends it, so the
        # Python default has to be the one we want.
        assert "config" not in minimal
        assert KarakeepSearchRequest().config == "full"


# ---------------------------------------------------------------------------
# what goes back, and whether TypeScript can parse it
# ---------------------------------------------------------------------------


class TestReplies:
    def _collect(self, kk) -> dict:
        out = {}
        for call in _calls():
            r = kk.replay(call)
            assert r.status_code == 200, f"{call['label']}: {r.text}"
            out[call["label"]] = _normalise(r.json())
        return out

    def test_the_committed_replies_are_what_the_routes_actually_return(self, kk):
        fresh = self._collect(kk)
        payload = {
            "_note": (
                "Generated by tests/test_karakeep_contract.py from the real routes. "
                "capture.ts feeds these back to the plugin. Regenerate with "
                "FACETMARK_UPDATE_CONTRACT=1 pytest tests/test_karakeep_contract.py"
            ),
            "by_label": fresh,
        }
        text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
        if REGENERATE:
            REPLIES.write_text(text, encoding="utf-8")
            pytest.skip("rewrote replies.json")
        have = json.loads(REPLIES.read_text(encoding="utf-8"))
        assert have.get("by_label") == fresh, (
            "replies.json is stale -- the routes now answer differently.\n"
            "  FACETMARK_UPDATE_CONTRACT=1 python -m pytest tests/test_karakeep_contract.py\n"
            "  then re-run the capture so the plugin side sees the new replies."
        )

    def test_search_replies_carry_every_field_karakeeps_type_declares_required(self, kk):
        for label in ("search_full", "search_minimal"):
            body = kk.replay(_by_label(label)).json()
            # SearchResponse{hits, totalHits, processingTimeMs} -- all three
            # required upstream. A route that omits one type-checks in Python and
            # breaks in TypeScript, which is the bug a single-language suite
            # cannot see.
            assert isinstance(body["hits"], list), label
            assert isinstance(body["totalHits"], int), label
            assert isinstance(body["processingTimeMs"], (int, float)), label
            for hit in body["hits"]:
                # `SearchResult.id` is `string`. Ours is the karakeep id, not the
                # integer bookmark id, and that distinction is the whole mapping.
                assert isinstance(hit["id"], str), f"{label}: id is {type(hit['id']).__name__}"
                assert isinstance(hit["score"], (int, float)), label

    def test_the_browse_path_also_answers_with_the_required_fields(self, kk):
        # An empty query goes down `_chronological`, which builds its reply by a
        # different route than search does. Same three fields have to be there.
        kk.replay(_by_label("addDocuments"))
        call = dict(_by_label("search_minimal"))
        call["body"] = {**call["body"], "query": ""}
        body = kk.replay(call).json()
        assert isinstance(body["hits"], list)
        assert isinstance(body["totalHits"], int)
        assert isinstance(body["processingTimeMs"], (int, float))
        assert body["engine"] == "chronological"

    def test_the_two_fields_typescript_throws_away_are_still_sent(self, kk):
        # The plugin's `search()` forwards only id/score/totalHits/processingTimeMs.
        # `engine` and `truncated` exist for our own debugging, and dropping them
        # would be a silent loss rather than a type error -- so pin them here.
        body = kk.replay(_by_label("search_full")).json()
        assert body["engine"].startswith("facetmark:")
        assert isinstance(body["truncated"], bool)


# ---------------------------------------------------------------------------
# guards on the capture side, checkable without node
# ---------------------------------------------------------------------------


class TestTheCaptureItself:
    """A contract test that quietly stops driving the real plugin is worse than none.

    None of this needs Node, which is the point: the Python job can tell that the
    other half is still wired up even though it cannot run it.
    """

    def test_the_capture_drives_the_shipping_plugin_rather_than_a_copy(self):
        src = (CONTRACT / "capture.ts").read_text(encoding="utf-8")
        assert 'from "../search-facetmark/src/index.ts"' in src
        assert "FacetmarkProvider" in src
        # If it ever grew its own `fetch(` to the service, it would be testing
        # itself. The only fetch it may define is the recorder that replaces the
        # global one.
        assert "globalThis.fetch = " in src

    def test_the_capture_is_reachable_from_an_npm_script(self):
        pkg = json.loads(
            (CONTRACT.parent / "typecheck" / "package.json").read_text(encoding="utf-8")
        )
        scripts = pkg["scripts"]
        assert "contract" in scripts and "contract:check" in scripts
        # Parameter properties in the plugin's constructor cannot be erased by
        # strip-only mode; the transform flag is load-bearing, not decorative.
        for name in ("contract", "contract:check"):
            assert "--experimental-transform-types" in scripts[name]
        assert scripts["contract:check"].endswith("--check")

    def test_ci_runs_both_halves(self):
        ci = (CONTRACT.parents[2] / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        assert "npm run contract:check" in ci
