---
from: claude
ts: 2026-07-28T06:05:00-03:00
re: 004_tex_overfull_hbox_bleed
type: response
thread: V04-tex-overfull-hbox-bleed
---

# V04 applied — 24 overfull hboxes reduced to 19; all four cited warnings gone

One attribution correction: three of the four cited paragraph overfulls live in
`tex/apendice.tex` (the artifact-ledger longtable's `\texttt` paths), not
`closedloop.tex`; the log's file nesting confirms it. The 37.75pt one is
`closedloop.tex` but is the running head of section 6.2 colliding with the page
number, not a float.

Fixes: `\allowbreak` after underscores in the three long `\texttt` paths
(`make_frontier_report.py`/`frontier_worktime_vs_worstp99`,
`make_metric_stack_figure`, `replay_archive_manifest.json`); for the running
head, `\section`'s own mark was suppressed for that one section so the
existing short `\sectionmark` becomes the page's first mark — the head now
reads "6.2. COMPARATORS: STATIC AND REACTIVE". ToC entry and heading text
byte-identical.

Residual: 19 warnings remain (8 apendice `\texttt` class 0.9–13.9pt, 3
related, 2 metodologia, 2 trace-eda, 1 closedloop inline-math 13.55pt, 3x
2.68pt output-routine) — same mechanical class, none page-bleeding at the
cited severity. Available for a second pass on request.

Build 0 errors / 0 undefined, 129 pages; `metric_stack_gate.py` OK.
