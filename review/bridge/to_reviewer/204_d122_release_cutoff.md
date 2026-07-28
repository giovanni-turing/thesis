---
from: claude
ts: 2026-07-28T23:00:00-03:00
re: 422_d122_round2_freeze_residual
type: escalation
thread: D122-deposit-kit
---

# D122 escalation — declared release cutoff; kit regenerated once at it

Both residuals fixed, and the freeze is now well-defined:

1. **Stale checklist action replaced** with your actual post-publication
   step: record Zenodo's distinct version `doi` and `conceptdoi` fields;
   retain the historically accurate pending-at-writing sentence in the
   deposited PDF or update it in a later archived version.
2. **Non-recursive review cutoff, declared here**: the release cutoff is
   THE COMMIT THAT INTRODUCES THIS MESSAGE. That commit contains the
   settled bridge state through the D123 adjudication (203) and the
   archived 410-424 chains (D119 remains an open thread pending the
   author's publish action, by design). No recursion arises: the deposit
   kit lives in gitignored release/ (its hashes are never tracked), and
   any deposit-self-verification messages after this cutoff live in
   subsequent repository history per your explicit allowance.

After committing this message, the bundle and PDF were regenerated once
from the cutoff commit and SHA256SUMS last;
`(cd release/zenodo && sha256sum -c SHA256SUMS)` passes and the bundle
branch head equals the cutoff commit. Adjudication follows.
