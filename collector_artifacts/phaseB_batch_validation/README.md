# Phase B — batch-axis validation of the encoder cost curve f(N)

## Question

(user, 2026-07-08) Is the rtx_5090 AIC collection fine-grained enough now
that parallel-chunk dispatch made f(N), N=1..64, the load-bearing cost
curve of every burst result?

## Method

Real extracted ViT (`models/Qwen3-VL-8B-ViT`, HF eager/sdpa stack)
measured for EVERY integer N in [1, 128] — one forward over N images of
448² — 8 CUDA-event iterations per point after warmup, model loaded once
(`bench_vit_batches.py`); abandon-on-OOM protocol (no OOM: all 128 points
completed). SM clock steady at 2385–2400 MHz throughout (lock reference
2407; per-point clock in the CSV). AIC side: `EncoderCostModel.latency_ms(N)`
— the exact query path the two-pool converter uses (`aic_f_n.csv`).

## Results

`measured_f_n.csv` vs `aic_f_n.csv`:

- N=1 ratio 1.43 — reproduces the calibration chapter's 1.45× wall-clock
  gap at 448², whose ledger was fully attributed (15.3% dispatch gaps,
  unmodeled patch-embed conv 4.8%, DeepStack glue, HF-vs-vLLM kernel
  variants ~12%). Consistency anchor: the harness agrees with itself.
- Ratio is NOT constant in N: dips to 1.28 (N≈4–6), then grows
  monotonically to 1.62 at N=64 and 1.66 at N=128.
  Mean 1.53 over N≤64; 1.63 over N>64.
- AIC's own batch-axis extrapolation past its collected range (batch>64)
  is smooth and near-linear (4.91→4.86 ms/img); the measured curve also
  stays smooth through 128 — no cliff at the cap.

## Query-grid anatomy (probed 2026-07-08)

f(N) at 448² issues ONE encoder-attention query at (b=N, s=784, 16h×72):
s=784 is NOT a collected point — every attention cost interpolates
s=576↔1024 (anchored physically by the chapter's 3% N=1 validation);
b interpolates between pow-2 rungs for non-pow-2 N. The MLP/projector
GEMMs are queried at m=784·N, so for N≳42 m exceeds 32,768 and lands in
the documented giant-tail OOM-gap region of the GEMM collection —
interpolator warnings confirm sparse anchors there ("only one data point
for a given xy", x=32/y=65536). Degraded large-m GEMM anchors are a
concrete additional contributor to the ratio growth at high N.

## Interpretation

The growing component means per-image costs that the AIC encoder graph
does not model (patch-embed conv and DeepStack gather/concat are
known-unmodeled and scale linearly with N; kernel-variant deltas scale
with GEMM volume) — and possibly full-attention layers priced
sub-quadratically. The N=1 decomposition covered its point; the GROWTH
N=1→64 (+13% relative) is not yet attributed term-by-term.

## Impact assessment

- The decoupling/reversal findings are unaffected (both pools' knees move
  together under a cost rescale; the vision-vs-LLM knee ratio and the
  burst-order reversal are scale-robust).
- Absolute C* values and vision GPU-hours inherit the bias direction
  debate: AIC prices the vLLM production kernel path (lower bound); the HF
  eager harness overstates a production serving stack (dispatch, kernel
  variants). Real vLLM-on-5090 sits between. Treat AIC as the optimistic
  bound and 1.6× as the pessimistic bound at N=64.

## Plateau analysis (2026-07-08)

Measured ms/img bottoms at N=6 (7.21), then drifts up to 8.07 by N=128;
marginal cost over N=81..128 is a flat ~8.2 ms/image — batching benefit
fully captured by N≈6–8, encoder compute-bound beyond. AIC's
fixed-overhead form keeps amortizing (4.86 at 128), which mechanically
produces the growing ratio. Real batching gain is ~1.4× (exhausted by
N≈6), not the AIC-side 1.6×-at-64 quoted in the twopool batching
paragraph.

## Statistical protocol note

8 timed iterations per point in ONE block (not the chapter's 5×50
replicated protocol; no t-CIs). Dispersion recorded: median
(mean−min)/mean 0.04% across all 128 points, worst 0.72% at N=2 — three
orders of magnitude below the 28–66% effects concluded from. Drift
check: per-point SM clock flat (2385–2400 MHz, no trend; N=1 and N=128
both at 2400), and the ratio's dip-then-rise shape is inconsistent with
monotone thermal drift. Sufficient for the ratio analysis; RE-MEASURE at
the chapter protocol (5×50, locked-clock confirmation) before any value
is quoted verbatim in the thesis or shipped as the converter cost table.

## Follow-ups

1. Kernel-level profile at N=64 (torch.profiler, as the chapter did at
   N=1) to close the growth ledger term-by-term.
2. `--encoder-cost-scale` sensitivity knob in the converter; re-derive C*
   at 1.6× to bound the static-optimal table (expected: C* roughly
   proportional; steady24h C*=2 likely → 3–4, burst5 16 → ~26).
3. Better: `--encoder-cost-table measured_f_n.csv` mode — cost forwards
   from the measured curve directly (we own f(N) for every queryable N).
   Removes the AIC-vs-eager band for the encoder pool and enables an
   honest cap-size study: on silicon, cap=8 matches cap=64 per-image cost
   with 8× finer blocking quanta → likely better burst tails at zero
   throughput cost. (The AIC-costed sim would wrongly punish small caps —
   its model believes amortization continues.)
4. Chapter caveat: twopool "1.6× gain / ~2.9 ms fixed overhead" is the
   AIC-model statement; measured gain ~1.4×, saturating at N≈6.
5. Candidate upstream note for the AIC PR: encoder graph lacks
   patch-embed conv + DeepStack terms; error grows with images-per-forward.
