"""Discover model choices without testing, saving credentials or generating text."""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import httpx

from . import local_agents
from .providers import ProviderError

MAX_MODELS = 2000
MAX_CATALOG_BYTES = 4 * 1024 * 1024


def _read_object(path: Path) -> dict:
    if not path.is_file():
        return {}
    if path.stat().st_size > MAX_CATALOG_BYTES:
        raise ValueError("Model catalog is too large")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Expected an object")
    return value


def _choices(rows: list, *, source: str) -> list[dict]:
    choices = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("visibility") == "hidden":
            continue
        model_id = row.get("slug") or row.get("id")
        if not isinstance(model_id, str) or not model_id.strip() or len(model_id) > 512:
            continue
        model_id = model_id.strip()
        label = row.get("display_name") or row.get("name") or model_id
        choice = {"id": model_id, "label": label if isinstance(label, str) else model_id,
                  "source": source}
        levels = row.get("supported_reasoning_levels", row.get("supported_reasoning_efforts"))
        if levels is None and isinstance(row.get("variants"), dict):
            levels = [{"effort": key} for key, value in row["variants"].items()
                      if isinstance(value, dict) and not value.get("disabled")]
        if isinstance(levels, list):
            safe_levels = {}
            for level in levels[:64]:
                effort = level if isinstance(level, str) else level.get("effort") if isinstance(level, dict) else None
                if isinstance(effort, str) and effort.strip() and len(effort) <= 128:
                    safe_levels[effort.strip()] = {"id": effort.strip()}
            choice["reasoning_levels"] = list(safe_levels.values())
        default = row.get("default_reasoning_level")
        if not isinstance(default, str):
            options = row.get("options", {})
            default = options.get("reasoningEffort") if isinstance(options, dict) else None
        if isinstance(default, str) and len(default) <= 128:
            choice["default_reasoning_effort"] = default
        choices[model_id] = {**choices.get(model_id, {}), **choice}
        if len(choices) >= MAX_MODELS:
            break
    return list(choices.values())


def _opencode_rows(output: str) -> list[dict]:
    """Read plain catalogs and --verbose ID/JSON pairs without losing variants."""
    rows = {}
    decoder = json.JSONDecoder()
    position = 0
    current = ""
    while position < len(output):
        end = output.find("\n", position)
        end = len(output) if end < 0 else end
        line = output[position:end].strip()
        if re.fullmatch(r"[\w.-]+/[\w./:@+-]+", line):
            current = line
            rows.setdefault(current, {"id": current})
        elif line.startswith("{"):
            try:
                value, consumed = decoder.raw_decode(output[position:].lstrip())
                position += len(output[position:]) - len(output[position:].lstrip()) + consumed
                if isinstance(value, dict):
                    model = value.get("id")
                    provider = value.get("providerID")
                    model = f"{provider}/{model}" if isinstance(provider, str) and isinstance(model, str) else current
                    if model:
                        rows[model] = {**value, "id": model}
                continue
            except ValueError:
                pass
        position = end + 1
    return list(rows.values())


