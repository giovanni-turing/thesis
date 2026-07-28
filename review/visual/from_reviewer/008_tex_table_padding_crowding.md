---
from: reviewer
ts: 2026-07-28T05:17:00-03:00
re: new
type: finding
thread: V08-tex-table-padding-crowding
---

## NIT: Compressed column spacing in Chapter 6 full-span summary tables

Rendered evidence:
- LaTeX source inspection of `tex/closedloop.tex`:
  - Table `tab:cl-metric-stack` (line 781): `\setlength{\tabcolsep}{4pt}`
  - Table `tab:cl-readiness` (line 814): `\setlength{\tabcolsep}{2.5pt}`
  - Table `tab:cl-ledger-enc` (line 1098): `\setlength{\tabcolsep}{3pt}`
  - Table `tab:cl-ledger-joint` (line 1223): `\setlength{\tabcolsep}{3pt}`
  - Table `tab:cl-llm-week-stack` (line 1381): `\setlength{\tabcolsep}{3.5pt}`

Defect analysis:
To squeeze 6--9 data columns into the standard 812 px text width, Chapter 6 tables reduce `\tabcolsep` down to 2.5--3.5 pt (compared to standard LaTeX default 6 pt). On rendered pages 86--94 (`tex/tese.pdf`), numbers in adjacent numerical columns sit tightly against vertical `\cmidrule` borders and column edges, creating visual crowding in dense multi-column tables.

Proposed fix:
For multi-column tables with text description columns (such as `tab:cl-readiness`), convert fixed text columns to wrapping `p{...}` or `X` columns with `\small` font to allow comfortable 4.5--6 pt column spacing.
