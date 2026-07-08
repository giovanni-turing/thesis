# Phase D — encoder-worker model-side cold start (RTX 5090)

**Question.** The 4.4 lead-time grids assume the vision encoder (576M params,
1.15 GB bf16) cold-starts much faster than a language worker. Measure the
model-side floor instead of assuming it.

**Method.** `measure_cold_start.py` — one fresh interpreter per trial, wall
timestamps per phase (imports → CUDA ctx → checkpoint load → GPU transfer →
first 448² forward → second forward). 3 trials into `trials.jsonl`. True
cold-disk cost bounded separately with an O_DIRECT sequential read of the
safetensors (page cache bypassed, no sudo). Clocks unlocked — irrelevant for
IO/init wall time; forward latencies here are indicative only (calibrated
numbers are Phase B's).

**Results (2026-07-08).**

| Phase | trial 1 (coolest) | trials 2–3 (warm cache) |
|---|---|---|
| python + torch + transformers imports | 2.82 s | 2.19–2.20 s |
| CUDA context | 0.09 s | 0.07 s |
| checkpoint load (mmap, lazy) | 0.09 s | 0.06 s |
| weights → GPU (incl. page-in) | 1.32 s | 0.13 s |
| first forward (autotune/handles) | 0.44 s | 0.32–0.33 s |
| **total to serving-ready** | **4.76 s** | **2.77–2.79 s** |
| second forward (steady) | 0.011 s | 0.011–0.012 s |

O_DIRECT read of the 1,152,811,416-byte checkpoint: **0.111 s (10.4 GB/s)** —
a fully cold page cache adds ≈0.1 s, bounded by this number.

**Conclusion.** Model-side cold start ≈ **3–5 s**, dominated by interpreter/
framework imports, not weights (0.11 s disk + 0.13 s H2D). A prewarmed
process (imports done, weights resident) restarts in well under a second.
Therefore every lead value above ~5 s in the 4.4 grid measures
**orchestration** — pod scheduling, image pull, router registration, node
acquisition — and the encoder-pool lead grid {10, 20, 30, 60, 120, 300 s}
spans warm-pool (short end) to node-provision (long end) regimes on top of a
measured ~3–5 s model floor. The language pool sits in a different regime by
construction (16 GB weights + engine init + KV allocation; see
ServerlessLLM/BlitzScale citations in related work) — per-pool provisioning
implies per-pool lead times.
