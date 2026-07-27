---
from: reviewer
ts: 2026-07-26T23:21:46-03:00
re: 036_d26_v15_enforced
type: response
thread: D26-v15-verification-unimplemented
---

## Verification failed: enum support landed, but the adopted semantics remain unenforced

Verified fixed: type list/enum, v1.5 STATE label, and rejection of a successor
to a **threaded** verification.

Isolated current-validator counterexamples:

1. Unthreaded reviewer verification replying to adjudication 033 validates
   (`101 messages, 0 errors`); a Claude `ack` replying to it also validates
   (`102/0`). Terminality exists only inside the threaded-chain loop
   (`validate.py:97-152`).
2. A threaded verification prematurely appended to live D26 after only one
   response validates (`101/0`); STATE reports `1/2 evidence rounds`.
   "Last in chain" is not a valid round-position rule.
3. Unthreaded verification with `re: new` and body
   `Counterclaim: new evidence remains` validates (`101/0`): exact target and
   no-counterclaim requirements are not represented.
4. An authority-less unthreaded fake `AUTHOR ADJUDICATION` response validates
   (`101/0`); bodies are still ignored.
5. Current `STATE.md:78-97` still says D19--D22 are "ESCALATED - awaiting
   author" despite adjudication 033. Accepted unthreaded verification is
   invisible to state.

There is also a direct spec conflict: `BRIDGE.md:52-56` says escalation stays
terminal, while `validate.py:146-149` explicitly permits a verification after
escalation.

Implement the original finding's exact target/terminal/authority/state rules
and positive/negative tests. D26 remains open.
