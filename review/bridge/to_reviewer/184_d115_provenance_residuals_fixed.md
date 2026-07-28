---
from: claude
ts: 2026-07-28T17:06:00-03:00
re: 398_d115_fix_verification
type: escalation
thread: D115-ime-frontmatter-conformance
---

# D115 residuals — all three provenance texts corrected at `eb3249a`

1. Ledger now says **17** new adversarial probes, with the correction
   noted in place (append-only discipline kept).
2. UPSTREAM.txt states the correct tracking facts: upstream cb57593 DOES
   track colinha.pdf (blob ad9351e8..., identical to ours; an ignore
   pattern does not untrack a tracked file); the file was omitted in the
   initial vendoring and restored, making the vendored tree COMPLETE
   with no deliberate deviation.
3. The title-destination comments now describe the model's actual
   behavior: the English \title prints on the capa and folha de rosto;
   \translatedtitle supplies the Resumo's bibliographic reference and
   the Portuguese XMP title alternative.

Build 111 pages 0 errors; gate OK; selftest ALL PASS. Please verify for
closure.
