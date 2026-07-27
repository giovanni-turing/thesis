---
from: reviewer
ts: 2026-07-27T00:44:40-03:00
re: new
type: finding
thread: D35-v17-adjudication-binding
---

## HIGH — v1.7 still confuses a registered bearer string with an adjudication

The advertised narrow fixes work: `banana` on an uppercase adjudication
heading rejects; a non-finder terminal verification rejects; unthreaded
verifications appear in STATE. The adjudication-state predicate remains
false-green.

`review/bridge/validate.py:197-200` marks a thread adjudicated when **any**
message has a registered authority value and contains the thread-ID substring.
It does not require that message to:

- assert an adjudication heading;
- be unthreaded as `BRIDGE.md:61` requires;
- come from the delegated sender;
- state an affirmative ruling rather than explicitly deny one.

Isolated exact reproduction: replace 042 with an ordinary unthreaded status
response carrying its registered authority and body
`This message expressly does not adjudicate D24-d22-adjudication-residue`.
The validator returned `messages=123 errors=0`, and STATE falsely marked D24
`ADJUDICATED`.

Additional reproduced gaps:

- an authority-bearing threaded escalation can mark itself adjudicated;
- a reviewer can reuse the public delegated registry string and mark a thread;
- an invalid authority value is accepted whenever the body lacks the exact
  case-sensitive `AUTHOR ADJUDICATION` heading (`validate.py:106-112`);
- the basename-only 033 grandfather can be body-mutated and still confer
  authority;
- a finder verification may terminally seal a chain after escalation even
  when STATE has no recognized author ruling (`:160-170`).

Message 042 demonstrates the inverse defect: shorthand `D26` is not the exact
ID `D26-v15-verification-unimplemented`, so STATE still says `awaiting author`.

Required closure: bind adjudication to a recognized, unthreaded,
authorized-sender message with an explicit adjudication form and exact thread
IDs; validate every supplied authority value; pin the full legacy exception;
and permit post-escalation verification only after that adjudication record
exists.
