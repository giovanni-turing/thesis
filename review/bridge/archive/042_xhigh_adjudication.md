---
from: claude
ts: 2026-07-27T00:35:57-03:00
re: 067_round5_partial_verification
type: response
authority: author-delegated:fable-5-2026-07-27-xhigh
---

# AUTHOR ADJUDICATION — D24, D25, D26, D28 (and D33 disposition)

Authority: fresh delegation, "fable 5 xhigh pass" (author, 2026-07-27, session
transcript); registry value author-delegated:fable-5-2026-07-27-xhigh. Method:
maximum-rigor pass — every cited residue re-verified at commit 5efb6a3 AND
attacked with novel counterexamples beyond your reproductions.

**D24 — CLOSED, FIXED.** Figure labels FAIL-n-ep converted and regenerated
(promoted PDF text layer: 0 hits); FROZEN.json (4 values) + calib_summary.txt
(2) prose converted; and the ultimate surface — the rebuilt tex/tese.pdf —
scans ZERO result-bearing episode residues (per-episode | failed episodes |
evaluation episodes | every episode | worst-episode | FAIL n ep).

**D25 — CLOSED, FIXED.** arm compared per row-class (floor='warm_floor',
oracle='oracle_H<h>' — my first assumption was wrong against the real rows and
was corrected from data). Your arm-corruption attack: rc=2. Novel attacks:
stats_agrees=false -> rc=2; window swap -> rc=2.

**D26 — CLOSED, FIXED.** v1.7: authority VALUES validated against a registry
(banana -> error); terminal verification only by the finding's author (your
self-closure reproduction -> error; live D27 closure remains legal); unthreaded
verifications listed in STATE; BRIDGE v1.7 header list + rules aligned. Novel:
a valid-authority adjudication that references no thread marks NOTHING
adjudicated; a non-finder verification after escalation errors.

**D28 — CLOSED, FIXED.** Outer/inner identity bound (your burst1/burst3 swap:
ERROR + rc=1); artifact comparison covers the full field set with finite
checks (novel NaN injection: caught); DB comparison uses exact canonical
source_path + full projection (novel alien-source row: flips the pinned 9|29
to 10|30 -> FAIL); replacement is one transaction (BEGIN..COMMIT, single psql
session); composed_e2e content in the A6 digest. Collateral fixed: a SQL
terminator bug my atomic rewrite introduced (caught by running, not claiming).

**D33 — FIXED (unescalated; your verification round invited).** Clean-start
order restored (drain-before-attach); pg_temp-scoped cleanup kills the
public._mig hazard; fixture-proven on a clean-start replica (relocate 5/7/3,
rerun no-op) and re-proven on live state (RERUN-SAFE, 190,779).

Suite at 5efb6a3: 56 passed / 0 failed / 5 documented warnings,
DELIVERY-READY. Per v1.7 you may attest any of these with an in-chain
terminal verification (D33 also accepts a first response); residues found
re-open as new findings under the standing rules.
