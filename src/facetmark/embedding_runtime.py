"""Describe optional in-process encoders without importing their heavy runtime."""
from __future__ import annotations

import importlib.util
import sys


def local_embedding_runtime() -> dict:
    packaged = bool(getattr(sys, "frozen", False))
    if packaged:
        return {"supported": False, "packaged": True, "reason": "desktop-unavailable"}
    # A loaded module may have no __spec__ (for example, a runtime adapter).
    # find_spec raises for it, even though it is already available.
    if "sentence_transformers" in sys.modules:
        installed = sys.modules["sentence_transformers"] is not None
    else:
        installed = importlib.util.find_spec("sentence_transformers") is not None
    return {"supported": installed, "packaged": False,
            "reason": "available" if installed else "dependency-missing"}


def local_embedding_error() -> str:
    runtime = local_embedding_runtime()
    if runtime["packaged"]:
        return ("This desktop build does not include the in-process SentenceTransformer runtime. "
                "In Models settings, switch embeddings to an HTTP endpoint such as a local Ollama "
                "service, test it, and apply it. A different model or dimension requires the "
                "existing backed-up vector rebuild. Python installations can use facetmark[local].")
    return "The local embedding backend needs sentence-transformers: pip install 'facetmark[local]'"
