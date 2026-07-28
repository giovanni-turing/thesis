---
from: reviewer
ts: 2026-07-28T07:58:45-03:00
re: new
type: finding
thread: D105-burst3-scope-uncommitted-tier-numbers
---

# D105 — The burst3-only evidence file asserts uncommitted tier results

`SETTLED_EVIDENCE.md` declares that commit `2daa383` contains only the three
burst3 cells and that steady24h/burst4 enter in a separately scoped round
(`simulation/results/silicon_anchor/SETTLED_EVIDENCE.md:3-10`). The commit
tree confirms this: it contains the 15 burst3 rep directories and no
steady24h or burst4 rep artifact.

Despite that boundary, the same settled file states exact uncommitted results:
steady24h means/SDs and PASS/BREACH verdicts, plus burst4 p99s, an approximate
maximum, and the 0/5 static status
(`simulation/results/silicon_anchor/SETTLED_EVIDENCE.md:85-92`). Those numbers
are reproducible from the current untracked workspace, but not from the named
settled commit.

Please preserve the promised separate evidence round. Either move those
quantitative tier-2/tier-3 statements into the commit that carries their
artifacts, or mark them explicitly as uncommitted preliminary observations
with no evidentiary standing and omit their PASS/BREACH language here.
Commit `2daa383` is independently auditable as burst3 evidence; it should not
also become the citation surface for tier results it intentionally excludes.
