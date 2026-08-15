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
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from .configfile import config_path, read_config


def default_data_dir(*, os_name: str | None = None) -> Path:
    """Per-OS application data directory.

    Windows is the primary target platform, so it is checked first. ``os_name``
    defaults to the running interpreter's and is an argument only so the Windows
    branch can be tested from CI: patching :data:`os.name` is not an option,
    because ``pathlib.Path`` chooses its concrete class from that attribute and
    ``WindowsPath`` refuses to instantiate on POSIX.
    """
    if (os.name if os_name is None else os_name) == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / "facetmark"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "facetmark"
    return Path.home() / ".local" / "share" / "facetmark"


def split_list(value: object) -> object:
    """Coerce ``"a.example, b.example"`` into ``("a.example", "b.example")``.

    One definition, shared by the field validator below and by the admin API,
    because the two disagreeing is how a text box ends up assigning a ``str``
    to a ``tuple`` field -- at which point ``host_excluded`` iterates
    *characters* and the privacy list silently matches the wrong hosts.

    Commas or whitespace, since a domain contains neither, and duplicates are
    dropped in first-seen order: the same domain twice is a typo, not an
    instruction.
    """
    if not isinstance(value, str):
        return value
    return tuple(dict.fromkeys(value.replace(",", " ").split()))


