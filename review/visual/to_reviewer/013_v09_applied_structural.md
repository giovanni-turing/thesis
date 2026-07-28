---
from: claude
ts: 2026-07-28T06:10:00-03:00
re: 009_qa_toc_straggler_page8
type: response
thread: V09-qa-toc-straggler-page8
---

# V09 applied — structural fix: TOC now terminates with \clearpage

Your two-line-nudge fix was superseded before it could land: a concurrent QA
reinforcement pass grew the crib 121→132 questions, and the TOC spill onto
page 8 grew from 2 lines to ~28. The nudge class of fix breaks every time the
crib grows, so the applied fix is structural: `\clearpage` after
`\tableofcontents`. Verified on the rebuilt PDF (61 pages, 0 errors): page 8
ends with the final TOC entry, Section 2 opens at the top of page 9 with no
straggler. This holds under any future TOC length.
