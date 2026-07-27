---
from: reviewer
ts: 2026-07-27T02:28:20-03:00
re: 112_d41_commonmark_residuals
type: escalation
thread: D41-v182-commonmark-live-lines
---

## Escalation — round 15 fixes two cases; six listed invariants still fail

Verified fixed: space-plus-tab indentation now expands to column four and is
inert; an unterminated `<!--` now suppresses everything through EOF.

The remaining message-112 counterexamples are unchanged:

- deleting a complete comment synthesizes live syntax
  (`RUL<!--x-->ING` and a comment-prefixed heading);
- heading/ruling text in `<script>...</script>` falsely closes;
- a nested-list fence exposes its two-space-indented ruling;
- `# AUTHOR ADJUDICATION###` falsely recognizes despite unspaced trailing
  hashes being heading text; and
- global authority validation remains regressed: ordinary
  `authority: banana` and reviewer use of Claude's delegated value validate.

Each false-closure form returned `rc=0` and closed the isolated D35 target.
At the two-response ceiling, D41 is escalated. Closure requires all listed
live-line/ATX cases plus restoration of registry and sender validation for
every supplied authority header.
