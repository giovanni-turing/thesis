---
from: claude
ts: 2026-07-28T06:09:00-03:00
re: 008_tex_table_padding_crowding
type: response
thread: V08-tex-table-padding-crowding
---

# V08 applied — both tables at 4pt tabcolsep, no new overfulls

`tab:cl-readiness` 2.5→4pt and `tab:cl-llm-week-stack` 3.5→4pt. Neither
produces an overfull warning; rendered pages sit inside the text block. The
readiness table's last column was already `p{3.3cm}` (no conversion needed);
`tab:cl-metric-stack` was already 4pt. The ledger tables at 3pt
(`tab:cl-ledger-enc`/`-joint`) were outside the finding's scope and are
unchanged — flag them separately if you want them swept.
