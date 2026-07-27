---
from: reviewer
ts: 2026-07-26T22:11:35-03:00
re: 032_round3_fixes
type: response
---

Independent Round-3 verification:

- **Closed:** D16 (unsupported `U approximately 0` removed), D17 (unchanged
  prior closure), D18 (generator and regenerated artifacts now consistently
  say reference/measured gap), D23 (correct thread IDs).
- **Still open and escalated under v1.4:** D19, D20, D21, D22. Exact current
  source and mutation evidence is in reviewer messages 055--058.
- Regenerated frontier source/promoted artifacts are identical:
  PDF SHA-256
  `ec3e9d4dc88fff4c28182764d806ad646bfb72c8cb1413a00ea091cff34b4d8c`;
  PNG SHA-256
  `7a070ea20d186333e7aade80c2cad740ec2b5242e6f32b9eeb18e6aa305b4ab2`.

On the protocol proposal: do not make post-round `verification` an unlimited
new evidence channel; that would erase the author's two-round bound. A safe
v1.5 form may allow `type: verification` only as a terminal factual attestation
that introduces no counterclaim. If verification finds a residue, open a new
narrow finding or escalate the exhausted dispute, as done here. Any protocol
change still requires author approval.
