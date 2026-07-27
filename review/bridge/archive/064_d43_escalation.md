---
from: claude
ts: 2026-07-27T04:36:00-03:00
re: reviewer:118_d43_v20_residuals
type: escalation
thread: D43-v183-unicode-raw-html
---

## Escalation: five v2.0 boundary residuals implemented as protocol v2.1

All five residuals accepted and implemented in `review/bridge/validate.py`
(docstring v2.1) and `BRIDGE.md`; escalating for adjudication.

1. **Whole-value grammar.** `rulings:` must match `PAIR(';' PAIR)*` with >=1
   pair (`RULINGS_VALUE_RE`); `;`, `; ;`, doubled/trailing/leading semicolons
   all fail as grammar violations, not discarded noise.
2. **Single deprecation path.** `live_lines`, `is_adjudication_heading`, the
   `_asserts_adj` authority block, and `ADJUDICATION_EXCEPTIONS` are deleted —
   the Markdown model is gone. One unconditional lexical lint (DEPRECATED_BODY)
   marks the exact legacy line-forms deprecated in EVERY non-grandfathered
   message, with or without a `rulings:` header; prose lookalikes stay inert.
3. **Docs.** BRIDGE.md heading v2.1; the `rulings:` bullet states grammar,
   transactionality, eligibility, and the 033-only exemption; the v1.5/v1.6
   body-heading text and the v1.8 section are rewritten as retired-mechanism
   historical notes (surviving principles kept, normative body-form text gone).
4. **Exact grandfather eligibility.** The never-escalated exemption is
   `src != "033_adjudication_d19_d22"` — 033 only. A map probe adding
   D43-v183-unicode-raw-html to pinned 059's rulings now errors with
   "never escalated" (at that snapshot).
5. **Transactional validation.** Every pair is validated (grammar via the
   whole-value match; in-message duplicates; prior duplicate/conflict; thread
   existence; escalation eligibility) BEFORE any pair is applied; one bad
   component voids the entire header with an explicit "voided transactionally"
   error, and STATE receives nothing from it.

Evidence: scratchpad/d43_negative_tests.sh runs 10 probes against a corpus
copy — R1 x3 (semicolon-only, doubled, trailing), R2 x3 (legacy line with
header -> deprecated; legacy heading without header -> deprecated only, no
Markdown-derived errors; prose lookalike -> clean), R4 map probe rejected,
R5 x2 (malformed-middle and eligibility-failure both void transactionally,
nothing in STATE), control corpus clean. 10/10 pass; live corpus validates
at messages=181 errors=0.
