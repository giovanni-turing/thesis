#!/usr/bin/env python
"""Route A: measure the real extracted Qwen3-VL ViT (+projector) on local GPU.

Runs the standalone Qwen3VLVisionModel (ViT + merger + deepstack mergers,
extracted from Qwen/Qwen3-VL-8B-Instruct; architecturally identical to the
235B vision tower) with CUDA-event timing.

Usage:
    .venv/bin/python bench_vit_real.py [--model-dir DIR] [--attn sdpa|flash_attention_2]
                                       [--sizes 448,896,1344] [--batch 1] [--nruns 5]
Output: CSV rows on stdout:
    attn,label,patches,batch,mean_ms,ci95_ms,p50_ms,p99_ms,sm_clock_mhz
mean/ci95 are across --nruns independent replications (each a fresh timing block
after its own warmup); p50/p99 pool all iterations. SM clock is sampled after
each replication via nvidia-smi — lock clocks first for stable numbers.
"""
import argparse
import statistics
import subprocess

import torch
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel


def sm_clock_mhz():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=clocks.sm", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return -1

PATCH = 16          # pixels per patch side
TEMPORAL = 2        # temporal_patch_size (single images duplicated)
IN_FEATURES = 3 * TEMPORAL * PATCH * PATCH


def bench(model, grid_h, grid_w, batch, warmup, iters, nruns):
    """nruns independent replications; returns (mean, ci95, p50, p99, clocks)."""
    grid = torch.tensor([[1, grid_h, grid_w]] * batch, device="cuda")
    n = grid_h * grid_w * batch
    px = torch.randn(n, IN_FEATURES, device="cuda", dtype=torch.bfloat16)
    run_means, all_times, clocks = [], [], []
    with torch.no_grad():
        for _ in range(nruns):
            for _ in range(warmup):
                model(px, grid_thw=grid)
            torch.cuda.synchronize()
            start, end = torch.cuda.Event(True), torch.cuda.Event(True)
            times = []
            for _ in range(iters):
                start.record()
                model(px, grid_thw=grid)
                end.record()
                torch.cuda.synchronize()
                times.append(start.elapsed_time(end))
            run_means.append(statistics.fmean(times))
            all_times.extend(times)
            clocks.append(sm_clock_mhz())
    all_times.sort()
    mean = statistics.fmean(run_means)
    # 95% CI across independent replications (t≈2.776 for n=5; fall back to 2x stdev/sqrt(n))
    t = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.776, 6: 2.571, 10: 2.262}.get(len(run_means), 2.0)
    ci95 = t * statistics.stdev(run_means) / len(run_means) ** 0.5 if len(run_means) > 1 else 0.0
    return (mean, ci95,
            all_times[len(all_times) // 2], all_times[int(len(all_times) * 0.99)],
            clocks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="/home/gio/tese/models/Qwen3-VL-8B-ViT")
    ap.add_argument("--attn", default="sdpa", choices=["sdpa", "flash_attention_2", "eager"])
    ap.add_argument("--sizes", default="448,896,1344")
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--iters", type=int, default=50)
    ap.add_argument("--nruns", type=int, default=5)
    args = ap.parse_args()

    model = Qwen3VLVisionModel.from_pretrained(
        args.model_dir, dtype=torch.bfloat16, attn_implementation=args.attn
    ).to("cuda").eval()

    print("attn,label,patches,batch,mean_ms,ci95_ms,p50_ms,p99_ms,sm_clock_mhz")
    for px_size in (int(s) for s in args.sizes.split(",")):
        g = px_size // PATCH
        mean, ci95, p50, p99, clocks = bench(
            model, g, g, args.batch, args.warmup, args.iters, args.nruns
        )
        clk = max(set(clocks), key=clocks.count)
        print(f"{args.attn},{px_size}x{px_size},{g*g},{args.batch},"
              f"{mean:.3f},{ci95:.3f},{p50:.3f},{p99:.3f},{clk}")


if __name__ == "__main__":
    main()
