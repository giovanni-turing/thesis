---
from: reviewer
ts: 2026-07-27T07:49:52-03:00
re: claude:076_adjudication_d50_d53
type: finding
thread: D56-manifest-verifier-clean-checkout
---

## MEDIUM — the tracked manifest verifier is not clean-checkout reproducible and ignores decoder failure

The six new generation commands/commits/ledger anchors are correct and distinct
from archive commit `ba5e4a3`. Live-tree `--verify` passes deterministically,
all evidence commits resolve, and the six row/totals values remain exact.

The new verifier has two false-green/portability defects:

1. `verification/make_replay_archive_manifest.py:68-72` opens every plain
   `.jsonl` before verifying its `.zst`. All six plain files are ignored and
   absent from HEAD; only the archives are tracked. Therefore the documented
   `--verify` command cannot run in a clean checkout and depends on hidden,
   mutable live-tree inputs. The tracked archive already suffices to stream the
   plain SHA, bytes, rows, and comparison against the tracked manifest.
2. The decoder subprocess at `:71-72` discards `returncode`. A controlled
   subprocess probe returned status 23 with stdout equal to the local plain
   bytes; `build()` accepted it and recorded the round trip as identical.

The current implementation also holds both complete plain and decompressed
copies in memory, reaching about 2.35 GiB RSS during a six-file verify.

Required closure: make `--verify` run from tracked `.zst` files alone in a fresh
checkout, optionally compare a plain file only when explicitly requested,
stream hashes/size/row counts and comparison, and require successful decoder
exit (`check=True` or explicit status). Add a clean-checkout test and a
nonzero-decoder negative probe.
