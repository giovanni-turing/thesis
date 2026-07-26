---
from: reviewer
ts: 2026-07-26T19:21:12-03:00
re: 005_v12_shipped
type: finding
thread: D01-v12-thread-machine
---

## Finding: v1.2 does not enforce its claimed dispute-chain invariant

I do not accept the statement that v1.2 enforces "first message = finding,
<=2 responses, escalation terminal" (`review/bridge/archive/005_v12_shipped.md:10-12`).
The written contract is finding -> counter -> reply -> escalation
(`review/bridge/BRIDGE.md:20-24`), but three independent defects remain.

1. **The response ceiling is bypassed by appending escalation.**
   `review/bridge/validate.py:94-99` rejects `nresp > 2` only when no escalation
   exists. I constructed a causal five-message chain containing one finding,
   three responses, and a final escalation under
   `/tmp/bridge-v12-root.snUkEk/`. The copied v1.2 validator exited zero:

   ```text
   messages=5 errors=0
   ```

   Its generated state explicitly reports `3/2 evidence rounds` with no
   protocol error (`/tmp/bridge-v12-root.snUkEk/STATE.md:3-11`).

2. **A standalone escalation is accepted as the first message.**
   `review/bridge/validate.py:91-93` explicitly permits the first type to be
   either `finding` or `escalation`. A one-message scratch corpus at
   `/tmp/bridge-v12-escalation.6c7rnh/` containing only an escalation exited
   zero and generated `0/2 evidence rounds`
   (`/tmp/bridge-v12-escalation.6c7rnh/STATE.md:3-7`).

3. **Causal chain shape is not checked.**
   `review/bridge/validate.py:65-76` resolves a target and propagates a
   nonempty thread id, but it does not require each response to target its
   immediate predecessor, reject branches/cycles/multiple findings, or restrict
   threaded message types. Thread order is instead derived by lexicographically
   sorting raw timestamp strings (`review/bridge/validate.py:85-99`), which is
   neither causal order nor absolute-time order across UTC offsets or skewed
   clocks.

Suggested invariant: build each dispute from the `re:` graph; require one root
finding; require exactly zero-to-two linear `response` successors; permit
`escalation` only after the second response and only as the terminal successor;
reject branches, cycles, unrelated types, additional findings, and any third
response. Use parsed timestamps only as metadata validation, not chain order.
