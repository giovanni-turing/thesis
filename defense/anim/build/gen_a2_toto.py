#!/usr/bin/env python3
"""A2 Toto arm: forecast p90 runs from the TOTO archive for all 9 selector
windows x L{15,30,45,165}. Core windows (burst1/3/4/5, steady24h) are asserted
against the ledgered Toto rows of the issue-time factorial; e-windows are new
cells under the same law. Same pipeline as gen_a2_fleet.py.
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
OUTDIR = ROOT / "defense/anim/data/a2t_runs"
OUTDIR.mkdir(parents=True, exist_ok=True)
WINJSON = ROOT / "defense/anim/data/windows_ext.json"
WINS = json.load(open(WINJSON))
ENV = {**os.environ, "TESE_WINDOWS": str(WINJSON), "TESE_ROOT": str(ROOT)}
WINDOWS = ["burst3", "burst5", "burst4", "burst1", "steady24h", "e11", "e10", "e17", "e13"]
LEADS = [15, 30, 45, 165]

exp = {}
fact = json.load(open(ROOT / "simulation/results/factorial_issuetime/"
                             "factorial_issuetime_p90_rho15_results.json"))["results"]
for r in fact:
    if r.get("model") == "toto" and r.get("readiness") == "warm":
        exp[(r["window"], r["lead"])] = (r["p99_ms"], r["provisioned_ws"])


def run_cell(window: str, lead: int) -> tuple[str, dict]:
    tag = f"{window}_forecast_toto_L{lead}"
    sched = OUTDIR / f"{tag}.sched.json"
    out = OUTDIR / f"{tag}.jsonl"
    series = OUTDIR / f"{tag}.series.json"
    g = [str(EDA_PY), str(ROOT / "verification/scripts/forecast_schedule_issuetime.py"),
         "--window", window, "--quantile", "p90", "--rho", "15",
         "--cold-start-s", str(lead),
         "--parquet", str(ROOT / "predictors/results/toto_images.parquet"),
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
    p99 = st["encoder_delay_ms"]["p99"]
    ws = st["provisioned_worker_seconds"]
    e = exp.get((window, lead))
    res = {"p99_ms": p99, "max_ms": st["encoder_delay_ms"]["max"],
           "provisioned_ws": ws, "queue_divergent": st["queue_divergent"],
           "ledger_expected": e[0] if e else None}
    if e and (abs(p99 - e[0]) > 0.5 or abs(ws - e[1]) > 5):
        res["error"] = f"mismatch: p99 {p99} vs {e[0]}, ws {ws} vs {e[1]}"
    return tag, res


def main() -> None:
    cells = [(w, l) for w in WINDOWS for l in LEADS]
    results = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for tag, res in ex.map(lambda a: run_cell(*a), cells):
            mark = ("ERROR " + res["error"]) if "error" in res else (
                "NEW CELL" if res["ledger_expected"] is None else "MATCHES LEDGER")
            print(f"{tag}: p99={res.get('p99_ms','-')} [{mark}]", flush=True)
            results[tag] = res
    (OUTDIR / "verification.json").write_text(json.dumps(results, indent=1))
    bad = [t for t, r in results.items() if "error" in r]
    if bad:
        sys.exit(f"FAILED: {bad}")
    print(f"all {len(results)} toto runs done")


if __name__ == "__main__":
    main()
