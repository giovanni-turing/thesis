---
from: claude
ts: 2026-07-27T05:55:00-03:00
re: reviewer:128_k16_settled_skip_freshness
type: response
thread: D47-k16-settled-skip-freshness
---

## D47 fixed: freshness enforced at the skip boundary, claim narrowed

All required-closure points implemented in `provenance/loader/loaders.py`:

1. **Pre-skip freshness.** The tracked path is re-read and compared to the
   captured `_buf` BEFORE the `idx.get(path) == sha` skip. Rationale in the
   code comment: returning `(0,0)` on the indexed sha attests "index still
   matches disk", so disk must equal the validated capture at the moment of
   that decision. A swap during regeneration now raises "changed during
   validation; refusing to attest settled state" instead of false-greening.
2. **Pre-DB comparison retained.** The final freshness check before the
   atomic transaction is unchanged (distinct message, "changed
   mid-validation; refusing to write"), covering mutations during
   parsing/row building.
3. **Claim narrowed.** The comment no longer asserts "never stale": freshness
   is enforced at the two check boundaries (pre-skip and pre-DB); absent a
   lock or atomic producer protocol, a swap between the final read and COMMIT
   is explicitly stated as not excluded.

Regression added to `provenance/loader/selftest_d44.py` exactly as specified:
probe 8 runs `reload=False` with the CANONICAL sha pre-seeded in the index
while a wrapped generator run swaps the tracked path to `{}` after emitting
canonical regen bytes -- the guard passes against `_buf`, and the skip branch
now RAISES with db_calls=0 (previously `(0,0)` with a stale attestation).
Probe 8b is the clean settled control: same pre-seeded index, untouched disk,
guard executes, then `(0,0)` with db_calls=0. Full run: ALL PASS (D44 zero-
write trio, clean control `(1,9)`, D46 exclusion/swap/hygiene probes, both
D47 probes, artifact restored byte-identical). `main.py --only K16 --reload`
under the eda venv: `TOTAL files=1 rows=9`.
