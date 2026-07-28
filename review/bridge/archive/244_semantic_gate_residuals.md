---
from: reviewer
ts: 2026-07-28T03:16:21-03:00
re: new
type: finding
thread: D72-semantic-gate-population-denominator-asymmetry
---

## D72 — three scientifically load-bearing role reversals still pass both gates

The committed prose is correct at these loci. The blocker is that the delivery
gates accept false statements that preserve the same numeric/textual multiset.
An isolated clean snapshot was mutated one case at a time; after every probe,
both checks returned:

```text
immutability OK: 10 chapters, numeric/ref/cite/env multisets identical to baseline
metric-stack gate: OK
```

The snapshot was inverse-patched after each probe and ended clean.

### 1. Abstract trace and evaluation populations can be swapped

Probe:

- `tex/tese.tex:68-69`: full trace changed from seven days / one million
  requests to 5.60 days / 749,601 requests.
- `tex/tese.tex:91-95`: the 0.62-times evaluation claim changed from 5.60 days /
  749,601 requests to seven days / one million requests.

Both gates stayed green. The correct roles are independently fixed by
`defense/anim/data/windows_ext.json:230-236` (Chronos offset 250,399,
749,601 targets, span 483,659.8 s) and the full-trace description at
`tex/tese.tex:68-69`. A swap silently extends the 0.62-times result to a
population on which no fixed-context forecast arm exists.

Minimal closure: locus-bind the full-trace population and the evaluation
population to their respective abstract clauses, including the Portuguese
mirror if it carries the same claim, and add a role-swap probe.

### 2. The 1.03-times language result can be relabeled time-matched

Probe: at `tex/conclusion.tex:192`, replace only `request-matched` with
`time-matched`. Both gates stayed green.

This reverses the result across unity:

```text
forecast artifact = 518.6063450234815 H100 GPU-h
time-matched static = 537.4093138649962 H100 GPU-h
518.6063450234815 / 537.4093138649962 = 0.96501182924

request-matched static
  = 672.0093014234247 * 749601 / 1000000
  = 503.7388443563 H100 GPU-h
518.6063450234815 / 503.7388443563 = 1.02951430257
```

Sources: `simulation/results/llm_week/week_fc_p90.report.json:7`,
`simulation/results/lang_qsweep/baseline_week/static_aggregate_tp2x2.report.json:7`,
and `provenance/audit/RESULTS_EVIDENCE.md:1026-1049`.
`provenance/verify_all.sh:243-252` checks both arithmetic results but not the
denominator word in the conclusion.

Minimal closure: bind `request-matched`, p90/scale-8, and 1.03-times together
at the conclusion locus, with a denominator-label probe.

### 3. Both defense mirrors can erase the post-hoc/asymmetric disclosure

Probe at `defense/reveal/index.html:512-513` and
`defense/deck_single.html:913-914`:

- `reactive-favorable post-hoc envelope` -> `pre-frozen symmetric envelope`;
- `no symmetric forecast+floor sweep` -> `a symmetric forecast+floor sweep`.

Both gates stayed green. The truth is fixed by
`simulation/results/comparator_frontier/FROZEN.json:83-95` (only the frozen
M=4 arm), `frontier_summary.json:360-363,1199-1206` (the post-hoc envelope,
M=6 cheapest passing, ratio 1.197), and
`tex/closedloop.tex:684-692,1593-1599` (reactive-favorable post-hoc selection
and the unrun symmetric forecast-plus-floor family).

Minimal closure: bind the disclosure and 1.20-times result together in both
deck mirrors, with a two-mirror semantic probe.

No experiment or printed result needs to change.
