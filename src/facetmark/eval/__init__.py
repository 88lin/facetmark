"""Synthetic corpus plus the A-E retrieval ablation bench."""

from __future__ import annotations

from .corpus import Corpus, EvalQuery, Page, generate_corpus, load_corpus
from .harness import (
    PASS_MARGIN_PP,
    QUERY_TYPES,
    RUNGS,
    Bench,
    Outcome,
    bootstrap_ci,
    build_bench,
    mcnemar,
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
    "bootstrap_ci",
    "build_bench",
    "generate_corpus",
    "load_corpus",
    "mcnemar",
    "run_demo",
    "run_eval",
    "run_rung",
    "summarise",
]
