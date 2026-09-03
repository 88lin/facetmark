"""The command line has to survive the terminal it is given.

Everything else in this suite runs against Python objects. These tests run
against the byte-level contract between the process and whatever it was piped
into, because that is where a Chinese bookmark library meets a Windows console
and loses.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from facetmark.cli import _harden_stdio, _harden_stream

CJK = "\u4e2d\u6587\u6807\u9898\u6d4b\u8bd5"  # 中文标题测试


def _stream(encoding: str, errors: str = "strict") -> io.TextIOWrapper:
    return io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors=errors)


class TestNarrowStdioIsWidened:
    """A redirected Windows stdout is the ANSI code page. CJK does not fit."""

    def test_a_codepage_stream_is_moved_to_utf8(self, monkeypatch):
        monkeypatch.delenv("PYTHONIOENCODING", raising=False)
        s = _stream("cp1252")
        _harden_stream(s)
        assert s.encoding == "utf-8"
        s.write(CJK)
        s.flush()
        assert s.buffer.getvalue().decode("utf-8") == CJK

    def test_an_ascii_stream_is_moved_to_utf8(self, monkeypatch):
        """POSIX with no locale at all lands here, not just Windows."""
        monkeypatch.delenv("PYTHONIOENCODING", raising=False)
        s = _stream("ascii", errors="surrogateescape")
        _harden_stream(s)
        assert s.encoding == "utf-8"
        s.write(CJK)  # would raise before the move

    def test_utf8_is_left_at_utf8(self, monkeypatch):
        monkeypatch.delenv("PYTHONIOENCODING", raising=False)
        s = _stream("utf-8")
        _harden_stream(s)
        assert s.encoding == "utf-8"
        assert s.errors == "replace"

    def test_an_already_forgiving_stream_is_not_touched(self, monkeypatch):
        monkeypatch.delenv("PYTHONIOENCODING", raising=False)
        s = _stream("utf-8", errors="backslashreplace")
        _harden_stream(s)
        assert (s.encoding, s.errors) == ("utf-8", "backslashreplace")

    def test_hardening_twice_changes_nothing(self, monkeypatch):
        monkeypatch.delenv("PYTHONIOENCODING", raising=False)
        s = _stream("cp1252")
        _harden_stream(s)
        first = (s.encoding, s.errors)
        _harden_stream(s)
        assert (s.encoding, s.errors) == first


class TestAnExplicitChoiceIsKept:
    """PYTHONIOENCODING is the user talking. Obey it -- but do not let it raise."""

    def test_the_requested_encoding_survives(self, monkeypatch):
        monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
        s = _stream("cp1252")
        _harden_stream(s)
        assert s.encoding == "cp1252"

    def test_but_an_unspellable_title_degrades_instead_of_raising(self, monkeypatch):
        monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
        s = _stream("cp1252")
        _harden_stream(s)
        s.write(CJK)
        s.flush()
        assert s.buffer.getvalue() == b"?" * len(CJK)


class TestStreamsThatAreNotReallyStreams:
    def test_a_stream_without_reconfigure_is_skipped(self):
        _harden_stream(io.StringIO())  # pytest capture objects look like this

    def test_a_detached_stream_does_not_take_the_process_down(self, monkeypatch):
        monkeypatch.delenv("PYTHONIOENCODING", raising=False)
        s = _stream("cp1252")
        s.detach()
        _harden_stream(s)

    def test_hardening_the_live_process_is_safe_under_pytest(self):
        _harden_stdio()
        assert sys.stdout is not None


class TestTheWholeProcessSurvivesTheRedirect:
    """The unit tests above check the lever. This checks the machine.

    Reproduces the real shape: no ``PYTHONIOENCODING``, a locale that gives
    Python an ASCII stdout, and output going to a pipe rather than a terminal --
    which is exactly what ``facetmark search > hits.txt`` looks like on a
    Windows box whose ANSI code page cannot hold the library's titles.
    """

    ENV = {
        "LC_ALL": "C",
        "LANG": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONUTF8": "0",
    }

    def _run(self, tmp_path: Path, body: str) -> subprocess.CompletedProcess[bytes]:
        script = tmp_path / "probe.py"
        script.write_text(textwrap.dedent(body), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}
        env.update(self.ENV)
        env["PYTHONPATH"] = os.pathsep.join(sys.path)
        return subprocess.run(
            [sys.executable, str(script)], capture_output=True, env=env, timeout=120
        )

    def test_a_bare_interpreter_really_does_die_here(self, tmp_path):
        """Guard the guard: if this ever passes, the test below proves nothing."""
        r = self._run(tmp_path, f'''
            import sys
            sys.stdout.write({CJK!r})
        ''')
        assert r.returncode != 0
        assert b"UnicodeEncodeError" in r.stderr

    def test_importing_the_cli_is_enough_to_save_it(self, tmp_path):
        r = self._run(tmp_path, f'''
            import sys
            import facetmark.cli  # noqa: F401  -- the import is the whole point
            sys.stdout.write({CJK!r})
            sys.stderr.write({CJK!r})
        ''')
        assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
        assert r.stdout.decode("utf-8") == CJK
        assert r.stderr.decode("utf-8") == CJK


class TestImportWithNoArgument:
    """The Windows first run. Nobody types the AppData path from memory."""

    def _runner(self):
        from typer.testing import CliRunner

        return CliRunner()

    # A path that cannot exist, spelled so the assertion survives both
    # separators: POSIX '/nowhere', Windows '\\nowhere'.
    NOWHERE_PARTS = ("/nowhere",) if os.name != "nt" else ("\\", "nowhere")
    NOWHERE_TEXT = str(Path(*NOWHERE_PARTS))

    def _invoke(self, monkeypatch, found, args, tmp_path):
        from facetmark import cli

        monkeypatch.setattr(cli, "discover_bookmark_files", lambda: found)
        monkeypatch.setattr(cli, "candidate_roots", lambda: [(Path(*self.NOWHERE_PARTS), "Chrome", "p")])
        monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path / "data"))
        return self._runner().invoke(cli.app, args)

    def test_one_profile_is_imported_without_being_named(self, tmp_path, monkeypatch):
        bm = tmp_path / "Bookmarks"
        bm.write_text(
            '{"roots":{"bookmark_bar":{"type":"folder","children":['
            '{"type":"url","name":"' + CJK + '","url":"https://example.com/a",'
            '"date_added":"13300000000000000"}]}}}',
            encoding="utf-8",
        )
        r = self._invoke(monkeypatch, [(bm, "Chrome", "Default")], ["import"], tmp_path)
        assert r.exit_code == 0, r.output
        assert "inserted" in r.output

    def test_two_profiles_are_not_guessed_between(self, tmp_path, monkeypatch):
        found = [
            (tmp_path / "a" / "Bookmarks", "Chrome", "Default"),
            (tmp_path / "b" / "Bookmarks", "Edge", "Default"),
        ]
        r = self._invoke(monkeypatch, found, ["import"], tmp_path)
        assert r.exit_code == 2
        # every candidate is printed as a command the user can paste back
        assert r.output.count("facetmark import ") >= 2

    def test_no_profile_says_where_it_looked(self, tmp_path, monkeypatch):
        r = self._invoke(monkeypatch, [], ["import"], tmp_path)
        assert r.exit_code == 2
        assert self.NOWHERE_TEXT in r.output

    def test_an_explicit_path_never_touches_discovery(self, tmp_path, monkeypatch):
        from facetmark import cli

        def boom():
            raise AssertionError("discovery ran even though a path was given")

        bm = tmp_path / "bookmarks.html"
        bm.write_text(
            '<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p>'
            f'<DT><A HREF="https://example.com/x" ADD_DATE="1690391875">{CJK}</A>'
            "</DL><p>",
            encoding="utf-8",
        )
        monkeypatch.setattr(cli, "discover_bookmark_files", boom)
        monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path / "data"))
        r = self._runner().invoke(cli.app, ["import", str(bm)])
        assert r.exit_code == 0, r.output

    def test_the_browsers_command_lists_what_was_found(self, tmp_path, monkeypatch):
        found = [(tmp_path / "a" / "Bookmarks", "Brave", "Profile 2")]
        r = self._invoke(monkeypatch, found, ["browsers", "--json"], tmp_path)
        assert r.exit_code == 0
        assert json.loads(r.stdout)[0]["browser"] == "Brave"

    def test_the_browsers_command_is_honest_about_finding_nothing(self, tmp_path, monkeypatch):
        r = self._invoke(monkeypatch, [], ["browsers"], tmp_path)
        assert r.exit_code == 0
        assert self.NOWHERE_TEXT in r.output


@pytest.mark.parametrize("stream_name", ["stdout", "stderr"])
def test_both_streams_are_covered(monkeypatch, stream_name):
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)
    monkeypatch.setattr(sys, stream_name, _stream("cp1252"))
    _harden_stdio()
    assert getattr(sys, stream_name).encoding == "utf-8"


class TestTheDocumentedCommands:
    """Every `facetmark X` the README names is a command that exists.

    Both READMEs advertised `init`, `import-json`, `fetch`, `enrich`, `embed`,
    `intents`, `edges`, `selfcheck-embed` and `export`. None of them existed,
    and `init` was the *first* line of the quickstart -- so the first thing a
    new reader typed printed "No such command". Prose drifts; a table of
    commands is a list of promises, and this is the test that keeps it one.
    """

    @staticmethod
    def _real() -> set[str]:
        from facetmark import cli

        names: set[str] = set()
        for c in cli.app.registered_commands:
            names.add(c.name or (c.callback.__name__ if c.callback else ""))
        # Sub-apps are commands too: `config path`, `config show`.
        for g in cli.app.registered_groups:
            if g.name:
                names.add(g.name)
        # Typer takes the function name when no explicit name is given, and
        # `import`/`eval` are keywords, so those two carry a `_cmd` suffix.
        return {n.replace("_cmd", "").replace("_", "-") for n in names if n}

    @staticmethod
    def _documented(path: Path) -> set[str]:
        """Every ``facetmark X`` the file presents as a command to run.

        Read from the two places that are promises rather than prose: a line
        *inside a fenced block* that starts with the binary, and a
        ```facetmark X``` span. ``cd facetmark`` is neither, and a
        Chinese sentence that happens to open with the product name is not a
        shell line.
        """
        import re

        found: set[str] = set()
        fenced = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            bare = line.strip()
            if fenced and bare.startswith("facetmark "):
                word = bare.split()[1]
                if re.fullmatch(r"[a-z][a-z0-9-]*", word):
                    found.add(word)
            for m in re.finditer(r"`facetmark ([a-z][a-z0-9-]*)", line):
                found.add(m.group(1))
        return found

    @pytest.mark.parametrize("readme", ["README.md", "README.zh-CN.md"])
    def test_the_readme_names_no_command_that_does_not_exist(self, readme):
        root = Path(__file__).resolve().parents[1]
        real = self._real()
        claimed = self._documented(root / readme)
        assert claimed, "parsed no commands out of the README -- the reader broke"
        missing = sorted(c for c in claimed if c not in real)
        assert not missing, f"{readme} documents commands that do not exist: {missing}"
