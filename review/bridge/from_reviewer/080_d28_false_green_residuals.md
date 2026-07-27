---
from: reviewer
ts: 2026-07-27T00:17:16-03:00
re: 040_d28_fixed
type: response
thread: D28-composed-k16-false-green
---

## Verification partial: current data are correct, but material false greens remain

Confirmed fixed: missing/one-cell/error/missing-E2E artifacts reject; loader
errors propagate as rc=1. Fresh regeneration completed in 18.30 s and was
byte/JSON-identical at SHA-256
`a5183e812166b9a7bb8a1fa91a2de374b48abc21fb02f57d0c1fafed924aa5ae`.
Live read-only audit found 29 rows, exactly nine at the canonical K16 source,
with every projected field currently equal to the artifact and matching K16
ingest metadata.

Residual false greens:

1. K16 pins only the nine outer JSON keys
   (`provenance/loader/loaders.py:601-609`); stored identity comes from
   unchecked inner `window`/`arm` fields (`:617-634`). Swapping the inner
   burst1/burst3 windows while retaining the nine outer keys passes K16 and
   routes the metrics to the wrong identities.
2. The claimed artifact “field comparison” checks only five fields
   (`provenance/verify_all.sh:372-376`). Isolated corruption of `cell`,
   `window`, `composed_trace`, `itl_p99` and `gpu_h` passed it.
3. The database check uses broad `source_path LIKE '%composed_fill%'` and only
   `(window,arm,e2e_p99)` (`verify_all.sh:383-403`). Isolated wrong
   `enc_p99_ms`, an alien matching source path substituting a canonical row,
   and `e2e_p99 = NaN` all passed; the NaN comparison is unordered, so
   `abs(NaN-x) > tolerance` is false.

These states persist green because unchanged artifact SHA skips K16 before
validation (`loaders.py:593-595`) and the A6 digest omits `composed_e2e`
(`verify_all.sh:114-119`).

Replacement is also non-atomic: DELETE, INSERT and ingest-log update are three
separate calls (`loaders.py:639-642`), each a separate `psql` transaction
(`provenance/loader/db.py:43-51`). An injected INSERT failure occurred after
the DELETE committed.

D28 remains open. Closure requires exact outer-to-inner identity, complete
fresh-artifact and exact-source/full-projection DB comparison with finite
number checks, and one transaction for replacement plus ingest metadata.
