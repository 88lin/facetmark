# The context gate, measured on the queries it should stay out of

Protocol: [`gate-precision-protocol.md`](gate-precision-protocol.md), frozen
2026-08-04 before a single probe query existed. Rules quoted below in §5 were
not written after the numbers.

Artifacts:

| file | what it is |
| --- | --- |
| `eval/queries/gate-precision.jsonl` | the 361 probes, frozen before either rung ran |
| `eval/gate-precision-gen.json` | generation log: frame, drop rates, token spend |
| `eval/gate-precision-eval.json` | `A` vs `A_gatedctx`, 361 queries |
| `eval/gate-precision.json` | the pre-registered verdict, computed by `scripts/gate_precision.py` |
| `eval/gate-v2-probe.json` | the remedy on the probe set (gate a) |
| `eval/gate-v2-holdout.json` | the remedy on the 616 W2/W3 queries (gate b) |
| `eval/gate-v2-disposition.json` | which pre-registered branch the two gates select |

---

## 1. Why this run exists

1.2.0 changed the default ranking for the first time since W1 on this evidence:

```
A -> A_gatedctx   +3.09pp Recall@5, CI95 [+1.79, +4.55], 19 better / 0 worse, n=616
  q_content       +0.00pp   (0 better / 0 worse, n=181)
  q_episodic      +8.48pp   CI95 [+4.91, +12.05]
```

The `q_content` row is what earned the gate its default. It is also the row
that cannot mean what it appears to mean, because of how those 181 queries were
made: the generator was told not to put dates in a content query. Of the 181,
**one** contained a year, so the gate fired on 1 of 181 (0.55%). A false
positive rate of 0.55% measured on a set built to contain almost no
opportunities for one is not a measurement of precision. It is a measurement of
the generator's instructions.

So the gate was shipped on 616 queries that tested when it *does* fire and
never tested when it *should not*.

## 2. The probe set

361 queries over 361 distinct bookmarks, one query per bookmark. Each one is a
topical search whose time expression belongs to the **subject matter**, never to
the filing date.

Frame: of 2,376 bookmarks, 1,727 have at least 300 characters of body text, and
**468** of those are about a year (1990-2025) that is not the year they were
saved. 400 targets were drawn from those 468, stratified by save year. 361
queries survived validation — 10.8% dropped for the year subtype, 8.5% for the
relative subtype, and 24 of the 39 drops were API parse failures rather than
validator rejections. The pre-registered floor was 200.

Two subtypes, 60/40 by seed:

| subtype | n | must contain | example |
| --- | --- | --- | --- |
| `p_year` | 199 | the content year, which differs from the save year | `2015年国际空间站咖啡机为什么那么贵那么重` (saved 2026, page about 2015) |
| `p_relative` | 162 | a relative time word | `recently overhyped tech fads that flopped completely` (saved 2026, page about 2025) |

Validation refused any query containing the save year, any query containing
save-action vocabulary, and any query that parroted the page title. It never
consulted `classify()` — whether the gate fires is the thing being measured, so
filtering on it would have guaranteed the answer.

The stratification came out at 286 Chinese-titled targets, save years
`{2022: 33, 2023: 46, 2024: 62, 2025: 63, 2026: 196}`, and a content-to-save
year distance of 2 / 7 / 15 years at p25 / p50 / p75.

**Firing rate: 361 of 361, 100.0%.** By rule: `time:absolute_year` 197,
`time:relative` 163, `time:n_ago` 1. Against 0.55% on the W2/W3 content
queries, from the same classifier and the same library.

## 3. The primary result

`A` vs `A_gatedctx`, same library, same clock (1785649110), 10,000 paired
bootstrap resamples, exact two-sided McNemar.

```
A          Recall@5 0.9058   Recall@1 0.801
A_gatedctx Recall@5 0.7175   Recall@1 0.363

Δ Recall@5  -18.83 pp   CI95 [-23.27, -14.68]
McNemar     3 better / 71 worse, p = 3.0e-16
detectable at 80% power with this many discordant pairs: 6.68pp
```

68 net losses out of 361. Recall@1 more than halves.

### The internal control the design did not plan for

A relative time word resolves against *now*, so a bookmark saved recently can
legitimately fall inside "last year". For 57 of the 162 relative probes the
resolved window does contain the target's own save time — there the gate is not
wrong. Splitting on that:

| subset | n | `A` | `A_gatedctx` | Δ Recall@5 | discordant |
| --- | --- | --- | --- | --- | --- |
| window cannot contain the answer | 304 | 0.8980 | 0.6743 | **-22.37 pp** [-27.30, -17.76] | 72 |
| window does contain the answer | 57 | 0.9474 | 0.9474 | **+0.00 pp** [-5.26, +5.26] | 2 |

This is worth more than the self-check the protocol asked for. That check —
Δ must be 0.00pp on queries where the gate never fires — is **vacuous here**,
because all 361 fired; an adversarial set is supposed to leave it empty. The
57-query split does the same job with data in it: when the gate's window is
right, the gate is free. The 22pp is the window being wrong, not the multiplier
being heavy.

### Secondary splits

| split | n | Δ Recall@5 | CI95 | McNemar |
| --- | --- | --- | --- | --- |
| `p_year` | 199 | -15.57 pp | [-21.11, -10.55] | 2 / 33 |
| `p_relative` | 162 | -22.84 pp | [-29.63, -16.67] | 1 / 38 |
| distance 1-2y | 119 | -21.85 pp | [-29.41, -15.13] | 0 / 26 |
| distance 3-7y | 87 | -17.25 pp | [-26.44, -9.20] | 1 / 16 |
| distance 8y+ | 155 | -17.42 pp | [-23.87, -10.97] | 2 / 29 |

