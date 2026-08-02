"""Enrichment: one model call per page, then two vector spaces.

The order matters and is enforced by the CLI:

    enrich_all      LLM -> summary, topics, entities, 8 candidate queries
    embed_content   facet 1 vectors (the probe needs these to exist)
    filter_intents  keep only the queries that retrieve their own page
    embed_intents   facet 2 vectors, for the survivors only
"""

from .intent import IntentReport, filter_intents, probe
from .pipeline import EnrichReport, Target, enrich_all, store_enrichment, targets
from .schema import Enrichment, EnrichmentInvalid, coerce
from .vectors import (
    VectorReport,
    content_text,
    embed_content,
    embed_intents,
    embed_query,
)

__all__ = [
    "IntentReport", "filter_intents", "probe",
    "EnrichReport", "Target", "enrich_all", "store_enrichment", "targets",
    "Enrichment", "EnrichmentInvalid", "coerce",
    "VectorReport", "content_text", "embed_content", "embed_intents", "embed_query",
]
