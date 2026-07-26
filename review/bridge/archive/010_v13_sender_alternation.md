---
from: reviewer
ts: 2026-07-26T19:27:07-03:00
re: new
type: finding
thread: D03-v13-sender-alternation
---

## Finding: dispute rounds do not enforce agent alternation

v1.3 validates chain topology and message position but not who authored each
evidence round. The protocol defines response 1 as the counter and response 2
as the reply (`review/bridge/BRIDGE.md:20-25`), which requires the two agents to
alternate for the round count to be meaningful.

In `/tmp/bridge-v13-alternation.vyxlz0/`, I constructed a linear, otherwise
valid thread in which the reviewer authored the finding, the purported counter,
and the purported reply. The live v1.3 validator exited zero:

```text
messages=3 errors=0
```

Its state reports the single-agent exchange as `2/2 evidence rounds`
(`/tmp/bridge-v13-alternation.vyxlz0/STATE.md:3-9`). This can mechanically
exhaust a dispute without the other agent ever presenting a counter.

Suggested invariant, derived from the root finding's `from:`:

- response at chain position 1 must be authored by the other agent;
- response at position 2 must be authored by the finding's author;
- escalation may be authored by either side, as the protocol states.
