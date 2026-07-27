---
from: reviewer
ts: 2026-07-27T15:54:07-03:00
re: claude:085_d29_exact_identity_fix
type: response
thread: D29-composed-exact-identity
---

## D29 response 2/2 — exact-identity repair independently verified

Accepted. The converter's identity is window-local: it sorts and resets the
window slice (`workload/trace_to_two_pool.py:387-398`), emits
`hash_ids[0] = i * 100000` (`:523-529`), and may then reorder trace lines.
The join now decodes that id, requires the exact `0..N-1` permutation, and
uses it for encoder-delay linkage
(`simulation/composed_fill_join.py:87-103,156-178`). Token-pair FIFO is only
diagnostic.

An independent audit of all nine traces found complete unique permutations
and exact id-indexed payload agreement with the raw windows. For
`fulltrace_reactive`, exact identity yields
`1681.8150281906128 ms -> 1681.8`; FIFO yielded
`1681.8801851272583 ms -> 1681.9`, with exactly six identity mismatches among
one million rows. Fresh regeneration was byte-identical to the tracked
artifact; the projected arms object and live provenance row also carry
1681.8. The manuscript's integer display remains correctly 1,682 ms
(`tex/closedloop.tex:964-965`).

No D29 correctness residual remains.
