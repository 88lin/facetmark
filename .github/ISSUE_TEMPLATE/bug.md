---
name: Bug
about: Something crashed, corrupted, or behaved incorrectly
labels: bug
---

**What happened**, and what you expected instead.

**Reproduction.** The command line, and the smallest library that shows it. If
it involves import or crawl, a bookmark file with two entries is far more useful
than a description of one with two thousand.

**Traceback**, complete, not the last line.

**Versions.** `facetmark --version`, `python --version`, OS. Also
`facetmark stats` if the database is involved — schema version is printed there
and migrations are a plausible suspect.

**Configured provider.** Real embedding model, local server, or mock. This
changes which retrieval path runs.
