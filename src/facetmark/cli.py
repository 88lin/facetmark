"""Command line. The entry point that has to work before any of the others do.

Ordering is enforced here rather than left to the user: ``index`` runs fetch,
enrich, embed-content, filter-intents, embed-intents, sessions and edges in the
one sequence that produces a correct index. The intent filter probes the live
index and asks whether each generated query retrieves the page it came from, so
content vectors have to exist first or the filter rejects good queries because
a facet is missing rather than because the query is bad.

``facetmark demo`` is the command that must work with no API key, no network and
no bookmark file, because a repository that cannot be run in sixty seconds does
not get evaluated.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, service
from . import health as healthmod
from .config import Settings, get_settings
from .db import SCHEMA_VERSION, apply_pending, connect, open_db, schema_status
from .importers.discovery import candidate_roots, discover_bookmark_files

_UTF8_ALIASES = frozenset({"utf-8", "utf8", "utf-8-sig", "utf8-sig", "cp65001"})


def _harden_stream(stream: object) -> None:
    """Stop one text stream from dying on a character the platform cannot spell.

    A Windows console talks UTF-8 to Python, but a *redirected* stdout is opened
    with the ANSI code page, so ``facetmark search > hits.txt`` on an en-US box
    raises UnicodeEncodeError the moment a result has a Chinese title. The same
    happens to any POSIX process started without a locale. A bookmark searcher
    that crashes on the titles it exists to find is not a bookmark searcher.

    Redirected output moves to UTF-8, which is what a file should hold anyway.
    An explicit ``PYTHONIOENCODING`` is the user's decision and is kept, but it
    is downgraded from raising to replacing: a mangled title still tells you
    which bookmark matched, a traceback tells you nothing.
    """
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:  # pytest capture, StringIO, an already-closed stream
        return
    encoding = (getattr(stream, "encoding", "") or "").lower().replace("_", "-")
    forgiving = getattr(stream, "errors", None) not in (None, "strict", "surrogateescape")
    try:
        if encoding in _UTF8_ALIASES or os.environ.get("PYTHONIOENCODING"):
            if not forgiving:
                reconfigure(errors="replace")
        else:
            reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, OSError):  # detached, or a stream that only pretends to be one
        return


def _harden_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        _harden_stream(stream)


_harden_stdio()

app = typer.Typer(
    name="facetmark",
    help="Bookmark retrieval that indexes why you saved a page, not just what it says.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err = Console(stderr=True)


# ---------------------------------------------------------------------------
# shared plumbing
# ---------------------------------------------------------------------------


def _settings(db: Path | None = None, mock: bool = False) -> Settings:
    st = get_settings()
    over: dict = {}
    if db is not None:
        over["data_dir"] = str(db.parent if db.suffix else db)
        if db.suffix:
            over["db_name"] = db.name
    if mock:
        over["use_mock_provider"] = True
    if over:
        st = get_settings(**{**st.model_dump(), **over})
    st.ensure_dirs()
    return st


def _open(st: Settings):
    return open_db(st.db_path)


def _fmt_ts(ts: int | None) -> str:
    if not ts:
        return "-"
    import datetime as _dt

    return _dt.datetime.fromtimestamp(ts, tz=_dt.timezone.utc).strftime("%Y-%m-%d")


def _emit(obj, as_json: bool) -> bool:
    """Print JSON and report whether it did, so callers can skip the pretty path."""
    if as_json:
        console.print_json(json.dumps(obj, ensure_ascii=False, default=str))
        return True
    return False


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


@app.command()
def version() -> None:
    """Print the version."""
    console.print(f"facetmark {__version__}")


@app.command("import")
def import_cmd(
    path: Path | None = typer.Argument(
        None, exists=True, readable=True,
        help="Netscape bookmarks.html or Chrome Bookmarks JSON. "
             "Omit to read the live browser profile.",
    ),
    db: Path | None = typer.Option(None, "--db", help="Database file or data directory."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Import a browser bookmark export. Never writes back to the browser.

    With no path, the live Chromium-family profile is located automatically.
    That is the whole first-run experience on Windows, where the file is buried
    at ``%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Bookmarks`` and
    nobody types it from memory. If more than one profile is installed the
    choice is not guessed -- importing the wrong person's bookmarks is worse
    than one extra command -- so the candidates are printed and you pick.
    """
    if path is None:
        path = _the_only_profile(json_out)
    st = _settings(db)
    conn = _open(st)
    try:
        stats = service.import_file(conn, str(path), settings=st)
    finally:
        conn.close()
    if _emit(stats, json_out):
        return
    t = Table(title=f"imported {path.name}", show_header=False, box=None)
    for k in ("parsed", "inserted", "updated", "merged_duplicates", "non_indexable",
              "missing_dates", "privacy_skipped", "folders", "max_depth",
              "timestamp_unit", "source"):
        t.add_row(k, str(stats[k]))
    console.print(t)
    for w in stats["warnings"][:10]:
        err.print(f"[yellow]warning[/yellow] {w}")


