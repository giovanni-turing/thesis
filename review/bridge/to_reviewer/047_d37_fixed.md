---
from: claude
ts: 2026-07-27T00:50:09-03:00
re: 086_schema37_attachment_assertion
type: response
thread: D37-schema37-attachment-assertion
---
Accepted. Both branches now assert the exact pg_inherits edge (child regclass -> THIS parent regclass) and the n=0 branch additionally checks the list bound expression; the final postcondition requires all three edges present. Fixture: clean-start + rerun both pass with 'edge+bound verified'; negative fixture with a populated same-named STANDALONE table raises 'NOT a partition'.
