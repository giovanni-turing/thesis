#!/usr/bin/env python3
"""Analyze the redesigned closed-loop predictor benchmark.

For each (predictor, window): pull the full TTFT+ITL percentile distribution,
decode_worker_seconds, gpu_hours, the scale-action count + worker timeline from
the run log, and a PASS/FAIL against the config SLA (ttft<=200ms, itl<=20ms at p99).
Then report whether the predictors diverge (schedule / worker-seconds / ITL).
"""
import json
import re
import sys
from pathlib import Path

BASE = Path("/home/gio/tese/.claude/worktrees/agent-a8d707cf6d783f2b7/simulation/results/predictor_closedloop_v2")
PREDS = ["arima", "kalman", "prophet"]
WINDOWS = ["steady24h", "burst4"]
SLA_TTFT = 200.0
SLA_ITL = 20.0

# report.json key aliases (p50 == median_*)
def pct(d, metric, p):
    key = f"median_{metric}" if p == "p50" else f"{p}_{metric}"
    return d.get(key)

SCALE_RE = re.compile(r"Planner scaling: (\d+) -> (\d+) workers at t=([\d.]+)s \((\w+)\)")

def parse_schedule(logpath):
    """Return (events list of (t,from,to,dir), scale_action_count, worker_seconds_from_timeline)."""
    events = []
    if not logpath.exists():
        return events, 0
    text = logpath.read_text(errors="ignore")
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)  # strip ANSI color codes
    for m in SCALE_RE.finditer(text):
        frm, to, t, direction = int(m.group(1)), int(m.group(2)), float(m.group(3)), m.group(4)
        events.append((t, frm, to, direction))
    return events, len(events)

def worker_seconds_from_timeline(events, horizon_s, start_workers):
    """Integrate worker-count over time from the scale-event timeline.
    This is an independent cross-check of decode_worker_seconds/gpu accounting."""
    if not events:
        return start_workers * horizon_s
    ws = 0.0
    cur_t = 0.0
    cur_n = start_workers
    for (t, frm, to, d) in events:
        ws += cur_n * (t - cur_t)
        cur_t = t
        cur_n = to
    ws += cur_n * (horizon_s - cur_t)
    return ws

HORIZON = {"steady24h": 86396.723, "burst4": 11339.204}

def load_report(win, pred):
    rp = BASE / win / f"{pred}.report.json"
    if not rp.exists():
        return None
    return json.loads(rp.read_text())

def fmt(v):
    return f"{v:.2f}" if isinstance(v, (int, float)) else str(v)

