#!/usr/bin/env python
"""Provisioned-regime companion to burst_anchor_all.py (which is 1-worker).

Sweep-only (aiconfigurator venv, no GPU). Reuses the dense live-ViT f(N)
measured by measure_fn_dense.py (fn_dense_{eager,compiled}.json) and reruns the
faithful multi-worker FIFO sweep from silicon_multiworker.py: per burst window
the minimum feasible worker count C* (p99 < 1000 ms, non-divergent) under the
AIC cost model vs. real silicon -- the "worker inflation" a real encoder demands
over what AIC provisions. Serving-mode (compiled) is the honest one; eager is
kept for the mode contrast.

Writes multiworker_anchor.json; leaves silicon_multiworker.json (prior eager) and
burst_anchor_all.json (1-worker) untouched.
"""
import json
from pathlib import Path
import silicon_multiworker as M

HERE = Path(__file__).resolve().parent
OUT = HERE / "multiworker_anchor.json"
SWEEP = list(range(1, 33)) + [36, 40, 48, 64]

fn_eager = json.load(open(HERE / "fn_dense_eager.json"))
fn_comp = json.load(open(HERE / "fn_dense_compiled.json"))
encoders = {"aic": M.AICEncoder(),
            "compiled": M.MeasuredEncoder(fn_comp),
            "eager": M.MeasuredEncoder(fn_eager)}

out = {"sla_ms": M.SLA_MS, "sweep": SWEEP,
       "fn64_ms": {"aic": M.AICEncoder()._f(64), "compiled": fn_comp["64"],
                   "eager": fn_eager["64"]},
       "windows": {}}
print(f"f(64) ms: AIC {out['fn64_ms']['aic']:.1f}  compiled {fn_comp['64']}  "
      f"eager {fn_eager['64']}")
print(f"\n{'window':8s} {'imgs':>10s} {'AIC_C*':>7s} {'comp_C*':>8s} {'eag_C*':>7s} "
      f"{'inflC':>6s} {'inflE':>6s}  comp_p99@AIC_C*  eag_p99@AIC_C*")
for name, offset, maxr, grid in M.WINDOWS:
    reqs, total = M.build_img_reqs(offset, maxr)
    rec = {"n_image_reqs": len(reqs), "total_images": int(sum(n for _, _, n in reqs)),
           "grid_cstar": grid}
    cs = {}
    for key, enc in encoders.items():
        c, row = M.feasible_cstar(reqs, enc, SWEEP, total)
        cs[key] = c
        rec[key] = {"cstar": c, "p99_by_W": row}
    ac = str(cs["aic"]) if cs["aic"] else None
    rec["inflation_compiled"] = round(cs["compiled"] / cs["aic"], 2) if (cs["aic"] and cs["compiled"]) else None
    rec["inflation_eager"] = round(cs["eager"] / cs["aic"], 2) if (cs["aic"] and cs["eager"]) else None
    rec["compiled_p99_at_aic_cstar"] = rec["compiled"]["p99_by_W"].get(ac, {}).get("p99")
    rec["eager_p99_at_aic_cstar"] = rec["eager"]["p99_by_W"].get(ac, {}).get("p99")
    out["windows"][name] = rec
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"{name:8s} {rec['total_images']:>10,d} {str(cs['aic']):>7s} "
          f"{str(cs['compiled']):>8s} {str(cs['eager']):>7s} "
          f"{str(rec['inflation_compiled']):>6s} {str(rec['inflation_eager']):>6s}  "
          f"{str(rec['compiled_p99_at_aic_cstar']):>13s}  {str(rec['eager_p99_at_aic_cstar']):>13s}")

# geomean inflation
import math
def gm(k):
    v = [out["windows"][w][k] for w in out["windows"] if out["windows"][w].get(k)]
    return round(math.exp(sum(math.log(x) for x in v) / len(v)), 3) if v else None
out["geomean_inflation_compiled"] = gm("inflation_compiled")
out["geomean_inflation_eager"] = gm("inflation_eager")
json.dump(out, open(OUT, "w"), indent=1)
print(f"\ngeomean worker inflation: compiled {out['geomean_inflation_compiled']}x  "
      f"eager {out['geomean_inflation_eager']}x")
print("DONE ->", OUT)
