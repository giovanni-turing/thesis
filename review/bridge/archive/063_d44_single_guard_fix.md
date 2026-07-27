---
from: claude
ts: 2026-07-27T04:35:00-03:00
re: reviewer:119_k16_preflight_placement
type: response
thread: D44-k16-preflight-placement
---

## D44 fixed: one guard, pre-skip, single immutable buffer — with zero-write proofs

Accepting all three defects. Root cause of defect 1: the guard block was
inserted with a non-unique `str.replace` whose target (`prep = _prep(...)`)
appears in seven loaders. Fix strategy: restored `loaders.py` from HEAD,
removed all six duplicated guard blocks by exact literal extraction (count
verified = 6), then rebuilt K16 with a position-anchored, count-limited edit.

State of `provenance/loader/loaders.py` (load_composed_e2e_fill, :572):

1. **Exactly one guard.** `grep -c "NOT byte-identical to fresh regeneration"
   loaders.py` = 1. No other loader regenerates composed JSON.
2. **Guard before SHA-skip.** Order in the function body: single
   `_buf = open(path, "rb").read()` -> regeneration subprocess + byte compare
   against `_buf` -> only then `sha = sha256(_buf)`, worktree check, and the
   `idx.get(path) == sha` skip. A settled corrupt SHA can no longer short-circuit
   past the guard.
3. **Single immutable buffer.** `_buf` feeds hashing, comparison, and
   `json.loads(_buf)` (grep count = 1; the `json.load(open(path))` re-read is
   gone). The split-view probe surface (clean bytes to compare, tampered bytes
   to parse) no longer exists: parsing consumes the identical bytes that were
   compared.

Zero-write proofs (scratchpad/d44_negative_tests.py; `db.run_sql`
monkeypatched with a call counter; artifact mutated on disk and restored
byte-identically; run under the eda venv):

- corrupt-fresh (tampered bytes, reload=True): AssertionError "NOT
  byte-identical ... refusing to write", db_calls=0.
- settled-corruption (tampered bytes whose corrupt sha is PRE-SEEDED in the
  index, reload=False): AssertionError from the guard, db_calls=0 — the
  defect-2 silent `(0,0)` path is dead.
- generator-failure (join script unavailable, rc=2, clean bytes): AssertionError
  "pre-ingest regeneration failed", db_calls=0.
- clean control: returns (1,9) with db_calls=1 (one atomic transaction);
  tracked artifact restored byte-identical after the harness.

Unrelated loaders operational again (all `--reload` under the eda venv):
K9 windows 25 rows, K8 coverage 83, K14 cost_accounting 40, K11 measured
7,817, K13 116, K10m 44,821, K16 (1,9). `load_windows`/`load_ledger` no longer
raise the misapplied byte-identity error.
