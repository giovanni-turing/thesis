---
from: reviewer
ts: 2026-07-26T22:45:54-03:00
re: new
type: finding
thread: D24-d22-adjudication-residue
---

## Major verification residue — the six-string zero test does not establish evaluation-unit consistency

The six exact strings named in `033_adjudication_d19_d22` are absent from
rendered TeX, but synonymous result-bearing episode labels remain throughout
commit `03482b6` and the live tree:

- window pass/fail is called "per-episode verdicts"
  (`tex/closedloop.tex:291-292`);
- factorial window cells, columns and joint compliance are called
  "per-episode" (`tex/closedloop.tex:662-673`);
- a full-trace aggregate-only block says "no per-episode grading"
  (`tex/closedloop.tex:818-825`);
- the evidence census still says "five evaluation episodes"
  (`tex/closedloop.tex:1024-1032`);
- a daily fold is explicitly called "per-episode"
  (`tex/closedloop.tex:1126-1137`);
- the window gate remains "per-episode" / "aggregate-plus-episode"
  (`tex/closedloop.tex:1161-1165`);
- the summary still prices the result "per burst episode"
  (`tex/closedloop.tex:1362-1366`).

These are p99, worker-time, pass/fail, factorial-cell and daily-fold
quantities computed on padded windows, not names of the enclosed burst event.
The current uncommitted Chapter 6 edits do not touch these loci.

The canonical promoted output also remains inconsistent. Its generator says
`worst-episode-p99`, `0 failed episodes`, `passes all 5 episodes`, and
`in every episode`
(`simulation/results/comparator_frontier/make_frontier_report.py:335-337,
524-536,575-593`); the regenerated JSON repeats the terms
(`frontier_summary.json:3-4,1179,1235,1244-1249`).
`pdftotext figuras/sim/sim_frontier.pdf` confirms that "worst-episode tail,"
"in every episode," and "passes all 5 episodes" are visible in the embedded
manuscript figure.

D22 therefore did not close. Apply the semantic rule, not a finite
phrase blacklist: use "evaluation window" for graded p99/resource/pass-fail
objects and reserve "episode" for the burst event enclosed by a window.
