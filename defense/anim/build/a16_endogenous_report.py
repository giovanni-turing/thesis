#!/usr/bin/env python3
"""Recompute the A16 endogenous REPORT from the stored iterations.

Reads defense/anim/data/a16_runs/verification.json (written by
gen_a16_endogenous.py) and re-derives every reportable statistic from the
`iterations` arrays.  Nothing is re-simulated; this is a pure function of the
shipped artifact, so every number it emits is independently recomputable by
re-running it.

Why this exists (reporting defects found in adversarial audit):

  D1  Neither arm reaches a FIXED POINT.  Both settle into a PERIOD-2 LIMIT
      CYCLE.  The reactive iterates are 10573.7, 1692.5, 1808.4, 1702.1,
      1808.4, 1702.1, 1808.4 -- an exact 2-cycle, not a transient decaying to
      a point.  In a map with an attracting 2-cycle the fixed point is
      generically repelling and unobservable, so the min/max band is a CYCLE
      ENVELOPE and NOT a bound on a fixed point, and its midpoint is an
      interpolation between two alternating states rather than a point
      estimate.  The two endpoints are moreover p99s over DIFFERENT served
      populations (2962 vs 2952 clients), so the envelope brackets a family of
      quantities, not one quantity.  This module detects the cycle explicitly
      and reports its period and per-phase populations.

  D2  "Failure relocates to lost customers" is FALSE.  Open-loop reactive
      failure is 7.92 % of the offered population and ALL of it is
      served-but-late (abandon_rate is 0 at iterate 0 by construction).  At the
      cycle failure is 6.98 %, of which 4.24-4.56 pp is abandonment and
      2.42-2.74 pp is still served-but-late.  Total failure DECREASED and only
      partly changed character.  This module emits that decomposition instead
      of a relocation claim.

Usage:  python3 defense/anim/build/a16_endogenous_report.py
        [--src <verification.json>] [--out <report.json>] [--print]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "defense/anim/data/a16_runs/verification.json"
OUT = ROOT / "defense/anim/data/a16_runs/a16_endogenous_report.json"

# Observables compared phase-wise when detecting a cycle.  gpu_hours is
# deliberately EXCLUDED: it differs by 0.001 h between the odd phases (1.099 vs
# 1.098), which is rounding, not a third phase.
CYCLE_KEYS = ("n_realized_attempts", "ttft_p99_served", "e2e_p99_from_ingress",
              "offered_goodput", "abandon_rate")
ENVELOPE_KEYS = CYCLE_KEYS + ("gpu_hours", "n_retry_attempts", "n_shed_at_encode",
                              "retry_amplification")


def _same(a, b, rel=1e-9):
    if a is None or b is None:
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= rel * max(1.0, abs(a), abs(b))
    return a == b


def detect_cycle(iters, keys=CYCLE_KEYS, max_period=3):
    """Smallest period p such that the tail alternates with period p.

    Excludes iterate 0 (the open-loop seed, which is not part of the orbit).
    Requires at least 2*p observed orbit iterates and checks EVERY available
    lag-p comparison, so a single accidental coincidence cannot produce a false
    positive.  `laps_verified` records how many repeats actually backed the
    call, because a period claimed off a single repeat is weaker evidence than
    one claimed off three.  Returns period=None when the tail supports no
    period <= max_period.
    """
    orbit = iters[1:]
    for p in range(1, max_period + 1):
        if len(orbit) < 2 * p:
            continue
        # compare the tail pairwise at lag p, over as many laps as we have
        tail = orbit[-(2 * p + 1):]
        n_cmp = len(tail) - p
        ok = all(_same(tail[i].get(k), tail[i + p].get(k))
                 for i in range(n_cmp) for k in keys)
        if ok:
            # Phase membership is drawn ONLY from the verified tail. Earlier
            # orbit iterates are transients that were never checked against the
            # cycle (e.g. reactive k=1 has n=2921 against the cycle's
            # 2952/2962) and must not be listed as cycle members.
            base = len(orbit) - len(tail) + 1   # absolute k of tail[0]
            phases = []
            for ph in range(p):
                members = [i for i in range(len(tail))
                           if (len(tail) - 1 - i) % p == (p - 1 - ph) % p]
                last = tail[members[-1]]
                phases.append({
                    "phase": ph,
                    "iterates": [base + i for i in members],
                    **{k: last.get(k) for k in ENVELOPE_KEYS if k in last},
                })
            # a period-1 "cycle" IS a fixed point; label it as such
            return {"period": p, "is_fixed_point": p == 1,
                    "orbit_iterates_observed": len(orbit),
                    "laps_verified": round(n_cmp / p, 2),
                    "keys_compared": list(keys),
                    "phases": phases}
    return {"period": None, "is_fixed_point": False,
            "orbit_iterates_observed": len(orbit),
            "laps_verified": 0, "keys_compared": list(keys), "phases": []}


def envelope(iters, period, keys=ENVELOPE_KEYS):
    """min/max over one full lap of the detected cycle (the last 2p iterates
    when p>1, else the last 3).  This is a CYCLE ENVELOPE, not a confidence
    interval and not a bound on a fixed point."""
    span = 2 * period if period and period > 1 else 3
    tail = iters[1:][-span:]
    return {k: [min(h[k] for h in tail), max(h[k] for h in tail)]
            for k in keys if all(k in h and h[k] is not None for h in tail)}


def failure_decomposition(it, budget_label="offered population"):
    """Split 1 - offered_goodput into abandonment and served-but-late.

    offered_goodput = (clients whose first token landed within the budget) / 3093
    abandon_rate    = (clients that never got a first token) / 3093
    so served-but-late = failure - abandonment, on the SAME fixed denominator.
    """
    n = it["n_offered_clients"]
    fail = 1.0 - it["offered_goodput"]
    ab = it["abandon_rate"]
    late = fail - ab
    return {"n_offered_clients": n,
            "failure_frac": round(fail, 6),
            "failure_clients": round(fail * n, 1),
            "abandoned_frac": round(ab, 6),
            "abandoned_clients": round(ab * n, 1),
            "served_but_late_frac": round(late, 6),
            "served_but_late_clients": round(late * n, 1),
            "denominator": budget_label}


def analyse(cellid, cell):
    iters = cell["iterations"]
    cyc = detect_cycle(iters)
    p = cyc["period"]
    env = envelope(iters, p)
    ol = iters[0]
    phase_decomp = [failure_decomposition(iters[ph["iterates"][-1]])
                    for ph in cyc["phases"]]
    # censoring: what percentile of the OFFERED population is observable at all
    obs = [{"iterate": i,
            "n_served_of_offered": it["n_realized_attempts"],
            "max_observable_percentile_of_offered":
                round(100.0 * it["n_realized_attempts"] / it["n_offered_clients"], 2)}
           for i, it in enumerate(iters)]
    return {
        "cell": cellid,
        "arm": cell["arm"],
        "converged_flag_in_artifact": cell["converged"],
        "converged_churn_only": cell.get("converged_churn_only"),
        "terminated_by": ("iteration budget (params.iters=%s, no early break)"
                          % cell["params"]["iters"]
                          if len(iters) - 1 >= cell["params"]["iters"]
                          else "early break on churn+band criterion"),
        "orbit": {
            "ITERATES_ttft_p99_served": [it["ttft_p99_served"] for it in iters],
            "ITERATES_offered_goodput": [it["offered_goodput"] for it in iters],
            "ITERATES_n_realized_attempts": [it["n_realized_attempts"] for it in iters],
            "ITERATES_abandon_rate": [it["abandon_rate"] for it in iters],
        },
        "cycle": cyc,
        "cycle_envelope": env,
        "envelope_semantics":
            ("CYCLE ENVELOPE over one full lap of the period-%s orbit. NOT a bound "
             "on a fixed point: the iteration located a cycle, and no fixed point "
             "is shown to lie inside. Endpoints are computed over DIFFERENT "
             "populations (see cycle.phases[*].n_realized_attempts), so this "
             "brackets a family of quantities, not one quantity. The midpoint is "
             "an interpolation between alternating states and MUST NOT be quoted "
             "as a point estimate." % p),
        "open_loop_failure": failure_decomposition(ol),
        "cycle_failure_by_phase": phase_decomp,
        "failure_delta_open_loop_to_cycle": {
            "note": "D2: total failure DECREASED and partly changed character; "
                    "it did NOT relocate. Both figures use the same fixed "
                    "offered denominator of %d clients." % ol["n_offered_clients"],
            "open_loop_failure_frac": round(1.0 - ol["offered_goodput"], 6),
            "cycle_failure_frac_by_phase": [d["failure_frac"] for d in phase_decomp],
            "cycle_abandoned_frac_by_phase": [d["abandoned_frac"] for d in phase_decomp],
            "cycle_served_but_late_frac_by_phase":
                [d["served_but_late_frac"] for d in phase_decomp],
            "total_failure_direction":
                ("DECREASED" if phase_decomp and
                 max(d["failure_frac"] for d in phase_decomp) < 1.0 - ol["offered_goodput"]
                 else "increased/unchanged"),
            "open_loop_is_all_served_but_late":
                bool(abs(ol["abandon_rate"]) < 1e-12),
        },
        "censoring": {
            "note": "ttft_p99_served is computed over SERVED clients only. Where "
                    "abandonment exceeds 1 %, the p99 of the OFFERED population is "
                    "inside the censored set (every abandoner is by construction "
                    "worse than every survivor) and is therefore NOT observable. "
                    "Any served-only p99 must be labelled as such and must not be "
                    "compared to an uncensored open-loop p99 without that label.",
            "per_iterate": obs,
            "served_only_p99_is_censored_at_cycle":
                bool(max(ph["abandon_rate"] for ph in cyc["phases"]) > 0.01)
                if cyc["phases"] else None,
        },
        "abandonment_channel": {
            "note": "n_shed_at_encode counts clients whose ENCODER delay alone "
                    "exceeded their patience (gen_a16_endogenous.py:511, "
                    "`if enc > P[li]`). That test reads only the fixed per-arm "
                    "encoder trace and the seeded patience draw, so it CANNOT "
                    "respond to the iteration -- which is why it is constant "
                    "across iterates. It is policy-determined (the reactive arm's "
                    "encoder backlog) but iteration-invariant, so the endogenous "
                    "FEEDBACK contributes only the residual.",
            "per_iterate_shed_at_encode": [it.get("n_shed_at_encode") for it in iters],
            "at_cycle": [
                {"phase": ph["phase"],
                 "abandoned_clients": round(ph["abandon_rate"] * iters[0]["n_offered_clients"], 1),
                 "shed_at_encode": ph.get("n_shed_at_encode"),
                 "residual_endogenous": round(
                     ph["abandon_rate"] * iters[0]["n_offered_clients"]
                     - (ph.get("n_shed_at_encode") or 0), 1)}
                for ph in cyc["phases"]],
        },
        "retry_activity": {
            "note": "Retry is modelled but essentially inactive; this is an "
                    "ABANDONMENT experiment, not an abandonment/retry experiment.",
            "per_iterate_n_retry_attempts": [it.get("n_retry_attempts") for it in iters],
            "retry_amplification_envelope": env.get("retry_amplification"),
        },
        "cost": {"gpu_hours_envelope": env.get("gpu_hours")},
    }


def build(src: Path):
    raw = src.read_bytes()
    d = json.loads(raw)
    cells = {k: analyse(k, c) for k, c in d["cells"].items()}
    fc = next(v for v in cells.values() if not v["arm"].startswith("reactive"))
    rx = next(v for v in cells.values() if v["arm"].startswith("reactive"))
    gh_fc, gh_rx = fc["cost"]["gpu_hours_envelope"], rx["cost"]["gpu_hours_envelope"]
    ratio = [round(gh_fc[0] / gh_rx[1], 2), round(gh_fc[1] / gh_rx[0], 2)]
    rxe, olf = rx["cycle_envelope"], rx["open_loop_failure"]
    rxfail = [round(1.0 - rxe["offered_goodput"][1], 4),
              round(1.0 - rxe["offered_goodput"][0], 4)]
    # collapse a degenerate range to a single figure rather than writing "x-x"
    rxfail_s = (f"{100 * rxfail[0]:.2f} %" if rxfail[0] == rxfail[1]
                else f"{100 * rxfail[0]:.2f}-{100 * rxfail[1]:.2f} %")
    quotable = (
        "Under a mean-field client model (lognormal patience, mean 5 s; retry "
        "fraction 0.3; two retries) iterated AROUND the unmodified discrete-event "
        "replay -- abandonment is resolved offline, not in-clock -- neither arm "
        "reaches a fixed point; both settle into a period-2 limit cycle. The "
        "forecast arm's latency observables are exactly invariant across every "
        "iterate (TTFT p99 %s ms, E2E-from-ingress p99 %s ms), while its goodput "
        "cycles over %s and its abandonment over %s. The reactive arm enters a "
        "period-2 cycle whose envelope is TTFT p99 %s ms over served clients "
        "only -- the two endpoints are p99s over %d and %d served clients of "
        "%d offered, so the envelope is not an interval for a single quantity "
        "and contains no demonstrated fixed point. Because %.1f-%.1f %% of "
        "offered clients never receive a first token, the reactive arm's p99 "
        "over the OFFERED population is censored and unobservable; the drop from "
        "the open-loop %s ms is therefore measured on a survivor population, and "
        "on the survivorship-immune client clock the served clients still see "
        "%s ms from original ingress. Total offered-goodput failure did NOT "
        "relocate to lost customers: it fell from %.2f %% open-loop (all of it "
        "served-but-late) to %s at the cycle, of which %.2f-%.2f pp is "
        "abandonment and the remainder is still served-but-late. The forecast "
        "arm's goodput is bought at %.1f-%.1fx the GPU-hours."
        % (fc["cycle_envelope"]["ttft_p99_served"][0],
           fc["cycle_envelope"]["e2e_p99_from_ingress"][0],
           fc["cycle_envelope"]["offered_goodput"],
           fc["cycle_envelope"]["abandon_rate"],
           rxe["ttft_p99_served"],
           rx["cycle"]["phases"][0]["n_realized_attempts"],
           rx["cycle"]["phases"][1]["n_realized_attempts"],
           olf["n_offered_clients"],
           100 * rxe["abandon_rate"][0], 100 * rxe["abandon_rate"][1],
           rx["orbit"]["ITERATES_ttft_p99_served"][0],
           rxe["e2e_p99_from_ingress"],
           100 * olf["failure_frac"], rxfail_s,
           100 * rxe["abandon_rate"][0], 100 * rxe["abandon_rate"][1],
           ratio[0], ratio[1]))
    return {
        "_source": {"path": str(src.relative_to(ROOT)),
                    "sha256": hashlib.sha256(raw).hexdigest()},
        "_derivation": "Pure recomputation from the stored `iterations` arrays of "
                       "the source artifact. Nothing re-simulated. Regenerate with "
                       "`python3 defense/anim/build/a16_endogenous_report.py`.",
        "_corrections": {
            "D1": "Reported object is a PERIOD-2 LIMIT CYCLE, not a fixed point. "
                  "Bands are cycle envelopes over different populations; midpoints "
                  "are interpolations and are not point estimates.",
            "D2": "'Failure relocates to lost customers' is retracted. Total "
                  "failure decreased (7.92 % -> 6.98 %) and only partly changed "
                  "character.",
        },
        "gpu_hour_ratio_forecast_over_reactive": ratio,
        "cells": cells,
        "corrected_quotable_claim": quotable,
        "forbidden_phrasings": [
            "fixed point (for either arm -- both are period-2 cycles)",
            "a bound on / bracketing the fixed point",
            "any single iterate quoted as a point estimate",
            "closed loop (this is mean-field, resolved offline)",
            "its failure relocates to lost customers",
            "rescued / latency rescue (the served-only p99 is survivor-censored)",
            "abandonment/retry as a description of what was exercised "
            "(retry amplification <= 0.0003)",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--print", action="store_true")
    a = ap.parse_args()
    rep = build(a.src)
    a.out.write_text(json.dumps(rep, indent=1))
    print(f"-> {a.out.relative_to(ROOT)}")
    for cid, c in rep["cells"].items():
        cy = c["cycle"]
        print(f"\n{cid}\n    PERIOD-{cy['period']} LIMIT CYCLE "
              f"(artifact converged flag={c['converged_flag_in_artifact']}; "
              f"terminated by {c['terminated_by']})")
        for ph in cy["phases"]:
            print(f"      phase {ph['phase']}: iterates {ph['iterates']} "
                  f"n_served={ph['n_realized_attempts']} "
                  f"ttft_p99={ph['ttft_p99_served']} "
                  f"goodput={ph['offered_goodput']} "
                  f"abandon={ph['abandon_rate']}")
        print(f"    envelope ttft_p99={c['cycle_envelope']['ttft_p99_served']} "
              f"goodput={c['cycle_envelope']['offered_goodput']}  "
              f"(envelope, NOT a fixed-point bound; midpoint is not an estimate)")
        olf = c["open_loop_failure"]
        print(f"    failure  open-loop {100*olf['failure_frac']:.2f} % "
              f"(abandon {100*olf['abandoned_frac']:.2f} pp / late "
              f"{100*olf['served_but_late_frac']:.2f} pp)")
        for ph, d in zip(cy["phases"], c["cycle_failure_by_phase"]):
            print(f"             cycle phase {ph['phase']} "
                  f"{100*d['failure_frac']:.2f} % (abandon "
                  f"{100*d['abandoned_frac']:.2f} pp / late "
                  f"{100*d['served_but_late_frac']:.2f} pp)")
    if a.__dict__["print"]:
        print("\n" + rep["corrected_quotable_claim"])


if __name__ == "__main__":
    main()