def _the_only_profile(json_out: bool) -> Path:
    """Resolve ``facetmark import`` with no argument, or explain why it cannot."""
    found = discover_bookmark_files()
    if len(found) == 1:
        p, browser, profile = found[0]
        err.print(f"[dim]reading {browser} / {profile}: {p}[/dim]")
        return p
    if not found:
        if json_out:
            console.print(json.dumps(
                {"error": "no browser profile found",
                 "searched": [str(r) for r, _, _ in candidate_roots()]},
                ensure_ascii=False, indent=2,
            ))
        else:
            err.print("[red]no browser profile found.[/red] looked in:")
            for root, browser, _ in candidate_roots():
                err.print(f"  [dim]{browser:<9}[/dim] {root}")
            err.print("\npass the file directly: [bold]facetmark import <path>[/bold]")
        raise typer.Exit(2)
    if json_out:
        console.print(json.dumps(
            {"error": "several browser profiles found",
             "profiles": [{"path": str(p), "browser": b, "profile": prof}
                          for p, b, prof in found]},
            ensure_ascii=False, indent=2,
        ))
    else:
        err.print(f"[yellow]{len(found)} browser profiles found.[/yellow] "
                  "pick one rather than let it be guessed:")
        for p, browser, profile in found:
            err.print(f"  [bold]facetmark import {p}[/bold]  [dim]# {browser} / {profile}[/dim]")
    raise typer.Exit(2)


@app.command()
def browsers(json_out: bool = typer.Option(False, "--json")) -> None:
    """List the live browser profiles that can be imported.

    Answers "is my browser even findable" without touching the database, which
    is the first question on a machine where ``import`` came up empty.
    """
    found = discover_bookmark_files()
    if _emit([{"path": str(p), "browser": b, "profile": prof} for p, b, prof in found],
             json_out):
        return
    if not found:
        console.print("[dim]no live browser profile found. searched:[/dim]")
        for root, browser, _ in candidate_roots():
            console.print(f"  [dim]{browser:<9} {root}[/dim]")
        return
    t = Table(title="live browser profiles", box=None)
    for col in ("browser", "profile", "path"):
        t.add_column(col)
    for p, browser, profile in found:
        t.add_row(browser, profile, str(p))
    console.print(t)


