---
from: reviewer
ts: 2026-07-27T20:30:24-03:00
re: new
type: ack
---

## Author directive: gradual readability through evidence layering

The author wants the thesis more focused without weakening scientific rigor
and explicitly does **not** want a radical rewrite. For the current closeout,
apply only a low-risk first pass: remove repetition, preserve the chapter
architecture, and make one locus canonical. Larger relocations can follow
incrementally.

### The narrative contract

Every main-text result should contain, in this order:

1. the claim in absolute units;
2. the population/denominator and declared endpoint;
3. the one material caveat that changes interpretation; and
4. a precise appendix/provenance pointer.

Everything else may move down one evidence layer. Moving proof is acceptable;
deleting it or burying a conclusion-changing limitation is not.

For RQ3, the focused main claim is:

> Over the 5.60-day, 749,601-request evaluation span, forecast-informed
> placement uses 669.7 provisioned worker-hours. Under the frozen every-window
> p99 compliance rule, the cheapest passing common-warm reactive floor uses
> 801.8 hours (1.20 times the forecast); the shipped reactive arm uses 725.4
> hours under different readiness mechanics. The resource-time advantage is
> robust, while latency ordering is readiness-dependent.

That is the convention-minimized victory. It does not erase the predeclared
window gate, and it does not manufacture readiness-invariant latency
dominance.

### Phase 1 now: deduplicate, do not restructure

- Make `tex/closedloop.tex:638-742` the single detailed locus for the new
  metric stack and readiness-separated interpretation.
- In `tex/closedloop.tex:748-787`, remove the second recitation of
  7.7%/11.0%, violation count and excess mass; retain the 0.62-times headline,
  the frozen every-window gate, and a backward reference to the detailed
  locus.
- In the chapter summary (`tex/closedloop.tex:1495-1535`), retain one result
  sentence, one failure/limitation sentence and cross-references. Do not
  reproduce the full comparator ladder again.
- In the abstract (`tex/tese.tex:86-105`), keep one numerical RQ3 sentence:
  the 5.60-day population, 669.7 hours / 1.20-times equal-compliance result,
  and the readiness-dependent-latency caveat. The abstract should not carry
  the threshold sweep, paired counts or gate mechanics.
- In the introduction contribution statement (`tex/intro.tex:282-286`), state
  the contribution and result class, then point to Chapter 8; do not repeat
  the exact tied-window inventory.
- In the conclusion (`tex/conclusion.tex:41-80`), give the same compact
  readiness-qualified result once. Remove the second threshold ladder,
  exact crossing sequence and duplicated 45.0% sensitivity statistic.

Use “aggregate/window p99 values tie,” not “the tails tie”: the distributions
separate above p99. Use “5.60-day evaluation span,” not “full trace.”

### Phase 2 later: relocate dense robustness, preserving pointers

The main chapter should retain one compact summary table or one main frontier
figure. The appendix may carry:

- the complete 20-arm by six-threshold grid;
- the three readiness comparisons (shipped mixed, common warm and near-strict);
- the percentile ladder;
- the exact empirical-survival reversal interval and 3-versus-2 count;
- paired win/tie/loss and gross/net delay identities;
- M1--M2 interpolation details; and
- gate self-tests and negative probes.

The main text must still say that first-order dominance fails and that
threshold-free delay ordering reverses under common-warm readiness; only the
exact diagnostic detail moves.

### Provenance layer

Keep the existing claim-to-artifact row at `tex/apendice.tex:245-252` and
extend it to name the readiness-comparison block. Canonical reproducibility is:

1. tracked raw JSONL traces and schedules;
2. tracked `metric_stack.json`;
3. its compute-only generator and structural gate; and
4. the provenance DB as a queryable index/cross-check.

I connected to the live PostgreSQL provenance store and verified that
`provenance.current_encoder_summary` contains the aggregate shipped and
readiness-repair rows, including worker-time, p99 and request count. It does
not yet contain the new total-delay mass, paired outcomes or full survival
comparison. Do not make the mutable live DB the sole proof and do not make a
new DB loader a closeout blocker: the tracked artifact plus raw recomputation
gate is sufficient if the appendix points to it exactly.

### Facts that may not be pushed out of the main text

- the 5.60-day/749,601-request scope;
- the frozen every-window p99 success criterion;
- the shipped readiness asymmetry;
- the common-warm reversal in latency ordering;
- the post-hoc/descriptive status of total-delay synthesis; and
- the single-trace generalization limit.

This pass should shorten by consolidation, not by weakening definitions or
removing adverse evidence. Please finish the scientific correction first,
then apply this Phase 1 deduplication only; avoid a chapter-wide stylistic
rewrite during metric-stack closeout.
