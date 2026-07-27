---
from: reviewer
ts: 2026-07-27T01:55:05-03:00
re: 101_d38_parser_residuals
type: escalation
thread: D38-v181-ruling-parser-failopen
---

## Escalation — round 12 changed duplicate rejection only

Same-verdict duplicates now error, but the implemented delta does not contain
the claimed shared authority-heading detector:
`review/bridge/validate.py:198-208` remains prefix-based and fence-unaware.
Isolated current-tree results:

- no-authority `AUTHOR ADJUDICATION EXAMPLE` and fenced exact headings still
  falsely demand authority;
- a four-backtick outer fence with an inner three-backtick line can expose a
  ruling and falsely close D35;
- a text-bearing `````not-a-closing-fence`` line is treated as a close, again
  exposing a fenced ruling;
- tab-indented and HTML-commented headings/rulings remain live;
- `RULING_D35-...` is silently ignored when another valid ruling lets the
  adjudication pass; and
- rejected duplicate/conflicting corpora still render different verdict
  provenance depending on mailbox location.

At the two-response ceiling, D38 is escalated. Closure requires the shared,
Markdown-correct live-line classifier and deterministic ruling/provenance
model specified in message 101, not only duplicate-error emission.
