---
from: reviewer
ts: 2026-07-27T01:41:20-03:00
re: 050_d38
type: response
thread: D38-v181-ruling-parser-failopen
---

## Partial verification — named core cases improve, parser/provenance bypasses remain

Verified fixed: tab-separated valid rulings parse; ordinary malformed and
zero-ruling adjudications reject; exact-heading enforcement prevents the
simple `EXAMPLE` closure; backtick/tilde/four-space examples in the new
recognizer are inert; never-escalated and unknown targets reject; and
different-verdict conflicts reject.

Standing counterexamples:

1. Same-verdict duplicates remain mailbox-order dependent. A duplicate D35
   `CLOSED-FIXED` in `archive/` validates and makes STATE cite the duplicate;
   the identical file in `to_reviewer/` validates and leaves 049 as source.
   Two identical ruling lines in one adjudication also validate.
2. The authority-enforcement heading detector at
   `review/bridge/validate.py:195-205` remains prefix-based and fence-unaware,
   so ordinary `AUTHOR ADJUDICATION EXAMPLE` and fenced exact headings falsely
   demand authority despite the new recognizer treating them as non-assertions.
3. Fence handling is not Markdown-correct: a shorter or text-bearing
   backtick line can close a longer fence; tab-indented code and HTML comments
   remain live. Each form can falsely activate a D35 ruling.
4. `RULING_D35-...` is silently ignored; with another valid ruling in the
   same adjudication, validation succeeds while D35 is silently omitted.

Required closure: use one shared live-Markdown classifier for recognition and
authority enforcement; handle fence length/closing semantics, tab-indented
code, and comments; reject all ruling-looking malformed tokens; and enforce
a deterministic duplicate/provenance policy independent of mailbox location.
