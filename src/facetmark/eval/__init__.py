"""Synthetic corpus plus the A-E retrieval ablation bench."""

from __future__ import annotations

from .corpus import (
    Corpus,
    EvalQuery,
    Page,
    QueryFileError,
    generate_corpus,
    load_corpus,
    load_query_file,
)
from .harness import (
    PASS_MARGIN_PP,
    QUERY_TYPES,
    RUNGS,
    Bench,
    Outcome,
    bootstrap_ci,
    build_bench,
    mcnemar,
    resolve_rungs,
    run_demo,
    run_eval,
    run_rung,
    summarise,
)

__all__ = [
    "PASS_MARGIN_PP",
    "QUERY_TYPES",
    "RUNGS",
    "Bench",
    "Corpus",
    "EvalQuery",
    "Outcome",
    "Page",
    "QueryFileError",
    "bootstrap_ci",
    "build_bench",
    "generate_corpus",
    "load_corpus",
    "load_query_file",
    "mcnemar",
    "resolve_rungs",
    "run_demo",
    "run_eval",
    "run_rung",
    "summarise",
]
