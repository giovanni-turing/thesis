#!/usr/bin/env python3
"""Aggregate the settled burst3 evidence into a tracked summary artifact.

Exact generation command (from the repository root; D108):

    python3 simulation/results/silicon_anchor/make_burst3_summary.py

Reads the 15 committed rep.json files (burst3__{fc,re,staticC8}/rep001-005),
recomputes the replicate estimand (per-repetition retimed p99 of per-request
encoder delay; mean and SAMPLE standard deviation across the five
predeclared repetitions), and writes burst3_summary.json next to this
script. Deterministic: no timestamps, ordered keys, fixed float formatting.
The manuscript values in tex/metodologia.tex (sec:aic-physical-replay) must
equal this artifact's rounded values digit-for-digit.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
CELLS = ("burst3__fc", "burst3__re", "burst3__staticC8")


def main() -> None:
    out: dict = {
        "estimand": ("per-repetition retimed p99 of per-request encoder "
                     "delay (ms); frozen-composition retiming"),
        "dispersion": "sample standard deviation over 5 predeclared reps",
        "bound_ms": 1000.0,
        "cells": {},
    }
    for cell in CELLS:
        reps = sorted((HERE / "reps" / cell).glob("rep00*/rep.json"))
        assert len(reps) == 5, f"{cell}: expected 5 reps, found {len(reps)}"
        vals, recon, memb = [], [], []
        for f in reps:
            j = json.loads(f.read_text())
            vals.append(j["retimed_encoder_delay_ms"]["p99"])
            recon.append(bool(j["reconstruction_gate"]["pass"]))
            memb.append([j["membership_recovery_requests_matched"],
                        j["membership_recovery_requests_total"]])
            assert (j["replayed_sim_encoder_delay_ms"]["p99"]
                    == j["banked_sim_encoder_delay_ms"]["p99"]), f
        out["cells"][cell] = {
            "n_reps": len(vals),
            "per_rep_retimed_p99_ms": vals,
            "mean_ms": round(statistics.mean(vals), 3),
            "mean_ms_3dp": f"{statistics.mean(vals):.3f}",
            "sample_sd_ms": round(statistics.stdev(vals), 3),
            "sample_sd_ms_3dp": f"{statistics.stdev(vals):.3f}",
            "reconstruction_gate_all_pass": all(recon),
            "membership_matched_total": memb,
        }
    dst = HERE / "burst3_summary.json"
    dst.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"wrote {dst}")
    for c, d in out["cells"].items():
        print(f"  {c}: {d['mean_ms']} +/- {d['sample_sd_ms']} ms")


if __name__ == "__main__":
    main()
