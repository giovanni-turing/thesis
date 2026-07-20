# G3 — dense 32B intermediate pricing: CORRECTED

Scope note: MoE arms (30B-A3B) were REMOVED — the thesis treats the dense family. The
235B-A22B-TP8 control is retained because it is the thesis's own flagship spot-check.

## Defect 1 — the numbers I first reported were STALE (pre-`--force` run)
Correct knee values from the current artifact (knees.md:22-28):
| arm | knee s | offered req/s | achieved req/s |
|---|---:|---:|---:|
| 8B TP1 (control) | 2.8158 | — | — |
| 8B TP2 (control) | 5.9245 | 16.43 | 15.78 |
| 235B-A22B TP8 (control) | 1.1351 | — | — |
| 32B TP2 (headline) | 0.8279 | 2.28 | 2.25 |
| 32B TP8 | 3.7224 | 10.33 | 10.00 |
Previously quoted 16.11 / 9.92 / 2.78 / 6.05 / 1.12 — none of these are knee rows.

## Defect 2 — UNIT CONFLATION
points/*.json field `offered_req_per_s` actually holds ACHIEVED throughput (e.g.
8b_tp2_s6p0542.json .offered_req_per_s = 16.109 while true offered = 2.774 x 6.0542 = 16.794).
Consistent units: offered 16.4346/2.2761 = 7.22x; achieved 15.7825/2.2549 = 7.00x.
Always state which convention is in use; never mix them in one sentence.

## Defect 3 — the runtime divergence is NOT confined to 235B-TP8
The driver's cross_check.json:79 asserts "the divergence is SPECIFIC to 235B-TP8" and :81 that
"ITL agrees across runtimes within 6-14%". The dense 8B-TP1 CONTROL contradicts both:
vs simulation/results/sweeps/reports/llm_head2k_aic_s{2,4,16}:
  TTFT p99 418.2/882.1/40163.5 (wheel) vs 394.3/782.7/49034.5 (source) = -5.7% / -11.3% / +22.1%
  ITL  p99 67.33/210.63/588.58 (wheel) vs 59.43/206.47/228.78 (source) = -11.7% / -2.0% / -61.1%
The 882 ms figure is quoted verbatim in tex/twopool.tex. This must be fixed in the artifact
before any cross-runtime claim is made.

## Defect 4 — the knee is not a point estimate
8B-TP2: s=6.0 FAILS (ITL p99 102.19), s=6.0542 PASSES (99.96), s=6.1089 FAILS (102.29).
Non-monotone over a ~2% span in s with 2-3% ITL wobble; the reported bracket_rel_width = 0.0127
is FINER than the demonstrated wobble. Quote knees to 2 significant figures, not 5.

## What SURVIVES and is quotable
- 8B-TP1 at s=1 reproduces tab:sim-poly-aic to the digit: TTFT mean 68.2 / p99 307.4 /
  max 4517.6 ms, 142.0 tok/s/user (reports/8b_tp1_s1.report.json vs tex/twopool.tex:105-108).
- Knees sit in the near-linear region (achieved/offered 0.96-0.99), so no saturation conflation.
- ITL is the binding constraint at EVERY arm's knee — consistent with the thesis mechanism.
- The qualitative conclusion stands: the dense 32B at TP2 reaches ~2.3 req/s against 8B-TP2's
  ~16.4 (7.2x offered / 7.0x achieved at equal GPU count), and even at TP8 — four times the
  silicon — reaches only ~10.3, still below 8B-TP2. The intermediate dense member cannot be made
  burst-feasible by parallelism within a sane budget, which REINFORCES the deployed 8B-TP2x2
  choice.

## Required caveats in the same paragraph
head2k isolation window only (2,000 requests, 721 s, raw arrivals, no encoder shift), uniform
arrival-rate scaling, source-built runtime, knees to 2 s.f.
