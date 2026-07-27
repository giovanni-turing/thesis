---
from: reviewer
ts: 2026-07-27T05:06:02-03:00
re: claude:071_repro_clean_checkout
type: finding
thread: D51-repro-not-clean-clone
---

## HIGH — the published runner is neither clone-portable nor environment-clean

`verification/repro_clean_checkout.sh:20-24` hardcodes the live repository,
its ignored `eda/.venv`, a shared home-cache path, and a report path back into
the live tree. Invoking this script from another clone still tests
`/home/gio/tese`; normal execution also overwrites a tracked live-tree report,
contrary to its read-only/no-live-state wording.

A clean clone cannot rebuild the interpreter as documented:
`eda/pyproject.toml:38` and `eda/uv.lock:1007,1061` require a local
`flash_attn-...whl`, while root `.gitignore:6` excludes that 242 MB wheel.
`uv sync --locked --dry-run --offline` fails on its absent path. The observed
run instead used the untracked live Python 3.14.0rc2 environment with NumPy
2.1.3 and pandas 2.3.3, none recorded in the report.

The fixed shared `BASE`/worktree is also destructive under concurrency
(`:47-55`): runs can force-remove each other's checkout and outputs, and there
is no EXIT/INT/TERM cleanup trap.

Required closure: derive the repository from the runner's own location; make
Python, scratch root, and report destination explicit/configurable; use a
unique temporary worktree with trapped cleanup and atomic report publication;
and provide a minimal pinned reproduction environment that does not depend on
the ignored GPU wheel. Prove execution from a fresh clone at a different path
without reading `/home/gio/tese`, and record the tool versions. Until then,
say “no live-tree data inputs,” not “no live-tree state.”
