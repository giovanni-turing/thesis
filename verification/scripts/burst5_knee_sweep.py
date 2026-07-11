#!/usr/bin/env python
"""Supplement: find burst5's true SLA knee (lowest feasible C once the endpoint
divergence artifact is removed) under AIC and silicon f(N), and confirm which
window binds the fleet-wide static denominator (burst2 needs C=8)."""
import sys
from pathlib import Path
sys.path.insert(0, "/home/gio/tese/verification/scripts")
from burst5_stability import (  # noqa: E402
    AICEncoder, MeasuredEncoder, build_img_reqs, eval_C, tiling_test, PHASEE)
import json

WINDOWS = [("burst2", 78376, 13870), ("burst5", 558386, 8983)]
CSET = list(range(4, 17))


def stable(reqs, C, enc, total, arr_end):
    r = eval_C(reqs, C, enc, total, arr_end)
    t = tiling_test(reqs, C, enc, 3)
    r["stable_new"] = bool(r["slope_img_per_s"] <= 1.0 and not t["backlog_growing"])
    return r


def main():
    aic = AICEncoder()
    fn = json.load(open(PHASEE / "oneworker_artifact" / "silicon_burst5.json"))["measured_fn"]
    sil = MeasuredEncoder(fn)
    for name, off, mx in WINDOWS:
        reqs, total, arr_end = build_img_reqs(off, mx)
        print(f"\n=== {name} (n={total}, img={len(reqs)}) ===")
        for lbl, enc in (("AIC", aic), ("SIL", sil)):
            knee_cond = knee_all = None
            line = []
            for C in CSET:
                r = stable(reqs, C, enc, total, arr_end)
                ok_cond = r["p99_cond"] < 1000 and r["stable_new"]
                ok_all = r["p99_all"] < 1000 and r["stable_new"]
                if ok_cond and knee_cond is None:
                    knee_cond = C
                if ok_all and knee_all is None:
                    knee_all = C
                line.append(f"C{C}:cond{r['p99_cond']:.0f}/all{r['p99_all']:.0f}"
                            f"{'*' if r['stable_new'] else 'X'}")
            print(f"  {lbl}: knee(cond<1000)={knee_cond}  knee(all<1000)={knee_all}")
            print("     " + "  ".join(line))


if __name__ == "__main__":
    main()
