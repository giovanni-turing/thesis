#!/usr/bin/env python3
"""Phase 2.3 — saturation-knee load sweeps over the two-pool simulation.

Sweeps arrival speedup s on one trace window and records, per pool, the
load-vs-latency curve and the detected saturation knee:

  * LLM pool   — one `dynamo.replay` run per speedup via `run_replay.sh`,
    using replay's NATIVE `--arrival-speedup-ratio` flag (the Rust core divides
    every trace timestamp by the ratio: lib/mocker/src/replay/mod.rs — verified
    empirically: s=4 compresses duration /4 and scales rps x4). No trace
    rewriting is needed for the LLM axis. The trace replayed is the LLM-pool
    ISOLATION trace (converter `--no-encoder-shift`, raw arrivals) so the knee
    is attributable to the language pool alone.
  * Vision pool — one converter run per speedup
    (`workload/trace_to_two_pool.py --arrival-speedup s --series-out ...`);
    the FIFO encoder pool is simulated inside the converter, so its
    `.stats.json` (encoder delay percentiles, encoder_utilization,
    offered_img_per_s, queue_divergent) is the whole measurement — no replay.
    Vision timing is always the AIC rtx_5090 encoder cost model; points are
    labeled timing="aic".

Windows
  head2k — trace head, --offset 0 --max-requests 2000 (steady stretch).
  burst1 — largest EDA image-burst episode (analysis/trace_eda/
           i_burst_anatomy_stats.json top6_by_peak[0]: baseline start
           2024-10-21 13:09, peak 370.18 img/s @ 19:53, baseline end 21:08),
           padded +/-10 min -> [12:59:00, 21:18:00) UTC. Converted to row
           offset/count by scanning the trace CSV with the converter's own
           normalization (pad 2-digit millis, sort by ts):
           offset=843072, count=64804 (span 29939 s, mean 2.165 req/s,
           116.173 img/s, text-only fraction 0.325).
  custom — pass --offset/--max-requests yourself.

Knee definition (per (pool, window, timing) curve)
  knee = largest swept speedup whose latency metrics stay under the SLA:
    vision: encoder_delay_ms.p99 < --vision-p99-threshold-ms (default 1000)
            AND not queue_divergent;
    llm:    ttft.p99 < --llm-ttft-p99-threshold-ms (default 1000)
            AND itl.p99 < --llm-itl-p99-threshold-ms (default 100).
  These defaults ARE the thesis SLA (progress/phase3-baselines.md): tail-based
  evaluation targets, 2x the SLA Planner's native window-mean targets
  (ttft_ms=500, itl_ms=50), which the reactive baseline runs unmodified.

Idempotent: a (pool, window, timing, speedup) point whose result JSON already
exists under --out-dir is skipped (--force reruns). Every invocation rebuilds
summary.json from all point files present.

Run with any python3 (stdlib only); sub-work runs in the aiconfigurator venv:
  python3 simulation/sweep_load.py --pool llm --window head2k --timing poly
  python3 simulation/sweep_load.py --pool vision --window burst1 --speedups 1 2 4
Figure: simulation/sweep_fig.py (eda venv; needs matplotlib) reads summary.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
AIC_DIR = Path("/home/gio/tese/ai-dynamo/aiconfigurator")
VENV_PY = AIC_DIR / ".venv/bin/python"
CONVERTER = Path("/home/gio/tese/workload/trace_to_two_pool.py")
RUN_REPLAY = HERE / "run_replay.sh"

# Window registry: name -> (offset, max_requests, provenance note).
WINDOWS: dict[str, tuple[int, int, str]] = {
    "head2k": (0, 2000, "trace head (steady): 2024-10-15 ~00:00, ~2.77 req/s, ~8.0 img/s"),
    "burst1": (843072, 64804,
               "largest burst episode +/-10min pad: 2024-10-21 12:59:00..21:18:00 UTC, "
               "peak 370.18 img/s @ 19:53; mean 2.165 req/s, 116.173 img/s"),
}

CONVERTER_RETRIES = 3          # the converter file may be edited concurrently
CONVERTER_RETRY_SLEEP_S = 30
CONVERTER_TIMEOUT_S = 2400
REPLAY_TIMEOUT_S = 3600


def log(msg: str) -> None:
    print(f"[sweep {datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fmt_s(speedup: float) -> str:
    return f"{speedup:g}"


def point_path(out_dir: Path, pool: str, window: str, timing: str, speedup: float) -> Path:
    return out_dir / f"{pool}_{window}_{timing}_s{fmt_s(speedup)}.json"


def run_logged(cmd: list[str], log_path: Path, cwd: Path | None, timeout: int) -> int:
    """Run cmd, teeing stdout+stderr to log_path; return exit code."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as lf:
        lf.write(f"# cmd: {' '.join(map(str, cmd))}\n# cwd: {cwd}\n")
        lf.flush()
        try:
            proc = subprocess.run(cmd, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT,
                                  timeout=timeout)
            return proc.returncode
        except subprocess.TimeoutExpired:
            lf.write(f"\n# TIMEOUT after {timeout}s\n")
            return -9


