#!/usr/bin/env python
"""Summarize the language quantile x scale calibration sweep (burst2 + burst6),
grade the tail SLA (TTFT p99 < 1000 ms AND ITL p99 < 100 ms) on BOTH windows,
and pick the cheapest passing operating point (tie-break: lowest quantile, then
lowest scale). Calibration is on the 1.4-day split only; the selected point is
evaluated held-out by run_lang_calib_eval.sh.
"""
import json, os, glob, re, sys

OUT = "/home/gio/tese/simulation/results/lang_qsweep"
TTFT_BOUND, ITL_BOUND = 1000.0, 100.0
WINDOWS = ("burst2", "burst6")
# auto-discover the (quantile, scale) grid from the reports on disk
_qs, _ss = set(), set()
for _f in glob.glob(f"{OUT}/burst2_*.report.json") + glob.glob(f"{OUT}/burst6_*.report.json"):
    _m = re.match(r"burst[26]_(p\d+)_s([0-9.]+)\.report\.json$", os.path.basename(_f))
    if _m:
        _qs.add(_m.group(1)); _ss.add(_m.group(2))
QS = sorted(_qs, key=lambda q: int(q[1:]))
SS = sorted(_ss, key=lambda s: float(s))

def load(w, q, s):
    p = f"{OUT}/{w}_{q}_s{s}.report.json"
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    return dict(ttft=d.get("p99_ttft_ms", float("nan")),
                itl=d.get("p99_itl_ms", float("nan")),
                gpu_h=d.get("gpu_hours", float("nan")),
                reqs=d.get("completed_requests"))

cells = {}
for q in QS:
    for s in SS:
        rec = {w: load(w, q, s) for w in WINDOWS}
        if any(v is None for v in rec.values()):
            cells[(q, s)] = None
            continue
        passes = all(rec[w]["ttft"] < TTFT_BOUND and rec[w]["itl"] < ITL_BOUND
                     for w in WINDOWS)
        cost = sum(rec[w]["gpu_h"] for w in WINDOWS)
        cells[(q, s)] = dict(rec=rec, passes=passes, cost=cost)

print(f"{'q':>4} {'scale':>5} | "
      f"{'b2 ttft':>8} {'b2 itl':>7} {'b2 gpuh':>8} | "
      f"{'b6 ttft':>8} {'b6 itl':>7} {'b6 gpuh':>8} | {'cost':>7} {'verdict':>7}")
print("-" * 92)
for q in QS:
    for s in SS:
        c = cells[(q, s)]
        if c is None:
            print(f"{q:>4} {s:>5} | (missing)")
            continue
        b2, b6 = c["rec"]["burst2"], c["rec"]["burst6"]
        v = "PASS" if c["passes"] else "fail"
        print(f"{q:>4} {s:>5} | "
              f"{b2['ttft']:8.1f} {b2['itl']:7.2f} {b2['gpu_h']:8.2f} | "
              f"{b6['ttft']:8.1f} {b6['itl']:7.2f} {b6['gpu_h']:8.2f} | "
              f"{c['cost']:7.2f} {v:>7}")

passing = [(q, s, c["cost"]) for (q, s), c in cells.items() if c and c["passes"]]
print("\n" + "=" * 60)
if not passing:
    print("NO passing cell on both burst2 AND burst6.")
    sys.exit(0)
# cheapest, tie-break lowest quantile then lowest scale
qrank = {q: i for i, q in enumerate(QS)}
srank = {s: i for i, s in enumerate(SS)}
cheapest = min(passing, key=lambda x: x[2])
minheadroom = min(passing, key=lambda x: (qrank[x[0]], srank[x[1]]))
print(f"Passing cells (both windows): {len(passing)}")
print(f"CHEAPEST passing (by calib GPU-h):   q={cheapest[0]} scale={cheapest[1]}  cost={cheapest[2]:.2f}")
print(f"MIN-HEADROOM passing (low q,low s):  q={minheadroom[0]} scale={minheadroom[1]}")
print(f"\nHeld-out eval:  EVAL_Q={cheapest[0]} EVAL_S={cheapest[1]} bash simulation/run_lang_calib_eval.sh")
