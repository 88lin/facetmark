---
name: Retrieval change proposal
about: An idea for improving search quality
labels: retrieval, needs-evidence
---

Read `docs/gate-w1.md` first if you have not. The four-facet fusion this project
was designed around lost its own ablation, and several intuitive fixes were
measured and found to do nothing. That report is the cheapest way to avoid
re-running an experiment that already has an answer.

**The mechanism.** What changes about how results are produced.

**Why you think it helps.** Which failure mode does it address?

**How it would be measured.** Which query type, which metric, and what
difference would count as a result rather than as noise. On 479 queries a 2pp
difference is routinely indistinguishable from zero, and per-type subsets buy
roughly ±4pp of confidence interval.

**Which query set.** If the evidence for the idea came from looking at a query
set, the test has to happen on a different one. Two knobs already ship switched
off for exactly this reason — see §9.5 of the report.

**What would make you drop it.** A proposal that no measurement could refute is
a preference, not a hypothesis, and preferences do not get to move the default.
