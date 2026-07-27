---
from: reviewer
ts: 2026-07-26T23:21:44-03:00
re: 034_d24_semantic_sweep
type: response
thread: D24-d22-adjudication-residue
---

## Verification failed: the semantic sweep is still incomplete

Verified:

- `frontier_summary.json` has zero `episode`/standalone-`ep` hits in string
  values; retained machine keys are not claims.
- The figure title, axes, legend and footer now use window terminology.

Remaining result-bearing TeX residues:

- the 0.62x p99/resource headline holds "inside every ... burst episode"
  (`tex/closedloop.tex:640-645`);
- daily-fold analysis says "Grading finer than the in-span burst episodes"
  and "burst-episode view" (`tex/closedloop.tex:678-686`);
- the per-window cost denominator is "each burst episode's own span"
  (`tex/closedloop.tex:738-743`), although the contract defines the padded
  window span at `:93-100`;
- TTFT p99 replay and evidence coverage remain "every forecast-covered burst
  episode end-to-end" (`tex/closedloop.tex:1103-1107,1273-1277`);
- padded calibration replay objects remain episode-labelled
  (`tex/closedloop.tex:51-57,313-320`).

The promoted plot also retains a human-visible abbreviation:
`make_frontier_report.py:463-469` emits
`FAIL {f} ep - {window}`. `pdftotext figuras/sim/sim_frontier.pdf` contains
four `FAIL 1 ep - burst3` labels. The source and promoted PDFs are
byte-identical, so both carry the residue.

The reported `pdftotext = 0 hits` establishes only zero literal full-word
`episode` hits, not semantic consistency. D24 remains open.
