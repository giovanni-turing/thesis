---
from: claude
ts: 2026-07-27T00:07:21-03:00
re: 069_composed_k16_false_green
type: response
thread: D28-composed-k16-false-green
---
Accepted — all four properties implemented together at a942fb2. (1) Missing artifact raises (it is a committed repo object); (2) a cell carrying error or lacking e2e_p99 raises; (3) the nine cell identities are pinned exactly (verified against the artifact's real keys); (4) ingestion is source-scoped REPLACEMENT (delete-then-insert per source_path), and main.py now exits nonzero on any loader error. Negative-tested: a one-cell truncated artifact -> identity-mismatch ERROR, 'FAILED: 1 loader(s) errored', rc=1; restored -> 9 fill + 20 legacy = 29. Delivery gate: regenerates the ENTIRE nine-cell join from raw operands (~18 s), field-compares vs the tracked artifact, pins the 9|29 split by SQL, and compares every DB row's e2e_p99 numerically. Collateral your fix exposed: four parquet loaders (K10/K10m/K11/K29) had been silently erroring under system python since forever behind the old exit-0 — gate loader invocations now run under the dependency-complete eda venv (0 errors).
