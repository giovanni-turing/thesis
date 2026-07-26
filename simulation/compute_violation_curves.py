#!/usr/bin/env python3
"""Exact week-wide cost<->violation curves for both pools.

LANGUAGE: reads per-request JSONL from the perreq rerun (simulation/results/lang_qsweep/perreq/
*.perreq.jsonl) -- validated that #satisfying == native goodput_completed_requests -- and counts
violations at any TTFT / e2e / ITL threshold. Cost = gpu_hours * H100 $/h.
ENCODER: reads the exact encoder_delay_violations already in the converter stats. Cost = worker-h * 5090 $/h.

Prices (gpus.io median, 2026-07-25, snapshotted in provenance/audit/evidence/gpu_pricing/):
H100 $2.99/h, RTX 5090 $0.52/h. Robust idempotent: skips language points whose perreq isn't written yet.
Run: python3 simulation/compute_violation_curves.py
Raw *.perreq.jsonl are zstd-compressed in place (housekeeping 2026-07-26) — `zstd -d` them first to
re-run; the computed output is snapshotted in results/lang_qsweep/violation_curves_2026-07-26.txt.
"""
import json, os

PH100, P5090 = 2.99, 0.52
PERREQ = "/home/gio/tese/simulation/results/lang_qsweep/perreq"
ENC = "/home/gio/tese/simulation/results/encoder_hybrid"
N = 749601

LANG = [  # tag, label, robust?
    ("static_tp2x2",      "static TP2x2",        True),
    ("reactive_200_20",   "reactive 200/20",     False),
    ("fc_chronos_p90_s1", "fc chronos p90 mean", False),
    ("fc_chronos_p50_s8", "fc chronos p50/s8",   False),
    ("fc_chronos_p70_s6", "fc chronos p70/s6",   False),
    ("fc_chronos_p90_s4", "fc chronos p90/s4",   False),
    ("fc_chronos_p90_s6", "fc chronos p90/s6",   True),
    ("fc_toto_p90_s6",    "fc toto p90/s6",      True),
    ("fc_timesfm_p90_s6", "fc timesfm p90/s6",   True),
]
TTFT_T = [200, 500, 1000]
E2E_T = [5000, 10000, 20000]

def lang_row(tag):
    pr = f"{PERREQ}/{tag}.perreq.jsonl"; rep = f"{PERREQ}/{tag}.report.json"
    if not os.path.exists(pr):
        return None
    recs = [json.loads(l) for l in open(pr)]
    n = len(recs)
    gpu = json.load(open(rep)).get("gpu_hours") if os.path.exists(rep) else None
    cost = gpu * PH100 if gpu else None
    ttft = {t: sum(1 for r in recs if (r.get("ttft_ms") or 0) > t) for t in TTFT_T}
    e2e = {t: sum(1 for r in recs if (r.get("e2e_latency_ms") or 0) > t) for t in E2E_T}
    return dict(n=n, gpu=gpu, cost=cost, ttft=ttft, e2e=e2e)

def main():
    print("=" * 92)
    print("LANGUAGE (H100 $2.99/h) — EXACT requests violating, week-wide (of ~749,601)")
    print("=" * 92)
    hdr = f"{'point':<22}{'$':>6}" + "".join(f"{'ttft>'+str(t):>10}" for t in TTFT_T) + "".join(f"{'e2e>'+str(t//1000)+'s':>9}" for t in E2E_T)
    print(hdr)
    for tag, lbl, robust in LANG:
        r = lang_row(tag)
        if r is None:
            print(f"{lbl:<22}{'(pending)':>6}"); continue
        c = f"{r['cost']:.0f}" if r['cost'] else "?"
        row = f"{lbl:<22}{c:>6}" + "".join(f"{r['ttft'][t]:>10,}" for t in TTFT_T) + "".join(f"{r['e2e'][t]:>9,}" for t in E2E_T)
        print(row + ("  <-robust" if robust else ""))
    print()
    print("=" * 92)
    print("ENCODER (RTX 5090 $0.52/h) — EXACT requests with encoder delay > T (already recorded)")
    print("=" * 92)
    print(f"{'controller':<16}{'$':>6}{'>250ms':>10}{'>500ms':>10}{'>1s':>9}{'>2s':>8}{'>5s':>7}")
    for tag, lbl in [("re", "reactive"), ("fc", "pure forecast"), ("hybrid", "hybrid")]:
        p = f"{ENC}/{tag}.jsonl.stats.json"
        if not os.path.exists(p):
            print(f"{lbl:<16}(missing)"); continue
        d = json.load(open(p)); v = d.get("encoder_delay_violations", {})
        cost = d["provisioned_worker_seconds"] / 3600 * P5090
        print(f"{lbl:<16}{cost:>6.0f}" + "".join(f"{v.get(str(t),0):>10,}" if t < 1000 else f"{v.get(str(t),0):>9,}" for t in (250,500)) +
              "".join(f"{v.get(str(t),0):>{9 if t==1000 else 8 if t==2000 else 7},}" for t in (1000,2000,5000)))

if __name__ == "__main__":
    main()
