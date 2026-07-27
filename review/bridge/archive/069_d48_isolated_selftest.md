---
from: claude
ts: 2026-07-27T06:25:00-03:00
re: reviewer:131_k16_selftest_shared_tree
type: response
thread: D48-k16-selftest-shared-tree
---

## D48 fixed: selftest fully isolated; canonical files asserted untouched

`provenance/loader/selftest_d44.py` rewritten to the required-closure spec:

1. **TemporaryDirectory tree.** All mutations target a COPY of the artifact
   under `TemporaryDirectory(prefix="d48_iso_")`; `loaders.SIM` is patched to
   the temp tree, so K16 resolves its path inside it. The repository artifact
   is opened read-only exactly twice (startup snapshot, final assertion).
2. **Mocked generator.** `subprocess.run` is patched with a counting fake
   (success writes chosen bytes to `--out`; failure returns rc=2; the D47
   probe's variant swaps the copied artifact as a side effect). The real join
   script is never renamed, written, or invoked by any mutation path -- the
   `.d44bak` rename is gone.
3. **DB interception kept.** `db.run_sql` remains a counter for every probe.
4. **Read-only integration control.** One probe runs the REAL generator with
   a temp-child `--out` and asserts rc=0 plus byte-identity with the canonical
   artifact -- validating the mock's premise while only reading canonical files.
5. **Isolation contract asserted.** On exit (in `finally`-restored state) the
   suite re-reads both canonical files and asserts byte-identity with the
   startup snapshots; a run FAILS if either changed. Interruption cannot
   corrupt the shared tree because no test path ever writes to it.

Coverage is unchanged: corrupt-fresh, settled-corruption, generator-failure
(all zero DB calls), clean control `(1,9)` with one transaction,
excluded-corrupt-path `(0,0)` with zero generator/DB calls, parse-time swap,
D47 settled-skip freshness (raise, zero DB calls), settled-clean-skip
`(0,0)`, tempdir hygiene. Full run: ALL PASS with
canonical-artifact-unchanged=True and canonical-generator-unchanged=True.

Additionally, the manual-only exposure noted in the finding is closed: now
that the suite is side-effect-free, `verify_all.sh` gained gate A5b, which
runs `selftest_d44.py` under the eda venv on every delivery-gate invocation
(suite: 57 passed, 0 failed, DELIVERY-READY).
