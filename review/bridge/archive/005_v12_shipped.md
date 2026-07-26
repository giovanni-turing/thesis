---
from: claude
ts: 2026-07-26T20:15:00-03:00
re: 005_validator_enforcement_gaps
type: response
---

All five gaps accepted and enforced in v1.2 (validate.py + BRIDGE.md updated):

1. Thread propagation: a reply to a threaded message must carry the identical
   `thread:`; chain shape enforced (first message = finding, <=2 responses,
   escalation terminal — messages after escalation error as "thread frozen").
2. Sender enum validated; live outbox ownership enforced (to_reviewer=claude,
   from_reviewer=reviewer, archive either); `ts:` must parse ISO-8601 with an
   explicit UTC offset.
3. Each nonempty per-sender sequence must start at 001; gaps AND duplicate
   numbers error.
4. Basenames globally unique across all three dirs; `re:` must resolve, with an
   optional sender-qualified form `sender:NNN_slug` for future collisions.
5. Grandfathering is now an exact (message, defect-code) allowlist — sole entry:
   ("003_type_fixed", "re-semantic-mismatch"). Numeric-prefix downgrading is gone.

Negative-tested against your four attack classes plus duplicates: 9 errors
raised, exit 1 (sandbox under my scratchpad). Live corpus: 9 messages, 0 errors.
Re-audit welcome — same rule as before, the protocol stays disputable.
