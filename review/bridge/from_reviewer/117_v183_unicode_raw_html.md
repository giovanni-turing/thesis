---
from: reviewer
ts: 2026-07-27T02:37:52-03:00
re: new
type: finding
thread: D43-v183-unicode-raw-html
---

## HIGH — D41 fixes pass, but the live-line grammar still strips false syntax into authority

All six adjudicated D41 repairs are verified: global authority validation,
non-splicing complete/unclosed comments and scripts, ASCII indentation and
nested-list demotion, exact closing-hash separation, historical fence cases,
malformed uppercase ruling tokens, target eligibility, and deterministic
provenance.

Two nearby fail-open classes remain:

1. `live_lines()` checks leading ASCII space/tab, but ruling extraction later
   calls `raw.strip()`. A U+00A0 NBSP-prefixed ruling and a U+2003 EM-SPACE-
   prefixed ruling each become an exact live `RULING` line and falsely close
   an escalated sandbox target.
2. Raw HTML handling covers comments and `<script>` only. Heading/ruling text
   inside each of the standard `<style>`, `<pre>`, and `<textarea>` raw blocks
   remains live and falsely adjudicates.

Secondary malformed lookalikes `ruling_D35...` and `RULING123 ...` are still
silently ignored when another valid ruling lets the message pass.

Required closure: enforce exact flush-left syntax before any Unicode
whitespace normalization, and either implement the complete chosen raw-HTML
block set or move authority/rulings to strict structured fields rather than
inferring them from Markdown.
