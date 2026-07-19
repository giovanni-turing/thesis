#!/usr/bin/env python
"""One-real-encoder end-to-end anchor across all six burst windows.

For each burst window we replay its actual image-arrival schedule through the
1-worker FIFO encoder pool (faithful port of the two-pool converter: greedy
whole-request batching to the 64-image cap), where the per-batch service time
is the LIVE Qwen3-VL vision-tower forward measured on THIS GPU. Two execution
modes are measured:
  - eager     : HuggingFace transformers eager (the ~1.4x-slow stack)
  - compiled  : torch.compile reduce-overhead (CUDA graphs) == the vLLM
                serving path AIC composes against
Each is compared to the AIC-simulated encoder-delay distribution per window.
This is the encoder-pool equivalent of the live LLM control-loop anchor and
the "one real encoder serving a burst replay end to end" of the conclusion.

Writes incrementally to burst_anchor_all.json (partial progress survives).
"""
import json, statistics, time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel

import silicon_in_loop as S   # simulate, aic_service_ms, load_aic_fn, handoff_ms, CAP, G, IN_FEATURES

HERE = Path(__file__).resolve().parent
OUT = HERE / "burst_anchor_all.json"
REQDIR = HERE / "reqs"; REQDIR.mkdir(exist_ok=True)
TRACE = "/home/gio/tese/data/AzureLMMInferenceTrace_multimodal.csv.gz"
WINDOWS = {  # UTC [start, end)  (top6_by_peak +/-10min pad, from windows.json)
    "burst1": ("2024-10-21 12:59", "2024-10-21 21:18"),
    "burst2": ("2024-10-15 21:16", "2024-10-15 23:10"),
    "burst3": ("2024-10-18 10:18", "2024-10-18 10:45"),
    "burst4": ("2024-10-18 15:37", "2024-10-18 18:46"),
    "burst5": ("2024-10-18 14:32", "2024-10-18 15:53"),
    "burst6": ("2024-10-15 23:26", "2024-10-16 00:48"),
}


def build_reqs():
    """Per-window [[arrival_s_rel, n_images], ...] for image-bearing requests."""
    need = [w for w in WINDOWS if not (REQDIR / f"{w}.json").exists()]
    if need:
        print("loading trace to build reqs for", need, flush=True)
        df = pd.read_csv(TRACE)
        ts = pd.to_datetime(df["TIMESTAMP"].str.replace("Z", "", regex=False), format="ISO8601")
        df = df.assign(ts=ts)
        for w in need:
            s, e = pd.Timestamp(WINDOWS[w][0]), pd.Timestamp(WINDOWS[w][1])
            m = (df.ts >= s) & (df.ts < e) & (df.NumImages > 0)
            sub = df.loc[m, ["ts", "NumImages"]].sort_values("ts")
            reqs = [[round((t - s).total_seconds(), 3), int(n)]
                    for t, n in zip(sub.ts, sub.NumImages)]
            json.dump(reqs, open(REQDIR / f"{w}.json", "w"))
            print(f"  {w}: {len(reqs)} image reqs, {sub.NumImages.sum()} images", flush=True)
    return {w: json.load(open(REQDIR / f"{w}.json")) for w in WINDOWS}


def needed_Ns(all_reqs):
    ns = set()
    for reqs in all_reqs.values():
        for _, n in reqs:
            full, rem = divmod(int(n), S.CAP)
            if full:
                ns.add(S.CAP)
            if rem:
                ns.add(rem)
    return sorted(ns)


def measure_fn(model, Ns, nruns=5, iters=20, warm=5):
    cache = {}
    for i, n in enumerate(Ns):
        grid = torch.tensor([[1, S.G, S.G]] * n, device="cuda")
        px = torch.randn(S.G * S.G * n, S.IN_FEATURES, device="cuda", dtype=torch.bfloat16)
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
        cache[n] = statistics.fmean(means)
        if i % 8 == 0 or n == Ns[-1]:
            print(f"    f(N={n}) = {cache[n]:.2f} ms  [{i+1}/{len(Ns)}]", flush=True)
    return cache


def chunked(cache, n):
    full, rem = divmod(int(n), S.CAP)
    tot = full * cache[S.CAP] if full else 0.0
    if rem:
        tot += cache[rem]
    return tot


def run():
    all_reqs = build_reqs()
    Ns = needed_Ns(all_reqs)
    aic = S.load_aic_fn()
    print(f"needed f(N) for {len(Ns)} sizes: {Ns}", flush=True)
    results = json.load(open(OUT)) if OUT.exists() else {"windows": {w: {} for w in WINDOWS}}

    def clk():
        try:
            import subprocess
            return int(subprocess.run(["nvidia-smi", "--query-gpu=clocks.sm",
                "--format=csv,noheader,nounits"], capture_output=True, text=True
                ).stdout.split("\n")[0])
        except Exception:
            return -1

    # AIC-sim per window (once)
    for w, reqs in all_reqs.items():
        results["windows"][w]["n_reqs"] = len(reqs)
        results["windows"][w]["images"] = int(sum(n for _, n in reqs))
        results["windows"][w]["aic"] = S.simulate(reqs, lambda n: S.aic_service_ms(aic, n), aic)
    json.dump(results, open(OUT, "w"), indent=1)

    for mode in ("eager", "compiled"):
        if all(mode in results["windows"][w] for w in WINDOWS):
            print(f"[{mode}] already done, skip", flush=True); continue
        t0 = time.time()
        print(f"\n=== loading ViT ({mode}) ===", flush=True)
        base = Qwen3VLVisionModel.from_pretrained(
            "/home/gio/tese/models/Qwen3-VL-8B-ViT", dtype=torch.bfloat16,
            attn_implementation="sdpa").to("cuda").eval()
        model = torch.compile(base, mode="reduce-overhead") if mode == "compiled" else base
        smhz = clk()
        print(f"  measuring f(N) [{mode}] at SM {smhz} MHz ...", flush=True)
        cache = measure_fn(model, Ns)
        results.setdefault("fn_" + mode, {str(k): round(v, 3) for k, v in cache.items()})
        results["sm_clock_mhz"] = smhz
        for w, reqs in all_reqs.items():
            sil = S.simulate(reqs, lambda n: chunked(cache, n), aic)
            sil["p99_over_aic"] = round(sil["p99"] / results["windows"][w]["aic"]["p99"], 3) \
                if results["windows"][w]["aic"]["p99"] else None
            results["windows"][w][mode] = sil
            json.dump(results, open(OUT, "w"), indent=1)
            print(f"  {w:7s} {mode:8s} p99 {sil['p99']:8.0f} ms  "
                  f"(AIC {results['windows'][w]['aic']['p99']:.0f}, "
                  f"ratio {sil['p99_over_aic']})", flush=True)
        del base, model
        torch.cuda.empty_cache()
        print(f"  [{mode}] done in {time.time()-t0:.0f}s", flush=True)
    print("\nDONE ->", OUT, flush=True)


if __name__ == "__main__":
    run()
