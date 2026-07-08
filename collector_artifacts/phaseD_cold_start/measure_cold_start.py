#!/usr/bin/env python3
"""Phase D — model-side cold start of the encoder worker (RTX 5090).

Measures the wall-clock anatomy of bringing one vision-encoder worker from
"process start" to "serving-ready" on the benchmark node, phase by phase:

  imports        python -> torch + transformers model class imported
  cuda_ctx       first CUDA op (context creation + allocator init)
  load_ckpt      Qwen3VLVisionModel.from_pretrained -> CPU, bf16
                 (1,152,811,416-byte safetensors on local NVMe)
  to_gpu         .to("cuda") weight transfer + sync
  first_forward  N=1 448x448 (784 patches) eager forward (kernel autotune,
                 cuDNN/cuBLAS handle init) + sync
  second_forward steady-state reference (same input) + sync

One trial = one fresh interpreter (run this script once per trial; the
driver below aggregates). Page-cache state is reported per trial via the
`drop_caches_hint` field: trial 1 after boot-ish cache is closest to cold;
repeats are warm-cache. True cold *disk* cost is bounded separately by an
O_DIRECT sequential read of the checkpoint (measure_disk.sh), which
bypasses the page cache without sudo.

Clocks are NOT locked (irrelevant for IO/init wall time; forward times here
are indicative only — the calibrated forward numbers live in Phase B).

Usage:  eda/.venv/bin/python measure_cold_start.py [--out out.json]
"""
import json
import os
import sys
import time

T0 = time.perf_counter()
STAMPS = [("start", T0)]


def stamp(name):
    STAMPS.append((name, time.perf_counter()))


import argparse  # noqa: E402  (stdlib, negligible)

ap = argparse.ArgumentParser()
ap.add_argument("--model-dir", default="/home/gio/tese/models/Qwen3-VL-8B-ViT")
ap.add_argument("--out", default=None)
args = ap.parse_args()

import torch  # noqa: E402
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel  # noqa: E402

stamp("imports")

torch.zeros(1, device="cuda")
torch.cuda.synchronize()
stamp("cuda_ctx")

model = Qwen3VLVisionModel.from_pretrained(args.model_dir, dtype=torch.bfloat16)
model.eval()
stamp("load_ckpt")

model.to("cuda")
torch.cuda.synchronize()
stamp("to_gpu")

PATCH, TEMPORAL = 16, 2
IN_FEATURES = 3 * TEMPORAL * PATCH * PATCH
grid = torch.tensor([[1, 28, 28]], device="cuda")            # 448x448 -> 784 patches
px = torch.randn(784, IN_FEATURES, device="cuda", dtype=torch.bfloat16)
with torch.no_grad():
    model(px, grid_thw=grid)
torch.cuda.synchronize()
stamp("first_forward")

with torch.no_grad():
    model(px, grid_thw=grid)
torch.cuda.synchronize()
stamp("second_forward")

phases, prev = {}, T0
for name, t in STAMPS[1:]:
    phases[name] = round(t - prev, 3)
    prev = t
result = {
    "total_s_to_ready": round(STAMPS[-2][1] - T0, 3),   # through first_forward
    "phases_s": phases,
    "ckpt_bytes": os.path.getsize(os.path.join(args.model_dir, "model.safetensors")),
    "gpu": torch.cuda.get_device_name(0),
    "torch": torch.__version__,
    "pid": os.getpid(),
}
print(json.dumps(result))
if args.out:
    with open(args.out, "a") as f:
        f.write(json.dumps(result) + "\n")
