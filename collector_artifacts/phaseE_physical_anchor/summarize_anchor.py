#!/usr/bin/env python
"""Summarize the physical encoder anchor: measured f(N) vs AIC-predicted f(N),
with the clock-invariant ratio, and a cross-check against the phase-B 5x50
silicon reference. Reads the anchor JSON produced by bench_encoder_anchor.py.

Usage: summarize_anchor.py anchor_sdpa_5x50.json
"""
import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PHASEB = os.path.join(_HERE, os.pardir, "phaseB_batch_validation",
                      "measured_f_n_5x50.csv")


def load_phaseb():
    ref = {}
    with open(PHASEB) as f:
        for row in csv.DictReader(f):
            ref[int(row["batch"])] = float(row["mean_ms"])
    return ref


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        _HERE, "anchor_sdpa_5x50.json")
    with open(path) as f:
        r = json.load(f)
    phaseb = load_phaseb()

    print(f"# {r['experiment']}  attn_used={r['attn_used']} "
          f"(requested {r['attn_requested']})")
    print(f"# torch {r['torch']} cuda {r['cuda']}  "
          f"protocol {r['protocol']['nruns']}x{r['protocol']['iters']} "
          f"warmup {r['protocol']['warmup']}  img {r['protocol']['image_px']}px")
    gs = r["gpu_state_before"]
    print(f"# GPU {gs.get('name')}  sm_clock {gs.get('sm_clock_mhz')} "
          f"/ max {gs.get('max_sm_clock_mhz')} MHz  clocks_locked={r['clocks_locked']}")
    print()
    hdr = ("N", "meas_ms", "ci95", "AIC_pred_ms", "ratio",
           "phaseB_ms", "vs_phaseB_%", "clk")
    print("{:>4} {:>9} {:>6} {:>11} {:>6} {:>9} {:>10} {:>5}".format(*hdr))
    ratios = []
    for row in r["rows"]:
        n = row["n_images"]
        ratio = row.get("ratio_meas_over_pred")
        if ratio:
            ratios.append(ratio)
        pb = phaseb.get(n)
        vs_pb = (100 * (row["mean_ms"] - pb) / pb) if pb else None
        print("{:>4} {:>9.3f} {:>6.3f} {:>11} {:>6} {:>9} {:>10} {:>5}".format(
            n, row["mean_ms"], row["ci95_ms"],
            f"{row['aic_pred_ms']:.3f}" if row.get("aic_pred_ms") else "NA",
            f"{ratio:.3f}" if ratio else "NA",
            f"{pb:.3f}" if pb else "NA",
            f"{vs_pb:+.2f}" if vs_pb is not None else "NA",
            row["sm_clock_mhz"]))
    if ratios:
        import statistics
        rmin, rmax, rmean = min(ratios), max(ratios), statistics.fmean(ratios)
        print()
        print(f"# ratio measured/AIC-pred over the sweep: "
              f"min {rmin:.3f}  max {rmax:.3f}  mean {rmean:.3f}  "
              f"spread {100*(rmax-rmin)/rmean:.1f}% of mean")
        req = [1, 6, 8, 16, 32, 64]
        req_ratios = [row["ratio_meas_over_pred"] for row in r["rows"]
                      if row["n_images"] in req and row.get("ratio_meas_over_pred")]
        if req_ratios:
            print(f"# over required N{{1,6,8,16,32,64}}: "
                  f"min {min(req_ratios):.3f} max {max(req_ratios):.3f} "
                  f"mean {statistics.fmean(req_ratios):.3f}")


if __name__ == "__main__":
    main()
