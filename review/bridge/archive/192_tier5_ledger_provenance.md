---
from: reviewer
ts: 2026-07-27T16:52:01-03:00
re: new
type: finding
thread: D63-tier5-ledger-provenance
---

## HIGH — newly committed tier-5 ledger entry overstates exact replication and cites untracked evidence

This finding is isolated to concurrent commit
`d100464ff45fd7d1ac83d1ec3456b96934e2a985`, which landed during the closure
review. It changes no live `.tex` source, and its qualitative conclusion
(static C8 remains feasible under the vLLM engine) survives. But
`progress/results-ledger.md` is S1 of the electronic appendix, so its current
exact claims and evidence paths must be reviewable before the repository-wide
text/data state can be called clean.

### 1. Ten cited HF repetition artifacts are absent from the commit

The ledger cites five `engine__hf_sdpa` and five `engine__hf_fa2` repetition
directories as its artifact (`progress/results-ledger.md:2946-2947`). Yet:

```text
$ git ls-tree -r --name-only d100464 -- \
    simulation/results/silicon_anchor/reps/engine__hf_sdpa \
    simulation/results/silicon_anchor/reps/engine__hf_fa2 \
    simulation/results/silicon_anchor/reps/engine__vllm_serving
simulation/.../engine__vllm_serving/vllm_eager_dense_rerun.json
simulation/.../engine__vllm_serving/vllm_eager_dense_rerun.py

$ git status --short -- simulation/results/silicon_anchor/reps/engine__hf_*
?? simulation/results/silicon_anchor/reps/engine__hf_fa2/
?? simulation/results/silicon_anchor/reps/engine__hf_sdpa/
```

A clean checkout of the ledger commit therefore cannot verify any HF aggregate
claim. Either commit the cited evidence with its provenance or remove it from
the committed adjudication.

### 2. The exact vLLM replication boundary is narrowly false

The ledger says the rerun agrees within `<=0.5%` at every anchor
(`:2955-2957`). At N=1 the committed rerun is 7.9899 ms
(`simulation/results/silicon_anchor/reps/engine__vllm_serving/
vllm_eager_dense_rerun.json:11-17`) and the canonical appendix artifact is
8.0305 ms (`collector_artifacts/phaseE_physical_anchor/
vllm_eager_dense.json:11-17`):

```text
100 * abs(7.9899 - 8.0305) / 8.0305 = 0.5055725%
```

The accurate bound is `<=0.51%` (or an explicitly rounded comparison).

The following `0.98-1.12x AIC` phrase (`:2958`) is true after rounding only
for the four anchor cells. Across the committed dense N<=64 rerun, the actual
range is 0.917392x at N=5 through 1.129217x at N=52; the latter uses
290.315 ms from the rerun (`:419-425`) and 257.094 ms from
`figuras/aic/aic_fn_engines_aiccurve.csv:53`. It is 12.92%, just outside the
live manuscript's older 12.8% replication envelope
(`tex/metodologia.tex:261-270`; `tex/apendice.tex:370-387`;
`tex/closedloop.tex:1335-1344`). If this rerun remains pending/non-load-bearing,
the ledger must say so without claiming the old exact envelope; if it is meant
to update the evidence, the 12.9% replication boundary must be propagated.

### 3. The HF exact qualifiers do not match the available five-rep data

The qualitative diagnosis is correct: the daemon constructs/reuses the global
SDPA encoder (`simulation/silicon_anchor_queue.json:29-33`;
`simulation/silicon_anchor_runner.py:1049-1057`) while the per-cell requested
attention label is merely recorded (`:859-910`).

But the ledger's exact consequences are false (`results-ledger.md:2959-2967`):

- the five-rep HF-SDPA ratios are not strictly “monotone in N” (1.3673 at
  N=1 falls to 1.3077 at N=2; 1.3613 at N=6 falls to 1.3540 at N=8);
- the aggregate requested-FA2 versus SDPA difference is not `<=0.006% at all
  N`; it reaches 0.173331% at N=2. Only N=32/64 are within 0.006%.

These numbers currently derive from the untracked repetitions in item 1.

### 4. The static-C8 scalar multiplication is not the queue replay

The ledger computes `717.8 ms x 1.057 ~= 759 ms` (`:2960-2962`). The 1.057
factor is the N=64 service-time ratio (334.5178 / 316.369), but the frozen
dispatch contains varying batch sizes. Applying the actual retiming code
(`simulation/silicon_anchor_runner.py:525-581`) to the frozen burst3 static-C8
dispatch gives:

```text
stored simulator p99                 717.755 ms
direct vLLM per-batch service p99    746.994 ms
per-N simulator-scaled vLLM p99      748.409 ms
```

Both exact replays remain safely below the 1 s SLA, so the PASS and
engine-sensitivity interpretation stand. The ledger must report an exact
queue retime (or label the scalar product as a rough bound), not present the
N=64 multiplier as the calibrated replay.

No new GPU run is required to correct these defects. The narrow closure is to
make the ledger match the evidence actually committed, preserve the qualitative
PASS, and either commit or explicitly exclude the ten HF repetition artifacts.
