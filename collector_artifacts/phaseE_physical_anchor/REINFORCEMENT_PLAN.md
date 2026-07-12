# Encoder / AIC-gap reinforcement — multi-day GPU execution plan

Goal: turn the encoder-side finding from "single-point diagnosis" into a
silicon-anchored, generalized, fixed-and-validated reinforcement of the thesis.
Headline is unchanged (two-pool provisioning, ρ=15, 0.62×); this hardens the
weakest-anchored layer (the encoder controller, "sim-only") and yields the
AIC-cost-model contribution as a bonus.

Ground already covered (done):
- encoder_attention full collect (7,679, 0 err) — reproduces committed exactly.
- gemm full collect (35,742, 0 err) + collector OOM patch (empty_cache + mem-adaptive copies).
- AIC vs silicon gap characterized: 1.29–1.62× underprediction, root-caused to
  vit_ops composition (missing patch-embed + deepstack merger + GEMM interp).
- Tier-2 silicon-latency propagation: encoder_delay p99 588→858 ms (still PASS).
- ρ-knee: AIC greenlights ρ=20; silicon fails it (ρ≤15 safe, ρ≥20 fail).
- Single-factor calibration: ×1.48 → 32% error to ~5% mean.

## Queue (priority order; each notes what it reinforces)

### P0 — running now (autonomous)
- **Dense f(N)**: sdpa (→512) + FA2 (queued). Rich curve to *validate* the
  analytic model on 69 pts, not 8; FA2/SDPA delta across full range; N>64 chunking.
  → Output: anchor_dense_{sdpa,fa2}_2400.json. Mop up tail OOM (256/512) standalone if needed.

### P1 — multi-resolution sweep  (generality; DocQA relevance)  [~1–2 h GPU]
- Parametrize bench_encoder_anchor.py for image resolution (GRID hardcoded at 28=448²).
- Run f(N) at 448², 896², 1288² (and one dynamic-res / DocQA-scale point).
- Reinforces: does the ~1.48× gap + the analytic model hold across resolution, or
  does the fixed-overhead term re-weight? Turns "single-point calibration" into
  "calibrated across the operating envelope" — the biggest credibility upgrade.
- Depends on: anchor param edit (add empty_cache between N while there).

### P2 — implement + validate the vit_ops fix  (the strong contribution)  [CPU + re-cost]
- Add to aiconfigurator vit_ops.py / _run_encoder_phase: patch_embed op,
  deepstack merger op, tighten GEMM lookup at ViT M (odd patch counts).
- Re-cost, show ratio collapses 1.29–1.62× → <5% across N *and* the P1 resolutions.
- Reinforces: "diagnosed → fixed → validated → upstreamable" (vs just "found a gap").
  This is the difference between a note and a contribution.
- Depends on: P0 (curve to fit/validate), ideally P1 (resolution generality).

### P3 — multi-GPU generality  (is it AIC-systematic or 5090-specific?)  [~2–3 h/GPU]
- Same f(N) anchor + AIC comparison on a 2nd GPU (H100/A100/whatever is gettable).
- Reinforces: AIC under-predicts on other silicon too → systematic cost-model bias,
  not SM120-specific. Generalizes beyond one card.
- Depends on: provisioning another GPU (user can get one).

### P4 — Tier-3 multi-pass routing replay  (physical encoder anchor)  [~1 h GPU]
- Extract burst3 batch schedule (worker, batch, arrival) from the sim.
- Variant A: feed measured per-batch silicon latency into recorded routing → routing-exact queue.
- Variant B: C concurrent CUDA streams replay each worker's batch sequence → measure
  co-location contention the sim's independent-worker model omits.
- Reinforces: the encoder *control loop* on real silicon (the language live-anchor's
  encoder-side complement), incl. whether "C independent workers" holds.
- Depends on: burst3_fifo_replay.json (exists) + a concurrent-stream harness.

### P5 — re-run ρ-knee / week surface with the *validated* silicon model  [CPU]
- Replace the post-hoc ×ratio with the P2 native-corrected AIC model.
- Reinforces: the definitive silicon-anchored ρ-knee + week feasibility, natively
  (not a multiplier bolted on). Feeds the thesis's ρ-band claim directly.
- Depends on: P2.

### P6 — FA2 as a deployment lever (secondary)  [CPU, uses P0]
- Quantify FA2's ~9% on the ρ-knee / TTFT margin: does FA2 push ρ=20 back to feasible?
- Reinforces: "an engine-config choice moves the operating point" — small but concrete.
- Depends on: P0 (FA2 dense) + P5.

## Sequencing / dependencies
P0 (running) → P1 → P2 → {P5, P6}.  P3, P4 are independent, run when a GPU is free.
Critical path to the strong claim: P0 → P1 → P2. P3 (multi-GPU) is the generality
multiplier if a second card appears.

## Notes
- All anchor runs: locked 2400 MHz, uncontended GPU (one bench at a time), stream
  rows to a .log so progress survives OOM.
- Keep parquets/patch as-is; P2 edits vit_ops.py (aiconfigurator, upstreamable).
- Scope honesty in thesis: present as "anchored + generalized across our operating
  envelope," not "AIC off by 1.48× universally," until P3 breadth exists.
