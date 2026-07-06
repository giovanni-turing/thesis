#!/usr/bin/env python
"""Two-pool minimal test, stage 1: encoder pool (rtx_5090) simulation.

Simulates a FIFO encoder pool of C workers whose per-image service time comes
from AIC's ViT costing on collected rtx_5090 silicon. Emits an agentic_mooncake
JSONL trace where each request's `tool_wait_ms` carries its encoder-pool delay
(queue wait + ViT service), ready for stage 2 (dynamo.replay LLM-pool sim).

Run from the aiconfigurator repo root:
    uv run --frozen python encoder_pool_sim.py --out /tmp/two_pool_trace.jsonl
"""
import argparse
import json

from aiconfigurator.sdk import config as sdk_config
from aiconfigurator.sdk.backends.factory import get_backend
from aiconfigurator.sdk.models import get_model
from aiconfigurator.sdk.perf_database import get_database

VISION_TOKENS_448 = 196  # 448x448 -> 28x28 patches -> /4 merge


def vit_latency_ms(image_px: int) -> float:
    """AIC-predicted ViT forward latency (ms) for one image on rtx_5090."""
    db = get_database(system="rtx_5090", backend="vllm", version="0.22.0")
    model = get_model("Qwen/Qwen3-VL-8B-Instruct", sdk_config.ModelConfig(), "vllm")
    backend = get_backend("vllm")
    rc = sdk_config.RuntimeConfig(batch_size=1, isl=1024, osl=128)
    rc.num_images_per_request = 1
    rc.image_height = image_px
    rc.image_width = image_px
    lat, *_ = backend._run_encoder_phase(model, db, rc, batch_size=1)
    return sum(lat.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/two_pool_trace.jsonl")
    ap.add_argument("--requests", type=int, default=50)
    ap.add_argument("--arrival-interval-ms", type=float, default=20.0)
    ap.add_argument("--encoder-workers", type=int, default=2)
    ap.add_argument("--image-px", type=int, default=448)
    ap.add_argument("--text-tokens", type=int, default=256)
    ap.add_argument("--output-tokens", type=int, default=128)
    args = ap.parse_args()

    service_ms = vit_latency_ms(args.image_px)

    # FIFO queue over C workers: start = max(arrival, earliest-free worker)
    workers = [0.0] * args.encoder_workers
    rows, delays = [], []
    for i in range(args.requests):
        arrival = i * args.arrival_interval_ms
        w = min(range(len(workers)), key=lambda j: workers[j])
        start = max(arrival, workers[w])
        finish = start + service_ms
        workers[w] = finish
        encoder_delay = finish - arrival  # queue wait + service
        delays.append(encoder_delay)

        input_len = args.text_tokens + VISION_TOKENS_448
        n_blocks = (input_len + 511) // 512  # trace-block-size 512
        # Older dynamo.replay wheels lack agentic_mooncake/tool_wait_ms; encode the
        # encoder-pool handoff by shifting the LLM-arrival timestamp instead —
        # semantically identical for an open-loop trace.
        rows.append({
            "timestamp": round(arrival + encoder_delay, 3),
            "input_length": input_len,
            "output_length": args.output_tokens,
            "hash_ids": [i * 100 + b for b in range(n_blocks)],  # unique: no cross-request prefix reuse
        })

    with open(args.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    delays.sort()
    print(f"encoder pool: {args.encoder_workers} workers, service={service_ms:.3f} ms/image")
    print(f"encoder delay ms: p50={delays[len(delays)//2]:.2f} "
          f"p99={delays[int(len(delays)*0.99)]:.2f} max={delays[-1]:.2f}")
    print(f"trace written: {args.out} ({len(rows)} requests, "
          f"input_length={rows[0]['input_length']} = {args.text_tokens} text + {VISION_TOKENS_448} vision)")


if __name__ == "__main__":
    main()
