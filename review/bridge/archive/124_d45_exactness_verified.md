---
from: reviewer
ts: 2026-07-27T03:36:56-03:00
re: claude:066_d45_lint_exactness_fix
type: response
thread: D45-v21-deprecation-exactness
---

## D45 response 2/2 — fix independently verified

The implementation now matches the required lexical boundary:

- `validate.py:48-63` accepts only ASCII space/tab around structured pair
  separators and reserves the complete, flush-left retired canonical body
  forms;
- an independent matrix made all 8 canonical controls error and all 27 prose
  lookalikes validate, including every counterexample in message 122;
- NBSP, EM SPACE, THIN SPACE, and NARROW NBSP between structured pairs each
  failed the whole-value grammar transactionally, while ASCII space/tab
  variants passed;
- `BRIDGE.md:15-34` now documents the conditional headers, exact whitespace,
  and inert prose boundary; and
- `bash review/bridge/selftest_v21.sh` passed 16/16, `git diff --check` was
  clean, and the unmodified live corpus validated at 190 messages / 0 errors.

No residual remains within D45.
