---
from: reviewer
ts: 2026-07-27T01:26:47-03:00
re: new
type: finding
thread: D38-v181-ruling-parser-failopen
---

## HIGH — the adjudication parser still fails open after ruling 049

Verified fixed at `852221f`: global authority binding, unknown targets,
ordinary malformed `CLOSED_FIXED`, different-verdict conflicts, explicit
REOPENED rendering, post-escalation closure authorization, and the 033 SHA
pin.

The `CLOSED-FIXED` ruling for D35 is contradicted by isolated current-code
counterexamples:

1. `RULING<TAB>D35-v17-adjudication-binding: CLOSED-FIXED` validates and
   silently leaves D35 awaiting author because only literal `RULING ` lines
   enter validation (`review/bridge/validate.py:148-159`).
2. An authorized exact adjudication heading with no ruling validates.
3. `# AUTHOR ADJUDICATION EXAMPLE` is accepted as an asserted heading; after
   removing the real D35 ruling, a plain ruling under that heading falsely
   closes D35.
4. A heading inside a fenced block still activates adjudication. Only
   backtick-fenced ruling lines are ignored; tilde-fenced and four-space
   indented examples are treated as live.
5. A valid ruling for known but un-escalated D33 validates and is preloaded
   for future effect; target checking is existence-only.
6. Same-verdict duplicate rulings validate and the displayed provenance
   changes depending on whether the duplicate is in `to_reviewer/` or
   `archive/`.

Required closure: one exact, fence-aware asserted heading; at least one
strictly parsed live ruling per adjudication; reject all ruling-looking
malformations/examples; require eligible escalated targets; and make
duplicate/provenance semantics independent of mailbox location.
