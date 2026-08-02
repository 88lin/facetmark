"""facetmark -- bookmark retrieval that indexes *why* you saved a page.

Existing bookmark tools all index the same thing: fetch body -> LLM summary and
tags -> one embedding -> semantic search. That indexes what the page *says*. What
actually survives in your memory months later is why you saved it and what you
were saving alongside it, and neither of those appears in the page body.

facetmark indexes four orthogonal facets and fuses them with Reciprocal Rank
Fusion:

* **F1 content** -- body -> summary -> vector (what every tool already does)
* **F2 intent** -- LLM-generated hypothetical queries (doc2query), vectorised
* **F3 lexical** -- BM25 over two FTS5 paths (trigram + jieba/unicode61)
* **F4 episodic** -- ``date_added`` session clustering plus folder co-location

F2 and F4 are the parts no existing tool has.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
