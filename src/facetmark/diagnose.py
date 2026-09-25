"""``facetmark doctor``: why is it doing that?

Ported from hister's ``doctor`` command and ``server/diagnostics``, which
answers the question every local-first tool eventually has to: the thing is
installed, it starts, and it returns nothing -- where did it go wrong? The
shape is theirs: a flat list of ``{name, status, message}``, one line each,
machine-readable with ``--json``, and a non-zero exit when any check errors.

Two rules, also theirs, and they are what keep the command trustworthy:

*It repairs nothing.* A diagnosis that edits the thing it is diagnosing cannot
be run twice with the same meaning, and cannot be run at all by somebody who
is not yet sure they want it changed. Every check here reads.

*It calls no model.* Reporting "your endpoint is unreachable" would need a
request, and a diagnostic that costs money or leaks a query to a third party
is one people learn not to run. What can be checked without the network --
which backend is configured, whether a key is set, whether the stored vectors
match the settings -- is checked; the rest is reported as configuration, not
as health.

The checks are the failure modes this project actually has. Most of them exist
because something in the codebase already defends against them: ``embed_dim``
drift raises :class:`SchemaMismatch` at write time, and
``vector_facets_present`` exists because a chat-only endpoint answers
``/chat/completions`` and 404s on ``/embeddings``, leaving a library with no
vectors and a profile that only ranks with them.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import Settings, get_settings
from .migrations import schema_status

#: Worst-first, so a caller can sort or colour by severity without a lookup.
SEVERITY = {"error": 2, "warn": 1, "ok": 0}


@dataclass(frozen=True)
class Check:
    """One answered question. ``name`` is dotted so related checks group."""

    name: str
    status: str
    message: str

    def as_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "message": self.message}


def _count(conn: sqlite3.Connection, sql: str, *params) -> int:
    try:
        row = conn.execute(sql, params).fetchone()
    except sqlite3.Error:
        return -1
    return int(row[0]) if row and row[0] is not None else 0


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,)
    ).fetchone() is not None


def check_data_dir(st: Settings) -> list[Check]:
    d = Path(st.data_dir)
    if not d.exists():
        return [Check("data_dir", "error", f"{d} does not exist")]
    probe = d / ".facetmark-write-probe"
    try:
        probe.write_text("", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return [Check("data_dir", "error", f"{d} is not writable: {exc}")]
    return [Check("data_dir", "ok", f"{d} exists and is writable")]


def check_config(st: Settings) -> list[Check]:
    """Which settings are in play, and where each came from.

    The source is the part worth printing. An exported ``FACETMARK_*`` variable
    outranks ``config.toml``, so "I edited the file and nothing changed" is the
    single most common configuration confusion, and it is invisible until
    something tells you which source won.
    """
    from .admin import settings_view

    try:
        report = settings_view(st)
    except Exception as exc:  # noqa: BLE001 - a diagnosis must not die diagnosing
        return [Check("config", "error", f"settings could not be read: {exc}")]
    out = [Check("config.file", "ok", f"config.toml path: {report['path']}")]
    from_env = [r["key"] for r in report["settings"] if r["source"] == "env"]
    if from_env:
        out.append(Check(
            "config.env", "ok",
            "set by environment and not editable from the file or the UI: "
            + ", ".join(sorted(from_env)),
        ))
    return out


def check_schema(conn: sqlite3.Connection) -> list[Check]:
    try:
        status = schema_status(conn)
    except sqlite3.Error as exc:
        return [Check("schema", "error",
                      f"the database has no schema table ({exc}); it is not a "
                      "facetmark library, or it was never initialised")]
    if status.found is None:
        return [Check("schema", "warn", "no schema version recorded; this looks "
                                        "like a database facetmark did not create")]
    if status.pending:
        names = ", ".join(str(m.version) for m in status.pending)
        return [Check("schema", "error",
                      f"database is at version {status.found}, this build expects "
                      f"{status.expected} (missing {names}). Run: facetmark migrate")]
    if status.found > status.expected:
        return [Check("schema", "error",
                      f"database is at version {status.found}, newer than this "
                      f"build's {status.expected}. Upgrade facetmark.")]
    return [Check("schema", "ok", f"version {status.found}, current")]


def check_library(conn: sqlite3.Connection) -> list[Check]:
    total = _count(conn, "SELECT COUNT(*) FROM bookmark")
    if total == 0:
        return [Check("library", "warn",
                      "no bookmarks yet. Run: facetmark import")]
    indexable = _count(conn, "SELECT COUNT(*) FROM bookmark WHERE indexable=1")
    out = [Check("library", "ok", f"{total} bookmarks, {indexable} indexable")]

    dated = _count(conn, "SELECT COUNT(*) FROM bookmark WHERE date_added IS NOT NULL"
                         " AND date_added > 0")
    if dated == 0:
        out.append(Check("library.dates", "warn",
                         "no bookmark carries a save date; the episodic facet and "
                         "every added:/sort:date query have nothing to work with"))
    elif dated < total:
        out.append(Check("library.dates", "ok",
                         f"{total - dated} bookmarks have no save date"))
    return out


def check_content(conn: sqlite3.Connection) -> list[Check]:
    indexable = _count(conn, "SELECT COUNT(*) FROM bookmark WHERE indexable=1")
    if indexable == 0:
        return []
    bodies = _count(conn, "SELECT COUNT(*) FROM content WHERE body_text IS NOT NULL"
                          " AND body_text <> ''")
    if bodies == 0:
        return [Check("content", "warn",
                      "no page text has been fetched. Search is matching titles "
                      "and URLs only. Run: facetmark index")]
    share = bodies / indexable
    status = "ok" if share >= 0.5 else "warn"
    return [Check("content", status,
                  f"{bodies} of {indexable} indexable pages have body text "
                  f"({share:.0%})")]


def check_lexical(conn: sqlite3.Connection) -> list[Check]:
    """The two FTS indexes. A missing one is a facet that answers nothing."""
    out = []
    total = _count(conn, "SELECT COUNT(*) FROM bookmark")
    for table, what in (("fts_seg", "word index"), ("fts_tri", "trigram index")):
        if not _table_exists(conn, table):
            out.append(Check(f"lexical.{table}", "error",
                             f"the {what} does not exist. Run: facetmark reindex"))
            continue
        n = _count(conn, f"SELECT COUNT(*) FROM {table}")
        if total and n == 0:
            out.append(Check(f"lexical.{table}", "error",
                             f"the {what} is empty while the library has {total} "
                             "bookmarks. Run: facetmark reindex"))
        elif total and n < total * 0.9:
            out.append(Check(f"lexical.{table}", "warn",
                             f"the {what} has {n} rows for {total} bookmarks; "
                             "some pages are not searchable by words"))
        else:
            out.append(Check(f"lexical.{table}", "ok", f"{n} rows"))
    return out


def check_vectors(conn: sqlite3.Connection, st: Settings) -> list[Check]:
    """Where a library most often turns out to be quietly lexical-only.

    Three separate ways to have no vectors, and they need different answers:
    the tables were never created, they exist and are empty, or they hold
    vectors built with settings that no longer match -- which is a hard error at
    write time and would otherwise only surface on the next index run.
    """
    from .db import get_meta

    out: list[Check] = []
    stored_dim = get_meta(conn, "embed_dim")
    stored_model = get_meta(conn, "embed_model")
    if stored_dim is not None and int(stored_dim) != st.embed_dim:
        out.append(Check(
            "vectors.dim", "error",
            f"stored vectors are {stored_dim}-dimensional, settings say "
            f"{st.embed_dim}. Every stored vector is unusable until they agree. "
            "Run: facetmark reindex --vectors",
        ))
    if stored_model is not None and stored_model != st.embed_model:
        out.append(Check(
            "vectors.model", "error",
            f"stored vectors were built with {stored_model!r}, settings say "
            f"{st.embed_model!r}. Run: facetmark reindex --vectors",
        ))

    if not _table_exists(conn, "vec_content"):
        out.append(Check("vectors", "warn",
                         "no vector tables; search is lexical only. That is a "
                         "working setup, and the one the measurements call the "
                         "weaker of the two on vague queries."))
        return out
    n = _count(conn, "SELECT COUNT(*) FROM vec_content")
    if n == 0:
        out.append(Check(
            "vectors", "warn",
            "the vector table exists but is empty, so every vector facet returns "
            "nothing. A key that answers /chat/completions and 404s on "
            "/embeddings looks exactly like this. Run: facetmark index",
        ))
    else:
        out.append(Check("vectors", "ok", f"{n} content vectors, dim {st.embed_dim}"))
    return out


def check_provider(st: Settings) -> list[Check]:
    """Reported, not probed: no request leaves this command."""
    if st.use_mock_provider:
        return [Check("provider", "warn",
                      "the mock provider is configured. It hashes text into a "
                      "vector, which is deterministic and meaningless -- fine for "
                      "a demo, not for a real library.")]
    out = [Check("provider.models", "ok",
                 f"chat {st.chat_model or '(unset)'}, embed "
                 f"{st.embed_model or '(unset)'} at {st.embed_dim} dims")]
    if st.embed_backend == "local":
        out.append(Check("provider.embed", "ok",
                         "embeddings are computed locally; no key needed"))
    elif not st.api_key:
        out.append(Check("provider.embed", "warn",
                         "no API key is set and the embedding backend is not "
                         "local, so nothing can be embedded or enriched"))
    else:
        out.append(Check("provider.embed", "ok",
                         f"key set, base url {st.base_url or '(default)'}"))
    return out


def check_queue(conn: sqlite3.Connection) -> list[Check]:
    if not _table_exists(conn, "fetch_queue"):
        return []
    waiting = _count(conn, "SELECT COUNT(*) FROM fetch_queue WHERE state='pending'")
    if waiting > 0:
        return [Check("queue", "ok", f"{waiting} pages waiting to be fetched. "
                                     "Run: facetmark index")]
    return [Check("queue", "ok", "nothing waiting to be fetched")]


def check_privacy(conn: sqlite3.Connection, st: Settings) -> list[Check]:
    excluded = tuple(st.privacy_excluded_domains or ())
    skipped = _count(conn, "SELECT COUNT(*) FROM bookmark WHERE privacy_skipped=1")
    if not excluded:
        return [Check("privacy", "ok", "no domains are excluded from fetching")]
    return [Check("privacy", "ok",
                  f"{len(excluded)} excluded domain(s), {skipped} bookmarks never "
                  f"fetched because of them: {', '.join(excluded[:5])}")]


def check_token(st: Settings) -> list[Check]:
    if not Path(st.token_path).exists():
        return [Check("token", "ok",
                      "no pairing token yet; one is written the first time you "
                      "run facetmark serve")]
    return [Check("token", "ok", f"pairing token at {st.token_path}")]


def run_checks(
    conn: sqlite3.Connection | None, settings: Settings | None = None
) -> list[Check]:
    """Every check, in the order a reader should meet them.

    Configuration first, then the database, then what is in it, then what can
    search it: a failure early on explains most failures later, and reading top
    to bottom should feel like being walked through the install.

    ``conn`` is ``None`` when there is no database file yet. That is a normal
    state on a fresh install, not an error, and it is the caller's job to pass
    ``None`` rather than create one: opening a library the usual way would both
    write the file and migrate it, which this command promises not to do.
    """
    st = settings or get_settings()
    checks: list[Check] = []
    checks += check_data_dir(st)
    checks += check_config(st)
    if conn is None:
        checks.append(Check("database", "warn",
                            f"no database at {st.db_path} yet. "
                            "Run: facetmark import"))
        checks += check_provider(st)
        checks += check_token(st)
        return checks
    checks.append(Check("database", "ok", str(st.db_path)))
    checks += check_schema(conn)
    checks += check_library(conn)
    checks += check_content(conn)
    checks += check_lexical(conn)
    checks += check_vectors(conn, st)
    checks += check_provider(st)
    checks += check_queue(conn)
    checks += check_privacy(conn, st)
    checks += check_token(st)
    return checks


def worst(checks: list[Check]) -> str:
    """The most severe status present, ``"ok"`` for an empty list."""
    return max((c.status for c in checks), key=lambda s: SEVERITY.get(s, 0), default="ok")


__all__ = ["Check", "SEVERITY", "run_checks", "worst"]
