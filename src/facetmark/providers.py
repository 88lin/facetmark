"""One entry point for every model call, and a deterministic offline stand-in.

There is exactly one network shape here: the OpenAI-compatible REST surface
(``/chat/completions`` and ``/embeddings``). Anything that speaks it -- OpenAI,
DeepSeek, Moonshot, SiliconFlow, Ollama, vLLM, LM Studio, an OpenRouter key --
works by changing ``base_url``, with no code path of its own. Provider-specific
SDKs were deliberately not used: each one adds a dependency, a distinct error
taxonomy and a distinct retry story, in exchange for nothing this project needs.

``MockProvider`` is not a test double bolted on afterwards. It is what makes
``facetmark demo`` and the whole evaluation harness runnable with no credentials
and no network. Its embeddings are **hashed lexical features, not semantics** --
see the class docstring. Every report that uses it must say so.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass

import httpx

from .config import Settings, get_settings
from .text import segment


class ProviderError(RuntimeError):
    """A model call failed in a way retrying will not fix."""


@dataclass(slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    embed_tokens: int = 0
    calls: int = 0

    def add(self, other: Usage) -> None:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.embed_tokens += other.embed_tokens
        self.calls += other.calls

    def as_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "embed_tokens": self.embed_tokens,
            "calls": self.calls,
        }


class Provider(ABC):
    name: str = "abstract"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.usage = Usage()

    @property
    def embed_dim(self) -> int:
        return self.settings.embed_dim

    @property
    def embed_model(self) -> str:
        return self.settings.embed_model

    @abstractmethod
    async def chat_json(self, system: str, user: str) -> dict: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def aclose(self) -> None:  # pragma: no cover - trivial
        return None


# ---------------------------------------------------------------------------
# Offline deterministic provider
# ---------------------------------------------------------------------------

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+_.-]{1,}|\d+")
_CAPS = re.compile(r"\b[A-Z][A-Za-z0-9+.-]{2,}\b")
_STOP_WORDS = (
    "the a an and or of to in for on with is are was were be been this that these those "
    "it its as at by from into about over after before between not no but if then than "
    "\u4f60 \u6211 \u4ed6 \u7684 \u4e86 \u662f \u5728 \u548c \u4e0e \u53ca \u6216 \u5c31 \u90fd \u4e5f \u800c \u4f46 \u88ab \u628a \u4ece \u5230 \u5bf9 \u4e3a \u4e0a \u4e0b \u4e2d \u540e \u524d \u8fd9 \u90a3 "
    "\u4e00\u4e2a \u53ef\u4ee5 \u5982\u4f55 \u4ec0\u4e48 \u600e\u4e48 \u6211\u4eec \u4ed6\u4eec \u4f7f\u7528 \u8fdb\u884c \u901a\u8fc7 \u4e00\u4e9b \u5df2\u7ecf \u56e0\u4e3a \u6240\u4ee5 \u5982\u679c \u90a3\u4e48"
)
_STOP = frozenset(_STOP_WORDS.split(" "))


def _tokens(text: str) -> list[str]:
    """Latin words plus jieba-segmented CJK, stopped and lowercased."""
    out = [w.lower() for w in _WORD.findall(text)]
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        out += [w.lower() for w in segment(text).split() if len(w) >= 2]
    return [t for t in out if t not in _STOP and len(t) > 1]


def _h(token: str, salt: str = "") -> int:
    return int.from_bytes(hashlib.blake2b((salt + token).encode(), digest_size=8).digest(), "big")


class MockProvider(Provider):
    """Deterministic, offline, and honest about what it is.

    ``embed`` is **feature hashing over lexical tokens**, signed and
    L2-normalised. Two texts are close when they share words, not when they
    share meaning: it will score "canine" and "dog" as unrelated. That is
    sufficient to prove the *pipeline* end to end -- vectors are written, KNN
    returns neighbours, RRF fuses four ranked lists, the ablation runs -- and it
    is not sufficient to say anything about retrieval *quality*. Any number
    produced under this provider must be reported as a plumbing check.

    ``chat_json`` derives its fields from the text by frequency and shape. The
    intent queries it produces are templated, so the self-consistency filter has
    something real to accept or reject, but they are not what a language model
    would write.
    """

    name = "mock"

    async def chat_json(self, system: str, user: str) -> dict:
        self.usage.calls += 1
        self.usage.prompt_tokens += len(user) // 4
        body = user
        # Strip the framing the prompt builder adds, keep the page text.
        marker = "<<<PAGE>>>"
        if marker in body:
            body = body.split(marker, 1)[1]
        toks = _tokens(body)
        freq = Counter(toks)
        top = [w for w, _ in freq.most_common(8)]
        ents = list(dict.fromkeys(_CAPS.findall(body)))[:6]
        first = next((ln.strip() for ln in body.splitlines() if len(ln.strip()) > 30), body[:160])
        summary = first[:200]
        n = self.settings.intent_generate_n
        stems = (top or ["this page"])[:4]
        templates = [
            "how do i use {}",
            "what is {}",
            "{} tutorial",
            "{} best practice",
            "{} 是什么",
            "怎么用 {}",
            "{} 教程",
            "{} 对比",
        ]
        queries = [templates[i % len(templates)].format(stems[i % len(stems)]) for i in range(n)]
        out = {
            "summary": summary,
            "key_points": [f"{w}: mentioned {freq[w]} times" for w in top[:4]],
            "entities": ents,
            "topics": top[:5],
            "utility": "reference" if len(body) > 2000 else "note",
            "content_type": "article",
            "intent_queries": queries,
        }
        self.usage.completion_tokens += len(json.dumps(out, ensure_ascii=False)) // 4
        return out

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.usage.calls += 1
        dim = self.embed_dim
        vecs: list[list[float]] = []
        for t in texts:
            self.usage.embed_tokens += max(1, len(t) // 4)
            v = [0.0] * dim
            toks = _tokens(t)
            if not toks:
                toks = [t[:32] or "empty"]
            for tok, cnt in Counter(toks).items():
                w = 1.0 + math.log(cnt)
                hv = _h(tok)
                v[hv % dim] += w if (hv >> 32) & 1 else -w
                hv2 = _h(tok, "b")           # second hash: fewer collisions
                v[hv2 % dim] += 0.5 * (w if (hv2 >> 32) & 1 else -w)
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            vecs.append([x / norm for x in v])
        return vecs


# ---------------------------------------------------------------------------
# OpenAI-compatible provider
# ---------------------------------------------------------------------------

_RETRYABLE = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


class OpenAICompatibleProvider(Provider):
    name = "openai-compatible"

    def __init__(self, settings: Settings | None = None,
                 client: httpx.AsyncClient | None = None) -> None:
        super().__init__(settings)
        if not self.settings.api_key:
            raise ProviderError(
                "no API key. Set FACETMARK_API_KEY (and FACETMARK_BASE_URL for a "
                "non-OpenAI endpoint), or run with FACETMARK_USE_MOCK_PROVIDER=1."
            )
        #: Index into ``settings.chat_model_chain()`` that ``chat_json`` starts
        #: from. Only ever moves forward; see ``chat_json``.
        self._chat_at = 0
        self.chat_calls: Counter[str] = Counter()
        self.chat_failures: Counter[str] = Counter()
        self._own = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self.settings.base_url.rstrip("/"),
            timeout=self.settings.request_timeout,
            headers={"Authorization": f"Bearer {self.settings.api_key}",
                     "Content-Type": "application/json"},
        )

    async def aclose(self) -> None:
        if self._own:
            await self._client.aclose()

    async def _post(self, path: str, payload: dict) -> dict:
        last: Exception | None = None
        for attempt in range(self.settings.max_retries):
            try:
                r = await self._client.post(path, json=payload)
            except httpx.HTTPError as exc:
                last = exc
            else:
                if r.status_code < 400:
                    return r.json()
                if r.status_code not in _RETRYABLE:
                    raise ProviderError(f"{path} -> HTTP {r.status_code}: {r.text[:300]}")
                last = ProviderError(f"HTTP {r.status_code}")
            await asyncio.sleep(min(2 ** attempt, 8) * 0.5)
        # Name the exception *class*. httpx raises several of its timeout and
        # protocol errors with an empty message, so interpolating only ``last``
        # produces "failed after 3 attempts: " -- which was, for one full
        # indexing run, the entire diagnostic available for every third
        # failure.
        detail = f"{type(last).__name__}: {last}" if last else "no attempt was made"
        raise ProviderError(
            f"{path} failed after {self.settings.max_retries} attempts: {detail}"
        )

    async def _chat_once(self, model: str, system: str, user: str) -> dict:
        data = await self._post("/chat/completions", {
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        })
        u = data.get("usage") or {}
        self.usage.calls += 1
        self.usage.prompt_tokens += int(u.get("prompt_tokens") or 0)
        self.usage.completion_tokens += int(u.get("completion_tokens") or 0)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"unexpected chat response shape: {str(data)[:300]}") from exc
        # parse_json_object is inside the failover boundary on purpose: a model
        # that ignores response_format has failed at the only thing this method
        # is for, and that is not distinguishable from absence to the caller.
        return parse_json_object(text)

    async def chat_json(self, system: str, user: str) -> dict:
        """Ask the first model in the chain that will answer with a JSON object.

        Failover is **forward-only and sticky**: once a model answers, later
        calls start from it and never re-probe the ones already ruled out. On a
        3,000-page index run, re-probing a dead model per call is 3,000 wasted
        timeouts, and a model that vanished once rarely returns mid-run.

        With no fallbacks configured this is exactly the old single-model path,
        including which exception surfaces.
        """
        chain = self.settings.chat_model_chain()
        last: Exception | None = None
        for i in range(self._chat_at, len(chain)):
            model = chain[i]
            try:
                got = await self._chat_once(model, system, user)
            except ProviderError as exc:
                last = exc
                self.chat_failures[model] += 1
                continue
            self._chat_at = i
            self.chat_calls[model] += 1
            return got
        raise ProviderError(
            f"no chat model answered. Tried {chain[self._chat_at:]} "
            f"(last: {last})"
        ) from last

    @property
    def chat_model_in_use(self) -> str:
        """The model later calls will be sent to first."""
        chain = self.settings.chat_model_chain()
        return chain[self._chat_at] if chain else ""

    def chat_model_mix(self) -> dict[str, dict[str, int]]:
        """Answers and failures per model, for reports to publish verbatim.

        A run that silently changed models is a run whose ``chat_model`` field
        is a lie. Anything reporting numbers from a failover chain has to carry
        this dict with it.
        """
        return {
            "answered": dict(self.chat_calls),
            "failed": dict(self.chat_failures),
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        data = await self._post("/embeddings", {
            "model": self.settings.embed_model,
            "input": texts,
        })
        u = data.get("usage") or {}
        self.usage.calls += 1
        self.usage.embed_tokens += int(u.get("total_tokens") or 0)
        try:
            rows = sorted(data["data"], key=lambda d: d.get("index", 0))
            vecs = [list(map(float, d["embedding"])) for d in rows]
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(f"unexpected embedding response: {str(data)[:300]}") from exc
        if len(vecs) != len(texts):
            raise ProviderError(f"asked for {len(texts)} embeddings, got {len(vecs)}")
        got = len(vecs[0])
        if got != self.embed_dim:
            raise ProviderError(
                f"{self.embed_model} returned {got}-dim vectors but settings say "
                f"{self.embed_dim}. Set FACETMARK_EMBED_DIM={got} and rebuild the "
                f"index with `facetmark reindex --vectors`."
            )
        return vecs


# ---------------------------------------------------------------------------
# Local embeddings, and splitting chat away from them
# ---------------------------------------------------------------------------


class LocalEmbeddingProvider(Provider):
    """Embeddings from a sentence-transformers model loaded in this process.

    This exists because "one OpenAI-compatible endpoint for everything" has a
    failure mode the design did not anticipate: an endpoint that serves
    ``/chat/completions`` and not ``/embeddings``. Aggregators and free relays
    do this routinely, and ``GET /v1/models`` does not warn you -- it lists the
    chat models and says nothing about which surfaces will accept them.

    The trap this class opens is worse than the one it closes. sqlite-vec will
    return nearest neighbours for *any* 1024-dim query vector, including one
    from a completely different encoder; the results will be ranked, plausible,
    and meaningless. Nothing in the code can detect that, because the vectors
    are structurally valid. So before trusting a local encoder against an
    existing index, re-encode something the index already holds and take the
    cosine against the stored vector. Verbatim-text vectors (``vec_intent``)
    are the right probe: no recipe, no truncation, nothing between the string
    and the encoder. This project's own check on 64 of them reproduced at a
    minimum self-cosine of 0.999976, against a best *wrong* match of 0.6501 --
    that gap is the evidence, not the 0.99 on its own.

    ``embed_model`` stays the name written into the index's ``meta`` table;
    ``local_embed_path`` is only where the weights are read from. Keeping them
    separate is what lets a local encoder serve an index built by a remote one.
    """

    name = "local-embedding"

    def __init__(self, settings: Settings | None = None, *, model: object = None) -> None:
        super().__init__(settings)
        self._path = self.settings.local_embed_path.strip()
        if model is None and not self._path:
            raise ProviderError(
                "embed_backend='local' needs FACETMARK_LOCAL_EMBED_PATH set to a "
                "sentence-transformers model (a HuggingFace id like 'BAAI/bge-m3', "
                "or a directory)."
            )
        self._model = model

    def _load(self) -> object:
        """Load on first use, not on construction.

        ``get_provider`` is called in code paths that never embed anything, and
        a sentence-transformers import alone pulls in torch -- seconds of
        startup and hundreds of MB of RSS to do nothing.
        """
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - depends on install
                raise ProviderError(
                    "embed_backend='local' needs sentence-transformers: "
                    "pip install 'facetmark[local]'"
                ) from exc
            m = SentenceTransformer(self._path, device=self.settings.local_embed_device)
            m.max_seq_length = self.settings.local_embed_max_seq
            self._model = m
        return self._model

    async def chat_json(self, system: str, user: str) -> dict:
        raise ProviderError(
            "LocalEmbeddingProvider has no chat model. Pair it with one via "
            "SplitProvider, which is what get_provider() does for "
            "embed_backend='local'."
        )

    def _encode(self, texts: list[str]) -> list[list[float]]:
        m = self._load()
        raw = m.encode(  # type: ignore[attr-defined]
            texts,
            batch_size=self.settings.local_embed_batch,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [[float(x) for x in row] for row in raw]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Encoding is a blocking, CPU-bound call. Off the event loop it goes,
        # or every concurrent caller in the enrichment pipeline stalls behind it.
        vecs = await asyncio.to_thread(self._encode, texts)
        got = len(vecs[0])
        if got != self.embed_dim:
            raise ProviderError(
                f"{self._path or 'local model'} returned {got}-dim vectors but "
                f"settings say {self.embed_dim}. Set FACETMARK_EMBED_DIM={got}; if "
                f"an index already exists it was built at another width and has to "
                f"be rebuilt, not reconciled."
            )
        # calls, but no tokens: nothing here is billed, and reporting an invented
        # token count would make a local run look like a paid one in the usage
        # totals. A zero in embed_tokens next to a non-zero call count is the
        # honest shape.
        self.usage.calls += 1
        return vecs


class SplitProvider(Provider):
    """Chat from one provider, embeddings from another.

    The two model calls in this project have nothing in common but a base URL:
    one wants a large instruct model and tolerates seconds of latency, the other
    wants a small encoder and runs thousands of times. Tying them to the same
    endpoint was a simplification, not a requirement, and it breaks the moment
    an endpoint serves only one of them.

    Both halves must still agree with the index: ``embed_model`` and
    ``embed_dim`` are recorded in ``meta`` and are checked on open. Which chat
    model produced an enrichment is *not* recorded per row, so a report that
    mixes chat providers has to say so itself.
    """

    name = "split"

    def __init__(self, chat: Provider, embed: Provider,
                 settings: Settings | None = None) -> None:
        # Deliberately not calling super().__init__: this provider owns no usage
        # of its own, and a plain attribute would shadow the sum below.
        self.settings = settings or chat.settings
        self.chat_provider = chat
        self.embed_provider = embed

    @property
    def usage(self) -> Usage:
        """The two halves' usage, summed on every read.

        Derived rather than accumulated, so it cannot drift from what the halves
        actually did.
        """
        total = Usage()
        total.add(self.chat_provider.usage)
        total.add(self.embed_provider.usage)
        return total

    @property
    def chat_model_in_use(self) -> str:
        got = getattr(self.chat_provider, "chat_model_in_use", None)
        return got if isinstance(got, str) else self.settings.chat_model

    def chat_model_mix(self) -> dict[str, dict[str, int]]:
        fn = getattr(self.chat_provider, "chat_model_mix", None)
        return fn() if callable(fn) else {"answered": {}, "failed": {}}

    async def chat_json(self, system: str, user: str) -> dict:
        return await self.chat_provider.chat_json(system, user)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self.embed_provider.embed(texts)

    async def aclose(self) -> None:
        await self.chat_provider.aclose()
        await self.embed_provider.aclose()


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def parse_json_object(text: str) -> dict:
    """Recover a JSON object from a model reply.

    Models that honour ``response_format`` return clean JSON. Models that do not
    wrap it in a fence, or bracket it with an apology. Both are common enough
    that failing on them would make half the OpenAI-compatible ecosystem
    unusable, and cheap enough to handle here.
    """
    text = (text or "").strip()
    for candidate in (text, *(m.group(1).strip() for m in _JSON_FENCE.finditer(text))):
        try:
            got = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(got, dict):
            return got
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            got = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(got, dict):
                return got
    raise ProviderError(f"model did not return a JSON object: {text[:200]!r}")


def get_provider(settings: Settings | None = None, **kw) -> Provider:
    s = settings or get_settings()
    base: Provider
    if s.use_mock_provider or not s.api_key:
        base = MockProvider(s)
    else:
        base = OpenAICompatibleProvider(s, **kw)
    if s.embed_backend == "local":
        return SplitProvider(base, LocalEmbeddingProvider(s), settings=s)
    return base
