#!/usr/bin/env python
"""Held-out evaluation summary for calibration-selected language operating points.
Reads simulation/results/lang_qsweep/eval_<q>_s<s>/{burst1,burst3,burst4,burst5,week}.report.json
and compares against the published baselines (llm_week/week_fc_{p90,p50}, week_re).
Tail SLA: TTFT p99 < 1000 ms AND ITL p99 < 100 ms.
"""
import json, os, sys

ROOT = "/home/gio/tese/simulation/results"
QS = "/home/gio/tese/simulation/results/lang_qsweep"
TTFT_B, ITL_B = 1000.0, 100.0
# points to summarize: (label, dir)
POINTS = [("p70/s6 (selected)", "eval_p70_s6"),
          ("p90/s4 (frontier)", "eval_p90_s4")]
EVAL_WINDOWS = ["burst1", "burst3", "burst4", "burst5", "week"]

def get(path):
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    return dict(ttft=d.get("p99_ttft_ms"), itl=d.get("p99_itl_ms"),
                gpu_h=d.get("gpu_hours"), reqs=d.get("completed_requests"))

def verdict(r):
    if r is None: return "  --  "
    return "PASS" if (r["ttft"] < TTFT_B and r["itl"] < ITL_B) else "FAIL"

print("=== HELD-OUT EVAL (eval span, production fixed-context archive) ===")
print("SLA: TTFT p99 < 1000 ms AND ITL p99 < 100 ms\n")
for label, d in POINTS:
    print(f"--- {label} ---")
    print(f"{'window':>8} | {'ttft p99':>9} {'itl p99':>8} {'gpu_h':>8} {'reqs':>8}  verdict")
    for w in EVAL_WINDOWS:
        r = get(f"{QS}/{d}/{w}.report.json")
        if r is None:
            print(f"{w:>8} | (not run)")
            continue
        print(f"{w:>8} | {r['ttft']:9.1f} {r['itl']:8.2f} {r['gpu_h']:8.1f} {str(r['reqs']):>8}  {verdict(r)}")
    print()

print("=== BASELINES (llm_week, published) ===")
for label, p in [("week fc-p90 (thesis)", f"{ROOT}/llm_week/week_fc_p90.report.json"),
                 ("week fc-p50",          f"{ROOT}/llm_week/week_fc_p50.report.json"),
                 ("week reactive",        f"{ROOT}/llm_week/week_re.report.json")]:
    r = get(p)
    if r: print(f"{label:>22}: ttft p99 {r['ttft']:7.1f}  itl p99 {r['itl']:6.2f}  gpu_h {r['gpu_h']:7.1f}  {verdict(r)}")
print("  static TP2x2 (time-matched): 537.4 GPU-h (reference denominator)")

# headline: selected-point week vs p90
sel = get(f"{QS}/eval_p70_s6/week.report.json")
base = get(f"{ROOT}/llm_week/week_fc_p90.report.json")
if sel and base:
    print(f"\n>>> SELECTED p70/s6 week: {sel['gpu_h']:.1f} GPU-h @ TTFT p99 {sel['ttft']:.0f} ms "
          f"({verdict(sel)})  vs  p90/s8 {base['gpu_h']:.1f} GPU-h  =  {sel['gpu_h']/base['gpu_h']:.3f}x p90; "
          f"{sel['gpu_h']/537.4:.3f}x static")