def run_converter(args_list: list[str], log_path: Path) -> int:
    """Converter run with light retry (another agent may be editing the file)."""
    cmd = [str(VENV_PY), str(CONVERTER)] + args_list
    for attempt in range(1, CONVERTER_RETRIES + 1):
        rc = run_logged(cmd, log_path, cwd=AIC_DIR, timeout=CONVERTER_TIMEOUT_S)
        if rc == 0:
            return 0
        log(f"  converter exit {rc} (attempt {attempt}/{CONVERTER_RETRIES}) — see {log_path}")
        if attempt < CONVERTER_RETRIES:
            time.sleep(CONVERTER_RETRY_SLEEP_S)
    return rc


# --------------------------------------------------------------------------
# LLM pool
# --------------------------------------------------------------------------

def ensure_llm_base_trace(out_dir: Path, window: str, offset: int, max_requests: int,
                          encoder_workers: int) -> tuple[Path, dict]:
    """LLM-isolation mooncake trace for the window at s=1 (speedup is applied
    natively by dynamo.replay, so ONE base trace serves the whole sweep)."""
    trace = out_dir / "traces" / f"llm_{window}.jsonl"
    stats_path = Path(f"{trace}.stats.json")
    if not (trace.exists() and stats_path.exists()):
        trace.parent.mkdir(parents=True, exist_ok=True)
        log(f"generating LLM base trace for {window} (offset={offset}, n={max_requests})")
        rc = run_converter(
            ["--out", str(trace), "--offset", str(offset), "--max-requests", str(max_requests),
             "--encoder-workers", str(encoder_workers), "--no-encoder-shift"],
            out_dir / "logs" / f"convert_llm_{window}.log")
        if rc != 0:
            raise RuntimeError(f"converter failed (exit {rc}) building {trace}")
    stats = json.loads(stats_path.read_text())
    return trace, stats


def trace_token_totals(trace: Path) -> tuple[int, int]:
    tin = tout = 0
    with open(trace) as f:
        for line in f:
            r = json.loads(line)
            tin += r["input_length"]
            tout += r["output_length"]
    return tin, tout


def run_llm_point(out_dir: Path, window: str, timing: str, speedup: float,
                  llm_workers: int, base_trace: Path, base_stats: dict) -> dict:
    report = out_dir / "reports" / f"llm_{window}_{timing}_s{fmt_s(speedup)}.report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["bash", str(RUN_REPLAY), str(base_trace), timing, str(report),
           str(llm_workers), "--arrival-speedup-ratio", str(speedup)]
    t0 = time.time()
    rc = run_logged(cmd, out_dir / "logs" / f"llm_{window}_{timing}_s{fmt_s(speedup)}.log",
                    cwd=HERE, timeout=REPLAY_TIMEOUT_S)
    wall = time.time() - t0
    if rc != 0 or not report.exists():
        raise RuntimeError(f"replay failed (exit {rc}) for llm/{window}/{timing}/s{fmt_s(speedup)}")

    rep = json.loads(report.read_text())
    horizon_s = float(base_stats["sim_horizon_s"])
    base_rps = float(base_stats["mean_requests_per_s"])
    tin, tout = trace_token_totals(base_trace)
    pick = lambda pfx: {k: rep.get(f"{k}_{pfx}") for k in
                        ("mean", "median", "p90", "p99", "max")}
    return {
        "pool": "llm", "window": window, "timing": timing, "speedup": speedup,
        "llm_workers": llm_workers,
        "mechanism": "dynamo.replay --arrival-speedup-ratio (native; timestamps /= ratio)",
        "trace": str(base_trace),
        "report": str(report),
        "base": {"req_per_s": base_rps, "horizon_s": horizon_s,
                 "requests": base_stats["requests"],
                 "input_tok_per_s": round(tin / horizon_s, 3),
                 "output_tok_per_s": round(tout / horizon_s, 3)},
        "offered": {"req_per_s": round(base_rps * speedup, 4),
                    "input_tok_per_s": round(tin / horizon_s * speedup, 2),
                    "output_tok_per_s": round(tout / horizon_s * speedup, 2),
                    "total_tok_per_s": round((tin + tout) / horizon_s * speedup, 2)},
        "measured": {"request_throughput_rps": rep["request_throughput_rps"],
                     "output_throughput_tok_s": rep["output_throughput_tok_s"],
                     "total_throughput_tok_s": rep["total_throughput_tok_s"],
                     "duration_ms": rep["duration_ms"],
                     "completed_requests": rep["completed_requests"],
                     "sim_wall_time_ms": rep.get("wall_time_ms"),
                     "driver_wall_s": round(wall, 1)},
        "ttft_ms": pick("ttft_ms"),
        "tpot_ms": pick("tpot_ms"),
        "itl_ms": pick("itl_ms"),
        "e2e_ms": pick("e2e_latency_ms"),
        "exit_code": rc,
    }


