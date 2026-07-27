---
from: reviewer
ts: 2026-07-27T03:25:54-03:00
re: new
type: finding
thread: D46-k16-exclusion-order
---

## MEDIUM — K16 validates before honoring active-worktree exclusion

`ic.is_worktree(path)` now runs only after the tracked read, approximately
18-second regeneration, and comparison
(`provenance/loader/loaders.py:597-613`). A clean excluded path invokes the
generator before returning `(0,0)`; a corrupt excluded path raises instead
of skipping. This defeats `PROVENANCE_SKIP_DIRS`' documented purpose for
half-written active artifacts.

Adjacent hardening:

- if the path changes after `_buf` capture while regeneration matches the
  captured buffer, K16 writes internally consistent captured rows/SHA but
  leaves ingest metadata temporarily stale relative to the current path;
- the initial tempfile unlink is outside `try`, so a forced unlink failure
  leaves the created temp file behind (zero generator/DB calls).

Required closure: honor worktree/SKIP_DIRS immediately after existence and
before reading or regenerating. Prefer a temporary directory with a
never-created child output; add an explicit path-freshness policy/check before
commit if single-call disk/ingest synchronization is required.
