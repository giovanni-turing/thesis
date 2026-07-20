#!/usr/bin/env python3
"""A16 — the forecasting-side upper bound: FINE-TUNED vs ZERO-SHOT forecasters.

Closes the gap left open at tex/predictors.tex:376 ("All models run zero-shot;
fine-tuning on the trace's first days (fit days 1--3, test 4--7) ... left as
future work") and the conclusion's "fine-tuned forecasters as the
forecasting-side upper bound".

THE QUESTION
------------
Does better forecast accuracy (WAPE) buy a better PROVISIONING outcome, or is
the system already accuracy-saturated? The thesis's own A14/A15 finding is that
model choice is second-order (chronos/toto/timesfm all land on an identical
651.1 ms E2E TTFT p99), which predicts saturation. If fine-tuning improves WAPE
but leaves the provisioning verdicts unchanged, that CONFIRMS the p90 headroom
mechanism -- not forecast accuracy -- is what carries the result. That is a
strengthening result, not a threatening one.

WHICH FAMILIES CAN ACTUALLY BE FINE-TUNED (checked, not assumed)
----------------------------------------------------------------
  chronos-2  YES, first-class. The installed `chronos-forecasting` 2.3.1 ships
             `chronos/chronos2/trainer.py` (`Chronos2Trainer`, an HF Trainer
             subclass) + `chronos/chronos2/dataset.py` (`Chronos2Dataset`), and
             `Chronos2Model.forward` returns a quantile `loss` when
             `future_target` is passed. 120M params -> trivially fits the 5090.
             ==> THIS IS THE PROOF POINT.
  timesfm    PARTIAL. `transformers.TimesFmModelForPrediction.forward` accepts
             `future_values` and returns `loss = mse_loss + quantile_loss`, so
             it is gradient-trainable, but no official fine-tune recipe ships
             with the checkpoint (upstream's is JAX). 500M params. Feasible as
             a second arm; see `--model timesfm` (opt-in, unvalidated recipe).
  toto       NO. The staged `toto2` package (models/toto/.venv) is
             inference-only -- it contains exactly configuration.py + model.py,
             no trainer, no dataset, no loss. Fine-tuning Toto would require
             vendoring Datadog's out-of-tree training code. Reported as a
             documented limitation rather than faked.

THE HONEST SPLIT (no leakage)
-----------------------------
Trace spans 2024-10-15 12:00 .. 2024-10-22 12:00 (7 days exactly, 10080 1-min
bins). Split at day 3 = 2024-10-18 12:00.
  TRAIN  bins [0, split)  -- the series handed to Chronos2Dataset are TRUNCATED
         at `split`, so no sampled training target can come from the test
         region. Truncation, not filtering, is the leakage guarantee.
  VAL    last `--val-frac` of the train region (monitoring/selection only;
         still strictly before the split).
  EVAL   forecast origins o with o >= split, i.e. every predicted step is in
         the held-out region. A forecast's CONTEXT may reach back across the
         split -- that is legitimate conditioning on observed history, exactly
         what a deployed forecaster does, and it is identical for both arms.
         Weights never saw a value at or after the split.

Episode -> region (derived from windows_ext.json notes, printed by `split`):
  TEST:  e7 e8 e12 e13 e16 burst1 burst4 burst5
  train: e9 e10 e11 e14 e15 e17 e18 burst2 burst3 burst6
e13 (the known p90 forecast-miss boundary case, 262.9 img/s peak, 7-min onset)
sits at day 5.27 -- HELD OUT, so "does fine-tuning rescue e13?" is an honest
question this driver can answer.

METHODOLOGY PRESERVED
---------------------
Forecasts stay ARCHIVED OFFLINE and lookup-only: `archive` writes rolling-origin
parquets on the SAME origin grid benchmark.py uses (multiples of H=12, ctx
8072), into a NEW directory. Nothing endogenous is precomputed -- TTFT, queue
depth, replica decisions and SLA verdicts all still come from the discrete-event
mocker on silicon-calibrated timings. No thesis artifact is modified; every
output is a new file under defense/anim/data/a16_ft/.

STAGES
------
  split      print the train/test partition + episode assignment (free, no GPU)
  train      fine-tune on the train region -> a16_ft/ckpt/
  archive    rolling-origin forecasts from the ckpt -> a16_ft/archives/
  wape       zero-shot vs fine-tuned WAPE on held-out origins -> wape.json
  provision  p90 schedule diff + per-episode E2E verdicts -> provision.json
  all        train -> archive -> wape -> provision

Usage
-----
  # free, instant: verify the split and episode assignment
  python gen_a16_finetune.py split

  # smoke (what was actually run to validate this driver)
  python gen_a16_finetune.py all --smoke

  # full study (supervisor-staged)
  python gen_a16_finetune.py all
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/a16_ft"
CKPT = OUT / "ckpt"
ARCH = OUT / "archives"
RUNS = OUT / "runs"
PRED = ROOT / "predictors"
ZS_DIR = PRED / "results"  # zero-shot archives (READ ONLY -- never written)

EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
SRC_PY = ROOT / "ai-dynamo/dynamo/.venv/bin/python"
RR = ROOT / "simulation/run_replay.sh"
GEN = ROOT / "verification/scripts/forecast_schedule_issuetime.py"
CONV = ROOT / "defense/anim/build/a2_conv_snapshot.py"
ENTRY = ROOT / "simulation/replay_with_forecast.py"
SMOKE_CFG = ROOT / "simulation/planner_forecast_smoke.json"
WINJSON = ROOT / "defense/anim/data/windows_ext.json"

TRACE_T0 = np.datetime64("2024-10-15T12:00:00")
SPLIT_DAY = 3.0  # thesis: "fit days 1--3, test 4--7"
H = 12
VARIATES = ("requests", "images", "ctx", "gen")
# Resolutions the study needs: 15s drives provisioning (FORECAST_RESOLUTION=15s),
# 1min is the cadence the thesis's WAPE table is quoted at.
STUDY_RES = ("15s", "1min")
CTX = 8192 - (1 + 9) * H  # 8072 -- benchmark.py's chronos budget, matched exactly

FT_MODEL = "chronos_ft"  # archive basename => FORECAST_MODEL=chronos_ft

# Episodes in the held-out region, in ledger order. e13 first: it is the case
# the thesis flags as the p90 forecast-miss boundary.
TEST_EPISODES = ["e13", "e8", "e7", "e12", "e16", "burst5", "burst4", "burst1"]


# ----------------------------------------------------------------- split ----
def _res_seconds(res: str) -> float:
    return {"1s": 1.0, "15s": 15.0, "30s": 30.0, "45s": 45.0, "1min": 60.0}[res]


def split_step(res: str) -> int:
    """First step of the held-out region, in `res` bins."""
    return int(round(SPLIT_DAY * 86400 / _res_seconds(res)))


def episode_regions() -> dict[str, dict]:
    """Map every named window to its start timestamp and train/test region."""
    wins = json.load(open(WINJSON))
    split_ts = TRACE_T0 + np.timedelta64(int(SPLIT_DAY * 86400), "s")
    out = {}
    for name, w in wins.items():
        if not isinstance(w, dict):
            continue
        ts = None
        if "t0" in w:
            ts = np.datetime64(str(w["t0"]).replace(" ", "T"))
        elif "note" in w:
            m = re.search(r"\[(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)", w["note"])
            if m:
                ts = np.datetime64(f"{m.group(1)}T{m.group(2)}")
        if ts is None:
            continue
        out[name] = {
            "t0": str(ts).replace("T", " "),
            "day": round(float((ts - TRACE_T0) / np.timedelta64(1, "s")) / 86400, 3),
            "region": "test" if ts >= split_ts else "train",
            "offset": w.get("offset"),
            "max_requests": w.get("max_requests"),
            "peak_img_s": w.get("peak_1min_img_per_s"),
        }
    return out


def cmd_split(args: argparse.Namespace) -> None:
    regions = episode_regions()
    print(f"trace t0 = {TRACE_T0}   split at day {SPLIT_DAY} = "
          f"{TRACE_T0 + np.timedelta64(int(SPLIT_DAY * 86400), 's')}")
    print(f"train = bins [0, split)  |  eval = forecast origins >= split\n")
    for res in STUDY_RES:
        print(f"  {res:>5}: split_step={split_step(res)}  ctx={CTX}  H={H}")
    print()
    for name, r in sorted(regions.items(), key=lambda kv: kv[1]["day"]):
        mark = "TEST " if r["region"] == "test" else "train"
        peak = f"{r['peak_img_s']:6.1f}" if r["peak_img_s"] else "     -"
        print(f"  {name:14s} day={r['day']:6.3f} {mark} peak={peak} "
              f"n={r['max_requests']}")
    ntest = [n for n, r in regions.items() if r["region"] == "test"]
    print(f"\n{len(ntest)} held-out windows; provisioning set = {TEST_EPISODES}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "split.json").write_text(json.dumps(
        {"split_day": SPLIT_DAY, "trace_t0": str(TRACE_T0),
         "split_step": {r: split_step(r) for r in STUDY_RES},
         "ctx": CTX, "horizon": H, "windows": regions,
         "leakage_guarantee":
             "training series truncated at split_step; eval origins >= split_step "
             "so every predicted target is held out. Contexts may span the split "
             "(legitimate conditioning on observed history, identical for both arms).",
         }, indent=1))
    print(f"wrote {OUT / 'split.json'}")


# ----------------------------------------------------------------- train ----
def _load_series(res: str) -> tuple[dict[str, np.ndarray], np.ndarray]:
    sys.path.insert(0, str(PRED))
    import benchmark  # noqa: E402  (read-only reuse of the thesis harness)

    return benchmark.load_series(res)


class _EvalRecorder:
    """TrainerCallback capturing every eval_loss so the lr sweep can select on it.

    Defined lazily (transformers imported inside cmd_train) via _make_recorder().
    """


def _make_recorder():
    from transformers import TrainerCallback

    class Recorder(TrainerCallback):
        def __init__(self) -> None:
            self.history: list[tuple[int, float]] = []

        def on_evaluate(self, args, state, control, metrics=None, **kw):  # noqa: ANN001
            if metrics and "eval_loss" in metrics:
                self.history.append((int(state.global_step), float(metrics["eval_loss"])))

        @property
        def best(self) -> float | None:
            return min((v for _, v in self.history), default=None)

    return Recorder()


def cmd_train(args: argparse.Namespace) -> None:
    import torch
    from chronos import Chronos2Pipeline

    torch.set_float32_matmul_precision("high")
    CKPT.mkdir(parents=True, exist_ok=True)

    # Training pool: every (resolution, variate) series, TRUNCATED at the split.
    # Univariate, matching how the archive is generated + consumed (mode="uni").
    res_list = list(args.train_res)
    train_inputs, val_inputs, manifest = [], [], []
    for res in res_list:
        data, _ = _load_series(res)
        s = split_step(res)
        for v in VARIATES:
            full = data[v][:s]  # <-- the leakage guarantee
            cut = int(len(full) * (1.0 - args.val_frac))
            tr, va = full[:cut], full[cut:]
            if len(tr) >= args.min_past + H:
                train_inputs.append(np.asarray(tr, dtype=np.float32))
            if len(va) >= args.min_past + H:
                val_inputs.append(np.asarray(va, dtype=np.float32))
            manifest.append({"resolution": res, "variate": v, "split_step": s,
                             "train_len": len(tr), "val_len": len(va)})
    print(f"[train] {len(train_inputs)} train series, {len(val_inputs)} val series "
          f"(res={res_list}, truncated at split)", flush=True)

    if not val_inputs:
        sys.exit("[train] no validation series -- refusing to train without "
                 "model selection (see --val-frac).")

    base = Chronos2Pipeline.from_pretrained(str(ROOT / "models/chronos"),
                                            device_map=args.device)

    # Fine-tuning uses the SHIPPED, validated recipe (Chronos2Pipeline.fit), not a
    # hand-rolled Trainer: it does periodic eval on the (strictly pre-split) val
    # slice, checkpoints by steps, and restores the best-eval_loss weights
    # (load_best_model_at_end). Selection never touches the held-out region.
    # Learning rate: the library default for FULL fine-tuning is 1e-6; 1e-5 is the
    # elevated setting recommended for LoRA. The previous 5e-5 default was 50x the
    # full-FT default and decalibrated the p90 head (the provisioning signal).
    eval_every = max(1, min(100, args.max_steps // 10))
    lrs = list(args.lr_sweep) if args.lr_sweep else [args.lr]
    sweep: list[dict] = []
    best = {"val_loss": float("inf"), "lr": None, "pipeline": None}
    t0 = time.time()
    for lr in lrs:
        rec = _make_recorder()
        print(f"[train] fine-tune mode={args.finetune_mode} lr={lr:g} "
              f"steps={args.max_steps}", flush=True)
        ft = base.fit(
            inputs=train_inputs,
            prediction_length=H,
            validation_inputs=val_inputs,
            finetune_mode=args.finetune_mode,
            context_length=args.context_length,
            learning_rate=lr,
            num_steps=args.max_steps,
            batch_size=args.batch_size,
            min_past=args.min_past,
            output_dir=str(CKPT / f"hf_lr{lr:g}"),
            callbacks=[rec],
            eval_steps=eval_every,
            save_steps=eval_every,
            logging_steps=max(1, args.max_steps // 20),
            seed=args.seed,
            bf16=bool(args.bf16),
        )
        vl = rec.best
        sweep.append({"lr": lr, "val_loss": vl, "eval_history": rec.history})
        print(f"[train]   lr={lr:g} best val_loss={vl}", flush=True)
        if vl is not None and vl < best["val_loss"]:
            best = {"val_loss": vl, "lr": lr, "pipeline": ft}
        elif best["pipeline"] is None:
            best = {"val_loss": vl if vl is not None else float("inf"), "lr": lr,
                    "pipeline": ft}
    dt = time.time() - t0

    pipeline = best["pipeline"]
    # LoRA: fit returns a peft-wrapped model; merge the adapter so the saved
    # checkpoint is a plain Chronos2Model that Chronos2Predictor can load.
    if args.finetune_mode == "lora" and hasattr(pipeline.model, "merge_and_unload"):
        merged = pipeline.model.merge_and_unload()
        pipeline = type(pipeline)(model=merged)

    pipeline.save_pretrained(str(CKPT / "model"))
    val_loss = None if best["val_loss"] == float("inf") else best["val_loss"]
    meta = {"base": "models/chronos (Chronos-2, 120M)", "steps": args.max_steps,
            "finetune_mode": args.finetune_mode,
            "lr": best["lr"], "lr_sweep": lrs, "sweep": sweep,
            "selection": "min eval_loss on the pre-split val slice "
                         "(load_best_model_at_end within a run; min across the lr sweep)",
            "eval_every_steps": eval_every,
            "batch_size": args.batch_size,
            "context_length": args.context_length, "prediction_length": H,
            "train_res": res_list, "val_frac": args.val_frac,
            "split_day": SPLIT_DAY, "seed": args.seed,
            "train_seconds": round(dt, 1), "final_val_loss": val_loss,
            "series_manifest": manifest,
            "leakage": "series truncated at split_step before slicing; "
                       "val slice is the tail of the TRAIN region only"}
    (CKPT / "train_meta.json").write_text(json.dumps(meta, indent=1))
    print(f"[train] done in {dt / 60:.1f} min, selected lr={best['lr']} "
          f"val_loss={val_loss}; ckpt -> {CKPT / 'model'}", flush=True)


# --------------------------------------------------------------- archive ----
def cmd_archive(args: argparse.Namespace) -> None:
    """Rolling-origin forecasts from the fine-tuned ckpt, on benchmark.py's grid."""
    sys.path.insert(0, str(PRED))
    import pyarrow as pa
    import pyarrow.parquet as pq
    import benchmark  # noqa: E402
    from chronos2 import Chronos2Predictor  # noqa: E402

    ARCH.mkdir(parents=True, exist_ok=True)
    model_dir = args.ckpt or str(CKPT / "model")
    predictor = None
    per_res: dict[str, dict] = {}

    for res in args.res:
        data, ts = benchmark.load_series(res)
        n = len(ts)
        origins = benchmark.grid_origins(n, CTX)
        if args.eval_only:  # only the held-out origins (all we score / provision on)
            origins = origins[origins >= split_step(res)]
        # limit AFTER the held-out filter, else the smoke slice lands entirely in
        # the train region and the filter empties it.
        # `--origins-covering W` anchors the slice at window W instead of the first
        # held-out origins: without it a truncated (smoke) archive sits right at the
        # split and covers NO provisioning episode, so the `ft` arm dies with
        # "no forecast rows cover window ...". The full run leaves limit_origins
        # None and archives every held-out origin, so this is a smoke-only path.
        if getattr(args, "origins_covering", None):
            w = episode_regions()[args.origins_covering]
            t0w = np.datetime64(str(w["t0"]).replace(" ", "T"))
            step = int((t0w - TRACE_T0) / np.timedelta64(1, "s") / _res_seconds(res))
            first = int(np.searchsorted(origins, step, side="right")) - 1
            origins = origins[max(0, first - 1):]  # start one grid origin before W
        if args.limit_origins:
            origins = origins[: args.limit_origins]
        if len(origins) == 0:
            print(f"[archive] {res}: no origins (ctx {CTX} > series {n})", flush=True)
            continue
        wins = {v: np.lib.stride_tricks.sliding_window_view(data[v], CTX) for v in VARIATES}
        if predictor is None:
            predictor = Chronos2Predictor(H, freq_s=benchmark.RESOLUTIONS[res],
                                          model_dir=model_dir, device=args.device,
                                          batch_size=args.batch_size)
        else:
            predictor.freq_s = benchmark.RESOLUTIONS[res]

        chunks, t0 = [], time.time()
        for c0 in range(0, len(origins), args.chunk):
            sub = origins[c0: c0 + args.chunk]
            ctxs = {v: np.ascontiguousarray(wins[v][sub - CTX]) for v in VARIATES}
            for v in VARIATES:
                buckets = [benchmark.Bucket(f"{res}:{v}:{o}", benchmark.RESOLUTIONS[res],
                                            {v: ctxs[v][i]})
                           for i, o in enumerate(sub)]
                fc = predictor.predict_batch(buckets)
                chunks.append(benchmark._rows(res, v, sub, fc, data, ts))
            print(f"[archive] {res}: {min(c0 + args.chunk, len(origins))}/{len(origins)} "
                  f"origins ({time.time() - t0:.0f}s)", flush=True)
        per_res[res] = {"origins": len(origins), "seconds": round(time.time() - t0, 1)}
        merged = {k: np.concatenate([c[k] for c in chunks]) for k in chunks[0]}
        (ARCH / "parts").mkdir(exist_ok=True)
        pq.write_table(pa.Table.from_pydict(merged), ARCH / "parts" / f"{res}.parquet")

    # Assemble per-variate archives in the layout the downstream consumers expect:
    #   forecast_schedule_issuetime.py --parquet <...>_images.parquet
    #   replay_with_forecast.py  FORECAST_DIR=<ARCH> FORECAST_MODEL=chronos_ft
    import pyarrow.compute as pc
    parts = [pq.read_table(p) for p in sorted((ARCH / "parts").glob("*.parquet"))]
    if not parts:
        sys.exit("[archive] no parts written")
    table = pa.concat_tables(parts).sort_by(
        [("resolution", "ascending"), ("variate", "ascending"),
         ("step", "ascending"), ("h", "ascending")])
    meta = {b"model": b"chronos_ft", b"mode": b"uni",
            b"context_length": str(CTX).encode(), b"horizon": str(H).encode(),
            b"base": b"chronos-2 fine-tuned on trace days 1-3",
            b"split_day": str(SPLIT_DAY).encode(),
            b"source": b"analysis/trace_eda/series/rates_{resolution}.parquet"}
    for v in VARIATES:
        sub = table.filter(pc.equal(table["variate"], v))
        out = ARCH / f"{FT_MODEL}_{v}.parquet"
        pq.write_table(sub.replace_schema_metadata(meta), out)
        print(f"[archive] wrote {out.name} ({sub.num_rows} rows)", flush=True)
    (ARCH / "archive_meta.json").write_text(json.dumps(
        {"per_resolution": per_res, "ckpt": model_dir, "eval_only": args.eval_only}, indent=1))


