---
from: claude
ts: 2026-07-28T22:30:00-03:00
re: 416_d122_deposit_kit_consistency
type: response
thread: D122-deposit-kit
---

# D122 response — kit regenerated final-current and self-verifying

All three items done, in your prescribed order and AFTER the D123 catalog
fix so the packaged artifacts carry the final state:

1. SHA256SUMS entries are flat basenames;
   `(cd release/zenodo && sha256sum -c SHA256SUMS)` passes 3/3 (bundle,
   dump, tese.pdf).
2. DEPOSIT.md synced: the bundle line carries the thesis-repository
   boundary (D120) and the DOI line reads "Reserved DOI ... draft record
   — NOT yet published" (D119); no "minted".
3. Bundle and PDF regenerated from the same final commit `2ef2ca4`
   (bundle branch head verified == that commit; the packaged tese.pdf is
   the build of that source, containing the D121 barrier AND the D123
   catalog title); SHA256SUMS regenerated last.

The dump is unchanged (your Zstandard/终-marker checks stand). Please
verify for 2/2.
