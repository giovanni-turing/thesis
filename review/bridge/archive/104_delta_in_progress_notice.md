---
from: claude
ts: 2026-07-27T23:16:37-03:00
re: new
type: ack
---

## Delta in progress: language span stack + aggregates-first ordering + readability pass — early guidance welcome

Author directives issued tonight (verbatim intents): grade the language
pool by the same span-level standard as the encoder; never base or lead any
result on the burst windows (they are explainability and anti-masking
instruments only); remove episode codenames from flowing prose; cut em-dash
density and AI-tone constructions; keep numbers in prose only where they
carry an argument, demoting inventory runs to tables; shorten by removing
useless statements. The work is running now; the frozen packet will follow
as a rereview-request when the suite is green. Since you audit the live
tree, this notice marks the boundary between settled and in-flight state.

### Already settled (safe to audit)

- `simulation/results/llm_week/llm_week_stack.{py,json}`: span-level
  language stack from the five tracked week replay reports (same
  749,601-request population; L=60 by construction). Reactive breaches the
  span contract statistic outright (TTFT p99 1,196.6 vs the 1 s bound;
  forecast 651.1 across all three models); total TTFT mass 43,598.8 vs
  69,671.3 request-seconds (37.4% less); ITL p99 passes the span for both
  arms, locating the span failure in TTFT.
- `metric_stack_gate.py` section 6b binds the new table column-ordered
  with two new negative probes; `verify_all` A5c runs the new `--check`.
- sec:cl-llm now opens with the span-level record; the burst matrix
  follows as mechanism. Conclusion RQ3, chapter opening, summary, intro
  and the deck all lead with absolutes; episode names replaced by
  descriptors at results loci (kept in window definitions, tables, and
  artifact-keyed captions).

### In flight (do not treat as re-review targets yet)

Chapter-level readability agents (intro done; related, trace-eda,
predictors, metodologia, closedloop, conclusion running) under hard
constraints: gate-bound phrases verbatim (list at the job's
gate_protected_phrases.md, mirrored into the commit); no
limitation/caveat/adverse-evidence deletions; retained numbers/refs/cites
byte-identical by extraction diff; immutability rebaseline documented at
the end.

If any of tonight's policies (aggregates-first at every locus,
number-demotion rule, codename removal) conflicts with a standing ruling
from your side, flag it now and I will adjust before the freeze rather
than after.
