#!/usr/bin/env python
"""Does the 0.27-0.31x economic headline survive measured silicon? (Phase 5.2 #3)

The headline forecast policy (p90 / rho=15 / L=30) provisions a time-varying
worker schedule C(t), priced on the AIC encoder model. This replays each
in-span burst window's image schedule through the grid's EXACT vision pool
(simulate_vision_pool with its worker_schedule hook) under that SAME C(t),
swapping only the per-batch cost f(N): AIC vs the memoized stable-clock 5090
silicon f(N). If the forecast C(t) stays feasible under silicon, the cost
ratio is unchanged (same schedule, still meets the SLA) and 0.27-0.31x holds;
if not, the policy would need a larger schedule and the ratio grows.

Worker-seconds (the cost) is fixed by the schedule, so the only question is
feasibility. burst2/6 are pre-forecast-context (forecast-free by design) and
excluded. Pure CPU; reuses the memoized silicon f(N). Run under the aic venv.
"""
import bisect
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/gio/tese/workload")
from trace_to_two_pool import (  # noqa: E402
    load_window, simulate_vision_pool, percentiles, build_series)

HERE = Path(__file__).resolve().parent
SCHED_DIR = Path("/tmp/claude-1000/-home-gio-tese/"
                 "d6b3c51b-c8eb-4cac-b863-ddeb531bba36/scratchpad/fcsched")
CAP, TOK, HID, BPE = 64, 196, 4096, 2
SLA_MS, RTT, GBPS = 1000.0, 0.2, 25.0
STATIC_C = 16  # deployable-static encoder fleet (burst5-set)

# in-span burst windows: name, offset, max_requests, span_s (windows.json)
WINDOWS = [
    ("burst1", 843072, 64804, 29939.3),
    ("burst3", 531966,  3093,  1619.7),
    ("burst4", 565664, 25639, 11339.2),
    ("burst5", 558386,  8983,  4857.9),
]


def handoff_ms(n):
    if GBPS <= 0 or n <= 0:
        return 0.0
    return RTT + (TOK * n * HID * BPE) / (GBPS * 1e9 / 8) * 1e3


class _Enc:
    def _f(self, n): raise NotImplementedError
    def latency_ms(self, n): return (self._f(int(n)), TOK * int(n))
    def chunked_service_ms(self, num, cap):
        full, rem = divmod(int(num), cap)
        t = full * self._f(cap) if full else 0.0
        if rem: t += self._f(rem)
        return t
    def post_merge_tokens(self, num): return TOK * max(0, int(num))


class AICEncoder(_Enc):
    def __init__(self):
        p = HERE.parent / "phaseB_batch_validation" / "aic_f_n_postinfill.csv"
        self.tab = {int(float(r["n_images"])): float(r["aic_ms"])
                    for r in csv.DictReader(open(p))}
    def _f(self, n):
        return self.tab.get(n) or self.tab[min(self.tab, key=lambda x: abs(x - n))]


class MeasuredEncoder(_Enc):
    def __init__(self, fn):
        self.xs = sorted(int(k) for k in fn)
        self.ys = [float(fn[str(x)]) for x in self.xs]
    def _f(self, n):
        n = int(n)
        if n <= self.xs[0]: return self.ys[0] * n / self.xs[0]
        if n >= self.xs[-1]: return self.ys[-1]
        j = bisect.bisect_left(self.xs, n)
        if self.xs[j] == n: return self.ys[j]
        x0, x1, y0, y1 = self.xs[j-1], self.xs[j], self.ys[j-1], self.ys[j]
        return y0 + (y1 - y0) * (n - x0) / (x1 - x0)


def build_img_reqs(offset, maxr):
    df = load_window(maxr, offset)
    t0 = df["ts"].iloc[0]
    arr = (df["ts"] - t0).dt.total_seconds().to_numpy() * 1000.0
    nimg = df["NumImages"].to_numpy()
    reqs = [(float(arr[i]), i, int(nimg[i])) for i in range(len(df)) if int(nimg[i]) > 0]
    return reqs, len(df)


def eval_schedule(reqs, sched_ms, encoder, total_reqs):
    n_slots = max(c for _, c in sched_ms)
    finish, batches, _ = simulate_vision_pool(reqs, n_slots, CAP, encoder,
                                              worker_schedule=sched_ms)
    delays = [(finish[i] - arr) + handoff_ms(n) for arr, i, n in reqs if n > 0]
    delays += [0.0] * max(0, total_reqs - len(delays))
    p99 = percentiles(delays)["p99"]
    t_end = max((fin for _s, fin, _t, _nf in batches), default=0.0)
    series = build_series(reqs, batches, t_end)
    arr_end = max((a for a, _i, _n in reqs), default=0.0)
    aes = min(len(series) - 1, int(arr_end // 1000)) if series else 0
    q = [s["queue_imgs_end"] for s in series[:aes + 1]]
    qmed = sorted(q)[len(q) // 2] if q else 0
    div = bool((q[-1] if q else 0) > 10 * max(1, qmed))
    return round(p99, 1), div, (p99 < SLA_MS and not div)


def worker_seconds(sched_s, span_s):
    ws = 0.0
    for (t, c), (t2, _c2) in zip(sched_s, sched_s[1:]):
        ws += c * (t2 - t)
    ws += sched_s[-1][1] * max(0.0, span_s - sched_s[-1][0])
    return ws


def main():
    aic = AICEncoder()
    meas = MeasuredEncoder(json.load(open(HERE / "oneworker_artifact" /
                                          "silicon_burst5.json"))["measured_fn"])
    out = {"policy": "p90/rho15/L30 (chronos)", "sla_ms": SLA_MS,
           "static_C": STATIC_C, "windows": {}}
    print("window   fc_ws/static  |  AIC p99  feas  |  SILICON p99  feas")
    fc_tot = st_tot = 0.0
    for name, off, maxr, span_s in WINDOWS:
        sched_s = json.load(open(SCHED_DIR / f"{name}_p90_rho15_L30.json"))
        sched_ms = [(float(t) * 1000.0, int(c)) for t, c in sched_s]
        reqs, total = build_img_reqs(off, maxr)
        ap99, adiv, afeas = eval_schedule(reqs, sched_ms, aic, total)
        sp99, sdiv, sfeas = eval_schedule(reqs, sched_ms, meas, total)
        fc_ws = worker_seconds(sched_s, span_s)
        st_ws = STATIC_C * span_s
        fc_tot += fc_ws; st_tot += st_ws
        out["windows"][name] = {
            "fc_worker_s": round(fc_ws), "static_worker_s": round(st_ws),
            "ratio": round(fc_ws / st_ws, 3),
            "aic_p99": ap99, "aic_feasible": afeas,
            "silicon_p99": sp99, "silicon_feasible": sfeas,
            "sched_peak": max(c for _, c in sched_s)}
        print("%-8s  %.3fx        | %8.0f  %-5s | %8.0f  %-5s" % (
            name, fc_ws / st_ws, ap99, "PASS" if afeas else "FAIL",
            sp99, "PASS" if sfeas else "FAIL"))
    out["aggregate_ratio_over_windows"] = round(fc_tot / st_tot, 3)
    out["all_silicon_feasible"] = all(v["silicon_feasible"] for v in out["windows"].values())
    print("---")
    print("burst-window worker-seconds ratio (fc/static): %.3fx" % (fc_tot / st_tot))
    print("all in-span windows silicon-feasible: %s" % out["all_silicon_feasible"])
    json.dump(out, open(HERE / "silicon_closedloop.json", "w"), indent=1)


if __name__ == "__main__":
    main()
