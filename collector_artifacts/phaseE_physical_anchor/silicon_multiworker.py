#!/usr/bin/env python
"""Multi-worker silicon feasibility across ALL six burst windows (Phase 5.2 #2).

Question: the single-worker silicon replay trivially fails, but the
*deployable* claim is a C-worker fleet. Does the AIC-sized encoder fleet
(the grid's feasible C*) still meet the encoder-delay SLA when the per-batch
service time is REAL RTX-5090 silicon, or does the measured 1.4-1.6x f(N)
inflation push the FIFO over the bound and demand more workers?

Method: reuse the grid's EXACT vision-pool dispatch and window construction
(import load_window + simulate_vision_pool + build_series + percentiles from
workload/trace_to_two_pool.py) and swap only the encoder cost object:
  * AICEncoder      -- f(N) from aic_f_n_postinfill.csv (the grid's costing)
  * MeasuredEncoder -- one canonical stable-clock 5090 f(N) (window-independent
                       silicon; from silicon_burst5.json), linearly interpolated
                       between the 12 measured N points for cross-request batch
                       totals in 1..64.
No GPU: f(N) is the memoized stable-clock measurement.

Per window, sweep worker count W and report the minimum feasible C* for each
cost model (grid gate: encoder-delay p99 < 1000 ms AND not queue_divergent;
text-only reqs enter as 0-delay), i.e. how far the AIC sizing must be inflated
to survive real silicon. Run under the aiconfigurator venv.
"""
import bisect
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/gio/tese/workload")
from trace_to_two_pool import (  # noqa: E402
    load_window, simulate_vision_pool, percentiles, build_series)

HERE = Path(__file__).resolve().parent
CAP = 64
TOKENS_PER_IMAGE = 196
LLM_HIDDEN = 4096
BYTES_PER_ELEM = 2
SLA_MS = 1000.0
HANDOFF_RTT_MS = 0.2
HANDOFF_GBPS = 25.0

# name, offset, max_requests, grid-reported feasible C* (committed vision points)
WINDOWS = [
    ("burst1", 843072, 64804, 6),   # onset 220 min
    ("burst2",  78376, 13870, 8),   # onset 48 min
    ("burst3", 531966,  3093, 7),   # onset 1 min
    ("burst4", 565664, 25639, 7),   # onset 60 min
    ("burst5", 558386,  8983, 16),  # onset 35 min
    ("burst6",  93867,  9821, 6),   # onset 1 min
]


def handoff_ms(n_img):
    if HANDOFF_GBPS <= 0 or n_img <= 0:
        return 0.0
    n_bytes = TOKENS_PER_IMAGE * n_img * LLM_HIDDEN * BYTES_PER_ELEM
    return HANDOFF_RTT_MS + n_bytes / (HANDOFF_GBPS * 1e9 / 8) * 1e3


class _Encoder:
    def _f(self, n):
        raise NotImplementedError

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


class AICEncoder(_Encoder):
    def __init__(self):
        p = HERE.parent / "phaseB_batch_validation" / "aic_f_n_postinfill.csv"
        self.tab = {int(float(r["n_images"])): float(r["aic_ms"])
                    for r in csv.DictReader(open(p))}

    def _f(self, n):
        return self.tab.get(n) or self.tab[min(self.tab, key=lambda x: abs(x - n))]


class MeasuredEncoder(_Encoder):
    """Canonical stable-clock silicon f(N), linearly interpolated between the
    measured N points (window-independent 5090 silicon)."""
    def __init__(self, measured_fn):
        self.xs = sorted(int(k) for k in measured_fn)
        self.ys = [float(measured_fn[str(x)]) for x in self.xs]

    def _f(self, n):
        n = int(n)
        if n <= self.xs[0]:
            return self.ys[0] * n / self.xs[0]
        if n >= self.xs[-1]:
            return self.ys[-1]
        j = bisect.bisect_left(self.xs, n)
        if self.xs[j] == n:
            return self.ys[j]
        x0, x1, y0, y1 = self.xs[j - 1], self.xs[j], self.ys[j - 1], self.ys[j]
        return y0 + (y1 - y0) * (n - x0) / (x1 - x0)


def build_img_reqs(offset, max_requests):
    """Grid-exact: load_window then the converter's img_reqs construction."""
    df = load_window(max_requests, offset)
    t0 = df["ts"].iloc[0]
    arr_ms = (df["ts"] - t0).dt.total_seconds().to_numpy() * 1000.0
    nimg = df["NumImages"].to_numpy()
    img_reqs = [(float(arr_ms[i]), i, int(nimg[i]))
                for i in range(len(df)) if int(nimg[i]) > 0]
    return img_reqs, len(df)


