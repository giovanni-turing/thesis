---
from: reviewer
ts: 2026-07-27T16:16:44-03:00
re: new
type: finding
thread: D60-d31-round2-propagation-provenance
---

## HIGH — D31's adjudicated patch leaves two prose contradictions and false archive provenance

Commit `947005c` fixes the view/table scope and most propagated synthesis, but
I cannot terminally verify D31 because four current-tree residues remain.

### 1. One promoted tie claim was missed

The chapter opening still says “on four of the five composed windows forecast
and reactive tail latencies tie exactly” (`tex/closedloop.tex:29-31`).
The declared population is five evaluation windows plus a non-independent
aggregate view (`:41-50`), and the corrected result elsewhere is three of
five (burst1/4/5) plus aggregate, calm within 5 ms.

### 2. The calm pass is immediately contradicted

The language synthesis correctly adds that calm reactive passes TTFT at
494.3 ms (`tex/closedloop.tex:1269-1272`), then says reactive is cheap because
it “fails the tail on every window” (`:1273-1277`). Calm reactive is also
cheaper than calm forecast (48.22 vs 106 GPU-h), so the universal causal
sentence remains false; it must be scoped to the five a12 aggregate/burst
rows or to the failing bursts.

### 3. The four new archive rows carry a false commit

`verification/make_replay_archive_manifest.py:149` hardcodes
`archived_in_commit = ba5e4a3` for **every** file. Consequently the four new
G1 rows repeat that value
(`verification/replay_archive_manifest.json:19,36,53,70`), but:

```text
$ git cat-file -e ba5e4a3:defense/anim/data/g1_runs/burst2_enc_static_C8.jsonl.zst
fatal: path ... does not exist in 'ba5e4a3'
$ git log --diff-filter=A --format='%h %s' -- <that path>
947005c D30/D31 round 2: view derivation, archived g1 halves, precise tie population
```

The same absence/addition result holds for all four G1 archives.
`make_replay_archive_manifest.py --verify --with-plain` returns OK, but only
because the verifier regenerates the same false hardcoded string; it verifies
bytes/rows, not the claimed Git object.

### 4. The “complete” pointer layer still cannot locate the new evidence

The appendix still pins only through `c6349c8`
(`tex/apendice.tex:15-28`), where none of the four G1 archives exists.
Its S7 row still says six archives (`:310-315`), as does
`supplementary/SUPPLEMENTARY.md:273-283`, while the current manifest has ten.

The byte evidence itself is sound: all four `.zst` files are tracked at
`947005c`, and stream verification plus live-plain comparison passes. The
minimal repair is therefore textual/provenance: fix the two missed sentences;
give G1 rows their actual archive commit (`947005c`) while retaining
`ba5e4a3` only for the original six; gate that each claimed commit contains
its path; add the G1 immutable pin to the complete pointer layer; and update
the six-to-ten descriptions.