The damage does not need a near-miss year. An eight-year-old window hurts about
as much as a one-year-old one, which is what a multiplicative boost on the wrong
2,376-row subset would predict.

**Verdict: `gate_precision_unqualified`.** Point estimate -18.83pp is at or
below the -2.0pp threshold and the CI95 upper bound -14.68pp excludes zero.
This is the one verdict that triggers a disposition.

## 4. The pre-registered remedy, and what it did

§6 of the protocol, written before the probe set existed: a bare
`time:absolute_year` stops counting as a filing-date signal on its own; it has
to arrive with a vague episodic marker or with save-action vocabulary.
`n_ago`, `time:relative` and `episodic_marker` are untouched. Implemented as
`Config.context_gate_version = 2` / `episodic_beyond_a_bare_year()`, and as the
rung `A_gatedctx_v2`.

Two bars, both frozen in advance.

**Gate (a) — the probe-set cost has to be gone (CI95 contains 0, or lower bound > 0).**

```
A -> A_gatedctx_v2   n=361   0.9058 -> 0.8006   -10.52 pp  CI95 [-13.85, -7.48]  1 / 39
  p_year             n=199   0.9095 -> 0.9045    -0.50 pp  CI95 [-1.51, +0.00]   0 / 1
  p_relative         n=162   0.9012 -> 0.6728   -22.84 pp  CI95 [-29.63, -16.67] 1 / 38
  v2 stays silent    n=197   0.9086 -> 0.9086    +0.00 pp  CI95 [+0.00, +0.00]   0 / 0
  v2 still fires     n=164   0.9024 -> 0.6707   -23.17 pp  CI95 [-29.88, -16.46] 1 / 39
```

**FAILED.** The narrowing works exactly as specified on the clause it names: the
197 probes it silences move 0.00pp with zero discordant pairs, and `p_year`
drops from -15.57pp to -0.50pp. The entire residual is `time:relative`, which
the remedy deliberately did not touch. (197 + 164 = 361; two `p_year` probes
also contain a relative word, and `_resolve_time` checks relative before
absolute, so they resolve as relative and still fire. That is the whole of
`p_year`'s remaining -0.50pp.)

**Gate (b) — the W2/W3 win has to survive (CI95 lower bound > 0 vs `A`).**

```
                       n=616   Recall@5           Δ vs A     CI95            McNemar
A                              0.5860
A_gatedctx  (v1)               0.6169             +3.09 pp   [+1.79, +4.55]   19 / 0
A_gatedctx_v2                  0.6039             +1.79 pp   [+0.81, +2.92]   11 / 0
  q_content  v2        n=181   0.9061             +0.00 pp   [+0.00, +0.00]    0 / 0
  q_vague    v2        n=211   0.6540             +0.00 pp   [+0.00, +0.00]    0 / 0
  q_episodic v2        n=224   0.3125             +4.91 pp   [+2.23, +8.04]   11 / 0
```

**PASSED.** Narrowing the year clause costs 8 of the 19 wins — the episodic
gain halves, from +8.48pp to +4.91pp — but the lower bound stays above zero.

## 5. Disposition

The protocol requires **both** bars. One passed, one failed, so `gate_v2` does
not ship, and the only non-shipping branch the protocol wrote is:

> 默认值退回 1.1.0 的无门控行为 — the default reverts to 1.1.0's ungated
> behaviour.

So `FULL` goes back to `content + graph + decay`, released as **1.3.0** because
the default ranking changes again. `A_gatedctx` and `A_gatedctx_v2` both stay in
the tree, implemented, off, and now with a number attached to why.

This gives up a measured +3.09pp on 616 queries to avoid a measured -18.83pp on
361. That trade is only obviously correct if you believe the probe distribution
is closer to real use than the holdout distribution is, and neither set is a
sample of real use. What decides it is that the protocol chose the branch before
the numbers arrived, for the reason it stated then: when a mechanism's sign
depends on a distribution nobody has measured, ship the behaviour that has never
been contradicted.

The obvious next move — narrow `time:relative` the same way — is **not taken
here**, and not because it looks unpromising. It looks quite promising: v2
already reduces `p_year` to -0.50pp and keeps +1.79pp, so a v3 that treats a
relative word the same way might clear both bars. It is not taken because these
361 queries have now been used to *choose between* two gates, which spends them.
A v3 selected on them and then tested on them would reproduce, exactly, the
circularity that made this run necessary. A v3 needs its own pre-registration
and its own probe set. Filed as a W4 item.

## 6. What this run does not measure

Four limits, stated in §5 of the protocol before any query existed and unchanged
by the results:

1. **It does not estimate a real false-positive rate.** The probe set is
   adversarial by construction — every query was built to look episodic and not
   be. 100% firing is a property of the design, not of a user's query log. The
   real rate lies somewhere between 0.55% (a set built to avoid dates) and 100%,
   and this run does not locate it.
2. **It prices the whole contextual multiplier, not just the wrong window.**
   Opening the gate also enables the session-peer and folder-peer boosts, which
   are not time-based. The 57-query control shows the window is the dominant
   term, but does not isolate it.
3. **Save timestamps in this library are constructed.** The corpus was
   assembled with synthetic `date_added` values on a plausible schedule, so
   "the window is wrong" is exact but "how wrong a real user's window would be"
   is not transferable.
4. **One library, one clock, one embedding model.** 2,376 bookmarks, bge-m3,
   clock 1785649110. Nothing here separates a property of the gate from a
   property of this corpus.

A fifth, found during the run rather than predicted: 57 of the 162 relative
probes have a window that legitimately contains the answer, so the headline
-18.83pp is diluted. The adversarial subset is -22.37pp. Both numbers are
reported; neither is substituted for the other.
