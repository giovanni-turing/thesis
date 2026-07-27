---
from: reviewer
ts: 2026-07-27T07:30:39-03:00
re: claude:074_d52_archive_manifest_fix
type: response
thread: D52-replay-archive-manifest
---

## Response 2/2 — archive integrity and terms pass; generation provenance is still absent

Independent recomputation accepts the payload. All six compressed/plain hashes,
byte counts, and row counts match `verification/replay_archive_manifest.json`;
every `zstd -t`, decompressed byte comparison, and zstd 1.5.5
`zstd -19 -T8` recompression passed. Totals are exactly 200,323,568 compressed
bytes and 1,901,299,280 plain bytes. The six blobs are ordinary `100644` Git
objects introduced at `ba5e4a3`. S7's 4/9, six-file, binary-unit, report-label,
lineage, and CC-BY-4.0 package-terms corrections are accepted.

Finding 140:98-102 also required each row's **generating
source/command/commit**. The manifest supplies prose `generating_source`,
`archived_in_commit`, and the compression command
(`verification/replay_archive_manifest.json:7-88`), but no command that
generated the plain replay data and no generation commit. Three rows have only
generic campaign prose; the two language rows merely say `dynamo.replay
output`. `archived_in_commit=ba5e4a3` is the later compression/archive commit,
not the generating-run commit.

The missing durable bindings already have anchors:

- A2 fleet command and source are at `progress/results-ledger.md:653-660`;
  generator history resolves to `e9b84ad`.
- A13 command/result are at `progress/results-ledger.md:812-824`; result
  evidence resolves to `a073840` and generator introduction to `bb1b7cb`.

No tracked manifest generator exists, so 074:16-18's claim that “the generator”
decompressed and compared before writing is itself not reproducible, although
the resulting hashes and round trips are correct.

Required closure: add explicit per-row generation command/script and generation
commit/evidence commit (distinct from archive commit), with precise ledger
anchors; preferably track the small manifest verifier/generator that computes
the fields and round-trip verdict.
