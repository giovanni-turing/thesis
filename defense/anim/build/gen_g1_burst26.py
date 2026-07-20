#!/usr/bin/env python3
"""G1 — grade burst2 and burst6 with a REAL FORECAST policy, both pools, E2E.

WHY THIS EXISTS
---------------
tex/closedloop.tex (Limitations) concedes:

    "the two out-of-span episodes (burst2/6, inside the first 1.4 days consumed
     as forecast context) are graded only by the forecast-free baselines of
     Chapter 5, never by a FORECAST policy -- the forecast is structurally
     absent there, a hole a deployed system entering the week with prior
     history would not have."

The expanding-context archives (predictors/results/{model}_{signal}_expctx.parquet,
built by predictors/benchmark_expctx.py) issue forecasts from 2024-10-15 12:03:00
= ~3 min into the trace, instead of requiring a full fixed context window.
burst2 starts 2024-10-15 21:16:02.822 (9.2 h of forecast history available) and
burst6 starts 2024-10-15 23:26:00.018 (11.4 h). Both are therefore INSIDE the
forecastable span once the archive is expanding-context. The hole is no longer
structural; this driver fills it.

WHAT IT RUNS (identical ledgered law, nothing new invented)
-----------------------------------------------------------
Encoder pool (RTX 5090, AIC-costed; a2_conv_snapshot.py converter):
  enc_fc_{chronos,toto,timesfm}_L30
        forecast_schedule_issuetime.py --quantile p90 --rho 15 --cold-start-s 30
        against {model}_images_expctx.parquet   (encoder issue-time lead L=30)
  enc_reactive_L30
        simulation/forecast_schedule.py --policy reactive --rho 15 --cold-start-s 30
  enc_static_C8 / enc_static_C2
        deployable static / calm-day optimum (Chapter-5 forecast-free baselines)

Language pool (H100, dynamo.replay mocker, TP2, AIC_VER 0.19.0, initial 2 replicas),
each arm running on ITS OWN encoder-composed trace (so the seam is real E2E):
  lang_fc_{model}_L{60,120,300}   planner simulation/planner_forecast_smoke.json
                                  + replay_with_forecast.py, FORECAST_SUFFIX=_expctx,
                                  p90 / 15s / FORECAST_REQ_SCALE=8.0
  lang_reactive_L{60,120,300}     SLA planner ARIMA ladder
                                  simulation/results/riders44/planner_ladder_t200_20.json
  lang_static_C8                  no planner, 2 replicas, on the C8-composed trace
  lang_repro_gridC8               REPRODUCTION ANCHOR. The static replay on the LEDGERED
                                  Chapter-5 trace simulation/results/grid/traces/
                                  grid_{w}_C8.jsonl, under the LEDGERED RUNTIME
                                  (pinned ai-dynamo==1.2.1 wheel, AIC_VER default
                                  0.22.0, no startup_time), asserted to 0.5 ms against
                                  the ledgered report (burst2 766.259 / burst6 735.318).
  lang_runtime_gridC8             The SAME trace + same fixed 2 replicas under THIS
                                  session's runtime (dynamo source build 70c965db26,
                                  AIC_VER 0.19.0). Its gap to lang_repro_gridC8 is the
                                  RUNTIME DELTA -- measured, not assumed, so Chapter-5
                                  numbers and this track's numbers can be compared
                                  honestly. Measured at smoke time: burst6 700.3 vs
                                  735.3 ms = -4.8 %, systematic (not run noise).

METHODOLOGY INVARIANTS (do not break these)
-------------------------------------------
* Forecasts are ARCHIVED OFFLINE and looked up. Nothing is forecast in flight.
* Everything endogenous -- encoder queue/delay, TTFT, ITL, replica decisions,
  SLA verdicts -- is computed by the discrete-event mocker / converter FIFO from
  silicon-calibrated timings.
* SLA: TTFT p99 <= 1000 ms, ITL p99 <= 100 ms (graded, not assumed).
* Writes only NEW files under defense/anim/data/g1_runs/. Reads ledgered
  artifacts; never writes them.

USAGE
-----
  # full track (both windows, all arms) -- SUPERVISOR COMMAND
  ai-dynamo/dynamo/.venv/bin/python defense/anim/build/gen_g1_burst26.py

  # smoke: preflight + burst6 encoder stage + 2 language cells
  ... gen_g1_burst26.py --smoke

  # subsets
  ... gen_g1_burst26.py --windows burst6 --stage enc
  ... gen_g1_burst26.py --only burst6_lang_fc_chronos_L60

Concurrency: G1_ENC_CONC (default 6), G1_LANG_CONC (default 4).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/g1_runs"
WINJSON = ROOT / "defense/anim/data/windows_ext.json"

EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
SRC_PY = ROOT / "ai-dynamo/dynamo/.venv/bin/python"

RR = ROOT / "simulation/run_replay.sh"
CONV = ROOT / "defense/anim/build/a2_conv_snapshot.py"
GEN_FC = ROOT / "verification/scripts/forecast_schedule_issuetime.py"
GEN_RE = ROOT / "simulation/forecast_schedule.py"
ENTRY = ROOT / "simulation/replay_with_forecast.py"
SMOKE_CFG = ROOT / "simulation/planner_forecast_smoke.json"
LADDER = ROOT / "simulation/results/riders44/planner_ladder_t200_20.json"
GRID_TR = ROOT / "simulation/results/grid/traces"
GRID_REP = ROOT / "simulation/results/grid/reports"

WINDOWS = ["burst2", "burst6"]
MODELS = ["chronos", "toto", "timesfm"]
LANG_LEADS = [60, 120, 300]
ENC_LEAD = 30          # ledgered encoder issue-time lead
SLA_TTFT_MS = 1000.0
SLA_ITL_MS = 100.0

# Chapter-5 ledgered forecast-free anchors (reused, asserted -- never re-derived).
# encoder: grid_{w}_C{n}.jsonl.stats.json -> encoder_delay_ms.p99
# language: grid_llm_{w}_C8_N2_TP2_aic.report.json -> p99_ttft_ms
LEDGER_ENC = {("burst2", 8): 855.829, ("burst2", 2): 6321.347,
              ("burst6", 8): 720.108, ("burst6", 2): 5333.174}
LEDGER_LANG_GRIDC8 = {"burst2": 766.259, "burst6": 735.318}

ENV = {**os.environ, "TESE_WINDOWS": str(WINJSON), "TESE_ROOT": str(ROOT)}


# ---------------------------------------------------------------- preflight --
@lru_cache(maxsize=None)
def window_t0(offset: int):
    """Trace-anchored window start, via the shipped ledgered helper.

    Memoized: window_start_ts() re-parses the full 1M-row trace CSV on every
    call, and this is called once per forecast language cell from inside the
    4-thread pool (up to 4 concurrent 1M-row parses). The result is a pure
    deterministic function of `offset`, so caching cannot change any number.
    """
    import pandas as pd  # noqa: F401  (imported for the helper's own use)
    sys.path.insert(0, str(ROOT / "simulation"))
    from forecast_schedule import window_start_ts
    return window_start_ts(offset)


def preflight() -> dict:
    """THE CRITICAL CORRECTNESS CHECK.

    The whole track is invalid unless the expanding-context archive's first
    forecast origin PRECEDES each window's t0, and the archive covers the window
    contiguously at 15 s. Assert it explicitly; refuse to run otherwise.
    """
    import pandas as pd
    W = json.load(open(WINJSON))
    report = {"windows": {}, "archives": {}}
    ok = True
    for w in WINDOWS:
        d = W[w]
        t0 = window_t0(d["offset"])
        t1 = t0 + pd.Timedelta(seconds=d["span_s"])
        report["windows"][w] = {"offset": d["offset"], "n": d["max_requests"],
                                "t0": str(t0), "t1": str(t1),
                                "span_s": d["span_s"]}
    for model in MODELS:
        for sig in ["images", "requests", "ctx", "gen"]:
            p = ROOT / f"predictors/results/{model}_{sig}_expctx.parquet"
            if not p.exists():
                report["archives"][f"{model}_{sig}"] = {"error": "MISSING"}
                ok = False
                continue
            df = pd.read_parquet(p)
            df = df[df.resolution == "15s"].sort_values("ts")
            first, last = df.ts.min(), df.ts.max()
            ent = {"first_forecast_ts": str(first), "last_forecast_ts": str(last),
                   "rows": int(len(df)), "duplicate_ts": int(df.ts.duplicated().sum())}
            for w in WINDOWS:
                t0 = pd.Timestamp(report["windows"][w]["t0"])
                t1 = pd.Timestamp(report["windows"][w]["t1"])
                lo = t0 - pd.Timedelta(minutes=1)
                sub = df[(df.ts >= lo) & (df.ts <= t1)]
                exp = int((t1 - lo).total_seconds() // 15)
                covers = bool(first <= t0 and last >= t1)
                contiguous = bool(
                    len(sub) >= exp
                    and set(sub.ts.diff().dropna().unique()) <= {pd.Timedelta(seconds=15)})
                ent[w] = {"covers_window": covers, "contiguous_15s": contiguous,
                          "rows_in_window": int(len(sub)), "rows_expected": exp,
                          "lead_time_h_before_t0": round(
                              (t0 - first).total_seconds() / 3600.0, 2)}
                if not (covers and contiguous):
                    ok = False
            report["archives"][f"{model}_{sig}"] = ent
    report["PREFLIGHT_OK"] = ok
    return report


# ------------------------------------------------------------------ encoder --
def enc_cells(windows: list[str]) -> list[str]:
    cells = []
    for w in windows:
        cells += [f"{w}_enc_fc_{m}_L{ENC_LEAD}" for m in MODELS]
        cells += [f"{w}_enc_reactive_L{ENC_LEAD}", f"{w}_enc_static_C8",
                  f"{w}_enc_static_C2"]
    return cells


def run_enc(tag: str) -> tuple[str, dict]:
    w, rest = tag.split("_enc_", 1)
    W = json.load(open(WINJSON))[w]
    out = OUT / f"{tag}.jsonl"
    sched = OUT / f"{tag}.sched.json"
    workers = 1
    res: dict = {"stage": "encoder", "window": w, "arm": rest}

    if rest.startswith("fc_"):
        model = rest.split("_")[1]
        g = [str(EDA_PY), str(GEN_FC), "--window", w, "--quantile", "p90",
             "--rho", "15", "--cold-start-s", str(ENC_LEAD),
             "--parquet", str(ROOT / f"predictors/results/{model}_images_expctx.parquet"),
             "--out", str(sched)]
    elif rest.startswith("reactive"):
        g = [str(EDA_PY), str(GEN_RE), "--window", w, "--policy", "reactive",
             "--resolution", "15s", "--rho", "15", "--cold-start-s", str(ENC_LEAD),
             "--hysteresis-min", "3", "--out", str(sched)]
    else:                                            # static_C{n}
        g = None
        workers = int(rest.split("_C")[1])

    if g is not None:
        r = subprocess.run(g, capture_output=True, text=True, env=ENV)
        if r.returncode != 0:
            return tag, {**res, "error": f"sched: {r.stderr[-500:]}"}

    cmd = [str(AIC_PY), str(CONV), "--out", str(out),
           "--offset", str(W["offset"]), "--max-requests", str(W["max_requests"]),
           "--encoder-workers", str(workers),
           "--series-out", str(OUT / f"{tag}.series.json")]
    if g is not None:
        cmd += ["--worker-schedule", str(sched)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return tag, {**res, "error": f"conv: {r.stderr[-500:]}"}

    st = json.load(open(f"{out}.stats.json"))
    nl = sum(1 for _ in open(out))
    res.update({"requests": nl,
                "enc_p99_ms": round(st["encoder_delay_ms"]["p99"], 3),
                "enc_p90_ms": round(st["encoder_delay_ms"]["p90"], 3),
                "enc_max_ms": round(st["encoder_delay_ms"]["max"], 3),
                "provisioned_worker_s": st["provisioned_worker_seconds"],
                "queue_divergent": st["queue_divergent"],
                "composed_trace": str(out.relative_to(ROOT))})
    if nl != W["max_requests"]:
        res["error"] = f"coverage hole: {nl} != {W['max_requests']}"
    if rest.startswith("static_C"):
        exp = LEDGER_ENC.get((w, workers))
        res["ledger_expected_p99"] = exp
        if exp is not None:
            res["ledger_delta_ms"] = round(res["enc_p99_ms"] - exp, 3)
            # a2_conv_snapshot drops the post-snapshot encoder_patch_embed_gemm
            # op (+0.931 ms @ f(64)) relative to the Chapter-5 grid converter, so
            # a small negative delta is EXPECTED, not a defect. Flag only if the
            # gap is large enough to indicate a different provisioning regime.
            if abs(res["ledger_delta_ms"]) > max(5.0, exp * 0.02):
                res["warn"] = (f"static p99 {res['enc_p99_ms']} vs Chapter-5 grid "
                               f"ledger {exp} (delta {res['ledger_delta_ms']} ms) "
                               f"-- exceeds the snapshot-op band; investigate")
    return tag, res


# ----------------------------------------------------------------- language --
def lang_cells(windows: list[str]) -> list[str]:
    cells = []
    for w in windows:
        for m in MODELS:
            cells += [f"{w}_lang_fc_{m}_L{l}" for l in LANG_LEADS]
        cells += [f"{w}_lang_reactive_L{l}" for l in LANG_LEADS]
        cells += [f"{w}_lang_static_C8", f"{w}_lang_repro_gridC8",
                  f"{w}_lang_runtime_gridC8"]
    return cells


def _src_trace(tag: str) -> tuple[Path, str]:
    """The encoder-composed trace this language cell replays, + its provenance."""
    w, rest = tag.split("_lang_", 1)
    if rest.endswith("gridC8"):
        return GRID_TR / f"grid_{w}_C8.jsonl", "ledgered Chapter-5 grid trace"
    if rest == "static_C8":
        return OUT / f"{w}_enc_static_C8.jsonl", "this track's C8 static composed trace"
    if rest.startswith("fc_"):
        model = rest.split("_")[1]
        return OUT / f"{w}_enc_fc_{model}_L{ENC_LEAD}.jsonl", "forecast-composed (expctx)"
    return OUT / f"{w}_enc_reactive_L{ENC_LEAD}.jsonl", "reactive-composed"


def run_lang(tag: str) -> tuple[str, dict]:
    w, rest = tag.split("_lang_", 1)
    W = json.load(open(WINJSON))[w]
    n = W["max_requests"]
    trace, prov = _src_trace(tag)
    res: dict = {"stage": "language", "window": w, "arm": rest,
                 "composed_trace": str(trace), "trace_provenance": prov}
    if not trace.exists():
        return tag, {**res, "error": f"missing composed trace {trace} "
                                     f"(run --stage enc first)"}

    lead = int(rest.rsplit("_L", 1)[1]) if "_L" in rest else 60
    rep = OUT / f"{tag}.report.json"
    jsonl = OUT / f"{tag}.requests.jsonl"

    if rest == "repro_gridC8":
        # LEDGERED RUNTIME: pinned ai-dynamo==1.2.1 wheel in the aiconfigurator
        # venv (run_replay.sh default REPLAY_PY), AIC_VER default 0.22.0, and NO
        # startup_time -- exactly what produced the Chapter-5 grid reports. This
        # cell exists to prove we reproduce Chapter 5, so it must not inherit
        # this session's source build. That wheel predates the per-request
        # records patch, so this cell carries NO --report-jsonl and is graded on
        # the aggregate p99 alone; reproduction is enforced at runtime by the
        # 0.5 ms check below, not by any claim recorded here.
        env = {**ENV, "RUST_LOG": "warn", "AIC_TP": "2"}
        lead = None
        res["runtime"] = "ledgered pinned wheel ai-dynamo==1.2.1, AIC_VER 0.22.0, no startup_time"
    else:
        env = {**ENV, "RUST_LOG": "warn", "AIC_TP": "2", "AIC_VER": "0.19.0",
               "REPLAY_PY": str(SRC_PY)}
        res["runtime"] = "this session's dynamo source build 70c965db26, AIC_VER 0.19.0"
        if rest == "runtime_gridC8":
            lead = None      # match the ledgered cell in everything but runtime
        else:
            env["STARTUP_TIME"] = str(lead)

    cmd = ["bash", str(RR), str(trace), "aic", str(rep), "2"]

    if rest.startswith("fc_"):
        model = rest.split("_")[1]
        env.update(REPLAY_ENTRY=str(ENTRY),
                   FORECAST_T0=str(window_t0(W["offset"])),
                   FORECAST_MODEL=model, FORECAST_QUANTILE="p90",
                   FORECAST_RESOLUTION="15s", FORECAST_REQ_SCALE="8.0",
                   FORECAST_SUFFIX="_expctx")
        cmd += ["--planner-config", str(SMOKE_CFG)]
        res["forecast_t0"] = env["FORECAST_T0"]
        res["forecast_suffix"] = "_expctx"
    elif rest.startswith("reactive"):
        cmd += ["--planner-config", str(LADDER)]
    # static / repro arms: no planner -- fixed 2 replicas
    # The repro cell runs the LEDGERED pinned wheel (ai-dynamo==1.2.1), which
    # predates the per-request-records patch (commit 70c965db26) and rejects
    # --report-jsonl outright. Its purpose is the aggregate p99 reproduction, so
    # skip the flag there; downstream code already tolerates a missing jsonl
    # (jsonl.exists() guard below, and the `nl is not None` coverage guard).
    if rest != "repro_gridC8":
        cmd += ["--report-jsonl", str(jsonl)]

    with open(OUT / f"{tag}.log", "w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
    if r.returncode != 0:
        return tag, {**res, "error": f"replay rc={r.returncode} (see {tag}.log)"}

    d = json.load(open(rep))
    nl = sum(1 for _ in open(jsonl)) if jsonl.exists() else None
    res.update({"lead_s": lead, "requests": nl,
                "completed": d["completed_requests"],
                "ttft_p99_ms": round(d["p99_ttft_ms"], 1),
                "itl_p99_ms": round(d["p99_itl_ms"], 1),
                # the ledgered pinned wheel omits gpu_hours; emit null (not NaN,
                # which json.dumps writes bare and strict JSON readers reject)
                "e2e_p99_ms": (round(d["p99_e2e_latency_ms"], 1)
                               if d.get("p99_e2e_latency_ms") is not None else None),
                "gpu_h": (round(d["gpu_hours"], 3)
                          if d.get("gpu_hours") is not None else None)})
    res["sla_ttft_pass"] = bool(res["ttft_p99_ms"] <= SLA_TTFT_MS)
    res["sla_itl_pass"] = bool(res["itl_p99_ms"] <= SLA_ITL_MS)
    res["sla_pass"] = bool(res["sla_ttft_pass"] and res["sla_itl_pass"])
    if d["completed_requests"] != n or (nl is not None and nl != n):
        res["error"] = (f"coverage hole: jsonl {nl} / completed "
                        f"{d['completed_requests']} != {n}")
    if rest == "repro_gridC8":
        exp = LEDGER_LANG_GRIDC8[w]
        res["ledger_expected_ttft_p99"] = exp
        # no planner in the loop here -> deterministic; demand exact reproduction
        if abs(res["ttft_p99_ms"] - exp) > 0.5:
            res["error"] = (f"REPRODUCTION FAILED: {res['ttft_p99_ms']} vs "
                            f"ledgered {exp} ms")
    if rest == "runtime_gridC8":
        exp = LEDGER_LANG_GRIDC8[w]
        res["ledgered_wheel_ttft_p99"] = exp
        res["runtime_delta_ms"] = round(res["ttft_p99_ms"] - exp, 3)
        res["runtime_delta_pct"] = round(100.0 * (res["ttft_p99_ms"] - exp) / exp, 2)
        res["note"] = ("source-build vs pinned-wheel runtime delta on an IDENTICAL "
                       "trace and identical fixed 2 replicas -- the correction to "
                       "apply when comparing this track's numbers to Chapter 5's")
    return tag, res


# --------------------------------------------------------------------- main --
def load_results() -> dict:
    p = OUT / "verification.json"
    return json.load(open(p)) if p.exists() else {}


def save(results: dict) -> None:
    (OUT / "verification.json").write_text(json.dumps(results, indent=1, default=str))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--windows", nargs="*", default=WINDOWS, choices=WINDOWS)
    ap.add_argument("--stage", default="all", choices=["preflight", "enc", "lang", "all"])
    ap.add_argument("--only", nargs="*", default=None, help="explicit cell tags")
    ap.add_argument("--smoke", action="store_true",
                    help="preflight + burst6 encoder stage + 2 burst6 language cells")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    results = load_results()

    pf = preflight()
    results["_preflight"] = pf
    save(results)
    print("=== PREFLIGHT: expanding-context forecast coverage ===", flush=True)
    for w, d in pf["windows"].items():
        print(f"  {w}: t0={d['t0']}  t1={d['t1']}  n={d['n']:,}", flush=True)
    for k, e in pf["archives"].items():
        if "error" in e:
            print(f"  {k}: {e['error']}", flush=True)
            continue
        bits = " ".join(
            f"{w}[covers={e[w]['covers_window']} contig={e[w]['contiguous_15s']} "
            f"+{e[w]['lead_time_h_before_t0']}h]" for w in WINDOWS)
        print(f"  {k}: first={e['first_forecast_ts']} {bits}", flush=True)
    print(f"  PREFLIGHT_OK = {pf['PREFLIGHT_OK']}", flush=True)
    if not pf["PREFLIGHT_OK"]:
        sys.exit("PREFLIGHT FAILED: the expctx archive does not cover burst2/burst6 "
                 "-- the track is invalid, do not interpret any downstream number.")
    if args.stage == "preflight":
        return

    windows = ["burst6"] if args.smoke else args.windows
    ec = enc_cells(windows)
    lc = lang_cells(windows)
    if args.smoke:
        lc = ["burst6_lang_fc_chronos_L60", "burst6_lang_reactive_L60",
              "burst6_lang_static_C8", "burst6_lang_repro_gridC8",
              "burst6_lang_runtime_gridC8"]
    if args.only:
        ec = [t for t in ec if t in args.only]
        lc = [t for t in lc if t in args.only]

    if args.stage in ("enc", "all"):
        print(f"\n=== ENCODER STAGE ({len(ec)} cells) ===", flush=True)
        with ThreadPoolExecutor(max_workers=int(os.environ.get("G1_ENC_CONC", "6"))) as ex:
            for tag, res in ex.map(run_enc, ec):
                results[tag] = res
                print(f"  {tag}: " + (res.get("error") or
                      f"enc_p99={res['enc_p99_ms']} ms n={res['requests']} "
                      f"prov_ws={res['provisioned_worker_s']}"
                      + (f" [{res['warn']}]" if "warn" in res else "")), flush=True)
        save(results)
        if any("error" in results[t] for t in ec):
            sys.exit(f"encoder stage failed: {[t for t in ec if 'error' in results[t]]}")

    if args.stage in ("lang", "all"):
        print(f"\n=== LANGUAGE STAGE ({len(lc)} cells) ===", flush=True)
        with ThreadPoolExecutor(max_workers=int(os.environ.get("G1_LANG_CONC", "4"))) as ex:
            for tag, res in ex.map(run_lang, lc):
                results[tag] = res
                print(f"  {tag}: " + (res.get("error") or
                      f"ttft_p99={res['ttft_p99_ms']} ms itl_p99={res['itl_p99_ms']} "
                      f"n={res['requests']} SLA={'PASS' if res['sla_pass'] else 'FAIL'}"),
                      flush=True)
        save(results)

    save(results)
    bad = [t for t, r in results.items()
           if isinstance(r, dict) and "error" in r and t in set(ec) | set(lc)]
    if bad:
        sys.exit(f"FAILED: {bad}")
    print(f"\nG1 COMPLETE: {len(ec)} encoder + {len(lc)} language cells "
          f"-> {OUT}/verification.json", flush=True)


if __name__ == "__main__":
    main()
