#!/usr/bin/env python
"""Phase 5.2 physical-silicon encoder anchor (RTX 5090).

Serves the extracted Qwen3-VL vision tower (models/Qwen3-VL-8B-ViT) as ONE
real encoder worker on the GPU and measures the ACTUAL per-batch encoder
service time f(N) — one forward over N images of 448x448 (28x28 patch grid,
196 post-merge tokens/image) — for a set of batch sizes N, then compares the
measured f(N) against the simulator's AIC-costed prediction
(aic_f_n_postinfill.csv, grid-exact post-infill) as a RATIO.

This is the silicon-side complement to the live control-loop anchor. Because
the SM clocks are NOT locked here (locking needs sudo), ABSOLUTE latencies run
~fast per the thesis's own finding; the RATIO measured/predicted is the
clock-invariant primary result and is what this script foregrounds.

Protocol (matches the chapter's replicated protocol used in
measured_f_n_5x50.csv): model loaded once; per N, NRUNS independent
replications, each with its own WARMUP forwards then ITERS CUDA-event-timed
forwards. mean/ci95 across replication means; p50/p99 pool all iterations.
SM clock sampled per replication.

Usage:
  bench_encoder_anchor.py [--attn flash_attention_2|sdpa]
                          [--ns 1,6,8,16,32,64] [--nruns 5] [--iters 50]
                          [--warmup 10] [--out out.json]
"""
import argparse
import csv
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

import torch
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel

PATCH = 16                 # pixels per patch side
TEMPORAL = 2               # temporal_patch_size (single images duplicated)
IN_FEATURES = 3 * TEMPORAL * PATCH * PATCH
GRID = 28                  # 448 / 16 -> 784 pre-merge patches, 196 post-merge tokens

_HERE = os.path.dirname(os.path.abspath(__file__))
AIC_CSV = os.path.join(_HERE, os.pardir, "phaseB_batch_validation",
                       "aic_f_n_postinfill.csv")


def gpu_state():
    """Snapshot name/clock/power/temp/mem via nvidia-smi (best effort)."""
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,clocks.sm,clocks.max.sm,power.draw,temperature.gpu,"
             "clocks_throttle_reasons.active,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        parts = [p.strip() for p in out.stdout.strip().splitlines()[0].split(",")]
        return {"name": parts[0], "sm_clock_mhz": int(parts[1]),
                "max_sm_clock_mhz": int(parts[2]), "power_w": float(parts[3]),
                "temp_c": int(parts[4]), "throttle_hex": parts[5],
                "mem_used_mib": int(parts[6])}
    except Exception as ex:  # noqa: BLE001
        return {"error": str(ex)}


def sm_clock_mhz() -> int:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=clocks.sm", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:  # noqa: BLE001
        return -1


def load_aic_prediction():
    pred = {}
    with open(AIC_CSV) as f:
        for row in csv.DictReader(f):
            pred[int(row["n_images"])] = float(row["aic_ms"])
    return pred


