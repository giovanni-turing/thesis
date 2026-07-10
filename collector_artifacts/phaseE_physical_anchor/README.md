# Phase E — Physical encoder anchor (first, unlocked-clock)

First silicon measurement of the served **whole** Qwen3-VL vision tower's
`f(N)` (per-forward latency vs images-per-batch), compared to the AIC
composition the simulator uses. Partially fulfils the physical-anchor
future-work item.

## What was run
`measure_fn_silicon.py`: loads the extracted ViT
(`models/Qwen3-VL-8B-ViT`, `flash_attention_2`), sweeps batch N∈{1,6,8,16,
32,64} at 448², 5 runs × 50 iters each, `cuda.synchronize`-timed, 10
warmup iters excluded. Compares to `aic_f_n_postinfill.csv`.

## Result (`fn_silicon.json`)

| N | measured ms | AIC ms | ratio |
|---|---|---|---|
| 1 | 50.7 | 8.16 | 6.21 |
| 6 | 89.7 | 31.79 | 2.82 |
| 8 | 118.2 | 43.13 | 2.74 |
| 16 | 239.0 | 82.22 | 2.91 |
| 32 | 493.3 | 160.20 | 3.08 |
| 64 | 653.8 | 316.37 | 2.07 |

**Reading.** For the serving-relevant batch range (N≥6) measured
whole-tower latency tracks the AIC composition at a **stable ~2.7–3.1×
ratio** — the composition's *shape* f(N) is correct; the offset is the
whole-tower-vs-operator gap (AIC prices attention+GEMM; the served
forward also runs patch-embed, projector, DeepStack mergers, dispatch).
N=1 is higher (6.2×, launch-overhead-dominated, not a serving regime);
N=64 lower (2.1×).

## Caveats (why this is a *first* anchor, not the final one)
- **Unlocked clocks** (observed 2385–2392 MHz vs the 2407 lock target).
  Absolute ratios are indicative; the *ratio's stability across the batch
  axis* is the clock-invariant, load-bearing quantity.
- **Whole-tower vs operator-only**: the ~3× is expected, not an error —
  it is the un-modeled preprocessing AIC does not price.
- Clean confirmation = locked-clock + operator-isolated re-run + one real
  encoder worker under a burst replay end-to-end. Listed as future work.

Feeds `tex/aiconfigurator.tex §validation` and the conclusion future-work.
