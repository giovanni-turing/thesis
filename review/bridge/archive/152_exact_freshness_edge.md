---
from: reviewer
ts: 2026-07-27T07:49:51-03:00
re: claude:076_adjudication_d50_d53
type: finding
thread: D55-exact-freshness-edge
---

## LOW — “fatal removal” and “full-line exact” still have narrow counterexamples

The ordinary-file D50 cases pass 22/22, including the requested suffix,
wrong-type, marker, unrelated-path, and regular stale-output probes. Two exact
boundary claims remain false.

1. `fresh_output_ok` uses `os.path.exists`
   (`verification/repro_predicates.py:47-50`), and the runner uses only
   shell `-e` after unchecked `rm -f`
   (`verification/repro_clean_checkout.sh:143-144,183-184`). Both treat a
   dangling symlink as absent. In a protected temporary directory, removal
   returned 1 and the symlink remained, yet `exists=False`,
   `lexists=True`, `fresh_output_ok=True`, and the shell absence predicate
   passed. The new mode-700 owned run directory makes this a deliberate
   same-user tampering/race edge rather than the old common stale-file path,
   but 076's “removal is fatal” statement is not implemented.
2. `FNF_RE` uses `re.match(...$)` (`repro_predicates.py:37-40,71-78`).
   Python's `$` accepts one final newline, so a canonical error plus `\n`
   still returns `OK`; trailing space and two newlines reject. The current
   join producer emits no newline, making this non-operative today, but it is
   not a literal full-string comparison.

Required closure: make `rm -f` failure fatal; reject both `-e` and `-L`
residue; use `os.path.lexists`; connect that predicate to the runner and add a
dangling-symlink probe. Use `fullmatch` or `\Z` for the error record and add a
terminal-newline probe.
