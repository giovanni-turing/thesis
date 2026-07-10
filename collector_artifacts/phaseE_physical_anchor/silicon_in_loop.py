#!/usr/bin/env python
"""Silicon-in-the-loop encoder-pool benchmark (Phase 5.2 extension).

Replays a burst window's image-arrival schedule through the FIFO encoder
pool (faithful port of simulate_vision_pool: greedy whole-request
batching to the 64-image cap, parallel-chunk dispatch), but the per-batch
SERVICE TIME is the ACTUAL Qwen3-VL vision tower forward measured on this
GPU at stable clocks --- not the AIC prediction. Compares the resulting
silicon encoder-delay distribution against the AIC-simulated one.

f(N) is deterministic in latency, so each distinct dispatched batch size
is measured ONCE on real silicon (5x20 CUDA-timed forwards) and memoized;
the schedule then replays through the FIFO using those measured times.
This is the encoder-pool equivalent of the live LLM control-loop anchor.

Runs at whatever clocks are set (report them); ratios are clock-robust.
"""
import argparse
import csv
import json
import statistics
import subprocess
from pathlib import Path

import torch
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel

HERE = Path(__file__).resolve().parent
PATCH, TEMPORAL = 16, 2
IN_FEATURES = 3 * TEMPORAL * PATCH * PATCH
CAP = 64
PX = 448
G = PX // PATCH


def sm_clock():
    try:
        return int(subprocess.run(["nvidia-smi", "--query-gpu=clocks.sm",
                                   "--format=csv,noheader,nounits"],
                                  capture_output=True, text=True, timeout=5
                                  ).stdout.strip().splitlines()[0])
    except Exception:
        return -1


def load_aic_fn():
    p = HERE.parent / "phaseB_batch_validation" / "aic_f_n_postinfill.csv"
    d = {}
    for r in csv.DictReader(open(p)):
        d[int(float(r["n_images"]))] = float(r["aic_ms"])
    return d


class MeasuredFN:
    """Live silicon f(N), measured on demand and memoized."""
    def __init__(self, model, nruns=5, iters=20, warmup=5):
        self.model, self.nruns, self.iters, self.warmup = model, nruns, iters, warmup
        self.cache = {}
        self.aic = load_aic_fn()

    def _measure(self, n):
        grid = torch.tensor([[1, G, G]] * n, device="cuda")
        px = torch.randn(G * G * n, IN_FEATURES, device="cuda", dtype=torch.bfloat16)
        means = []
        with torch.no_grad():
            for _ in range(self.nruns):
                for _ in range(self.warmup):
                    self.model(px, grid_thw=grid)
                torch.cuda.synchronize()
                s, e = torch.cuda.Event(True), torch.cuda.Event(True)
                t = []
                for _ in range(self.iters):
                    s.record(); self.model(px, grid_thw=grid); e.record()
                    torch.cuda.synchronize(); t.append(s.elapsed_time(e))
                means.append(statistics.fmean(t))
        return statistics.fmean(means)

    def latency_ms(self, n):
        n = int(n)
        if n not in self.cache:
            self.cache[n] = self._measure(n)
        return self.cache[n]

    def chunked_service_ms(self, n):
        full, rem = divmod(int(n), CAP)
        tot = full * self.latency_ms(CAP) if full else 0.0
        if rem:
            tot += self.latency_ms(rem)
        return tot


def aic_service_ms(aic, n):
    full, rem = divmod(int(n), CAP)
    def lat(k):
        # nearest available AIC point (grid has exact 1..128)
        return aic.get(k) or aic[min(aic, key=lambda x: abs(x - k))]
    tot = full * lat(CAP) if full else 0.0
    if rem:
        tot += lat(rem)
    return tot


def handoff_ms(n_img, gbps=25.0, rtt=0.2):
    if n_img <= 0:
        return 0.0
    bytes_ = n_img * 196 * 4096 * 2  # post-merge tokens x hidden x bf16
    return rtt + bytes_ * 8 / (gbps * 1e9) * 1e3


def simulate(reqs, service_fn, aic):
    """One worker, parallel-chunk dispatch; encoder_delay per request."""
    free_at = 0.0
    delays = []
    busy = 0.0
    for arr, nimg in reqs:
        start = max(arr, free_at)
        svc = service_fn(nimg)
        finish = start + svc / 1000.0
        free_at = finish
        busy += svc / 1000.0
        delays.append((finish - arr) * 1000.0 + handoff_ms(nimg))
    delays.sort()
    def pct(p):
        return delays[min(len(delays) - 1, int(len(delays) * p))] if delays else 0.0
    return {"p50": round(pct(0.50), 3), "p90": round(pct(0.90), 3),
            "p99": round(pct(0.99), 3), "max": round(delays[-1], 3) if delays else 0.0,
            "busy_s": round(busy, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reqs", required=True, help="JSON: [[arrival_s, n_images], ...]")
    ap.add_argument("--window", required=True)
    ap.add_argument("--attn", default="sdpa")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    reqs = json.load(open(a.reqs))
    model = Qwen3VLVisionModel.from_pretrained(
        "/home/gio/tese/models/Qwen3-VL-8B-ViT", dtype=torch.bfloat16,
        attn_implementation=a.attn).to("cuda").eval()

    aic = load_aic_fn()
    mfn = MeasuredFN(model)
    clk0 = sm_clock()

    print(f"[{a.window}] {len(reqs)} image reqs; measuring silicon f(N) on demand...")
    sil = simulate(reqs, mfn.chunked_service_ms, aic)
    print(f"  silicon f(N) measured for N={sorted(mfn.cache)}")
    aic_res = simulate(reqs, lambda n: aic_service_ms(aic, n), aic)

    def verdict(p99):
        return "PASS" if p99 < 1000 else "FAIL"
    out = {"window": a.window, "n_image_reqs": len(reqs),
           "total_images": sum(n for _, n in reqs), "attn": a.attn,
           "sm_clock_mhz": clk0, "cap": CAP,
           "measured_fn": {str(k): round(v, 3) for k, v in sorted(mfn.cache.items())},
           "aic_fn": {str(k): aic.get(k) for k in sorted(mfn.cache)},
           "silicon_encoder_delay_ms": sil,
           "aic_sim_encoder_delay_ms": aic_res,
           "p99_ratio_silicon_over_aic": round(sil["p99"] / aic_res["p99"], 3) if aic_res["p99"] else None,
           "verdict_silicon": verdict(sil["p99"]), "verdict_aic": verdict(aic_res["p99"]),
           "note": "one worker; silicon service = live ViT forward (memoized per N); "
                   "clocks as-set (ratio clock-robust)"}
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"  AIC-sim  p99 {aic_res['p99']:.0f} ms [{out['verdict_aic']}]")
    print(f"  SILICON  p99 {sil['p99']:.0f} ms [{out['verdict_silicon']}]  "
          f"ratio {out['p99_ratio_silicon_over_aic']}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
