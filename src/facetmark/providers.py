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
        raise ProviderError(f"{path} failed after {self.settings.max_retries} attempts: {last}")

    async def chat_json(self, system: str, user: str) -> dict:
        data = await self._post("/chat/completions", {
            "model": self.settings.chat_model,
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
        return parse_json_object(text)

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
    if s.use_mock_provider or not s.api_key:
        return MockProvider(s)
    return OpenAICompatibleProvider(s, **kw)
