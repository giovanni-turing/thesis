# Phase 5.2 — physical-silicon encoder anchor (RTX 5090)

## Question

Thesis §5.2 lists a physical-silicon encoder anchor as future work: serve the
extracted Qwen3-VL vision tower as ONE real encoder worker on the GPU, measure
the ACTUAL per-batch encoder service time f(N), and tie the simulator's
AIC-costed f(N) prediction to hardware. This is the silicon-side complement to
the live control-loop anchor.

## Method

Real extracted ViT (`models/Qwen3-VL-8B-ViT`, 576M params, the tower used
across the Qwen3-VL family) served as one worker on the RTX 5090 (SM120).
Each N images of 448² (28×28 patch grid → 196 post-merge tokens/image) run as
ONE forward — exactly the `(batch_size=1, num_images=N)` query the two-pool
converter costs the encoder pool by (`EncoderCostModel.latency_ms(N)`;
converter docstring: encoder latency is exactly a function of TOTAL images).
Chapter replicated protocol: model loaded once, per N five independent
replications each with its own 10-forward warmup then 50 CUDA-event-timed
forwards; mean/CI95 across replication means. `bench_encoder_anchor.py`.

Measured f(N) is compared to the simulator's AIC prediction
(`../phaseB_batch_validation/aic_f_n_postinfill.csv`, grid-exact post-infill,
f(1)=8.162, f(64)=316.369 — the exact numbers the thesis Table quotes) as a
RATIO. **Clocks were NOT locked** (locking needs sudo); per the thesis finding,
absolute latencies at unlocked clocks run fast, but the measured/predicted
RATIO is clock-invariant and is the primary result. GPU throttle-reasons hex
stayed 0x0 (boost clock 2385–2400 MHz, no thermal throttle; max SM 3105 MHz —
this is the unlocked-boost regime, a locked-clock re-run is needed for
publication-grade absolutes).

## Results

`anchor_sdpa_5x50.json` (primary), `summarize_anchor.py` for the table.
Measured f(N) reproduces the phase-B 5×50 silicon reference to within ±0.7% at
every shared N (N=64: 511.26 vs 511.23 ms — 0.01%), an independent
same-methodology confirmation. Measured/AIC ratio rises 1.37 (N=1) → 1.62
(N=64), mean 1.47 over N∈{1,6,8,16,32,64} — reproducing on today's silicon the
phase-B ratio curve (1.43→1.62) that §5.3.1 attributes term-by-term
(patch-embed conv + DeepStack, unmodeled by the AIC encoder graph; growing with
images-per-forward).

Backend: `sdpa` is the reported primary because it is the phase-B backend, so
the ±0.7% cross-check is like-for-like. `flash_attention_2` loads and runs
cleanly on SM120 **when uncontended** (`anchor_flash_attention_2_5x50.json`,
CI ≤0.08 ms): it ties sdpa at N=1 (11.22 ms) and is faster at higher N — N=8
54.1 vs 58.5 ms, N=64 465.7 vs 511.3 ms (~9%). So fa2 gives a LOWER ratio band
(1.37→1.47 over N=1→64) than sdpa (1.37→1.62): the production flash-attn kernel
path sits closer to the AIC prediction than the HF sdpa stack, consistent with
§5.3.1's framing of AIC (vLLM production kernels) as the optimistic bound and
the HF harness as the pessimistic bound — measured silicon lands between,
nearer the optimistic side under fa2. A first fa2 attempt showed wild
instability (N=1 at 50 ms, CI 300+ ms) — traced to GPU contention with a
concurrent agent process sharing this GPU, NOT a flash-attn defect; every
primary here was re-run on a verified-idle GPU (single compute app, 88 MiB
baseline, throttle hex 0x0).

### (iii) end-to-end FIFO replay

`replay_burst3_fifo.py` / `burst3_fifo_replay.json`: the burst3 image-arrival
schedule (1241 image-bearing reqs, 143,240 images, regenerated exactly from the
trace) replayed through a faithful port of `simulate_vision_pool` (1 worker,
64-cap) under two cost models. Replay-under-AIC reproduces the sim's
`vision_burst3_C1.json` encoder-delay to the digit (p99 54169.571 vs 54169.533)
— proving the port is faithful. Swapping in the MEASURED f(N) raises encoder-
delay p99 2.87× (54,170→155,349 ms) and busy-time 712→1,144 s over the 1,601 s
horizon (44%→71% util): the measured silicon is slower than the AIC model, so
the single-worker case is even more infeasible — consistent with the ratio.

## Files

- `bench_encoder_anchor.py` — the silicon f(N) runner (5×50 protocol, ratio vs AIC).
- `anchor_sdpa_5x50.json` — primary result (measured f(N), ratios, GPU state).
- `anchor_flash_attention_2_5x50.json` — fa2 spot-check documenting its instability.
- `summarize_anchor.py` — measured-vs-AIC table + phase-B cross-check.
- `replay_burst3_fifo.py`, `burst3_fifo_replay.json`, `burst3_img_reqs.json` — (iii).

## Stable-clock confirmation (2026-07-10)
Re-run on a single-tenant GPU at stable clocks (SM 2377-2400 MHz, mem
14001, persistence on) — `anchor_sdpa_locked2400.json`: ratio 1.32-1.62
(mean 1.43), CI95 <=0.05 ms. Confirms the reported 1.37-1.62 band at
steady clocks; absolutes now publication-grade (2400 vs the 2407 target
is 0.3%, negligible). N=64: 511.68 ms measured vs the phase-B 511.23 —
0.09% reproduction.
