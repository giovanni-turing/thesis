#!/usr/bin/env python3
"""Empirically-calibrated p90 bands for the forward EWMA forecaster (RQ4 / the
"cheap forward baseline" the closed loop never priced).

The closed loop (Ch. baselines/closedloop) drives the encoder on the p90 path
of a foundation model, and separately shows a *trailing* observed-p90 reactive
controller fails the fast onset. It never runs a *forward* classical forecaster
at a *calibrated* p90 through the same pipeline. This builds exactly that:
EWMA's forward point path (predictors/results/ewma_images.parquet), with a p90
band calibrated on the 1.4-day forecast-context window (every EWMA forecast
before the evaluation span start T0 = 2024-10-16 21:39:00 UTC) so that its
empirical coverage matches the nominal 0.90 -- the same target the TSFM p90 is
read against (measured coverage 0.88-0.90).

Three standard, parameter-light calibration schemes (report all; the finding
should be robust to the choice):
  add  : split-conformal additive, per horizon h -> p90 = point + Q0.90(y-point)
  mult : split-conformal multiplicative, per h    -> p90 = point * Q0.90(y/point)
  wsc  : width-scale EWMA's native band by one k   -> p90 = point + k*(p90_nat-point)
Each writes a parquet in the {model}_images.parquet schema the issue-time
schedule generator consumes (resolution/variate/ts/h/point/p50/p90...).
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "predictors/results/ewma_images.parquet"
T0 = pd.Timestamp("2024-10-16 21:39:00")   # eval-span start (windows.json aggregate note)
RES = "15s"
NOMINAL = 0.90
EPS = 1e-6

df = pd.read_parquet(SRC)
df = df[(df.resolution == RES) & (df.variate == "images")].sort_values(["ts", "h"]).reset_index(drop=True)
df["ts"] = pd.to_datetime(df.ts)
calib = df.ts < T0
evalm = ~calib
print(f"rows={len(df)}  calib(ts<{T0.date()} {T0.time()})={calib.sum()}  eval={evalm.sum()}")
print(f"calib ts [{df.ts[calib].min()} .. {df.ts[calib].max()}]")
print(f"eval  ts [{df.ts[evalm].min()} .. {df.ts[evalm].max()}]  (trace end ~2024-10-22 12:00)")
print(f"eval bins={evalm.sum()}  expected~{int(483659.8/15)} (aggregate span/15s)")

y = df.y_true.to_numpy(float)
pt = df.point.to_numpy(float)
nat = df.p90.to_numpy(float)          # EWMA native (Gaussian) p90
h = df.h.to_numpy(int)
cov = lambda p90, mask: float(np.mean(y[mask] <= p90[mask]))

def report(name, p90):
    print(f"  {name:5s}: coverage calib={cov(p90,calib.to_numpy()):.3f} "
          f"eval={cov(p90,evalm.to_numpy()):.3f}  "
          f"p90@eval median={np.median(p90[evalm.to_numpy()]):.0f} "
          f"max={np.max(p90[evalm.to_numpy()]):.0f}")

print("\ncalibration:")
report("nat(k=1)", nat)

# --- add: per-h additive conformal ---
p90_add = pt.copy()
qadd = {}
for hh in range(1, 13):
    m = calib.to_numpy() & (h == hh)
    q = np.quantile(y[m] - pt[m], NOMINAL)
    qadd[hh] = float(q)
    p90_add[h == hh] = np.maximum(pt[h == hh] + q, 0.0)
report("add", p90_add)

# --- mult: per-h multiplicative conformal (guard small point) ---
p90_mult = pt.copy()
qmul = {}
for hh in range(1, 13):
    m = calib.to_numpy() & (h == hh) & (pt > EPS)
    ratio = y[m] / pt[m]
    q = float(np.quantile(ratio, NOMINAL))
    qmul[hh] = q
    p90_mult[h == hh] = np.maximum(pt[h == hh] * q, 0.0)
report("mult", p90_mult)

# --- wsc: single width-scale k on native band, bisect to nominal coverage on calib ---
exc = np.maximum(nat - pt, 0.0)
cm = calib.to_numpy()
def cov_k(k):
    return float(np.mean(y[cm] <= pt[cm] + k * exc[cm]))
lo, hi = 0.0, 50.0
for _ in range(60):
    mid = 0.5 * (lo + hi)
    if cov_k(mid) < NOMINAL:
        lo = mid
    else:
        hi = mid
k = 0.5 * (lo + hi)
p90_wsc = np.maximum(pt + k * exc, 0.0)
report("wsc", p90_wsc)
print(f"  wsc k={k:.3f}  (k<1 shrinks native band, k>1 widens)")

# --- write parquets in the consumed schema ---
outs = {"add": p90_add, "mult": p90_mult, "wsc": p90_wsc}
manifest = {"source": str(SRC), "T0_eval": str(T0), "nominal": NOMINAL,
            "resolution": RES, "n_calib": int(calib.sum()), "n_eval": int(evalm.sum()),
            "coverage": {}, "params": {"add_qh": qadd, "mult_qh": qmul, "wsc_k": k}}
for name, p90 in outs.items():
    o = df.copy()
    o["p90"] = p90
    o["p50"] = o["point"]                       # keep p50=point so p50 runs work
    path = ROOT / f"predictors/results/ewma_cal_{name}_images.parquet"
    o.to_parquet(path, index=False)
    manifest["coverage"][name] = {"calib": cov(p90, cm), "eval": cov(p90, evalm.to_numpy())}
    print(f"wrote {path}")
manifest["coverage"]["native"] = {"calib": cov(nat, cm), "eval": cov(nat, evalm.to_numpy())}
(ROOT / "predictors/results/ewma_cal_manifest.json").write_text(json.dumps(manifest, indent=1))
print("\nmanifest -> predictors/results/ewma_cal_manifest.json")
