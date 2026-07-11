#!/usr/bin/env python
"""Blocker B1 fix: recompute the static-optimal encoder fleet on the
STAGE-CONDITIONAL (image-bearing) encoder-delay p99.

The thesis currently computes encoder-delay p99 over ALL requests, appending
encoder_delay=0.0 for text-only requests (workload/trace_to_two_pool.py
lines 481-495 / the grid feasibility gate), while calling it "the worst
percentile of vision-pool users." That mixed-population p99 UNDERSTATES the
tail seen by image-bearing users (the text zeros pad the bottom of the sorted
array, pulling the 99th-percentile index toward the median of the image
distribution).

This script reruns the grid's EXACT vision-pool dispatch (import
simulate_vision_pool + load_window + percentiles + build_series from
workload/trace_to_two_pool.py, and reuse the AICEncoder f(N) costing from
collector_artifacts/phaseE_physical_anchor/silicon_multiworker.py) but reports
BOTH:
  * mixed p99      -- delays over image reqs, padded with 0.0 for text-only
                      (reproduces grid_summary.json vision_curve; sanity check)
  * image p99      -- p99 over ONLY NumImages>0 requests, no zero padding
                      (the corrected, stage-conditional metric)

Feasibility gate (unchanged in FORM): p99 < 1000 ms AND not queue_divergent.
The divergence test is image-queue based (build_series -> queue_imgs_end) and
is IDENTICAL under both metrics; only the p99 that feeds the threshold changes.

For each window (6 bursts + steady day) it finds:
  * mixed  C* / p99  (== the current thesis / grid numbers)
  * image  C* / p99  (== the corrected numbers)
and computes corrected 5090 encoder GPU-h = C* * span_h.

Run under the aiconfigurator venv:
  /home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python rerun_b1.py
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/gio/tese/workload")
from trace_to_two_pool import (  # noqa: E402
    load_window, simulate_vision_pool, percentiles, build_series)

TESE = Path("/home/gio/tese")
PHASEE = TESE / "collector_artifacts" / "phaseE_physical_anchor"
GRID = TESE / "simulation" / "results" / "grid" / "grid_summary.json"

CAP = 64
TOKENS_PER_IMAGE = 196
LLM_HIDDEN = 4096
BYTES_PER_ELEM = 2
SLA_MS = 1000.0
HANDOFF_RTT_MS = 0.2
HANDOFF_GBPS = 25.0

# name, offset, max_requests, grid-reported feasible C* (the CURRENT numbers),
# span_h (from grid_summary), llm_gpus (H100 side, UNCHANGED by this fix).
WINDOWS = [
    ("burst1",  843072, 64804,  6,  8.316, 4),
    ("burst2",   78376, 13870,  8,  1.899, 4),
    ("burst3",  531966,  3093,  7,  0.450, 4),
    ("burst4",  565664, 25639,  7,  3.150, 4),
    ("burst5",  558386,  8983, 16,  1.349, 4),
    ("burst6",   93867,  9821,  6,  1.366, 4),
    ("steady",  627019, 88260,  2, 23.999, 2),
]


def handoff_ms(n_img):
    if HANDOFF_GBPS <= 0 or n_img <= 0:
        return 0.0
    n_bytes = TOKENS_PER_IMAGE * n_img * LLM_HIDDEN * BYTES_PER_ELEM
    return HANDOFF_RTT_MS + n_bytes / (HANDOFF_GBPS * 1e9 / 8) * 1e3


class AICEncoder:
    """AIC f(N) costing, exactly as silicon_multiworker.py loads it."""
    def __init__(self):
        p = PHASEE.parent / "phaseB_batch_validation" / "aic_f_n_postinfill.csv"
        self.tab = {int(float(r["n_images"])): float(r["aic_ms"])
                    for r in csv.DictReader(open(p))}

    def _f(self, n):
        n = int(n)
        return self.tab.get(n) or self.tab[min(self.tab, key=lambda x: abs(x - n))]

    def latency_ms(self, n):
        return (self._f(int(n)), TOKENS_PER_IMAGE * int(n))

    def chunked_service_ms(self, num_images, cap):
        full, rem = divmod(int(num_images), cap)
        total = full * self._f(cap) if full else 0.0
        if rem:
            total += self._f(rem)
        return total

    def post_merge_tokens(self, num_images):
        return TOKENS_PER_IMAGE * max(0, int(num_images))


def build_img_reqs(offset, max_requests):
    """Grid-exact: load_window then the converter's img_reqs construction
    (trace_to_two_pool.py lines 461-462)."""
    df = load_window(max_requests, offset)
    t0 = df["ts"].iloc[0]
    arr_ms = (df["ts"] - t0).dt.total_seconds().to_numpy() * 1000.0
    nimg = df["NumImages"].to_numpy()
    img_reqs = [(float(arr_ms[i]), i, int(nimg[i]))
                for i in range(len(df)) if int(nimg[i]) > 0]
    return img_reqs, len(df)


def eval_point(reqs, n_workers, encoder, total_reqs):
    """Returns (mixed_p99, image_p99, divergent).

    image delays (image-bearing users' encoder delay) computed exactly as the
    grid does; mixed pads with 0.0 for text-only (grid behavior); divergence
    is the grid's image-queue test, common to both.
    """
    finish, batches, _ = simulate_vision_pool(reqs, n_workers, CAP, encoder)
    img_delays = [(finish[i] - arr) + handoff_ms(n) for arr, i, n in reqs if n > 0]
    mixed_delays = img_delays + [0.0] * max(0, total_reqs - len(img_delays))
    image_p99 = percentiles(img_delays)["p99"]      # CORRECTED: no zero padding
    mixed_p99 = percentiles(mixed_delays)["p99"]     # CURRENT: grid behavior

    # divergence (grid-exact, image-queue based; identical under both metrics)
    t_end_ms = max((fin for _s, fin, _t, _nf in batches), default=0.0)
    series = build_series(reqs, batches, t_end_ms)
    arr_end_ms = max((arr for arr, _i, _n in reqs), default=0.0)
    arr_end_sec = min(len(series) - 1, int(arr_end_ms // 1000)) if series else 0
    q = [s["queue_imgs_end"] for s in series[: arr_end_sec + 1]]
    q_median = sorted(q)[len(q) // 2] if q else 0
    q_end = q[-1] if q else 0
    divergent = bool(q_end > 10 * max(1, q_median))
    return mixed_p99, image_p99, divergent


def cstar(reqs, encoder, sweep, total_reqs):
    """First feasible C under mixed gate and under image gate; full curves."""
    curve = {}
    mixed_cstar = image_cstar = None
    for w in sweep:
        mp99, ip99, div = eval_point(reqs, w, encoder, total_reqs)
        mixed_feas = (mp99 < SLA_MS) and not div
        image_feas = (ip99 < SLA_MS) and not div
        curve[w] = {"mixed_p99": round(mp99, 1), "image_p99": round(ip99, 1),
                    "div": div, "mixed_feas": mixed_feas, "image_feas": image_feas}
        if mixed_cstar is None and mixed_feas:
            mixed_cstar = w
        if image_cstar is None and image_feas:
            image_cstar = w
    return mixed_cstar, image_cstar, curve


def main():
    sweep = list(range(1, 33)) + [36, 40, 48, 64]
    enc = AICEncoder()
    grid = json.load(open(GRID))

    out = {"sla_ms": SLA_MS, "windows": {}}
    print(f"{'window':8s} {'span_h':>7s} {'grid_C*':>7s} "
          f"{'mixC*':>5s} {'mix_p99':>8s} | {'imgC*':>5s} {'img_p99':>8s} "
          f"{'dC':>3s} {'5090_GPUh':>10s}  note")
    print("-" * 92)

    image_cstars = []
    for name, offset, maxr, grid_cs, span_h, llm_gpus in WINDOWS:
        reqs, total = build_img_reqs(offset, maxr)
        mixed_cs, image_cs, curve = cstar(reqs, enc, sweep, total)
        image_cstars.append(image_cs)

        mix_p99 = curve[mixed_cs]["mixed_p99"] if mixed_cs else None
        img_p99 = curve[image_cs]["image_p99"] if image_cs else None
        # image p99 EVALUATED AT the mixed (current) C* — shows the metric gap
        img_p99_at_mixcs = curve[mixed_cs]["image_p99"] if mixed_cs else None

        gpuh_5090_old = round((mixed_cs or 0) * span_h, 1)
        gpuh_5090_new = round((image_cs or 0) * span_h, 1)
        gpuh_h100 = round(llm_gpus * span_h, 1)

        delta = (image_cs - mixed_cs) if (image_cs and mixed_cs) else None
        note = "UNCHANGED" if delta == 0 else f"+{delta} worker"

        out["windows"][name] = {
            "offset": offset, "max_requests": maxr, "span_h": span_h,
            "n_image_reqs": len(reqs), "total_reqs": total,
            "grid_cstar_reported": grid_cs,
            "current_mixed_cstar": mixed_cs, "current_mixed_p99": mix_p99,
            "corrected_image_cstar": image_cs, "corrected_image_p99": img_p99,
            "image_p99_at_current_cstar": img_p99_at_mixcs,
            "delta_workers": delta,
            "gpuh_5090_old": gpuh_5090_old, "gpuh_5090_new": gpuh_5090_new,
            "gpuh_h100": gpuh_h100, "llm_gpus": llm_gpus,
            "reproduces_grid_mixed_cstar": mixed_cs == grid_cs,
            "curve": {str(k): v for k, v in curve.items() if k <= 20},
        }
        print(f"{name:8s} {span_h:7.3f} {grid_cs:7d} "
              f"{str(mixed_cs):>5s} {str(mix_p99):>8s} | "
              f"{str(image_cs):>5s} {str(img_p99):>8s} "
              f"{('+%d'%delta if delta is not None else '?'):>3s} "
              f"{gpuh_5090_new:10.1f}  {note} "
              f"(img@curC*={img_p99_at_mixcs})")

    deployable_static_old = max(w["current_mixed_cstar"] for w in out["windows"].values())
    deployable_static_new = max(w["corrected_image_cstar"] for w in out["windows"].values())
    out["deployable_static_old"] = deployable_static_old
    out["deployable_static_new"] = deployable_static_new
    out["burst5_c16_image_p99"] = out["windows"]["burst5"]["curve"]["16"]["image_p99"]
    out["burst5_c16_mixed_p99"] = out["windows"]["burst5"]["curve"]["16"]["mixed_p99"]

    print("-" * 92)
    print(f"deployable static (max C*):  OLD mixed = {deployable_static_old}   "
          f"NEW image = {deployable_static_new}")
    print(f"burst5 C=16 denominator floor:  mixed p99 = {out['burst5_c16_mixed_p99']} ms   "
          f"image p99 = {out['burst5_c16_image_p99']} ms")

    dest = TESE / "verification" / "rerun_b1_results.json"
    json.dump(out, open(dest, "w"), indent=1)
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
