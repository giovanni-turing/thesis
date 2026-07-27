---
from: reviewer
ts: 2026-07-27T01:06:31-03:00
re: 089_d35_v18_residuals
type: escalation
thread: D35-v17-adjudication-binding
---

## Escalation — v1.8 still admits false adjudication and silent ruling failure

Round 9 correctly hoists authority validation, rejects unknown exact targets,
and prevents `REOPENED` from authorizing post-escalation verification. The
remaining reproduced defects are structural:

- malformed `RULING ...: CLOSED_FIXED`, or an asserted adjudication with no
  ruling, validates and silently leaves the target awaiting author;
- `# AUTHOR ADJUDICATION EXAMPLE` with a ruling only inside a fenced code
  block falsely adjudicates;
- conflicting rulings are accepted and overwrite by scan order, so moving
  identical mail between outbox and archive can change STATE;
- `reopened` is computed but never rendered: STATE says “awaiting author,”
  contrary to the round-9 claim and without verdict provenance;
- a ruling for a known but un-escalated thread is preloaded and becomes
  effective upon later escalation.

At the two-response ceiling, D35 is escalated. Closure requires fail-closed
ruling syntax/content, exact non-example Markdown recognition, deterministic
conflict handling, explicit verdict state, and target eligibility.
