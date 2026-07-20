#!/usr/bin/env python3
"""G4 — within-trace TEMPORAL GENERALIZATION of the closed-loop headline claims.

WHAT GAP THIS ADDRESSES
-----------------------
tex/closedloop.tex (Limitations) concedes:

    "every quantity here (the 4x/2x over-provisioning, the rho frontier, the
     0.62x) derives from a single Azure production trace over one 5.60-day
     span; generalization to other workloads, models, and datacenters is
     unaddressed."

We cannot obtain another datacenter's trace. What we CAN do is split the ONE
trace into disjoint contiguous folds and ask whether the headline quantities
are properties of *the span as a whole* (a single lucky 5.6-day average) or
reproduce independently inside each fold. That is a real, bounded, honest
partial answer: it converts "n=1 span" into "n=7 disjoint diurnal cycles,
each independently graded". It does NOT establish cross-workload or
cross-datacenter generalization, and nothing in the output should be read
that way.

FOLD SCHEME AND ITS JUSTIFICATION
---------------------------------
Seven disjoint contiguous 24-hour folds, cut at 12:00 UTC (the trace's own
start-of-record phase):

    F1  2024-10-15 12:00 -> 10-16 12:00      F5  10-19 12:00 -> 10-20 12:00
    F2  2024-10-16 12:00 -> 10-17 12:00      F6  10-20 12:00 -> 10-21 12:00
    F3  2024-10-17 12:00 -> 10-18 12:00      F7  10-21 12:00 -> 10-22 12:00
    F4  2024-10-18 12:00 -> 10-19 12:00

Why 24 h and why this phase:

1. DIURNAL PHASE ALIGNMENT. tex/trace-eda.tex establishes that the dominant
   spectral structure is a diurnal harmonic family (24 h fundamental plus
   harmonics) with no dominant non-harmonic sub-diurnal line. A fold length
   that is not a whole multiple of 24 h would give folds different *phases*
   of the driving cycle, so any cross-fold spread would confound "policy is
   fold-unstable" with "these folds are not the same kind of object". One
   full diurnal cycle per fold is the smallest unit that is phase-comparable.
2. DISJOINT AND EXHAUSTIVE. The seven folds tile the forecastable trace
   exactly (F1 already trimmed by its first F1_SKIP=401 requests -- see 3):
   173,057 + 183,285 + 186,359 + 135,637 + 72,547 + 84,329 + 164,385
   = 999,599 requests = 1,000,000 - 401 pre-forecast head. No fold shares a
   request with another, so the seven verdicts are not re-reads of the same
   data.
3. FORECAST GRADABILITY. The fixed-context archives only begin 1.4 days in,
   which is exactly why per-fold grading was impossible before: F1-F2 had no
   forecast. The NEW expanding-context archives
   (predictors/results/{model}_{signal}_expctx.parquet) issue their first
   forecast at 2024-10-15 12:03:00, 3 min into the trace. F1 therefore starts
   at offset 401 (t0 = 12:03:00.013) so that every fold is graded by a
   forecast policy that was actually archived over it, with NO look-ahead
   into a bin whose forecast does not exist. All seven folds are forecast-
   gradable; this driver is only possible because of the expctx archives.
4. BURST CONTENT (gradability). Of the 18 detected burst episodes, the folds
   carry: F1 {burst2, burst6, e18}, F3 {burst3, e9, e10, e11, e14, e15, e17},
   F4 {burst4, burst5, e7}, F6 {e13, e16}, F7 {burst1, e8, e12}. F2 and F5
   contain NO top-18 episode -- they are the trace's quiet stretches (1-min
   image peaks 111.6 and 61.2 img/s vs 337-370 in the burst folds). They are
   retained and run, but reported as QUIET CONTROLS, not as evidence about
   burst-handling: on a fold with no burst the static-optimal fleet collapses
   to a small C and the forecast policy has little to anticipate, so its cost
   ratio is a different quantity. The fold-stability verdict is computed over
   the five BURST-BEARING folds, with the quiet folds shown alongside. Any
   other choice (dropping them silently, or averaging them in) would be
   dishonest in opposite directions.

ANCHOR FOLD (FULL) AND THE WHOLE-SPAN STATIC LADDER
---------------------------------------------------
Every sibling fleet (A11/A12/A14/A15) reproduces a ledgered endpoint exactly;
without one, nothing links THIS harness to the harness that produced the 0.62x.
So a pseudo-fold FULL (offset 401, 999,599 requests, t0 2024-10-15 12:03:00.013
-- byte-identical span to A15) is run through the identical encoder path and
asserted against the ledgered artifacts:

    enc p99      == 588.4 ms +/- 1 ms   (a15_runs/chronos_composed.jsonl.stats)
    provisioned  == 2,962,304.8 ws +/- 0.5%          (same)
    ratio_vs_C8  == 0.612 +/- 0.005     (C8 = 8 * sim_horizon over that span;
                                         cross-checked vs a13_runs/ft_static_C8)
    lang TTFT p99 == 651.1 ms +/- 5 ms  (a15_runs/chronos_e2e.report.json)
                                         -- only with --anchor-lang (~2 h)

The FULL fold ALSO sweeps static C in {1..8} over the whole span, which settles
a question the thesis never actually answered: a13_runs swept only C2 (FAIL)
and C8 (PASS), so C8 was ASSERTED, never verified, as the whole-span static
optimum -- and C8 is the DENOMINATOR of the 0.62x. If the whole-span C* < 8 the
headline must be restated as "vs the deployed C=8 fleet", not "vs the static
optimum". folds_table.md states the answer explicitly either way.

FULL overlaps every other fold by construction. It is an ANCHOR and a
DENOMINATOR CHECK ONLY: it is excluded from the fold partition, from every
cross-fold claim, and from every aggregate.

WHAT IS MEASURED PER FOLD
-------------------------
Encoder pool (RTX 5090, AIC-costed, converter with per-second series):
  * forecast p90, L=30 s issue-time actuation, rho in {10,15,20,25}
    -> the rho FRONTIER, per fold
  * reactive rho15/L30 (15-s trailing observation)
  * static C in {1..8}  -> the per-fold STATIC-OPTIMAL C*(f) = smallest C
    whose encoder-delay p99 <= 1000 ms
Language pool (H100, dynamo.replay mocker, TP2, per-request records) on the
matching composed trace, for three arms: forecast (planner_forecast_smoke +
FORECAST_SUFFIX=_expctx), reactive (SLA/ARIMA ladder), static (TP2x2, no
planner).

Headline quantities graded per fold:
  cost_ratio_vs_C8    = ws(forecast rho15) / ws(static C=8)   <- the 0.62x
  cost_ratio_vs_Cstar = ws(forecast rho15) / ws(static C*(f)) <- the harder
        test: re-optimize the baseline inside each fold, so the forecast
        policy is not being flattered by a fleet sized for a different day.
  rho frontier        = cost ratio + p99 at rho in {10,15,20,25}
  reactive/forecast pass-fail pattern, encoder AND language, per fold.

METHODOLOGY PRESERVED
---------------------
Forecasts are read from the OFFLINE rolling-origin archives only (lookup, no
in-flight inference). Everything endogenous -- encoder queueing, TTFT, ITL,
replica scaling decisions, SLA verdicts -- is computed by the discrete-event
mocker from silicon-calibrated timings. Identical to A2/A11/A12/A15.

THE FOLDS ARE NOT i.i.d. REPLICATES
-----------------------------------
The folds are disjoint TEST windows -- no request appears in two of them. But
the expanding-context forecaster's CONDITIONING HISTORY IS NESTED: the forecast
issued inside fold 5 is conditioned on the observed history of folds 1-4. That
is legitimate operator history (it is exactly what a deployed forecaster would
have) and it is NOT leakage -- no forecast ever sees its own future, every
origin is strictly causal. But it does mean the seven verdicts are not
independent draws. Consequently NO confidence interval, standard error, or
significance test may be computed across folds, and none is reported here. The
per-fold numbers are seven graded observations, min/median/max only.

USAGE
-----
  # everything (supervisor's single command)
  ai-dynamo/aiconfigurator/.venv/bin/python defense/anim/build/gen_g4_folds.py \
      --folds FULL,F1,F2,F3,F4,F5,F6,F7 --anchor-lang

  # smoke: plumbing only -- ALWAYS stamps a SMOKE banner and refuses a verdict
  ... gen_g4_folds.py --folds F5 --smoke 2000

Stages are resumable. A cached cell is reused ONLY if its recorded request
count matches what the current invocation would simulate, so a --smoke cell can
never be silently promoted to a full-scale result (it was, once -- see the
SMOKE banner machinery; that incident is why this guard exists).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/g4_folds"
EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
SRC_PY = ROOT / "ai-dynamo/dynamo/.venv/bin/python"
CONV = ROOT / "defense/anim/build/a2_conv_snapshot.py"
RR = ROOT / "simulation/run_replay.sh"
GEN_ISSUE = ROOT / "verification/scripts/forecast_schedule_issuetime.py"
GEN_SCHED = ROOT / "simulation/forecast_schedule.py"
ENTRY = ROOT / "simulation/replay_with_forecast.py"
SMOKE_PLANNER = ROOT / "simulation/planner_forecast_smoke.json"
LADDER = ROOT / "simulation/results/riders44/planner_ladder_t200_20.json"
TRACE = ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz"
WINJSON = OUT / "windows_folds.json"
RESJSON = OUT / "results.json"

MODEL = "chronos"          # thesis headline forecaster (smallest of the three)
RHOS = [10, 15, 20, 25]    # the rho frontier
RHO_HEADLINE = 15
STATIC_CS = [1, 2, 3, 4, 5, 6, 7, 8]
C_DEPLOYABLE = 8           # the thesis's deployable static fleet
LEAD_S = 30                # encoder cold-start lead L
ENC_P99_BOUND_MS = 1000.0  # encoder-delay tail bound (tex/closedloop.tex)
TTFT_P99_BOUND_MS = 1000.0
ITL_P99_BOUND_MS = 100.0
FOLD_HOURS = 24
N_FOLDS = 7
F1_SKIP = 401              # first expctx-forecastable request (t0 = 12:03:00)

FOLD_IDS = [f"F{i + 1}" for i in range(N_FOLDS)]
# Folds with >=1 of the 18 detected burst episodes; F2/F5 are quiet controls.
BURST_FOLDS = {"F1", "F3", "F4", "F6", "F7"}

# ---- anchor pseudo-fold: the whole expctx-forecastable span, = A15's span ----
ANCHOR = "FULL"
ALL_IDS = [ANCHOR] + FOLD_IDS
A15_STATS = ROOT / "defense/anim/data/a15_runs/chronos_composed.jsonl.stats.json"
A15_REPORT = ROOT / "defense/anim/data/a15_runs/chronos_e2e.report.json"
A13_C8_STATS = ROOT / "defense/anim/data/a13_runs/ft_static_C8.jsonl.stats.json"
ANCHOR_TOL = {"enc_p99_ms": 1.0,          # absolute ms
              "provisioned_ws_rel": 0.005,  # 0.5 %
              "ratio_vs_C8": 0.005,       # absolute
              "ttft_p99_ms": 5.0}         # absolute ms


# --------------------------------------------------------------------------
# stage 0: fold windows (computed once from the trace, cached)
# --------------------------------------------------------------------------
def add_anchor(wins: dict) -> dict:
    """Derive the FULL anchor pseudo-fold from the tiling folds (no trace read).

    FULL spans exactly [F1.t0 .. F7.t_end] = A15's span_expctx: offset 401,
    999,599 requests. It OVERLAPS every fold and is never part of the fold
    partition -- it exists to reproduce a ledgered endpoint and to sweep the
    whole-span static ladder that fixes the 0.62x denominator.
    """
    if ANCHOR in wins:
        return wins
    import datetime as _dt
    f1, f7 = wins["F1"], wins["F7"]
    t0 = _dt.datetime.fromisoformat(f1["t0"])
    te = _dt.datetime.fromisoformat(f7["t_end"])
    span = sum(w["span_s"] for w in wins.values())
    wins[ANCHOR] = {
        "offset": f1["offset"],
        "max_requests": sum(wins[f]["max_requests"] for f in FOLD_IDS),
        "requests": sum(wins[f]["max_requests"] for f in FOLD_IDS),
        "span_s": round((te - t0).total_seconds(), 1),
        "t0": f1["t0"], "t_end": f7["t_end"], "utc_day": f1["utc_day"],
        # derived from the folds (span-weighted), descriptive only, never graded
        "mean_img_per_s": round(
            sum(wins[f]["mean_img_per_s"] * wins[f]["span_s"]
                for f in FOLD_IDS) / span, 2),
        "peak_1min_img_per_s": max(wins[f]["peak_1min_img_per_s"]
                                   for f in FOLD_IDS),
        "p99_1min_img_per_s": None,   # not derivable from per-fold p99s
        "episodes": sorted({e for f in FOLD_IDS for e in wins[f]["episodes"]}),
        "burst_bearing": False,       # excluded from the partition entirely
        "anchor": True,
        "note": ("ANCHOR pseudo-fold: the whole expctx-forecastable span "
                 "(= A15 span_expctx). OVERLAPS all folds; excluded from every "
                 "cross-fold claim and aggregate. Used to reproduce a ledgered "
                 "endpoint and to sweep the whole-span static C ladder."),
    }
    WINJSON.write_text(json.dumps(wins, indent=1))
    return wins


def build_windows() -> dict:
    if WINJSON.exists():
        return add_anchor(json.loads(WINJSON.read_text()))
    import numpy as np
    import pandas as pd

    df = pd.read_csv(TRACE)
    ts = (df["TIMESTAMP"].str.replace("Z", "", regex=False)
          .str.pad(23, "right", "0"))
    t = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
    order = np.argsort(t.values, kind="stable")
    t = t.iloc[order].reset_index(drop=True)
    img = df["NumImages"].iloc[order].reset_index(drop=True)

    t0_trace = pd.Timestamp("2024-10-15 12:00:00")
    bounds = [t0_trace + pd.Timedelta(hours=FOLD_HOURS * d)
              for d in range(N_FOLDS + 1)]
    offs = [int(np.searchsorted(t.values, np.datetime64(b))) for b in bounds]

    per_s = pd.Series(img.values, index=t).resample("60s").sum() / 60.0
    eps = json.loads((ROOT / "defense/anim/data/windows_ext.json").read_text())
    ep_names = [k for k in eps
                if k.startswith("burst") or (k[1:].isdigit() and k[0] == "e")]

    wins = {}
    for i, fid in enumerate(FOLD_IDS):
        lo, hi = offs[i], offs[i + 1]
        if fid == "F1":
            lo += F1_SKIP          # start at the first expctx-forecastable req
        first, last = t.iloc[lo], t.iloc[hi - 1]
        m = (per_s.index >= bounds[i]) & (per_s.index < bounds[i + 1])
        episodes = sorted(
            [e for e in ep_names if lo <= eps[e]["offset"] < hi],
            key=lambda e: -eps[e]["peak_1min_img_per_s"])
        wins[fid] = {
            "offset": lo,
            "max_requests": hi - lo,
            "requests": hi - lo,
            "span_s": round(float((last - first).total_seconds()), 1),
            "t0": str(first),
            "t_end": str(last),
            "utc_day": str(bounds[i]),
            "mean_img_per_s": round(float(per_s[m].mean()), 2),
            "peak_1min_img_per_s": round(float(per_s[m].max()), 1),
            "p99_1min_img_per_s": round(float(per_s[m].quantile(0.99)), 1),
            "episodes": episodes,
            "burst_bearing": fid in BURST_FOLDS,
            "note": (f"G4 temporal fold {fid}: [{bounds[i]} .. {bounds[i+1]}) UTC, "
                     f"{hi - lo} requests"
                     + (", starts at first expctx-forecastable request "
                        f"(offset {F1_SKIP})" if fid == "F1" else "")),
        }
    OUT.mkdir(parents=True, exist_ok=True)
    WINJSON.write_text(json.dumps(wins, indent=1))
    tot = sum(w["max_requests"] for w in wins.values())
    print(f"[windows] {N_FOLDS} folds, {tot:,} requests "
          f"(= 1,000,000 - {F1_SKIP} pre-forecast head)", flush=True)
    return add_anchor(wins)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def run(cmd, env, log: Path | None = None) -> subprocess.CompletedProcess:
    if log is None:
        return subprocess.run(cmd, capture_output=True, text=True, env=env)
    with open(log, "w") as fh:
        return subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env)


def base_env(extra: dict | None = None) -> dict:
    e = {**os.environ, "TESE_WINDOWS": str(WINJSON), "TESE_ROOT": str(ROOT)}
    if extra:
        e.update(extra)
    return e


def n_req(win: dict, smoke: int | None) -> int:
    return min(win["max_requests"], smoke) if smoke else win["max_requests"]


DRIVER = Path(__file__).resolve()


def _mtime(p: Path) -> str | None:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))
    except OSError:
        return None


def _git_hash() -> str | None:
    """Driver provenance, so a stale (summary, results.json) pairing is
    detectable after the fact rather than argued about."""
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h",
                            "--", str(DRIVER)],
                           capture_output=True, text=True, timeout=20)
        h = r.stdout.strip()
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain",
                                "--", str(DRIVER)],
                               capture_output=True, text=True, timeout=20).stdout.strip()
        return (h or "untracked") + ("+dirty" if dirty else "")
    except Exception:
        return None


# --------------------------------------------------------------------------
# stage 1: encoder schedules
# --------------------------------------------------------------------------
def sched_path(fid: str, arm: str, kind: str) -> Path:
    """Parameter-stamped schedule filename.

    The stem carries every input that changes the schedule (model/parquet,
    quantile, lead, resolution) so a change to any of them cannot collide with
    a cached file from the previous setting.
    """
    if kind == "forecast":
        stem = f"{MODEL}_expctx.p90.L{LEAD_S}"
    else:
        stem = f"reactive.15s.L{LEAD_S}.hyst3"
    return OUT / f"{fid}_{arm}.{stem}.sched.json"


def make_schedule(job) -> tuple[str, dict]:
    fid, arm, rho, kind, force = job
    out = sched_path(fid, arm, kind)
    if out.exists() and not force:
        return f"{fid}/{arm}", {"sched": str(out), "cached": True}
    if kind == "forecast":
        cmd = [str(EDA_PY), str(GEN_ISSUE), "--window", fid,
               "--quantile", "p90", "--rho", str(rho),
               "--cold-start-s", str(LEAD_S),
               "--parquet", str(ROOT / f"predictors/results/{MODEL}_images_expctx.parquet"),
               "--out", str(out),
               "--ledger-out", str(OUT / f"{fid}_{arm}.ledger.json")]
    else:
        cmd = [str(EDA_PY), str(GEN_SCHED), "--window", fid,
               "--policy", "reactive", "--resolution", "15s",
               "--rho", str(rho), "--cold-start-s", str(LEAD_S),
               "--hysteresis-min", "3", "--out", str(out)]
    r = run(cmd, base_env())
    if r.returncode != 0:
        return f"{fid}/{arm}", {"error": f"sched rc={r.returncode}: {r.stderr[-500:]}"}
    return f"{fid}/{arm}", {"sched": str(out)}


# --------------------------------------------------------------------------
# stage 2: encoder converters
# --------------------------------------------------------------------------
def converter(job) -> tuple[str, str, dict]:
    fid, arm, win, workers, sched, smoke = job
    n = n_req(win, smoke)
    trace = OUT / f"{fid}_{arm}.jsonl"
    cmd = [str(AIC_PY), str(CONV), "--out", str(trace),
           "--offset", str(win["offset"]), "--max-requests", str(n),
           "--encoder-workers", str(workers)]
    if sched:
        cmd += ["--worker-schedule", str(sched)]
    t = time.time()
    r = run(cmd, base_env(), OUT / f"{fid}_{arm}.conv.log")
    if r.returncode != 0:
        return fid, arm, {"error": f"conv rc={r.returncode} (see {fid}_{arm}.conv.log)"}
    st = json.loads(Path(f"{trace}.stats.json").read_text())
    nl = sum(1 for _ in open(trace))
    res = {
        "enc_p99_ms": round(st["encoder_delay_ms"]["p99"], 1),
        "enc_max_ms": round(st["encoder_delay_ms"]["max"], 1),
        "provisioned_ws": st["provisioned_worker_seconds"],
        "queue_divergent": st["queue_divergent"],
        "requests": nl,
        "enc_pass": (st["encoder_delay_ms"]["p99"] <= ENC_P99_BOUND_MS
                     and not st["queue_divergent"]),
        "wall_s": round(time.time() - t, 1),
    }
    if nl != n:
        res["error"] = f"coverage {nl} != {n}"
    return fid, arm, res


# --------------------------------------------------------------------------
# stage 3: language replays
# --------------------------------------------------------------------------
def language(job) -> tuple[str, str, dict]:
    fid, arm, win, policy, smoke = job
    n = n_req(win, smoke)
    src = {"lang_fc": f"{fid}_enc_fc_rho{RHO_HEADLINE}",
           "lang_reactive": f"{fid}_enc_reactive",
           "lang_static": f"{fid}_enc_static_C{C_DEPLOYABLE}"}[arm]
    trace = OUT / f"{src}.jsonl"
    if not trace.exists():
        return fid, arm, {"error": f"missing composed trace {trace.name}"}
    rep = OUT / f"{fid}_{arm}.report.json"
    jsonl = OUT / f"{fid}_{arm}.requests.jsonl"
    env = base_env({"RUST_LOG": "warn", "AIC_TP": "2", "AIC_VER": "0.19.0",
                    "REPLAY_PY": str(SRC_PY), "STARTUP_TIME": "60"})
    cmd = ["bash", str(RR), str(trace), "aic", str(rep), "2",
           "--report-jsonl", str(jsonl)]
    if policy == "forecast":
        env.update({"REPLAY_ENTRY": str(ENTRY), "FORECAST_T0": win["t0"],
                    "FORECAST_MODEL": MODEL, "FORECAST_QUANTILE": "p90",
                    "FORECAST_RESOLUTION": "15s", "FORECAST_REQ_SCALE": "8.0",
                    "FORECAST_SUFFIX": "_expctx"})
        cmd += ["--planner-config", str(SMOKE_PLANNER)]
    elif policy == "reactive":
        cmd += ["--planner-config", str(LADDER)]
    t = time.time()
    r = run(cmd, env, OUT / f"{fid}_{arm}.log")
    if r.returncode != 0:
        return fid, arm, {"error": f"lang rc={r.returncode} (see {fid}_{arm}.log)"}
    d = json.loads(rep.read_text())
    nl = sum(1 for _ in open(jsonl))
    res = {
        "requests": nl, "completed": d["completed_requests"],
        "ttft_p99_ms": round(d["p99_ttft_ms"], 1),
        "ttft_mean_ms": round(d.get("mean_ttft_ms", float("nan")), 1),
        "itl_p99_ms": round(d["p99_itl_ms"], 1),
        "gpu_h": round(d["gpu_hours"], 2),
        "lang_pass": (d["p99_ttft_ms"] <= TTFT_P99_BOUND_MS
                      and d["p99_itl_ms"] <= ITL_P99_BOUND_MS),
        "wall_s": round(time.time() - t, 1),
    }
    if nl != n or d["completed_requests"] != n:
        res["error"] = (f"coverage jsonl {nl} completed "
                        f"{d['completed_requests']} != {n}")
    return fid, arm, res


# --------------------------------------------------------------------------
# stage 4: per-fold table + fold-stability verdict
# --------------------------------------------------------------------------
def _cell_request_counts(r: dict) -> set[int]:
    return {c["requests"] for c in r.values()
            if isinstance(c, dict) and isinstance(c.get("requests"), int)}


def check_anchor(row: dict, results: dict) -> dict:
    """Reproduce a ledgered endpoint with THIS harness, or fail loudly.

    Without this, nothing connects the fold harness to the harness that
    produced the thesis 0.62x. The reference values are read live from the
    ledgered artifacts, never hardcoded.
    """
    a = {"fold": ANCHOR, "checks": [], "ok": None,
         "reference_files": [str(A15_STATS), str(A15_REPORT), str(A13_C8_STATS)]}
    if not row:
        a["ok"] = None
        a["reason"] = f"anchor fold {ANCHOR} not in this invocation"
        return a
    try:
        ref = json.loads(A15_STATS.read_text())
    except OSError as e:
        a["ok"] = None
        a["reason"] = f"cannot read anchor reference: {e}"
        return a

    exp_p99 = round(ref["encoder_delay_ms"]["p99"], 1)
    exp_ws = ref["provisioned_worker_seconds"]
    exp_c8_ws = C_DEPLOYABLE * ref["sim_horizon_s"]
    exp_ratio = exp_ws / exp_c8_ws

    def chk(name, got, exp, tol, rel=False):
        ok = None if got is None else (
            abs(got - exp) <= tol * (abs(exp) if rel else 1.0))
        a["checks"].append({"check": name, "got": got, "expected": round(exp, 4),
                            "tol": tol, "relative": rel, "ok": ok})

    fc, c8 = row["forecast_rho15"], row["static_C8"]
    chk("enc_p99_ms", fc.get("enc_p99_ms"), exp_p99, ANCHOR_TOL["enc_p99_ms"])
    chk("provisioned_ws", fc.get("provisioned_ws"), exp_ws,
        ANCHOR_TOL["provisioned_ws_rel"], rel=True)
    chk("ratio_vs_C8", row.get("cost_ratio_vs_C8"), exp_ratio,
        ANCHOR_TOL["ratio_vs_C8"])
    # independent cross-check of the C8 denominator against the a13 full-trace
    # static run (1,000,000 req vs our 999,599 -> compare the per-second rate)
    try:
        c13 = json.loads(A13_C8_STATS.read_text())
        a["c8_rate_crosscheck"] = {
            "a13_ws_per_s": round(c13["provisioned_worker_seconds"]
                                  / c13["sim_horizon_s"], 4),
            "g4_ws_per_s": (round(c8["provisioned_ws"] / ref["sim_horizon_s"], 4)
                            if c8.get("provisioned_ws") else None),
            "expected": float(C_DEPLOYABLE)}
    except OSError:
        pass
    lang = row.get("lang_fc")
    if lang and lang.get("ttft_p99_ms") is not None:
        try:
            rep = json.loads(A15_REPORT.read_text())
            chk("lang_ttft_p99_ms", lang["ttft_p99_ms"],
                round(rep["p99_ttft_ms"], 1), ANCHOR_TOL["ttft_p99_ms"])
        except OSError:
            pass
    else:
        a["lang_anchor"] = "NOT RUN (pass --anchor-lang; ~2 h full-span replay)"
    vals = [c["ok"] for c in a["checks"]]
    a["ok"] = None if (not vals or any(v is None for v in vals)) else all(vals)
    return a


def summarize(wins: dict, results: dict, folds: list[str],
              smoke: int | None = None, meta: dict | None = None) -> dict:
    rows = {}
    coverage_conflicts = {}
    for fid in folds:
        r = results.get(fid, {})
        w = wins[fid]
        fc = r.get(f"enc_fc_rho{RHO_HEADLINE}", {})
        c8 = r.get(f"enc_static_C{C_DEPLOYABLE}", {})
        rea = r.get("enc_reactive", {})
        # ---- MEASURED request count, never the window size. A smoke cell must
        # ---- never be able to present itself as a full-scale fold.
        counts = _cell_request_counts(r)
        if len(counts) > 1:
            coverage_conflicts[fid] = sorted(counts)
        n_measured = max(counts) if counts else None
        # per-fold static-optimal: the PASSING C with minimum provisioned cost.
        # (Scan all C rather than breaking at the first pass: ws is monotone in
        # C today, but "smallest passing" and "cheapest passing" are different
        # questions and only the latter is the baseline we mean.)
        passing = [(r[f"enc_static_C{c}"]["provisioned_ws"], c)
                   for c in STATIC_CS
                   if r.get(f"enc_static_C{c}", {}).get("enc_pass")]
        cstar_ws, cstar = min(passing) if passing else (None, None)
        static_ladder = {
            str(c): {k: r.get(f"enc_static_C{c}", {}).get(k)
                     for k in ("enc_p99_ms", "provisioned_ws", "enc_pass")}
            for c in STATIC_CS if f"enc_static_C{c}" in r}
        frontier = {}
        for rho in RHOS:
            s = r.get(f"enc_fc_rho{rho}", {})
            if "provisioned_ws" in s and c8.get("provisioned_ws"):
                frontier[str(rho)] = {
                    "ratio_vs_C8": round(s["provisioned_ws"] / c8["provisioned_ws"], 3),
                    "ratio_vs_Cstar": (round(s["provisioned_ws"] / cstar_ws, 3)
                                       if cstar_ws else None),
                    "enc_p99_ms": s["enc_p99_ms"], "enc_pass": s["enc_pass"],
                }
        # cheapest FEASIBLE rho = the passing rho with least provisioned cost.
        # The thesis frontier claim is that this is rho=15; monotonicity of the
        # frontier does NOT imply it, so it is graded separately and explicitly.
        feas = [(v["ratio_vs_C8"], int(k)) for k, v in frontier.items()
                if v["enc_pass"]]
        cheapest_rho = min(feas)[1] if feas else None
        row = {
            "t0": w["t0"],
            "requests": n_measured,
            "window_max_requests": w["max_requests"],
            "is_smoke_cell": (n_measured is not None
                              and n_measured < w["max_requests"]),
            "span_h": round(w["span_s"] / 3600, 2),
            "mean_img_per_s": w["mean_img_per_s"],
            "peak_1min_img_per_s": w["peak_1min_img_per_s"],
            "episodes": w["episodes"],
            "burst_bearing": w["burst_bearing"],
            "is_anchor": bool(w.get("anchor")),
            "C_star": cstar, "C_star_ws": cstar_ws,
            "static_ladder": static_ladder,
            "static_C8": {k: c8.get(k) for k in
                          ("enc_p99_ms", "provisioned_ws", "enc_pass")},
            "forecast_rho15": {k: fc.get(k) for k in
                               ("enc_p99_ms", "provisioned_ws", "enc_pass")},
            "reactive": {k: rea.get(k) for k in
                         ("enc_p99_ms", "provisioned_ws", "enc_pass")},
            "rho_frontier": frontier,
            "cheapest_feasible_rho": cheapest_rho,
            "rho15_is_cheapest_feasible": (None if cheapest_rho is None
                                           else cheapest_rho == RHO_HEADLINE),
        }
        if fc.get("provisioned_ws") and c8.get("provisioned_ws"):
            row["cost_ratio_vs_C8"] = round(
                fc["provisioned_ws"] / c8["provisioned_ws"], 3)
        if fc.get("provisioned_ws") and cstar_ws:
            row["cost_ratio_vs_Cstar"] = round(fc["provisioned_ws"] / cstar_ws, 3)
        if rea.get("provisioned_ws") and c8.get("provisioned_ws"):
            row["reactive_ratio_vs_C8"] = round(
                rea["provisioned_ws"] / c8["provisioned_ws"], 3)
        for arm in ("lang_fc", "lang_reactive", "lang_static"):
            if arm in r:
                row[arm] = {k: r[arm].get(k) for k in
                            ("ttft_p99_ms", "itl_p99_ms", "gpu_h", "lang_pass")}
        # ---- LANGUAGE-POOL cost, the other half of the cited thesis sentence
        # ---- ("the 4x/2x over-provisioning"), which is a language quantity.
        ls = row.get("lang_static", {}).get("gpu_h")
        if ls:
            for arm, key in (("lang_fc", "lang_cost_ratio_vs_static"),
                             ("lang_reactive", "lang_reactive_ratio_vs_static")):
                g = row.get(arm, {}).get("gpu_h")
                if g:
                    row[key] = round(g / ls, 3)
        # E2E pass = both pools clear their bound under the same policy
        for pol, ea, la in (("forecast", f"enc_fc_rho{RHO_HEADLINE}", "lang_fc"),
                            ("reactive", "enc_reactive", "lang_reactive"),
                            ("static", f"enc_static_C{C_DEPLOYABLE}", "lang_static")):
            e, l = r.get(ea, {}), r.get(la, {})
            if "enc_pass" in e and "lang_pass" in l:
                row[f"e2e_pass_{pol}"] = bool(e["enc_pass"] and l["lang_pass"])
                row["e2e_sum_p99_ms"] = row.get("e2e_sum_p99_ms", {})
                # NOT the request-linked composition A12 performs; a sum of two
                # marginal p99s is an upper-bound-ish diagnostic, not an E2E p99.
                row["e2e_sum_p99_ms"][pol] = round(
                    e["enc_p99_ms"] + l["ttft_p99_ms"], 1)
        rows[fid] = row

    # ---- scope: the anchor overlaps every fold and is NEVER graded with them
    graded = [f for f in folds if not rows[f]["is_anchor"]]
    burst = [f for f in graded if rows[f]["burst_bearing"]]
    quiet = [f for f in graded if not rows[f]["burst_bearing"]]

    ratios8 = [rows[f]["cost_ratio_vs_C8"] for f in burst
               if "cost_ratio_vs_C8" in rows[f]]
    ratiosS = [rows[f]["cost_ratio_vs_Cstar"] for f in burst
               if "cost_ratio_vs_Cstar" in rows[f]]
    fc_pass = [f for f in burst if rows[f].get("e2e_pass_forecast")]
    fc_fail = [f for f in burst if rows[f].get("e2e_pass_forecast") is False]
    re_fail = [f for f in burst if rows[f].get("e2e_pass_reactive") is False]

    # monotonicity is scoped to BURST folds only, like every other claim, so
    # all claims share one scope and a quiet control cannot veto the frontier.
    def mono_of(fs):
        out = []
        for f in fs:
            fr = rows[f]["rho_frontier"]
            ks = [k for k in [str(x) for x in RHOS] if k in fr]
            if len(ks) < 2:
                continue
            out.append({
                "fold": f,
                "cost_monotone_decreasing": all(
                    fr[a]["ratio_vs_C8"] >= fr[b]["ratio_vs_C8"] - 1e-9
                    for a, b in zip(ks, ks[1:])),
                "p99_monotone_increasing": all(
                    fr[a]["enc_p99_ms"] <= fr[b]["enc_p99_ms"] + 1e-9
                    for a, b in zip(ks, ks[1:])),
                "cheapest_feasible_rho": rows[f]["cheapest_feasible_rho"]})
        return out

    mono = mono_of(burst)
    mono_quiet = mono_of(quiet)          # reported, UNGRADED

    # ---- evaluability gates. A claim is None = NOT EVALUABLE. None must never
    # ---- be rendered as False, and a partial fold subset must never produce a
    # ---- verdict: one quiet fold is not evidence about burst handling.
    burst_complete = set(BURST_FOLDS) <= set(burst)
    smoke_run = bool(smoke) or any(rows[f]["is_smoke_cell"] for f in folds)
    gate_ok = burst_complete and not smoke_run and not coverage_conflicts
    gate_reasons = []
    if smoke_run:
        gate_reasons.append(
            "SMOKE RUN (or smoke-sized cells present): request counts are "
            "capped, so no number here is a result")
    if not burst_complete:
        gate_reasons.append(
            "burst-bearing folds incomplete: have "
            f"{sorted(burst) or 'none'}, need {sorted(BURST_FOLDS)}")
    if coverage_conflicts:
        gate_reasons.append(
            f"cells of one fold disagree on request count: {coverage_conflicts}")

    def gated(x):
        return x if gate_ok else None

    forecast_claims = {
        "cost_ratio_below_1_in_every_burst_fold":
            gated(all(x < 1.0 for x in ratios8) if ratios8 else None),
        "cost_ratio_below_1_vs_refit_baseline":
            gated(all(x < 1.0 for x in ratiosS) if ratiosS else None),
        "forecast_passes_every_burst_fold":
            gated((not fc_fail) if (fc_pass or fc_fail) else None),
        "rho_frontier_shape_stable":
            gated(all(m["cost_monotone_decreasing"] for m in mono)
                  if mono else None),
    }
    # Graded and reported, but deliberately NOT folded into fold_stable: it is
    # a claim about WHERE the frontier's feasible knee sits, not about whether
    # the headline operating point reproduces. Full F5 already contradicts it.
    rho15_vals = [rows[f]["rho15_is_cheapest_feasible"] for f in burst
                  if rows[f]["rho15_is_cheapest_feasible"] is not None]
    frontier_claims = {
        "rho15_is_cheapest_feasible_in_every_burst_fold":
            gated(all(rho15_vals) if rho15_vals else None),
        "cheapest_feasible_rho_per_fold":
            {f: rows[f]["cheapest_feasible_rho"] for f in graded},
        "folds_contradicting_rho15":
            [f for f in graded
             if rows[f]["rho15_is_cheapest_feasible"] is False],
    }
    lang_ratios = [rows[f]["lang_cost_ratio_vs_static"] for f in burst
                   if "lang_cost_ratio_vs_static" in rows[f]]
    language_claims = {
        "lang_cost_ratio_vs_static_per_fold":
            {f: rows[f].get("lang_cost_ratio_vs_static") for f in graded},
        "lang_reactive_ratio_vs_static_per_fold":
            {f: rows[f].get("lang_reactive_ratio_vs_static") for f in graded},
        "lang_forecast_cheaper_than_static_in_every_burst_fold":
            gated(all(x < 1.0 for x in lang_ratios) if lang_ratios else None),
        "note": ("Language cost is GPU-hours of the TP2 mocker replay. The "
                 "thesis's '4x/2x over-provisioning' is a language-pool "
                 "quantity; these ratios are what this harness can say about "
                 "it per fold. They are reported, not folded into "
                 "fold_stable."),
    }
    # A property of the BASELINE, not of any thesis claim about the forecast
    # policy. Keeping it out of fold_stable: if reactive happened to pass every
    # fold, a collapsed boolean would read as "the thesis did not replicate".
    baseline_claims = {
        "reactive_fails_at_least_one_burst_fold":
            gated(bool(re_fail) if burst else None),
    }

    verdict = {
        "scope": ("WITHIN-TRACE TEMPORAL generalization across 7 disjoint "
                  "24-h diurnal folds of ONE Azure trace. This does NOT "
                  "establish cross-workload, cross-model or cross-datacenter "
                  "generalization."),
        "smoke": smoke,
        "is_smoke_run": smoke_run,
        "provenance": meta or {},
        "n_folds_graded": len(graded), "burst_bearing_folds": burst,
        "quiet_control_folds": quiet,
        "anchor_fold_present": ANCHOR in folds,
        "coverage_conflicts": coverage_conflicts,
        "thesis_headline_cost_ratio": 0.62,
        "cost_ratio_vs_C8": {
            "per_fold": {f: rows[f].get("cost_ratio_vs_C8") for f in graded},
            "burst_min": min(ratios8) if ratios8 else None,
            "burst_max": max(ratios8) if ratios8 else None,
            "burst_median": (sorted(ratios8)[len(ratios8) // 2]
                             if ratios8 else None),
        },
        "cost_ratio_vs_Cstar": {
            "per_fold": {f: rows[f].get("cost_ratio_vs_Cstar") for f in graded},
            "burst_min": min(ratiosS) if ratiosS else None,
            "burst_max": max(ratiosS) if ratiosS else None,
        },
        "forecast_e2e_pass_folds": fc_pass,
        "forecast_e2e_fail_folds": fc_fail,
        "reactive_e2e_fail_folds": re_fail,
        "rho_frontier_monotonicity": mono,
        "rho_frontier_monotonicity_quiet_ungraded": mono_quiet,
        "claims": forecast_claims,
        "frontier_claims": frontier_claims,
        "language_claims": language_claims,
        "baseline_claims": baseline_claims,
        "no_confidence_intervals": (
            "Folds are disjoint TEST windows but the expanding-context "
            "forecaster's conditioning history is NESTED (a fold-5 forecast is "
            "conditioned on folds 1-4). Legitimate operator history, not "
            "leakage -- but the folds are NOT i.i.d. replicates, so no CI, "
            "standard error or significance test is computed across them."),
    }
    vals = list(forecast_claims.values())
    verdict["fold_stable"] = (None if any(v is None for v in vals)
                              else all(vals))
    verdict["evaluable"] = gate_ok and not any(v is None for v in vals)
    if not verdict["evaluable"]:
        if not gate_reasons:
            gate_reasons.append(
                "one or more forecast claims not evaluable on this fold subset")
        verdict["incomplete_reason"] = ("; ".join(gate_reasons)
                                        + " -- run the full 7-fold set")

    # ---- anchor + whole-span denominator ---------------------------------
    anchor_row = rows.get(ANCHOR)
    verdict["anchor"] = check_anchor(anchor_row, results)
    if anchor_row:
        wc = anchor_row["C_star"]
        verdict["whole_span_static_ladder"] = {
            "ladder": anchor_row["static_ladder"],
            "whole_span_C_star": wc,
            "C_deployable": C_DEPLOYABLE,
            "C8_is_whole_span_optimum": (None if wc is None
                                         else wc == C_DEPLOYABLE),
            "denominator_statement": (
                "not evaluated" if wc is None else
                (f"C={C_DEPLOYABLE} IS the whole-span static optimum; the "
                 "0.62x denominator is the static optimum."
                 if wc == C_DEPLOYABLE else
                 f"whole-span C* = {wc} < {C_DEPLOYABLE}: the 0.62x "
                 f"denominator is the DEPLOYED C={C_DEPLOYABLE} fleet, NOT "
                 f"the static optimum. Against C*={wc} the ratio is "
                 f"{anchor_row.get('cost_ratio_vs_Cstar')}. The thesis "
                 "sentence must be restated accordingly.")),
        }
    return {"folds": rows, "verdict": verdict}


def write_markdown(summary: dict, path: Path) -> None:
    rows, v = summary["folds"], summary["verdict"]
    L = ["# G4 — within-trace temporal fold generalization", ""]
    if v["is_smoke_run"]:
        L += ["> # ⚠️  SMOKE RUN — NOT A RESULT  ⚠️",
              f"> **--smoke {v['smoke']}: request counts are CAPPED "
              "(see the `req` column vs `window req`). Every number below is a "
              "plumbing check. It is NOT a measurement, it MUST NOT be quoted, "
              "cited, or compared with any ledgered value, and no verdict is "
              "computed.**", ""]
    L += [v["scope"], "",
          "## Per-fold headline quantities", "",
          "| Fold | t0 (UTC) | req | window req | peak img/s | episodes | C* | "
          "fc rho15 p99 | static C8 p99 | cost vs C8 | cost vs C* | "
          "reactive p99 | fc TTFT p99 | react TTFT p99 | lang fc/static GPU-h | "
          "fc E2E | react E2E |",
          "|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:--:|:--:|"]

    def g(d, k, fmt="{}"):
        x = d.get(k)
        return "-" if x is None else fmt.format(x)

    for f, r in rows.items():
        label = f + (" (ANCHOR)" if r["is_anchor"]
                     else "" if r["burst_bearing"] else " (quiet)")
        L.append("| {} | {} | {} | {:,} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            label, r["t0"][:16],
            "-" if r["requests"] is None else f"{r['requests']:,}"
            + (" ⚠SMOKE" if r["is_smoke_cell"] else ""),
            r["window_max_requests"], r["peak_1min_img_per_s"],
            ",".join(r["episodes"]) or "none", g(r, "C_star"),
            g(r["forecast_rho15"], "enc_p99_ms"), g(r["static_C8"], "enc_p99_ms"),
            g(r, "cost_ratio_vs_C8", "{:.3f}x"), g(r, "cost_ratio_vs_Cstar", "{:.3f}x"),
            g(r["reactive"], "enc_p99_ms"),
            g(r.get("lang_fc", {}), "ttft_p99_ms"),
            g(r.get("lang_reactive", {}), "ttft_p99_ms"),
            g(r, "lang_cost_ratio_vs_static", "{:.3f}x"),
            "PASS" if r.get("e2e_pass_forecast") else ("FAIL" if "e2e_pass_forecast" in r else "-"),
            "PASS" if r.get("e2e_pass_reactive") else ("FAIL" if "e2e_pass_reactive" in r else "-")))
    L += ["", "*`req` is the MEASURED number of simulated requests, read back "
          "from each converter's own output — not the window size.*", ""]

    L += ["## rho frontier per fold (cost vs static C8 / encoder p99 ms)", "",
          "| Fold | " + " | ".join(f"rho={x}" for x in RHOS)
          + " | cheapest feasible rho |",
          "|---|" + "---|" * (len(RHOS) + 1)]
    for f, r in rows.items():
        cells = []
        for rho in RHOS:
            c = r["rho_frontier"].get(str(rho))
            cells.append("-" if not c else
                         f"{c['ratio_vs_C8']:.2f}x / {c['enc_p99_ms']:.0f}"
                         + ("" if c["enc_pass"] else " **FAIL**"))
        cr = r["cheapest_feasible_rho"]
        cells.append("-" if cr is None else
                     (f"**{cr}**" + ("" if cr == RHO_HEADLINE
                                     else f" (≠ headline {RHO_HEADLINE})")))
        L.append(f"| {f} | " + " | ".join(cells) + " |")
    fcl = v["frontier_claims"]
    contra = fcl["folds_contradicting_rho15"]
    L += ["",
          f"- `rho15_is_cheapest_feasible_in_every_burst_fold`: "
          f"**{'n/a' if fcl['rho15_is_cheapest_feasible_in_every_burst_fold'] is None else fcl['rho15_is_cheapest_feasible_in_every_burst_fold']}**",
          (f"- **CONTRADICTED in {', '.join(contra)}**: in these folds a "
           f"cheaper rho than the thesis headline rho={RHO_HEADLINE} still "
           "meets the encoder tail bound, so rho=15 is feasible but not "
           "cost-optimal there. Reported, not suppressed."
           if contra else
           "- No fold contradicts rho=15 as the cheapest feasible rho."),
          "", "Monotonicity of the frontier does NOT imply rho=15 is the "
          "cheapest feasible rho; the two are graded separately.", ""]

    # ---- anchor -----------------------------------------------------------
    a = v["anchor"]
    L += ["## Anchor — does this harness reproduce a ledgered endpoint?", ""]
    if a["ok"] is None and not a["checks"]:
        L += [f"**NOT RUN** — {a.get('reason', 'anchor fold absent')}. Without "
              "the anchor, nothing links this harness to the one that produced "
              "the thesis 0.62x.", ""]
    else:
        L += [f"**anchor_ok = {a['ok']}**", "",
              "| check | got | expected (ledgered) | tol | ok |",
              "|---|---:|---:|---:|:--:|"]
        for c in a["checks"]:
            L.append("| {} | {} | {} | {}{} | {} |".format(
                c["check"], c["got"], c["expected"], c["tol"],
                " (rel)" if c["relative"] else "",
                "-" if c["ok"] is None else ("ok" if c["ok"] else "**MISMATCH**")))
        if "lang_anchor" in a:
            L.append("")
            L.append(f"Language anchor: {a['lang_anchor']}")
        L.append("")

    # ---- whole-span denominator ------------------------------------------
    ws = v.get("whole_span_static_ladder")
    L += ["## Whole-span static ladder — is C=8 really the denominator?", ""]
    if not ws:
        L += ["**NOT SWEPT** — the anchor fold was not run, so the whole-span "
              f"static optimum is unknown and C={C_DEPLOYABLE} remains "
              "ASSERTED rather than verified as the 0.62x denominator.", ""]
    else:
        L += ["| C | enc p99 (ms) | provisioned ws | pass |", "|---:|---:|---:|:--:|"]
        for c, d in ws["ladder"].items():
            L.append("| {} | {} | {} | {} |".format(
                c, d.get("enc_p99_ms"),
                "-" if d.get("provisioned_ws") is None else f"{d['provisioned_ws']:,.0f}",
                "-" if d.get("enc_pass") is None else ("PASS" if d["enc_pass"] else "FAIL")))
        L += ["", f"**whole-span C\\* = {ws['whole_span_C_star']}** — "
              + ws["denominator_statement"], ""]

    # ---- verdict ----------------------------------------------------------
    L += ["## Verdict", "",
          f"**fold_stable = {v['fold_stable']}**"
          + ("" if v["evaluable"] else "  (NOT EVALUABLE — " + v["incomplete_reason"] + ")"),
          "",
          "`fold_stable` is the conjunction of the FORECAST-POLICY claims only, "
          "and is secondary to the per-claim rows below. It is `None` — never "
          "`False` — whenever the fold subset cannot decide it.", ""]
    for k, val in v["claims"].items():
        L.append(f"- `{k}`: **{'n/a' if val is None else val}**")
    L += ["", "### Baseline claims (about reactive, NOT about the thesis claim)", ""]
    for k, val in v["baseline_claims"].items():
        L.append(f"- `{k}`: **{'n/a' if val is None else val}**")
    lc = v["language_claims"]
    L += ["", "### Language-pool cost (the other half of the cited sentence)", "",
          f"- `lang_forecast_cheaper_than_static_in_every_burst_fold`: "
          f"**{'n/a' if lc['lang_forecast_cheaper_than_static_in_every_burst_fold'] is None else lc['lang_forecast_cheaper_than_static_in_every_burst_fold']}**",
          f"- forecast/static GPU-h per fold: {lc['lang_cost_ratio_vs_static_per_fold']}",
          f"- reactive/static GPU-h per fold: {lc['lang_reactive_ratio_vs_static_per_fold']}",
          ""]
    L += [f"Cost ratio vs C8 over burst-bearing folds: "
          f"{v['cost_ratio_vs_C8']['burst_min']} .. "
          f"{v['cost_ratio_vs_C8']['burst_max']} "
          f"(thesis whole-span headline {v['thesis_headline_cost_ratio']}).",
          f"Cost ratio vs per-fold refit static-optimal C*: "
          f"{v['cost_ratio_vs_Cstar']['burst_min']} .. "
          f"{v['cost_ratio_vs_Cstar']['burst_max']}.",
          f"Forecast E2E fails: {v['forecast_e2e_fail_folds'] or 'none'}. "
          f"Reactive E2E fails: {v['reactive_e2e_fail_folds'] or 'none'}.",
          "",
          "### What this does NOT establish", "",
          "One trace, one datacenter, one model family, one 7-day record. The",
          "folds share the same tenant mix, the same request-size distribution",
          "and the same hardware calibration; they differ only in time. A",
          "fold-stable result here rules out *the single-span average being",
          "carried by one lucky day*; it does not speak to another workload,",
          "another datacenter, or a non-diurnal arrival process.",
          "",
          "**The folds are not i.i.d. replicates.** " + v["no_confidence_intervals"],
          "",
          "The `e2e_sum_p99_ms` field is p99(encoder) + p99(TTFT) — a sum of two",
          "marginal tails, NOT the request-linked composition A12 computes. It is",
          "a diagnostic; the composed E2E p99 is A12's number.", ""]
    if v["provenance"]:
        L += ["---", "", "Provenance: "
              + ", ".join(f"`{k}`={val}" for k, val in v["provenance"].items()), ""]
    path.write_text("\n".join(L))


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folds", default=",".join(ALL_IDS),
                    help=f"comma list, e.g. F5 or F1,F3,F4 or {ANCHOR}")
    ap.add_argument("--stages", default="windows,sched,enc,lang,table")
    ap.add_argument("--smoke", type=int, default=None,
                    help="cap requests per fold (PLUMBING TEST ONLY -- stamps a "
                         "SMOKE banner and refuses to compute a verdict)")
    ap.add_argument("--enc-jobs", type=int, default=6)
    ap.add_argument("--anchor-enc-jobs", type=int, default=2,
                    help="parallelism for the FULL anchor fold's converters "
                         "(1M-request runs; 2-wide matches A13's RAM budget)")
    ap.add_argument("--lang-jobs", type=int, default=3,
                    help="~3 GB RSS per fold-scale replay; 3-wide is gentle")
    ap.add_argument("--anchor-lang", action="store_true",
                    help="also replay the FULL anchor fold's language arm to "
                         "assert TTFT p99 == 651.1 ms (adds ~2 h)")
    ap.add_argument("--force", action="store_true", help="ignore cached cells")
    ap.add_argument("--keep-traces", action="store_true",
                    help="keep every composed trace (default: keep only the "
                         "three the language stage consumes)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    folds = [f.strip() for f in args.folds.split(",") if f.strip()]
    stages = set(args.stages.split(","))
    bad = [f for f in folds if f not in ALL_IDS]
    if bad:
        sys.exit(f"unknown folds {bad}; valid: {ALL_IDS}")
    if args.smoke:
        print("=" * 78 +
              f"\n  SMOKE RUN (--smoke {args.smoke}): PLUMBING ONLY."
              "\n  Output is NOT a result and no verdict will be computed."
              "\n" + "=" * 78, flush=True)

    wins = build_windows()
    results = json.loads(RESJSON.read_text()) if RESJSON.exists() else {}
    if args.force:                      # drop only the SELECTED folds' cells
        for f in folds:
            results.pop(f, None)

    def save():
        RESJSON.write_text(json.dumps(results, indent=1))

    def reusable(fid: str, arm: str, expect_n: int) -> bool:
        """A cached cell is reusable ONLY if it simulated the same number of
        requests this invocation would. Keying on 'no error key' (as this
        driver once did) makes a --smoke cell indistinguishable from a
        full-scale one and silently promotes it to a result. It did."""
        if args.force:
            return False
        c = results.get(fid, {}).get(arm)
        if not isinstance(c, dict) or "error" in c:
            return False
        if c.get("requests") != expect_n:
            return False
        if arm.startswith("lang_") and c.get("completed") != expect_n:
            return False
        return True

    # ---- stage: schedules ------------------------------------------------
    scheds: dict[tuple[str, str], Path] = {}
    if "sched" in stages:
        jobs = []
        for f in folds:
            for rho in RHOS:
                jobs.append((f, f"fc_rho{rho}", rho, "forecast", args.force))
            jobs.append((f, "reactive", RHO_HEADLINE, "reactive", args.force))
        with ThreadPoolExecutor(max_workers=args.enc_jobs) as ex:
            for (job, (key, res)) in zip(jobs, ex.map(make_schedule, jobs)):
                if "error" in res:
                    sys.exit(f"[sched] {key}: {res['error']}")
                scheds[(job[0], job[1])] = Path(res["sched"])
        print(f"[sched] {len(jobs)} schedules ok", flush=True)
    else:
        for f in folds:
            for rho in RHOS:
                scheds[(f, f"fc_rho{rho}")] = sched_path(
                    f, f"fc_rho{rho}", "forecast")
            scheds[(f, "reactive")] = sched_path(f, "reactive", "reactive")

    # ---- stage: encoder converters ---------------------------------------
    if "enc" in stages:
        def enc_jobs_for(f):
            w, js = wins[f], []
            for rho in RHOS:
                js.append((f, f"enc_fc_rho{rho}", w, 2,
                           scheds[(f, f"fc_rho{rho}")], args.smoke))
            js.append((f, "enc_reactive", w, 2, scheds[(f, "reactive")], args.smoke))
            for c in STATIC_CS:
                js.append((f, f"enc_static_C{c}", w, c, None, args.smoke))
            return [j for j in js if not reusable(f, j[1], n_req(w, args.smoke))]

        # the anchor fold's converters are whole-span (1M req): run them in a
        # narrower pool so peak RAM stays near A13's budget.
        for group, width in ((folds, args.enc_jobs),) if ANCHOR not in folds else (
                ([f for f in folds if f != ANCHOR], args.enc_jobs),
                ([ANCHOR], args.anchor_enc_jobs)):
            jobs = [j for f in group for j in enc_jobs_for(f)]
            if not jobs:
                continue
            with ThreadPoolExecutor(max_workers=width) as ex:
                for fid, arm, res in ex.map(converter, jobs):
                    results.setdefault(fid, {})[arm] = res
                    tag = res.get("error") or (
                        f"p99={res['enc_p99_ms']}ms ws={res['provisioned_ws']:,.0f} "
                        f"n={res['requests']:,} "
                        f"{'PASS' if res['enc_pass'] else 'FAIL'}")
                    print(f"[enc] {fid}/{arm}: {tag}", flush=True)
            save()
        errs = [(f, a) for f in folds for a, r in results.get(f, {}).items()
                if a.startswith("enc_") and "error" in r]
        if errs:
            sys.exit(f"encoder stage failed: {errs}")
        if not args.keep_traces:
            # GC is scoped to THIS invocation's folds only. A global glob with a
            # current-folds keep-set deletes other folds' language inputs, which
            # breaks the documented fold-by-fold workflow.
            keep = {f"{f}_enc_fc_rho{RHO_HEADLINE}.jsonl" for f in folds} | \
                   {f"{f}_enc_reactive.jsonl" for f in folds} | \
                   {f"{f}_enc_static_C{C_DEPLOYABLE}.jsonl" for f in folds}
            for f in folds:
                for p in OUT.glob(f"{f}_enc_*.jsonl"):
                    if p.name not in keep:
                        p.unlink(missing_ok=True)

    # ---- stage: language replays -----------------------------------------
    if "lang" in stages:
        jobs = []
        for f in folds:
            w = wins[f]
            if f == ANCHOR:
                # anchor needs only the forecast arm (its assertion is TTFT p99
                # vs A15); the static/reactive whole-span replays cost hours and
                # buy nothing the fold rows do not already give.
                arms = [("lang_fc", "forecast")] if args.anchor_lang else []
            else:
                arms = [("lang_fc", "forecast"), ("lang_reactive", "reactive"),
                        ("lang_static", "static")]
            for arm, pol in arms:
                if not reusable(f, arm, n_req(w, args.smoke)):
                    jobs.append((f, arm, w, pol, args.smoke))
        with ThreadPoolExecutor(max_workers=args.lang_jobs) as ex:
            for fid, arm, res in ex.map(language, jobs):
                results.setdefault(fid, {})[arm] = res
                tag = res.get("error") or (
                    f"ttft_p99={res['ttft_p99_ms']}ms itl_p99={res['itl_p99_ms']}ms "
                    f"gpu_h={res['gpu_h']} n={res['requests']:,} "
                    f"{'PASS' if res['lang_pass'] else 'FAIL'}")
                print(f"[lang] {fid}/{arm}: {tag}", flush=True)
                save()
        errs = [(f, a) for f in folds for a, r in results.get(f, {}).items()
                if a.startswith("lang_") and "error" in r]
        if errs:
            sys.exit(f"language stage failed: {errs}")

    # ---- stage: table + verdict ------------------------------------------
    if "table" in stages:
        meta = {
            "driver": str(DRIVER),
            "driver_mtime": _mtime(DRIVER),
            "driver_git": _git_hash(),
            "results_json_mtime": _mtime(RESJSON),
            "written_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "invocation": " ".join(sys.argv),
            "folds_requested": folds,
            "smoke": args.smoke,
            "anchor_lang": args.anchor_lang,
        }
        summary = summarize(wins, results, folds, smoke=args.smoke, meta=meta)
        (OUT / "folds_summary.json").write_text(json.dumps(summary, indent=1))
        write_markdown(summary, OUT / "folds_table.md")
        v = summary["verdict"]
        print("\n" + (OUT / "folds_table.md").read_text())
        a = v["anchor"]
        if v["coverage_conflicts"]:
            # table is still written (for diagnosis) but the run FAILS: cells of
            # one fold that disagree on request count mean some cell is smoke.
            sys.exit("COVERAGE CONFLICT — cells of a fold disagree on how many "
                     "requests they simulated; re-run those folds with --force: "
                     f"{v['coverage_conflicts']}")
        if a.get("ok") is False:
            sys.exit("ANCHOR MISMATCH — this harness does not reproduce the "
                     f"ledgered endpoint; refusing to certify the run: "
                     f"{[c for c in a['checks'] if c['ok'] is False]}")
        print(f"G4 COMPLETE: {len(folds)} folds -> {OUT/'folds_table.md'}  "
              f"fold_stable={v['fold_stable']}  anchor_ok={a.get('ok')}"
              + ("  [SMOKE — NOT A RESULT]" if v["is_smoke_run"] else ""))


if __name__ == "__main__":
    main()