# ------------------------------------------------------------------ wape ----
def _wape(y: np.ndarray, yhat: np.ndarray) -> float:
    """sum|yhat - y| / sum|y| -- matches predictors/precision.py."""
    denom = np.abs(y).sum()
    return float(np.abs(yhat - y).sum() / denom) if denom > 0 else float("nan")


def cmd_wape(args: argparse.Namespace) -> None:
    import pandas as pd

    rows = []
    p90_stats: dict = {}
    for res in args.res:
        s = split_step(res)
        for v in VARIATES:
            zs_p = ZS_DIR / f"chronos_{v}.parquet"
            ft_p = ARCH / f"{FT_MODEL}_{v}.parquet"
            if not (zs_p.exists() and ft_p.exists()):
                print(f"[wape] skip {res}/{v}: missing archive", flush=True)
                continue
            zs = pd.read_parquet(zs_p)
            ft = pd.read_parquet(ft_p)
            zs = zs[(zs.resolution == res) & (zs.origin >= s)]
            ft = ft[(ft.resolution == res) & (ft.origin >= s)]
            if zs.empty or ft.empty:
                continue
            # Score on the intersection of origins so the arms are like-for-like.
            keys = ["origin", "h"]
            m = zs.merge(ft, on=keys, suffixes=("_zs", "_ft"))
            if m.empty:
                continue
            y = m["y_true_zs"].to_numpy(float)
            assert np.allclose(y, m["y_true_ft"].to_numpy(float)), "y_true mismatch"
            rows.append({
                "resolution": res, "variate": v, "head": "point",
                "n": int(len(m)), "origins": int(m.origin.nunique()),
                "wape_zeroshot": _wape(y, m["point_zs"].to_numpy(float)),
                "wape_finetuned": _wape(y, m["point_ft"].to_numpy(float)),
            })
            # The p90 head is the PROVISIONING signal, and WAPE is the wrong
            # metric for a quantile (a narrower band trivially lowers |p90 - y|
            # while destroying the headroom the mechanism depends on). Score it
            # the two ways that actually matter:
            #   pinball(0.9) -- proper scoring rule for the 0.9 quantile
            #   exceedance   -- P(y > p90); a calibrated p90 sits near 0.10
            #                   (thesis measures 11% of common-span image bins)
            #   mean_p90     -- the provisioned-capacity level itself
            for arm in ("zs", "ft"):
                p90 = m[f"p90_{arm}"].to_numpy(float)
                d = y - p90
                pin = float(np.mean(np.where(d >= 0, 0.9 * d, -0.1 * d)))
                p90_stats[(res, v, arm)] = {
                    "pinball_q90": pin,
                    "exceedance": float(np.mean(y > p90)),
                    "mean_p90": float(p90.mean()),
                    "mean_y": float(y.mean()),
                }
            zsx, ftx = p90_stats[(res, v, "zs")], p90_stats[(res, v, "ft")]
            rows.append({
                "resolution": res, "variate": v, "head": "p90_provisioning",
                "n": int(len(m)), "origins": int(m.origin.nunique()),
                "wape_zeroshot": zsx["pinball_q90"], "wape_finetuned": ftx["pinball_q90"],
                "metric": "pinball_q90 (lower=better)",
                "exceedance_zs": round(zsx["exceedance"], 4),
                "exceedance_ft": round(ftx["exceedance"], 4),
                "mean_p90_zs": round(zsx["mean_p90"], 1),
                "mean_p90_ft": round(ftx["mean_p90"], 1),
                "mean_y": round(zsx["mean_y"], 1),
                "headroom_ratio_zs": round(zsx["mean_p90"] / zsx["mean_y"], 3)
                if zsx["mean_y"] else None,
                "headroom_ratio_ft": round(ftx["mean_p90"] / ftx["mean_y"], 3)
                if ftx["mean_y"] else None,
            })
            # h=1 slice, the horizon the schedule actually leans on
            m1 = m[m.h == 1]
            rows.append({
                "resolution": res, "variate": v, "head": "point_h1",
                "n": int(len(m1)), "origins": int(m1.origin.nunique()),
                "wape_zeroshot": _wape(m1["y_true_zs"].to_numpy(float),
                                       m1["point_zs"].to_numpy(float)),
                "wape_finetuned": _wape(m1["y_true_zs"].to_numpy(float),
                                        m1["point_ft"].to_numpy(float)),
            })
    for r in rows:
        rel = round((r["wape_zeroshot"] - r["wape_finetuned"]) / r["wape_zeroshot"] * 100, 2) \
            if r["wape_zeroshot"] else None
        if r["head"] == "p90_provisioning":
            # These fields hold pinball_q90 losses in RAW UNITS, not WAPE fractions.
            # Multiplying by 100 and calling it "percentage points" produced garbage
            # like delta_pp = 159997.393. Name them for what they are.
            r["delta_pinball"] = round(r["wape_finetuned"] - r["wape_zeroshot"], 4)
            r["rel_improvement_pct"] = rel
            r["units"] = "pinball_q90 in raw signal units (delta_pp not applicable)"
        else:
            r["delta_pp"] = round((r["wape_finetuned"] - r["wape_zeroshot"]) * 100, 3)
            r["rel_improvement_pct"] = rel
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wape.json").write_text(json.dumps(
        {"wape_def": "sum|yhat - y| / sum|y| (predictors/precision.py)",
         "eval": f"held-out origins >= day {SPLIT_DAY}", "rows": rows}, indent=1))
    acc = [r for r in rows if r["head"] in ("point", "point_h1")]
    print(f"\nACCURACY -- WAPE (%) on held-out origins (>= day {SPLIT_DAY})")
    print(f"{'res':>5} {'variate':>9} {'head':>9} {'origins':>8} "
          f"{'zero-shot':>10} {'fine-tuned':>11} {'delta_pp':>9} {'rel%':>7}")
    for r in acc:
        print(f"{r['resolution']:>5} {r['variate']:>9} {r['head']:>9} {r['origins']:>8} "
              f"{r['wape_zeroshot'] * 100:>10.3f} {r['wape_finetuned'] * 100:>11.3f} "
              f"{r['delta_pp']:>+9.3f} {r['rel_improvement_pct']:>+7.2f}")

    prov = [r for r in rows if r["head"] == "p90_provisioning"]
    print(f"\nPROVISIONING SIGNAL -- p90 head (the mechanism the thesis credits)")
    print(f"{'res':>5} {'variate':>9} {'pinball_zs':>11} {'pinball_ft':>11} "
          f"{'exc_zs':>7} {'exc_ft':>7} {'hdrm_zs':>8} {'hdrm_ft':>8}")
    for r in prov:
        print(f"{r['resolution']:>5} {r['variate']:>9} "
              f"{r['wape_zeroshot']:>11.2f} {r['wape_finetuned']:>11.2f} "
              f"{r['exceedance_zs']:>7.3f} {r['exceedance_ft']:>7.3f} "
              f"{str(r['headroom_ratio_zs']):>8} {str(r['headroom_ratio_ft']):>8}")
    print("  exc = P(y > p90); calibrated ~0.10.  hdrm = mean(p90)/mean(y).")
    print("  A fine-tune that lowers point WAPE but SHRINKS hdrm removes the very")
    print("  headroom the p90 mechanism relies on -- watch this before reading the")
    print("  accuracy table as good news.")
    print(f"\nwrote {OUT / 'wape.json'}")


