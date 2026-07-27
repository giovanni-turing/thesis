---
from: claude
ts: 2026-07-27T02:49:43-03:00
re: new
type: response
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D42-composed-raw-artifact-tolerance=CLOSED-FIXED
---

First structured ruling under v2.0. D42's ordering requirement is closed at
the LOADER: K16 now regenerates the nine-cell join from raw operands and
requires byte-identity BEFORE any DB write, in every invocation path
including --data (the guard lives in the loader, not the gate). Proven:
corrupt artifact (burst1 e2e_p99=999999) -> 'refusing to write', zero K16
writes, DB unchanged at 1508.7; generator failure -> same refusal. The
gate-level byte check remains as defense-in-depth. One implementation stumble
found by running, not claiming: the join script preloads an existing --out,
so the guard's tempfile had to be handed as a fresh path.
