---
from: claude
ts: 2026-07-27T10:37:00-03:00
re: reviewer:140_replay_archive_manifest
type: response
thread: D52-replay-archive-manifest
---

## D52 fixed: tracked per-file provenance manifest; documentation drift corrected

1. **Tracked manifest.** `verification/replay_archive_manifest.json`
   (commit d140bfe) carries, per archive file: plain SHA-256, compressed
   SHA-256, exact plain and compressed byte counts, row count, generating
   source (campaign + ledger pointer), the commit that archived it
   (ba5e4a3), the compression command (`zstd -19 -T8`) and zstd version,
   and a round-trip comparison RE-VERIFIED at manifest generation (the
   generator decompresses each archive and byte-compares against the plain
   file before writing the row). Package totals: 200,323,568 B compressed
   (191.043 MiB), 1,901,299,280 B plain (1.77072 GiB) -- matching your
   independent counts.
2. **Lineage and terms.** The manifest binds the package to its source:
   replay outputs derived from AzureLMMInferenceDataset2025 (CC-BY, per
   `data/source/README.md`), with explicit reuse terms (distributed with
   the repository under the source attribution's terms; cite thesis +
   dataset). S7 points at the manifest.
3. **Factual drift corrected.** Runner v2's header states 4/9
   archive-dependent cells and six archive files; S7 states exact bytes
   with binary units (1.77 GiB / 191.04 MiB) instead of "1.8 GB / ~192
   MB"; S7 no longer calls the committed report "latest"/"at HEAD" -- it
   is described as labeled with the exact HEAD it observed, to be
   regenerated rather than trusted as current. The committed report was
   regenerated at the closure commit chain (beb8db2 run committed in
   d140bfe).
