"""Stage E: reranking the top of the fused list.

Honest scoping first. The design document specifies a **cross-encoder** here.
This module does not ship one, and pretending otherwise would corrupt the
ablation. A cross-encoder is a supervised relevance model that reads the query
and the document jointly; shipping one means either a ~300 MB PyTorch download
at install time or a hosted reranking endpoint, and neither belongs in a tool
whose selling point is that it runs offline on a laptop.

What ships instead is the *role*, behind an interface, with two
implementations:

``LLMReranker``       listwise scoring through the same OpenAI-compatible chat
                      endpoint the rest of the system uses. This is a real
                      reranker with real quality, and it is what runs when the
                      user has configured credentials.
``OverlapReranker``   deterministic, offline, no model: term overlap between
                      the query and the title/summary, with the title weighted
                      up. This exists so ``facetmark demo`` and the test suite
                      have a stage E at all.

Consequence for the evaluation, stated here so it cannot be missed: **an
ablation run under the offline reranker measures the harness, not the idea.**
The A-E table produced by ``facetmark eval`` prints which reranker was active,
and a run whose stage E used ``OverlapReranker`` must not be quoted as evidence
that reranking helps.

Reranking touches only the top ``rerank_depth`` rows. Below that the fused
order is already better than a reranker's noise floor, and every additional row
is either latency (LLM) or nothing (overlap).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ..providers import Provider
from ..text import segment

DEFAULT_DEPTH = 20


@dataclass(slots=True)
class RerankDoc:
    doc_id: int
    title: str
    summary: str = ""


class Reranker(Protocol):
    name: str

    async def score(self, query: str, docs: Sequence[RerankDoc]) -> list[float]:
        """Relevance in [0, 1], aligned positionally with ``docs``."""
        ...


def _terms(text: str) -> set[str]:
    return {t for t in segment(text.lower()).split() if len(t) > 1}


class OverlapReranker:
    """Offline placeholder. Lexical overlap, title weighted 2x.

    Deliberately weak and deliberately deterministic. Its only job is to make
    stage E *exist* without a network call.
    """

    name = "overlap(offline placeholder)"

    async def score(self, query: str, docs: Sequence[RerankDoc]) -> list[float]:
        q = _terms(query)
        if not q:
            return [0.0] * len(docs)
        out: list[float] = []
        for d in docs:
            t = _terms(d.title)
            s = _terms(d.summary)
            hit = 2.0 * len(q & t) + 1.0 * len(q & s)
            out.append(min(hit / (2.0 * len(q)), 1.0))
        return out


_SYSTEM = "You rank bookmarks by how well they answer a search. Reply with JSON only."
_TEMPLATE = """Query: {query}

Candidates:
{candidates}

For each candidate return a relevance score from 0.0 (irrelevant) to 1.0 (exactly
what the query is looking for). Judge whether the page would satisfy the person
who typed the query, not whether the words overlap.

Return JSON: {{"scores": {{"<id>": <float>, ...}}}} covering every id above."""


class LLMReranker:
    """Listwise rerank through the configured chat model."""

    name = "llm-listwise"

    def __init__(self, provider: Provider, *, model_name: str = "") -> None:
        self.provider = provider
        if model_name:
            self.name = f"llm-listwise:{model_name}"

    async def score(self, query: str, docs: Sequence[RerankDoc]) -> list[float]:
        if not docs:
            return []
        lines = []
        for d in docs:
            summary = (d.summary or "")[:200]
            lines.append(f"[{d.doc_id}] {d.title}\n    {summary}".rstrip())
        try:
            payload = await self.provider.chat_json(
                system=_SYSTEM,
                user=_TEMPLATE.format(query=query, candidates="\n".join(lines)),
            )
        except Exception:
            # A reranker that fails must leave the fused order alone, not
            # collapse the page to zeros.
            return [0.0] * len(docs)
        raw = payload.get("scores")
        if not isinstance(raw, dict):
            return [0.0] * len(docs)
        out: list[float] = []
        for d in docs:
            v = raw.get(str(d.doc_id), raw.get(d.doc_id, 0.0))
            try:
                out.append(min(max(float(v), 0.0), 1.0))
            except (TypeError, ValueError):
                out.append(0.0)
        return out


def get_reranker(settings, provider: Provider | None) -> Reranker:
    """Pick a reranker. Mock or credential-less setups get the offline one."""
    if provider is None or getattr(settings, "use_mock_provider", False):
        return OverlapReranker()
    if not getattr(settings, "api_key", ""):
        return OverlapReranker()
    return LLMReranker(provider, model_name=getattr(settings, "chat_model", ""))


def reorder(
    hits: Sequence, scores: Sequence[float], *, depth: int = DEFAULT_DEPTH
) -> list:
    """Re-sort the first ``depth`` hits by rerank score, keeping the tail.

    The fused score is preserved on each hit; only the order changes. Ties fall
    back to the fused order, so a reranker that returns all-zeros is a no-op
    rather than a shuffle.
    """
    head = list(hits[:depth])
    tail = list(hits[depth:])
    order = sorted(
        range(len(head)), key=lambda i: (-float(scores[i]), i)
    )
    return [head[i] for i in order] + tail
