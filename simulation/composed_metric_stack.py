#!/usr/bin/env python3
"""Metric stack for the nine composed request-linked cells (compute-only):
full per-request TTFT and composed-E2E distributions from the same archived
inputs the join reads -- quantile grids, swept violation thresholds, excess
mass. Writes simulation/results/composed_fill/composed_metric_stack.json;
touches no manuscript file."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import composed_fill_join as J

TTFT_THRESH = [500, 750, 1000, 1500, 2000]
E2E_THRESH = [1000, 1500, 2000, 3000, 5000]
QS = [50, 90, 95, 99, 99.9]


def q(a, p):
    s = np.sort(a)
    return round(float(s[min(len(s) - 1, int(len(s) * p / 100))]), 3)


def sweep(a, ths):
    return {str(t): {
        "count": int((a > t).sum()),
        "fraction": round(float((a > t).mean()), 6),
        "excess_mass_request_s": round(float(np.clip(a - t, 0, None).sum()) / 1000.0, 1),
    } for t in ths}


def cell_row(cell):
    win_key, trace_path, rec_path, rep_path, planner = J.CELLS[cell]
    win = J.WINS[win_key]
    N = int(win["max_requests"])
    w = J.raw_frame().iloc[win["offset"]:win["offset"] + N].reset_index(drop=True)
    rel_ms = ((w.ts - w.ts.iloc[0]).dt.total_seconds() * 1000.0).to_numpy()
    t_ts, t_il, t_ol, t_cl, t_rid = J.read_trace(trace_path)
    assert np.array_equal(np.sort(t_rid), np.arange(len(t_ts)))
    enc = np.full(N, np.nan)
    enc[t_rid] = t_ts - rel_ms[t_rid]
    sid, r_arr, r_ttft, r_il, r_ol = J.read_records(rec_path)
    if planner:
        import re
        rec2line = np.array([int(re.match(r"request_(\d+)", s).group(1)) - 1 for s in sid])
    else:
        rec2line, _ = J.key_assign(t_ts, t_cl, t_ol, r_arr, r_il, r_ol)
    ttft = np.full(N, np.nan)
    ttft[rec2line] = r_ttft
    e2e = enc[t_rid][np.argsort(t_rid)] if False else enc + np.nan  # placeholder
    # composed e2e per request: enc delay (indexed by raw i) + ttft (by line -> raw)
    enc_of_line = enc[t_rid]
    e2e_line = enc_of_line + ttft
    return {
        "cell": cell, "n_requests": int(N),
        "ttft_quantiles_ms": {str(p): q(ttft, p) for p in QS} | {"max": round(float(np.nanmax(ttft)), 3)},
        "e2e_quantiles_ms": {str(p): q(e2e_line, p) for p in QS} | {"max": round(float(np.nanmax(e2e_line)), 3)},
        "ttft_violations": sweep(ttft, TTFT_THRESH),
        "e2e_violations": sweep(e2e_line, E2E_THRESH),
    }


def main():
    rows = [cell_row(c) for c in J.CELLS]
    out = Path(J.OUT) / "composed_metric_stack.json"
    out.write_text(json.dumps({"note": "compute-only distribution layer",
                               "cells": rows}, indent=1))
    print(f"{'cell':<22}{'ttft p99':>10}{'e2e p99':>10}"
          + "".join(f"{'t>' + str(t):>8}" for t in TTFT_THRESH)
          + "".join(f"{'e>' + str(t):>8}" for t in E2E_THRESH))
    for r in rows:
        print(f"{r['cell']:<22}{r['ttft_quantiles_ms']['99']:>10.1f}{r['e2e_quantiles_ms']['99']:>10.1f}"
              + "".join(f"{r['ttft_violations'][str(t)]['count']:>8}" for t in TTFT_THRESH)
              + "".join(f"{r['e2e_violations'][str(t)]['count']:>8}" for t in E2E_THRESH))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
