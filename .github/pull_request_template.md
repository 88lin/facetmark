## What changed, and why

<!-- What was wrong, not what you typed. -->

## Evidence

- [ ] `pytest -q` passes locally
- [ ] `ruff check src tests scripts` clean
- [ ] `python scripts/mcp_e2e.py` passes (only if MCP or search behaviour moved)

**If this changes retrieval behaviour**, also:

- [ ] The variant is a named configuration; no default moved in this commit
- [ ] Paired statistics reported (McNemar + bootstrap CI), not means
- [ ] The query set used did **not** suggest the change

Numbers, if any:

| | before | after | Δ | CI95 | won/lost | p |
|---|---|---|---|---|---|---|
| | | | | | | |

A change that makes the numbers worse but explains why is welcome. State it
plainly rather than framing it as a win — the CHANGELOG has room for negative
results and the report already leads with one.
