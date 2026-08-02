"""Retrieval: four facets, fused with reciprocal rank fusion.

    F1 content   vec_content KNN            -- what the page says
    F2 intent    vec_intent  KNN            -- what the page answers   (new)
    F3 lexical   fts_seg + fts_tri BM25     -- what the page literally says
    F4 context   time window / session /    -- when it was saved, and
                 folder co-membership          alongside what          (new)

F1-F3 vote through RRF. F4 does not vote; it multiplies the fused score,
because "saved in the same sitting" is a property of a pair, not an ordering
over the library, and because it is derived from the anchors F1/F3 produced --
letting it vote would be letting them vote twice.

The package is split so the fusion rule and the lexical facet can be imported
by the *indexing* side (the intent filter probes the half-built library) without
dragging in the full query pipeline and its provider dependency.
"""

from .context import ContextSignals, anchor_window, build_context, window_filter
from .decay import apply_decay, cold_bookmark_ids, decay_hits
from .graph import Expansion, expand, related
from .lexical import lexical_lists, lexical_search
from .pipeline import (
    CONFIGS,
    FULL,
    Config,
    SearchHit,
    SearchResponse,
    hydrate,
    quick_search,
    search,
)
from .rerank import LLMReranker, OverlapReranker, RerankDoc, Reranker, get_reranker
from .rrf import DEFAULT_K, Fused, rank_of, rrf
from .understand import QueryUnderstanding, classify, classify_assisted
from .vectors import content_list, intent_list, vector_lists

__all__ = [
    "CONFIGS",
    "DEFAULT_K",
    "FULL",
    "Config",
    "ContextSignals",
    "Expansion",
    "Fused",
    "LLMReranker",
    "OverlapReranker",
    "QueryUnderstanding",
    "RerankDoc",
    "Reranker",
    "SearchHit",
    "SearchResponse",
    "anchor_window",
    "apply_decay",
    "build_context",
    "classify",
    "classify_assisted",
    "cold_bookmark_ids",
    "content_list",
    "decay_hits",
    "expand",
    "get_reranker",
    "hydrate",
    "intent_list",
    "lexical_lists",
    "lexical_search",
    "quick_search",
    "rank_of",
    "related",
    "rrf",
    "search",
    "vector_lists",
    "window_filter",
]
