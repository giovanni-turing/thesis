---
from: reviewer
ts: 2026-07-26T21:39:13-03:00
re: new
type: finding
thread: D17-grid-onset-mapping-residual
---

## Moderate provenance residue — the separately mapped grid artifact still exposes both superseded onset labels

The new caveat at `tex/apendice.tex:185-195` grammatically covers the riders
objects in that row. A separate appendix row maps the baseline grid to
`simulation/results/grid/grid_summary.json` without a caveat
(`tex/apendice.tex:172-178`). That mapped JSON still reports burst1 onset
`220 min` and burst6 onset `1 min`
(`grid_summary.json:9-14,65-69`), contradicting the authoritative 404/53
statistics.

Either correct/regenerate the historical metadata or add the same explicit
legacy-label caveat and authoritative pointer to the grid row. Otherwise a
reader following the appendix still reaches both rejected Finding-8 values.
