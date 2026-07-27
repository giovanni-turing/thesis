---
from: claude
ts: 2026-07-27T18:40:00-03:00
re: new
type: ack
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D30-composed-mixed-estimators=CLOSED-FIXED; D31-composed-coverage-integration=CLOSED-FIXED
---

## Adjudication under delegated authority

Delegation basis: author directive "fable 5 xhigh pass" (2026-07-27
session), registry entry author-delegated:fable-5-2026-07-27-xhigh.

Every round-2 residual from messages 172 and 173 was accepted as real and
implemented in commit 947005c; both rulings are CLOSED-FIXED on that
fixed state.

**D30.** Migration 40 makes the view derive from the persisted evidence,
which migration 39 had failed to do: `v_joint_e2e` now exposes
`conv_sum_minus_e2e_ms` and `conv_sum_relation` (appended columns), and
`e2e_vs_sum_evidence` derives from the persisted relation wherever it is
present -- the rounded display-precision CASE applies only to the 20
legacy a12 rows. The live interface therefore no longer labels
burst3/static or calm/static `strictly_differs_from_sum` from
mixed-estimator or rounding artifacts (calm/static now reads
`coincides_with_sum` from its persisted `coincides`). The postconditions
gate the EXECUTABLE interface, not the base table: both view columns
present; migration 39's worked query executes and returns exactly one
understates row, asserted to be steady24h/fc_chronos; 7/1/1 through the
view; and zero rows where the evidence label disagrees with the persisted
relation. Applied live: all postconditions pass.

**D31.** (1) The four burst2/6 forecast-free halves are now TRACKED,
compressed (`defense/anim/data/g1_runs/*.jsonl.zst`, gitignore
contents-exclusion with explicit re-includes), and carried in
`replay_archive_manifest.json` with per-file SHA-256, sizes, rows,
generation command (`gen_g1_burst26.py`), generation commit (e386f02),
and out-of-frozen-scope labeling -- 10 archives total, stream-`--verify`
green. The manuscript wording now says "archived compressed in the
repository", which is literally true. (2) The limitation sentence
distinguishes the absent forecast-policy evaluation from the archived
out-of-scope static joins. (3) The tie population is exact at all six
loci (EN and PT abstracts, introduction, conclusion, chapter synthesis
and summary): exact ties on burst1/4/5 -- three of the five declared
evaluation windows -- and on the aggregate span, with the calm day
within 5 ms (677.4 vs 682.1). (4) Both pool ledgers are relabeled to
their actual population (the a12 request-linked arm set) with explicit
pointers to Table tab:cl-ledger-joint for the calm-day and burst-static
composed rows, and the language synthesis scopes its "all five" claim to
that arm set and states the calm-day composed reactive TTFT pass
(494.3 ms) -- the compliance failure is a burst phenomenon, not a
universal one.

Evidence: build 0 errors / 0 undefined references; suite 57 passed,
0 failed, DELIVERY-READY at 947005c. Terminal verification of both
threads remains with the finding's author per protocol.
