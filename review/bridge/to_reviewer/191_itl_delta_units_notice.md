---
from: claude
ts: 2026-07-28T19:40:00-03:00
re: new
type: question
---

# Change notice — tab:val-anchor forecast-ITL delta now dual-unit

Author question surfaced a presentational inconsistency: the live-vs-
offline table's delta column is percentages in every row except the
forecast ITL, which read "+1.8 ms" alone. Rationale was
percentage-on-small-base optics (9.7 ms base, 100 ms bound), but a
mixed-unit column can read as concealment. Fixed the honest way: the
cell now reads "$+18.6\%$ ($+1.8$\,ms)" — percentage first like its
neighbors, absolute retained for the operational context — and the prose
disclosure two paragraphs below is aligned from "18%" to "18.6%"
(1.8/9.7 = 18.56%, matching the column's (live-offline)/offline
convention). One cell + one numeral; build 111 pages 0 errors; gate OK.
Flag if you want it as a numbered round.
