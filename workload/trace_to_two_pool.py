#!/usr/bin/env python
"""Phase 1+2.2 — Azure LMM inference trace -> two-pool workload converter.

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
the pinned PyPI `ai-dynamo` wheel predates). With `--no-encoder-shift` the
emitted timestamps are the raw (speedup-compressed) arrivals — LLM-pool
isolation — but the vision pool is STILL simulated so the stats/series describe
the same hypothetical encoder pool in both modes; only the emission differs
(`encoder_shift_applied` in the stats records which one you got).

Field semantics (from the dataset card, `data/source/*.md`)
-----------------------------------------------------------
- ContextTokens *already includes* text AND image tokens -> it IS the LLM
  `input_length` directly; no vision-token arithmetic is added here.
- GeneratedTokens -> `output_length`.
- NumImages -> drives the vision pool only.

Encoder cost model (probe-backed)
---------------------------------
Latency comes from AIC's `_run_encoder_phase` (rtx_5090 / vLLM 0.22.0,
Qwen3-VL-8B) at a FIXED per-image resolution (`--image-px`, default 448 -> 784
pre-merge patches / 196 post-merge tokens per image). Probe (this file's
authoring, deltas printed by `_run_encoder_phase` directly): the predicted
latency is EXACTLY a function of total images — (batch_size=1, num_images=N)
== (batch_size=k, num_images=N/k) for every split tried, e.g. all of
(1,64)/(2,32)/(4,16)/(8,8)/(64,1) = 314.498 ms; N=8 -> 44.105 ms and N=32 ->
160.701 ms at every factoring (delta +0.000000 ms). Source-level reason: ViT
attention is queried with eff_batch = batch_size*num_images (varlen over the
image axis) and every other op with x = total patch/token count, so each term
depends only on the product. Service time is therefore memoized by TOTAL image
count per forward. Anchors: f(1)=7.822 ms, f(64)=314.498 ms -> 4.91 ms/img
amortized at full batch vs 7.82 solo (~1.6x throughput), i.e. ~2.9 ms fixed
per-forward overhead that batching amortizes.

Fixed 448² rationale: the trace records no per-image sizes, so a uniform
assumed resolution is the honest choice (a documented knob to sweep), not an
invented size distribution. Per Result B (progress/phase2-simulation.md) AIC
under-predicts comparable measured ViT work by ~1.14x at 448² — a bounded,
conservative bias for the decoupling argument.

Cross-request encoder batching
------------------------------
The pool is event-driven: when a worker frees, it greedily takes WHOLE queued
requests from the FIFO head while their summed image count stays within
`--encoder-batch-images` (default 64 = the collected batch range, so no AIC
batch-axis extrapolation), and runs them as ONE ViT forward costed at the batch
total. A request larger than the remaining room waits for the next batch —
FIFO admission order is exact, so no starvation: the head request always enters
first. An oversized single request (> cap; the trace maxes at 9409 images) gets
a batch of its own, chunked into sequential <=cap forwards on that ONE worker
(e.g. 9409 -> 147 x f(64) + f(1) ≈ 46.2 s); `requests_chunked` counts these.
A request's encoder finish = its batch's finish. No coalescing wait is added:
under low load a lone request dispatches immediately (batch of 1), reproducing
the old per-request-forward behavior.

Handoff-transfer bound
----------------------
After encoder service, the post-merge vision embeddings cross to the LLM pool:
bytes = post_merge_tokens x 4096 (Qwen3-VL projector/LLM hidden) x 2 (bf16);
transfer_ms = --handoff-rtt-ms (default 0.2) + bytes / (--handoff-gbps line
rate, default 25 -> bytes/s = gbps*1e9/8). Per image at 448²: 196 x 4096 x 2 B
≈ 1.6 MB -> ~0.51 ms at 25 Gbps, ~0.71 ms with RTT. The transfer is added to
the request's `encoder_delay` but does NOT occupy the worker (async DMA/NIC
behind the compute stream): optimistic for encoder throughput, conservative
for request latency. `--handoff-gbps 0` disables the term (old behavior).
Sizing uses AIC's post-merge token count for the request's own image count
(n_img_post is exactly tokens_per_image x n in the SDK, so it is derived from
the memoized 1-image query).

Arrival speedup
---------------
`--arrival-speedup S` divides every inter-arrival gap by S BEFORE the encoder
sim (arrivals_ms /= S), compressing the offered load; the emitted mooncake
timestamps are the compressed ones and the stats record S. This is the load
knob the Phase-2.3 sweep driver turns to find each pool's saturation knee.

Per-second series (`--series-out`)
----------------------------------
Optional vision-pool time series JSON, one entry per second of the compressed
clock relative to the first arrival: images arrived / completed in that second
and queue depth (images) / busy workers at the second's end. The stats also
gain `encoder_utilization` (busy worker-ms over workers x horizon incl. drain
tail), `offered_img_per_s`, and `queue_divergent` (queue at the END OF
ARRIVALS > 10x max(1, median-to-that-point) — backlog outgrew steady state:
past the saturation knee; the drain tail is excluded because a finite window
always drains to 0 eventually).

Run inside the aiconfigurator env (needs the SDK + collected rtx_5090 data):
    cd /home/gio/tese/ai-dynamo/aiconfigurator
    .venv/bin/python /home/gio/tese/workload/trace_to_two_pool.py \
        --out /tmp/azure_two_pool.jsonl --max-requests 2000
"""
from __future__ import annotations

