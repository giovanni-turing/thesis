# Phase B — batch-axis validation of the encoder cost curve f(N)

**Question** (user, 2026-07-08): is the rtx_5090 AIC collection fine-grained
enough now that parallel-chunk dispatch made f(N), N=1..64, the load-bearing
cost curve of every burst result?

**Method**: real extracted ViT (`models/Qwen3-VL-8B-ViT`, HF eager/sdpa
stack) measured for EVERY integer N in [1, 128] — one forward over N images
of 448² — 8 CUDA-event iterations per point after warmup, model loaded once
(`bench_vit_batches.py`); abandon-on-OOM protocol (no OOM: all 128 points
completed). SM clock steady at 2385–2400 MHz throughout (lock reference
2407; per-point clock in the CSV). AIC side: `EncoderCostModel.latency_ms(N)`
— the exact query path the two-pool converter uses (`aic_f_n.csv`).

**Results** (`measured_f_n.csv` vs `aic_f_n.csv`):

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

**Interpretation.** The growing component means per-image costs that the
AIC encoder graph does not model (patch-embed conv and DeepStack
gather/concat are known-unmodeled and scale linearly with N; kernel-variant
deltas scale with GEMM volume) — and possibly full-attention layers priced
sub-quadratically. The N=1 decomposition covered its point; the GROWTH
N=1→64 (+13% relative) is not yet attributed term-by-term.

**Impact assessment.**
- The decoupling/reversal findings are unaffected (both pools' knees move
  together under a cost rescale; the vision-vs-LLM knee ratio and the
  burst-order reversal are scale-robust).
- Absolute C* values and vision GPU-hours inherit the bias DIRECTION
  DEBATE: AIC prices the vLLM production kernel path (lower bound); the HF
  eager harness overstates a production serving stack (dispatch, kernel
  variants). Real vLLM-on-5090 sits between. Treat AIC as the optimistic
  bound and 1.6× as the pessimistic bound at N=64.

**Follow-ups**
1. Kernel-level profile at N=64 (torch.profiler, as the chapter did at
   N=1) to close the growth ledger term-by-term.
2. `--encoder-cost-scale` sensitivity knob in the converter; re-derive C*
   at 1.6× to bound the static-optimal table (expected: C* roughly
   proportional; steady24h C*=2 likely → 3–4, burst5 16 → ~26).
3. Candidate upstream note for the AIC PR: encoder graph lacks
   patch-embed conv + DeepStack terms; error grows with images-per-forward.
