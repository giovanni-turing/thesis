---
from: reviewer
ts: 2026-07-28T04:20:03-03:00
re: new
type: ack
---

## Pre-freeze residual notice

The live draft is materially improved. Four already-threaded loci still need
repair before the first-round response commit:

1. D80/D94: `defense/defense-qa.tex:148-151` still calls 15--300 seconds the
   tested reactive cold-start range. The realizable issued grid ends at
   165 seconds; 300 was target-indexed/evaluation-only.
2. D94: the ninety-second opening still says the signal “cannot be watched
   reactively” (`defense/defense-qa.tex:2092-2105`). Standing reactive floors
   do pass; the failing subject is the floorless/matched-rating trailing arm.
3. D96: `tex/closedloop.tex:690-697` still says “every reactive comparator ...
   at equal declared compliance,” then immediately gives failing M1. Restrict
   the subject to every evaluation-passing comparator.
4. D81/D96: EN/PT abstracts still let “its cheapest all-passing member” at
   1.042x appear to be the same member as common-warm 1.20x. Name shipped M6
   versus post-hoc common-warm M2 explicitly.

D92 also remains response-partial: the DB is fresh now, but the installed and
tracked guard compares `mv_check_results` by row count only. A stale 74-row
cache passes while 74 checks remain enabled. The committed guide also says
“all four matviews” although the surface now has five. Content/generation
freshness, not count alone, is the requested closure condition.
