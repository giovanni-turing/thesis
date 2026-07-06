"""Rolling-origin benchmark of every predictor over the materialized demand
series (analysis/trace_eda/series/rates_{res}.parquet — 7 days of the Azure
multimodal trace at 5 bin resolutions; columns requests/images/ctx/gen).

Design
------
- Forecast origins sit on a common grid: every origin is a multiple of H
  (=12). Origin o forecasts steps [o, o+H) from context [o-C, o), so stride H
  tiles the timeline into a continuous, non-overlapping prediction path, and
  every model lands on the same absolute steps wherever its context allows —
  cross-model comparison just intersects on step (all steps >= 8076 are
  predicted by every model at every resolution).
- Effective context C = model max context − (1 point + 9 quantile heads) × H
  of headroom for the forecast tokens themselves:
      timesfm 2048−120=1928   toto 4096−120=3976   chronos 8192−120=8072
  Baselines (naive/ewma/holt_winters) get the TimesFM budget (1928) so they
  share its grid — the cheapest models are compared on the widest span.
- Modes:
  - uni: each variate forecast from its own history alone (covariate-blind).
  - cov: the model's *native* covariate mechanism, targets = all 4 variates —
    chronos: per target, the other 3 series ride as past-only covariates;
    toto:    all 4 variates form one multivariate series (variate-axis
             attention), each target read from the joint forecast.
    TimesFM and the baselines have no covariate path — uni only.
- GPU batching: window matrices are sliced zero-copy per chunk
  (sliding_window_view) and each backend receives max_batch_size buckets per
  predict_batch call, which it turns into a single dense forward (timesfm,
  toto) or an internally sub-batched pipeline call (chronos).

Output
------
results/parts/{model}/{mode}_{res}_{first_origin}.parquet, written atomically
(tmp + rename) so an interrupted run resumes by skipping finished parts.
`assemble` concatenates parts into results/{model}_{variate}.parquet (uni) and
results/{model}_covariates.parquet (cov), sorted by (resolution, variate,
step), with run parameters in the parquet key-value metadata.

Row schema (long format — one row per predicted value):
  resolution  str   series file the row came from (1s|15s|30s|45s|1min)
  variate     str   forecast target (requests|images|ctx|gen)
  origin      int32 first predicted step of this forecast call ("prediction step")
  h           int8  horizon position 1..H
  step        int32 absolute index in the series file (= origin + h - 1)
  ts          timestamp[ns]  window_start of the predicted bin
  y_true      float32        observed value of that bin
  point       float32        point forecast
  p10..p90    float32 ×9     quantile forecasts (QUANTILE_LEVELS order)

Usage
-----
  python benchmark.py run --model chronos                # all resolutions, uni+cov
  python benchmark.py run --model timesfm --res 1min 45s # subset
  python benchmark.py run --model toto --limit-origins 8 # smoke (parts/smoke/)
  python benchmark.py assemble                           # finished models only
  python benchmark.py plan                               # print work table
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))

from predictor import QUANTILE_LEVELS, Bucket, Predictor  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SERIES_DIR = ROOT / "analysis" / "trace_eda" / "series"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

H = 12
HEADROOM = (1 + len(QUANTILE_LEVELS)) * H  # (point + 9 quantile heads) × horizon = 120
VARIATES = ("requests", "images", "ctx", "gen")
# Small files first: failures surface in seconds, checkpoints accumulate early.
RESOLUTIONS: dict[str, float] = {"1min": 60.0, "45s": 45.0, "30s": 30.0, "15s": 15.0, "1s": 1.0}
QCOLS = [f"p{int(round(level * 100)):02d}" for level in QUANTILE_LEVELS]  # p10..p90

# chunk = buckets per predict_batch call (one dense native batch; chronos
# sub-batches internally so it takes several batches' worth per call).
MODELS: dict[str, dict] = {
    "naive": dict(ctx=2048 - HEADROOM, gpu=False, chunk=4096),
    "ewma": dict(ctx=2048 - HEADROOM, gpu=False, chunk=4096),
    "holt_winters": dict(ctx=2048 - HEADROOM, gpu=False, chunk=4096),
    "timesfm": dict(ctx=2048 - HEADROOM, gpu=True, chunk=256),
    "toto": dict(ctx=4096 - HEADROOM, gpu=True, chunk=256, cov_chunk=64, cov=True),
    "chronos": dict(ctx=8192 - HEADROOM, gpu=True, chunk=2048, cov_chunk=512, cov=True),
}
# Holt-Winters seasonal period per resolution: one hour of bins, except at 1s
# where two full hours (7200) would not fit the 1928-step context — 15 min is
# the largest round period with the required two full cycles of history.
HW_SEASON = {"1s": 900, "15s": 240, "30s": 120, "45s": 80, "1min": 60}

_SERIES_CACHE: dict[str, tuple[dict[str, np.ndarray], np.ndarray]] = {}


def load_series(res: str) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """-> ({variate: float32 values}, window_start datetime64[ns]) for one file."""
    if res not in _SERIES_CACHE:
        table = pq.read_table(SERIES_DIR / f"rates_{res}.parquet")
        data = {v: table[v].to_numpy().astype(np.float32) for v in VARIATES}
        _SERIES_CACHE[res] = (data, table["window_start"].to_numpy())
    return _SERIES_CACHE[res]


def grid_origins(n: int, ctx: int, limit: int | None = None) -> np.ndarray:
    """Multiples of H in [ctx, n-H] — every origin has a full context behind it
    and a full horizon ahead; stride H makes consecutive forecasts contiguous."""
    first = -(-ctx // H) * H
    origins = np.arange(first, n - H + 1, H, dtype=np.int64)
    return origins[:limit] if limit else origins


def make_predictor(model: str, res: str, device: str | None) -> Predictor:
    freq_s = RESOLUTIONS[res]
    if model == "naive":
        from naive import NaivePredictor

        return NaivePredictor(H, freq_s=freq_s)
    if model == "ewma":
        from ewma import EWMAPredictor

        return EWMAPredictor(H, freq_s=freq_s)
    if model == "holt_winters":
        from holt_winters import HoltWintersPredictor

        return HoltWintersPredictor(H, freq_s=freq_s, seasonal_periods=HW_SEASON[res])
    if model == "timesfm":
        from timesfm_hf import TimesFMPredictor

        return TimesFMPredictor(H, freq_s=freq_s, device=device, batch_size=MODELS[model]["chunk"])
    if model == "toto":
        from toto import TotoPredictor

        return TotoPredictor(H, freq_s=freq_s, device=device, batch_size=MODELS[model]["chunk"])
    if model == "chronos":
        from chronos2 import Chronos2Predictor

        return Chronos2Predictor(H, freq_s=freq_s, device=device, batch_size=256)
    raise ValueError(f"unknown model {model!r}")


def _rows(
    res: str,
    variate: str,
    origins: np.ndarray,
    forecasts: list,
    data: dict[str, np.ndarray],
    ts: np.ndarray,
) -> dict[str, np.ndarray]:
    """Explode one chunk of Forecasts for one variate into long-format columns."""
    n = len(origins)
    point = np.asarray([f.point[variate] for f in forecasts], dtype=np.float32)  # (n, H)
    quant = np.asarray([f.quantiles[variate] for f in forecasts], dtype=np.float32)  # (n, 9, H)
    steps = (origins[:, None] + np.arange(H)[None, :]).ravel()
    cols = {
        "resolution": np.repeat(res, n * H),
        "variate": np.repeat(variate, n * H),
        "origin": np.repeat(origins, H).astype(np.int32),
        "h": np.tile(np.arange(1, H + 1, dtype=np.int8), n),
        "step": steps.astype(np.int32),
        "ts": ts[steps],
        "y_true": data[variate][steps],
        "point": point.ravel(),
    }
    for qi, qcol in enumerate(QCOLS):
        cols[qcol] = quant[:, qi, :].ravel()
    return cols


def _write_part(path: Path, col_chunks: list[dict[str, np.ndarray]]) -> int:
    merged = {k: np.concatenate([c[k] for c in col_chunks]) for k in col_chunks[0]}
    table = pa.Table.from_pydict(merged)
    tmp = path.with_suffix(".tmp")
    pq.write_table(table, tmp)
    os.replace(tmp, path)
    return table.num_rows


def run_model(
    model: str,
    resolutions: list[str],
    modes: list[str],
    part_origins: int,
    limit_origins: int | None,
    device: str | None,
) -> None:
    cfg = MODELS[model]
    parts_root = (RESULTS_DIR / "parts" / "smoke" / model) if limit_origins else (RESULTS_DIR / "parts" / model)
    parts_root.mkdir(parents=True, exist_ok=True)
    predictor: Predictor | None = None  # FM weights load once, reused across resolutions

    for res in resolutions:
        data, ts = load_series(res)
        n = len(ts)
        ctx = cfg["ctx"]
        origins = grid_origins(n, ctx, limit_origins)
        wins = {v: np.lib.stride_tricks.sliding_window_view(data[v], ctx) for v in VARIATES}

        if predictor is None:
            predictor = make_predictor(model, res, device)
        elif not cfg["gpu"]:
            predictor = make_predictor(model, res, device)  # per-res seasonal_periods etc.
        else:
            predictor.freq_s = RESOLUTIONS[res]

        for mode in modes:
            if mode == "cov" and not cfg.get("cov"):
                continue
            chunk = cfg["cov_chunk"] if mode == "cov" else cfg["chunk"]
            n_parts = (len(origins) + part_origins - 1) // part_origins
            for pi in range(n_parts):
                part = origins[pi * part_origins : (pi + 1) * part_origins]
                part_path = parts_root / f"{mode}_{res}_{part[0]:08d}.parquet"
                if part_path.exists():
                    continue
                t0 = time.time()
                chunks: list[dict[str, np.ndarray]] = []
                for c0 in range(0, len(part), chunk):
                    sub = part[c0 : c0 + chunk]
                    ctxs = {v: np.ascontiguousarray(wins[v][sub - ctx]) for v in VARIATES}
                    if not cfg["gpu"]:  # python-loop baselines: lists beat np-scalar iteration
                        ctxs = {v: ctxs[v].tolist() for v in VARIATES}
                    if mode == "uni":
                        for v in VARIATES:
                            buckets = [
                                Bucket(f"{res}:{v}:{o}", RESOLUTIONS[res], {v: ctxs[v][i]})
                                for i, o in enumerate(sub)
                            ]
                            forecasts = predictor.predict_batch(buckets)
                            chunks.append(_rows(res, v, sub, forecasts, data, ts))
                    elif model == "toto":  # cov: one joint multivariate series per origin
                        buckets = [
                            Bucket(f"{res}:joint:{o}", RESOLUTIONS[res], {v: ctxs[v][i] for v in VARIATES})
                            for i, o in enumerate(sub)
                        ]
                        forecasts = predictor.predict_batch(buckets)
                        for v in VARIATES:
                            chunks.append(_rows(res, v, sub, forecasts, data, ts))
                    else:  # cov, chronos: per target, the other three as past covariates
                        for v in VARIATES:
                            others = [w for w in VARIATES if w != v]
                            buckets = [
                                Bucket(
                                    f"{res}:{v}:{o}",
                                    RESOLUTIONS[res],
                                    {v: ctxs[v][i]},
                                    covariates={w: ctxs[w][i] for w in others},
                                )
                                for i, o in enumerate(sub)
                            ]
                            forecasts = predictor.predict_batch(buckets)
                            chunks.append(_rows(res, v, sub, forecasts, data, ts))
                rows = _write_part(part_path, chunks)
                dt = time.time() - t0
                print(
                    f"[{model} {mode} {res}] part {pi + 1}/{n_parts}: {len(part)} origins, "
                    f"{rows} rows in {dt:.1f}s ({len(part) / dt:.0f} orig/s)",
                    flush=True,
                )
    print(f"[{model}] done", flush=True)


def _expected_origins(model: str, res: str) -> int:
    n = len(load_series(res)[1])
    return len(grid_origins(n, MODELS[model]["ctx"]))


def assemble(models: list[str]) -> None:
    for model in models:
        cfg = MODELS[model]
        parts_dir = RESULTS_DIR / "parts" / model
        if not parts_dir.is_dir():
            print(f"[{model}] no parts, skipping")
            continue
        modes = ["uni"] + (["cov"] if cfg.get("cov") else [])
        for mode in modes:
            missing = []
            tables = []
            for res in RESOLUTIONS:
                paths = sorted(parts_dir.glob(f"{mode}_{res}_*.parquet"))
                got = sum(pq.read_metadata(p).num_rows for p in paths)
                want = _expected_origins(model, res) * len(VARIATES) * H
                if got != want:
                    missing.append(f"{res}: {got}/{want} rows")
                tables += [pq.read_table(p) for p in paths]
            if missing:
                print(f"[{model} {mode}] incomplete — not assembling: {'; '.join(missing)}")
                continue
            table = pa.concat_tables(tables).sort_by(
                [("resolution", "ascending"), ("variate", "ascending"), ("step", "ascending"), ("h", "ascending")]
            )
            meta = {
                "model": model,
                "mode": mode,
                "context_length": str(cfg["ctx"]),
                "context_budget": f"max_ctx - (1 point + {len(QUANTILE_LEVELS)} quantiles) * H = max_ctx - {HEADROOM}",
                "horizon": str(H),
                "origin_grid": f"multiples of {H} in [context_length (ceil), n-{H}]; stride {H} => contiguous coverage",
                "quantile_levels": ",".join(str(q) for q in QUANTILE_LEVELS),
                "covariates": {
                    "uni": "none (each variate forecast from its own history)",
                    "cov": "chronos: other 3 variates as past-only covariates; toto: all 4 variates jointly (variate-axis attention)",
                }[mode],
                "source": "analysis/trace_eda/series/rates_{resolution}.parquet",
            }
            meta = {k.encode(): v.encode() for k, v in meta.items()}
            if mode == "cov":
                out = RESULTS_DIR / f"{model}_covariates.parquet"
                pq.write_table(table.replace_schema_metadata(meta), out)
                print(f"[{model}] wrote {out.name} ({table.num_rows} rows)")
            else:
                for v in VARIATES:
                    sub = table.filter(pc.equal(table["variate"], v))
                    out = RESULTS_DIR / f"{model}_{v}.parquet"
                    pq.write_table(sub.replace_schema_metadata(meta), out)
                    print(f"[{model}] wrote {out.name} ({sub.num_rows} rows)")


def plan() -> None:
    print(f"H={H}  headroom={HEADROOM}  quantiles={QUANTILE_LEVELS}")
    for model, cfg in MODELS.items():
        total = 0
        line = []
        for res in RESOLUTIONS:
            k = _expected_origins(model, res)
            total += k
            line.append(f"{res}:{k}")
        modes = "uni+cov" if cfg.get("cov") else "uni"
        print(
            f"{model:>13}  ctx={cfg['ctx']:<5} {modes:<8} origins {total:>6} "
            f"({', '.join(line)}) -> {total * len(VARIATES) * H} rows/mode"
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    runp = sub.add_parser("run", help="run one model (resumable)")
    runp.add_argument("--model", required=True, choices=list(MODELS))
    runp.add_argument("--res", nargs="+", default=list(RESOLUTIONS), choices=list(RESOLUTIONS))
    runp.add_argument("--modes", nargs="+", default=["uni", "cov"], choices=["uni", "cov"])
    runp.add_argument("--part-origins", type=int, default=4096, help="origins per checkpoint part file")
    runp.add_argument("--limit-origins", type=int, default=None, help="smoke run: first K origins, parts under parts/smoke/")
    runp.add_argument("--device", default=None)

    asmp = sub.add_parser("assemble", help="concat parts into final per-variate/covariate files")
    asmp.add_argument("--models", nargs="+", default=list(MODELS), choices=list(MODELS))

    sub.add_parser("plan", help="print the work table")

    args = ap.parse_args()
    if args.cmd == "run":
        run_model(args.model, args.res, args.modes, args.part_origins, args.limit_origins, args.device)
    elif args.cmd == "assemble":
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        assemble(args.models)
    else:
        plan()


if __name__ == "__main__":
    main()
