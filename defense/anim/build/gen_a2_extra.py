#!/usr/bin/env python3
"""A2 extra episodes: fleet over the 11 unevaluated in-coverage burst episodes
(e7..e17 from detect_extra_episodes.py) x {forecast p90 chronos, reactive} x
L{15,30,45,165}. Same ledgered pipeline as gen_a2_fleet.py (issue-time
forecast, 15-s reactive, rho15, hyst 3 min, snapshot-graph converter with
--series-out). These windows have NO ledgered cells — every result is a new
run under the identical law, recorded in verification.json.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/gio/tese")
EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
OUTDIR = ROOT / "defense/anim/data/a2x_runs"
OUTDIR.mkdir(parents=True, exist_ok=True)
WINJSON = ROOT / "defense/anim/data/windows_ext.json"
WINS = json.load(open(WINJSON))
ENV = {**os.environ, "TESE_WINDOWS": str(WINJSON), "TESE_ROOT": str(ROOT)}
WINDOWS = [k for k in WINS if k.startswith("e") and WINS[k].get("in_coverage")]
LEADS = [15, 30, 45, 165]


def run_cell(window: str, policy: str, lead: int) -> tuple[str, dict]:
    tag = f"{window}_{policy}_L{lead}"
    sched = OUTDIR / f"{tag}.sched.json"
    out = OUTDIR / f"{tag}.jsonl"
    series = OUTDIR / f"{tag}.series.json"
    if policy == "forecast":
        g = [str(EDA_PY), str(ROOT / "verification/scripts/forecast_schedule_issuetime.py"),
             "--window", window, "--quantile", "p90", "--rho", "15",
             "--cold-start-s", str(lead),
             "--parquet", str(ROOT / "predictors/results/chronos_images.parquet"),
             "--out", str(sched)]
    else:
        g = [str(EDA_PY), str(ROOT / "simulation/forecast_schedule.py"),
             "--window", window, "--policy", "reactive", "--resolution", "15s",
             "--rho", "15", "--cold-start-s", str(lead), "--hysteresis-min", "3",
             "--out", str(sched)]
    r = subprocess.run(g, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return tag, {"error": f"gen: {r.stderr[-400:]}"}
    w = WINS[window]
    c = [str(AIC_PY), str(ROOT / "defense/anim/build/a2_conv_snapshot.py"),
         "--out", str(out), "--offset", str(w["offset"]),
         "--max-requests", str(w["max_requests"]), "--encoder-workers", "2",
         "--worker-schedule", str(sched), "--series-out", str(series)]
    r = subprocess.run(c, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return tag, {"error": f"conv: {r.stderr[-400:]}"}
    st = json.load(open(f"{out}.stats.json"))
    return tag, {"p99_ms": st["encoder_delay_ms"]["p99"],
                 "max_ms": st["encoder_delay_ms"]["max"],
                 "provisioned_ws": st["provisioned_worker_seconds"],
                 "queue_divergent": st["queue_divergent"],
                 "ledger_expected": None}


def main() -> None:
    cells = [(w, p, l) for w in WINDOWS for p in ("forecast", "reactive") for l in LEADS]
    results = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        for tag, res in ex.map(lambda a: run_cell(*a), cells):
            print(tag, res.get("error") or f"p99={res['p99_ms']}", flush=True)
            results[tag] = res
    (OUTDIR / "verification.json").write_text(json.dumps(results, indent=1))
    bad = [t for t, r in results.items() if "error" in r]
    if bad:
        sys.exit(f"FAILED: {bad}")
    # summary: where does reactive fail?
    print("\nwindow  onset  " + "  ".join(f"re L{l}" for l in LEADS) + "   fc worst")
    for wk in WINDOWS:
        rp = [results[f"{wk}_reactive_L{l}"]["p99_ms"] for l in LEADS]
        fp = max(results[f"{wk}_forecast_L{l}"]["p99_ms"] for l in LEADS)
        marks = "  ".join(f"{v:8.0f}{'X' if v >= 1000 else ' '}" for v in rp)
        print(f"{wk:6s} {WINS[wk]['onset_min']:4d}m  {marks}  {fp:8.0f}")


if __name__ == "__main__":
    main()
