#!/usr/bin/env python3
"""A11 'the race — language pool': planner replays with per-request records.

4 windows x {fc_chronos, fc_toto, reactive} x replica leads {60,120,300} =
36 dynamo.replay planner runs on the ledgered grid traces, each emitting
  <tag>.report.json      aggregate (anchor-asserted at L60 vs ledgered twins)
  <tag>.requests.jsonl   per-request records (this session's source-build patch:
                         PlannerReplayBridge report_jsonl_path)
  <tag>.log              stdout incl. the planner "Scaling events" block
Configs replicate the ledgered runs exactly (episode twins / live51 cap4 twins /
riders ladder); fc uses replay_with_forecast.py (tail-aware SCALE=8.0, p90, 15s).
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/a11_runs"
OUT.mkdir(parents=True, exist_ok=True)
RR = ROOT / "simulation/run_replay.sh"
SRC_PY = ROOT / "ai-dynamo/dynamo/.venv/bin/python"
ENTRY = ROOT / "simulation/replay_with_forecast.py"
SMOKE = ROOT / "simulation/planner_forecast_smoke.json"
LADDER = ROOT / "simulation/results/riders44/planner_ladder_t200_20.json"
FC_CAP4 = ROOT / "simulation/results/live51/planner_fc_twin_cap4.json"
RE_CAP4 = ROOT / "simulation/results/live51/planner_re_twin_cap4.json"
TR = ROOT / "simulation/results/grid/traces"

WINDOWS = {
    "burst3": {"trace": TR / "grid_burst3_C7.jsonl", "t0": "2024-10-18 10:18:00",
               "fc_cfg": FC_CAP4, "re_cfg": RE_CAP4},
    "burst5": {"trace": TR / "grid_burst5_C8.jsonl", "t0": "2024-10-18 14:32:00",
               "fc_cfg": SMOKE, "re_cfg": LADDER},
    "burst4": {"trace": TR / "grid_burst4_C7.jsonl", "t0": "2024-10-18 15:37:00",
               "fc_cfg": SMOKE, "re_cfg": LADDER},
    "burst1": {"trace": TR / "grid_burst1_C6.jsonl", "t0": "2024-10-21 12:59:00",
               "fc_cfg": SMOKE, "re_cfg": LADDER},
    # full 5.60-day covered span: the composed week trace under the winning
    # encoder schedule (the exact trace of the ledgered llm_week runs)
    "week": {"trace": ROOT / "simulation/results/aggregate44/fc_p90_L30.jsonl",
             "t0": "2024-10-16 21:39:00", "fc_cfg": SMOKE, "re_cfg": LADDER},
}
LEADS = [60, 120, 300]
# ledgered anchors at L=60 (episode twins / live51 twins / riders ladder)
EXPECT = {("burst3", "fc_chronos"): 651.1, ("burst3", "reactive"): 3494.7,
          ("burst5", "fc_chronos"): 651.1, ("burst5", "reactive"): 2151.6,
          ("burst4", "fc_chronos"): 651.1, ("burst4", "reactive"): 2775.8,
          ("burst1", "fc_chronos"): 705.5, ("burst1", "reactive"): 1615.5,
          ("week", "fc_chronos"): 651.1, ("week", "fc_toto"): 651.1,
          ("week", "reactive"): 1196.6}


def run_cell(window: str, policy: str, lead: int) -> tuple[str, dict]:
    w = WINDOWS[window]
    tag = f"{window}_{policy}_L{lead}"
    rep = OUT / f"{tag}.report.json"
    env = {**os.environ, "RUST_LOG": "warn", "AIC_TP": "2", "AIC_VER": "0.19.0",
           "REPLAY_PY": str(SRC_PY), "STARTUP_TIME": str(lead)}
    cfg = w["re_cfg"]
    if policy.startswith("fc_"):
        cfg = w["fc_cfg"]
        env.update(REPLAY_ENTRY=str(ENTRY), FORECAST_T0=w["t0"],
                   FORECAST_MODEL=policy.split("_")[1], FORECAST_QUANTILE="p90",
                   FORECAST_RESOLUTION="15s", FORECAST_REQ_SCALE="8.0")
    cmd = ["bash", str(RR), str(w["trace"]), "aic", str(rep), "2",
           "--planner-config", str(cfg),
           "--report-jsonl", str(OUT / f"{tag}.requests.jsonl")]
    with open(OUT / f"{tag}.log", "w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
    if r.returncode != 0:
        return tag, {"error": f"replay rc={r.returncode} (see {tag}.log)"}
    d = json.load(open(rep))
    res = {"ttft_p99": round(d["p99_ttft_ms"], 1), "itl_p99": round(d["p99_itl_ms"], 1),
           "gpu_h": round(d["gpu_hours"], 2),
           "ledger_expected": EXPECT.get((window, policy)) if lead == 60 else None}
    exp = res["ledger_expected"]
    # planner-in-loop replays carry a documented ~4% p99 run-noise band
    # (tex/closedloop.tex); forecast cells reproduce exactly, reactive/ARIMA
    # cells within the band.
    if exp is not None and abs(res["ttft_p99"] - exp) > max(0.5, exp * 0.04):
        res["error"] = f"anchor mismatch: {res['ttft_p99']} vs {exp}"
    elif exp is not None and abs(res["ttft_p99"] - exp) > 0.5:
        res["note"] = f"within documented ~4% planner-in-loop run noise (ledgered {exp})"
    nreq = sum(1 for _ in open(OUT / f"{tag}.requests.jsonl"))
    res["requests"] = nreq
    return tag, res


def main() -> None:
    only = sys.argv[1:] or None
    cells = [(w, p, l) for w in WINDOWS for p in ("fc_chronos", "fc_toto", "reactive")
             for l in ([60] if w == "week" else LEADS)
             if only is None or f"{w}_{p}_L{l}" in only]
    results = {}
    if (OUT / "verification.json").exists():
        results = json.load(open(OUT / "verification.json"))
    with ThreadPoolExecutor(max_workers=int(os.environ.get("A11_CONC", "6"))) as ex:
        for tag, res in ex.map(lambda a: run_cell(*a), cells):
            mark = res.get("error") or (
                "MATCHES LEDGER" if res.get("ledger_expected") is not None else "NEW CELL")
            print(f"{tag}: ttft_p99={res.get('ttft_p99')} n={res.get('requests')} [{mark}]",
                  flush=True)
            results[tag] = res
    (OUT / "verification.json").write_text(json.dumps(results, indent=1))
    bad = [t for t, r in results.items() if "error" in r]
    if bad:
        sys.exit(f"FAILED: {bad}")
    print(f"all {len(results)} runs verified")


if __name__ == "__main__":
    main()
