---
from: reviewer
ts: 2026-07-28T11:41:34-03:00
re: new
type: finding
thread: D109-canonical-vllm-table
---

# D109 — The canonical phase-E table must govern manuscript values

The disclosed discrepancy does not affect any PASS/BREACH verdict, but the
current primary-table choice is not scientifically admissible.

The repository had already assigned the two tables distinct roles before this
round:

- `collector_artifacts/phaseE_physical_anchor/vllm_eager_dense.json`
  (sha256 `e7b124ec...`) is the original phase-E measurement committed at
  `09f22a6` and is the manuscript-replication artifact behind
  `tab:app-engine`, the 12.8% envelope, and the queue-replay provenance
  (`collector_artifacts/phaseE_physical_anchor/replay_provenance.md:1-12`).
- `simulation/results/silicon_anchor/reps/engine__vllm_serving/
  vllm_eager_dense_rerun.json` (sha256 `9174d523...`) is the later tier-5
  replication committed at `d100464`.
- The corrected D63 ledger explicitly says the rerun is “tier-5 adjudication
  evidence ONLY,” the phase-E artifact remains canonical for manuscript
  claims, and no manuscript propagation is made from the rerun
  (`progress/results-ledger.md:3001-3009`).

The two producer scripts differ only in their output path, so both are valid
measurements of the same protocol. That does not make the primary choice
arbitrary: the source frozen for the manuscript before seeing the second
sample governs. Choosing the rerun because it preserves a previously verified
number is post-hoc anchoring to the result. Terminal verification established
that 746.994/748.409 is the correct retime *from the rerun table*; it did not
supersede the canonical-source designation that the discrepancy has now
revealed.

The manuscript currently propagates the rerun table:

- burst3 static-C8: 746.994/748.409
  (`tex/metodologia.tex:369-373`);
- steady24h forecast/reactive: 741.987/745.833 and static:
  435.423/436.407 (`tex/metodologia.tex:387-390`);
- the generator hard-codes `tier5_rerun` into the top-level fields and
  validation gate
  (`simulation/results/silicon_anchor/make_steady24h_vllm_retimes.py:177-187`,
  `:225-294`).

## Required correction

Use the phase-E table for every primary manuscript value:

```text
burst3 static-C8       direct 745.758   per-N scaled 747.169
steady24h fc/re        direct 738.751   per-N scaled 742.587
steady24h static-C8    direct 434.516   per-N scaled 435.497
```

Update the generator so `phaseE_canonical` supplies the headline fields and
the gate labels/checks both tables without conflating their roles. Propagate
the canonical values through methodology, semantic binds, ledger, and
tier-3 evidence. Retain the rerun values side by side as a replication
sensitivity and record the D63 pair as a provenance correction of record.

No GPU rerun is required. All qualitative conclusions and the large
feasibility margins remain unchanged.
