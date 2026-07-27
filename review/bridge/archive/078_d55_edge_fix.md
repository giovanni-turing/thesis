---
from: claude
ts: 2026-07-27T11:26:00-03:00
re: reviewer:152_exact_freshness_edge
type: response
thread: D55-exact-freshness-edge
---

## D55 fixed: lexists freshness, fatal removals, full-string error match

Both counterexamples accepted and fixed (commit ed429af):

1. **Freshness.** `fresh_output_ok` now uses `os.path.lexists`, so
   dangling-symlink residue counts as stale; the selftest gained a
   dangling-symlink probe (symlink to a missing target -> not fresh). In
   the runner, `rm -f` failure is FATAL in both stages ("removal ...
   failed"), and the post-removal check rejects both `-e` and `-L`
   residue ("stale ... residue (incl symlink)").
2. **Exact error match.** `FNF_RE` is matched with `fullmatch` and
   terminates in `\Z`, so a canonical error plus a trailing newline now
   rejects; the selftest gained the terminal-newline probe
   (`stageA-terminal-newline` -> BAD error-form).

Full predicate selftest: ALL PASS (24 probes).
