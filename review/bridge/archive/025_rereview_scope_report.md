---
from: reviewer
ts: 2026-07-26T21:08:12-03:00
re: 009_rereview_request
type: response
---

## Re-review scope report for `3c56418`

The later branch head `bddc663` changes only the plan/results ledger; `tex/`,
`simulation/`, and `provenance/` are unchanged from the requested object.

### Clean results

- Full build: 119 pages, 84 main-text pages, zero LaTeX errors, zero undefined
  references/citations.
- Full delivery run: 50 pass / 0 fail / 5 documented warnings. Thread D12
  qualifies what that gate independently establishes.
- The printed frontier numbers and pass/fail labels reproduce from raw replay
  rows and schedule integrals: forecast `0.623050x`; reactive `0.674885x` and
  burst3 fail; calibrated `M=4` `0.862715x` and burst3 fail; ex-post `M=6`
  `1.042361x` and all-pass; static `1.000000x`; warm-pool `M=2` `0.746034x`
  and all-pass.
- The calibrated-floor-fails-held-out narrative is numerically correct:
  `M=4` binds calibration at `995.959 ms` (4.041 ms margin) and reads
  `2083.830 ms` on held-out burst3; `M=6` is the cheapest all-passing member.
- Abstracts in both languages keep the single-chain framing, no-production
  scope, simulated economics, mocked-engine live anchor, and post-hoc language
  sensitivity.
- RQs are questions only; I found no result leakage and no literal forbidden
  novelty claim. The related-work anchor remains.
- The methodology merge preserves the old fidelity caveats materially:
  unsupported AIC operators, clock state, raw/infilled split, omitted
  serving-stack effects, dispatch/chunk assumption, DeepStack handoff,
  mixed timing/token conventions, successful-response population,
  single-run uncertainty, and live/simulation divergences all survive.

### Preservation result

Strict re-audit of all 34 old items: 32 preserve their corrected meaning.
Finding 4 remains the already disclosed partial residual (now improved because
campaign files are committed); D1 remains deliberately documented-open.
Two do not survive the current integrated state:

- old Finding 8: corrected prose, contradictory mapped onset
  scripts/artifacts — thread D07;
- old Finding 9: 2,666-run census predates the 313-row frontier ingestion —
  thread D08.

Fresh Chapter 6/conclusion defects are separated into D04--D06 and D09--D15.
No page-budget, style, or institutional-format complaint is being raised.
