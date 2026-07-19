#!/usr/bin/env python3
"""A6 'The week' — regenerate the 5.60-day aggregate policy runs with series.

5 policies over windows.json 'aggregate' (offset 250399, 749,601 requests,
2024-10-16 21:39 UTC .. trace end), exact ledgered pipeline (+ --series-out,
converter under the load-bearing snapshot graph via a2_conv_snapshot.py):

  toto_p90_L30   issue-time gen, toto archive, p90 rho15 L30 (warm)
  toto_p50_L30   ditto at p50
  react_L30      forecast_schedule.py --policy reactive 15s rho15 L30 hyst3
  static_C8      converter --encoder-workers 8 (deployable static)
  static_C2      converter --encoder-workers 2 (calm-day optimum)

Ledgered expectations asserted:
  toto p90/p50: week_surface_issuetime_results.json (rho15 L30)
  react_L30 / static_C2: simulation/results/aggregate44/*.jsonl.stats.json
  static_C8: simulation/results/rerun_verify/week_static_C8.jsonl.stats.json
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/gio/tese")
EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
OUTDIR = ROOT / "defense/anim/data/a6_runs"
OUTDIR.mkdir(parents=True, exist_ok=True)
AGG = json.load(open(ROOT / "simulation/windows.json"))["aggregate"]

EXPECT = {  # tag -> (p99_ms, provisioned_ws, ws_tol)
    "toto_p90_L30": (588.37, 2389710, 1500),
    "toto_p50_L30": (1937.67, 1012440, 1500),
    "react_L30": (588.37, 2611319.7, 5),
    "static_C8": (644.44, 3869278.8, 5),
    "static_C2": (2952.781, 967319.7, 5),
}


def gen_sched(tag: str, sched: Path) -> None:
    if tag.startswith("toto"):
        q = "p90" if "p90" in tag else "p50"
        cmd = [str(EDA_PY), str(ROOT / "verification/scripts/forecast_schedule_issuetime.py"),
               "--window", "aggregate", "--quantile", q, "--rho", "15",
               "--cold-start-s", "30",
               "--parquet", str(ROOT / "predictors/results/toto_images.parquet"),
               "--out", str(sched)]
    elif tag == "react_L30":
        cmd = [str(EDA_PY), str(ROOT / "simulation/forecast_schedule.py"),
               "--window", "aggregate", "--policy", "reactive", "--resolution", "15s",
               "--rho", "15", "--cold-start-s", "30", "--hysteresis-min", "3",
               "--out", str(sched)]
    else:
        return
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"sched gen failed ({tag}):\n{r.stderr[-800:]}")


def run(tag: str) -> tuple[str, dict]:
    sched = OUTDIR / f"{tag}.sched.json"
    out = OUTDIR / f"{tag}.jsonl"
    series = OUTDIR / f"{tag}.series.json"
    gen_sched(tag, sched)
    cmd = [str(AIC_PY), str(ROOT / "defense/anim/build/a2_conv_snapshot.py"),
           "--out", str(out), "--offset", str(AGG["offset"]),
           "--max-requests", str(AGG["max_requests"]),
           "--series-out", str(series)]
    if tag.startswith("static"):
        cmd += ["--encoder-workers", tag.split("_C")[1]]
    else:
        cmd += ["--encoder-workers", "2", "--worker-schedule", str(sched)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return tag, {"error": f"conv: {r.stderr[-500:]}"}
    st = json.load(open(f"{out}.stats.json"))
    p99 = st["encoder_delay_ms"]["p99"]
    ws = st["provisioned_worker_seconds"]
    exp_p99, exp_ws, tol = EXPECT[tag]
    res = {"p99_ms": p99, "max_ms": st["encoder_delay_ms"]["max"],
           "provisioned_ws": ws, "queue_divergent": st["queue_divergent"],
           "ledger_expected": {"p99_ms": exp_p99, "provisioned_ws": exp_ws}}
    if abs(p99 - exp_p99) > 0.5 or abs(ws - exp_ws) > tol:
        res["error"] = f"mismatch: p99 {p99} vs {exp_p99}, ws {ws} vs {exp_ws}"
    return tag, res


def main() -> None:
    results = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for tag, res in ex.map(run, EXPECT):
            print(tag, res.get("error") or
                  f"p99={res['p99_ms']} ws={res['provisioned_ws']:.0f} [MATCHES LEDGER]",
                  flush=True)
            results[tag] = res
    (OUTDIR / "verification.json").write_text(json.dumps(results, indent=1))
    bad = [t for t, r in results.items() if "error" in r]
    if bad:
        sys.exit(f"FAILED: {bad}")
    print("all 5 aggregate runs verified")


if __name__ == "__main__":
    main()
