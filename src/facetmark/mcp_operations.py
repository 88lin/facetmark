"""Accept MCP settings and their original receipt in one config replacement.

Receipt metadata contains hashes and IDs only. The ordinary config writer
preserves these reserved scalar keys; Settings ignores them. Old tokens are
never copied into the receipt history or returned by confirmation.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time

from .config import Settings
from .configfile import config_path, external_setting_keys, read_config, update_config

HISTORY_KEY = "_mcp_operations"
GENERATION_KEY = "_mcp_generation"


class McpOperationConflict(ValueError):
    pass


def _digest(values) -> str:
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def configuration_revision(settings: Settings, values: dict | None = None) -> str:
    saved = read_config(config_path(settings.data_dir)) if values is None else values
    return _digest([str(settings.data_dir.resolve()), settings.mcp_enabled, settings.mcp_token, saved.get("mcp_enabled"),
                    saved.get("mcp_token"), saved.get(GENERATION_KEY),
                    sorted(external_setting_keys({"mcp_enabled", "mcp_token"}))])


def history(values: dict) -> dict:
    raw = values.get(HISTORY_KEY, "{}")
    try:
        receipts = json.loads(raw)
        if not isinstance(receipts, dict):
            raise ValueError
        for request_id, receipt in receipts.items():
            if (not isinstance(request_id, str) or not isinstance(receipt, dict)
                    or receipt.get("action") != "configure"
                    or receipt.get("state") not in {"accepted", "closed"}
                    or not all(isinstance(receipt.get(key), str) and len(receipt[key]) == 64
                               for key in ("fingerprint", "accepted_revision"))
                    or not isinstance(receipt.get("accepted_at"), int)):
                raise ValueError
        return receipts
    except (TypeError, ValueError):
        raise McpOperationConflict("MCP operation history could not be read; keep the original request for review") from None


def receipt(settings: Settings, request_id: str) -> dict | None:
    saved = read_config(config_path(settings.data_dir))
    found = history(saved).get(request_id)
    return {"request_id": request_id, **found} if found else None


def public_receipt(found: dict, settings: Settings) -> dict:
    return {"request_id": found["request_id"], "action": "configure",
            "state": found["state"],
            "accepted_revision": found["accepted_revision"], "accepted_at": found["accepted_at"],
            "superseded": found["accepted_revision"] != configuration_revision(settings)}


def accept_configuration(settings: Settings, *, enabled: bool | None, rotate_token: bool,
                         request_id: str | None, expected_revision: str | None) -> tuple[dict, dict | None]:
    """Called under the service metadata lock; no network wait owns that lock."""
    path = config_path(settings.data_dir)
    saved = read_config(path)
    receipts = history(saved)
    fingerprint = _digest([enabled, rotate_token, expected_revision])
    if request_id and request_id in receipts:
        found = receipts[request_id]
        if found["fingerprint"] != fingerprint:
            raise McpOperationConflict("This request ID belongs to a different original MCP configuration change")
        if found["state"] == "closed":
            raise McpOperationConflict("This original MCP change was closed; read the current settings before a new change")
        return {}, {"request_id": request_id, **found}
    if expected_revision is not None and expected_revision != configuration_revision(settings, saved):
        raise McpOperationConflict("MCP configuration changed in another window; read the current settings before changing them")
    changes = {}
    if enabled is not None and enabled != settings.mcp_enabled:
        changes["mcp_enabled"] = enabled
    token_changes = rotate_token or (enabled and not settings.mcp_token)
    keys = set(changes) | ({"mcp_token"} if token_changes else set())
    if external_setting_keys(keys):
        raise McpOperationConflict("MCP settings are set by the environment; unset the variables to edit here")
    if token_changes:
        changes["mcp_token"] = secrets.token_urlsafe(32)
    found = None
    if changes or request_id:
        metadata = {GENERATION_KEY: secrets.token_hex(16)}
        if request_id:
            prospective = settings.model_copy(update=changes)
            found = {"request_id": request_id, "action": "configure", "state": "accepted", "fingerprint": fingerprint,
                     "accepted_revision": configuration_revision(prospective, {**saved, **changes, **metadata}),
                     "accepted_at": int(time.time())}
            receipts[request_id] = {key: value for key, value in found.items() if key != "request_id"}
            metadata[HISTORY_KEY] = json.dumps(receipts, sort_keys=True, separators=(",", ":"))
        # The new token and receipt are in the same atomic file replacement.
        # A failed replacement accepts neither; a restart reads both.
        update_config({**changes, **metadata}, path)
    return changes, found


def close_configuration(settings: Settings, *, request_id: str, enabled: bool | None,
                        rotate_token: bool, expected_revision: str) -> dict:
    """Close an unaccepted original ID so its late request cannot still rotate.

If acceptance won the race, return its receipt and leave the current settings
alone. Closing an ID never revokes a token or rewrites an accepted operation.
"""
    path = config_path(settings.data_dir)
    saved = read_config(path)
    receipts = history(saved)
    fingerprint = _digest([enabled, rotate_token, expected_revision])
    if request_id in receipts:
        found = receipts[request_id]
        if found["fingerprint"] != fingerprint:
            raise McpOperationConflict("This request ID belongs to a different original MCP configuration change")
        return {"request_id": request_id, **found}
    found = {"request_id": request_id, "action": "configure", "state": "closed", "fingerprint": fingerprint,
             "accepted_revision": configuration_revision(settings, saved), "accepted_at": int(time.time())}
    receipts[request_id] = {key: value for key, value in found.items() if key != "request_id"}
    update_config({HISTORY_KEY: json.dumps(receipts, sort_keys=True, separators=(",", ":"))}, path)
    return found
