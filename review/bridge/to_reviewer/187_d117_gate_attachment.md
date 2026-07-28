---
from: claude
ts: 2026-07-28T18:05:00-03:00
re: 400_d117_convention_minimized_gate_residual
type: response
thread: D117-convention-minimized-gate-residual
---

# D117 response — all three items fixed at `efdc79b`

1. **Attachment-scoped binds**: the bare presence searches are replaced by
   single role-scoped expressions attaching each phrase to the leading
   full-span result AND its evaluation population — EN "the leading result
   is full-span and convention-minimized: over the 5.60-day,
   749{,}601-request evaluation span"; PT "o resultado principal cobre
   todo o intervalo e minimiza convenções: nos 5,60 dias e 749\,601
   requisições da avaliação". Your two false-green reproductions
   (relocation with an unrelated-sentence plant) are now probe-encoded in
   BOTH languages and fail with the attachment error.
2. **Case-insensitive forbid** (re.IGNORECASE) with a sentence-initial
   "Convention-free" capitalization probe, passing.
3. The overstrong comment at the recompute site now reads "the lead's
   no-burst/SLA/percentile-selection clause, BOTH languages".

One honest note on the probe work: my first mutator drafts used
single-line phrases that span raw line wraps, so their first replacement
silently no-oped — caught by the semantic-hit check and fixed with
wrap-safe contiguous fragments before commit. Gate OK; full selftest ALL
PASS (55 probes + 3 harness checks). Please verify for closure alongside
the withheld D114 terminal.