def bench_n(model, n, warmup, iters, nruns):
    """nruns replications for batch size n; returns metrics dict."""
    grid = torch.tensor([[1, GRID, GRID]] * n, device="cuda")
    px = torch.randn(GRID * GRID * n, IN_FEATURES, device="cuda", dtype=torch.bfloat16)
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
    peak_mem_gb = torch.cuda.max_memory_allocated() / 1e9
    del px, grid
    all_times.sort()
    mean = statistics.fmean(run_means)
    t = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.776, 6: 2.571, 8: 2.365, 10: 2.262}.get(
        len(run_means), 2.0)
    ci95 = (t * statistics.stdev(run_means) / len(run_means) ** 0.5
            if len(run_means) > 1 else 0.0)
    return {
        "n_images": n,
        "patches": GRID * GRID * n,
        "post_merge_tokens": 196 * n,
        "mean_ms": round(mean, 4),
        "ci95_ms": round(ci95, 4),
        "p50_ms": round(all_times[len(all_times) // 2], 4),
        "p99_ms": round(all_times[int(len(all_times) * 0.99)], 4),
        "min_ms": round(all_times[0], 4),
        "sm_clock_mhz": max(set(clocks), key=clocks.count),
        "sm_clock_all": clocks,
        "peak_mem_gb": round(peak_mem_gb, 3),
        "ms_per_img": round(mean / n, 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="/home/gio/tese/models/Qwen3-VL-8B-ViT")
    ap.add_argument("--attn", default="flash_attention_2",
                    choices=["flash_attention_2", "sdpa", "eager"])
    ap.add_argument("--ns", default="1,6,8,16,32,64")
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--iters", type=int, default=50)
    ap.add_argument("--nruns", type=int, default=5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ns = [int(x) for x in args.ns.split(",")]
    pred = load_aic_prediction()

    attn_used = args.attn
    t0 = time.time()
    try:
        model = Qwen3VLVisionModel.from_pretrained(
            args.model_dir, dtype=torch.bfloat16, attn_implementation=args.attn
        ).cuda().eval()
    except Exception as ex:  # noqa: BLE001
        print(f"# {args.attn} load failed ({type(ex).__name__}: {ex}); "
              f"falling back to sdpa", file=sys.stderr, flush=True)
        attn_used = "sdpa"
        model = Qwen3VLVisionModel.from_pretrained(
            args.model_dir, dtype=torch.bfloat16, attn_implementation="sdpa"
        ).cuda().eval()
    load_s = time.time() - t0
    n_params = sum(p.numel() for p in model.parameters())

    state_before = gpu_state()
    rows = []
    print("n_images,post_tokens,mean_ms,ci95_ms,p50_ms,p99_ms,min_ms,"
          "ms_per_img,sm_clock_mhz,peak_mem_gb,aic_pred_ms,ratio", flush=True)
    for n in ns:
        torch.cuda.reset_peak_memory_stats()
        m = bench_n(model, n, args.warmup, args.iters, args.nruns)
        aic = pred.get(n)
        m["aic_pred_ms"] = aic
        m["ratio_meas_over_pred"] = round(m["mean_ms"] / aic, 4) if aic else None
        rows.append(m)
        print(f"{n},{m['post_merge_tokens']},{m['mean_ms']:.3f},{m['ci95_ms']:.3f},"
              f"{m['p50_ms']:.3f},{m['p99_ms']:.3f},{m['min_ms']:.3f},"
              f"{m['ms_per_img']:.3f},{m['sm_clock_mhz']},{m['peak_mem_gb']:.3f},"
              f"{aic if aic else 'NA'},"
              f"{m['ratio_meas_over_pred'] if m['ratio_meas_over_pred'] else 'NA'}",
              flush=True)
    state_after = gpu_state()

    result = {
        "experiment": "phase5.2_physical_encoder_anchor",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "attn_requested": args.attn,
        "attn_used": attn_used,
        "model_dir": args.model_dir,
        "n_params": n_params,
        "load_s": round(load_s, 2),
        "protocol": {"nruns": args.nruns, "iters": args.iters,
                     "warmup": args.warmup, "image_px": 448, "grid": GRID},
        "aic_reference_csv": os.path.abspath(AIC_CSV),
        "clocks_locked": False,
        "gpu_state_before": state_before,
        "gpu_state_after": state_after,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "python": platform.python_version(),
        "rows": rows,
    }
    ratios = [r["ratio_meas_over_pred"] for r in rows if r["ratio_meas_over_pred"]]
    if ratios:
        result["ratio_summary"] = {
            "min": round(min(ratios), 3), "max": round(max(ratios), 3),
            "mean": round(statistics.fmean(ratios), 3),
            "spread_pct": round(100 * (max(ratios) - min(ratios)) / statistics.fmean(ratios), 1),
        }
    out_path = args.out or os.path.join(
        _HERE, f"anchor_{attn_used}_{args.nruns}x{args.iters}.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"# wrote {out_path}", file=sys.stderr, flush=True)
    if "ratio_summary" in result:
        rs = result["ratio_summary"]
        print(f"# ratio measured/AIC-pred: min {rs['min']}  max {rs['max']}  "
              f"mean {rs['mean']}  spread {rs['spread_pct']}%",
              file=sys.stderr, flush=True)
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
