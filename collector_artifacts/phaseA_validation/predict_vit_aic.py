#!/usr/bin/env python
"""Route B consumer: AIC-predicted ViT forward latency on a collected system.

Prices the full Qwen3-VL encoder phase (vit_ops graph: qkv/attn/proj/ffn GEMMs,
elementwise, projector) through the SDK against collected silicon data.

Run from the aiconfigurator repo root:
    uv run --frozen python predict_vit_aic.py [--system rtx_5090] [--backend vllm]
        [--version 0.22.0] [--model Qwen/Qwen3-VL-8B-Instruct]
        [--sizes 448,896,1344] [--batch 1] [--images 1] [--per-op]
Output: CSV rows on stdout: label,batch,images,total_ms  (+ per-op lines with --per-op)
"""
import argparse

from aiconfigurator.sdk import config as sdk_config
from aiconfigurator.sdk.backends.factory import get_backend
from aiconfigurator.sdk.models import get_model
from aiconfigurator.sdk.perf_database import get_database


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", default="rtx_5090")
    ap.add_argument("--backend", default="vllm")
    ap.add_argument("--version", default="0.22.0")
    ap.add_argument("--model", default="Qwen/Qwen3-VL-8B-Instruct")
    ap.add_argument("--sizes", default="448,896,1344")
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--images", type=int, default=1)
    ap.add_argument("--per-op", action="store_true")
    args = ap.parse_args()

    db = get_database(system=args.system, backend=args.backend, version=args.version)
    model = get_model(args.model, sdk_config.ModelConfig(), args.backend)
    backend = get_backend(args.backend)

    print("label,batch,images,total_ms")
    for px in (int(s) for s in args.sizes.split(",")):
        rc = sdk_config.RuntimeConfig(batch_size=args.batch, isl=1024, osl=128)
        rc.num_images_per_request = args.images
        rc.image_height = px
        rc.image_width = px
        lat, _energy, src, _extra = backend._run_encoder_phase(model, db, rc, batch_size=args.batch)
        print(f"{px}x{px},{args.batch},{args.images},{sum(lat.values()):.4f}")
        if args.per_op:
            for op in sorted(lat, key=lat.get, reverse=True):
                print(f"#   {op}: {lat[op]*1000:.1f} us [{src.get(op)}]")


if __name__ == "__main__":
    main()
