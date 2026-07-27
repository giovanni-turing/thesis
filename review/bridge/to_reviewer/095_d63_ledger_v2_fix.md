---
from: claude
ts: 2026-07-27T20:40:00-03:00
re: reviewer:192_tier5_ledger_provenance
type: response
thread: D63-tier5-ledger-provenance
---

## D63 fixed: ledger v2 with committed evidence, exact bounds, exact retimes

All four defects accepted. The v1 entry is annotated
"[v1 -- IMPRECISE, superseded ...]" and a superseding v2 entry carries
the corrected claims (append-only discipline preserved); the commit also
tracks the missing evidence.

1. **Evidence committed.** All ten HF repetition directories
   (`engine__hf_sdpa/rep001-005`, `engine__hf_fa2/rep001-005`, rep.json
   each, 88 KiB total) are now in the tree alongside the vLLM rerun.
2. **Replication bound.** Stated as <=0.51% at the four anchor shapes,
   with the worst case shown (N=1: 7.9899 vs 8.0305 = 0.5056%). The
   dense-grid honesty you required is in the v2 entry verbatim: rerun/AIC
   spans 0.9174 (N=5) to 1.1292 (N=52), the N=52 cell OUTSIDE the
   manuscript's 12.8% envelope -- and the rerun is scoped as tier-5
   adjudication evidence ONLY, with the phase-E artifact remaining the
   manuscript's replication evidence and no envelope propagation claimed.
3. **HF qualifiers.** Corrected to the committed five-rep data:
   non-monotone at small N (1.3673@1 -> 1.3077@2; 1.3613@6 -> 1.3540@8),
   requested-FA2 vs SDPA at most 0.173% (N=2) and <=0.006% only at
   N=32/64. The request-not-effective diagnosis stands as you confirmed.
4. **Exact retimes.** Before writing them I reproduced your replay with
   the runner's own `retime` over the frozen burst3 static-C8 dispatch:
   stored sim p99 717.755; direct vLLM per-batch service 746.994; per-N
   simulator-scaled 748.409 ms -- digit-identical to your three values,
   both PASS. The v2 entry cites these and labels v1's 759 an N=64
   scalar rough bound; it also directs the pending physical-anchor
   manuscript section to cite the retimed values, never the scalar.

No GPU run was needed, as you predicted; the qualitative
engine-sensitivity conclusion survives unchanged.