def eval_point(reqs, n_workers, encoder, total_reqs):
    """Grid feasibility gate: p99 < SLA AND not queue_divergent."""
    finish, batches, _ = simulate_vision_pool(reqs, n_workers, CAP, encoder)
    delays = [(finish[i] - arr) + handoff_ms(n) for arr, i, n in reqs if n > 0]
    delays += [0.0] * max(0, total_reqs - len(delays))  # text-only reqs = 0-delay
    p99 = percentiles(delays)["p99"]
    t_end_ms = max((fin for _s, fin, _t, _nf in batches), default=0.0)
    series = build_series(reqs, batches, t_end_ms)
    arr_end_ms = max((arr for arr, _i, _n in reqs), default=0.0)
    arr_end_sec = min(len(series) - 1, int(arr_end_ms // 1000)) if series else 0
    q = [s["queue_imgs_end"] for s in series[: arr_end_sec + 1]]
    q_median = sorted(q)[len(q) // 2] if q else 0
    q_end = q[-1] if q else 0
    divergent = bool(q_end > 10 * max(1, q_median))
    return p99, divergent, ((p99 < SLA_MS) and not divergent)


def feasible_cstar(reqs, encoder, sweep, total_reqs):
    row, cstar = {}, None
    for w in sweep:
        p99, div, feas = eval_point(reqs, w, encoder, total_reqs)
        row[str(w)] = {"p99": round(p99, 1), "div": div}
        if cstar is None and feas:
            cstar = w
    return cstar, row


def main():
    sweep = list(range(1, 33)) + [36, 40, 48, 64]
    aic = AICEncoder()
    canonical_fn = json.load(open(HERE / "oneworker_artifact" /
                                  "silicon_burst5.json"))["measured_fn"]
    meas = MeasuredEncoder(canonical_fn)
    out = {"sla_ms": SLA_MS, "sweep": sweep,
           "canonical_fn_source": "oneworker_artifact/silicon_burst5.json (stable 2400MHz)",
           "windows": {}}
    print("window   onset   grid_C*  AIC_C*  SIL_C*  inflation  | sil p99 @AIC-C*")
    for name, offset, maxr, grid_cstar in WINDOWS:
        reqs, total_reqs = build_img_reqs(offset, maxr)
        aic_cstar, aic_row = feasible_cstar(reqs, aic, sweep, total_reqs)
        sil_cstar, sil_row = feasible_cstar(reqs, meas, sweep, total_reqs)
        infl = round(sil_cstar / aic_cstar, 2) if (aic_cstar and sil_cstar) else None
        ac = str(aic_cstar)
        out["windows"][name] = {
            "offset": offset, "max_requests": maxr,
            "n_image_reqs": len(reqs), "total_images": sum(n for _, _, n in reqs),
            "grid_cstar_reported": grid_cstar,
            "aic_feasible_cstar": aic_cstar, "silicon_feasible_cstar": sil_cstar,
            "aic_reproduces_grid": aic_cstar == grid_cstar,
            "worker_inflation_x": infl,
            "silicon_p99_at_aic_cstar": sil_row[ac]["p99"],
            "aic_p99_by_W": aic_row, "silicon_p99_by_W": sil_row,
        }
        print("%-8s %-7s %5d   %5s   %5s   %6s     | %.0f ms (%s)" % (
            name, out["windows"][name].get("onset", ""), grid_cstar, aic_cstar,
            sil_cstar, infl, sil_row[ac]["p99"],
            "grid-match" if aic_cstar == grid_cstar else "MISMATCH"))
    # Single-worker (W=1) end-to-end amplification: silicon p99 / AIC p99.
    # NOTE: at 1 worker every window is deeply infeasible; this ratio is
    # dominated by runaway-backlog depth (grows with window length AND
    # sustained volume), so it is a saturation-regime illustration, NOT a
    # clean per-op metric. The deployment-relevant amplification is the ~2x
    # worker margin at the feasible knee (the C* result above).
    swa = {}
    for name, v in out["windows"].items():
        a1 = v["aic_p99_by_W"]["1"]["p99"]; s1 = v["silicon_p99_by_W"]["1"]["p99"]
        swa[name] = {"aic_p99": a1, "silicon_p99": s1,
                     "ratio": round(s1 / a1, 2) if a1 else None}
    out["single_worker_amplification"] = {
        "note": "W=1 end-to-end p99 ratio; saturation-regime, backlog-depth "
                "dominated (window length + volume), not a clean per-op metric",
        "by_window": swa,
        "range": [min(x["ratio"] for x in swa.values()),
                  max(x["ratio"] for x in swa.values())],
    }
    print("single-worker amplification (W=1, sil/AIC p99):",
          {k: x["ratio"] for k, x in swa.items()})
    dest = HERE / "silicon_multiworker.json"
    json.dump(out, open(dest, "w"), indent=1)
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
