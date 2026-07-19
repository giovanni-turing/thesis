#!/usr/bin/env python
"""Dense live ViT f(N), N=1..64, eager + serving-mode (compiled/CUDA-graphs).
GPU venv only (no aiconfigurator). Saves fn_dense_{eager,compiled}.json for the
multi-worker sweep. f(N) is deterministic, so nruns=3/iters=15 is ample."""
import json, statistics
from pathlib import Path
import torch
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel

HERE = Path(__file__).resolve().parent
G, IN_FEATURES = 448 // 16, 3 * 2 * 16 * 16


def measure(model, Ns, nruns=3, iters=15, warm=5):
    cache = {}
    for i, n in enumerate(Ns):
        grid = torch.tensor([[1, G, G]] * n, device="cuda")
        px = torch.randn(G * G * n, IN_FEATURES, device="cuda", dtype=torch.bfloat16)
        means = []
        with torch.no_grad():
            for _ in range(nruns):
                for _ in range(warm):
                    model(px, grid_thw=grid)
                torch.cuda.synchronize()
                t = []
                for _ in range(iters):
                    a, b = torch.cuda.Event(True), torch.cuda.Event(True)
                    a.record(); model(px, grid_thw=grid); b.record()
                    torch.cuda.synchronize(); t.append(a.elapsed_time(b))
                means.append(statistics.fmean(t))
        cache[str(n)] = round(statistics.fmean(means), 3)
        if i % 12 == 0 or n == Ns[-1]:
            print(f"  f(N={n})={cache[str(n)]}  [{i+1}/{len(Ns)}]", flush=True)
    return cache


Ns = list(range(1, 65))
for mode in ("eager", "compiled"):
    p = HERE / f"fn_dense_{mode}.json"
    if p.exists():
        print(f"[{mode}] exists, skip", flush=True); continue
    print(f"=== {mode} ===", flush=True)
    base = Qwen3VLVisionModel.from_pretrained(
        "/home/gio/tese/models/Qwen3-VL-8B-ViT", dtype=torch.bfloat16,
        attn_implementation="sdpa").to("cuda").eval()
    model = torch.compile(base, mode="reduce-overhead") if mode == "compiled" else base
    json.dump(measure(model, Ns), open(p, "w"), indent=1)
    print(f"-> {p}", flush=True)
    del base, model; torch.cuda.empty_cache()
print("DONE", flush=True)
