---
from: reviewer
ts: 2026-07-26T21:53:01-03:00
re: 025_d17_fixed
type: response
thread: D17-grid-onset-mapping-residual
---

## Verified

The separately mapped grid row now explicitly identifies the historical
220/1-minute labels as legacy metadata, points to the authoritative 404/53
values, and limits the unaffected scope to window spans and `$C^*$`
(`tex/apendice.tex:174-182`). The artifact values remain unchanged as
disclosed (`simulation/results/grid/grid_summary.json:9-15,65-69`), while
`analysis/trace_eda/i_burst_anatomy_stats.json:24-31,75-81` supplies 404/53.

D17 is closed on the current source.
