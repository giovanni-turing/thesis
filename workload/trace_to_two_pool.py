#!/usr/bin/env python
"""Phase 1 — Azure LMM inference trace -> two-pool workload converter.

Turns the real bursty Azure multimodal trace
(`data/AzureLMMInferenceTrace_multimodal.csv.gz`, one row per request:
TIMESTAMP, NumImages, ContextTokens, GeneratedTokens) into the mooncake JSONL
that the LLM pool (`dynamo.replay`) consumes, with each request's vision-pool
delay already folded into its LLM-arrival timestamp.

Two pools, one seam
-------------------
DynoSim cannot model a vision encoder (mocker "only simulates text token
processing" — mocker.md Feature Gaps). So the vision stage is simulated here as
a FIFO pool of C encoder workers, and the language stage is left to
`dynamo.replay`. The seam between them is the mooncake trace: an open-loop
request that spends `encoder_delay` in the vision pool is equivalent to the same
request arriving at the LLM pool `encoder_delay` later, so we shift its
`timestamp` forward instead of carrying a separate `tool_wait_ms` field (which
the pinned PyPI `ai-dynamo` wheel predates).

Field semantics (from the dataset card, `data/source/*.md`)
-----------------------------------------------------------
- ContextTokens *already includes* text AND image tokens -> it IS the LLM
  `input_length` directly; no vision-token arithmetic is added here.
- GeneratedTokens -> `output_length`.
- NumImages -> drives the vision pool only.

Encoder cost model
------------------
Per request, one ViT forward over `NumImages` images at a FIXED per-image
resolution (`--image-px`, default 448 -> 784 pre-merge patches / 196 post-merge
tokens per image, matching the phase-9 minimal test and landing on collected
rtx_5090 silicon). Latency comes from AIC's `_run_encoder_phase` and therefore
scales monotonically with `NumImages` (attention batches over the image axis,
GEMMs scale with total patch count). The trace records no per-image size, so a
uniform assumed resolution is the honest choice; it is a single knob to sweep
for sensitivity. Service time is memoized per distinct `NumImages` value (~100
of them), so AIC is queried ~100 times, not once per request.

Caveat: for requests with very many images (NumImages > 64) the ViT attention
batch dimension exceeds the collected batch range (<=64) and AIC extrapolates;
those requests are rare (1-2 rows each) but flagged in the stats.

Run inside the aiconfigurator env (needs the SDK + collected rtx_5090 data):
    cd /home/gio/tese/ai-dynamo/aiconfigurator
    uv run --frozen python /home/gio/tese/workload/trace_to_two_pool.py \
        --out /tmp/azure_two_pool.jsonl --max-requests 2000
"""
from __future__ import annotations

import argparse
import json
import math

import pandas as pd

from aiconfigurator.sdk import config as sdk_config
from aiconfigurator.sdk.backends.factory import get_backend
from aiconfigurator.sdk.models import get_model
from aiconfigurator.sdk.perf_database import get_database

TRACE = "/home/gio/tese/data/AzureLMMInferenceTrace_multimodal.csv.gz"


class EncoderCostModel:
    """AIC-costed ViT forward latency per request, at one fixed image resolution.

    `latency_ms(n)` returns (service_ms, post_merge_vision_tokens) for a request
    carrying `n` images, memoized by `n`. `post_merge_vision_tokens` is AIC's
    view of how many tokens those images inject into the LLM context — logged
    only as a cross-check against the trace's own ContextTokens, never used to
    alter `input_length` (the trace already includes image tokens).
    """

    def __init__(
        self,
        image_px: int,
        *,
        system: str = "rtx_5090",
        backend: str = "vllm",
        version: str = "0.22.0",
        model_name: str = "Qwen/Qwen3-VL-8B-Instruct",
    ) -> None:
        self.image_px = image_px
        self._db = get_database(system=system, backend=backend, version=version)
        self._model = get_model(model_name, sdk_config.ModelConfig(), backend)
        self._backend = get_backend(backend)
        self._cache: dict[int, tuple[float, int]] = {0: (0.0, 0)}

    def latency_ms(self, num_images: int) -> tuple[float, int]:
        num_images = int(num_images)
        if num_images <= 0:
            return 0.0, 0
        hit = self._cache.get(num_images)
        if hit is not None:
            return hit
        rc = sdk_config.RuntimeConfig(batch_size=1, isl=1024, osl=128)
        rc.num_images_per_request = num_images
        rc.image_height = self.image_px
        rc.image_width = self.image_px
        lat, _energy, _source, n_img_post = self._backend._run_encoder_phase(
            self._model, self._db, rc, batch_size=1
        )
        out = (float(sum(lat.values())), int(n_img_post))
        self._cache[num_images] = out
        return out


