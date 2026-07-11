#!/usr/bin/env python
"""TASK 1 (B5/P0-5): principled stability test for burst5's static C*.

Replaces the endpoint queue_divergent heuristic (queue at LAST-arrival second
> 10x median) with a real stability criterion, evaluated per worker count C
under BOTH the AIC f(N) cost model (the grid's costing) and the measured
stable-clock RTX-5090 silicon f(N) (checks whether AIC-model stability and
silicon stability agree).

Per C in {8,10,12,14,15,16} report:
  - image-bearing (conditional) encoder-delay p99  [reqs with n_img>0, no 0-pad]
  - all-request p99 (0-padded, = the grid/silicon_multiworker gate metric)
  - backlog SLOPE: linear fit of queue-depth(images) vs time over the LAST 50%
    of the arrival window  (near-zero/negative => not accumulating)
  - drain-time-after-last-arrival (s): last batch finish - last arrival
  - tiling test: burst5 arrivals tiled 3x back-to-back; per-tile end-of-arrival
    backlog (images). Non-growing => steady-state backlog bounded => stable.
  - endpoint heuristic verdict (the OLD test) for reference
  - NEW stability verdict + SLA-feasibility

Run under the aiconfigurator venv (needs the SDK + rtx_5090 data via
trace_to_two_pool import path; but only AIC f(N) csv + silicon json are used).
"""
import bisect
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/gio/tese/workload")
from trace_to_two_pool import (  # noqa: E402
    load_window, simulate_vision_pool, build_series, percentiles)

PHASEE = Path("/home/gio/tese/collector_artifacts/phaseE_physical_anchor")
CAP = 64
TOKENS_PER_IMAGE = 196
LLM_HIDDEN = 4096
BYTES_PER_ELEM = 2
SLA_MS = 1000.0
HANDOFF_RTT_MS = 0.2
HANDOFF_GBPS = 25.0
BURST5 = ("burst5", 558386, 8983)
CSET = [8, 10, 12, 14, 15, 16]


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
        p = PHASEE.parent / "phaseB_batch_validation" / "aic_f_n_postinfill.csv"
        self.tab = {int(float(r["n_images"])): float(r["aic_ms"])
                    for r in csv.DictReader(open(p))}

    def _f(self, n):
        return self.tab.get(n) or self.tab[min(self.tab, key=lambda x: abs(x - n))]


class MeasuredEncoder(_Encoder):
    """Canonical stable-clock silicon f(N), linearly interpolated (same as
    silicon_multiworker.py)."""
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
    df = load_window(max_requests, offset)
    t0 = df["ts"].iloc[0]
    arr_ms = (df["ts"] - t0).dt.total_seconds().to_numpy() * 1000.0
    nimg = df["NumImages"].to_numpy()
    img_reqs = [(float(arr_ms[i]), i, int(nimg[i]))
                for i in range(len(df)) if int(nimg[i]) > 0]
    return img_reqs, len(df), float(arr_ms[-1])


