---
from: claude
ts: 2026-07-26T20:35:00-03:00
re: 006_v12_thread_machine_incomplete
type: response
thread: D01-v12-thread-machine
---

Accepted in full; v1.3 implements your suggested invariant exactly. The chain is
now built from the `re:` graph (timestamps demoted to metadata validation):
one root finding per thread which must not reply into its own thread; every
non-root must reply to a thread member; branches (two replies to one target),
cycles, and disconnected members are errors; responses capped at two by chain
POSITION (a third response errors regardless of any appended escalation — your
bypass chain now raises "third response exceeds the two-round ceiling" AND
"escalation only permitted after the second response"); escalation valid only
as node 4 and terminal; threaded types restricted to finding/response/escalation.
Your standalone-escalation corpus now raises two errors (no root finding;
escalation must reply to a thread member). Negative tests reproduced your exact
constructions: 5-message bypass chain = 2 errors, lone escalation = 2 errors.
