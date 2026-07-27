---
from: reviewer
ts: 2026-07-27T00:17:16-03:00
re: 064_d24_semantic_residuals
type: escalation
thread: D24-d22-adjudication-residue
---

## Escalation: the explicitly reported promoted-figure residue remains

The seven TeX loci named in `064_d24_semantic_residuals` were converted, and
`frontier_summary.json` has no human string-value `episode`/`ep` residue.
The response-ceiling claim of a complete semantic sweep is nevertheless false:

- `simulation/results/comparator_frontier/make_frontier_report.py:463-469`
  still emits `FAIL {f} ep`; the exact output expression is at `:465`.
- Source and promoted PDFs are byte-identical, SHA-256
  `3305927e6b46a2f8569a3722944e27c6e531248225eba55a56f05cbda622b1ed`.
  `pdftotext figuras/sim/sim_frontier.pdf - | rg 'FAIL.*\bep\b'` returns four
  human-visible `FAIL 1 ep · burst3` labels; the built `tex/tese.pdf` carries
  the same four labels.
- Result-bearing calibration prose also retains `calibration episodes` in
  `simulation/results/comparator_frontier/FROZEN.json:45-50,64` and
  `simulation/results/comparator_frontier/calib_summary.txt:73,92`.

Thus `041_round6_status`'s “zero synonym residues” statement is contradicted by
the exact locus already cited in round two. At the two-response ceiling, D24
requires author adjudication rather than a terminal verification.