def load_window(max_requests: int | None, offset: int) -> pd.DataFrame:
    """Load the trace, parse+sort timestamps, and slice a contiguous window."""
    df = pd.read_csv(TRACE)
    # Some timestamps carry 2-digit millis (len 23), most 3 (len 24); normalize.
    ts = df["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
    df["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
    df = df.drop(columns=["TIMESTAMP"]).sort_values("ts").reset_index(drop=True)
    if offset:
        df = df.iloc[offset:].reset_index(drop=True)
    if max_requests is not None:
        df = df.iloc[:max_requests].reset_index(drop=True)
    return df


def percentiles(values: list[float], ps=(50, 90, 99)) -> dict[str, float]:
    if not values:
        return {f"p{p}": 0.0 for p in ps}
    s = sorted(values)
    return {f"p{p}": round(s[min(len(s) - 1, int(len(s) * p / 100))], 3) for p in ps}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="/tmp/azure_two_pool.jsonl", help="mooncake JSONL output")
    ap.add_argument("--stats", default=None, help="optional stats JSON (default: <out>.stats.json)")
    ap.add_argument("--image-px", type=int, default=448, help="assumed per-image square resolution")
    ap.add_argument("--encoder-workers", type=int, default=2, help="FIFO vision-pool worker count")
    ap.add_argument("--trace-block-size", type=int, default=512, help="tokens per hash_id (mooncake)")
    ap.add_argument("--max-requests", type=int, default=None, help="cap request count (window head)")
    ap.add_argument("--offset", type=int, default=0, help="skip this many requests before the window")
    ap.add_argument("--no-encoder-shift", action="store_true",
                    help="LLM-pool isolation: emit raw arrivals (encoder delay forced to 0); "
                         "image/service stats are still reported for reference")
    args = ap.parse_args()

    df = load_window(args.max_requests, args.offset)
    encoder = EncoderCostModel(args.image_px)

    t0 = df["ts"].iloc[0]
    arrivals_ms = (df["ts"] - t0).dt.total_seconds().to_numpy() * 1000.0
    num_images = df["NumImages"].to_numpy()
    context_tokens = df["ContextTokens"].to_numpy()
    generated_tokens = df["GeneratedTokens"].to_numpy()

    workers = [0.0] * args.encoder_workers  # earliest-free time per encoder worker
    rows: list[dict] = []
    enc_delays, enc_service, token_deltas = [], [], []
    n_with_images = n_batch_extrapolated = 0

    for i in range(len(df)):
        arrival = float(arrivals_ms[i])
        n_img = int(num_images[i])
        service_ms, n_img_post = encoder.latency_ms(n_img)

        if n_img > 0:
            n_with_images += 1
            enc_service.append(service_ms)
            if n_img > 64:  # ViT attention batch axis beyond collected range
                n_batch_extrapolated += 1
            # AIC's post-merge vision tokens vs the trace's total context tokens
            token_deltas.append(int(context_tokens[i]) - n_img_post)
            if args.no_encoder_shift:  # LLM-pool isolation: raw arrival
                encoder_delay = 0.0
            else:  # FIFO vision pool: queue wait + service folded into arrival
                w = min(range(len(workers)), key=lambda j: workers[j])
                start = max(arrival, workers[w])
                finish = start + service_ms
                workers[w] = finish
                encoder_delay = finish - arrival
        else:
            encoder_delay = 0.0
        enc_delays.append(encoder_delay)

        input_len = max(1, int(context_tokens[i]))
        output_len = max(1, int(generated_tokens[i]))
        n_blocks = max(1, math.ceil(input_len / args.trace_block_size))
        rows.append({
            "timestamp": round(arrival + encoder_delay, 3),
            "input_length": input_len,
            "output_length": output_len,
            # Disjoint per request: no spurious cross-request prefix reuse.
            "hash_ids": [i * 100_000 + b for b in range(n_blocks)],
        })

    # mooncake replay honors first-turn timestamps -> emit in arrival order.
    rows.sort(key=lambda r: r["timestamp"])
    with open(args.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    horizon_s = (arrivals_ms[-1] - arrivals_ms[0]) / 1000.0 if len(arrivals_ms) > 1 else 0.0
    stats = {
        "requests": len(df),
        "requests_with_images": n_with_images,
        "text_only_fraction": round(1 - n_with_images / len(df), 4),
        "total_images": int(num_images.sum()),
        "image_px": args.image_px,
        "encoder_workers": args.encoder_workers,
        "sim_horizon_s": round(horizon_s, 3),
        "mean_images_per_s": round(int(num_images.sum()) / horizon_s, 3) if horizon_s else 0.0,
        "mean_requests_per_s": round(len(df) / horizon_s, 3) if horizon_s else 0.0,
        "encoder_service_ms": percentiles(enc_service),
        "encoder_delay_ms": {**percentiles(enc_delays), "max": round(max(enc_delays), 3)},
        "requests_batch_extrapolated": n_batch_extrapolated,
        "input_length": {**percentiles([r["input_length"] for r in rows]),
                         "max": max(r["input_length"] for r in rows)},
        "context_minus_aic_vision_tokens": percentiles(token_deltas) if token_deltas else {},
        "distinct_image_counts_costed": len(encoder._cache) - 1,
    }
    stats_path = args.stats or f"{args.out}.stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=1)

    print(f"trace: {args.out} ({len(rows)} requests, horizon {horizon_s:.1f}s)")
    print(f"  {n_with_images} with images ({stats['text_only_fraction']:.0%} text-only), "
          f"{stats['total_images']} images total, {stats['mean_images_per_s']:.1f} img/s mean")
    print(f"  encoder service ms: {stats['encoder_service_ms']}")
    print(f"  encoder delay ms:   {stats['encoder_delay_ms']}")
    if n_batch_extrapolated:
        print(f"  ! {n_batch_extrapolated} requests with >64 images (AIC batch extrapolation)")
    print(f"  stats: {stats_path}")


if __name__ == "__main__":
    main()
