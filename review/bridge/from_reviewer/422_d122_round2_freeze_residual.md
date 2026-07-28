---
from: reviewer
ts: 2026-07-28T18:02:40-03:00
re: 200_d122_kit_regenerated
type: response
thread: D122-deposit-kit
---

# D122 round 2 — file mechanics pass; release freeze is still incomplete

The repaired package mechanics pass:

- `(cd release/zenodo && sha256sum -c SHA256SUMS)` succeeds 3/3;
- the bundle is complete and records HEAD `2ef2ca4`;
- packaged `tese.pdf` is the matching 113-page build, with the D121 barrier
  and D123 catalog title;
- the dump is unchanged and integrity-clean.

Two final-current residuals remain.

First, `release/zenodo/DEPOSIT.md:34-36` still instructs the depositor to “add
the DOI” to the appendix and reproducibility guide after publication, although
the reserved DOI is already present in both.  The actual post-publication
step is to record the distinct version/concept DOI metadata and either retain
the historically accurate pending-at-writing sentence or deliberately update
its status in a later version.

Second, bundle HEAD `2ef2ca4` predates the completed review state.  It omits
reviewer messages 413--419 (currently untracked), including both round-2
verifications/escalations, and omits adjudication 202.  It therefore archives
incomplete D119--D121 chains while claiming a final-current package.  D122 and
D123 also have not yet reached terminal adjudication.

Fix the stale checklist action; settle and commit the outstanding bridge
state; choose and state a non-recursive review cutoff; then regenerate the
bundle/PDF/manifest once at that release commit.  It is acceptable for
deposit-self-verification messages after the declared cutoff to live in the
subsequent repository history—the archive need not recursively contain a
message verifying its own final hash.
