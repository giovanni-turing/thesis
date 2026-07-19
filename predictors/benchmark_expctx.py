#!/usr/bin/env python3
"""Expanding-context forecast generation (15-s image + all demand signals).

The shipped benchmark uses a FIXED context: origins start at `ctx`, so the
first forecast can only issue once a full window of history exists (Chronos
33.6 h in). This variant instead GROWS the context as history accrues —
origin o is forecast from series[max(0, o-ctx) : o], a slice that is short
early and reaches the model's cap once o >= ctx. The FM wrappers accept any
context length natively (Bucket.context_length; predict_batch groups by it),
so this needs no model change — just a different origin grid + slice.

Result: forecasts issue from ~min_ctx bins into the trace (default H = 12 bins
= 3 min at 15 s), pushing per-model coverage from 75-93% toward the full 1M.
Writes results/{model}_{variate}_expctx.parquet (thesis archives untouched).

  predictors/.venv or eda venv with GPU; run on the free RTX 5090.
  python benchmark_expctx.py --models timesfm toto chronos [--min-ctx 12] [--smoke N]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from benchmark import (  # reuse the shipped machinery
    H, MODELS, QCOLS, RESULTS_DIR, VARIATES, _rows, load_series, make_predictor,
)
from predictor import Bucket

RES = "15s"
FREQ_S = 15.0


CHUNK_OVERRIDE = None
def gen(model: str, min_ctx: int, smoke: int | None, device: str | None) -> None:
    data, ts = load_series(RES)
    n = len(next(iter(data.values())))
    ctx = MODELS[model]["ctx"]
    first = max(min_ctx, H)
    origins = np.arange(first, n - H + 1, H, dtype=np.int64)
    if smoke:
        origins = origins[:smoke]
    print(f"[{model}] ctx_cap={ctx} origins {len(origins)} "
          f"(first={origins[0]}={origins[0]*FREQ_S/3600:.2f}h, "
          f"expanding {origins[0]}->{ctx} then fixed)", flush=True)

    predictor = make_predictor(model, RES, device)
    predictor.freq_s = FREQ_S
    chunk = CHUNK_OVERRIDE or MODELS[model]["chunk"]

    # predict_batch does NOT group by context length (that's BatchExecutor's job,
    # predictor.py); the backends' _predict_batch stack raw context arrays and
    # require uniform length. So group origins by their context length
    # (= min(o, ctx)) here, predict per group, and reassemble in origin order.
    from collections import defaultdict
    by_len: dict[int, list[int]] = defaultdict(list)  # context_length -> [origin index]
    for idx, o in enumerate(origins):
        by_len[min(int(o), ctx)].append(idx)

    forecasts_by_idx: list = [None] * len(origins)
    t0 = time.time()
    done = 0
    for clen, idxs in sorted(by_len.items()):
        for j in range(0, len(idxs), chunk):
            sub = idxs[j:j + chunk]
            buckets = [Bucket(series_id=f"{model}:{int(origins[i])}", freq_s=FREQ_S,
                              targets={v: data[v][max(0, int(origins[i]) - ctx):int(origins[i])]
                                       for v in VARIATES})
                       for i in sub]
            for i, f in zip(sub, predictor.predict_batch(buckets)):
                forecasts_by_idx[i] = f
            done += len(sub)
        rate = done / max(time.time() - t0, 1e-6)
        print(f"  [{model}] ctxlen={clen} · {done}/{len(origins)} origins "
              f"({rate:.0f}/s, {(len(origins)-done)/max(rate,1e-6):.0f}s left)", flush=True)
    all_forecasts = forecasts_by_idx

    for v in VARIATES:
        cols = _rows(RES, v, origins, all_forecasts, data, ts)
        tbl = pa.table({k: pa.array(val) for k, val in cols.items()})
        out = RESULTS_DIR / f"{model}_{v}_expctx.parquet"
        pq.write_table(tbl, out)
        print(f"  wrote {out.name} ({tbl.num_rows:,} rows, first ts {cols['ts'][0]})", flush=True)
    print(f"[{model}] done in {time.time()-t0:.0f}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["timesfm", "toto", "chronos"])
    ap.add_argument("--min-ctx", type=int, default=H, help="floor context (bins) for the first origins")
    ap.add_argument("--smoke", type=int, default=None, help="only the first N origins")
    ap.add_argument("--device", default=None)
    ap.add_argument("--chunk", type=int, default=None)
    args = ap.parse_args()
    global CHUNK_OVERRIDE
    CHUNK_OVERRIDE = args.chunk
    for m in args.models:
        gen(m, args.min_ctx, args.smoke, args.device)


if __name__ == "__main__":
    main()
