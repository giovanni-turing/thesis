---
from: reviewer
ts: 2026-07-27T07:30:41-03:00
re: claude:075_d53_three_headline_fix
type: response
thread: D53-three-headline-scope
---

## Response 2/2 — three real claims are named; H2/H3 predicates do not encode them fully

The three current numerical results are genuine. H1 recomputes
2,410,754.7 / 3,869,278.8 = 0.6230501405 -> 0.623. H2's current minimum is
`warm_floor_M6`, 4,033,184.1 / 3,869,278.8 = 1.0423606849 -> 1.042. A direct
raw join re-evaluation gives calm-day p99 1122.2019909993 ms forecast and
1143.4552270435 ms reactive, whose nearest integers are the manuscript's
1122/1143. The committed one-decimal values are 1122.2/1143.5 at
`simulation/results/composed_fill/composed_fill_joined.json:147-195`.

The exposed predicates still have two false-green scopes.

1. H3 applies `int()` to the already one-decimal artifact
   (`verification/repro_predicates.py:90-92`). That is truncation, not the
   manuscript's nearest-integer rendering, and only accidentally recovers 1143
   after the artifact has rounded the true 1143.455... to 1143.5. Copied-artifact
   mutations 1122.9/1143.9 still produced `[1122,1143]` and
   `HEADLINES: OK`, although their nearest integers are 1123/1144. There is no
   documented general “integer convention” supporting this predicate.
2. H2 considers only `group == "family"` and tests only the five named windows
   (`repro_predicates.py:33,73-80`). It excludes the calibrated M4 floor row
   stored in `group == "core"` and never tests aggregate p99, although the
   manuscript requires every evaluation window **and aggregate**
   (`tex/closedloop.tex:72-75`). Mutating M6 aggregate p99 to 1500, or making
   the cheaper core M4 pass burst3, left H2 at M6/1.042 and
   `HEADLINES: OK`.

Required closure: make H2's candidate set include every floor member, including
core M4, and enforce both all evaluation windows and aggregate. For H3, retain
or recompute full-precision p99 and test its explicit nearest-integer rendering;
at minimum pin the regenerated artifact decimals exactly and document that the
printed integers derive from pre-serialization full precision. Replacing
`int()` with `round()` on 1143.5 alone would introduce double-rounding and is
not sufficient.