# --------------------------------------------------------------------------
# Vision pool
# --------------------------------------------------------------------------

def run_vision_point(out_dir: Path, window: str, speedup: float, offset: int,
                     max_requests: int, encoder_workers: int) -> dict:
    tag = f"vision_{window}_s{fmt_s(speedup)}"
    trace = out_dir / "traces" / f"{tag}.jsonl"
    series = out_dir / "series" / f"{tag}.series.json"
    trace.parent.mkdir(parents=True, exist_ok=True)
    series.parent.mkdir(parents=True, exist_ok=True)
    rc = run_converter(
        ["--out", str(trace), "--offset", str(offset), "--max-requests", str(max_requests),
         "--encoder-workers", str(encoder_workers),
         "--arrival-speedup", str(speedup), "--series-out", str(series)],
        out_dir / "logs" / f"{tag}.log")
    stats_path = Path(f"{trace}.stats.json")
    if rc != 0 or not stats_path.exists():
        raise RuntimeError(f"converter failed (exit {rc}) for vision/{window}/s{fmt_s(speedup)}")

    st = json.loads(stats_path.read_text())
    return {
        "pool": "vision", "window": window, "timing": "aic", "speedup": speedup,
        "encoder_workers": st["encoder_workers"],
        "image_px": st["image_px"],
        "encoder_batch_images": st.get("encoder_batch_images"),
        "mechanism": "converter --arrival-speedup (inter-arrival gaps /= s before FIFO sim)",
        "trace": str(trace), "stats": str(stats_path), "series": str(series),
        "base": {"img_per_s": round(st["offered_img_per_s"] / speedup, 3),
                 "req_per_s": round(st["mean_requests_per_s"] / speedup, 3)},
        "offered": {"img_per_s": st["offered_img_per_s"],
                    "req_per_s": st["mean_requests_per_s"]},
        "requests": st["requests"],
        "total_images": st["total_images"],
        "horizon_s": st["sim_horizon_s"],
        "vision_sim_end_s": st.get("vision_sim_end_s"),
        "encoder_delay_ms": st["encoder_delay_ms"],
        "encoder_service_ms": st["encoder_service_ms"],
        "encoder_batch_service_ms": st.get("encoder_batch_service_ms"),
        "handoff_ms": st.get("handoff_ms"),
        "encoder_utilization": st.get("encoder_utilization"),
        "queue_divergent": st.get("queue_divergent"),
        "batches": st.get("batches"),
        "exit_code": rc,
    }


# --------------------------------------------------------------------------
# Knees + summary
# --------------------------------------------------------------------------

def knee_metric(point: dict) -> tuple[float, bool]:
    """(primary metric, secondary_criteria_ok).

    vision: (delay p99, not queue-divergent); llm: (TTFT p99, ITL p99 under
    its own SLA bound — stored on the point dict by detect_knee)."""
    if point["pool"] == "vision":
        return float(point["encoder_delay_ms"]["p99"]), not bool(point.get("queue_divergent"))
    itl_ok = bool(point.get("_itl_ok", True))
    return float(point["ttft_ms"]["p99"]), itl_ok


