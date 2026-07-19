#!/usr/bin/env python3
"""A2 fleet: regenerate ALL episode runs with per-second series.

5 windows (burst1/3/4/5 + steady24h) x 2 policies x 4 leads {15,30,45,165}
through the exact ledgered pipeline (schedule generator -> two-pool converter
under the load-bearing snapshot encoder graph via a2_conv_snapshot.py).

Endpoint p99s are asserted against the ledgers wherever a ledgered cell exists:
  reactive rho15 L{15,30,45}  -> simulation/results/results_44.jsonl
  forecast p90/rho15 chronos warm L{15,30,45,165}
      -> simulation/results/factorial_issuetime/factorial_issuetime_p90_rho15_results.json
Reactive L165 cells are new (same law; its ledgered neighbor is L300).
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/gio/tese")
EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
OUTDIR = ROOT / "defense/anim/data/a2_runs"
OUTDIR.mkdir(parents=True, exist_ok=True)
WINS = json.load(open(ROOT / "simulation/windows.json"))
WINDOWS = ["burst1", "burst3", "burst4", "burst5", "steady24h"]
LEADS = [15, 30, 45, 165]

# ---- ledgered expectations ----
fc_exp, re_exp = {}, {}
fact = json.load(open(ROOT / "simulation/results/factorial_issuetime/"
                             "factorial_issuetime_p90_rho15_results.json"))["results"]
for r in fact:
    if r.get("model") == "chronos" and r.get("readiness") == "warm":
        fc_exp[(r["window"], r["lead"])] = r["p99_ms"]
for line in open(ROOT / "simulation/results/results_44.jsonl"):
    r = json.loads(line)
    c = r["cell"]
    if (isinstance(c, dict) and c.get("policy") == "reactive" and c.get("rho") == 15
            and c.get("cold_start_s") in (15, 30, 45)):
        re_exp[(c["window"], c["cold_start_s"])] = r["p99_ms"]


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
    r = subprocess.run(g, capture_output=True, text=True)
    if r.returncode != 0:
        return tag, {"error": f"gen: {r.stderr[-400:]}"}
    w = WINS[window]
    c = [str(AIC_PY), str(ROOT / "defense/anim/build/a2_conv_snapshot.py"),
         "--out", str(out), "--offset", str(w["offset"]),
         "--max-requests", str(w["max_requests"]), "--encoder-workers", "2",
         "--worker-schedule", str(sched), "--series-out", str(series)]
    r = subprocess.run(c, capture_output=True, text=True)
    if r.returncode != 0:
        return tag, {"error": f"conv: {r.stderr[-400:]}"}
    st = json.load(open(f"{out}.stats.json"))
    p99 = st["encoder_delay_ms"]["p99"]
    exp = (fc_exp if policy == "forecast" else re_exp).get((window, lead))
    res = {"p99_ms": p99, "max_ms": st["encoder_delay_ms"]["max"],
           "provisioned_ws": st["provisioned_worker_seconds"],
           "queue_divergent": st["queue_divergent"], "ledger_expected": exp}
    if exp is not None and abs(p99 - exp) > max(0.5, exp * 1e-4):
        res["error"] = f"p99 {p99} != ledgered {exp}"
    return tag, res


def main() -> None:
    cells = [(w, p, l) for w in WINDOWS for p in ("forecast", "reactive") for l in LEADS]
    results = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for tag, res in ex.map(lambda a: run_cell(*a), cells):
            mark = ("ERROR " + res["error"]) if "error" in res else (
                "NEW CELL" if res["ledger_expected"] is None else "MATCHES LEDGER")
            print(f"{tag}: p99={res.get('p99_ms', '-')} [{mark}]", flush=True)
            results[tag] = res
    (OUTDIR / "verification.json").write_text(json.dumps(results, indent=1))
    bad = [t for t, r in results.items() if "error" in r]
    if bad:
        sys.exit(f"FAILED cells: {bad}")
    print(f"all {len(results)} runs verified -> {OUTDIR}")


if __name__ == "__main__":
    main()
