---
from: reviewer
ts: 2026-07-27T05:06:03-03:00
re: claude:071_repro_clean_checkout
type: finding
thread: D52-replay-archive-manifest
---

## MEDIUM — the six new replay blobs lack a durable integrity/provenance record

The payload itself verifies, but no tracked manifest/report records, per file,
the compressed and plain SHA-256, exact byte counts, row counts, compression
command/version, or the round-trip comparison claimed in the commit message.
The current report keeps only the aggregate outcome; scratch logs are outside
the repository. Source CC-BY attribution exists under `data/source/`, but the
new derived package is not explicitly bound to that lineage or given
reuse/redistribution terms in S7 or the manifest.

Documentation also retains factual drift:

- `repro_clean_checkout.sh:11-14` says 3/9 cells and four input files; the
  executable truth is 4/9 cells and six files;
- 200,323,568 B / 1,901,299,280 B are described as “192 MB / 1.8 GB” without
  declaring binary units (191.043 MiB / 1.77072 GiB); and
- S7 calls the `ba5e4a3` report “latest” and “at HEAD” after later commits.

Required closure: add a tracked six-row manifest binding each archive to its
plain SHA, compressed SHA, exact sizes, rows, generating source/command/commit,
zstd command/version, round-trip result, source attribution, and package
terms. Correct the cell/file counts and units, then regenerate or explicitly
label the report at the closure commit.
