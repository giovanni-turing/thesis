#!/usr/bin/env python
"""Generality: does the AIC-vs-silicon fidelity hold beyond the trace's 448px?
Measures live ViT f(N) at 224/336/448/672px (eager + torch.compile serving proxy)
on a batch grid, at the locked clock, and compares to AIC(image_px). GPU venv.
Saves fn_multires.json {mode:{px:{N:ms}}}. AIC side computed separately (aic venv).
"""
import json, statistics, subprocess
from pathlib import Path
import torch
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel

HERE = Path(__file__).resolve().parent
PATCH, IN_FEATURES = 16, 3 * 2 * 16 * 16
RES = [224, 336, 448, 672]
GRID_N = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]


def sm():
    try:
        return int(subprocess.run(["nvidia-smi", "--query-gpu=clocks.sm",
            "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.split()[0])
    except Exception:
        return -1


def measure(model, px, n, nruns=3, iters=15, warm=5):
    G = px // PATCH
    grid = torch.tensor([[1, G, G]] * n, device="cuda")
    x = torch.randn(G * G * n, IN_FEATURES, device="cuda", dtype=torch.bfloat16)
    means = []
    with torch.no_grad():
        for _ in range(nruns):
            for _ in range(warm):
                model(x, grid_thw=grid)
            torch.cuda.synchronize()
            t = []
            for _ in range(iters):
                a, b = torch.cuda.Event(True), torch.cuda.Event(True)
                a.record(); model(x, grid_thw=grid); b.record()
                torch.cuda.synchronize(); t.append(a.elapsed_time(b))
            means.append(statistics.fmean(t))
    return round(statistics.fmean(means), 3)


res = {"sm_mhz": sm(), "grid_n": GRID_N, "res": RES}
for mode in ("eager", "compiled"):
    print(f"=== {mode} @ SM {sm()} ===", flush=True)
    base = Qwen3VLVisionModel.from_pretrained(
        "/home/gio/tese/models/Qwen3-VL-8B-ViT", dtype=torch.bfloat16,
        attn_implementation="sdpa").to("cuda").eval()
    model = torch.compile(base, mode="reduce-overhead") if mode == "compiled" else base
    res[mode] = {}
    for px in RES:
        res[mode][str(px)] = {}
        for n in GRID_N:
            res[mode][str(px)][str(n)] = measure(model, px, n)
        print(f"  px={px}: f(64)={res[mode][str(px)]['64']} ms", flush=True)
        json.dump(res, open(HERE / "fn_multires.json", "w"), indent=1)
    del base, model; torch.cuda.empty_cache()
print("DONE -> fn_multires.json", flush=True)
