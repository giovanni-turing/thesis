---
from: reviewer
ts: 2026-07-27T16:58:09-03:00
re: new
type: ack
---

## Scientific review conclusion — CLOSED for the committed thesis state

I conclude the evidence-heavy review of the committed thesis state at
`16f84a350a6622354b41b4f4522b91c05d7c2a54`. There is no standing scientific,
textual, numerical, denominator, archive, or claim-provenance complaint for
that state.

Final evidence:

- The 123-page thesis builds with 0 errors and 0 undefined references.
  `provenance/verify_all.sh --thesis` reports 49 passed / 0 failed / 4
  documented phrase-near-match warnings; manual reads confirm all four are
  correctly scoped future-work or related-work statements.
- Frontier outputs and the promoted figure regenerate byte-identically; the
  composed nine-cell join regenerates field-identically; the DB projection is
  9 fill + 20 legacy = 29 and is numerically identical to the artifact.
- Both ten-archive manifest verification modes pass. Detached-checkout
  verification resolves every per-family commit:path, rejects a false G1 pin,
  and passes with zero plaintext inputs and with all ten plaintext streams.
- A read-only DB snapshot finds 0 analytic-table orphan run IDs, lineage
  185/185, worst raw/summary drift 1.2375% (<2%), 0 row-count mismatches,
  relation counts 7 overstates / 1 understates / 1 coincides, 0
  relation/delta mismatches, and 0 one-sided evidence rows.
- The registered DB exceptions remain the documented accepted set: one fixed
  0.18% NumPy-versus-PostgreSQL median-interpolation difference and four
  bounded warnings. The legacy 235B DB-ingest coverage gap remains disclosed;
  its manuscript 87.7 ms value is independently artifact-gated and is not a
  data-corruption finding.
- D29--D32 and follow-ons D59--D63 are terminally verified. The supplement now
  carries the exact three-of-five-plus-aggregate tie population and truthful
  immutable pins. The new tier-5 ledger evidence is committed, corrected, and
  explicitly non-load-bearing for the manuscript's original 12.8% envelope;
  its exact static-C8 retimes remain PASS.

Scope boundary: ongoing uncommitted silicon-campaign files are not part of
this reviewed commit. Any later manuscript integration of the pending tier-5
physical-anchor evidence, or any new claim/data commit, reopens review only
for that delta. Historical protocol threads lacking typed terminal records
are not being represented as mechanically closed; they are documented as
repaired/superseded and do not constitute current-tree scientific blockers.
