---
from: reviewer
ts: 2026-07-28T17:57:10-03:00
re: 197_d120_bundle_scope_narrowed
type: response
thread: D120-bundle-scope
---

# D120 round 2 — repository boundary now correct

Verified at `f10304c`.

- `tex/apendice.tex:350-353` now limits bundle resolution to cited
  thesis-repository evidence commits and explicitly routes external hashes to
  their own repositories.
- `REPRODUCIBILITY.md:78-80` states the same boundary.
- `git bundle verify release/zenodo/thesis-full-history.bundle` succeeds; its
  recorded HEAD is `f10304c`.
- All ten rendered thesis-repository commit pins are ancestors of that bundled
  HEAD.  The two rendered AIC commits remain external exactly as disclosed.

No counterclaim remains on D120.  The narrower wording is rigorous and avoids
unnecessary archive expansion.
