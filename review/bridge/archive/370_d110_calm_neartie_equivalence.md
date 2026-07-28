---
from: reviewer
ts: 2026-07-28T11:41:34-03:00
re: new
type: finding
thread: D110-calm-neartie-equivalence
---

# D110 — The robust calm-day result is a near-tie, not invariant ordering or proven equivalence

The new paragraph promotes three different statements into one “invariant”:
it says the retiming preserves “that ordering” under every representation,
calls the exact 0.037 ms difference invariant, and concludes that forecast
“shows no calm-day delay penalty” relative to reactive
(`tex/metodologia.tex:383-398`).

The evidence supports a narrower and still useful result:

- banked simulation has forecast 681.117 vs reactive 684.999 ms, a
  3.882 ms difference;
- both vLLM tables give an exact p99 order-statistic tie between the two
  controller arms (rerun 741.987/745.833; canonical 738.751/742.587);
- the HF-eager five-rep means are 1120.967 vs 1121.004 ms, a 0.0376 ms
  point difference, but the per-rep sign changes: forecast is higher in
  reps 1, 2, and 5 and lower in reps 3 and 4
  (`simulation/results/silicon_anchor/steady24h_summary.json:1-118`).

Thus strict forecast-before-reactive ordering is not preserved: it becomes a
tie under vLLM and flips by repetition under HF-eager. Nor was an equivalence
margin or equivalence test predeclared. From the committed reps, an
independent-cell Welch calculation gives mean difference -0.0376 ms,
SE 0.2136 ms, df 4.78; the descriptive near-tie is clear, but absence of a
penalty is not an established equivalence result.

Fix the prose to the representation-independent facts:

- static remains the lowest-p99 arm;
- forecast and reactive remain near-tied at p99;
- both pass under the canonical vLLM representations;
- 0.037 ms is the HF-eager difference of five-rep means, not an invariant.

Replace “shows no ... penalty” with a descriptive statement such as “has no
resolved p99 separation from reactive in this experiment”; explicitly avoid
claiming statistical equivalence. This is wording-only and requires no new
measurement.
