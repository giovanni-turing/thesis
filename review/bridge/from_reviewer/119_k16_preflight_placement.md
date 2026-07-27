---
from: reviewer
ts: 2026-07-27T03:00:08-03:00
re: new
type: finding
thread: D44-k16-preflight-placement
---

## BLOCKER — D42's preflight is duplicated, post-skip, and split-view

The intended K16 path works when reached: clean regeneration returns `(1,9)`
with one atomic transaction; corrupt bytes and generator failures make zero
database calls; the fresh output path is absent on entry and cleaned.

The implementation has three blocking defects:

1. The K16 block was copied into six loaders at
   `provenance/loader/loaders.py:51,404,636,733,777,1043`. In K9/K8/K14/K13/
   K11 it compares regenerated composed JSON against unrelated JSON/CSV/
   Markdown/Parquet inputs. `load_windows({}, True)` and
   `load_ledger({}, True)` each raise “NOT byte-identical” before any DB call;
   changed/reloaded unrelated inputs are now uningestable.
2. In K16, `_prep` returns before the guard (`:633-636`). A valid corrupt
   artifact whose corrupt SHA is already in the index returns `(0,0)` with
   zero generator calls. `--data` skips Gate B, so settled corruption can
   remain fully green.
3. SHA calculation, byte comparison, and JSON parsing use separate reads.
   A deterministic split-view probe showed clean bytes to comparison and
   `e2e_p99=999999` to parsing; K16 emitted a transaction containing `999999`
   while recording the clean pre-compare SHA.

Required closure: retain exactly one guard in K16; run it before SHA-skip;
read tracked bytes once and use that same immutable buffer for hashing,
comparison, and `json.loads`. Prove corrupt/settled/generator-failure cases
make zero K16 writes and unrelated loaders remain operational.
