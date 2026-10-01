"""Who, besides you, can read the library.

Reported from a Debian box: the pairing token was 0600 and the database beside
it was 0644, inside a 0775 directory. The token guards the API; the database
*is* the reading history, and its `-wal` holds whatever was written most
recently. Guarding the key and leaving the door open is not a threat model.

Real mode checks run on POSIX. Simulated permission snapshots also exercise
the diagnostic decisions on Windows, which does not expose POSIX permissions.
"""

from __future__ import annotations

import os
import shlex
import sqlite3
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from facetmark.config import Settings
from facetmark.configfile import write_config
from facetmark.db import open_db

posix_only = pytest.mark.skipif(
    os.name == "nt", reason="Windows has no POSIX mode for this to be about"
)


def mode_of(path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def others_can_read(path) -> bool:
    return bool(mode_of(path) & 0o077)


@posix_only
class TestNothingIsWorldReadableWhenItIsMade:
    def test_the_data_directory_denies_everyone_else(self, tmp_path):
        st = Settings(data_dir=tmp_path / "lib")
        st.ensure_dirs()
        assert mode_of(st.data_dir) == 0o700, oct(mode_of(st.data_dir))

    def test_a_umask_that_would_have_widened_it_does_not(self, tmp_path):
        """0o022 is the stock default and 0o002 is what a Debian box with
        per-user groups uses. Neither may reach this directory: `mkdir(mode=)`
        is masked by the umask, so the mode has to be one the umask cannot
        widen -- which 0o700 is, for any umask, because the umask only ever
        clears bits."""
        old = os.umask(0o002)
        try:
            st = Settings(data_dir=tmp_path / "loose")
            st.ensure_dirs()
            assert mode_of(st.data_dir) == 0o700, oct(mode_of(st.data_dir))
        finally:
            os.umask(old)

    def test_the_database_denies_everyone_else(self, tmp_path):
        db = tmp_path / "lib" / "facetmark.db"
        conn = open_db(str(db))
        conn.close()
        assert db.exists()
        assert mode_of(db) == 0o600, oct(mode_of(db))

    def test_saving_settings_first_still_creates_a_private_directory(self, tmp_path):
        target = tmp_path / "lib"
        write_config({"api_key": "example"}, path=target / "config.toml")
        assert mode_of(target) == 0o700

    def test_an_existing_directory_is_left_as_it_was(self, tmp_path):
        st = Settings(data_dir=tmp_path / "lib")
        st.ensure_dirs()
        st.data_dir.chmod(0o755)
        st.ensure_dirs()
        write_config({"port": 8787}, path=st.data_dir / "config.toml")
        open_db(st.db_path).close()
        assert mode_of(st.data_dir) == 0o755

    def test_the_wal_sidecars_are_covered_too(self, tmp_path):
        """SQLite recreates `-wal` and `-shm` on its own schedule at whatever
        the umask allows, and nothing gets a chance to chmod them. They are
        covered by the directory denying traversal rather than by their own
        mode, which is why the directory is 0700 and not merely 0755."""
        db = tmp_path / "lib" / "facetmark.db"
        conn = open_db(str(db))
        conn.execute("CREATE TABLE t(x)")
        conn.execute("INSERT INTO t VALUES(1)")
        wal = db.with_name(db.name + "-wal")
        assert wal.exists(), "WAL mode is not on -- this test is measuring nothing"
        conn.close()
        assert mode_of(db.parent) == 0o700, oct(mode_of(db.parent))

    def test_an_existing_database_is_left_as_it_was(self, tmp_path):
        """Owner-only on creation only. A file somebody deliberately widened is
        their decision; `doctor` reports it rather than this changing it under
        them on the next run."""
        db = tmp_path / "lib" / "facetmark.db"
        open_db(str(db)).close()
        os.chmod(db, 0o644)
        open_db(str(db)).close()
        assert mode_of(db) == 0o644, "an existing file was re-chmodded"

    def test_an_in_memory_database_still_works(self):
        conn = open_db(":memory:")
        conn.execute("CREATE TABLE t(x)")
        conn.close()


@posix_only
class TestDoctorReportsWhatItFinds:
    """The fixes above help a new install. An install made before them keeps
    what it had, so the only thing that helps an existing box is being told."""

    def _checks(self, data_dir, db_path):
        from facetmark.diagnose import check_permissions

        return check_permissions(Settings(data_dir=data_dir, db_name=db_path.name))

    def test_a_tight_install_passes(self, tmp_path):
        st = Settings(data_dir=tmp_path / "lib")
        st.ensure_dirs()
        open_db(str(st.db_path)).close()
        checks = self._checks(st.data_dir, st.db_path)
        assert [c.status for c in checks] == ["ok"], [c.message for c in checks]

    @pytest.mark.parametrize("mode", [0o755, 0o775, 0o777])
    def test_a_loose_directory_is_reported(self, tmp_path, mode):
        st = Settings(data_dir=tmp_path / "lib")
        st.ensure_dirs()
        open_db(str(st.db_path)).close()
        os.chmod(st.data_dir, mode)
        checks = self._checks(st.data_dir, st.db_path)
        assert [c.status for c in checks] == ["warn"]
        assert "directory" in checks[0].message

    def test_a_loose_database_is_reported_even_inside_a_tight_directory(self, tmp_path):
        """The state this was found in: the token 0600, the directory 0775 and
        the database 0644. Each alone is enough to report."""
        st = Settings(data_dir=tmp_path / "lib")
        st.ensure_dirs()
        open_db(str(st.db_path)).close()
        os.chmod(st.db_path, 0o644)
        checks = self._checks(st.data_dir, st.db_path)
        assert [c.status for c in checks] == ["warn"]
        assert "database" in checks[0].message

    def test_the_message_names_the_modes_and_the_command_that_fixes_them(self, tmp_path):
        st = Settings(data_dir=tmp_path / "lib")
        st.ensure_dirs()
        open_db(str(st.db_path)).close()
        os.chmod(st.data_dir, 0o775)
        os.chmod(st.db_path, 0o644)
        msg = self._checks(st.data_dir, st.db_path)[0].message
        assert "775" in msg and "644" in msg, msg
        assert "chmod 700" in msg and "chmod 600" in msg, msg

    def test_a_wal_left_behind_is_reported(self, tmp_path):
        st = Settings(data_dir=tmp_path / "lib")
        st.ensure_dirs()
        conn = open_db(str(st.db_path))
        conn.execute("CREATE TABLE t(x)")
        conn.execute("INSERT INTO t VALUES(1)")
        wal = st.db_path.with_name(st.db_path.name + "-wal")
        assert wal.exists()
        os.chmod(wal, 0o644)
        checks = self._checks(st.data_dir, st.db_path)
        conn.close()
        assert [c.status for c in checks] == ["warn"]
        assert "wal" in checks[0].message, checks[0].message

    def test_a_missing_database_is_not_an_error(self, tmp_path):
        """`doctor` runs on a fresh install too, before anything is imported."""
        st = Settings(data_dir=tmp_path / "lib")
        st.ensure_dirs()
        checks = self._checks(st.data_dir, st.db_path)
        assert [c.status for c in checks] == ["ok"]


@pytest.mark.skipif(os.name != "nt", reason="the Windows half of the same rule")
def test_windows_gets_no_permission_check_rather_than_a_wrong_one(tmp_path):
    """There is no POSIX mode to report, and inventing a verdict from an
    `st_mode` Windows synthesises would be asserting something nobody checked.
    The rest of `doctor` still has to work."""
    from facetmark.diagnose import check_permissions

    st = Settings(data_dir=tmp_path / "lib")
    st.ensure_dirs()
    assert check_permissions(st) == []


def test_the_database_is_created_wherever_it_is_asked_for(tmp_path):
    """Both platforms: the chmod is best effort and must not become the reason
    a database fails to open."""
    db = tmp_path / "deep" / "deeper" / "facetmark.db"
    conn = open_db(str(db))
    conn.execute("CREATE TABLE t(x)")
    conn.close()
    assert db.exists()
    with sqlite3.connect(str(db)) as c:
        names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert "t" in names


@pytest.fixture
def permission_snapshot(monkeypatch):
    """Exercise POSIX diagnostic decisions on Windows without changing os.name
    globally, which would also change pathlib's platform implementation."""
    import facetmark.diagnose as diagnose

    monkeypatch.setattr(diagnose, "os", SimpleNamespace(name="posix"))
    original_stat = Path.stat

    def install(st, modes):
        paths = [st.data_dir, st.db_path, Path(f"{st.db_path}-wal"), Path(f"{st.db_path}-shm")]
        values = {str(p): value for p, value in zip(paths, modes, strict=True)}

        def fake_stat(path, *args, **kwargs):
            key = str(path)
            if key not in values:
                return original_stat(path, *args, **kwargs)
            value = values[key]
            if value is None:
                raise FileNotFoundError(key)
            if isinstance(value, OSError):
                raise value
            return SimpleNamespace(st_mode=value)

        monkeypatch.setattr(Path, "stat", fake_stat)
        return diagnose.check_permissions(st)

    return install


@pytest.mark.parametrize("modes,label", [
    ([0o755, 0o600, None, None], "directory 755"),
    ([0o700, 0o644, None, None], "database 644"),
    ([0o700, 0o600, 0o640, None], "wal 640"),
    ([0o700, 0o600, None, 0o660], "shm 660"),
])
def test_doctor_reports_each_loose_path(tmp_path, permission_snapshot, modes, label):
    checks = permission_snapshot(Settings(data_dir=tmp_path / "lib"), modes)
    assert [c.status for c in checks] == ["warn"]
    assert label in checks[0].message


def test_repair_command_quotes_paths_and_does_not_match_backups(tmp_path, permission_snapshot):
    st = Settings(data_dir=tmp_path / "a b'$(echo example)", db_name="notes[1].db")
    checks = permission_snapshot(st, [0o775, 0o644, 0o644, None])
    command = checks[0].message.split("Tighten with: ", 1)[1]
    tokens = shlex.split(command)
    assert tokens == [
        "chmod", "700", "--", str(st.data_dir), "&&",
        "chmod", "600", "--", str(st.db_path), "&&",
        "chmod", "600", "--", f"{st.db_path}-wal",
    ]
    assert "*" not in command


@pytest.mark.parametrize("position", range(4))
def test_inaccessible_paths_are_not_reported_as_private(tmp_path, permission_snapshot, position):
    modes = [0o700, 0o600, None, None]
    modes[position] = PermissionError("access denied")
    checks = permission_snapshot(Settings(data_dir=tmp_path / "lib"), modes)
    assert [c.status for c in checks] == ["warn"]
    assert "could not inspect" in checks[0].message


def test_missing_paths_do_not_produce_an_owner_only_claim(tmp_path, permission_snapshot):
    assert permission_snapshot(Settings(data_dir=tmp_path / "missing"), [None] * 4) == []


def test_a_private_directory_with_no_database_yet_passes(tmp_path, permission_snapshot):
    checks = permission_snapshot(Settings(data_dir=tmp_path / "lib"), [0o700, None, None, None])
    assert [c.status for c in checks] == ["ok"]