@app.command()
def migrate(
    db: Path | None = typer.Option(None, "--db"),
    check: bool = typer.Option(False, "--check",
                               help="Report and exit non-zero if behind. Changes nothing."),
    backup: bool = typer.Option(True, "--backup/--no-backup",
                                help="Snapshot the file before the first migration."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Bring the database schema up to what this build expects.

    Opening a database migrates it anyway; this command exists so the upgrade
    can be done deliberately -- before a long index run rather than during one
    -- and so ``--check`` can gate a deploy without touching the file.
    """
    st = _settings(db)
    if check and not Path(st.db_path).exists():
        # Do not create a file just to answer a question about it.
        if not _emit({"found": None, "expected": SCHEMA_VERSION, "fresh": True,
                      "current": True, "too_new": False, "pending": []}, json_out):
            console.print("[dim]no database yet[/dim]")
        return
    conn = connect(st.db_path)
    try:
        status = schema_status(conn)
        if status.too_new:
            err.print(f"[red]database is at schema v{status.found}, this build knows "
                      f"v{status.expected}. Upgrade facetmark.[/red]")
            raise typer.Exit(2)
        if check:
            if _emit(status.as_dict(), json_out):
                raise typer.Exit(1 if status.pending else 0)
            if status.fresh:
                console.print("[dim]no database yet[/dim]")
            elif status.current:
                console.print(f"schema v{status.found} [green]up to date[/green]")
            else:
                console.print(f"schema v{status.found}, [yellow]{len(status.pending)} "
                              f"pending[/yellow] -> v{status.expected}")
                for m in status.pending:
                    console.print(f"  [dim]v{m.version}[/dim] {m.note}")
            raise typer.Exit(1 if status.pending else 0)

        done, saved = apply_pending(conn, backup=backup)
        out = {"from": status.found, "to": schema_status(conn).found,
               "applied": [{"version": m.version, "note": m.note} for m in done],
               "backup": str(saved) if saved else None}
    finally:
        conn.close()
    if _emit(out, json_out):
        return
    if not done:
        console.print(f"schema v{out['to']} [green]up to date[/green]")
        return
    if saved:
        console.print(f"[dim]backup {saved.name}[/dim]")
    for m in done:
        console.print(f"  [green]v{m.version}[/green] {m.note}")
    console.print(f"schema v{out['from']} -> v{out['to']}")


@app.command()
def index(
    db: Path | None = typer.Option(None, "--db"),
    no_fetch: bool = typer.Option(False, "--no-fetch",
                                  help="Skip crawling. Index titles only."),
    limit: int | None = typer.Option(None, "--limit", help="Cap bookmarks per stage."),
    force: bool = typer.Option(False, "--force", help="Redo work already done."),
    mock: bool = typer.Option(False, "--mock", help="Offline deterministic provider."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Build the whole index: fetch, enrich, embed, sessions, edges."""
    st = _settings(db, mock)
    if not st.api_key and not st.use_mock_provider:
        err.print("[yellow]no FACETMARK_API_KEY set; falling back to --mock[/yellow]")
        st = _settings(db, mock=True)
    conn = _open(st)
    try:
        def progress(name: str, value) -> None:
            if not json_out:
                console.print(f"  [dim]{name}[/dim] {value}")

        rep = asyncio.run(service.index_all(
            conn, settings=st, fetch=not no_fetch, limit=limit, force=force,
            progress=progress,
        ))
    finally:
        conn.close()
    if _emit(rep.as_dict(), json_out):
        return
    t = Table(title="index", box=None)
    t.add_column("stage")
    t.add_column("seconds", justify="right")
    for k, v in rep.seconds.items():
        t.add_row(k, f"{v:.2f}")
    console.print(t)


@app.command()
def reindex(
    db: Path | None = typer.Option(None, "--db"),
    mock: bool = typer.Option(False, "--mock"),
) -> None:
    """Rebuild everything from scratch, keeping the bookmarks themselves."""
    index(db=db, no_fetch=False, limit=None, force=True, mock=mock, json_out=False)


@app.command()
def search(
    query: str = typer.Argument(...),
    db: Path | None = typer.Option(None, "--db"),
    limit: int = typer.Option(10, "-n", "--limit"),
    quick: bool = typer.Option(False, "--quick", help="Lexical only, no model call."),
    config: str = typer.Option("full", "--config", help="full or an ablation rung A-E."),
    mock: bool = typer.Option(False, "--mock"),
    explain: bool = typer.Option(False, "--explain", help="Show which facets matched."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Search the library."""
    from .search.pipeline import ALL_CONFIGS, default_config

    st = _settings(db, mock)
    conn = _open(st)
    try:
        if quick:
            resp = service.quick_search(conn, query, limit=limit)
        else:
            cfg = default_config(st) if config in ("", "full") else (
                ALL_CONFIGS.get(config) or ALL_CONFIGS.get(config.upper())
            )
            if cfg is None:
                err.print(f"[red]unknown config {config!r}[/red]")
                raise typer.Exit(2)
            resp = asyncio.run(service.search(
                conn, query, limit=limit, config=cfg, settings=st))
        payload = resp.as_dict()
    finally:
        conn.close()

    if _emit(payload, json_out):
        return
    u = resp.understanding
    if u is not None:
        console.print(f"[dim]labels[/dim] {','.join(u.labels)}  "
                      f"[dim]episodic[/dim] {u.episodic_confidence:.1f}  "
                      f"[dim]facets[/dim] {resp.facet_sizes}")
    t = Table(box=None)
    t.add_column("#", justify="right")
    t.add_column("score", justify="right")
    t.add_column("title", overflow="fold", max_width=52)
    t.add_column("domain")
    t.add_column("added")
    if explain:
        t.add_column("facets")
    for i, h in enumerate(resp.hits, 1):
        row = [str(i), f"{h.score:.4f}", h.title or h.url, h.domain, _fmt_ts(h.date_added)]
        if explain:
            row.append(",".join(h.facets))
        t.add_row(*row)
    console.print(t)
    if resp.expanded:
        console.print("[dim]related[/dim]")
        for h in resp.expanded[:5]:
            console.print(f"  via {h.via} ({h.via_kind}): {h.title or h.url}")


@app.command()
def show(
    bookmark_id: int = typer.Argument(...),
    db: Path | None = typer.Option(None, "--db"),
    body: bool = typer.Option(False, "--body"),
) -> None:
    """Print one bookmark record as JSON."""
    st = _settings(db)
    conn = _open(st)
    try:
        rec = service.bookmark_record(conn, bookmark_id, settings=st, include_body=body)
    finally:
        conn.close()
    if rec is None:
        err.print(f"[red]no bookmark {bookmark_id}[/red]")
        raise typer.Exit(1)
    console.print_json(json.dumps(rec, ensure_ascii=False, default=str))


@app.command()
def sessions(
    db: Path | None = typer.Option(None, "--db"),
    limit: int = typer.Option(20, "-n", "--limit"),
) -> None:
    """List reconstructed saving episodes."""
    st = _settings(db)
    conn = _open(st)
    try:
        rows = service.session_list(conn, limit=limit)
    finally:
        conn.close()
    t = Table(box=None)
    t.add_column("id", justify="right")
    t.add_column("when")
    t.add_column("size", justify="right")
    t.add_column("span")
    t.add_column("label", overflow="fold", max_width=48)
    for r in rows:
        span = r["span_seconds"]
        t.add_row(str(r["session_id"]), _fmt_ts(r["started_at"]), str(r["size"]),
                  f"{span // 60}m", r["label"])
    console.print(t)


@app.command()
def health(
    db: Path | None = typer.Option(None, "--db"),
    check: bool = typer.Option(False, "--check", help="Actually probe the network."),
    limit: int = typer.Option(50, "--limit"),
    no_external: bool = typer.Option(False, "--no-external",
                                     help="Local probes only. Cannot confirm 'gone'."),
    no_save_recovered: bool = typer.Option(
        False, "--no-save-recovered",
        help="Do not file reader-proxy text into the index. Makes the sweep "
             "read-only apart from the health log, which is what you want "
             "before measuring anything against this library."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Link health, and whether the metabolism layer can see any of it.

    Reports only; nothing is ever deleted or hidden. The ``cold_layer`` block
    exists because the two are coupled and the coupling is easy to miss: the
    demotion in :mod:`facetmark.search.decay` needs a dead verdict or a
    supersession edge, so on a library that has never been checked the layer
    runs on edges alone and silently does almost nothing.
    """
    st = _settings(db)
    if no_external:
        st = get_settings(**{**st.model_dump(), "health_enable_external": False})
    from .search.decay import cold_census

    conn = _open(st)
    try:
        if check:
            rep = asyncio.run(healthmod.check_bookmarks(
                conn, limit=limit, settings=st, save_recovered=not no_save_recovered))
            conn.commit()
            payload = {**rep.as_dict(), "summary": healthmod.summary(conn)}
        else:
            payload = {"summary": healthmod.summary(conn),
                       "due_now": len(healthmod.due_for_check(conn, limit=100000))}
        payload["cold_layer"] = cold_census(
            conn, age_days=st.decay_age_days, min_body_chars=st.min_body_chars
        )
    finally:
        conn.close()
    if _emit(payload, json_out):
        return
    t = Table(title="link health", box=None, show_header=False)
    for k, v in payload["summary"].items():
        t.add_row(k, str(v))
    console.print(t)
    if check:
        console.print(f"[dim]probed[/dim] {payload['probed']}  "
                      f"[dim]escalated[/dim] {payload['escalated']}  "
                      f"[dim]bodies recovered[/dim] {payload['recovered_bodies']}")
        if payload["confirmed_gone"]:
            console.print(f"[yellow]{len(payload['confirmed_gone'])} link(s) now meet the "
                          f"two-confirmation bar for 'gone'. They stay in the library.[/yellow]")
    else:
        console.print(f"[dim]due for a check now:[/dim] {payload['due_now']}")

    cl = payload["cold_layer"]
    console.print(
        f"[dim]cold layer:[/dim] {cl['cold']} page(s) "
        f"({cl['condition3_by_dead_verdict']} via a dead verdict, "
        f"{cl['condition3_by_supersession']} via a supersession edge); "
        f"{cl['servable_cold']} of them still have indexed text"
    )
    if "health_never_checked" in cl["degenerate_conditions"]:
        console.print(
            "[yellow]No health check has ever run on this library, so the "
            "demotion layer's third condition is running on supersession edges "
            "alone. Try `fm health --check` before drawing conclusions about "
            "how the library ranks.[/yellow]"
        )
    if "never_opened_selects_everything" in cl["degenerate_conditions"]:
        console.print(
            f"[yellow]All {cl['bookmarks']} bookmarks have open_count = 0, so "
            f"the 'never opened' condition currently selects the whole library. "
            f"Browser exports carry no usage telemetry; this resolves itself "
            f"once facetmark has observed opens of its own.[/yellow]"
        )


@app.command()
def stats(
    db: Path | None = typer.Option(None, "--db"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Index size and coverage."""
    st = _settings(db)
    conn = _open(st)
    try:
        payload = service.library_stats(conn, st)
    finally:
        conn.close()
    if _emit(payload, json_out):
        return
    t = Table(box=None, show_header=False)
    for k, v in payload.items():
        t.add_row(k, json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else str(v))
    console.print(t)


@app.command()
def token(
    db: Path | None = typer.Option(None, "--db"),
    rotate: bool = typer.Option(False, "--rotate", help="Invalidate the old token."),
) -> None:
    """Print the pairing token the browser extension needs."""
    st = _settings(db)
    tok = service.rotate_token(st) if rotate else service.pairing_token(st)
    console.print(tok)
    err.print(f"[dim]stored at {st.token_path}[/dim]")


@app.command()
def serve(
    db: Path | None = typer.Option(None, "--db"),
    host: str | None = typer.Option(None, "--host"),
    port: int | None = typer.Option(None, "--port"),
    mock: bool = typer.Option(False, "--mock"),
) -> None:
    """Run the local HTTP service the browser extension talks to."""
    from .api import serve as _serve

    st = _settings(db, mock)
    over = {}
    if host:
        over["host"] = host
    if port:
        over["port"] = port
    if over:
        st = get_settings(**{**st.model_dump(), **over})
    if st.host not in ("127.0.0.1", "localhost", "::1"):
        err.print(f"[yellow]binding to {st.host}: the index contains your whole "
                  f"browsing interest graph. Only do this on a trusted network.[/yellow]")
    _serve(st)


@app.command()
def mcp(
    db: Path | None = typer.Option(None, "--db"),
    mock: bool = typer.Option(False, "--mock"),
) -> None:
    """Run the MCP server on stdio, for Claude Desktop and other MCP clients."""
    from .mcp_server import main as _main

    _main(_settings(db, mock))


@app.command()
def demo(
    db: Path | None = typer.Option(None, "--db", help="Where to build the demo index."),
    size: int = typer.Option(60, "--size", help="Synthetic pages to generate."),
    keep: bool = typer.Option(False, "--keep", help="Leave the demo database in place."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Build a synthetic library offline and search it. No key, no network.

    The demo corpus has real page bodies, which matters: on a title-only index
    the intent facet has almost nothing to work with, so a demo built from
    titles alone would misrepresent the system.
    """
    from .eval import run_demo

    payload = asyncio.run(run_demo(db=db, size=size, keep=keep, console=console,
                                   quiet=json_out))
    if _emit(payload, json_out):
        return


@app.command("eval")
def eval_cmd(
    db: Path | None = typer.Option(None, "--db"),
    ablation: bool = typer.Option(False, "--ablation", help="Run rungs A through E."),
    rungs: str = typer.Option(
        "", "--rungs",
        help="Comma-separated rungs to run instead of the A-E ladder, e.g. "
             "'C,C_notri'. Deltas compare adjacent entries in the order given."),
    size: int = typer.Option(120, "--size", help="Synthetic corpus size when building."),
    build: bool = typer.Option(True, "--build/--no-build",
                               help="Generate the corpus, or evaluate an existing db."),
    bootstrap: int = typer.Option(1000, "--bootstrap", help="Resamples for the CI."),
    queries: Path | None = typer.Option(
        None, "--queries",
        help="JSONL of {text, qtype, target_url} to evaluate an existing library."),
    concurrency: int = typer.Option(
        1, "--concurrency",
        help="Queries in flight per rung. >1 makes p50/p95 meaningless; use it for "
             "the quality numbers and re-run at 1 on a subsample for latency."),
    out: Path | None = typer.Option(None, "--out", help="Write the full report as JSON."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Run the retrieval evaluation, optionally as an A-E ablation.

    Reports Recall@1/5/10 and MRR@10 split by query type, with bootstrap
    confidence intervals and McNemar tests between adjacent rungs. Always prints
    which provider and which reranker actually ran: under the mock provider the
    numbers are a plumbing check, not a quality measurement.

    With ``--no-build --db LIB --queries FILE`` it measures a library you
    already indexed, using whatever provider the environment names. That is the
    mode that produces a number worth quoting.
    """
    from .eval import run_eval

    payload = asyncio.run(run_eval(
        db=db, ablation=ablation, size=size, build=build, bootstrap=bootstrap,
        queries_path=queries, concurrency=concurrency,
        rungs=[r for r in rungs.split(",") if r.strip()] or None,
        console=None if json_out else console,
    ))
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        err.print(f"[dim]wrote {out}[/dim]")
    if _emit(payload, json_out):
        return


def main() -> None:  # pragma: no cover - console script shim
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":  # pragma: no cover
    main()
