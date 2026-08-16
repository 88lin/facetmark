"""Read and write ``<data_dir>/config.toml``.

Both READMEs have promised this file since 1.0 and nothing ever implemented it:
settings came from ``FACETMARK_*`` environment variables and a ``.env`` in the
process working directory, and nothing else. That gap is invisible from a
terminal -- anyone reading the README exports a variable instead and moves on --
but it is fatal for the web UI, which has no shell to export into and must put
an API key somewhere that survives a restart.

Two rules make adding a fourth configuration source safe.

**It loses every tie.** The source is registered last in
:meth:`Settings.settings_customise_sources`, so the order is init argument >
environment variable > ``.env`` > this file > field default. An existing install
without the file behaves exactly as before, and an operator who exports a
variable is never overridden by a file some UI wrote months ago.

**It is flat.** Every field on :class:`~facetmark.config.Settings` is a scalar, a
``Path``, or a homogeneous tuple, so the file is one table of ``key = value``
lines with no nesting to disagree about. That keeps the writer to a few lines of
string formatting rather than a TOML serialiser dependency -- there is no such
thing as a TOML writer in the standard library, only a reader, and only since
3.11.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):  # pragma: no cover - one branch per interpreter
    import tomllib
else:  # pragma: no cover - exercised on 3.10 in CI
    import tomli as tomllib

CONFIG_NAME = "config.toml"

#: Written above the table so the next person to open the file knows what it is
#: and, more usefully, knows that exporting a variable will silently win.
HEADER = """\
# facetmark configuration.
#
# Lowest priority of any source: a FACETMARK_* environment variable or a .env
# file in the working directory overrides anything written here. Keys use the
# field name without the FACETMARK_ prefix, lowercased.
#
# Written by facetmark; hand edits are preserved on the next write only for
# keys that are still set.
"""


def config_path(data_dir: Path | None = None) -> Path:
    """Where the file lives.

    ``data_dir`` is itself a setting, which looks circular and is not: a file
    cannot choose its own location, so the directory is resolved from the
    environment (or the per-OS default) before the file is read. Setting
    ``data_dir`` inside ``config.toml`` therefore moves the database and leaves
    the config file where it was, which is the only behaviour that terminates.
    """
    if data_dir is None:
        from .config import default_data_dir

        env = os.environ.get("FACETMARK_DATA_DIR")
        data_dir = Path(os.path.expandvars(env)).expanduser() if env else default_data_dir()
    return Path(data_dir) / CONFIG_NAME


def read_config(path: Path | None = None) -> dict[str, Any]:
    """Parsed table, or ``{}`` when the file is absent.

    A malformed file raises. Silently ignoring a syntax error would mean a user
    who fat-fingered a quote gets the default model with no indication why, and
    "my settings stopped applying" is a far worse afternoon than a parse error
    naming the line.
    """
    p = config_path() if path is None else Path(path)
    if not p.is_file():
        return {}
    with p.open("rb") as fh:
        data = tomllib.load(fh)
    # Tolerate the shape people write by hand after reading a pyproject.toml.
    inner = data.get("facetmark")
    if isinstance(inner, dict):
        merged = {k: v for k, v in data.items() if k != "facetmark"}
        merged.update(inner)
        return merged
    return data


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):  # before int: bool is an int subclass
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        text = repr(value)
        # TOML floats need a fractional part or an exponent; `repr(1e30)` gives
        # `1e+30`, which qualifies, but `repr(3.0)` gives `3.0`, which also
        # qualifies. The only gap is a float that reprs as bare digits, which
        # CPython does not produce -- belt and braces anyway.
        return text if ("." in text or "e" in text or "E" in text) else text + ".0"
    text = str(value)
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def to_toml(values: Mapping[str, Any]) -> str:
    """Serialise a flat mapping. ``None`` drops the key -- TOML has no null."""
    lines = [HEADER]
    for key in sorted(values):
        value = values[key]
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            items = ", ".join(_toml_scalar(v) for v in value)
            lines.append(f"{key} = [{items}]")
        else:
            lines.append(f"{key} = {_toml_scalar(value)}")
    return "\n".join(lines) + "\n"


def write_config(values: Mapping[str, Any], path: Path | None = None) -> Path:
    """Replace the file atomically, owner-readable only.

    The file holds an API key, so it is written to a sibling temporary path and
    renamed: a crash mid-write leaves the previous file intact rather than a
    truncated one, and the mode is set before any bytes land rather than after,
    which would leave a window where the key is world-readable.
    """
    p = config_path() if path is None else Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(to_toml(values))
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, p)
    return p


def update_config(changes: Mapping[str, Any], path: Path | None = None) -> Path:
    """Merge ``changes`` into the existing table and rewrite it.

    A key mapped to ``None`` is removed, which is how the UI clears a setting
    back to its default. Writing an empty string instead would pin the field to
    ``""`` forever, and "clear this" and "set this to empty" are different
    requests for ``base_url``.
    """
    p = config_path() if path is None else Path(path)
    merged = dict(read_config(p))
    for key, value in changes.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return write_config(merged, p)