# ------------------------------------------------------------- provision ----
def _sched(window: str, parquet: Path, out: Path, env: dict) -> dict:
    r = subprocess.run(
        [str(EDA_PY), str(GEN), "--window", window, "--quantile", "p90",
         "--rho", "15", "--cold-start-s", "30", "--parquet", str(parquet),
         "--out", str(out)], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        return {"error": f"sched: {r.stderr[-400:]}"}
    return {"schedule": json.load(open(out))}


def _staircase(sched: object) -> list:
    """Normalize a worker schedule to a comparable list of (t, workers) steps."""
    if isinstance(sched, dict):
        for k in ("schedule", "steps", "workers", "entries"):
            if k in sched:
                sched = sched[k]
                break
    out = []
    for e in sched if isinstance(sched, list) else []:
        if isinstance(e, dict):
            t = e.get("t") or e.get("time") or e.get("ts") or e.get("issue_time")
            w = e.get("workers") or e.get("n") or e.get("count") or e.get("replicas")
            out.append([t, w])
        elif isinstance(e, (list, tuple)) and len(e) >= 2:
            out.append([e[0], e[1]])
    return out


def _episode_arm(window: str, arm: str, wins: dict, env: dict,
                 ckpt_stamp: str | None = None) -> dict:
    """One (episode, arm) cell: encoder schedule -> composed trace -> language replay."""
    w = wins[window]
    tag = f"{window}_{arm}"
    d = RUNS / tag
    d.mkdir(parents=True, exist_ok=True)
    parquet = (ARCH / f"{FT_MODEL}_images.parquet") if arm == "ft" \
        else (ZS_DIR / "chronos_images.parquet")
    res: dict = {"window": window, "arm": arm, "day": w["day"], "region": w["region"],
                 "ckpt_stamp": ckpt_stamp if arm == "ft" else None}

    s = _sched(window, parquet, d / "enc.sched.json", env)
    if "error" in s:
        return {**res, **s}
    res["staircase"] = _staircase(s["schedule"])
    res["peak_workers"] = max((x[1] for x in res["staircase"] if x[1] is not None),
                              default=None)

    n = w["max_requests"]
    trace = d / "composed.jsonl"
    r = subprocess.run(
        [str(AIC_PY), str(CONV), "--out", str(trace), "--offset", str(w["offset"]),
         "--max-requests", str(n), "--encoder-workers", "2",
         "--worker-schedule", str(d / "enc.sched.json"),
         "--series-out", str(d / "enc.series.json")],
        capture_output=True, text=True, env=env)
    if r.returncode != 0:
        return {**res, "error": f"conv: {r.stderr[-400:]}"}
    st = json.load(open(f"{trace}.stats.json"))
    ed = st["encoder_delay_ms"]
    # p99 alone is saturated by the shared 1-worker cold-start head and can be
    # byte-identical between arms while the pool demonstrably changed; keep the
    # responsive statistics too (p50/p90/max + provisioned worker-seconds).
    res["enc_p50"] = round(ed["p50"], 1)
    res["enc_p90"] = round(ed["p90"], 1)
    res["enc_p99"] = round(ed["p99"], 1)
    res["enc_max"] = round(ed.get("max", float("nan")), 1)
    res["prov_worker_s"] = round(
        st.get("worker_schedule", {}).get("provisioned_worker_seconds",
                                          st.get("provisioned_worker_seconds", 0.0)), 1)
    res["enc_requests"] = sum(1 for _ in open(trace))

    lenv = {**env, "RUST_LOG": "warn", "AIC_TP": "2", "AIC_VER": "0.19.0",
            "REPLAY_PY": str(SRC_PY), "STARTUP_TIME": "60",
            "REPLAY_ENTRY": str(ENTRY), "FORECAST_T0": w["t0"],
            "FORECAST_QUANTILE": "p90", "FORECAST_RESOLUTION": "15s",
            "FORECAST_REQ_SCALE": "8.0",
            "FORECAST_MODEL": FT_MODEL if arm == "ft" else "chronos",
            "FORECAST_DIR": str(ARCH) if arm == "ft" else str(ZS_DIR)}
    rep = d / "e2e.report.json"
    with open(d / "e2e.log", "w") as log:
        r = subprocess.run(
            ["bash", str(RR), str(trace), "aic", str(rep), "2",
             "--planner-config", str(SMOKE_CFG),
             "--report-jsonl", str(d / "e2e.requests.jsonl")],
            stdout=log, stderr=subprocess.STDOUT, env=lenv)
    if r.returncode != 0:
        return {**res, "error": f"lang rc={r.returncode} (see {d / 'e2e.log'})"}
    rp = json.load(open(rep))
    res.update({
        "lang_requests": sum(1 for _ in open(d / "e2e.requests.jsonl")),
        "completed": rp["completed_requests"],
        "ttft_p99": round(rp["p99_ttft_ms"], 1),
        "itl_p99": round(rp["p99_itl_ms"], 1),
        "gpu_h": round(rp["gpu_hours"], 3),
    })
    res["e2e_p99"] = round(res["enc_p99"] + res["ttft_p99"], 1)
    # GRADING CONVENTION -- must match the ledger, else A16 contradicts A2/A12.
    #   encoder pool : encoder delay p99 <= 1000 ms   (A2, extract_a2_fleet.py:73)
    #   language pool: TTFT p99 <= 1000 ms AND ITL p99 <= 100 ms  (§0 SLA)
    #   composed E2E : enc p99 + TTFT p99 <= 2000 ms  (the two per-pool budgets;
    #                  conservative upper bound -- this is a sum of marginal p99s,
    #                  not A12's request-linked composed p99)
    # A language-only verdict scored e13 (an ENCODER-side failure, enc_p99 = 6.1 s)
    # as PASS, which made the "does fine-tuning rescue e13?" question unanswerable.
    res["verdict_enc"] = "PASS" if res["enc_p99"] <= 1000.0 else "FAIL"
    res["verdict_lang"] = "PASS" if (res["ttft_p99"] <= 1000.0
                                     and res["itl_p99"] <= 100.0) else "FAIL"
    res["verdict_e2e"] = "PASS" if res["e2e_p99"] <= 2000.0 else "FAIL"
    res["verdict"] = "PASS" if (res["verdict_enc"] == "PASS"
                                and res["verdict_lang"] == "PASS"
                                and res["verdict_e2e"] == "PASS") else "FAIL"
    return res


def _ckpt_stamp() -> str | None:
    """Identity of the fine-tuned checkpoint, so resumed `ft` cells can be
    invalidated when the model changes. Hash of the weight file(s) + train_meta."""
    import hashlib

    md = CKPT / "model"
    if not md.exists():
        return None
    h = hashlib.sha256()
    for f in sorted(md.rglob("*")):
        if f.is_file():
            st = f.stat()
            h.update(f.name.encode())
            h.update(str(st.st_size).encode())
            h.update(str(int(st.st_mtime)).encode())
    tm = CKPT / "train_meta.json"
    if tm.exists():
        h.update(tm.read_bytes())
    return h.hexdigest()[:16]


def _accuracy_verdict() -> dict:
    """Did fine-tuning actually improve accuracy? Read wape.json, do not assume.

    `ft_better` is None when the answer is unknown (no wape.json / no point rows).
    Also flags p90 decalibration, since the p90 head -- not the point head -- is
    what provisioning consumes.
    """
    p = OUT / "wape.json"
    if not p.exists():
        return {"ft_better": None, "n_point": 0, "n_better": 0,
                "reason": "wape.json absent"}
    rows = json.load(open(p)).get("rows", [])
    pts = [r for r in rows if r.get("head") in ("point", "point_h1")
           and r.get("wape_zeroshot") is not None]
    if not pts:
        return {"ft_better": None, "n_point": 0, "n_better": 0,
                "reason": "no point rows in wape.json"}
    n_better = sum(1 for r in pts if r["wape_finetuned"] <= r["wape_zeroshot"])
    p90 = [r for r in rows if r.get("head") == "p90_provisioning"]
    decal = [{"resolution": r["resolution"], "variate": r["variate"],
              "headroom_zs": r.get("headroom_ratio_zs"),
              "headroom_ft": r.get("headroom_ratio_ft"),
              "exceedance_zs": r.get("exceedance_zs"),
              "exceedance_ft": r.get("exceedance_ft")}
             for r in p90
             if r.get("headroom_ratio_zs") and r.get("headroom_ratio_ft")
             and abs(r["headroom_ratio_ft"] - r["headroom_ratio_zs"])
             > 0.05 * r["headroom_ratio_zs"]]
    return {
        "ft_better": bool(n_better == len(pts)),
        "ft_better_majority": bool(n_better * 2 > len(pts)),
        "n_point": len(pts), "n_better": n_better,
        "p90_decalibrated_rows": decal,
        "criterion": "ft_better = point WAPE <= zero-shot on ALL point/point_h1 rows",
    }


def cmd_provision(args: argparse.Namespace) -> None:
    wins = episode_regions()
    env = {**os.environ, "TESE_WINDOWS": str(WINJSON), "TESE_ROOT": str(ROOT)}
    RUNS.mkdir(parents=True, exist_ok=True)
    episodes = args.episodes or TEST_EPISODES
    bad = [e for e in episodes if wins.get(e, {}).get("region") != "test"]
    if bad and not args.allow_train_region:
        sys.exit(f"refusing: {bad} are in the TRAIN region (contaminated). "
                 f"--allow-train-region to override (results are NOT honest).")

    cells = [(e, a) for e in episodes for a in ("zs", "ft")]
    ckpt_stamp = _ckpt_stamp()
    results: dict[str, dict] = {}
    if (OUT / "provision.json").exists() and args.resume:
        results = json.load(open(OUT / "provision.json")).get("cells", {})
        # An `ft` cell computed against a DIFFERENT checkpoint is stale: re-training
        # must not be silently mixed with old fine-tuned cells.
        stale = [k for k, v in results.items()
                 if v.get("arm") == "ft" and v.get("ckpt_stamp") != ckpt_stamp]
        for k in stale:
            results.pop(k)
        if stale:
            print(f"[provision] invalidated {len(stale)} ft cell(s) from a different "
                  f"checkpoint: {sorted(stale)}", flush=True)
    todo = [c for c in cells if f"{c[0]}_{c[1]}" not in results]

    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(_episode_arm, e, a, wins, env, ckpt_stamp): (e, a)
                for e, a in todo}
        for f in as_completed(futs):
            e, a = futs[f]
            r = f.result()
            results[f"{e}_{a}"] = r
            print(f"[{e}/{a}] " + (r.get("error") or
                  f"enc_p90={r['enc_p90']} enc_p99={r['enc_p99']} "
                  f"ttft_p99={r['ttft_p99']} e2e={r['e2e_p99']} "
                  f"prov_ws={r['prov_worker_s']} {r['verdict']}"), flush=True)

    # The question that matters: did fine-tuning change the provisioning outcome?
    comparison = []
    for e in episodes:
        z, f_ = results.get(f"{e}_zs", {}), results.get(f"{e}_ft", {})
        if "error" in z or "error" in f_ or not z or not f_:
            comparison.append({"window": e, "error": z.get("error") or f_.get("error")
                               or "missing"})
            continue
        vt_zs = (z.get("verdict_enc"), z.get("verdict_lang"), z.get("verdict_e2e"))
        vt_ft = (f_.get("verdict_enc"), f_.get("verdict_lang"), f_.get("verdict_e2e"))
        comparison.append({
            "window": e, "day": z.get("day"),
            "schedule_changed": z.get("staircase") != f_.get("staircase"),
            "peak_workers_zs": z.get("peak_workers"), "peak_workers_ft": f_.get("peak_workers"),
            "prov_worker_s_zs": z.get("prov_worker_s"),
            "prov_worker_s_ft": f_.get("prov_worker_s"),
            "enc_p90_zs": z.get("enc_p90"), "enc_p90_ft": f_.get("enc_p90"),
            "enc_p99_zs": z.get("enc_p99"), "enc_p99_ft": f_.get("enc_p99"),
            "enc_max_zs": z.get("enc_max"), "enc_max_ft": f_.get("enc_max"),
            "ttft_p99_zs": z.get("ttft_p99"), "ttft_p99_ft": f_.get("ttft_p99"),
            "e2e_p99_zs": z.get("e2e_p99"), "e2e_p99_ft": f_.get("e2e_p99"),
            "gpu_h_zs": z.get("gpu_h"), "gpu_h_ft": f_.get("gpu_h"),
            "verdict_enc_zs": vt_zs[0], "verdict_enc_ft": vt_ft[0],
            "verdict_lang_zs": vt_zs[1], "verdict_lang_ft": vt_ft[1],
            "verdict_e2e_zs": vt_zs[2], "verdict_e2e_ft": vt_ft[2],
            "verdict_zs": z.get("verdict"), "verdict_ft": f_.get("verdict"),
            "verdict_changed": vt_zs != vt_ft,
        })
    n_sched = sum(1 for c in comparison if c.get("schedule_changed"))
    n_verdict = sum(1 for c in comparison if c.get("verdict_changed"))
    e13 = next((c for c in comparison if c["window"] == "e13" and "error" not in c), None)
    # e13 is an ENCODER-side failure boundary; "rescued" must be graded on the
    # encoder/E2E verdict, not on language TTFT (which passes either way).
    if e13 is None:
        e13_rescued = None  # absent / errored -- not measured, not False
    else:
        failed_zs = "FAIL" in (e13["verdict_enc_zs"], e13["verdict_e2e_zs"])
        passed_ft = (e13["verdict_enc_ft"] == "PASS"
                     and e13["verdict_e2e_ft"] == "PASS"
                     and e13["verdict_lang_ft"] == "PASS")
        e13_rescued = bool(failed_zs and passed_ft)

    # The interpretation is only licensed if the fine-tune actually IMPROVED
    # accuracy. A degraded fine-tune leaving verdicts unchanged is "our recipe
    # failed", not "the system is accuracy-saturated" -- the latter would be a
    # FALSE negative dressed up as a finding.
    acc = _accuracy_verdict()
    if acc["ft_better"] is None:
        interp = ("INCONCLUSIVE: wape.json missing/empty -- cannot tell whether the "
                  "fine-tune improved accuracy, so no saturation claim is licensed.")
    elif not acc["ft_better"]:
        interp = (f"RECIPE-FAILED: fine-tuning did NOT improve point WAPE "
                  f"({acc['n_better']}/{acc['n_point']} rows better). No "
                  f"forecasting-side upper-bound or accuracy-saturation claim is "
                  f"licensed from this run; report it as a failed fine-tune recipe.")
    elif n_verdict == 0:
        interp = (f"ACCURACY-SATURATED: fine-tuning improved point WAPE "
                  f"({acc['n_better']}/{acc['n_point']} rows better) yet moved no "
                  f"provisioning verdict; the p90 headroom mechanism carries the result.")
    else:
        interp = (f"NOT saturated: fine-tuning improved point WAPE "
                  f"({acc['n_better']}/{acc['n_point']} rows) AND changed "
                  f"{n_verdict} provisioning verdict(s).")
    summary = {
        "episodes": len(comparison),
        "schedules_changed": n_sched,
        "verdicts_changed": n_verdict,
        "cells_errored": sum(1 for c in comparison if "error" in c),
        "verdict_tuple": "(encoder, language, composed-E2E)",
        "grading": {"encoder_delay_p99_ms": 1000.0, "ttft_p99_ms": 1000.0,
                    "itl_p99_ms": 100.0, "e2e_p99_ms": 2000.0,
                    "note": "matches A2 (encoder delay p99 vs 1000 ms) and the §0 SLA"},
        "accuracy_check": acc,
        "e13_rescued": e13_rescued,
        "interpretation": interp,
    }
    (OUT / "provision.json").write_text(json.dumps(
        {"summary": summary, "ckpt_stamp": ckpt_stamp,
         "comparison": comparison, "cells": results}, indent=1))
    print("\n" + "=" * 110)
    print(f"{'window':>8} {'sched?':>7} {'encp90_zs':>9} {'encp90_ft':>9} "
          f"{'encp99_zs':>9} {'encp99_ft':>9} {'ttft_zs':>8} {'ttft_ft':>8} "
          f"{'e2e_zs':>8} {'e2e_ft':>8} {'zs(E/L/E2E)':>12} {'ft(E/L/E2E)':>12} "
          f"{'changed?':>9}")
    for c in comparison:
        if "error" in c:
            print(f"{c['window']:>8}  ERROR {c['error'][:50]}")
            continue
        tz = "/".join(x[0] for x in (c['verdict_enc_zs'], c['verdict_lang_zs'],
                                     c['verdict_e2e_zs']))
        tf = "/".join(x[0] for x in (c['verdict_enc_ft'], c['verdict_lang_ft'],
                                     c['verdict_e2e_ft']))
        print(f"{c['window']:>8} {str(c['schedule_changed']):>7} "
              f"{c['enc_p90_zs']:>9.1f} {c['enc_p90_ft']:>9.1f} "
              f"{c['enc_p99_zs']:>9.1f} {c['enc_p99_ft']:>9.1f} "
              f"{c['ttft_p99_zs']:>8.1f} {c['ttft_p99_ft']:>8.1f} "
              f"{c['e2e_p99_zs']:>8.1f} {c['e2e_p99_ft']:>8.1f} "
              f"{tz:>12} {tf:>12} {str(c['verdict_changed']):>9}")
    print("=" * 110)
    print("  verdict tuple = (Encoder p99<=1000, Language TTFT/ITL, composed E2E<=2000);"
          " P=PASS F=FAIL")
    print(json.dumps(summary, indent=1))
    print(f"\nwrote {OUT / 'provision.json'}")


