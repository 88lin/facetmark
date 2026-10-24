"""Embedding identity shared by Web, CLI and vector stages."""
from __future__ import annotations

import hashlib
import json

from .config import Settings
from .db import SchemaMismatch, get_meta, validate_vec_schema


def space_id(settings: Settings) -> str:
    channel = settings.channel_settings("embed")
    parts = [
        settings.embed_backend,
        settings.embed_model,
        settings.embed_dim,
        settings.local_embed_path
        if settings.embed_backend == "local"
        else channel.base_url.rstrip("/"),
        settings.use_mock_provider,
    ]
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()


def validate_space(conn, settings: Settings) -> None:
    validate_vec_schema(conn, settings.embed_dim, settings.embed_model)
    stored = get_meta(conn, "embedding_space")
    if stored and stored != space_id(settings):
        raise SchemaMismatch(
            "Embedding endpoint or model changed. Confirm a backed-up vector rebuild in Settings."
        )