def detect_knee(points: list[dict], threshold: float, itl_threshold: float | None = None) -> dict:
    pts = sorted(points, key=lambda p: p["speedup"])
    if itl_threshold is not None:
        for p in pts:
            if p["pool"] == "llm":
                p["_itl_ok"] = float(p["itl_ms"]["p99"]) < itl_threshold
    under = [p for p in pts if knee_metric(p)[0] < threshold and knee_metric(p)[1]]
    over = [p for p in pts if not (knee_metric(p)[0] < threshold and knee_metric(p)[1])]
    knee = max((p["speedup"] for p in under), default=None)
    first_over = min((p["speedup"] for p in over), default=None)
    # monotonicity of the knee metric with speedup (5% rel + 10 ms abs tolerance)
    violations = []
    for a, b in zip(pts, pts[1:]):
        va, vb = knee_metric(a)[0], knee_metric(b)[0]
        if vb < va - max(0.05 * va, 10.0):
            violations.append({"from_s": a["speedup"], "to_s": b["speedup"],
                               "metric_from": va, "metric_to": vb})
    return {
        "speedups": [p["speedup"] for p in pts],
        "metric": [round(knee_metric(p)[0], 3) for p in pts],
        "offered": [p["offered"]["img_per_s" if p["pool"] == "vision" else "req_per_s"]
                    for p in pts],
        "queue_divergent": [bool(p.get("queue_divergent")) for p in pts]
        if pts and pts[0]["pool"] == "vision" else None,
        "threshold": threshold,
        "knee_speedup": knee,
        "first_over_speedup": first_over,
        "saturated_in_range": first_over is not None,
        "monotonic_ok": not violations,
        "monotonicity_violations": violations,
    }


def sanity_offered_scaling(points: list[dict]) -> list[dict]:
    """offered load must scale ~ s x base (2% tolerance), per curve."""
    issues = []
    pts = sorted(points, key=lambda p: p["speedup"])
    if not pts:
        return issues
    key = "img_per_s" if pts[0]["pool"] == "vision" else "req_per_s"
    base = pts[0]["offered"][key] / pts[0]["speedup"]
    for p in pts:
        expect = base * p["speedup"]
        got = p["offered"][key]
        if abs(got - expect) > 0.02 * expect:
            issues.append({"point": f"{p['pool']}/{p['window']}/{p['timing']}/s{fmt_s(p['speedup'])}",
                           "expected": round(expect, 3), "got": got})
    return issues


