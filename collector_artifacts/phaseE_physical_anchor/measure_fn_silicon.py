#!/usr/bin/env python
"""Phase 5.2 physical encoder anchor: measured f(N) on RTX 5090 silicon vs
the simulator's AIC-predicted f(N). Reuses the validated ViT-load + timing
pattern from phaseA_validation/bench_vit_real.py; sweeps the BATCH axis
(images per forward) at 448px, which is exactly what the simulator's
encoder cost model f(N) predicts.

Clock note: if clocks are unlocked the ABSOLUTE ms run ~fast, but the
measured/predicted RATIO is clock-invariant (thesis Phase A finding) ---
so the ratio column is the anchor result.
"""
import argparse
import csv
import json
import statistics
import subprocess
from pathlib import Path

import torch
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel

PATCH = 16
TEMPORAL = 2
IN_FEATURES = 3 * TEMPORAL * PATCH * PATCH
HERE = Path(__file__).resolve().parent


def sm_clock_mhz():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=clocks.sm", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return -1


def bench(model, g, batch, warmup, iters, nruns):
    grid = torch.tensor([[1, g, g]] * batch, device="cuda")
    n = g * g * batch
    px = torch.randn(n, IN_FEATURES, device="cuda", dtype=torch.bfloat16)
    run_means, clocks = [], []
    with torch.no_grad():
        for _ in range(nruns):
            for _ in range(warmup):
                model(px, grid_thw=grid)
            torch.cuda.synchronize()
            s, e = torch.cuda.Event(True), torch.cuda.Event(True)
            times = []
            for _ in range(iters):
                s.record(); model(px, grid_thw=grid); e.record()
                torch.cuda.synchronize()
                times.append(s.elapsed_time(e))
            run_means.append(statistics.fmean(times))
            clocks.append(sm_clock_mhz())
    mean = statistics.fmean(run_means)
    t = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.776}.get(len(run_means), 2.0)
    ci = t * statistics.stdev(run_means) / len(run_means) ** 0.5 if len(run_means) > 1 else 0.0
    return mean, ci, max(set(clocks), key=clocks.count)


def load_aic_fn():
    """AIC composed f(N) reference: {N: latency_ms}."""
    p = HERE.parent / "phaseB_batch_validation" / "aic_f_n_postinfill.csv"
    out = {}
    with open(p) as f:
        for row in csv.DictReader(f):
            for k in row:
                if k.lower() in ("n", "batch", "images"):
                    nkey = k
            lk = [k for k in row if "lat" in k.lower() or "compos" in k.lower() or "ms" in k.lower()]
            try:
                out[int(float(row[nkey]))] = float(row[lk[0]])
            except Exception:
                pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="/home/gio/tese/models/Qwen3-VL-8B-ViT")
    ap.add_argument("--attn", default="flash_attention_2")
    ap.add_argument("--px", type=int, default=448)
    ap.add_argument("--batches", default="1,6,8,16,32,64")
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--iters", type=int, default=50)
    ap.add_argument("--nruns", type=int, default=5)
    ap.add_argument("--out", default=str(HERE / "fn_silicon.json"))
    a = ap.parse_args()

    try:
        model = Qwen3VLVisionModel.from_pretrained(
            a.model_dir, dtype=torch.bfloat16, attn_implementation=a.attn).to("cuda").eval()
        attn = a.attn
    except Exception as ex:
        print(f"[warn] {a.attn} load failed ({ex}); falling back to sdpa", flush=True)
        model = Qwen3VLVisionModel.from_pretrained(
            a.model_dir, dtype=torch.bfloat16, attn_implementation="sdpa").to("cuda").eval()
        attn = "sdpa"

    g = a.px // PATCH
    aic = load_aic_fn()
    rows = []
    print(f"attn={attn} px={a.px} patches={g*g}")
    print(f"{'N':>4} {'meas_ms':>9} {'ci95':>6} {'aic_ms':>8} {'ratio':>6} {'clk':>5}")
    for N in (int(x) for x in a.batches.split(",")):
        try:
            mean, ci, clk = bench(model, g, N, a.warmup, a.iters, a.nruns)
        except torch.cuda.OutOfMemoryError:
            print(f"{N:>4}  OOM — skip"); torch.cuda.empty_cache(); continue
        pred = aic.get(N)
        ratio = mean / pred if pred else None
        rows.append({"N": N, "meas_ms": round(mean, 3), "ci95_ms": round(ci, 3),
                     "aic_ms": pred, "ratio_meas_over_aic": round(ratio, 3) if ratio else None,
                     "sm_clock_mhz": clk})
        print(f"{N:>4} {mean:>9.3f} {ci:>6.3f} "
              f"{(pred if pred else float('nan')):>8.2f} "
              f"{(ratio if ratio else float('nan')):>6.3f} {clk:>5}")
    ratios = [r["ratio_meas_over_aic"] for r in rows if r["ratio_meas_over_aic"]]
    summary = {"attn": attn, "px": a.px, "rows": rows,
               "ratio_mean": round(statistics.fmean(ratios), 3) if ratios else None,
               "ratio_min": min(ratios) if ratios else None,
               "ratio_max": max(ratios) if ratios else None,
               "clocks_locked": False,
               "note": "unlocked clocks: ratios clock-invariant, absolutes ~fast"}
    json.dump(summary, open(a.out, "w"), indent=1)
    print(f"\nratio range: {summary['ratio_min']}-{summary['ratio_max']} "
          f"(mean {summary['ratio_mean']}) -> {a.out}")


if __name__ == "__main__":
    main()
