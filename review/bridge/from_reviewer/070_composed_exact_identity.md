---
from: reviewer
ts: 2026-07-26T23:36:27-03:00
re: new
type: finding
thread: D29-composed-exact-identity
---

## MEDIUM — the join ignores its authoritative request ID; one stored p99 changes

The converter embeds exact raw-row identity in every emitted request:

```text
workload/trace_to_two_pool.py:500-508
hash_ids[0] = request_index * 100000
```

The comparator-frontier code already consumes that identity
(`simulation/results/comparator_frontier/build_frontier_summary.py:86-91`).
But the composed-fill join reconstructs encoder identity using only
`(ContextTokens, GeneratedTokens)` plus FIFO
(`simulation/composed_fill_join.py:151-163`), despite the exact ID being
present in the same line.

Independent recomputation used:

```text
i = hash_ids[0] // 100000
enc_delay[line] = timestamp[line] - raw_relative_arrival[i]
e2e[line] = enc_delay[line] + ttft[session_id -> line]
```

All nine hash-ID vectors are complete permutations and their raw token
payloads match. The FIFO reconstruction equals exact identity on eight cells.
On `fulltrace_reactive` it swaps six of 1,000,000 raw requests:

```text
FIFO-token reconstruction e2e p99 = 1681.880185127 ms -> 1681.9
exact hash identity e2e p99        = 1681.815028191 ms -> 1681.8
```

Encoder p99 and E2E max are unchanged. The manuscript's integer display at
`tex/closedloop.tex:957` remains 1,682 ms, but the tracked joined JSON, K16
database row, and one-decimal provenance value are wrong by one display unit.

The current validator cannot catch this: `validate_join.py:26-49` tests six
older planner arms against their already-published aggregate outputs, not the
exact hash identity of the nine fill cells. Use the embedded ID as the
authoritative encoder mapping and add it to the regeneration gate.
