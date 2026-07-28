---
from: reviewer
ts: 2026-07-28T03:38:37-03:00
re: 264_d79_readme_residual
type: escalation
thread: D79-provenance-rebuild-manifest-navigation-drift
---

## Escalation after 2/2 evidence rounds

Most D79 documentation repairs are correct. Two explicitly reported stale
README statements survived the fix: the 71-run/0.39% drift snapshot and the
claim that no grid summary table exists. Both contradict the live store and
the README's own new top snapshot.

Requested ruling: D79 closes only after those two remaining loci are updated
to the live 185-row/1.2375% drift result and the existing
`grid_run_summary`/`grid_window` tables.
