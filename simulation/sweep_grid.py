#!/usr/bin/env python3
"""Phase 3.1 — static-optimal baseline: minimum worker counts per window.

For each window in simulation/windows.json (six burst episodes + steady24h,
derived by derive_windows.py), finds the cheapest static configuration
(C encoder workers, N LLM workers) that meets the thesis evaluation SLA at
the trace's own rate (s=1):

  vision:  encoder_delay p99 < 1000 ms AND queue not divergent
  llm:     TTFT p99 < 1000 ms AND ITL p99 < 100 ms   (AIC h100_sxm timing)

Search structure — NOT a full grid. Under the per-pool SLA the vision bound
depends only on C (the FIFO encoder sim lives in the converter), and the LLM
bound depends on N given the C*-shifted arrivals. Feasibility is monotone in
worker count, so each pool is a 1-D first-feasible walk up a ladder plus an
integer bisection refine:

  Phase V: C ladder walk (converter run per C; the run at each C also emits
           the encoder-shifted mooncake trace) -> C* = min feasible C.
  Phase L: N ladder walk replaying the C* trace via run_replay.sh -> N*.
  Cross-check: replay (C*+1 rung, N*) — LLM feasibility must not flip, which
           validates treating the corner point as the optimum (the encoder
           shift only smooths arrivals as C grows).

GPU-hours are reported PER HARDWARE CLASS and never summed: rtx5090-hours =
C* x span, h100-hours = N* x span (8B at TP1: one GPU per worker). The
summary also computes the all-windows static configuration (max C*, max N*
over windows) and its overprovisioning factor on steady24h — the headline.

Idempotent like sweep_load.py: point JSONs under --out-dir are reused unless
--force. Run with any python3; sub-work runs in the aiconfigurator venv:
  python3 simulation/sweep_grid.py --windows steady24h burst3
  python3 simulation/sweep_grid.py            # all windows, default ladders
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sweep_load as sl  # noqa: E402  (run_logged, run_converter, VENV_PY, ...)

WINDOWS_FILE = HERE / "windows.json"
SLA = {"vision_p99_ms": 1000.0, "llm_ttft_p99_ms": 1000.0, "llm_itl_p99_ms": 100.0}


def log(msg: str) -> None:
    print(f"[grid {datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------
# Points (idempotent JSON per (pool, window, workers))
# --------------------------------------------------------------------------

def vision_point(out_dir: Path, window: str, win: dict, c: int, force: bool) -> dict:
    """Converter run at s=1 with C encoder workers; ALSO leaves the
    encoder-shifted trace behind for Phase L."""
    pp = out_dir / f"vision_{window}_C{c}.json"
    if pp.exists() and not force:
        return json.loads(pp.read_text())
    tag = f"grid_{window}_C{c}"
    trace = out_dir / "traces" / f"{tag}.jsonl"
    trace.parent.mkdir(parents=True, exist_ok=True)
    log(f"  converter: {window} C={c}")
    rc = sl.run_converter(
        ["--out", str(trace), "--offset", str(win["offset"]),
         "--max-requests", str(win["max_requests"]), "--encoder-workers", str(c)],
        out_dir / "logs" / f"{tag}.log")
    stats_path = Path(f"{trace}.stats.json")
    if rc != 0 or not stats_path.exists():
        raise RuntimeError(f"converter failed (exit {rc}) for {window}/C{c}")
    st = json.loads(stats_path.read_text())
    rec = {
        "pool": "vision", "window": window, "encoder_workers": c,
        "trace": str(trace), "stats": str(stats_path),
        "offered_img_per_s": st["offered_img_per_s"],
        "horizon_s": st["sim_horizon_s"],
        "encoder_delay_ms": st["encoder_delay_ms"],
        "encoder_utilization": st.get("encoder_utilization"),
        "queue_divergent": bool(st.get("queue_divergent")),
        "feasible": (float(st["encoder_delay_ms"]["p99"]) < SLA["vision_p99_ms"]
                     and not st.get("queue_divergent")),
    }
    pp.write_text(json.dumps(rec, indent=1))
    log(f"    -> delay p99 {st['encoder_delay_ms']['p99']:.0f} ms, "
        f"divergent={rec['queue_divergent']}, feasible={rec['feasible']}")
    return rec


def llm_point(out_dir: Path, window: str, c: int, n: int, timing: str,
              trace: Path, force: bool, tp: int = 1) -> dict:
    tp_tag = "" if tp == 1 else f"_TP{tp}"          # TP1 keeps legacy names
    pp = out_dir / f"llm_{window}_C{c}_N{n}{tp_tag}_{timing}.json"
    if pp.exists() and not force:
        return json.loads(pp.read_text())
    tag = f"grid_llm_{window}_C{c}_N{n}{tp_tag}_{timing}"
    report = out_dir / "reports" / f"{tag}.report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    log(f"  replay: {window} C={c} N={n} TP={tp} ({timing})")
    t0 = time.time()
    rc = sl.run_logged(["env", f"AIC_TP={tp}", "bash", str(sl.RUN_REPLAY),
                        str(trace), timing, str(report), str(n)],
                       out_dir / "logs" / f"{tag}.log", cwd=HERE,
                       timeout=sl.REPLAY_TIMEOUT_S * 2)
    if rc != 0 or not report.exists():
        raise RuntimeError(f"replay failed (exit {rc}) for {window}/C{c}/N{n}/TP{tp}")
    rep = json.loads(report.read_text())
    pick = lambda pfx: {k: rep.get(f"{k}_{pfx}") for k in
                        ("mean", "median", "p90", "p99", "max")}
    ttft, itl = pick("ttft_ms"), pick("itl_ms")
    rec = {
        "pool": "llm", "window": window, "encoder_workers": c, "llm_workers": n,
        "tp": tp, "gpus": tp * n,
        "timing": timing, "trace": str(trace), "report": str(report),
        "ttft_ms": ttft, "itl_ms": itl, "tpot_ms": pick("tpot_ms"),
        "completed_requests": rep.get("completed_requests"),
        "driver_wall_s": round(time.time() - t0, 1),
        "feasible": (float(ttft["p99"]) < SLA["llm_ttft_p99_ms"]
                     and float(itl["p99"]) < SLA["llm_itl_p99_ms"]),
    }
    pp.write_text(json.dumps(rec, indent=1))
    log(f"    -> TTFT p99 {ttft['p99']:.0f} ms, ITL p99 {itl['p99']:.1f} ms, "
        f"feasible={rec['feasible']}")
    return rec


# --------------------------------------------------------------------------
# First-feasible ladder walk + integer bisection
# --------------------------------------------------------------------------

def min_feasible(ladder: list[int], run) -> tuple[int | None, dict[int, dict]]:
    """Walk `ladder` upward until feasible, then bisect integers between the
    last infeasible rung and the first feasible one. run(k) -> point dict
    with a 'feasible' bool. Returns (minimum feasible count or None, points)."""
    points: dict[int, dict] = {}
    prev_infeasible = None
    first_feasible = None
    for k in ladder:
        points[k] = run(k)
        if points[k]["feasible"]:
            first_feasible = k
            break
        prev_infeasible = k
    if first_feasible is None:
        return None, points
    lo = (prev_infeasible if prev_infeasible is not None else 0)
    hi = first_feasible
    while hi - lo > 1:                      # invariant: lo infeasible, hi feasible
        mid = (lo + hi) // 2
        points[mid] = run(mid)
        if points[mid]["feasible"]:
            hi = mid
        else:
            lo = mid
    return hi, points


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--windows", nargs="+", default=None,
                    help="window names from windows.json (default: all)")
    ap.add_argument("--timing", choices=["poly", "aic"], default="aic",
                    help="LLM timing model (headline runs: aic)")
    ap.add_argument("--c-ladder", type=int, nargs="+", default=[1, 2, 4, 8, 16, 32])
    ap.add_argument("--n-ladder", type=int, nargs="+", default=[1, 2, 4, 8, 16])
    ap.add_argument("--tp-ladder", type=int, nargs="+", default=[1, 2, 4],
                    help="LLM tensor-parallel sizes to consider; cost = TP x N GPUs. "
                         "TP is the lever against the per-request prefill floor of "
                         "giant multimodal contexts (TTFT p99 plateaus in N at TP1)")
    ap.add_argument("--out-dir", type=Path, default=HERE / "results" / "grid")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--summary-only", action="store_true")
    args = ap.parse_args()

    registry = json.loads(WINDOWS_FILE.read_text())
    names = args.windows or list(registry)
    unknown = [w for w in names if w not in registry]
    if unknown:
        ap.error(f"unknown windows {unknown}; known: {list(registry)}")
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    failures: list[str] = []
    for window in names:
        win = registry[window]
        if args.summary_only:
            continue
        log(f"=== window {window} (n={win['max_requests']}, "
            f"span {win['span_s']/3600:.2f} h) ===")
        try:
            # Phase V — minimum encoder workers.
            c_star, vpoints = min_feasible(
                sorted(args.c_ladder),
                lambda c: vision_point(out_dir, window, win, c, args.force))
            if c_star is None:
                failures.append(f"{window}: vision infeasible up to "
                                f"C={max(args.c_ladder)}")
                continue
            # Phase L — cheapest (TP, N) on the C* (encoder-shifted) trace.
            # Cost = TP x N GPUs; TP parallelizes a single request's prefill,
            # so it (not N) is the lever when TTFT p99 hits the per-request
            # prefill floor of giant multimodal contexts. A TP rung is only
            # tried while it could still beat the best cost found (min N = 1).
            c_trace = Path(vpoints[c_star]["trace"])
            best = None  # (cost_gpus, tp, n_star, lpoints)
            for tp in args.tp_ladder:
                if best is not None and tp >= best[0]:
                    break
                n_star_tp, lp = min_feasible(
                    sorted(args.n_ladder),
                    lambda n, _tp=tp: llm_point(out_dir, window, c_star, n,
                                                args.timing, c_trace,
                                                args.force, tp=_tp))
                if n_star_tp is not None:
                    cost = tp * n_star_tp
                    if best is None or cost < best[0]:
                        best = (cost, tp, n_star_tp, lp)
            if best is None:
                failures.append(f"{window}: llm infeasible up to "
                                f"N={max(args.n_ladder)} x TP={max(args.tp_ladder)} "
                                f"at C={c_star}")
                continue
            llm_gpus, tp_star, n_star, lpoints = best
            # Cross-check — corner-point independence: at the next C rung the
            # same (TP*, N*) must stay feasible (shift only smooths as C grows).
            c_next = next((c for c in sorted(args.c_ladder) if c > c_star), None)
            cross = None
            if c_next is not None:
                vnext = vision_point(out_dir, window, win, c_next, args.force)
                cross = llm_point(out_dir, window, c_next, n_star, args.timing,
                                  Path(vnext["trace"]), args.force, tp=tp_star)
                if not cross["feasible"]:
                    failures.append(f"{window}: cross-check FAILED — TP{tp_star}/"
                                    f"N{n_star} infeasible at C={c_next}; corner "
                                    f"point is not independent, needs a full grid")
            span_h = win["span_s"] / 3600.0
            results[window] = {
                "c_star": c_star, "tp_star": tp_star, "n_star": n_star,
                "llm_gpus": llm_gpus,
                "span_h": round(span_h, 3),
                "gpu_hours": {"rtx5090": round(c_star * span_h, 2),
                              "h100": round(llm_gpus * span_h, 2)},
                "vision_delay_p99_ms_at_cstar":
                    vpoints[c_star]["encoder_delay_ms"]["p99"],
                "llm_ttft_p99_ms_at_star": lpoints[n_star]["ttft_ms"]["p99"],
                "llm_itl_p99_ms_at_star": lpoints[n_star]["itl_ms"]["p99"],
                "cross_check_ok": bool(cross and cross["feasible"]),
                "vision_points_run": sorted(vpoints),
                "llm_points_run": sorted(lpoints),
            }
            log(f"  {window}: C*={c_star} TP*={tp_star} N*={n_star} "
                f"({results[window]['gpu_hours']['rtx5090']} 5090-h, "
                f"{results[window]['gpu_hours']['h100']} h100-h)")
        except (RuntimeError, KeyError, OSError) as exc:
            failures.append(f"{window}: {exc}")
            log(f"  FAILED: {exc}")

    # ---- summary (always rebuilt from point files on disk) ----
    all_points = [json.loads(f.read_text())
                  for f in sorted(out_dir.glob("*.json"))
                  if f.name != "grid_summary.json"]
    per_window: dict[str, dict] = {}
    for w in {p["window"] for p in all_points}:
        vp = {p["encoder_workers"]: p for p in all_points
              if p["pool"] == "vision" and p["window"] == w}
        lp = {(p["encoder_workers"], p.get("tp", 1), p["llm_workers"]): p
              for p in all_points if p["pool"] == "llm" and p["window"] == w}
        c_feas = sorted(c for c, p in vp.items() if p["feasible"])
        c_star = c_feas[0] if c_feas else None
        feas = [(tp * n, tp, n) for (c, tp, n), p in lp.items()
                if c == c_star and p["feasible"]] if c_star else []
        cost_star, tp_star, n_star = min(feas) if feas else (None, None, None)
        span_h = registry[w]["span_s"] / 3600.0 if w in registry else None
        per_window[w] = {
            "c_star": c_star, "tp_star": tp_star, "n_star": n_star,
            "llm_gpus": cost_star, "span_h": round(span_h, 3),
            "gpu_hours": ({"rtx5090": round(c_star * span_h, 2),
                           "h100": round(cost_star * span_h, 2)}
                          if c_star and cost_star else None),
            "vision_curve": {c: {"p99": vp[c]["encoder_delay_ms"]["p99"],
                                 "feasible": vp[c]["feasible"]} for c in sorted(vp)},
            "llm_curve": {f"C{c}_TP{tp}_N{n}":
                          {"ttft_p99": lp[(c, tp, n)]["ttft_ms"]["p99"],
                           "itl_p99": lp[(c, tp, n)]["itl_ms"]["p99"],
                           "feasible": lp[(c, tp, n)]["feasible"]}
                          for (c, tp, n) in sorted(lp)},
        }
    complete = {w: r for w, r in per_window.items()
                if r["c_star"] is not None and r["llm_gpus"] is not None}
    headline = None
    if complete:
        c_all = max(r["c_star"] for r in complete.values())
        binding = max(complete, key=lambda w: complete[w]["llm_gpus"])
        headline = {
            "static_all_windows": {
                "encoder_workers": c_all,
                "llm_config_binding_window": binding,
                "llm_tp": complete[binding]["tp_star"],
                "llm_workers": complete[binding]["n_star"],
                "llm_gpus": complete[binding]["llm_gpus"],
                "note": "LLM all-windows config = the binding (most expensive) "
                        "window's optimum; verify feasibility on the remaining "
                        "windows before quoting (feasibility is monotone in N "
                        "at fixed TP but not across TP)",
            },
            "overprovision_vs_per_window": {
                w: {"vision_x": round(c_all / r["c_star"], 2),
                    "llm_x": round(complete[binding]["llm_gpus"] / r["llm_gpus"], 2)}
                for w, r in complete.items()},
            "note": "static config sized to pass ALL windows vs each window's "
                    "own optimum — the calm-traffic overprovisioning headline "
                    "is the steady24h row",
        }
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sla": SLA, "timing": args.timing,
        "windows": {w: registry[w] for w in registry},
        "per_window": per_window,
        "headline": headline,
        "failures": failures,
    }
    (out_dir / "grid_summary.json").write_text(json.dumps(summary, indent=1))
    log(f"grid_summary.json rebuilt: {len(per_window)} windows, "
        f"{len(all_points)} points")
    if headline:
        log(f"  all-windows static: {headline['static_all_windows']}")
    if failures:
        log("FAILURES:\n  " + "\n  ".join(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