def rebuild_summary(out_dir: Path, vision_thr: float, llm_thr: float, llm_itl_thr: float) -> dict:
    points = []
    for f in sorted(out_dir.glob("*_s*.json")):
        if f.name == "summary.json":
            continue
        try:
            points.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            log(f"  ! unparseable point file skipped: {f}")

    curves: dict[str, dict] = {}
    sanity_scaling: list[dict] = []
    groups: dict[tuple, list[dict]] = {}
    for p in points:
        groups.setdefault((p["pool"], p["window"], p["timing"]), []).append(p)
    for (pool, window, timing), pts in sorted(groups.items()):
        thr = vision_thr if pool == "vision" else llm_thr
        itl = None if pool == "vision" else llm_itl_thr
        curves[f"{pool}|{window}|{timing}"] = detect_knee(pts, thr, itl)
        sanity_scaling += sanity_offered_scaling(pts)

    # Decoupling: compare vision vs llm knees on the same window.
    decoupling = {}
    for window in {p["window"] for p in points}:
        v = curves.get(f"vision|{window}|aic")
        for timing in ("poly", "aic"):
            l = curves.get(f"llm|{window}|{timing}")
            if v and l:
                decoupling[f"{window}|llm-{timing}"] = {
                    "vision_knee_speedup": v["knee_speedup"],
                    "llm_knee_speedup": l["knee_speedup"],
                    "knees_differ": v["knee_speedup"] != l["knee_speedup"],
                    "llm_over_vision_knee_ratio":
                        round(l["knee_speedup"] / v["knee_speedup"], 3)
                        if v["knee_speedup"] and l["knee_speedup"] else None,
                }

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "thresholds": {
            "vision_encoder_delay_p99_ms": vision_thr,
            "llm_ttft_p99_ms": llm_thr,
            "llm_itl_p99_ms": llm_itl_thr,
            "note": "thesis SLA (progress/phase3-baselines.md): tail-based evaluation "
                    "targets; the SLA Planner baseline runs its native window-mean "
                    "targets (ttft_ms=500, itl_ms=50) as policy config",
        },
        "windows": {w: {"offset": o, "max_requests": n, "note": note}
                    for w, (o, n, note) in WINDOWS.items()},
        "mechanisms": {
            "llm": "native dynamo.replay --arrival-speedup-ratio on the s=1 isolation trace",
            "vision": "converter --arrival-speedup per point (FIFO encoder sim in converter)",
        },
        "points": points,
        "curves": curves,
        "decoupling": decoupling,
        "sanity": {
            "offered_scaling_issues": sanity_scaling,
            "nonmonotonic_curves": [k for k, c in curves.items() if not c["monotonic_ok"]],
            "all_exit_codes_zero": all(p.get("exit_code") == 0 for p in points),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    return summary


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", choices=["vision", "llm", "both"], default="both")
    ap.add_argument("--window", choices=["head2k", "burst1", "custom"], default="head2k")
    ap.add_argument("--timing", choices=["poly", "aic"], default="poly",
                    help="LLM-pool timing model; vision points are always AIC-costed")
    ap.add_argument("--speedups", type=float, nargs="+", default=[1, 2, 4, 8, 16, 32])
    ap.add_argument("--llm-workers", type=int, default=2)
    ap.add_argument("--encoder-workers", type=int, default=2)
    ap.add_argument("--out-dir", type=Path, default=HERE / "results" / "sweeps")
    ap.add_argument("--offset", type=int, default=None, help="custom window row offset")
    ap.add_argument("--max-requests", type=int, default=None, help="custom window row count")
    ap.add_argument("--vision-p99-threshold-ms", type=float, default=1000.0,
                    help="vision SLA: encoder_delay p99 bound (thesis SLA)")
    ap.add_argument("--llm-ttft-p99-threshold-ms", type=float, default=1000.0,
                    help="llm SLA: TTFT p99 bound (thesis SLA)")
    ap.add_argument("--llm-itl-p99-threshold-ms", type=float, default=100.0,
                    help="llm SLA: ITL p99 bound (thesis SLA; knee requires both)")
    ap.add_argument("--force", action="store_true", help="rerun existing points")
    ap.add_argument("--summary-only", action="store_true",
                    help="skip runs; just rebuild summary.json from existing points")
    args = ap.parse_args()

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.window == "custom":
        if args.offset is None or args.max_requests is None:
            ap.error("--window custom requires --offset and --max-requests")
        offset, max_requests = args.offset, args.max_requests
        WINDOWS["custom"] = (offset, max_requests, "user-provided")
    else:
        offset, max_requests, _ = WINDOWS[args.window]

    failures = []
    if not args.summary_only:
        pools = ["llm", "vision"] if args.pool == "both" else [args.pool]
        for pool in pools:
            timing = args.timing if pool == "llm" else "aic"
            base_trace = base_stats = None
            for s in sorted(args.speedups):
                pp = point_path(out_dir, pool, args.window, timing, s)
                if pp.exists() and not args.force:
                    log(f"skip (exists): {pp.name}")
                    continue
                log(f"run: {pool}/{args.window}/{timing}/s{fmt_s(s)}")
                try:
                    if pool == "llm":
                        if base_trace is None:
                            base_trace, base_stats = ensure_llm_base_trace(
                                out_dir, args.window, offset, max_requests,
                                args.encoder_workers)
                        rec = run_llm_point(out_dir, args.window, timing, s,
                                            args.llm_workers, base_trace, base_stats)
                    else:
                        rec = run_vision_point(out_dir, args.window, s, offset,
                                               max_requests, args.encoder_workers)
                    pp.write_text(json.dumps(rec, indent=1))
                    m, ok = knee_metric(rec)
                    log(f"  -> {pp.name}: metric={m:.1f} ms"
                        f"{'' if ok else '  !! queue divergent'}")
                except (RuntimeError, KeyError, OSError) as exc:
                    failures.append(f"{pool}/{args.window}/{timing}/s{fmt_s(s)}: {exc}")
                    log(f"  FAILED: {exc}")

    summary = rebuild_summary(out_dir, args.vision_p99_threshold_ms,
                              args.llm_ttft_p99_threshold_ms,
                              args.llm_itl_p99_threshold_ms)
    log(f"summary.json rebuilt: {len(summary['points'])} points, "
        f"{len(summary['curves'])} curves")
    for name, c in summary["curves"].items():
        log(f"  {name}: knee=s{c['knee_speedup']} first_over=s{c['first_over_speedup']} "
            f"metric={c['metric']}")
    if failures:
        log("FAILURES:\n  " + "\n  ".join(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
