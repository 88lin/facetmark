"""Finding the browser's bookmark file on all three platforms, from one of them.

Windows is the stated primary target and the platform this code is least likely
to be developed on, so before these tests the Windows branch was covered by
reading it. It now runs here: ``candidate_roots`` takes the OS as an argument
precisely because ``os.name`` cannot be patched -- ``pathlib.Path`` picks
``WindowsPath`` from it and that class will not instantiate on POSIX.

The paths built under a faked ``nt`` are therefore POSIX paths with the Windows
*table* -- which is the part that rots. Whether ``C:\\Users`` parses is CPython's
problem, not ours; whether Edge is looked for under ``Microsoft/Edge/User Data``
is ours.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from facetmark.config import default_data_dir
from facetmark.importers.chrome_json import discover_bookmark_files as reexported
from facetmark.importers.discovery import candidate_roots, discover_bookmark_files

CHROME_JSON = json.dumps({"roots": {"bookmark_bar": {"type": "folder", "children": []}}})


def _profile(root: Path, *parts: str) -> Path:
    """Create ``root/<parts>/Bookmarks`` and return it."""
    d = root.joinpath(*parts)
    d.mkdir(parents=True, exist_ok=True)
    f = d / "Bookmarks"
    f.write_text(CHROME_JSON, encoding="utf-8")
    return f


@pytest.fixture
def win(tmp_path, monkeypatch):
    """A tmp_path shaped like %LOCALAPPDATA% and %APPDATA%."""
    local, roaming = tmp_path / "Local", tmp_path / "Roaming"
    local.mkdir()
    roaming.mkdir()
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("APPDATA", str(roaming))
    return local, roaming


@pytest.mark.skipif(os.name == "nt", reason="table tests fake Windows from POSIX; on real Windows the path shape inverts")
class TestWindows:
    def test_the_default_chrome_profile_is_found(self, win):
        local, _ = win
        want = _profile(local, "Google", "Chrome", "User Data", "Default")
        assert discover_bookmark_files(os_name="nt") == [(want, "Chrome", "Default")]

    def test_edge_is_looked_for_where_edge_actually_is(self, win):
        local, _ = win
        want = _profile(local, "Microsoft", "Edge", "User Data", "Profile 1")
        assert discover_bookmark_files(os_name="nt") == [(want, "Edge", "Profile 1")]

    def test_a_profile_beyond_the_guessed_ones_is_still_found(self, win):
        """Users make more than four profiles. Listing the root catches them."""
        local, _ = win
        want = _profile(local, "Google", "Chrome", "User Data", "Profile 17")
        assert discover_bookmark_files(os_name="nt") == [(want, "Chrome", "Profile 17")]

    def test_a_directory_that_is_not_a_profile_is_ignored(self, win):
        local, _ = win
        root = local / "Google" / "Chrome" / "User Data"
        _profile(root, "System Profile")  # real, and not a user's bookmarks
        _profile(root, "Guest Profile")
        assert discover_bookmark_files(os_name="nt") == []

    def test_opera_is_roaming_not_local_and_keeps_no_profile_dir(self, win):
        """The one browser in the table that breaks both Chromium conventions."""
        _, roaming = win
        d = roaming / "Opera Software" / "Opera Stable"
        d.mkdir(parents=True)
        (d / "Bookmarks").write_text(CHROME_JSON, encoding="utf-8")
        assert discover_bookmark_files(os_name="nt") == [
            (d / "Bookmarks", "Opera", "Opera Stable")
        ]

    def test_several_browsers_are_all_reported(self, win):
        local, roaming = win
        a = _profile(local, "Google", "Chrome", "User Data", "Default")
        b = _profile(local, "Microsoft", "Edge", "User Data", "Default")
        got = discover_bookmark_files(os_name="nt")
        assert {p for p, _, _ in got} == {a, b}

    def test_no_appdata_at_all_is_empty_not_a_crash(self, monkeypatch):
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.delenv("APPDATA", raising=False)
        assert candidate_roots(os_name="nt") == []
        assert discover_bookmark_files(os_name="nt") == []

    def test_the_relative_tables_never_contain_a_backslash(self):
        """A literal ``\\`` in a table entry is a component that never splits.

        It happens to work on Windows because ``WindowsPath`` re-parses it, and
        it is invisible until someone tries to test the branch anywhere else.
        """
        for root, _, _ in candidate_roots(os_name="nt"):
            assert "\\" not in str(root)


@pytest.mark.skipif(os.name == "nt", reason="posix table tests fake $HOME; on Windows Path.home() ignores it")
class TestMacAndLinux:
    def test_mac_looks_under_application_support(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        base = tmp_path / "Library" / "Application Support"
        want = _profile(base, "Google", "Chrome", "Default")
        assert discover_bookmark_files(os_name="posix", platform="darwin") == [
            (want, "Chrome", "Default")
        ]

    def test_linux_honours_xdg_config_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        cfg = tmp_path / "elsewhere"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg))
        want = _profile(cfg, "google-chrome", "Default")
        assert discover_bookmark_files(os_name="posix", platform="linux") == [
            (want, "Chrome", "Default")
        ]

    def test_linux_falls_back_to_dot_config(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        want = _profile(tmp_path / ".config", "chromium", "Default")
        assert discover_bookmark_files(os_name="posix", platform="linux") == [
            (want, "Chromium", "Default")
        ]

    def test_the_three_tables_cover_the_same_browsers(self):
        """A browser added to one platform and forgotten on the others."""
        import facetmark.importers.discovery as d

        names = [{n for _, n, _ in table} for table in (d._WIN_LOCAL + d._WIN_ROAMING,
                                                        d._MAC_BASES, d._LINUX_BASES)]
        core = {"Chrome", "Edge", "Brave", "Vivaldi", "Chromium", "Opera"}
        for got in names:
            assert core <= got


class TestTheFileIsActuallyImportable:
    def test_what_discovery_returns_parses_as_chrome_json(self, win, conn):
        from facetmark.service import import_file

        local, _ = win
        _profile(local, "Google", "Chrome", "User Data", "Default")
        (path, _, _), = discover_bookmark_files(os_name="nt")
        stats = import_file(conn, str(path))
        assert stats["source"] == "chrome_json"

    def test_the_old_import_path_still_works(self):
        assert reexported is discover_bookmark_files


class TestDefaultDataDir:
    def test_windows_uses_localappdata(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert default_data_dir(os_name="nt") == tmp_path / "facetmark"

    def test_windows_without_localappdata_falls_back_to_home(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        assert default_data_dir(os_name="nt") == tmp_path / "facetmark"

    def test_posix_honours_xdg_data_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        assert default_data_dir(os_name="posix") == tmp_path / "facetmark"

    @pytest.mark.skipif(os.name == "nt", reason="Path.home() on Windows ignores the patched HOME")
    def test_posix_defaults_to_local_share(self, tmp_path, monkeypatch):
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        assert default_data_dir(os_name="posix") == tmp_path / ".local/share/facetmark"
