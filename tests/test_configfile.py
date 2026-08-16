"""``<data_dir>/config.toml``: round trip, precedence, and failure modes.

The precedence tests are the ones that matter. A configuration source that can
override an environment variable is a support burden with a long tail -- "it
works on my machine" where the difference is a file written by a UI six months
ago -- so every tie is pinned here rather than left to the reader of
``settings_customise_sources``.
"""

from __future__ import annotations

import os
import stat

import pytest

from facetmark.config import Settings, default_data_dir
from facetmark.configfile import (
    config_path,
    read_config,
    to_toml,
    update_config,
    write_config,
)


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Relocate the per-OS default rather than exporting ``FACETMARK_DATA_DIR``.

    Exporting it would be the easier fixture and the wrong one: the environment
    variable outranks the file, so every test written on top of it would be
    quietly testing the environment source instead. The variable gets its own
    test below.
    """
    monkeypatch.delenv("FACETMARK_DATA_DIR", raising=False)
    monkeypatch.setattr("facetmark.config.default_data_dir", lambda **kw: tmp_path)
    return tmp_path


# --------------------------------------------------------------------------
# location
# --------------------------------------------------------------------------


def test_path_follows_the_data_dir_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(tmp_path))
    assert config_path() == tmp_path / "config.toml"


def test_path_falls_back_to_the_per_os_default(monkeypatch):
    monkeypatch.delenv("FACETMARK_DATA_DIR", raising=False)
    assert config_path() == default_data_dir() / "config.toml"


def test_path_expands_user_and_variables(monkeypatch, tmp_path):
    monkeypatch.setenv("FM_TEST_HOME", str(tmp_path))
    monkeypatch.setenv("FACETMARK_DATA_DIR", "$FM_TEST_HOME/nested")
    assert config_path() == tmp_path / "nested" / "config.toml"


def test_a_data_dir_inside_the_file_does_not_move_the_file(data_dir, tmp_path):
    """The one recursion that has to terminate.

    A file cannot choose its own location. Setting ``data_dir`` in the table
    moves the database and leaves the config where the environment put it.
    """
    elsewhere = tmp_path / "elsewhere"
    write_config({"data_dir": str(elsewhere)})
    assert Settings().data_dir == elsewhere
    assert config_path() == data_dir / "config.toml"


# --------------------------------------------------------------------------
# round trip
# --------------------------------------------------------------------------


def test_missing_file_reads_as_empty(data_dir):
    assert read_config() == {}


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("chat_model", "deepseek-chat"),
        ("embed_dim", 1024),
        ("request_timeout", 30.0),
        ("respect_robots", False),
        ("health_enable_doh", True),
        ("privacy_excluded_domains", ["bank.example", "mail.example"]),
        ("session_eps_grid_minutes", [5, 15, 45]),
        ("base_url", ""),
    ],
)
def test_every_field_shape_survives_a_round_trip(data_dir, key, value):
    write_config({key: value})
    assert read_config()[key] == value


def test_settings_coerce_what_the_file_returns(data_dir):
    write_config(
        {
            "privacy_excluded_domains": ["bank.example"],
            "embed_dim": 1024,
            "respect_robots": False,
            "data_dir": str(data_dir / "db"),
        }
    )
    s = Settings()
    assert s.privacy_excluded_domains == ("bank.example",)
    assert s.embed_dim == 1024
    assert s.respect_robots is False
    assert s.data_dir == data_dir / "db"


def test_quotes_and_backslashes_survive(data_dir):
    """API keys are opaque. Escaping them wrong corrupts a working credential."""
    nasty = 'sk-a"b\\c\td\ne'
    write_config({"api_key": nasty})
    assert read_config()["api_key"] == nasty
    assert Settings().api_key == nasty


def test_none_is_omitted_rather_than_written_as_a_null():
    assert "session_eps_minutes" not in to_toml({"session_eps_minutes": None})


def test_floats_keep_a_fractional_part():
    """``60 = 60`` parses back as an int and fails float validation later."""
    assert "request_timeout = 60.0" in to_toml({"request_timeout": 60.0})


def test_booleans_are_not_written_as_integers():
    """``bool`` is an ``int`` subclass; the naive branch order writes ``1``."""
    body = to_toml({"respect_robots": True, "health_enable_doh": False})
    assert "respect_robots = true" in body
    assert "health_enable_doh = false" in body


def test_keys_are_sorted_so_rewrites_produce_stable_diffs():
    body = to_toml({"port": 1, "api_key": "x", "chat_model": "y"})
    keys = [line.split(" =")[0] for line in body.splitlines() if " = " in line]
    assert keys == sorted(keys)


# --------------------------------------------------------------------------
# precedence -- the whole reason this is safe to add
# --------------------------------------------------------------------------


def test_environment_variable_beats_the_file(data_dir, monkeypatch):
    write_config({"chat_model": "from-file"})
    monkeypatch.setenv("FACETMARK_CHAT_MODEL", "from-env")
    assert Settings().chat_model == "from-env"


def test_dotenv_beats_the_file(data_dir, monkeypatch, tmp_path):
    write_config({"chat_model": "from-file"})
    (tmp_path / ".env").write_text("FACETMARK_CHAT_MODEL=from-dotenv\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert Settings().chat_model == "from-dotenv"


def test_dotenv_data_dir_selects_the_same_config_file(tmp_path, monkeypatch):
    target = tmp_path / "configured"
    target.mkdir()
    (tmp_path / ".env").write_text(
        f"FACETMARK_DATA_DIR={target}\n", encoding="utf-8"
    )
    (target / "config.toml").write_text('chat_model = "from-configured-dir"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FACETMARK_DATA_DIR", raising=False)
    settings = Settings()
    assert settings.data_dir == target
    assert config_path() == target / "config.toml"
    assert settings.chat_model == "from-configured-dir"


def test_process_data_dir_beats_dotenv_data_dir(tmp_path, monkeypatch):
    dotenv_dir = tmp_path / "dotenv"
    process_dir = tmp_path / "process"
    dotenv_dir.mkdir()
    process_dir.mkdir()
    (tmp_path / ".env").write_text(
        f"FACETMARK_DATA_DIR={dotenv_dir}\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(process_dir))
    assert config_path() == process_dir / "config.toml"


def test_init_argument_beats_the_file(data_dir):
    write_config({"chat_model": "from-file"})
    assert Settings(chat_model="from-init").chat_model == "from-init"


def test_the_file_beats_the_field_default(data_dir):
    write_config({"chat_model": "from-file"})
    assert Settings().chat_model == "from-file"


def test_an_absent_file_changes_nothing(data_dir):
    """The install base that has never seen this feature must not move."""
    assert Settings().chat_model == Settings.model_fields["chat_model"].default


def test_unknown_keys_are_ignored_not_fatal(data_dir):
    (data_dir / "config.toml").write_text(
        'chat_model = "kept"\nnot_a_setting = "ignored"\n', encoding="utf-8"
    )
    assert Settings().chat_model == "kept"


def test_a_facetmark_table_is_accepted(data_dir):
    """Because people copy the shape they last saw in a ``pyproject.toml``."""
    (data_dir / "config.toml").write_text(
        '[facetmark]\nchat_model = "nested"\n', encoding="utf-8"
    )
    assert Settings().chat_model == "nested"


# --------------------------------------------------------------------------
# failure modes
# --------------------------------------------------------------------------


def test_a_malformed_file_names_itself(data_dir):
    """Silence here means "my settings stopped applying" with no thread to pull."""
    (data_dir / "config.toml").write_text('chat_model = "unclosed\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"config\.toml"):
        Settings()


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits")
def test_the_file_is_owner_only(data_dir):
    """It holds an API key."""
    p = write_config({"api_key": "sk-secret"})
    assert stat.S_IMODE(p.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits")
def test_a_rewrite_does_not_widen_the_mode(data_dir):
    write_config({"api_key": "sk-one"})
    p = update_config({"api_key": "sk-two"})
    assert stat.S_IMODE(p.stat().st_mode) == 0o600


def test_no_temporary_file_is_left_behind(data_dir):
    write_config({"api_key": "sk-secret"})
    assert not list(data_dir.glob("*.tmp"))


def test_update_merges_rather_than_replaces(data_dir):
    write_config({"chat_model": "keep-me", "port": 1234})
    update_config({"port": 9999})
    table = read_config()
    assert table == {"chat_model": "keep-me", "port": 9999}


def test_update_with_none_clears_back_to_the_default(data_dir):
    """"Clear this" and "set this to empty" are different requests."""
    write_config({"base_url": "https://custom.example/v1"})
    update_config({"base_url": None})
    assert "base_url" not in read_config()
    assert Settings().base_url == Settings.model_fields["base_url"].default


def test_write_creates_the_directory(tmp_path, monkeypatch):
    target = tmp_path / "not" / "yet"
    monkeypatch.setenv("FACETMARK_DATA_DIR", str(target))
    write_config({"port": 1})
    assert (target / "config.toml").is_file()