async def _cli_catalog(agent: str, directory: Path, env: dict) -> str:
    command = local_agents.resolve_command(agent)
    if not command:
        raise ProviderError("Selected agent is not installed. Detect agents again.")
    if agent == "opencode":
        env = local_agents._opencode_environment(directory, env)
        args = ["models", "--verbose"]
    else:
        args = ["debug", "models", *local_agents._codex_model_config(env)]
    options = ({"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
               if os.name == "nt" else {"start_new_session": True})
    # Spool output to bounded-on-read files; a verbose CLI cannot grow RAM without limit.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        try:
            process = subprocess.Popen([*command, *args], cwd=directory, env=env,
                stdin=subprocess.DEVNULL, stdout=output, stderr=errors, **options)
        except OSError:
            raise ProviderError("Cannot start the agent to read its models. Detect it again.") from None
        waiter = asyncio.create_task(asyncio.to_thread(process.wait, timeout=20))
        try:
            await asyncio.shield(waiter)
            if process.returncode:
                raise ProviderError("The agent could not list models. Check its installation and sign-in, or enter a model name.")
            output.seek(0)
            raw = output.read(MAX_CATALOG_BYTES + 1)
            if len(raw) > MAX_CATALOG_BYTES:
                raise ProviderError("The agent model catalog is too large. Enter a model name instead.")
            return raw.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            await asyncio.to_thread(local_agents._terminate, process)
            raise ProviderError("Model discovery timed out. Retry or enter a model name.") from None
        except asyncio.CancelledError:
            await asyncio.to_thread(local_agents._terminate, process)
            with contextlib.suppress(Exception):
                await waiter
            raise


async def agent_catalog(preference: str) -> dict:
    agent = local_agents.selected_agent(preference)
    if not agent:
        raise ProviderError("Selected agent is not installed. Detect agents again.")
    models: list[dict] = []
    default = ""
    warning = ""
    configured_effort = ""
    env = dict(os.environ)
    try:
        if agent == "claude":
            config = local_agents._claude_configuration(env)
            configured_env = config.get("env", {})
            configured_env = configured_env if isinstance(configured_env, dict) else {}
            effective_env = {**configured_env, **env}
            default = effective_env.get("ANTHROPIC_MODEL") or config.get("model", "")
            configured_effort = effective_env.get("CLAUDE_CODE_EFFORT_LEVEL") or config.get("effortLevel", "")
            rows = [{"id": name, "name": name.title()} for name in ("sonnet", "opus", "haiku")]
            rows += [{"id": value} for key, value in effective_env.items()
                     if key.startswith("ANTHROPIC_DEFAULT_") and key.endswith("_MODEL")]
            rows += [{"id": default}] if isinstance(default, str) and default else []
            saved = config.get("modelSettings", {})
            for row in rows:
                if not isinstance(row["id"], str):
                    continue
                actual = effective_env.get("ANTHROPIC_DEFAULT_" + row["id"].upper() + "_MODEL", row["id"])
                entry = saved.get(actual, {}) if isinstance(saved, dict) and isinstance(actual, str) else {}
                if isinstance(entry, dict) and isinstance(entry.get("effortLevel"), str):
                    row["default_reasoning_level"] = effective_env.get("CLAUDE_CODE_EFFORT_LEVEL") or entry["effortLevel"]
            models = _choices(rows, source="alias")
        elif agent == "codex":
            root = Path(env.get("CODEX_HOME", Path.home() / ".codex"))
            config = local_agents._codex_configuration(env)
            default = config.get("model", "")
            # Keep the explicitly configured effort separate from managed
            # defaults, which a later model selection overrides.
            explicit = local_agents._codex_configuration(env, model="facetmark-explicit-selection")
            configured_effort = explicit.get("model_reasoning_effort", "")
            try:
                cache = _read_object(root / "models_cache.json")
            except (OSError, ValueError):
                cache = {}
            rows = cache.get("models", [])
            models = _choices(rows if isinstance(rows, list) else [], source="cache")
            # Refresh through the installed CLI. Older versions may not implement
            # debug models; the locally cached catalog stays useful and explicit.
            with tempfile.TemporaryDirectory(prefix="facetmark-models-") as directory:
                try:
                    raw = json.loads(await _cli_catalog(agent, Path(directory), env))
                    rows = raw if isinstance(raw, list) else raw.get("models", [])
                    live = _choices(rows if isinstance(rows, list) else [], source="cli")
                    if live:
                        models = live
                    else:
                        warning = "empty_catalog"
                except (ProviderError, ValueError, AttributeError):
                    warning = "cached_catalog" if models else "catalog_unavailable"
        else:
            with tempfile.TemporaryDirectory(prefix="facetmark-models-") as directory:
                isolated = local_agents._opencode_environment(Path(directory), env)
                config = json.loads(isolated["OPENCODE_CONFIG_CONTENT"])
                default = config.get("model", "")
                models = _choices([{**(info if isinstance(info, dict) else {}), "id": f"{provider}/{model}"}
                    for provider, definition in config.get("provider", {}).items() if isinstance(definition, dict)
                    for model, info in (definition.get("models", {}) if isinstance(definition.get("models"), dict) else {}).items()], source="config")
                try:
                    output = await _cli_catalog(agent, Path(directory), dict(os.environ))
                    live = _choices(_opencode_rows(output), source="cli")
                    combined = {item["id"]: item for item in models}
                    for item in live:
                        combined[item["id"]] = {**combined.get(item["id"], {}), **item}
                    models = list(combined.values())
                    if not live:
                        warning = "configured_catalog" if models else "empty_catalog"
                except ProviderError:
                    warning = "configured_catalog" if models else "catalog_unavailable"
        default = default if isinstance(default, str) else ""
        if default and not any(model["id"] == default for model in models):
            models.insert(0, {"id": default, "label": default, "source": "config"})
    except (OSError, ValueError, TypeError, AttributeError):
        raise ProviderError("Cannot read the agent model configuration. Check its settings, then retry.") from None
    configured_effort = configured_effort if isinstance(configured_effort, str) else ""
    default_choice = next((model for model in models if model["id"] == default), {})
    default_effort = configured_effort or default_choice.get("default_reasoning_effort", "")
    if agent == "claude":
        default_effort = default_choice.get("default_reasoning_effort") or configured_effort
    if agent == "codex":
        default_effort = config.get("model_reasoning_effort") or default_effort
    return {"agent": agent, "models": models, "default_model": default, "warning": warning,
            "configured_reasoning_effort": configured_effort,
            "default_reasoning_effort": default_effort if isinstance(default_effort, str) else ""}


async def endpoint_catalog(settings, channel: str) -> dict:
    configured = settings.channel_settings(channel)
    if not configured.api_key and not configured.endpoint_allow_no_key:
        raise ProviderError("Enter an API key, or enable keyless access for a local service.")
    headers = {"Authorization": f"Bearer {configured.api_key}"} if configured.api_key else {}
    try:
        async with (httpx.AsyncClient(timeout=15, follow_redirects=False) as client,
                    client.stream("GET", configured.base_url.rstrip("/") + "/models", headers=headers) as response):
            if response.status_code in (401, 403):
                raise ProviderError("Model access was denied. Check the API key and service address.")
            if not response.is_success:
                raise ProviderError("This service could not list models. Retry or enter its model name manually.")
            chunks = bytearray()
            async for chunk in response.aiter_bytes():
                chunks.extend(chunk)
                if len(chunks) > MAX_CATALOG_BYTES:
                    raise ProviderError("The model catalog is too large. Enter a model name manually.")
        value = json.loads(chunks)
        rows = value.get("data", []) if isinstance(value, dict) else []
        models = _choices(rows if isinstance(rows, list) else [], source="api")
        return {"models": models, "default_model": "", "warning": "" if models else "empty_catalog"}
    except (httpx.HTTPError, ValueError):
        raise ProviderError("Could not read models from the service. Check the connection or enter a model name.") from None
