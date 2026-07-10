"""Rolling-origin benchmark of Dynamo's SHIPPED load predictors (arima, kalman,
prophet, constant) on the IMAGE-rate demand signal, scored with the same WAPE
metric and on the same common-span origin grid as the thesis's foundation-model
benchmark (predictors/benchmark.py + precision.py).

Purpose
-------
Chapter 4 (tex/predictors.tex) benchmarked zero-shot TSFMs (Toto/Chronos/TimesFM)
vs naive/EWMA/Holt-Winters, but NOT vs the specific classical predictors Dynamo's
planner ships (dynamo.planner.core.load.predictors). This fills that gap so the
thesis can state numerically that Dynamo's shipped predictors are worse on the
vision (image-rate) signal than the zero-shot foundation models.

Protocol (mirrors predictors/benchmark.py)
------------------------------------------
- Series: analysis/trace_eda/series/rates_{res}.parquet, column `images`.
- Origin grid: multiples of H=12 (the FM grid stride). Common span = origins in
  [ceil(8072/12)*12, n-12] = [8076, n-12] — the steps every FM forecasts (chronos
  ctx=8072 sets the left edge). h=1 forecast at origin o predicts step o, compared
  to y_true[o]. This is exactly the FM h1 evaluation set, so numbers are directly
  comparable to predictors/results/metrics/metrics_h1.parquet (span='common').
- Per origin o: instantiate a fresh predictor (shipped default PlannerConfig,
  environment=virtual/mode=agg/backend=vllm), feed a trailing window of history
  [o-WINDOW, o) point-by-point via add_data_point, call reset_idle_skip() after
  warmup, then predict_next() -> yhat for step o. Predictions clipped at 0.
  Fresh instance per origin keeps origins independent (matches the FM, which uses
  a bounded fixed context per origin) and avoids cross-origin state leakage.
  NOTE: prophet caps its own buffer at config.prophet_window_size (shipped=50) and
  arima/kalman self-manage; WINDOW just bounds how much history we offer them.
- WAPE = sum|y - yhat| / sum|y| over all scored origins (same as precision.py).
- Origins can be subsampled evenly to cap runtime for slow re-fitting predictors;
  the count actually used is logged and written to the results JSON (no silent
  truncation). Errors/NaN/inf are caught per origin and counted, not dropped
  silently.

Usage
-----
  python dynamo_predictors_bench.py --predictor arima --res 1min --max-origins 20   # smoke
  python dynamo_predictors_bench.py --predictor kalman --res 1min 15s --out out.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SERIES_DIR = ROOT / "analysis" / "trace_eda" / "series"

H = 12
CHRONOS_CTX = 8192 - (1 + 9) * H  # 8072 — sets the common-span left edge
SIGNAL = "images"


def grid_origins(n: int) -> np.ndarray:
    """Common-span origin grid: multiples of H in [ceil(CHRONOS_CTX/H)*H, n-H]."""
    first = -(-CHRONOS_CTX // H) * H
    return np.arange(first, n - H + 1, H, dtype=np.int64)


def subsample(origins: np.ndarray, cap: int | None) -> np.ndarray:
    if cap is None or len(origins) <= cap:
        return origins
    idx = np.linspace(0, len(origins) - 1, cap).round().astype(int)
    return origins[np.unique(idx)]


def make_predictor(name: str):
    from dynamo.planner.config.planner_config import PlannerConfig
    from dynamo.planner.core.load.predictors import LOAD_PREDICTORS

    cfg = PlannerConfig.model_validate(
        {"environment": "virtual", "mode": "agg", "backend": "vllm"}
    )
    return LOAD_PREDICTORS[name](cfg)


def run(name: str, res: str, window: int, max_origins: int | None, verbose: bool) -> dict:
    df = pd.read_parquet(SERIES_DIR / f"rates_{res}.parquet")
    y = df[SIGNAL].to_numpy().astype(float)
    n = len(y)
    origins_all = grid_origins(n)
    origins = subsample(origins_all, max_origins)

    yhat_list: list[float] = []
    ytrue_list: list[float] = []
    n_fail = 0
    n_nonfinite = 0
    fail_examples: list[str] = []
    t0 = time.time()

    for oi, o in enumerate(origins):
        lo = max(0, o - window)
        hist = y[lo:o]
        try:
            p = make_predictor(name)
            for v in hist:
                p.add_data_point(float(v))
            # After feeding warmup history, reset idle-skip so the predictor
            # treats the next (live) step normally — matches planner warmup flow.
            p.reset_idle_skip()
            yhat = float(p.predict_next())
        except Exception as e:  # noqa: BLE001
            n_fail += 1
            if len(fail_examples) < 5:
                fail_examples.append(f"origin {int(o)}: {type(e).__name__}: {e}")
            yhat = float(y[o - 1]) if o > 0 else 0.0  # fall back to last value
        if not math.isfinite(yhat):
            n_nonfinite += 1
            if len(fail_examples) < 5:
                fail_examples.append(f"origin {int(o)}: non-finite yhat={yhat}")
            yhat = float(y[o - 1]) if o > 0 else 0.0
        yhat = max(0.0, yhat)
        yhat_list.append(yhat)
        ytrue_list.append(float(y[o]))
        if verbose and (oi + 1) % 50 == 0:
            print(f"  [{name} {res}] {oi + 1}/{len(origins)} origins", flush=True)

    yhat_arr = np.array(yhat_list)
    ytrue_arr = np.array(ytrue_list)
    denom = np.abs(ytrue_arr).sum()
    wape = float(np.abs(ytrue_arr - yhat_arr).sum() / denom) if denom > 0 else float("nan")
    mae = float(np.abs(ytrue_arr - yhat_arr).mean())
    dt = time.time() - t0

    result = {
        "predictor": name,
        "resolution": res,
        "signal": SIGNAL,
        "horizon": 1,
        "metric": "WAPE = sum|y-yhat|/sum|y|",
        "window": window,
        "n_origins_available": int(len(origins_all)),
        "n_origins_used": int(len(origins)),
        "common_span_first_origin": int(origins_all[0]),
        "common_span_last_origin": int(origins_all[-1]),
        "wape": wape,
        "mae": mae,
        "n_fail": n_fail,
        "n_nonfinite": n_nonfinite,
        "fail_examples": fail_examples,
        "seconds": round(dt, 1),
        "orig_per_s": round(len(origins) / dt, 2) if dt > 0 else None,
    }
    print(
        f"[{name} {res}] WAPE={wape:.4f} MAE={mae:.1f} "
        f"origins={len(origins)}/{len(origins_all)} window={window} "
        f"fail={n_fail} nonfinite={n_nonfinite} in {dt:.1f}s",
        flush=True,
    )
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--predictor", required=True, choices=["arima", "kalman", "prophet", "constant"])
    ap.add_argument("--res", nargs="+", default=["1min"], choices=["1min", "15s", "30s", "45s", "1s"])
    ap.add_argument("--window", type=int, default=512, help="trailing history window fed per origin")
    ap.add_argument("--max-origins", type=int, default=None, help="cap origins (even subsample); default all common-span")
    ap.add_argument("--out", default=None, help="write results JSON to this path")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    results = []
    for res in args.res:
        results.append(run(args.predictor, res, args.window, args.max_origins, not args.quiet))

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2))
        print(f"wrote {args.out}", flush=True)
    else:
        json.dump(results, sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
