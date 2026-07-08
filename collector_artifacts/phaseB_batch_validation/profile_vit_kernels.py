#!/usr/bin/env python
"""Phase B follow-up #1: kernel-level ledger of the ViT forward at N images.

torch.profiler over the extracted tower (same harness family as the
chapter's N=1 ledger), CUDA kernel self-time aggregated into operator
categories by kernel-name patterns. Run at N=1 and N=64 to attribute the
measured/AIC ratio GROWTH term-by-term: categories that scale linearly
with N but are absent from AIC's operator graph (patch-embed conv,
DeepStack gather/cat, unfused elementwise) are the growth's suspects.

Run (eda venv, locked clocks, GPU free):
  .../eda/.venv/bin/python profile_vit_kernels.py --n 1 64
Output: kernel_ledger_N{n}.json per N + a printed category table.
"""
import argparse
import json
import os
import re

import torch
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel

PATCH, TEMPORAL, GRID = 16, 2, 28
IN_FEATURES = 3 * TEMPORAL * PATCH * PATCH

CATEGORIES = [  # first match wins
    ("attention", re.compile(r"flash|fmha|attn", re.I)),
    ("patch_embed_conv", re.compile(r"conv|cudnn|winograd|implicit", re.I)),
    ("gemm", re.compile(r"gemm|cutlass|nvjet|matmul|s16816|hmma|wgmma", re.I)),
    ("norm", re.compile(r"norm", re.I)),
    ("gather_cat", re.compile(r"cat_|catarray|gather|index_select|scatter", re.I)),
    ("elementwise", re.compile(r"elementwise|vectorized|gelu|silu|act|add|mul|copy", re.I)),
]


def categorize(name: str) -> str:
    for cat, pat in CATEGORIES:
        if pat.search(name):
            return cat
    return "other"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="/home/gio/tese/models/Qwen3-VL-8B-ViT")
    ap.add_argument("--n", type=int, nargs="+", default=[1, 64])
    ap.add_argument("--attn", default="sdpa")
    args = ap.parse_args()

    model = Qwen3VLVisionModel.from_pretrained(
        args.model_dir, dtype=torch.bfloat16, attn_implementation=args.attn
    ).cuda().eval()
    out_dir = os.path.dirname(os.path.abspath(__file__))

    for n in args.n:
        grid = torch.tensor([[1, GRID, GRID]] * n, device="cuda")
        px = torch.randn(GRID * GRID * n, IN_FEATURES, device="cuda",
                         dtype=torch.bfloat16)
        with torch.no_grad():
            for _ in range(5):
                model(px, grid_thw=grid)
            torch.cuda.synchronize()
            with torch.profiler.profile(
                activities=[torch.profiler.ProfilerActivity.CUDA],
                schedule=torch.profiler.schedule(wait=1, warmup=2, active=5),
            ) as prof:
                for _ in range(8):
                    model(px, grid_thw=grid)
                    torch.cuda.synchronize()
                    prof.step()

        cats: dict[str, float] = {}
        kernels: dict[str, float] = {}
        for evt in prof.key_averages():
            t = evt.self_device_time_total  # us, summed over 5 active steps
            if t <= 0 or evt.key.startswith(("cudaLaunch", "cudaDevice", "Memcpy")):
                continue
            ms = t / 1000.0 / 5.0  # per-forward
            kernels[evt.key] = kernels.get(evt.key, 0.0) + ms
            cats[categorize(evt.key)] = cats.get(categorize(evt.key), 0.0) + ms

        total = sum(cats.values())
        rec = {"n_images": n, "total_kernel_ms": round(total, 3),
               "categories_ms": {k: round(v, 3) for k, v in
                                 sorted(cats.items(), key=lambda kv: -kv[1])},
               "top_kernels": {k: round(v, 3) for k, v in
                               sorted(kernels.items(), key=lambda kv: -kv[1])[:15]}}
        path = os.path.join(out_dir, f"kernel_ledger_N{n}.json")
        json.dump(rec, open(path, "w"), indent=1)
        print(f"N={n}: kernel total {total:.2f} ms")
        for k, v in rec["categories_ms"].items():
            print(f"   {k:>18s}: {v:8.3f} ms  ({100*v/total:4.1f}%)")


if __name__ == "__main__":
    main()
