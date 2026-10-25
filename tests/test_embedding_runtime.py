"""Optional local-encoder support must describe the runtime actually shipped."""
from types import ModuleType

import pytest

from facetmark import embedding_runtime
from facetmark.admin import settings_view
from facetmark.config import Settings
from facetmark.providers import LocalEmbeddingProvider, ProviderError


def test_packaged_desktop_reports_unavailable_local_encoder_and_recovery_path(tmp_path, monkeypatch):
    monkeypatch.setattr(embedding_runtime.sys, "frozen", True, raising=False)
    settings = Settings(data_dir=tmp_path, embed_backend="local", local_embed_path="synthetic-model")
    status = settings_view(settings)["local_embedding_runtime"]
    assert status == {"supported": False, "packaged": True, "reason": "desktop-unavailable"}
    assert not settings.channel_ready("embed")
    with pytest.raises(ProviderError, match="HTTP endpoint"):
        LocalEmbeddingProvider(settings)._load()


def test_python_local_dependency_is_detected_without_loading_torch(monkeypatch):
    monkeypatch.setattr(embedding_runtime.sys, "frozen", False, raising=False)
    seen = []

    def find(name):
        seen.append(name)
        return None

    monkeypatch.setattr(embedding_runtime.importlib.util, "find_spec", find)
    assert embedding_runtime.local_embedding_runtime()["reason"] == "dependency-missing"
    assert seen == ["sentence_transformers"]


@pytest.mark.parametrize("loaded", [ModuleType("sentence_transformers"), None])
def test_already_loaded_local_encoder_does_not_need_a_module_spec(monkeypatch, loaded):
    monkeypatch.setattr(embedding_runtime.sys, "frozen", False, raising=False)
    monkeypatch.setitem(embedding_runtime.sys.modules, "sentence_transformers", loaded)

    def find(_name):
        pytest.fail("Already-loaded modules must not be rediscovered")

    monkeypatch.setattr(embedding_runtime.importlib.util, "find_spec", find)
    status = embedding_runtime.local_embedding_runtime()
    assert status["supported"] is (loaded is not None)
    assert status["reason"] == ("available" if loaded is not None else "dependency-missing")