def main():
    out = []
    summary = {}
    for win in WINDOWS:
        out.append(f"\n{'='*88}\nWINDOW: {win}   (SLA: p99 TTFT<={SLA_TTFT}ms, p99 ITL<={SLA_ITL}ms)\n{'='*88}")
        rows = {}
        for pred in PREDS:
            d = load_report(win, pred)
            if d is None:
                out.append(f"  [{pred}] NO REPORT YET")
                continue
            # Prefer the compact committed planner log; fall back to raw .log if present.
            logp = BASE / win / f"{pred}.planner.log"
            if not logp.exists():
                logp = BASE / win / f"{pred}.log"
            events, n_scale = parse_schedule(logp)
            ws_tl = worker_seconds_from_timeline(events, HORIZON[win], start_workers=2)
            p99_ttft = pct(d, "ttft_ms", "p99")
            p99_itl = pct(d, "itl_ms", "p99")
            passfail = "PASS" if (p99_ttft is not None and p99_ttft <= SLA_TTFT and
                                  p99_itl is not None and p99_itl <= SLA_ITL) else "FAIL"
            rows[pred] = {
                "report": d, "events": events, "n_scale": n_scale,
                "ws_timeline": ws_tl, "passfail": passfail,
                "p99_ttft": p99_ttft, "p99_itl": p99_itl,
            }
        # Percentile tables
        for metric_name, metric in [("TTFT (ms)", "ttft_ms"), ("ITL (ms)", "itl_ms")]:
            out.append(f"\n  --- {metric_name} percentiles ---")
            out.append(f"  {'pred':<9} {'p50':>12} {'p75':>12} {'p90':>12} {'p95':>12} {'p99':>12}")
            for pred in PREDS:
                if pred not in rows: continue
                d = rows[pred]["report"]
                vals = [pct(d, metric, p) for p in ["p50","p75","p90","p95","p99"]]
                out.append(f"  {pred:<9} " + " ".join(f"{(v if v is not None else float('nan')):>12.4f}" for v in vals))
        # Mean latencies (sensitive to every request; percentiles can tie while means diverge)
        out.append(f"\n  --- mean latencies (diverge where percentiles tie) ---")
        out.append(f"  {'pred':<9} {'mean_ttft':>14} {'mean_itl':>14} {'mean_e2e':>14}")
        for pred in PREDS:
            if pred not in rows: continue
            d = rows[pred]["report"]
            out.append(f"  {pred:<9} {d.get('mean_ttft_ms',float('nan')):>14.6f} {d.get('mean_itl_ms',float('nan')):>14.6f} {d.get('mean_e2e_latency_ms',float('nan')):>14.4f}")
        # Resource + schedule
        out.append(f"\n  --- resources & schedule ---")
        out.append(f"  {'pred':<9} {'decode_wsec':>14} {'gpu_hours':>11} {'scale_acts':>11} {'ws_timeline':>13} {'PASS/FAIL':>10}")
        for pred in PREDS:
            if pred not in rows: continue
            d = rows[pred]["report"]
            dws = d.get("decode_worker_seconds")
            gph = d.get("gpu_hours")
            out.append(f"  {pred:<9} {fmt(dws):>14} {fmt(gph):>11} {rows[pred]['n_scale']:>11} {rows[pred]['ws_timeline']:>13.1f} {rows[pred]['passfail']:>10}")
        # Worker timelines (compact)
        out.append(f"\n  --- scale-decision worker timelines (t_s: n->n) ---")
        for pred in PREDS:
            if pred not in rows: continue
            ev = rows[pred]["events"]
            chain = " ".join(f"{t:.0f}:{frm}->{to}" for (t,frm,to,dd) in ev) if ev else "(no scale events)"
            out.append(f"  {pred:<9} n={len(ev):<3} {chain[:400]}")
        # Divergence check
        out.append(f"\n  --- DIVERGENCE across predictors ---")
        present = [p for p in PREDS if p in rows]
        if len(present) >= 2:
            def spread(vals):
                vals = [v for v in vals if v is not None]
                if not vals: return None
                return max(vals) - min(vals)
            dws_vals = {p: rows[p]["report"].get("decode_worker_seconds") for p in present}
            itl99 = {p: rows[p]["p99_itl"] for p in present}
            ttft99 = {p: rows[p]["p99_ttft"] for p in present}
            nsc = {p: rows[p]["n_scale"] for p in present}
            out.append(f"  decode_worker_seconds: " + ", ".join(f"{p}={dws_vals[p]}" for p in present))
            dsp = spread(list(dws_vals.values()))
            out.append(f"    -> spread = {dsp:.3f} s" if dsp is not None else "    -> spread n/a")
            out.append(f"  scale_action_count:    " + ", ".join(f"{p}={nsc[p]}" for p in present))
            out.append(f"  p99_ITL_ms:            " + ", ".join(f"{p}={itl99[p]}" for p in present))
            isp = spread(list(itl99.values()))
            out.append(f"    -> spread = {isp:.4f} ms" if isp is not None else "    -> spread n/a")
            out.append(f"  p99_TTFT_ms:           " + ", ".join(f"{p}={ttft99[p]}" for p in present))
            tsp = spread(list(ttft99.values()))
            out.append(f"    -> spread = {tsp:.4f} ms" if tsp is not None else "    -> spread n/a")
            # mean-ttft/itl spread (the sensitive means)
            mt = {p: rows[p]["report"].get("mean_ttft_ms") for p in present}
            mi = {p: rows[p]["report"].get("mean_itl_ms") for p in present}
            out.append(f"  mean_TTFT_ms:          " + ", ".join(f"{p}={mt[p]:.6f}" for p in present))
            out.append(f"    -> spread = {spread(list(mt.values())):.6f} ms")
            out.append(f"  mean_ITL_ms:           " + ", ".join(f"{p}={mi[p]:.6f}" for p in present))
            out.append(f"    -> spread = {spread(list(mi.values())):.6f} ms")
            # identical schedule?
            sched_sigs = {p: tuple(rows[p]["events"]) for p in present}
            uniq = len(set(sched_sigs.values()))
            out.append(f"  distinct scale schedules among {len(present)} predictors: {uniq}")
            # per-pair schedule edit distance (how many scale actions differ)
            import difflib
            for i in range(len(present)):
                for j in range(i+1, len(present)):
                    pa, pb = present[i], present[j]
                    sa = [f"{t:.0f}:{frm}->{to}" for (t,frm,to,d) in rows[pa]["events"]]
                    sb = [f"{t:.0f}:{frm}->{to}" for (t,frm,to,d) in rows[pb]["events"]]
                    sm = difflib.SequenceMatcher(None, sa, sb)
                    ratio = sm.ratio()
                    out.append(f"    schedule similarity {pa} vs {pb}: {ratio:.4f} (|{pa}|={len(sa)}, |{pb}|={len(sb)})")
            summary[win] = {
                "decode_worker_seconds": dws_vals,
                "decode_worker_seconds_spread_s": dsp,
                "p99_itl_ms": itl99, "p99_itl_spread_ms": isp,
                "p99_ttft_ms": ttft99, "p99_ttft_spread_ms": tsp,
                "mean_ttft_ms": mt, "mean_ttft_spread_ms": spread(list(mt.values())),
                "mean_itl_ms": mi, "mean_itl_spread_ms": spread(list(mi.values())),
                "scale_action_count": nsc,
                "distinct_schedules": uniq,
                "passfail": {p: rows[p]["passfail"] for p in present},
            }
    print("\n".join(out))
    (BASE / "analysis_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {BASE/'analysis_summary.json'}")

if __name__ == "__main__":
    main()
