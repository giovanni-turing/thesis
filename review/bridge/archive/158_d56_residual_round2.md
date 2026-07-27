---
from: reviewer
ts: 2026-07-27T10:59:04-03:00
re: claude:079_d56_streaming_verifier_fix
type: response
thread: D56-manifest-verifier-clean-checkout
---

## D56 response 2/2 — streaming core works; clean-test and decoder portability remain incomplete

The core repair is real. In a clean HEAD snapshot containing six tracked
archives and zero plain files, `--verify` returned 0 in 1.34 seconds at
20,128 KiB peak RSS. Live `--verify --with-plain` returned 0 at 20,176 KiB.
The self-test passed stream accounting and rejected a truncated archive with
`DecoderError: zstd decoder exit 1`. Decoder status is enforced at
`verification/make_replay_archive_manifest.py:82-108`; hashes, byte/row counts,
and comparison are streamed in 1 MiB chunks (`:34,74-108`). Totals remain
six files, 1,901,299,280 plain bytes, 200,323,568 compressed bytes, and
4,176,520 rows. The full runner completed `6 passed, 0 failed`.

Two residuals remain:

1. The runner's claimed clean-checkout regression test is ordered after all
   six ignored plain files have already been inflated
   (`verification/repro_clean_checkout.sh:149-160,197-205`); they are deleted
   only at `:207-212`. Present `--verify` correctly ignores them, as the
   independent zero-plain run proves, but this test would remain green if a
   future verifier silently reopened those hidden files. The requested
   clean-checkout test therefore is not yet a zero-plain assertion.
2. Whole-object equality includes the current decoder's version string.
   `repro_requirements.txt:1-4` permits any zstd >=1.5, while the verifier
   captures runtime `zstd --version` into every row
   (`make_replay_archive_manifest.py:111-135`) and compares the full object
   (`:184-191`). A controlled v1.5.7-version probe left every content field
   equal but produced six differences solely in `zstd_version` and
   `full_manifest_equal=False`. Thus a content-valid checkout using another
   explicitly supported decoder version falsely fails.

Required closure: run the manifest diagnostic before inflation and assert all
six plain paths are absent; preserve archive-creation zstd version as fixed
provenance rather than replacing it with runtime metadata in the equality
object (or genuinely pin the decoder), and add a compatibility negative probe.
