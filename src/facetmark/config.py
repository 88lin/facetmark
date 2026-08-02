"""Configuration.

Everything the user may need to tune lives here, loadable from a ``.env`` file or
environment variables prefixed with ``FACETMARK_``.

Design rule: the model layer is reached through **one** OpenAI-compatible endpoint.
A single ``base_url`` + ``api_key`` pair covers OpenAI, DeepSeek, Kimi, Zhipu,
SiliconFlow, Aliyun Bailian, Ollama and vLLM. There is deliberately no
provider-specific branching anywhere in the codebase.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_data_dir() -> Path:
    """Per-OS application data directory.

    Windows is the primary target platform, so it is checked first.
    """
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / "facetmark"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "facetmark"
    return Path.home() / ".local" / "share" / "facetmark"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FACETMARK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- storage ----------
    data_dir: Path = Field(default_factory=default_data_dir)
    db_name: str = "facetmark.db"

    # ---------- model access (OpenAI-compatible, single entry point) ----------
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    chat_model: str = "gpt-4o-mini"
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536
    """Must match the model's real output dimension. Recorded in the ``meta``
    table on first index build; a later mismatch raises rather than silently
    mixing incompatible vectors."""

    request_timeout: float = 60.0
    max_retries: int = 3

    #: When true, all model calls are served by the deterministic offline mock.
    #: This is what makes ``facetmark demo`` runnable with no credentials.
    use_mock_provider: bool = False

    # ---------- fetching ----------
    fetch_concurrency: int = 30
    fetch_per_host_concurrency: int = 2
    fetch_per_host_min_interval: float = 0.5
    fetch_timeout: float = 15.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 facetmark/0.1"
    )
    #: Read ``/robots.txt`` once per host and honour it. Turning this off is a
    #: decision the operator makes about their own liability, not a default.
    respect_robots: bool = True
    #: ``allow`` or ``deny``: what an *unreachable* robots.txt means. RFC 9309
    #: says deny; the default here is allow, because a 502 from one CDN should
    #: not silently remove the user's own pages from the user's own index.
    robots_on_error: str = "allow"
    #: Upper bound on an honoured ``Crawl-delay``, in seconds.
    robots_max_crawl_delay: float = 5.0
    #: Below this many characters the extraction is considered failed and the
    #: bookmark is queued for channel B (extension background tab).
    min_body_chars: int = 200
    #: Body text is truncated head+tail to this many characters before enrichment.
    body_truncate_chars: int = 6000

    # ---------- enrichment / intent ----------
    #: In-flight enrichment calls. The right value is a property of the backend,
    #: not of facetmark: a hosted API rations by tokens-per-minute and punishes
    #: bursts, while a self-hosted llama.cpp with continuous batching gets
    #: *faster* per token as the batch grows. 4 is a safe hosted default;
    #: a local server with N parallel slots wants N.
    enrich_concurrency: int = 4
    intent_generate_n: int = 8
    intent_keep_n: int = 4
    """How many self-consistent intent queries to keep. Report's ablation should
    sweep 2/4/6; this is a hyperparameter, not a constant."""
    intent_probe_top_k: int = 10

    # ---------- session reconstruction ----------
    #: Grid searched by the adaptive selector, in minutes.
    session_eps_grid_minutes: tuple[int, ...] = (5, 10, 20, 30, 45, 60, 90, 120, 180, 240)
    #: Manual override; when set, the adaptive search is skipped entirely.
    session_eps_minutes: int | None = None
    #: >this many bookmarks inside a 1-second window marks the batch as an
    #: import artifact, whose timestamps carry no episodic signal.
    import_artifact_per_second: int = 50

    # ---------- retrieval ----------
    rrf_k: int = 60
    """RRF smoothing constant. k=60 is the standard value and is not tuned."""
    candidates_per_facet: int = 50
    graph_expand_hops: int = 1
    graph_expand_factor: float = 0.6
    decay_factor: float = 0.5
    decay_age_days: int = 365
    #: If the hottest hit scores below this, the cold-layer demotion is lifted
    #: and results are re-ranked once as a fallback.
    decay_rescue_threshold: float = 0.02

    # ---------- link health ----------
    health_soft_gone_length_ratio: float = 0.30
    health_gone_confirm_days: int = 7
    #: Master switch for layer 2. Off means local-only probing, which by design
    #: can never reach the confidence that confirming `gone` requires.
    health_enable_external: bool = True
    #: Each third-party source is separately switchable, because they leak
    #: different things. DoH sees only the hostname; Wayback and the reader
    #: proxy see the full URL.
    health_enable_doh: bool = True
    health_enable_wayback: bool = True
    health_enable_reader: bool = True
    health_doh_endpoints: tuple[str, ...] = (
        "https://cloudflare-dns.com/dns-query",
        "https://dns.google/resolve",
    )
    health_wayback_api: str = "https://archive.org/wayback/available"
    health_reader_proxy: str = "https://r.jina.ai/"
    #: Layer 3. A user-supplied second egress; default off.
    health_proxy_url: str | None = None

    # ---------- privacy ----------
    #: Domains (suffix match) excluded from enrichment, embedding and every
    #: third-party probe. They degrade to title+lexical indexing only.
    privacy_excluded_domains: tuple[str, ...] = ()

    # ---------- service ----------
    host: str = "127.0.0.1"
    port: int = 8787

    @field_validator("data_dir", mode="before")
    @classmethod
    def _expand(cls, v: object) -> object:
        if isinstance(v, str):
            return Path(os.path.expandvars(v)).expanduser()
        return v

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_name

    @property
    def token_path(self) -> Path:
        """One-time pairing token handed to the browser extension."""
        return self.data_dir / "pairing-token.txt"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings(**overrides: object) -> Settings:
    """Process-wide settings singleton.

    Passing overrides builds a fresh instance instead of touching the singleton,
    which keeps tests isolated.
    """
    global _settings
    if overrides:
        return Settings(**overrides)  # type: ignore[arg-type]
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None
