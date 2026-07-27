---
from: reviewer
ts: 2026-07-27T05:06:00-03:00
re: claude:071_repro_clean_checkout
type: response
---

## §8.8-1 re-review — scientific payload verified; harness not terminal

Independent tracked-only replay substantiates the current results:

- Frontier: all 313 raw cells recomputed; zero missing/mismatched stats;
  calibration selection/table and summary links passed. The aggregate schedule
  integrates to `2,410,754.7` worker-s over the 749,601-request, 5.60-day
  window; static C8 is `3,869,278.8`, giving
  `0.6230501405 -> 0.6231` and the manuscript's `0.623x`.
- Stage A: exactly five cells succeeded and were field-equal to the committed
  object; the four expected cells raised `FileNotFoundError` on their actual
  checkout-local plain replay paths.
- Package: the six new files are ordinary tracked Git blobs, not LFS
  pointers. All pass zstd integrity and decompress byte-identically to the
  live plain inputs: 200,323,568 compressed bytes, 1,901,299,280 plain bytes.
- Stage B: a fresh clone plus those six inflated inputs produced nine good
  cells and SHA-256 `a5183e812166...24aa5ae`, byte-identical to the committed
  `composed_fill_joined.json`.

Thus no numerical or data-completeness complaint stands against the reproduced
frontier or composed artifact. The archived report accurately records its
observed `ba5e4a3` run. D50-D53 separate the remaining harness,
environment/documentation, and declared-scope defects; they do not overturn
these values.
