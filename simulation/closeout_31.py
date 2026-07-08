#!/usr/bin/env python3
"""Phase 3.1 close-out checks (run after the grid; 20-way parallel).

A. Router-knob sensitivity at each window's corner (C*, TP*, N*): replay
   with the two knobs DynoSim Sweep tunes — overlap_score_credit and
   prefill_load_scale — at half/double their defaults, and verify the
   evaluation-SLA verdict does not flip. This is the piece of the official
   sweep's router-search stage our cost-minimizing grid omitted
   (progress/phase3-baselines.md, "Relation to DynoSim Sweep").
B. Binding-config verification: the all-windows static config is
   C=16 encoders + LLM TP2xN2 (binding windows burst5 / burst1). Verify
   that config is feasible on EVERY window: converter at C=16 (reusing
   cached points where present) + TP2xN2 replay on the C16-shifted trace.

Outputs one JSON per check under results/grid/closeout/ (idempotent) and
closeout_summary.json. Run: python3 simulation/closeout_31.py
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sweep_load as sl  # noqa: E402
import sweep_grid as sg  # noqa: E402

OUT = HERE / "results" / "grid" / "closeout"
GRID = HERE / "results" / "grid"
SLA = sg.SLA
ROUTER_VARIANTS = {
    # overlap_score_credit is hard-bounded to [0,1], 1.0 = default/max —
    # the upper direction doesn't exist; prefill weighting beyond default
    # is prefill_load_scale's job (per the KvRouterConfig validation).
    "credit0.25": {"overlap_score_credit": 0.25},
    "credit0.5": {"overlap_score_credit": 0.5},
    "pls0.5": {"prefill_load_scale": 0.5},
    "pls2.0": {"prefill_load_scale": 2.0},
}
BINDING = {"c": 16, "tp": 2, "n": 2}


def log(msg: str) -> None:
    print(f"[closeout {datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def replay(tag: str, trace: Path, tp: int, n: int, extra: list[str]) -> dict:
    pp = OUT / f"{tag}.json"
    if pp.exists():
        return json.loads(pp.read_text())
    report = OUT / "reports" / f"{tag}.report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = sl.run_logged(["env", f"AIC_TP={tp}", "bash", str(sl.RUN_REPLAY),
                        str(trace), "aic", str(report), str(n)] + extra,
                       OUT / "logs" / f"{tag}.log", cwd=HERE,
                       timeout=sl.REPLAY_TIMEOUT_S * 2)
    if rc != 0 or not report.exists():
        raise RuntimeError(f"replay failed (exit {rc}) for {tag}")
    rep = json.loads(report.read_text())
    ttft99, itl99 = float(rep["p99_ttft_ms"]), float(rep["p99_itl_ms"])
    rec = {"tag": tag, "ttft_p99": ttft99, "itl_p99": itl99,
           "feasible": ttft99 < SLA["llm_ttft_p99_ms"] and itl99 < SLA["llm_itl_p99_ms"],
           "wall_s": round(time.time() - t0, 1)}
    pp.write_text(json.dumps(rec, indent=1))
    log(f"  {tag}: TTFT p99 {ttft99:.0f}, ITL p99 {itl99:.1f}, feasible={rec['feasible']}")
    return rec


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = json.loads((GRID / "grid_summary.json").read_text())
    windows = json.loads(sg.WINDOWS_FILE.read_text())
    corners = {w: r for w, r in summary["per_window"].items()
               if r["c_star"] is not None}

    jobs = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        # A: router sensitivity at each corner
        for w, r in corners.items():
            trace = GRID / "traces" / f"grid_{w}_C{r['c_star']}.jsonl"
            for vname, cfg in ROUTER_VARIANTS.items():
                tag = f"router_{w}_C{r['c_star']}_TP{r['tp_star']}_N{r['n_star']}_{vname}"
                jobs.append((tag, ex.submit(
                    replay, tag, trace, r["tp_star"], r["n_star"],
                    ["--router-config", json.dumps(cfg)])))
        # B: binding config on every window (converter at C=16 first, serial
        # per window inside the pool via a small closure)
        def binding_job(w: str) -> dict:
            vp = GRID / f"vision_{w}_C{BINDING['c']}.json"
            if vp.exists():
                vrec = json.loads(vp.read_text())
            else:
                vrec = sg.vision_point(GRID, w, windows[w], BINDING["c"], False)
            return replay(f"binding_{w}_C16_TP2_N2", Path(vrec["trace"]),
                          BINDING["tp"], BINDING["n"], [])
        for w in corners:
            jobs.append((f"binding_{w}", ex.submit(binding_job, w)))

        results, failures = {}, []
        for tag, fut in jobs:
            try:
                results[tag] = fut.result()
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{tag}: {exc}")
                log(f"  FAILED {tag}: {exc}")

    flips = [t for t, r in results.items()
             if t.startswith("router_") and not r["feasible"]]
    binding_bad = [t for t, r in results.items()
                   if t.startswith("binding_") and not r["feasible"]]
    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "router_variants": ROUTER_VARIANTS, "binding_config": BINDING,
        "results": results,
        "router_verdict_flips": flips,
        "binding_infeasible": binding_bad,
        "failures": failures,
        "conclusion": ("PASS: no router-knob verdict flips; binding config "
                       "feasible on all windows" if not flips and not binding_bad
                       and not failures else "ATTENTION — see lists above"),
    }
    (OUT / "closeout_summary.json").write_text(json.dumps(out, indent=1))
    log(f"summary: {out['conclusion']}")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
