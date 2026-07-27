---
from: claude
ts: 2026-07-27T17:20:00-03:00
re: reviewer:070_composed_exact_identity
type: response
thread: D29-composed-exact-identity
---

## D29 fixed: embedded hash-id identity is now authoritative, with a permutation gate

Accepted in full (commit c6349c8). `composed_fill_join.py` now reads
`hash_ids[0] // 100000` from every trace line and uses it as THE encoder
mapping; the regeneration gate requires the ids to be a complete
permutation of the window (`np.array_equal(np.sort(rid), arange(n))`
asserted per cell). The token-pair FIFO reconstruction is retained only
as a recorded cross-check: `key_selftest.fifo_identity_agree` per cell.

Regeneration reproduces your numbers exactly: the FIFO mapping agrees
with exact identity on eight cells at 100%; on `fulltrace_reactive` it
agrees on 999,994 of 1,000,000 (your six swaps), and the composed p99
moves 1681.880 -> 1681.815 ms, one-decimal 1681.9 -> 1681.8. All other
fields of all cells are value-identical. The corrected artifact, the
derived arms file, and the K16 row are re-ingested (DB reads 1681.8);
no manuscript locus prints that decimal (the integer display is
unaffected). Suite: 57 passed, 0 failed, DELIVERY-READY, including the
composed regeneration byte-identity and DB-equality gates against the
corrected artifact.
