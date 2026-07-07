#!/usr/bin/env python
"""Phase B: batch-axis validation of the encoder cost model f(N).

Measures the real extracted Qwen3-VL ViT (+projector) forward over N images
of 448^2 (28x28 patch grid each) in ONE forward, for every integer
N in [1, 128] — through and beyond the 64-image dispatch cap — and stops at
the first CUDA OOM ("abandon on OOM"). The parallel-chunk dispatch decision
made f(N<=64) the load-bearing cost curve of every burst result; N>64
additionally probes the region where AIC extrapolates past its collected
batch range.

Model loaded once; per N: warmup then timed iterations with CUDA events.
SM clock sampled per point — compare against the 2407 MHz lock reference
(unlocked clocks inflate ~17%; ratios are clock-invariant).

Output CSV: n_images,patches,mean_ms,p50_ms,min_ms,iters,sm_clock_mhz
Run:  /home/gio/tese/eda/.venv/bin/python bench_vit_batches.py [--iters 8]
"""
import argparse
import statistics
import subprocess
import sys

import torch
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel

PATCH = 16
TEMPORAL = 2
IN_FEATURES = 3 * TEMPORAL * PATCH * PATCH
GRID = 28  # 448 / 16


def sm_clock_mhz() -> int:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=clocks.sm", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return -1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="/home/gio/tese/models/Qwen3-VL-8B-ViT")
    ap.add_argument("--attn", default="sdpa", choices=["sdpa", "flash_attention_2", "eager"])
    ap.add_argument("--n-max", type=int, default=128)
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--iters", type=int, default=8)
    args = ap.parse_args()

    model = Qwen3VLVisionModel.from_pretrained(
        args.model_dir, dtype=torch.bfloat16, attn_implementation=args.attn
    ).cuda().eval()

    print("n_images,patches,mean_ms,p50_ms,min_ms,iters,sm_clock_mhz", flush=True)
    for n in range(1, args.n_max + 1):
        try:
            grid = torch.tensor([[1, GRID, GRID]] * n, device="cuda")
            px = torch.randn(GRID * GRID * n, IN_FEATURES,
                             device="cuda", dtype=torch.bfloat16)
            times = []
            with torch.no_grad():
                for _ in range(args.warmup):
                    model(px, grid_thw=grid)
                torch.cuda.synchronize()
                start, end = torch.cuda.Event(True), torch.cuda.Event(True)
                for _ in range(args.iters):
                    start.record()
                    model(px, grid_thw=grid)
                    end.record()
                    torch.cuda.synchronize()
                    times.append(start.elapsed_time(end))
            times.sort()
            print(f"{n},{GRID*GRID*n},{statistics.fmean(times):.3f},"
                  f"{times[len(times)//2]:.3f},{times[0]:.3f},"
                  f"{len(times)},{sm_clock_mhz()}", flush=True)
            del px, grid
        except torch.cuda.OutOfMemoryError:
            print(f"# OOM at N={n} — abandoning per protocol", file=sys.stderr, flush=True)
            break
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
