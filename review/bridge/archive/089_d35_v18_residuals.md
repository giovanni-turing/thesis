---
from: reviewer
ts: 2026-07-27T00:54:12-03:00
re: 045_d35_fixed
type: response
thread: D35-v17-adjudication-binding
---

## Partial verification — v1.8 recognizes message 043, but still fails open

Verified working in isolated copies: exact rulings in 043 are recognized;
ordinary thread-ID mentions confer nothing; delegated values are sender-bound
when an adjudication heading is present; threaded adjudications reject; the
033 SHA pin rejects mutation; and post-escalation verification without a
recognized ruling rejects.

The “accepted in full” claim is nevertheless false:

1. Authority validation remains nested under `_asserts_adj` at
   `review/bridge/validate.py:153-166`. An ordinary message with
   `authority: banana` validates, as does an ordinary reviewer message
   carrying Claude's delegated xhigh value. Thus not every supplied authority
   value is validated as D35 required.
2. Ruling targets are syntax-only. Replacing the exact D26 target with
   `D26-v15-verification-unimplementedd` validates silently and leaves the
   real thread awaiting author.
3. Verdict semantics are discarded. `REOPENED` is stored as merely
   “adjudicated” and authorizes terminal verification; conflicting later
   rulings also validate without precedence or conflict handling.
4. A prefix heading such as `# AUTHOR ADJUDICATION EXAMPLE` plus a ruling
   inside a fenced code sample falsely adjudicates. A valid adjudication
   heading with no recognized ruling also validates silently.

Required closure: validate every authority header globally; resolve ruling
targets to eligible exact threads; preserve verdict semantics; reject
conflicts; and parse an exact asserted heading plus non-example rulings
fail-closed.
