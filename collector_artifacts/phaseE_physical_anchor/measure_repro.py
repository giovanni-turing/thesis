#!/usr/bin/env python
"""Fresh f(N) reproduction at the now-LOCKED clock, with per-N SM-clock logging.
Confirms the banked 2400 MHz curves (merged_sdpa.csv, vit_compile_dense.json)
reproduce, validating the clock lock + measurement pipeline. GPU venv.
Saves fn_repro.json: {mode: {N: {ms, ci95, sm_mhz}}}.
"""
import json, statistics, subprocess
from pathlib import Path
import torch
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel

HERE = Path(__file__).resolve().parent
G, IN_FEATURES = 448 // 16, 3 * 2 * 16 * 16


def sm():
    try:
        return int(subprocess.run(["nvidia-smi", "--query-gpu=clocks.sm",
            "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.split()[0])
    except Exception:
        return -1


def measure(model, Ns, nruns=5, iters=20, warm=6):
    out = {}
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
        m = statistics.fmean(means)
        ci = 1.96 * (statistics.pstdev(means) / len(means) ** 0.5) if len(means) > 1 else 0.0
        out[str(n)] = {"ms": round(m, 3), "ci95": round(ci, 3), "sm_mhz": sm()}
        if i % 12 == 0 or n == Ns[-1]:
            print(f"  {list(out)[-1]}: {out[str(n)]}  [{i+1}/{len(Ns)}]", flush=True)
    return out


Ns = list(range(1, 65))
res = {}
for mode in ("eager", "compiled"):
    print(f"=== {mode} @ SM {sm()} MHz ===", flush=True)
    base = Qwen3VLVisionModel.from_pretrained(
        "/home/gio/tese/models/Qwen3-VL-8B-ViT", dtype=torch.bfloat16,
        attn_implementation="sdpa").to("cuda").eval()
    model = torch.compile(base, mode="reduce-overhead") if mode == "compiled" else base
    res[mode] = measure(model, Ns)
    json.dump(res, open(HERE / "fn_repro.json", "w"), indent=1)
    del base, model; torch.cuda.empty_cache()
print("DONE -> fn_repro.json", flush=True)
