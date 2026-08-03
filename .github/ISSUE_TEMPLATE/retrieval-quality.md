---
name: Search returned the wrong thing
about: A query that should have found a page in your library, and did not
labels: retrieval
---

**The query, verbatim.** Copy exactly what you typed, including language and
punctuation — the classifier reads both.

**What you expected to find.** Title or URL is enough.

**Where it actually ranked**, if anywhere. `facetmark search "<query>" --limit 20`
shows the ranked page and the second, expansion group separately.

**What the system thought you meant.** Paste the `understanding` block:

```
facetmark search "<query>" --json | head -40
```

The `labels` and `time_window` fields matter most. A query read as `episodic`
takes a different path through the pipeline than one read as `content`, and
about half of the reports that look like ranking bugs are classification bugs.

**Which configuration ran.** The `config` field of the response, not the one you
asked for. With no embedding model configured the default falls back to lexical
fusion, and that fallback has measurably different behaviour.

**Library size.** `facetmark stats`.
