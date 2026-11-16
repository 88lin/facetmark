"""Local named connections. Views and portable library exports omit credentials."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from . import admin
from .config import Settings

Channel = Literal["chat", "embed"]
MAX_PROFILES = 64
MAX_FILE_BYTES = 1024 * 1024
FIELDS = {
    "chat": frozenset(name for name in admin.WRITABLE
                      if name.startswith("chat_") and name != "chat_concurrency"),
    "embed": frozenset(name for name in admin.WRITABLE
                       if name.startswith("embed_") or name == "local_embed_path"),
}


class ProfileName(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Use a non-empty connection name without control characters")
        return value


class ProfileDraft(ProfileName):
    id: str = Field(default="", max_length=64, pattern=r"^[a-zA-Z0-9_-]*$")
    channel: Channel
    values: dict[str, Any] = Field(default_factory=dict)


def _path(data_dir: Path) -> Path:
    return data_dir / "model-profiles.json"


def read_profiles(data_dir: Path) -> list[dict]:
    path = _path(data_dir)
    if not path.exists():
        return []
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("Oversized connection file")
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("version") != 1:
            raise ValueError("Unsupported connection file")
        profiles = document["profiles"]
        if not isinstance(profiles, list) or len(profiles) > MAX_PROFILES:
            raise ValueError("Invalid connection list")
        ids: set[str] = set()
        for row in profiles:
            draft = ProfileDraft.model_validate(row)
            if (not draft.id or draft.id in ids or set(draft.values) != FIELDS[draft.channel]
                    or not isinstance(row.get("updated_at"), int)):
                raise ValueError("Incomplete connection")
            ids.add(draft.id)
        return profiles
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(500, "Saved connections could not be read. Restore model-profiles.json from a local backup; the file has been kept.") from exc


def write_profiles(data_dir: Path, profiles: list[dict]) -> None:
    raw = json.dumps({"version": 1, "profiles": profiles}, ensure_ascii=False).encode("utf-8")
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(413, "Saved connections exceed the local storage limit")
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".model-profiles-", dir=data_dir)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, _path(data_dir))
    except BaseException:
        with contextlib.suppress(OSError):
            Path(temporary).unlink()
        raise


def profile_settings(current: Settings, profile: dict) -> Settings:
    try:
        return admin.draft_settings(current, profile["values"])
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(400, "Saved connection is invalid. Check its endpoint, model and field types.") from exc


def _proof(settings: Settings, channel: Channel, result: dict, tested_at: int | None = None) -> dict | None:
    if result.get("ok") is not True or (channel == "embed" and result.get("dim_matches") is not True):
        return None
    return {"version": 2, "fingerprint": admin.probe_fingerprint(settings, channel),
            "tested_at": tested_at or int(time.time()),
            "result": {key: result[key] for key in ("ok", "model", "ms", "dim", "expected_dim", "dim_matches")
                       if key in result}}


def saved_proof(settings: Settings, profile: dict) -> dict | None:
    proof = profile.get("proof")
    if not isinstance(proof, dict) or not isinstance(proof.get("result"), dict):
        return None
    channel = profile["channel"]
    if proof.get("version") != 2 or proof.get("fingerprint") != admin.probe_fingerprint(settings, channel):
        return None
    return _proof(settings, channel, proof["result"], proof.get("tested_at"))


def profile_view(current: Settings, profile: dict, probes: dict) -> dict:
    candidate = profile_settings(current, profile)
    channel = profile["channel"]
    proof = admin.matching_probe(candidate, channel, probes) or saved_proof(candidate, profile)
    backend = candidate.chat_backend if channel == "chat" else candidate.embed_backend
    model = (candidate.chat_agent_model if channel == "chat" and backend == "agent" else
             candidate.local_embed_path if channel == "embed" and backend == "local" else
             getattr(candidate, f"{channel}_model"))
    return {"id": profile["id"], "name": profile["name"], "channel": channel,
            "backend": backend, "model": model, "agent": candidate.chat_agent if backend == "agent" else "",
            "base_url": getattr(candidate, f"{channel}_base_url") if backend == "endpoint" else "",
            "key_set": bool(getattr(candidate, f"{channel}_api_key")) if backend == "endpoint" else False,
            "configured": candidate.channel_ready(channel), "tested": bool(proof),
            "current": admin.probe_fingerprint(candidate, channel) == admin.probe_fingerprint(current, channel),
            "updated_at": profile["updated_at"]}


def update_profile_proofs(state, settings: Settings, results: dict) -> None:
    profiles = read_profiles(state.settings.data_dir)
    changed = False
    for row in profiles:
        channel = row["channel"]
        if channel not in results:
            continue
        candidate = profile_settings(settings, row)
        if admin.probe_fingerprint(candidate, channel) == admin.probe_fingerprint(settings, channel):
            row["proof"] = _proof(settings, channel, results[channel])
            changed = True
    if changed:
        write_profiles(state.settings.data_dir, profiles)


def register(app: FastAPI, deps: list, write_settings) -> None:
    @app.get("/admin/model-profiles", dependencies=deps)
    async def list_profiles(request: Request, channel: Channel | None = None) -> dict:
        state = request.app.state.fm
        async with state.lock:
            current = admin.draft_settings(state.settings, state.pending_settings)
            profiles = read_profiles(state.settings.data_dir)
            return {"profiles": [profile_view(current, row, state.probe_results) for row in profiles
                                 if channel is None or row["channel"] == channel]}

    @app.post("/admin/model-profiles", dependencies=deps)
    async def save_profile(body: ProfileDraft, request: Request) -> dict:
        state = request.app.state.fm
        if set(body.values) - FIELDS[body.channel]:
            raise HTTPException(400, "Only connection fields for the selected channel can be saved")
        async with state.lock:
            current = admin.draft_settings(state.settings, state.pending_settings)
            profiles = read_profiles(state.settings.data_dir)
            identity = body.id or uuid.uuid4().hex
            signature = hashlib.sha256(json.dumps({"name": body.name, "channel": body.channel,
                "values": body.values}, sort_keys=True).encode()).hexdigest()
            previous = next((row for row in profiles if row["id"] == identity), None)
            if previous:
                if previous.get("request_hash") != signature:
                    raise HTTPException(409, "This request ID belongs to a different saved connection")
                return {"profile": profile_view(current, previous, state.probe_results)}
            try:
                candidate = admin.draft_settings(current, body.values)
            except (ValueError, TypeError) as exc:
                raise HTTPException(400, "Invalid connection; check endpoint URLs and field types") from exc
            if any(getattr(candidate, key) != getattr(current, key)
                   for key in set(body.values) & admin.env_locked()):
                raise HTTPException(409, "Connection fields are controlled by environment variables")
            if any(row["id"] != identity and row["channel"] == body.channel
                   and row["name"].casefold() == body.name.casefold() for row in profiles):
                raise HTTPException(409, "A connection with this name already exists in this channel")
            if not previous and len(profiles) >= MAX_PROFILES:
                raise HTTPException(409, "Keep up to 64 named connections; remove an unused connection first")
            values = {key: getattr(candidate, key) for key in FIELDS[body.channel]}
            # Snapshot effective endpoint credentials, including explicit empty
            # keys. A later legacy/default endpoint must never fill a hole.
            values[f"{body.channel}_api_key"] = getattr(candidate, f"{body.channel}_api_key") or ""
            match = admin.matching_probe(candidate, body.channel, state.probe_results)
            proof = _proof(candidate, body.channel, match["result"], match.get("tested_at")) if match else None
            row = {"id": identity, "name": body.name, "channel": body.channel, "values": values,
                   "proof": proof, "updated_at": time.time_ns() // 1_000_000, "request_hash": signature}
            write_profiles(state.settings.data_dir, [item for item in profiles if item["id"] != identity] + [row])
            return {"profile": profile_view(current, row, state.probe_results)}

    @app.put("/admin/model-profiles/{profile_id}", dependencies=deps)
    async def rename_profile(profile_id: str, body: ProfileName, request: Request) -> dict:
        state = request.app.state.fm
        async with state.lock:
            profiles = read_profiles(state.settings.data_dir)
            row = next((item for item in profiles if item["id"] == profile_id), None)
            if row is None:
                raise HTTPException(404, "Saved connection no longer exists")
            if any(item["id"] != profile_id and item["channel"] == row["channel"]
                   and item["name"].casefold() == body.name.casefold() for item in profiles):
                raise HTTPException(409, "A connection with this name already exists in this channel")
            row.update(name=body.name, updated_at=time.time_ns() // 1_000_000)
            write_profiles(state.settings.data_dir, profiles)
            current = admin.draft_settings(state.settings, state.pending_settings)
            return {"profile": profile_view(current, row, state.probe_results)}

    @app.delete("/admin/model-profiles/{profile_id}", dependencies=deps)
    async def remove_profile(profile_id: str, request: Request) -> dict:
        state = request.app.state.fm
        async with state.lock:
            profiles = read_profiles(state.settings.data_dir)
            if not any(row["id"] == profile_id for row in profiles):
                raise HTTPException(404, "Saved connection no longer exists")
            write_profiles(state.settings.data_dir, [row for row in profiles if row["id"] != profile_id])
            return {"removed": profile_id}

    @app.post("/admin/model-profiles/{profile_id}/apply", dependencies=deps)
    async def apply_profile(profile_id: str, request: Request) -> dict:
        state = request.app.state.fm
        async with state.lock:
            profiles = read_profiles(state.settings.data_dir)
            row = next((item for item in profiles if item["id"] == profile_id), None)
            if row is None:
                raise HTTPException(404, "Saved connection no longer exists")
            current = admin.draft_settings(state.settings, state.pending_settings)
            candidate = profile_settings(current, row)
            locked = admin.env_locked()
            if any(getattr(candidate, key) != getattr(current, key) for key in set(row["values"]) & locked):
                raise HTTPException(409, "Connection fields are controlled by environment variables")
            values = {key: value for key, value in row["values"].items() if key not in locked}
            result = await write_settings(admin.SettingsPatch(values=values), request)
            proof = saved_proof(candidate, row)
            if proof:
                admin.remember_probe(state.probe_results, row["channel"], proof["fingerprint"], proof["result"], candidate)
                admin.persist_probes(state.settings.data_dir, state.probe_results)
            active = admin.draft_settings(state.settings, state.pending_settings)
            return {**result, "profile": profile_view(active, row, state.probe_results)}
