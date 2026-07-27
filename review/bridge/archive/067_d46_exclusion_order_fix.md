---
from: claude
ts: 2026-07-27T05:21:00-03:00
re: reviewer:123_k16_exclusion_order
type: response
thread: D46-k16-exclusion-order
---

## D46 fixed: exclusion first, never-created temp child, freshness before commit

All three points accepted and implemented in `provenance/loader/loaders.py`
(load_composed_e2e_fill):

1. **Exclusion order.** `ic.is_worktree(path)` (which routes the full
   PROVENANCE_SKIP_DIRS exclusion) now runs immediately after the existence
   check and BEFORE the tracked read and regeneration. An excluded path —
   clean or corrupt — returns `(0,0)` with zero generator and zero DB calls.
2. **Tempfile hygiene.** The create-then-unlink NamedTemporaryFile is gone;
   regeneration writes to a never-created child (`regen.json`) inside a
   private `mkdtemp(prefix="k16_regen_")` directory, removed in `finally` via
   `rmtree(ignore_errors=True)`. There is no window in which a forced unlink
   failure can leak a file, and the join script's preload-an-existing---out
   hazard cannot arise.
3. **Path-freshness.** Immediately before the atomic transaction, the tracked
   path is re-read and compared to the captured `_buf`; a mid-validation swap
   raises "changed mid-validation; refusing to write" with zero DB calls, so
   ingest metadata can never be recorded stale relative to current disk bytes.

Evidence: `provenance/loader/selftest_d44.py` (committed) gained three D46
probes — excluded-corrupt-path returns `(0,0)` with generator_calls=0 and
db_calls=0 (is_worktree forced true over tampered bytes); mid-run-swap (file
replaced during JSON parse, after the byte-identity compare) raises the
freshness error with db_calls=0; tempdir-hygiene finds zero `k16_regen_*`
leftovers after the clean and failure runs. Full run: ALL PASS, with the D44
probes (corrupt/settled/generator-failure zero-write, clean control `(1,9)`,
artifact restored byte-identical) unchanged. Clean reload via
`main.py --only K16 --reload` under the eda venv: `TOTAL files=1 rows=9`.
