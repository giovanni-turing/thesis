#!/usr/bin/env python3
"""G7 - cold-start accounting. CORRECTED after adversarial audit (2026-07-19).

=====================================================================
HEADLINE, AND IT IS THE OPPOSITE OF THE ORIGINAL G7 CLAIM:
  The LANGUAGE-pool GPU-hours reported throughout this thesis ALREADY
  BILL FROM INSTANCE ORDER, not from readiness. NO cold-start surcharge
  may be added to them - doing so double-counts.
=====================================================================

Source of truth (verified by reading the mocker):
  lib/mocker/src/replay/collector.rs:44-52  - `decode_worker_seconds` is the
    time-integral of the PROVISIONED worker count, "active + starting-up +
    draining", and `gpu_hours = worker_seconds x gpus_per_worker / 3600`.
  lib/mocker/src/replay/offline/agg.rs:823-836 - `advance_now_ms` accrues
    `engine.worker_count()` (= provisioned, incl. pending startup) each clock
    advance.
  defense/anim/build/gen_a11_runs.py:75 - the a11 driver reads exactly that
    field (`d["gpu_hours"]`), NOT the planner's active-only diagnostics
    counter (`replay_adapter.py:_record_diagnostics`, which uses
    `active_decode_count` and is a different, unused number).
So the startup ramp is inside every reported language GPU-hour already.

The ENCODER pool is structurally the OPPOSITE, and there the dual accounting
is legitimate:
  simulation/forecast_schedule.py:146-149 - the emitted schedule is the
    AVAILABLE (ready-to-serve) capacity: `avail[i] = min(desired[i-lead:i+1])`,
    i.e. an up-step decided at t only appears at t+lead.
  workload/trace_to_two_pool.py:522-529 - `provisioned_worker_seconds`
    integrates that READY schedule.
  => the encoder genuinely bills from readiness, so warm-up is unbilled there
     and `warmup_ws` in a2_cost_accounting.csv is a real, non-double-counted
     surcharge. This driver re-derives it from the shipped schedules.

What this driver now emits:
  LANGUAGE  - (1) the evidence that billing is already from order;
              (2) a purely DESCRIPTIVE churn-intensity statistic, using each
                  run's own STARTUP_TIME (= its lead, gen_a11_runs.py:61 -
                  the old flat 60 s was wrong for 36 of 52 runs), stated as a
                  share of an ALREADY-PAID bill, never as an extra cost;
              (3) ordered-replica counts as BOUNDS, since the log's target
                  series and its (to-from) deltas bracket the truth.
  ENCODER   - the A2 dual accounting, independently recomputed from the
              shipped .sched.json files (exact, 40/40), with SLA feasibility
              of the reactive comparator attached to every ratio.

Reads : defense/anim/data/a11_data.json, defense/anim/data/a11_runs/*.log,
        defense/anim/data/a2_data.json, defense/anim/data/a2_runs/*.sched.json,
        defense/anim/data/a2_cost_accounting.csv
Writes: defense/anim/data/g7_coldstart/{coldstart.json,coldstart.csv,REPORT.md}
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path("/home/gio/tese")
A11 = ROOT / "defense/anim/data/a11_data.json"
A11RUNS = ROOT / "defense/anim/data/a11_runs"
A2 = ROOT / "defense/anim/data/a2_data.json"
A2RUNS = ROOT / "defense/anim/data/a2_runs"
A2CSV = ROOT / "defense/anim/data/a2_cost_accounting.csv"
OUT = ROOT / "defense/anim/data/g7_coldstart"
OUT.mkdir(parents=True, exist_ok=True)

GPUS_PER_REPLICA = 2          # language: TP2
SLA_MS = 1000.0               # language + encoder p99 bound
ENC_SLA_MS = 1000.0
LANG_TOL = 0.02               # order-integral vs reported gpu_h
STEP_RE = re.compile(r"\s*t=([\d.]+)s \[\w+\]: (\d+) -> (\d+) workers")


def startup_s(run_key: str) -> float:
    """Each run's actual STARTUP_TIME. gen_a11_runs.py:61 sets
    STARTUP_TIME = str(lead), and the run key carries the lead as _L<lead>."""
    return float(run_key.rsplit("_L", 1)[1])


def integrate(sched: list, span_s: float) -> float:
    """Replica-seconds under the staircase. The staircase timestamps are
    planner DECISION instants (replay_adapter.py:_compute_scale_decision logs
    `now_s`), so this is the FROM-ORDER integral, not a from-readiness one."""
    rs = 0.0
    for i, (t, n) in enumerate(sched):
        t_end = sched[i + 1][0] if i + 1 < len(sched) else span_s
        rs += n * max(0.0, min(t_end, span_s) - min(t, span_s))
    return rs


def integrate_lagged(sched: list, span_s: float, lag_s: float) -> float:
    """Counterfactual: what the bill WOULD be if only READY replicas were
    charged - every up-step delayed by lag_s, down-steps effective at once.
    If the thesis numbers were from-readiness, THIS would reproduce them."""
    pts = []
    for i, (t, n) in enumerate(sched):
        prev = sched[i - 1][1] if i else n
        pts.append([t + lag_s if n > prev else t, n])
    pts.sort(key=lambda p: p[0])
    # keep the last level set at each instant
    merged: list[list[float]] = []
    for t, n in pts:
        if merged and merged[-1][0] == t:
            merged[-1][1] = n
        else:
            merged.append([t, n])
    if merged[0][0] > 0.0:
        merged.insert(0, [0.0, sched[0][1]])
    return integrate(merged, span_s)


def ordered_bounds(tag: str, sched: list) -> tuple[int, int, int]:
    """Replicas ordered by up-steps. The log gives `from -> to`, where `from`
    is the ACTIVE count (replay_adapter.py: current_d = active_decode_count)
    and `to` is the TARGET. The engine actually adds
    `target - (active + pending_startup)` (agg.rs apply_target_count), so:
      lower bound = target-to-target deltas (what extract_a11 kept)
      upper bound = per-event (to - from)
    The truth lies between and is NOT observable from these logs.
    Returns (upsteps, lower, upper)."""
    lower = sum(max(0, sched[i][1] - sched[i - 1][1]) for i in range(1, len(sched)))
    upsteps = sum(1 for i in range(1, len(sched)) if sched[i][1] > sched[i - 1][1])
    upper = 0
    log = A11RUNS / f"{tag}.log"
    if log.exists():
        for line in open(log):
            m = STEP_RE.match(line)
            if m and int(m.group(3)) > int(m.group(2)):
                upper += int(m.group(3)) - int(m.group(2))
    return upsteps, lower, max(upper, lower)


# --------------------------------------------------------------------------
# LANGUAGE POOL - evidence + descriptive churn only
# --------------------------------------------------------------------------
def language() -> tuple[list, dict]:
    data = json.load(open(A11))
    rows, fails = [], []
    for wk, w in data["windows"].items():
        span = float(w["meta"]["span_s"])
        for run_key, r in w["runs"].items():
            sched = r.get("sched")
            if not sched:
                continue
            tag = f"{wk}_{run_key}"
            su = startup_s(run_key)
            order_rs = integrate(sched, span)
            order_gpu_h = order_rs * GPUS_PER_REPLICA / 3600.0
            lag_gpu_h = integrate_lagged(sched, span, su) * GPUS_PER_REPLICA / 3600.0
            reported = r["stats"].get("gpu_h")
            rel_order = rel_lag = None
            if reported:
                rel_order = abs(order_gpu_h - reported) / reported
                rel_lag = (lag_gpu_h - reported) / reported
                if rel_order > LANG_TOL:
                    fails.append(f"{tag}: order integral {order_gpu_h:.2f} vs "
                                 f"reported {reported:.2f} ({rel_order:.1%})")
            upsteps, lo, hi = ordered_bounds(tag, sched)
            # churn intensity: startup-seconds ordered, as a share of the bill.
            # This is a SHARE OF AN ALREADY-PAID BILL, not an extra charge.
            churn_rs_lo, churn_rs_hi = lo * su, hi * su
            rows.append({
                "window": wk, "run": run_key,
                "policy": "reactive" if "reactive" in run_key else "forecast",
                "lead_s": su, "startup_s": su, "span_s": span,
                "reported_gpu_h": reported,
                "order_integral_gpu_h": round(order_gpu_h, 3),
                "order_integral_rel_err": (round(rel_order, 4) if rel_order is not None else None),
                "readiness_lagged_gpu_h": round(lag_gpu_h, 3),
                "readiness_lagged_rel_vs_reported": (round(rel_lag, 4) if rel_lag is not None else None),
                "upsteps": upsteps,
                "replicas_ordered_lo": lo, "replicas_ordered_hi": hi,
                "churn_share_of_bill_lo": round(churn_rs_lo * GPUS_PER_REPLICA / 3600.0 / order_gpu_h, 4) if order_gpu_h else None,
                "churn_share_of_bill_hi": round(churn_rs_hi * GPUS_PER_REPLICA / 3600.0 / order_gpu_h, 4) if order_gpu_h else None,
                "ttft_p99": r["stats"].get("ttft_p99"),
                "sla_ok": (r["stats"].get("ttft_p99") or 0) <= SLA_MS,
            })
    ok = [x for x in rows if x["order_integral_rel_err"] is not None]
    lag = sorted(x["readiness_lagged_rel_vs_reported"] for x in ok)
    rl = [x["readiness_lagged_rel_vs_reported"] for x in ok if x["policy"] == "reactive"]
    evidence = {
        "n_lagged_below": sum(1 for v in lag if v < 0),
        "lagged_median": round(lag[len(lag) // 2], 4),
        "react_lagged_min_rel": round(min(rl), 4),
        "react_lagged_max_rel": round(max(rl), 4),
        "claim": "the reported language gpu_h is already a FROM-ORDER bill",
        "n_runs": len(ok),
        "order_integral_max_rel_err": round(max(x["order_integral_rel_err"] for x in ok), 4),
        "readiness_lagged_min_rel": round(min(x["readiness_lagged_rel_vs_reported"] for x in ok), 4),
        "readiness_lagged_max_rel": round(max(x["readiness_lagged_rel_vs_reported"] for x in ok), 4),
        "reading": "the decision-time (order) integral reproduces every reported "
                   "gpu_h; the readiness-lagged counterfactual falls short. "
                   "Therefore warm-up is ALREADY BILLED and no surcharge applies.",
        "selfcheck_failures": fails,
    }
    return rows, evidence


# --------------------------------------------------------------------------
# ENCODER POOL - the dual accounting is LEGITIMATE here; re-derive it
# --------------------------------------------------------------------------
def encoder() -> tuple[list, list, dict]:
    a2 = json.load(open(A2))
    csv_rows = list(csv.DictReader(open(A2CSV)))
    rows, mism = [], 0
    for r in csv_rows:
        wk, pol, L = r["window"], r["policy"], float(r["lead_s"])
        tag = f"{wk}_{pol}_L{r['lead_s']}"
        sched = json.load(open(A2RUNS / f"{tag}.sched.json"))
        span = float(a2["windows"][wk]["meta"]["span_s"])
        # warm-up = each ordered replica billed over [order, ready] = [t-L, t],
        # clipped to the window. Reproduces the shipped warmup_ws exactly.
        warm = 0.0
        added = 0
        for i in range(1, len(sched)):
            d = sched[i][1] - sched[i - 1][1]
            if d > 0:
                added += d
                tr = sched[i][0]
                warm += d * max(0.0, min(span, tr) - max(0.0, tr - L))
        prov = integrate(sched, span)
        shipped_warm = float(r["warmup_ws"])
        if abs(warm - shipped_warm) > 0.51:
            mism += 1
        rows.append({
            "window": wk, "policy": pol, "lead_s": L, "p99_ms": float(r["p99_ms"]),
            "sla_ok": float(r["p99_ms"]) <= ENC_SLA_MS,
            "provisioned_ws_shipped": float(r["provisioned_ws"]),
            "provisioned_ws_recomputed_over_span": round(prov, 1),
            "replicas_ordered": added,
            "warmup_ws_shipped": shipped_warm,
            "warmup_ws_recomputed": round(warm, 1),
            "total_from_order_ws": float(r["total_from_order_ws"]),
            "warmup_frac": round(shipped_warm / float(r["total_from_order_ws"]), 4),
        })
    idx = {(x["window"], x["policy"], x["lead_s"]): x for x in rows}
    ratios = []
    for wk in ["burst1", "burst3", "burst4", "burst5", "steady24h"]:
        for L in (15.0, 30.0, 45.0, 165.0):
            f, rc = idx.get((wk, "forecast", L)), idx.get((wk, "reactive", L))
            if not f or not rc:
                continue
            rr = f["provisioned_ws_shipped"] / rc["provisioned_ws_shipped"]
            ro = f["total_from_order_ws"] / rc["total_from_order_ws"]
            ratios.append({
                "window": wk, "lead_s": L,
                "ready_ratio_fc_over_react": round(rr, 4),
                "order_ratio_fc_over_react": round(ro, 4),
                "flips_sign": (rr - 1.0) * (ro - 1.0) < 0,
                "reactive_p99_ms": rc["p99_ms"], "forecast_p99_ms": f["p99_ms"],
                "comparator_feasible": rc["sla_ok"] and f["sla_ok"],
                "quotable": bool((rr - 1.0) * (ro - 1.0) < 0 and rc["sla_ok"] and f["sla_ok"]),
            })
    ev = {
        "claim": "the encoder pool genuinely bills from READINESS, so its "
                 "from-order surcharge is real and is NOT a double count",
        "code_evidence": ["simulation/forecast_schedule.py:146-149 (avail = min "
                          "over trailing lead window => schedule is ready-capacity)",
                          "workload/trace_to_two_pool.py:522-529 (provisioned_ws "
                          "integrates that ready schedule)"],
        "numeric_evidence": "provisioned_ws FALLS monotonically with lead at fixed "
                            "policy (e.g. burst5 reactive 100713.0 / 98643.0 / "
                            "96573.0 ws at L=15/30/45), and total_from_order_ws is "
                            "exactly INVARIANT (102783.0 at all three). Under "
                            "order-billing provisioned_ws would instead be the "
                            "lead-invariant quantity. It is not.",
        "warmup_ws_rows_reproduced": len(rows) - mism,
        "warmup_ws_rows_total": len(rows),
        "warmup_rule": "sum over up-steps of delta x |[max(0,t_ready-L), "
                       "min(span,t_ready)]|, from the shipped .sched.json",
    }
    return rows, ratios, ev


def main() -> None:
    lang_rows, lang_ev = language()
    enc_rows, enc_ratios, enc_ev = encoder()

    payload = {
        "what": "cold-start accounting, corrected 2026-07-19 after adversarial audit",
        "headline": "LANGUAGE-pool GPU-hours in this thesis ALREADY BILL FROM ORDER "
                    "(the mocker integrates provisioned = active + starting-up + "
                    "draining workers). NO cold-start surcharge may be added to any "
                    "language cost number. The ENCODER pool is the opposite: it bills "
                    "from readiness, so its from-order surcharge (A2) is legitimate.",
        "retracted": ["the language-pool 'from-order' bill and its warm-up fractions "
                      "(double count)",
                      "'cold start erodes reactive's cost advantage by 0.28-0.74x' "
                      "(double-counted, and those were ratio-point deltas, not factors)",
                      "the flat STARTUP_S=60 s (wrong for 36 of 52 runs; "
                      "STARTUP_TIME = lead in {60,120,300})",
                      "the encoder burst5-L165 'cost order flip' (its reactive "
                      "comparator misses the SLA at p99=3250.2 ms)"],
        "language_pool": {"evidence": lang_ev, "rows": lang_rows,
                          "note": "churn_share_of_bill_* is a CHURN-INTENSITY "
                                  "descriptor - the share of an ALREADY-PAID bill "
                                  "spent on replicas that were ordered but not yet "
                                  "serving. It is not an additional cost."},
        "encoder_pool": {"evidence": enc_ev, "rows": enc_rows, "ratios": enc_ratios},
    }
    (OUT / "coldstart.json").write_text(json.dumps(payload, indent=1))

    with open(OUT / "coldstart.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(lang_rows[0]))
        w.writeheader()
        w.writerows(lang_rows)
    with open(OUT / "encoder_coldstart.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(enc_rows[0]))
        w.writeheader()
        w.writerows(enc_rows)

    # ---------------- report ----------------
    L = ["# G7 - cold-start accounting (CORRECTED 2026-07-19)", "",
         "## The finding is a NEGATIVE one, and it is load-bearing", "",
         "**The language-pool GPU-hours reported throughout this thesis already bill",
         "from instance ORDER, not from readiness.** The mocker's `gpu_hours` is the",
         "time-integral of the *provisioned* worker count - active + starting-up +",
         "draining (`lib/mocker/src/replay/collector.rs:44-52`, accrued in",
         "`offline/agg.rs:823-836`) - and `gen_a11_runs.py:75` reads exactly that field.",
         "**No cold-start surcharge may be added to any language cost number in this",
         "thesis; doing so double-counts.** The previous version of this driver did",
         "exactly that and its output is retracted.", ""]
    e = lang_ev
    L += ["### Evidence (recomputable from a11_data.json + a11_runs/*.log)", "",
          f"- The order-time staircase integral reproduces the reported `gpu_h` on all",
          f"  {e['n_runs']} runs to within {e['order_integral_max_rel_err']:.2%}.",
          f"- The readiness-lagged counterfactual (each up-step delayed by that run's own",
          f"  STARTUP_TIME) instead lands {e['readiness_lagged_min_rel']:+.1%} to "
          f"{e['readiness_lagged_max_rel']:+.1%} against the reported value, falling SHORT on "
          f"{e['n_lagged_below']}/{e['n_runs']} runs (median {e['lagged_median']:+.1%}); the "
          f"{e['n_runs'] - e['n_lagged_below']} exceptions are low-churn forecast arms at "
          f"+0.5% and +1.6%.",
          f"- On the reactive arms, which churn hardest, the lagged series falls "
          f"{e['react_lagged_min_rel']:+.1%} to {e['react_lagged_max_rel']:+.1%} short - "
          f"exactly the discrimination the test needs.",
          "- If billing were from readiness the lagged series would match and the order",
          "  integral would overshoot by the warm-up share. The opposite holds.", ""]
    if e["selfcheck_failures"]:
        L += ["**SELF-CHECK FAILURES:**"] + [f"  - {x}" for x in e["selfcheck_failures"]] + [""]

    L += ["### What survives for the language pool: a churn descriptor, not a cost", "",
          "`churn_share_of_bill` = (replicas ordered x that run's STARTUP_TIME x 2 GPUs)",
          "/ billed GPU-seconds. It measures how much of an **already-paid** bill goes to",
          "replicas that were ordered but not yet serving. Reported as a range because the",
          "planner log's target series and its per-event `(to - from)` deltas only bracket",
          "the true ordered count (`agg.rs` adds `target - (active + pending_startup)`).", ""]
    react = [x for x in lang_rows if x["policy"] == "reactive" and x["lead_s"] == 60]
    fcst = [x for x in lang_rows if x["policy"] == "forecast" and x["lead_s"] == 60]
    if react and fcst:
        L += [f"At the shared L=60 lead (n={len(react)} reactive, n={len(fcst)} forecast):", "",
              f"- reactive churn share {min(x['churn_share_of_bill_lo'] for x in react):.1%}"
              f"-{max(x['churn_share_of_bill_hi'] for x in react):.1%} of its bill",
              f"- forecast churn share {min(x['churn_share_of_bill_lo'] for x in fcst):.1%}"
              f"-{max(x['churn_share_of_bill_hi'] for x in fcst):.1%} of its bill",
              "",
              "This band is L=60-specific. At L=120/300 the startup time equals the lead and",
              "the ordering is not preserved - see coldstart.csv for all rows. Any sentence",
              "quoting reactive's lower language-pool cost must carry its SLA violation in",
              "the same sentence: reactive TTFT p99 runs "
              f"{min(x['ttft_p99'] for x in react if x['ttft_p99']):.0f}-"
              f"{max(x['ttft_p99'] for x in react if x['ttft_p99']):.0f} ms against a "
              f"{SLA_MS:.0f} ms SLA.", ""]

    L += ["---", "", "## Encoder pool (A2): here the dual accounting IS legitimate", "",
          "The encoder controller applies cold start by **delaying availability**:",
          "`simulation/forecast_schedule.py:146-149` emits `avail[i] = min(desired[i-lead:i+1])`,",
          "so an up-step decided at *t* only appears in the schedule at *t+lead*, and",
          "`workload/trace_to_two_pool.py:522-529` integrates that ready-capacity schedule.",
          "The encoder therefore genuinely bills from readiness and its warm-up is unbilled.", "",
          "Numeric confirmation, from `a2_cost_accounting.csv` alone: at fixed policy",
          "`provisioned_ws` **falls** with lead (burst5 reactive: 100713.0 / 98643.0 /",
          "96573.0 ws at L=15/30/45) while `total_from_order_ws` is **exactly invariant**",
          "(102783.0 at all three). Under order-billing the invariant column would be",
          "`provisioned_ws`. It is not.", "",
          f"`warmup_ws` reproduces from the shipped `a2_runs/*.sched.json` on",
          f"{enc_ev['warmup_ws_rows_reproduced']}/{enc_ev['warmup_ws_rows_total']} rows",
          f"under the rule: {enc_ev['warmup_rule']}.", "",
          "### Where re-accounting flips the cost order", "",
          "| window | lead | ready f/r | from-order f/r | flips | reactive p99 | quotable |",
          "|---|---|---|---|---|---|---|"]
    for r in enc_ratios:
        L.append(f"| {r['window']} | {r['lead_s']:.0f} | {r['ready_ratio_fc_over_react']:.4f} | "
                 f"{r['order_ratio_fc_over_react']:.4f} | {'yes' if r['flips_sign'] else ''} | "
                 f"{r['reactive_p99_ms']:.1f} | {'YES' if r['quotable'] else 'no'} |")
    q = [r for r in enc_ratios if r["quotable"]]
    nq = [r for r in enc_ratios if r["flips_sign"] and not r["quotable"]]
    L += ["", "**RETRACTED:** " + ("; ".join(
        f"{r['window']}-L{r['lead_s']:.0f} (reactive p99 {r['reactive_p99_ms']:.1f} ms "
        f"misses the {ENC_SLA_MS:.0f} ms SLA - an infeasible comparator cannot carry a "
        f"cost comparison)" for r in nq) if nq else "none"), ""]
    if q:
        L += ["**Defensible flips** (both arms inside the SLA):", ""]
        for r in q:
            L.append(f"- **{r['window']}, L={r['lead_s']:.0f}**: forecast is "
                     f"{r['ready_ratio_fc_over_react']:.3f}x reactive's cost billed from "
                     f"readiness (dearer) but {r['order_ratio_fc_over_react']:.3f}x billed "
                     f"from order (cheaper); reactive p99 {r['reactive_p99_ms']:.1f} ms, "
                     f"forecast p99 {r['forecast_p99_ms']:.1f} ms.")
        L += ["", "Both flips sit at the L=165 cold-pool lead only. Across the L=15/45",
              "warm-pool band forecast is already the cheaper arm under **both**",
              "conventions on burst1, burst4, burst5 and steady24h, so the flip changes",
              "the story only for a cold pool.", ""]
    L += ["---", "", "## Do not write", "",
          "- any language-pool cold-start surcharge, warm-up fraction-as-cost, or",
          "  \"cold start erodes reactive's advantage\" statement;",
          "- the figure \"0.28-0.74x\" (double-counted, and a ratio-point delta, not a factor);",
          "- the encoder burst5-L165 flip;",
          "- any language churn number computed with a flat 60 s startup.", ""]
    (OUT / "REPORT.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
