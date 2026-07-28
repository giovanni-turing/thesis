---
from: reviewer
ts: 2026-07-28T00:18:27-03:00
re: new
type: finding
thread: D69-d68-semantic-gate-residual
---

## D69 — D68 wording/data pass; semantic gate still false-greens

Independent snapshot hashes:

- `tex/closedloop.tex` `ef556bbb...`;
- `tex/conclusion.tex` `0f45ed41...`;
- `defense/reveal/index.html` `c595e13a...`;
- `defense/deck_single.html` `61cbf729...`; and
- `verification/metric_stack_gate.py` `93b719b9...`.

The live scientific scopes now separate the frontier strict-rewarm population
from the 60-cell strict factorial; integer-bound/readiness qualifiers are
present; the abstract, deck headings, a12 captions, and campaign glosses are
fixed; provenance and all underlying numbers pass. Clean binding and the
built-in selftest both report success.

### One display-precision correction

`tex/closedloop.tex:847-850` prints `733.0 ms` and immediately says the strict
`p99 < B` pass survives down to `733 ms`. At displayed precision this reads as
`733.0 < 733`, which is false. Print the exact `732.999 ms; lowest passing
integer-ms bound 733 ms`, or explicitly mark `approximately 733.0 ms` before
the integer-bound statement. Keep the separate factorial
`733.643 ms -> 734 ms` scope.

### Reproduced gate false-greens

Independent temporary-clone mutations still return gate success for:

- chapter crossing `808 -> 809`;
- chapter crossing `907 -> 908`;
- chapter role `frontier strict -> factorial strict`;
- conclusion `682`, its warm-pool qualifier, or `733` changed independently;
- deck `682`, `808`, or `907` changed independently; and
- deck warm-pool/static/strict-rewarm role qualifiers changed independently.

The cause is visible in the live gate:

- `verification/metric_stack_gate.py:279-316` derives the right values and
  binds some chapter phrases, but not all crossings/roles;
- the binder input list at `:70` does not read either deck; and
- the selftest probe list at `:432-511` contains no D68 mutation probes.

Bind all promoted chapter, conclusion, and both deck-mirror claims to their
artifact-derived roles, and add independent probes for each failure class.
The gate should verify that the two deck mirrors agree as well as that each
agrees with evidence.

This is the sole standing blocker found in the post-226 state. It requires no
new experiment and no change to the favorable scientific result.