# ------------------------------------------------------------------ main ----
def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("split", help="print/write the train-test partition (free)")

    t = sub.add_parser("train", help="fine-tune Chronos-2 on the train region")
    t.add_argument("--max-steps", type=int, default=2000)
    # 1e-6 = the shipped library default for FULL fine-tuning (Chronos2Pipeline.fit).
    # The old 5e-5 was 50x that and decalibrated the p90 provisioning head.
    t.add_argument("--lr", type=float, default=1e-6)
    t.add_argument("--lr-sweep", type=float, nargs="+", default=None,
                   help="train one model per lr and keep the best val_loss "
                        "(e.g. --lr-sweep 1e-6 5e-6 1e-5)")
    t.add_argument("--finetune-mode", choices=["full", "lora"], default="full",
                   help="lora recommends lr ~1e-5")
    t.add_argument("--batch-size", type=int, default=32)
    t.add_argument("--context-length", type=int, default=CTX)
    t.add_argument("--min-past", type=int, default=64)
    t.add_argument("--val-frac", type=float, default=0.1)
    t.add_argument("--train-res", nargs="+", default=["15s", "1min", "30s", "45s"])
    t.add_argument("--device", default="cuda")
    t.add_argument("--bf16", action="store_true", default=True)
    t.add_argument("--no-bf16", dest="bf16", action="store_false")
    t.add_argument("--seed", type=int, default=0)

    a = sub.add_parser("archive", help="rolling-origin forecasts from the ckpt")
    a.add_argument("--res", nargs="+", default=list(STUDY_RES))
    a.add_argument("--chunk", type=int, default=256)
    a.add_argument("--batch-size", type=int, default=256)
    a.add_argument("--limit-origins", type=int, default=None)
    a.add_argument("--origins-covering", default=None,
                   help="anchor a truncated archive at this window (smoke only)")
    a.add_argument("--eval-only", action="store_true", default=True,
                   help="only held-out origins (all the study scores/provisions on)")
    a.add_argument("--all-origins", dest="eval_only", action="store_false")
    a.add_argument("--ckpt", default=None)
    a.add_argument("--device", default="cuda")

    w = sub.add_parser("wape", help="zero-shot vs fine-tuned WAPE, held-out only")
    w.add_argument("--res", nargs="+", default=list(STUDY_RES))

    p = sub.add_parser("provision", help="p90 schedule diff + per-episode E2E verdicts")
    p.add_argument("--episodes", nargs="+", default=None)
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--resume", action="store_true", default=True)
    p.add_argument("--no-resume", dest="resume", action="store_false")
    p.add_argument("--allow-train-region", action="store_true")

    al = sub.add_parser("all", help="train -> archive -> wape -> provision")
    al.add_argument("--smoke", action="store_true",
                    help="tiny: 20 steps, 32 origins, e13 only")
    al.add_argument("--jobs", type=int, default=2)
    al.add_argument("--lr-sweep", type=float, nargs="+", default=[1e-6, 5e-6, 1e-5],
                    help="lr sweep for the full run; selection on val loss")
    al.add_argument("--finetune-mode", choices=["full", "lora"], default="full")

    args = ap.parse_args()
    if args.cmd == "all":
        ns = argparse.Namespace
        if args.smoke:
            cmd_train(ns(max_steps=20, lr=1e-6, lr_sweep=None, finetune_mode="full",
                         batch_size=8, context_length=2048,
                         min_past=64, val_frac=0.1, train_res=["1min"],
                         device="cuda", bf16=True, seed=0))
            cmd_archive(ns(res=["15s"], chunk=32, batch_size=32, limit_origins=32,
                           origins_covering="e13", eval_only=True, ckpt=None,
                           device="cuda"))
            cmd_wape(ns(res=["15s"]))
            cmd_provision(ns(episodes=["e13"], jobs=1, resume=False,
                             allow_train_region=False))
        else:
            cmd_train(ns(max_steps=2000, lr=1e-6,
                         lr_sweep=args.lr_sweep, finetune_mode=args.finetune_mode,
                         batch_size=32, context_length=CTX,
                         min_past=64, val_frac=0.1,
                         train_res=["15s", "1min", "30s", "45s"],
                         device="cuda", bf16=True, seed=0))
            cmd_archive(ns(res=list(STUDY_RES), chunk=256, batch_size=256,
                           limit_origins=None, origins_covering=None,
                           eval_only=True, ckpt=None, device="cuda"))
            cmd_wape(ns(res=list(STUDY_RES)))
            cmd_provision(ns(episodes=None, jobs=args.jobs, resume=True,
                             allow_train_region=False))
        return
    {"split": cmd_split, "train": cmd_train, "archive": cmd_archive,
     "wape": cmd_wape, "provision": cmd_provision}[args.cmd](args)


if __name__ == "__main__":
    main()
