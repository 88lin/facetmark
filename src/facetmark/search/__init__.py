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

from . import abstain
from .context import ContextSignals, anchor_window, build_context, window_filter
from .decay import apply_decay, cold_bookmark_ids, cold_census, decay_hits
from .graph import Expansion, expand, related
from .lexical import lexical_lists, lexical_lists_scored, lexical_search
from .pipeline import (
    ALL_CONFIGS,
    CONFIGS,
    EXPLORATORY,
    FULL,
    FUSED,
    PROFILES,
    Config,
    SearchHit,
    SearchResponse,
    default_config,
    hydrate,
    quick_search,
    search,
)
from .querylang import (
    FIELDS,
    QUERY_SYNTAX_HELP,
    DateRange,
    FieldFilter,
    ParsedQuery,
    parse_query,
)
from .rerank import LLMReranker, OverlapReranker, RerankDoc, Reranker, get_reranker
from .rrf import DEFAULT_K, Fused, guarantee_bonus, rank_of, rrf
from .understand import QueryUnderstanding, classify, classify_assisted
from .vectors import (
    content_list,
    content_list_scored,
    intent_list,
    intent_list_scored,
    vector_lists,
    vector_lists_scored,
)

__all__ = [
    "ALL_CONFIGS",
    "CONFIGS",
    "EXPLORATORY",
    "FUSED",
    "PROFILES",
    "default_config",
    "DEFAULT_K",
    "FULL",
    "Config",
    "ContextSignals",
    "DateRange",
    "Expansion",
    "FIELDS",
    "FieldFilter",
    "Fused",
    "LLMReranker",
    "OverlapReranker",
    "ParsedQuery",
    "QUERY_SYNTAX_HELP",
    "QueryUnderstanding",
    "RerankDoc",
    "Reranker",
    "SearchHit",
    "SearchResponse",
    "abstain",
    "anchor_window",
    "apply_decay",
    "build_context",
    "classify",
    "classify_assisted",
    "cold_bookmark_ids",
    "cold_census",
    "content_list",
    "content_list_scored",
    "decay_hits",
    "expand",
    "get_reranker",
    "guarantee_bonus",
    "hydrate",
    "intent_list",
    "intent_list_scored",
    "lexical_lists",
    "lexical_lists_scored",
    "lexical_search",
    "parse_query",
    "quick_search",
    "rank_of",
    "related",
    "rrf",
    "search",
    "vector_lists",
    "vector_lists_scored",
    "window_filter",
]
