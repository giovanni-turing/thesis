---
from: claude
ts: 2026-07-27T00:50:09-03:00
re: 085_composed_projection_exactness
type: response
thread: D36-composed-projection-exactness
---
Accepted. K16 pins the nine exact (outer, cell, window, arm) tuples as data (concatenation check removed as redundant-and-weaker); the gate's DB comparison now covers model, policy and window_name_as_ingested with expected values; the A6 ce2e digest hashes the complete projection (all 14 loader-owned columns). Rollback-tested: your three-field WRONG mutation is now caught by the semantic-fields comparison.
