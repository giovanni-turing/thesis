---
from: reviewer
ts: 2026-07-27T16:34:09-03:00
re: claude:091_d60_propagation_fix
type: response
thread: D60-d31-round2-propagation-provenance
---

## D60 response 2/2 — substantive fixes pass; immutable pointer still stops one commit early

I independently accept the text, data, archive-byte, per-family
`archived_in_commit`, and containment-gate fixes in `f7a64be`. In particular,
the four G1 rows now name `947005c`, the six earlier rows retain `ba5e4a3`,
both manifest verification modes pass, and the false archive pin is rejected.

One narrow pointer residue prevents terminal verification. The appendix's
newest pin is still `947005c` (`tex/apendice.tex:23-30`), and it describes that
commit as holding the ten-row manifest. That historical manifest does exist,
but its four G1 rows still falsely name `ba5e4a3` as their archive commit:

- `git show 947005c:verification/replay_archive_manifest.json`, lines
  19, 36, 53, and 70.

The corrected ten-row manifest and the executable commit-containment gate
first appear in `f7a64be`, while S7 advertises those corrected properties
(`tex/apendice.tex:312-318`; `supplementary/SUPPLEMENTARY.md:280-283`).
Because `f7a64be` could not self-pin, closure needs one follow-up source commit
that adds `f7a64be` as the immutable locator for the corrected manifest and
gate (or equivalently narrows the current `947005c` claim). No scientific
number, archive byte, or result needs to change.
