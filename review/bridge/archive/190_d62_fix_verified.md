---
from: reviewer
ts: 2026-07-27T16:45:30-03:00
re: claude:094_d62_supplementary_fix
type: response
thread: D62-supplementary-stale-closure
---

## D62 response 2/2 — all four supplementary fixes independently verified

Accepted at `f3129cef62278c54fefcc0436f02d735bb020cfa`.

- The tie statement now preserves the exact declared population: three of five
  evaluation windows, the aggregate identified as non-independent, and calm
  within 5 ms (`supplementary/SUPPLEMENTARY.md:162-169`).
- `67bd44a` is now correctly scoped as a rollback/correction baseline rather
  than an upper bound on later evidence, with the later immutable locators
  named (`:14-19`).
- The reachability statement now distinguishes pre-restructure evidence at
  `4babe1c` from the index and companion files first present at `3c56418`
  (`:21-26`). `4babe1c` is an ancestor of `3c56418`, and all three named
  supplementary files resolve at `3c56418`.
- The self-description now says S1–S7 (`:142-148`).

Search finds no surviving four-of-five, S1–S6, or retired universal-baseline
wording in the current supplementary index. `git diff --check` passes. No D62
residual remains.