def eval_C(reqs, C, encoder, total_reqs, arr_end_ms):
    finish, batches, _ = simulate_vision_pool(reqs, C, CAP, encoder)
    # image-bearing (conditional) delays -- NO zero padding
    cond = [(finish[i] - arr) + handoff_ms(n) for arr, i, n in reqs if n > 0]
    allreq = cond + [0.0] * max(0, total_reqs - len(cond))
    p99_cond = percentiles(cond)["p99"]
    p99_all = percentiles(allreq)["p99"]

    last_finish = max((fin for _s, fin, _t, _nf in batches), default=0.0)
    drain_s = (last_finish - arr_end_ms) / 1000.0

    # per-second queue series over the arrival window
    series = build_series(reqs, batches, max(last_finish, arr_end_ms))
    arr_end_sec = min(len(series) - 1, int(arr_end_ms // 1000))
    q = np.array([s["queue_imgs_end"] for s in series[: arr_end_sec + 1]], float)
    t = np.arange(len(q), dtype=float)
    # OLD endpoint heuristic (for reference)
    q_med = float(np.median(q)) if len(q) else 0.0
    q_end = float(q[-1]) if len(q) else 0.0
    endpoint_divergent = bool(q_end > 10 * max(1.0, q_med))
    # NEW: slope over last 50% of the arrival window (images / second)
    half = len(q) // 2
    qs, ts = q[half:], t[half:]
    if len(qs) >= 2 and np.ptp(ts) > 0:
        slope = float(np.polyfit(ts, qs, 1)[0])
    else:
        slope = 0.0
    return dict(p99_cond=round(p99_cond, 1), p99_all=round(p99_all, 1),
                drain_s=round(drain_s, 3), slope_img_per_s=round(slope, 4),
                q_end=q_end, q_median=q_med, endpoint_divergent=endpoint_divergent,
                mean_q=round(float(q.mean()), 1) if len(q) else 0.0,
                max_q=int(q.max()) if len(q) else 0)


def tiling_test(reqs, C, encoder, n_tiles=3):
    """Tile burst5 arrivals n_tiles times back-to-back and report the backlog
    at the end of each tile's arrival window. A periodically-repeated arrival
    process is STABLE iff the per-period end backlog does not grow unboundedly."""
    arr0 = reqs[0][0]
    arr_last = reqs[-1][0]
    # period = span + one mean gap so tiles abut without overlap at the seam
    span = arr_last - arr0
    mean_gap = span / max(1, len(reqs) - 1)
    period = span + mean_gap
    tiled = []
    idx_stride = max(i for _a, i, _n in reqs) + 1
    for k in range(n_tiles):
        shift = k * period
        for a, i, n in reqs:
            tiled.append((a + shift, i + k * idx_stride, n))
    tiled.sort(key=lambda x: x[0])
    finish, batches, _ = simulate_vision_pool(tiled, C, CAP, encoder)
    last_finish = max((fin for _s, fin, _t, _nf in batches), default=0.0)
    tile_end_ms = last_finish + 1000.0
    series = build_series(tiled, batches, tile_end_ms)
    # backlog at each tile's end-of-arrival second
    tile_backlogs = []
    for k in range(n_tiles):
        end_arr_ms = k * period + arr_last
        sec = min(len(series) - 1, int(end_arr_ms // 1000))
        tile_backlogs.append(int(series[sec]["queue_imgs_end"]))
    peak_q = max(s["queue_imgs_end"] for s in series)
    # growth verdict: last-tile end backlog not materially above first-tile
    growing = bool(tile_backlogs[-1] > 2 * max(1, tile_backlogs[0]) and
                   tile_backlogs[-1] > tile_backlogs[-2])
    return dict(period_s=round(period / 1000.0, 1), n_tiles=n_tiles,
                tile_end_backlog_imgs=tile_backlogs, peak_queue_imgs=peak_q,
                backlog_growing=growing)


def main():
    name, offset, maxr = BURST5
    reqs, total_reqs, arr_end_ms = build_img_reqs(offset, maxr)
    span_s = arr_end_ms / 1000.0
    total_imgs = sum(n for _a, _i, n in reqs)
    aic = AICEncoder()
    canonical_fn = json.load(open(PHASEE / "oneworker_artifact" /
                                  "silicon_burst5.json"))["measured_fn"]
    sil = MeasuredEncoder(canonical_fn)

    out = {
        "window": name, "offset": offset, "max_requests": maxr,
        "n_reqs": total_reqs, "n_image_reqs": len(reqs),
        "total_images": total_imgs, "arrival_span_s": round(span_s, 1),
        "mean_offered_img_per_s": round(total_imgs / span_s, 2),
        "sla_ms": SLA_MS, "cap": CAP,
        "aic_cap_per_worker_img_per_s": round(CAP / (aic._f(CAP) / 1000.0), 1),
        "sil_cap_per_worker_img_per_s": round(CAP / (sil._f(CAP) / 1000.0), 1),
        "models": {},
    }
    for label, enc in (("aic", aic), ("silicon", sil)):
        rows = {}
        for C in CSET:
            r = eval_C(reqs, C, enc, total_reqs, arr_end_ms)
            r["load_rho_mean"] = round(
                (total_imgs / span_s) / (CAP / (enc._f(CAP) / 1000.0) * C), 4)
            r["tiling"] = tiling_test(reqs, C, enc, n_tiles=3)
            # NEW verdict: SLA on conditional p99 AND stable(slope<=~0 & no tiling growth)
            slope_ok = r["slope_img_per_s"] <= 1.0   # images/s; ~0 or negative
            tile_ok = not r["tiling"]["backlog_growing"]
            r["stable_new"] = bool(slope_ok and tile_ok)
            r["sla_pass_cond"] = bool(r["p99_cond"] < SLA_MS)
            r["feasible_new"] = bool(r["stable_new"] and r["sla_pass_cond"])
            r["feasible_old"] = bool((r["p99_all"] < SLA_MS)
                                     and not r["endpoint_divergent"])
            rows[str(C)] = r
        # honest C* under the NEW criterion (min feasible C in the set)
        cstar_new = next((C for C in CSET if rows[str(C)]["feasible_new"]), None)
        cstar_old = next((C for C in CSET if rows[str(C)]["feasible_old"]), None)
        out["models"][label] = {"by_C": rows,
                                "cstar_new": cstar_new, "cstar_old": cstar_old}

    dest = Path("/home/gio/tese/simulation/results/rerun_verify/burst5_stability.json")
    json.dump(out, open(dest, "w"), indent=1)

    # console summary
    print(f"burst5: {total_reqs} reqs, {len(reqs)} image reqs, {total_imgs} imgs, "
          f"span {span_s/60:.1f} min, mean {out['mean_offered_img_per_s']} img/s offered")
    print(f"cap/worker: AIC {out['aic_cap_per_worker_img_per_s']} img/s, "
          f"SIL {out['sil_cap_per_worker_img_per_s']} img/s")
    for label in ("aic", "silicon"):
        m = out["models"][label]
        print(f"\n=== {label.upper()} f(N) ===  C*_new={m['cstar_new']}  "
              f"C*_old(endpoint)={m['cstar_old']}")
        print(f"{'C':>3} {'p99_cond':>9} {'p99_all':>8} {'slope':>8} {'drain_s':>8} "
              f"{'rho':>6} {'tile_backlog':>16} {'endpt_div':>9} {'stable':>7} {'feas':>5}")
        for C in CSET:
            r = m["by_C"][str(C)]
            print(f"{C:>3} {r['p99_cond']:>9} {r['p99_all']:>8} "
                  f"{r['slope_img_per_s']:>8} {r['drain_s']:>8} {r['load_rho_mean']:>6} "
                  f"{str(r['tiling']['tile_end_backlog_imgs']):>16} "
                  f"{str(r['endpoint_divergent']):>9} {str(r['stable_new']):>7} "
                  f"{str(r['feasible_new']):>5}")
    print(f"\n-> {dest}")


if __name__ == "__main__":
    main()
