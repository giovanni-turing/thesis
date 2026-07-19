#!/usr/bin/env python3
"""A2 'The race' — regenerate burst3 policy runs WITH per-second series.

Re-runs the exact ledgered pipeline (schedule generator -> two-pool converter)
for forecast-p90 (issue-time, warm-pool) and reactive policies at each
cold-start lead, adding --series-out so every on-screen pixel is simulator
output. Endpoint p99s are asserted against the ledgered values:

  reactive rho15 (simulation/results/results_44.jsonl, = thesis Tab. 7.3):
      L15 9481.285 / L30 16078.706 / L45 28342.19  (L165: new cell, same law)
  forecast p90/rho15 chronos issue-time warm
      (results/factorial_issuetime/factorial_issuetime_p90_rho15_results.json):
      p99 = max = 588.37 at L in {15,30,45,165}

Replicates run_cell.py / run_44_factorial_issuetime.py invocations verbatim
(burst3: --offset 531966 --max-requests 3093 --encoder-workers 2).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/gio/tese")
EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
OUTDIR = ROOT / "defense/anim/data/a2_runs"
OUTDIR.mkdir(parents=True, exist_ok=True)
WIN = json.load(open(ROOT / "simulation/windows.json"))["burst3"]

LEADS = [15, 30, 45, 165]
LEDGER = {  # (policy, lead) -> expected p99_ms (None = new cell, no assertion)
    ("forecast", 15): 588.37, ("forecast", 30): 588.37,
    ("forecast", 45): 588.37, ("forecast", 165): 588.37,
    ("reactive", 15): 9481.285, ("reactive", 30): 16078.706,
    ("reactive", 45): 28342.19, ("reactive", 165): None,
}


def gen_schedule(policy: str, lead: int, sched: Path) -> None:
    if policy == "forecast":
        cmd = [str(EDA_PY), str(ROOT / "verification/scripts/forecast_schedule_issuetime.py"),
               "--window", "burst3", "--quantile", "p90", "--rho", "15",
               "--cold-start-s", str(lead),
               "--parquet", str(ROOT / "predictors/results/chronos_images.parquet"),
               "--out", str(sched)]
    else:  # reactive twin: identical law/rho/hysteresis, trailing observed rate
        cmd = [str(EDA_PY), str(ROOT / "simulation/forecast_schedule.py"),
               "--window", "burst3", "--policy", "reactive", "--resolution", "15s",
               "--rho", "15", "--cold-start-s", str(lead), "--hysteresis-min", "3",
               "--out", str(sched)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"schedule gen failed ({policy} L{lead}):\n{r.stderr[-800:]}")
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else f"{policy} L{lead}: sched ok")


def run_converter(sched: Path, tag: str) -> dict:
    out = OUTDIR / f"{tag}.jsonl"
    series = OUTDIR / f"{tag}.series.json"
    # a2_conv_snapshot shim = trace_to_two_pool under the load-bearing snapshot
    # encoder graph (patch-embed operator off; see shim docstring).
    cmd = [str(AIC_PY), str(ROOT / "defense/anim/build/a2_conv_snapshot.py"),
           "--out", str(out), "--offset", str(WIN["offset"]),
           "--max-requests", str(WIN["max_requests"]), "--encoder-workers", "2",
           "--worker-schedule", str(sched), "--series-out", str(series)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"converter failed ({tag}):\n{r.stderr[-800:]}")
    stats = json.load(open(f"{out}.stats.json"))
    # keep the per-request jsonl too: extract_a2.py derives per-request encoder
    # delays from emitted-vs-raw timestamps (delay is folded into the arrival)
    return stats


def main() -> None:
    results = {}
    for policy in ("forecast", "reactive"):
        for lead in LEADS:
            tag = f"{policy}_L{lead}"
            sched = OUTDIR / f"{tag}.sched.json"
            gen_schedule(policy, lead, sched)
            stats = run_converter(sched, tag)
            p99 = stats["encoder_delay_ms"]["p99"]
            exp = LEDGER[(policy, lead)]
            verdict = "NEW CELL" if exp is None else (
                "MATCHES LEDGER" if abs(p99 - exp) < 0.5 else f"MISMATCH exp {exp}")
            if exp is not None and abs(p99 - exp) >= 0.5:
                sys.exit(f"{tag}: p99 {p99} != ledgered {exp} — refusing to proceed")
            print(f"{tag}: p99={p99:.2f} max={stats['encoder_delay_ms']['max']:.0f} "
                  f"prov={stats['provisioned_worker_seconds']:.0f} ws  [{verdict}]")
            results[tag] = {"p99_ms": p99, "max_ms": stats["encoder_delay_ms"]["max"],
                            "provisioned_ws": stats["provisioned_worker_seconds"],
                            "queue_divergent": stats["queue_divergent"],
                            "ledger_expected": exp}
    (OUTDIR / "verification.json").write_text(json.dumps(results, indent=1))
    print(f"all runs verified -> {OUTDIR}")


if __name__ == "__main__":
    main()