import argparse
import json
import os
import math
from collections import deque

import pandas as pd

from aiconfigurator.sdk import config as sdk_config
from aiconfigurator.sdk.backends.factory import get_backend
from aiconfigurator.sdk.models import get_model
from aiconfigurator.sdk.perf_database import get_database

# Portable: TESE_TRACE overrides; else TESE_ROOT/data/...; else repo root
# inferred from this file (workload/ -> parents[1]).
_ROOT = os.environ.get("TESE_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.environ.get("TESE_TRACE",
    os.path.join(_ROOT, "data/AzureLMMInferenceTrace_multimodal.csv.gz"))
LLM_HIDDEN = 4096  # Qwen3-VL-8B projector output / LLM hidden size
BYTES_PER_ELEM = 2  # bf16 embeddings on the wire


class EncoderCostModel:
    """AIC-costed ViT forward latency, at one fixed image resolution.

    `latency_ms(total_images)` returns (service_ms, post_merge_vision_tokens)
    for ONE forward over `total_images` images, memoized by that total — valid
    because the probe showed AIC's prediction depends only on the product
    batch_size x num_images (see module docstring), so a cross-request batch of
    T images is costed as (batch_size=1, num_images=T).
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
        self.memo_hits = 0
        self._tokens_per_image: int | None = None

    def latency_ms(self, total_images: int) -> tuple[float, int]:
        total_images = int(total_images)
        if total_images <= 0:
            return 0.0, 0
        hit = self._cache.get(total_images)
        if hit is not None:
            self.memo_hits += 1
            return hit
        rc = sdk_config.RuntimeConfig(batch_size=1, isl=1024, osl=128)
        rc.num_images_per_request = total_images
        rc.image_height = self.image_px
        rc.image_width = self.image_px
        lat, _energy, _source, n_img_post = self._backend._run_encoder_phase(
            self._model, self._db, rc, batch_size=1
        )
        out = (float(sum(lat.values())), int(n_img_post))
        self._cache[total_images] = out
        return out

    @property
    def tokens_per_image(self) -> int:
        """Post-merge vision tokens per image (196 at 448²); n_img_post is
        exactly tokens_per_image x num_images in the SDK, so one 1-image query
        sizes every request without extrapolated large-count queries."""
        if self._tokens_per_image is None:
            _, post_1 = self.latency_ms(1)
            self._tokens_per_image = int(post_1)
        return self._tokens_per_image

    def post_merge_tokens(self, num_images: int) -> int:
        return self.tokens_per_image * max(0, int(num_images))

    def chunked_service_ms(self, num_images: int, cap: int) -> float:
        """Service for one request run alone: sequential <=cap forwards."""
        full, rem = divmod(int(num_images), cap)
        total = full * self.latency_ms(cap)[0] if full else 0.0
        if rem:
            total += self.latency_ms(rem)[0]
        return total

    @property
    def distinct_sizes_costed(self) -> int:
        return len(self._cache) - 1  # minus the 0-image sentinel


def build_slot_windows(
    schedule: list[tuple[float, int]],  # (step_ms, capacity), step 0 first, sorted
) -> list[list[tuple[float, float]]]:
    """Piecewise-constant capacity schedule -> per-slot active windows.

    Slots activate lowest-index-first on scale-up and retire LIFO
    (highest-index-first) on scale-down, so a scale-down followed by a
    scale-up reuses the highest slot indices. Returns, per slot, a sorted
    list of [activate_ms, deactivate_ms) windows (last window open-ended
    at +inf)."""
    max_cap = max(c for _, c in schedule)
    windows: list[list[tuple[float, float]]] = [[] for _ in range(max_cap)]
    open_since: list[float | None] = [None] * max_cap
    active = 0
    for t, cap_now in schedule:
        if cap_now > active:
            for w in range(active, cap_now):
                open_since[w] = t
        elif cap_now < active:
            for w in range(cap_now, active):
                windows[w].append((open_since[w], t))
                open_since[w] = None
        active = cap_now
    for w in range(max_cap):
        if open_since[w] is not None:
            windows[w].append((open_since[w], float("inf")))
    return windows


def simulate_vision_pool(
    reqs: list[tuple[float, int, int]],  # (arrival_ms, request_index, num_images), FIFO order
    n_workers: int,
    cap: int,
    encoder: EncoderCostModel,
    parallel_chunks: bool = True,
    worker_schedule: list[tuple[float, int]] | None = None,
) -> tuple[dict[int, float], list[tuple[float, float, int, int]], int]:
    """Event-driven FIFO pool with greedy whole-request batching.

    Oversized requests (> cap images) are chunked into <=cap-image forwards.
    With parallel_chunks=True (default, Phase-3 policy) each chunk is an
    independent FIFO dispatch unit, so multiple free workers drain one
    oversized request concurrently — physically valid because images are
    independent in the encoder and cost is exactly f(total images); chunks
    are never batched with other requests. With parallel_chunks=False the
    request's chunks run sequentially on ONE worker (the Phase-2 policy,
    kept for reproducibility of the earlier knee results): that policy
    gives large requests an intrinsic multi-second service floor that no
    worker count removes. A request finishes when its LAST unit finishes.

    worker_schedule (Phase 4.3/3.2 autoscaling hook): piecewise-constant
    capacity steps [(t_ms, workers), ...] relative to the window start,
    first step at t=0. Semantics: a forward may START on a slot only
    inside one of that slot's active windows; in-flight forwards run to
    completion past a deactivation (drain, no preemption). Cold-start
    lead belongs to the CONTROLLER: a scale-up decided at t must appear
    in the schedule at t + lead. When None, capacity is n_workers
    throughout (the static behavior, bit-identical to before).

    Returns (finish_ms by request index,
             batches as (start_ms, finish_ms, total_images, n_forwards),
             requests_chunked).
    """
    # Decompose requests into dispatch units: (arrival, idx, n_img, is_chunk).
    units: list[tuple[float, int, int, bool]] = []
    requests_chunked = 0
    for arr, idx, n in reqs:
        if n > cap and parallel_chunks:
            requests_chunked += 1
            full, rem = divmod(n, cap)
            units.extend((arr, idx, cap, True) for _ in range(full))
            if rem:
                units.append((arr, idx, rem, True))
        else:
            if n > cap:
                requests_chunked += 1
            units.append((arr, idx, n, False))

    finish: dict[int, float] = {}
    batches: list[tuple[float, float, int, int]] = []
    if worker_schedule is None:
        slot_windows = [[(0.0, float("inf"))] for _ in range(n_workers)]
    else:
        slot_windows = build_slot_windows(worker_schedule)
    n_slots = len(slot_windows)
    worker_free = [0.0] * n_slots

    def earliest_start(w: int, lower: float) -> float:
        """Earliest time slot w may START a forward at/after `lower`."""
        s = max(worker_free[w], lower)
        for a, d in slot_windows[w]:
            if s < a:
                s = a
            if s < d:
                return s
        return float("inf")

    queue: deque[tuple[float, int, int, bool]] = deque()
    i = 0

    while i < len(units) or queue:
        if not queue:  # idle pool: wait for the next arrival
            queue.append(units[i])
            i += 1
        head_arrival = queue[0][0]
        w = min(range(n_slots), key=lambda k: (earliest_start(k, head_arrival), k))
        start = earliest_start(w, head_arrival)
        assert start != float("inf"), (
            "worker schedule leaves the pool at zero capacity forever with "
            "work still queued — schedules must keep at least one eventual slot")
        # Everything that has arrived by the batch start is eligible, FIFO.
        while i < len(units) and units[i][0] <= start:
            queue.append(units[i])
            i += 1
        head = queue.popleft()
        members = [head]
        total = head[2]
        if head[3]:  # chunk of an oversized request: one forward, never batched
            n_forwards = 1
            service = encoder.latency_ms(total)[0]
        elif total > cap:  # oversized, sequential policy: own batch, chained chunks
            n_forwards = math.ceil(total / cap)
            service = encoder.chunked_service_ms(total, cap)
        else:
            while queue and not queue[0][3] and total + queue[0][2] <= cap:
                u = queue.popleft()
                members.append(u)
                total += u[2]
            n_forwards = 1
            service = encoder.latency_ms(total)[0]
        fin = start + service
        worker_free[w] = fin
        batches.append((start, fin, total, n_forwards))
        for arr, idx, _n, _c in members:
            assert fin >= arr, "request finished before it arrived"
            finish[idx] = max(finish.get(idx, 0.0), fin)
    return finish, batches, requests_chunked


def build_series(
    reqs: list[tuple[float, int, int]],
    batches: list[tuple[float, float, int, int]],
    t_end_ms: float,
) -> list[dict]:
    """Per-second vision-pool series on the compressed clock (t=0 at first arrival)."""
    ARR, FIN, START = 0, 1, 2  # tie order keeps queue >= 0 and busy <= workers
    events: list[tuple[float, int, int]] = []
    for arr, _idx, n in reqs:
        events.append((arr, ARR, n))
    for start, fin, total, _nf in batches:
        events.append((start, START, total))
        events.append((fin, FIN, total))
    events.sort(key=lambda e: (e[0], e[1]))

    n_sec = int(t_end_ms // 1000) + 1 if t_end_ms > 0 else 1
    series: list[dict] = []
    queue_imgs = busy = 0
    e = 0
    for t in range(n_sec):
        boundary = (t + 1) * 1000.0
        arrived = completed = 0
        while e < len(events) and events[e][0] < boundary:
            _tm, kind, qty = events[e]
            if kind == ARR:
                queue_imgs += qty
                arrived += qty
            elif kind == START:
                queue_imgs -= qty
                busy += 1
            else:  # FIN
                busy -= 1
                completed += qty
            e += 1
        assert queue_imgs >= 0 and busy >= 0
        series.append({
            "t": t,
            "img_arrived": arrived,
            "img_completed": completed,
            "queue_imgs_end": queue_imgs,
            "busy_workers_end": busy,
        })
    return series


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
    ap.add_argument("--encoder-batch-images", type=int, default=64,
                    help="max images per ViT forward (cross-request batch cap; 64 = collected "
                         "batch range). Oversized single requests are chunked to <=cap forwards")
    ap.add_argument("--handoff-rtt-ms", type=float, default=0.2,
                    help="fixed per-request encoder->LLM handoff latency (ms)")
    ap.add_argument("--handoff-gbps", type=float, default=25.0,
                    help="encoder->LLM link rate for post-merge embeddings (Gbps line rate); "
                         "0 disables the handoff term entirely")
    ap.add_argument("--arrival-speedup", type=float, default=1.0,
                    help="divide all inter-arrival gaps by this factor before the encoder sim "
                         "(compresses offered load; emitted timestamps are the compressed ones)")
    ap.add_argument("--series-out", default=None,
                    help="optional per-second vision-pool series JSON (arrivals/completions/"
                         "queue depth/busy workers on the compressed clock)")
    ap.add_argument("--trace-block-size", type=int, default=512, help="tokens per hash_id (mooncake)")
    ap.add_argument("--max-requests", type=int, default=None, help="cap request count (window head)")
    ap.add_argument("--offset", type=int, default=0, help="skip this many requests before the window")
    ap.add_argument("--worker-schedule", default=None,
                    help="JSON file: [[t_seconds, workers], ...] piecewise-constant "
                         "encoder capacity relative to window start (first step at "
                         "t=0). Overrides --encoder-workers as the capacity over "
                         "time; cold-start lead must already be applied by the "
                         "schedule's author. Slots retire LIFO and drain in-flight "
                         "forwards (no preemption)")
    ap.add_argument("--sequential-chunks", action="store_true",
                    help="restore the Phase-2 dispatch policy (an oversized request's "
                         "chunks run sequentially on one worker) instead of the default "
                         "parallel chunk dispatch across free workers")
    ap.add_argument("--batches-out", default=None,
                    help="optional dispatch-log dump: JSONL, one dispatched encoder batch "
                         "per line as [start_ms, finish_ms, total_images, n_forwards] in "
                         "dispatch order, plus a companion <path>.reqs.json with the "
                         "image-bearing arrival list [[arrival_ms, req_index, n_images], ...]. "
                         "Read-only side effect: nothing else in the run changes")
    ap.add_argument("--no-encoder-shift", action="store_true",
                    help="LLM-pool isolation: emit raw (speedup-compressed) arrivals — encoder "
                         "delay is NOT folded in; the vision pool is still simulated so stats/"
                         "series stay comparable across modes")
    args = ap.parse_args()
    if args.arrival_speedup <= 0:
        ap.error("--arrival-speedup must be > 0")
    if args.encoder_workers < 1 or args.encoder_batch_images < 1:
        ap.error("--encoder-workers and --encoder-batch-images must be >= 1")

    df = load_window(args.max_requests, args.offset)
    encoder = EncoderCostModel(args.image_px)
    cap = args.encoder_batch_images

    t0 = df["ts"].iloc[0]
    arrivals_ms = (df["ts"] - t0).dt.total_seconds().to_numpy() * 1000.0
    arrivals_ms /= args.arrival_speedup  # compress offered load BEFORE the encoder sim
    num_images = df["NumImages"].to_numpy()
    context_tokens = df["ContextTokens"].to_numpy()
    generated_tokens = df["GeneratedTokens"].to_numpy()

    # ---- vision pool: event-driven FIFO with cross-request batching ----
    img_reqs = [(float(arrivals_ms[i]), i, int(num_images[i]))
                for i in range(len(df)) if int(num_images[i]) > 0]
    schedule = None
    if args.worker_schedule:
        raw = json.load(open(args.worker_schedule))
        schedule = sorted((float(t) * 1000.0, int(c)) for t, c in raw)
        if not schedule or schedule[0][0] != 0.0:
            ap.error("--worker-schedule must start with a step at t=0")
    finish, batches, requests_chunked = simulate_vision_pool(
        img_reqs, args.encoder_workers, cap, encoder,
        parallel_chunks=not args.sequential_chunks,
        worker_schedule=schedule)

    # Dispatch-log dump (opt-in, read-only): the exact batch sequence this arm
    # dispatched, for physical replay on real silicon. Written before anything
    # else so a dump is available even if downstream emission fails.
    if args.batches_out:
        with open(args.batches_out, "w") as bf:
            for start, fin, total, n_fwd in batches:
                bf.write(f"[{start!r}, {fin!r}, {total}, {n_fwd}]\n")
        with open(f"{args.batches_out}.reqs.json", "w") as rf:
            json.dump({"n_all_requests": len(df),
                       "cap": cap,
                       "handoff_rtt_ms": args.handoff_rtt_ms,
                       "handoff_gbps": args.handoff_gbps,
                       "reqs": [[a, i, n] for a, i, n in img_reqs]}, rf)

    # Handoff bound: post-merge embeddings cross pools (async; not worker time).
    def handoff_ms(n_img: int) -> float:
        if args.handoff_gbps <= 0 or n_img <= 0:
            return 0.0
        n_bytes = encoder.post_merge_tokens(n_img) * LLM_HIDDEN * BYTES_PER_ELEM
        return args.handoff_rtt_ms + n_bytes / (args.handoff_gbps * 1e9 / 8) * 1e3

    rows: list[dict] = []
    enc_delays, enc_service, handoffs, token_deltas = [], [], [], []
    for i in range(len(df)):
        arrival = float(arrivals_ms[i])
        n_img = int(num_images[i])
        if n_img > 0:
            enc_service.append(encoder.chunked_service_ms(n_img, cap))  # standalone reference
            token_deltas.append(int(context_tokens[i]) - encoder.post_merge_tokens(n_img))
            h = handoff_ms(n_img)
            handoffs.append(h)
            encoder_delay = (finish[i] - arrival) + h
        else:
            encoder_delay = 0.0
        enc_delays.append(encoder_delay)
        emitted_delay = 0.0 if args.no_encoder_shift else encoder_delay

        input_len = max(1, int(context_tokens[i]))
        output_len = max(1, int(generated_tokens[i]))
        n_blocks = max(1, math.ceil(input_len / args.trace_block_size))
        rows.append({
            "timestamp": round(arrival + emitted_delay, 3),
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

    # ---- series + pool-level stats (always computed; file only on request) ----
    horizon_s = (arrivals_ms[-1] - arrivals_ms[0]) / 1000.0 if len(arrivals_ms) > 1 else 0.0
    last_finish = max((b[1] for b in batches), default=0.0)
    t_end_ms = max(float(arrivals_ms[-1]) if len(arrivals_ms) else 0.0, last_finish)
    series = build_series(img_reqs, batches, t_end_ms)
    busy_ms = sum(fin - start for start, fin, _t, _nf in batches)
    if schedule is None:
        provisioned_ms = args.encoder_workers * t_end_ms
    else:  # integrate the piecewise-constant capacity up to the sim end
        provisioned_ms = 0.0
        for (t0, c0), (t1, _c1) in zip(schedule, schedule[1:]):
            provisioned_ms += c0 * max(0.0, min(t1, t_end_ms) - min(t0, t_end_ms))
        provisioned_ms += schedule[-1][1] * max(0.0, t_end_ms - schedule[-1][0])
    utilization = busy_ms / provisioned_ms if provisioned_ms > 0 else 0.0
    # Divergence is judged at the END OF ARRIVALS (the series itself runs through
    # the drain tail, where a finite window's queue always returns to 0).
    arr_end_sec = min(len(series) - 1, int(arrivals_ms[-1] // 1000)) if len(series) else 0
    q_to_arr_end = [s["queue_imgs_end"] for s in series[: arr_end_sec + 1]]
    q_median = sorted(q_to_arr_end)[len(q_to_arr_end) // 2] if q_to_arr_end else 0
    q_at_arrival_end = q_to_arr_end[-1] if q_to_arr_end else 0
    queue_divergent = bool(q_at_arrival_end > 10 * max(1, q_median))
    total_images = int(num_images.sum())
    n_with_images = len(img_reqs)

    if args.series_out:
        with open(args.series_out, "w") as f:
            json.dump({"freq_s": 1, "arrival_speedup": args.arrival_speedup,
                       "series": series}, f)

    stats = {
        "requests": len(df),
        "requests_with_images": n_with_images,
        "text_only_fraction": round(1 - n_with_images / len(df), 4),
        "total_images": total_images,
        "image_px": args.image_px,
        "encoder_workers": args.encoder_workers,
        "encoder_batch_images": cap,
        "chunk_dispatch": "sequential" if args.sequential_chunks else "parallel",
        "worker_schedule": (None if schedule is None else {
            "steps": len(schedule),
            "min_workers": min(c for _, c in schedule),
            "max_workers": max(c for _, c in schedule),
            "provisioned_worker_seconds": round(provisioned_ms / 1000.0, 1),
        }),
        "provisioned_worker_seconds": round(provisioned_ms / 1000.0, 1),
        "busy_worker_seconds": round(busy_ms / 1000.0, 1),
        "arrival_speedup": args.arrival_speedup,
        "handoff_rtt_ms": args.handoff_rtt_ms,
        "handoff_gbps": args.handoff_gbps,
        "encoder_shift_applied": not args.no_encoder_shift,
        "sim_horizon_s": round(horizon_s, 3),
        "vision_sim_end_s": round(t_end_ms / 1000.0, 3),  # incl. drain tail
        "mean_images_per_s": round(total_images / horizon_s, 3) if horizon_s else 0.0,
        "offered_img_per_s": round(total_images / horizon_s, 3) if horizon_s else 0.0,
        "mean_requests_per_s": round(len(df) / horizon_s, 3) if horizon_s else 0.0,
        "encoder_service_ms": percentiles(enc_service),  # per-request standalone (chunk-aware)
        "encoder_batch_service_ms": {  # per dispatched batch (the actual forwards)
            **percentiles([fin - start for start, fin, _t, _nf in batches]),
            "max": round(max((fin - start for start, fin, _t, _nf in batches), default=0.0), 3),
        },
        "encoder_delay_ms": {**percentiles(enc_delays), "max": round(max(enc_delays), 3)},
        # week-wide SLO-violation counts: how many of ALL requests had encoder delay > T ms
        "encoder_delay_violations": {
            str(T): int(sum(1 for d in enc_delays if d > T)) for T in (250, 500, 1000, 2000, 5000)},
        "encoder_delay_violation_frac": {
            str(T): round(sum(1 for d in enc_delays if d > T) / len(enc_delays), 6)
            for T in (250, 500, 1000, 2000, 5000)} if enc_delays else {},
        "handoff_ms": {**percentiles(handoffs),
                       "max": round(max(handoffs), 3) if handoffs else 0.0},
        "encoder_utilization": round(utilization, 4),
        "queue_imgs_at_arrival_end": q_at_arrival_end,
        "queue_divergent": queue_divergent,
        "batches": len(batches),
        "encoder_forwards": sum(nf for _s, _f, _t, nf in batches),
        "images_per_batch": percentiles([t for _s, _f, t, _nf in batches]),
        "requests_chunked": requests_chunked,
        "service_memo_hits": encoder.memo_hits,
        "distinct_service_sizes_costed": encoder.distinct_sizes_costed,
        "input_length": {**percentiles([r["input_length"] for r in rows]),
                         "max": max(r["input_length"] for r in rows)},
        "context_minus_aic_vision_tokens": percentiles(token_deltas) if token_deltas else {},
    }
    stats_path = args.stats or f"{args.out}.stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=1)

    print(f"trace: {args.out} ({len(rows)} requests, horizon {horizon_s:.1f}s, "
          f"speedup x{args.arrival_speedup:g}"
          f"{', ISOLATION (no encoder shift)' if args.no_encoder_shift else ''})")
    print(f"  {n_with_images} with images ({stats['text_only_fraction']:.0%} text-only), "
          f"{total_images} images total, {stats['offered_img_per_s']:.1f} img/s offered")
    print(f"  vision pool: {len(batches)} batches / {stats['encoder_forwards']} forwards "
          f"(cap {cap} img), {requests_chunked} chunked oversized, "
          f"memo {encoder.memo_hits} hits / {encoder.distinct_sizes_costed} AIC sizes")
    print(f"  encoder service ms (standalone): {stats['encoder_service_ms']}")
    print(f"  encoder delay ms (queue+service+handoff): {stats['encoder_delay_ms']}")
    print(f"  handoff ms: {stats['handoff_ms']}")
    print(f"  utilization {utilization:.1%} over {stats['vision_sim_end_s']:.1f}s"
          f"{'  !! QUEUE DIVERGENT' if queue_divergent else ''}")
    if args.series_out:
        print(f"  series: {args.series_out} ({len(series)} x 1s)")
    print(f"  stats: {stats_path}")


if __name__ == "__main__":
    main()