class ConfigFileSource(PydanticBaseSettingsSource):
    """``<data_dir>/config.toml`` as the lowest-priority settings source.

    Registered last on purpose. See :mod:`facetmark.configfile` for why a file
    that loses every tie is the only version of this feature that is safe to
    add to an install base that has been exporting environment variables for a
    year.
    """

    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self._data: dict[str, object] | None = None

    @property
    def data(self) -> dict[str, object]:
        if self._data is None:
            try:
                self._data = read_config()
            except Exception as exc:  # noqa: BLE001 - re-raised with the path
                raise ValueError(f"cannot read {config_path()}: {exc}") from exc
        return self._data

    def get_field_value(self, field: object, field_name: str) -> tuple[object, str, bool]:
        return self.data.get(field_name), field_name, False

    def __call__(self) -> dict[str, object]:
        known = self.settings_cls.model_fields
        return {k: v for k, v in self.data.items() if k in known}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FACETMARK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Priority, highest first. The config file is deliberately last."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            ConfigFileSource(settings_cls),
        )

    # ---------- storage ----------
    data_dir: Path = Field(default_factory=default_data_dir)
    db_name: str = "facetmark.db"

    # ---------- model access (OpenAI-compatible, single entry point) ----------
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    chat_model: str = "gpt-4o-mini"
    chat_model_fallbacks: str = ""
    """Comma-separated models to try, in order, when ``chat_model`` will not
    answer. Empty by default: a paid endpoint that returns an error is telling
    you something, and swallowing it is worse than failing.

    This exists for free and shared endpoints, where a listed model can be
    absent, out of quota, or unable to honour ``response_format`` -- three
    failures that look nothing alike to a caller and identical to a run. The
    provider records which model actually answered each call, and any report
    built on a failover chain has to publish that mix; see
    ``providers.OpenAICompatibleProvider``."""
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536
    """Must match the model's real output dimension. Recorded in the ``meta``
    table on first index build; a later mismatch raises rather than silently
    mixing incompatible vectors."""

    embed_backend: str = "endpoint"
    """Where embeddings come from: ``endpoint`` or ``local``.

    ``endpoint`` is the default and the design rule -- one OpenAI-compatible
    base_url for everything. ``local`` exists because that rule has a real
    failure mode: a chat endpoint that does not serve ``/embeddings``. Free and
    aggregated endpoints frequently do not, and there is no advance warning --
    ``GET /v1/models`` will happily list six models and serve none of them to
    ``/embeddings``. With ``local``, chat still goes to the endpoint and only
    the encoder moves into this process; see ``providers.SplitProvider``."""

    local_embed_path: str = ""
    """Path or HuggingFace id of a sentence-transformers model, e.g.
    ``BAAI/bge-m3`` or ``/models/bge-m3``. Required when
    ``embed_backend='local'``. It must be the *same* model the index was built
    with -- a different encoder produces vectors in a different space, and
    sqlite-vec will return nearest neighbours from it without complaining."""

    local_embed_device: str = "cpu"
    local_embed_batch: int = 8
    local_embed_max_seq: int = 1024
    """Token budget per text for the local encoder.

    Not cosmetic. Reproducing this project's own bge-m3 index, 512 tokens gave a
    minimum self-cosine of 0.9769 against the stored vectors while 1024 gave
    0.99995 -- the shortfall was truncation of the longest documents, not a
    different encoder. 1024 covers the ~2,500-character ceiling that
    ``enrich.vectors.content_text`` produces; queries are far shorter and are
    unaffected either way. Raising it costs CPU quadratically for no gain here."""

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
    """Floor on how deep each facet is asked to rank.

    A floor, not a fixed value: a request for page N needs ``limit + offset``
    candidates to have anything to slice, so the pipeline raises the depth to
    cover the page and this setting only decides how much is fetched *beyond*
    that. Raising it costs one deeper KNN and one deeper FTS5 scan per facet;
    it does not change the ranking of anything already in the pool, because RRF
    scores a document from its *rank* inside a facet's list and that rank does
    not move when the list gets longer."""

    max_page_size: int = 200
    """Hard ceiling on one page of results.

    Not unbounded, and the reasons are all in this codebase rather than in
    general caution. A page is what the LLM reranker is handed (bounded again
    by ``rerank_depth``, but the page is the outer bound), what ``hydrate``
    turns into SQL placeholders, and what the caller has to hold in memory and
    -- for the MCP surface -- in a context window. 200 is well past what any
    UI renders at once; raise it in ``.env`` if a script wants bigger pages."""

    max_candidate_depth: int = 2000
    """Hard ceiling on per-facet retrieval depth, i.e. on how deep paging can go.

    ``limit + offset`` above this is answered with a truncated pool and
    ``depth_capped: true`` in the response, rather than silently returning a
    short page that looks like the end of the library. The cost this bounds is
    not the fusion -- that is linear and cheap -- it is the intent facet, which
    over-fetches ``depth * intent_keep_n`` vectors to survive deduplication, so
    depth 2000 is already a KNN of 8000 rows."""

    rerank_depth: int = 20
    """How many rows of a page the reranker is allowed to touch.

    Was a module constant in ``search.rerank`` that the pipeline overrode with
    the whole page, which tied stage E's cost to ``limit``. ``LLMReranker`` is
    listwise -- one ``chat_json`` call carrying a line per candidate, obliged to
    return a score for every id it was handed -- so a longer page grows the
    prompt and the demanded output together, and past some page size the "score
    every id" contract stops fitting the model's context window. That is a wrong
    answer, not merely a slow one. 20 is the depth ``search.rerank`` already
    documented; rows below it keep their fused order, and whether that beats a
    reranked tail has not been measured."""

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

    @field_validator("privacy_excluded_domains", mode="before")
    @classmethod
    def _domain_list(cls, v: object) -> object:
        """A comma-separated string is a shape callers actually send.

        The settings page renders this field as one text box, and
        ``chat_model_fallbacks`` next door has been comma-separated since it
        was added, so a string is what arrives. Refusing it made the only
        list-valued setting in the UI impossible to save, and ``Input should
        be a valid tuple`` is not a message anyone can act on.
        """
        return split_list(v)

    # ---------- service ----------
    host: str = "127.0.0.1"
    port: int = 8787

    admin_api: bool = True
    """Whether ``/admin/*`` -- import, index and settings -- is mounted.

    On by default because it is the entire first-run experience for anyone who
    is not going to use a terminal, and it is already gated twice: the pairing
    token, and a hard loopback check on the TCP peer that no configuration can
    lift. Turn it off on a shared or LAN-bound host where the token file is
    readable by someone you would not hand the API key to."""

    @field_validator("data_dir", mode="before")
    @classmethod
    def _expand(cls, v: object) -> object:
        if isinstance(v, str):
            return Path(os.path.expandvars(v)).expanduser()
        return v

    @field_validator("embed_backend")
    @classmethod
    def _known_embed_backend(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("endpoint", "local"):
            raise ValueError(f"embed_backend must be 'endpoint' or 'local', not {v!r}")
        return v

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_name

    @property
    def token_path(self) -> Path:
        """One-time pairing token handed to the browser extension."""
        return self.data_dir / "pairing-token.txt"

    def chat_model_chain(self) -> list[str]:
        """``chat_model`` first, then the fallbacks, deduplicated in order.

        Order is the caller's stated preference and is preserved exactly.
        Duplicates are dropped because retrying the same dead model under a
        second name costs a timeout and buys nothing.
        """
        chain: list[str] = []
        for name in (self.chat_model, *self.chat_model_fallbacks.split(",")):
            name = name.strip()
            if name and name not in chain:
                chain.append(name)
        return chain

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
