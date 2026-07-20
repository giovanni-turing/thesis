#!/usr/bin/env python3
"""G6 — encoder image-SIZE sensitivity sweep.

Closes the `tex/intro.tex` Scope caveat:

    "The trace records image counts, not sizes, so the encoder pool assumes a
     uniform 448^2 image."

True sizes are unrecoverable from the Azure trace, so the honest substitute is a
sensitivity analysis, built to the same template as Appendix
`app:engine-sensitivity`:

  hold the SCHEDULE fixed -> reprice the encoder -> re-grade the SLA.

That appendix's numbers, stated correctly (`tex/apendice.tex` 113-117, 186-197):
against the engine it targets, AIC's composition stays within **12.8%** across
the whole N<=64 serving regime (residuals -2.2%/+11.3%/+5.5% at N=8/32/64 on
vLLM's own vision tower). The **1.4-1.6x figure is the HuggingFace-eager
execution-stack difference**, an upper-bound arm rather than the model's error
bar; `tex/closedloop.tex` 625-632 reprices the winning schedule under that
slower f(N) (encoder-delay p99 784 vs 588 ms) and finds the p90/rho=15 headroom
provisions 24-32 workers against the 12-16 required, absorbing it with no added
workers. G6 borrows the METHOD, not the magnitude.

PROVENANCE WARNING. Every size distribution swept here is ASSUMED. The trace has
no size field. Only the f(N) cost of a given mixture is silicon-grounded. Each
`reprice` entry carries `size_distribution_provenance` and a per-entry
rationale; any figure or table built from this artifact must repeat the label.

FABRIC. The encoder->LLM handoff is priced single-stream, and its bytes scale
with mean POST-MERGE tokens -- i.e. it amplifies with resolution exactly as f(N)
does. `tex/intro.tex` 513-518 states that the 588 ms floor and the 0.62x result
assume an embedding-only handoff or a >=100 Gbps fabric, since at the default
25 Gbps transfer alone violates the bound for every policy. Reporting a
size break-point at 25 Gbps alone would therefore attribute to image SIZE a
failure the thesis has already scoped to the FABRIC. Every cell is consequently
run at BOTH 25 and 100 Gbps (`--fabrics`), and every SLA verdict and break-point
is reported per fabric. 25 Gbps verdicts are labelled `fabric_limited`.

Holding the schedule fixed is the *deployed* situation, not a simplification:
the planner forecasts an image RATE and converts it at rho=15 img/s/worker, a
constant calibrated at 448^2. A size-unaware planner facing bigger images
issues exactly the same schedule and simply under-provisions. Two consequences,
both reported:

  * the cost ratio's numerator (provisioned worker-seconds) is *structurally
    invariant* to repricing -- the schedule did not change, so the 0.62x cannot
    move under a size-unaware planner. The driver asserts this rather than
    assuming it.
  * therefore the entire sensitivity lands on the SLA verdict. What breaks is
    feasibility, and the `esc*` ladder locates the break-point.

The `recover` stage then prices what it costs to fix a broken world: a
size-AWARE planner re-derives rho by the measured cost multiplier
(rho' = 15 / k, k = f_mix(64)/f_448(64)) and regenerates the schedule. G6 does
NOT simulate a correspondingly grown static fleet, so it does not report a true
size-aware cost ratio. What it reports instead, and all it claims:

  * the size-UNAWARE ratio is structurally invariant (asserted, not assumed);
  * the recover arm's ABSOLUTE provisioned worker-seconds, and their ratio to
    the *unchanged* u448 static C=8 denominator -- explicitly labelled an
    UPPER BOUND on the size-aware ratio, since a static fleet facing the same
    mixture would have to grow too and that growth is not simulated here.

Stages
------
  reprice   f(N) curves per distribution; cost multipliers; DB source tags.
            Pure AIC lookups, no pool simulation. Seconds.
  pool      per (distribution, window, policy) converter re-runs under the
            ledgered schedules. The bulk of the wall time.
  recover   size-aware replan for distributions that failed `pool`.

Gates (the driver exits non-zero rather than emit a number it cannot defend):
  1. `MixtureEncoderCostModel.selftest_reduction()` -- the mixture kernel must
     equal AIC's own `_run_encoder_phase` to 1e-9 ms on every single-resolution
     mixture. Run over the UNION of every resolution in play ({224,336,448,672,
     896}), not just the baseline, so it covers 896^2 where encoder_attention
     is extrapolated -- that is precisely where the identity must be checked.
  2. the `u448` control must reproduce the ledgered endpoints exactly
     (f(64)=316.369 ms; burst3 forecast-L30 encoder-delay p99 = 588.37 ms at
     the ledgered 25 Gbps fabric). Hard-fails if the control cell is absent
     from a non-smoke run rather than skipping silently.

Usage
-----
  # smoke (what was run to validate this driver; ~1 min, 1 core)
  aiconfigurator/.venv/bin/python gen_g6_sizesens.py --smoke

  # full sweep
  aiconfigurator/.venv/bin/python gen_g6_sizesens.py --stage all --jobs 6

Writes NEW files only, under defense/anim/data/g6_runs/.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from g6_sizemix import (  # noqa: E402
    BASELINE, DISTRIBUTION_RATIONALE, DISTRIBUTIONS, SIZE_PROVENANCE)

ROOT = Path("/home/gio/tese")
EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
CONV = ROOT / "defense/anim/build/g6_conv_sizemix.py"
SCHED_GEN = ROOT / "verification/scripts/forecast_schedule_issuetime.py"
PARQUET = ROOT / "predictors/results/chronos_images.parquet"
OUTDIR = ROOT / "defense/anim/data/g6_runs"

# SLA + ledgered control values (thesis Tab. cl-aggregate / cl-ewma).
SLA_ENCODER_P99_MS = 1000.0
LEDGER_F64_448_MS = 316.369
LEDGER_BURST3_FC_L30_P99 = 588.37

# The two policies that define the cost ratio. Static C=8 is the *deployable*
# static fleet (the ratio's denominator); forecast p90/rho15/L30 is the winner.
POLICIES = {
    "fc_L30":    {"kind": "forecast", "lead": 30, "rho": 15.0, "quantile": "p90"},
    "static_C8": {"kind": "static", "workers": 8},
    "static_C2": {"kind": "static", "workers": 2},
}
DEFAULT_POLICIES = ["fc_L30", "static_C8"]
DEFAULT_WINDOWS = ["burst3", "burst5", "burst4", "steady24h"]

# Handoff-fabric arm. 25 Gbps is the converter default and the fabric the
# ledgered endpoints were produced under; 100 Gbps is the fabric tex/intro.tex
# 513-518 says the 588 ms floor and the 0.62x result assume. Size sensitivity
# interacts directly with fabric (handoff bytes scale with post-merge tokens),
# so a break-point is meaningless without saying which fabric it is on.
DEFAULT_FABRICS = [25.0, 100.0]
LEDGER_FABRIC_GBPS = 25.0
# forecast_schedule_issuetime.py --max-workers default; the replan ceiling.
SCHED_MAX_WORKERS = 32


def gtag(gbps: float) -> str:
    return f"g{int(round(gbps))}"


_WIN_CACHE: dict | None = None


def windows() -> dict:
    global _WIN_CACHE
    if _WIN_CACHE is None:
        _WIN_CACHE = json.load(open(ROOT / "simulation/windows.json"))
    return _WIN_CACHE


# --------------------------------------------------------------------------
# stage: reprice
# --------------------------------------------------------------------------
def stage_reprice(dists: list[str], sizes=(1, 2, 4, 8, 16, 32, 48, 64)) -> dict:
    """f(N) per distribution + cost multiplier vs the 448^2 baseline."""
    from g6_sizemix import MixtureEncoderCostModel

    base = MixtureEncoderCostModel(DISTRIBUTIONS[BASELINE])

    # GATE 1 -- the mixture kernel must equal AIC's own _run_encoder_phase at
    # EVERY resolution in play, not just the baseline. selftest_reduction()
    # probes each px in its model's own mixture, so build one probe model whose
    # mixture spans the union of all resolutions the run will price. This is
    # what covers 896^2, where encoder_attention is extrapolated.
    all_px = sorted({px for d in dists for px in DISTRIBUTIONS[d]} | {448})
    probe = MixtureEncoderCostModel({px: 1.0 / len(all_px) for px in all_px})
    probe.selftest_reduction()
    print(f"gate 1 ok: mixture kernel == _run_encoder_phase at px={all_px}")

    f448 = {n: base.latency_ms(n)[0] for n in sizes}
    if abs(f448[64] - LEDGER_F64_448_MS) > 1e-3:
        sys.exit(f"GATE FAIL: f(64)@448 = {f448[64]} != ledgered {LEDGER_F64_448_MS}")
    print(f"gate 1b ok: f(64)@448 = {f448[64]:.3f} ms (ledger {LEDGER_F64_448_MS})")

    out = {}
    for name in dists:
        m = MixtureEncoderCostModel(DISTRIBUTIONS[name])
        # include this mixture's patch-equivalent cap so floor_decomposition can
        # read f(cap) for the capsweep cells without a second AIC pass. Shares
        # the single definition with stage_capsweep -- do not inline it here.
        pcap = patch_equivalent_cap({"mixture": m.mix})
        fn = {n: m.latency_ms(n)[0] for n in sorted(set(sizes) | {pcap})}
        out[name] = {
            "mixture": {str(k): v for k, v in m.mix.items()},
            "size_distribution_provenance": SIZE_PROVENANCE,
            "size_distribution_rationale": DISTRIBUTION_RATIONALE.get(
                name, "no rationale on record; ASSUMED."),
            "f_n_ms": {str(n): round(v, 4) for n, v in fn.items()},
            "cost_mult_at_64": round(fn[64] / f448[64], 4),
            "cost_mult_at_8": round(fn[8] / f448[8], 4),
            "patch_equivalent_cap_images": pcap,
            "mean_post_merge_tokens_per_image": m.tokens_per_image,
            "handoff_mult": round(m.tokens_per_image / 196.0, 4),
            "op_db_sources": dict(m.op_sources),
            "extrapolated_ops": [k for k, v in m.op_sources.items()
                                 if v not in ("silicon", "empirical")],
        }
        print(f"  {name:14s} f(64)={fn[64]:9.2f} ms  x{out[name]['cost_mult_at_64']:6.3f}  "
              f"handoff x{out[name]['handoff_mult']:.2f}  "
              f"extrap={out[name]['extrapolated_ops'] or '-'}")
    return out


# --------------------------------------------------------------------------
# stage: pool
# --------------------------------------------------------------------------
def gen_schedule(window: str, lead: int, rho: float, quantile: str, dest: Path) -> None:
    if dest.exists():
        return
    cmd = [str(EDA_PY), str(SCHED_GEN), "--window", window,
           "--quantile", quantile, "--rho", str(rho), "--cold-start-s", str(lead),
           "--parquet", str(PARQUET), "--out", str(dest)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"schedule gen failed ({window} L{lead} rho{rho}):\n{r.stderr[-800:]}")


def run_cell(mix: str, window: str, policy: str, tag: str,
             sched: Path | None, workers: int, cap: int | None = None,
             handoff_gbps: float = LEDGER_FABRIC_GBPS) -> dict:
    """One converter run. Returns the graded stats."""
    out = OUTDIR / f"{tag}.jsonl"
    cmd = [str(AIC_PY), str(CONV), "--out", str(out),
           "--offset", str(windows()[window]["offset"]),
           "--max-requests", str(windows()[window]["max_requests"]),
           "--encoder-workers", str(workers),
           "--handoff-gbps", str(handoff_gbps)]
    if cap is not None:
        cmd += ["--encoder-batch-images", str(cap)]
    if sched is not None:
        cmd += ["--worker-schedule", str(sched)]
    env = dict(os.environ, G6_MIX=mix)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"converter failed ({tag}):\n{r.stderr[-1500:]}")
    st = json.load(open(str(out) + ".stats.json"))
    mixinfo = json.load(open(str(out) + ".g6mix.json"))
    p99 = st["encoder_delay_ms"]["p99"]
    div = st["queue_divergent"]
    rec = {
        "mixture": mix, "window": window, "policy": policy,
        "encoder_delay_p99_ms": p99,
        "encoder_delay_max_ms": st["encoder_delay_ms"]["max"],
        "handoff_p99_ms": st["handoff_ms"]["p99"],
        "provisioned_worker_s": st["provisioned_worker_seconds"],
        "queue_divergent": div,
        "sla_pass": bool((not div) and p99 <= SLA_ENCODER_P99_MS),
        "handoff_gbps": handoff_gbps,
        # tex/intro.tex:513-518: at 25 Gbps the single-stream handoff alone
        # violates the bound for every policy, so a FAIL here is not
        # attributable to image size without the 100 Gbps arm beside it.
        "fabric_limited": handoff_gbps <= 25.0,
        "small_batch_lt8_forward_fraction": mixinfo["small_batch_lt8_forward_fraction"],
        "small_batch_lt8_worker_second_fraction": mixinfo.get(
            "small_batch_lt8_worker_second_fraction"),
        "size_distribution_provenance": SIZE_PROVENANCE,
        "extrapolated_ops": mixinfo["extrapolated_ops"],
        "batch_cap_images": cap or 64,
        "runtime_s": round(time.time() - t0, 1),
    }
    # free the big per-request jsonl: G6 grades on stats, not per-request records
    try:
        out.unlink()
    except FileNotFoundError:
        pass
    return rec


def stage_pool(dists, wins, policies, jobs, fabrics) -> dict:
    cells = []
    for w in wins:
        for pol in policies:
            spec = POLICIES[pol]
            if spec["kind"] == "forecast":
                sched = OUTDIR / f"sched_{w}_{pol}.json"
                gen_schedule(w, spec["lead"], spec["rho"], spec["quantile"], sched)
                workers = 2
            else:
                sched, workers = None, spec["workers"]
            for m in dists:
                # the fabric arm: the same cell at every handoff line rate, so
                # no SLA verdict is ever reported without its fabric attached
                for g in fabrics:
                    cells.append((m, w, pol, f"{m}__{w}__{pol}__{gtag(g)}",
                                  sched, workers, None, g))

    print(f"pool stage: {len(cells)} cells "
          f"({len(dists)}x{len(wins)}x{len(policies)}x{len(fabrics)} fabrics), "
          f"{jobs} concurrent")
    res = {}
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(run_cell, *c): c for c in cells}
        for fut in cf.as_completed(futs):
            c = futs[fut]
            rec = fut.result()
            res[c[3]] = rec
            print(f"  {c[3]:48s} p99={rec['encoder_delay_p99_ms']:9.1f} "
                  f"prov={rec['provisioned_worker_s']:9.1f} "
                  f"{'PASS' if rec['sla_pass'] else 'FAIL'}"
                  f"{' [fabric-limited 25G]' if rec['fabric_limited'] else ''}"
                  f"{' DIVERGENT' if rec['queue_divergent'] else ''}")
    return res


def gate2(res: dict, smoke: bool) -> None:
    """GATE 2 -- the u448 control must reproduce the ledgered endpoint.

    Fails CLOSED: the control cell is the only thing tying G6 to the ledgered
    588.37 ms, and --dists/--windows are user-settable, so a run that omits it
    must not quietly emit numbers with no anchor.
    """
    key = f"{BASELINE}__burst3__fc_L30__{gtag(LEDGER_FABRIC_GBPS)}"
    ctrl = res.get(key)
    if ctrl is None:
        msg = (f"GATE 2 UNRUNNABLE: control cell {key} absent. The ledgered "
               f"anchor requires --dists to include {BASELINE}, --windows to "
               f"include burst3, --policies to include fc_L30 and --fabrics to "
               f"include {LEDGER_FABRIC_GBPS:g}.")
        if not smoke:
            sys.exit(msg)
        print("WARNING (smoke only): " + msg)
        return
    if abs(ctrl["encoder_delay_p99_ms"] - LEDGER_BURST3_FC_L30_P99) > 0.5:
        sys.exit(f"GATE 2 FAIL: u448 burst3 fc_L30 @25G p99 = "
                 f"{ctrl['encoder_delay_p99_ms']} != ledgered "
                 f"{LEDGER_BURST3_FC_L30_P99}")
    print(f"gate 2 ok: u448 control reproduces ledgered burst3 p99 "
          f"{ctrl['encoder_delay_p99_ms']} ms @ {LEDGER_FABRIC_GBPS:g} Gbps")


# --------------------------------------------------------------------------
# stage: recover  (size-AWARE replan -- where the cost ratio actually moves)
# --------------------------------------------------------------------------
def broken_mixtures(pool: dict, fabric: float | None = None) -> list[str]:
    """Mixtures whose forecast arm fails the SLA (optionally at one fabric)."""
    return sorted({v["mixture"] for v in pool.values()
                   if v["policy"] == "fc_L30" and not v["sla_pass"]
                   and (fabric is None or v["handoff_gbps"] == fabric)})


def stage_recover(reprice: dict, pool: dict, wins, jobs, fabrics) -> dict:
    # A mixture only needs recovering if it breaks on the fabric the thesis
    # actually assumes. Breaking only at 25 Gbps is a fabric result, not a size
    # result, and replanning worker counts cannot fix a link.
    target = max(fabrics)
    broken = broken_mixtures(pool, target)
    also_25 = [m for m in broken_mixtures(pool) if m not in broken]
    print(f"recover stage: {len(broken)} mixtures broken at {target:g} Gbps -> {broken}")
    if also_25:
        print(f"  (not recovered, break only at <={min(fabrics):g} Gbps i.e. "
              f"FABRIC-limited, not size-limited: {also_25})")
    res = {}

    # size-aware replan schedules. gen_schedule shells out to a parquet-loading
    # subprocess each time; serially this dominates the stage's wall time, so
    # generate them all in parallel BEFORE dispatching the converter cells.
    plans = []
    for m in broken:
        k = reprice[m]["cost_mult_at_64"]
        rho = round(15.0 / k, 4)  # size-aware capacity conversion
        for w in wins:
            plans.append((m, w, rho, OUTDIR / f"sched_{w}_fcAware_{m}.json"))
    ok: dict[tuple[str, str], tuple[float, Path]] = {}
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(gen_schedule, w, 30, rho, "p90", sched): (m, w, rho, sched)
                for m, w, rho, sched in plans}
        for fut in cf.as_completed(futs):
            m, w, rho, sched = futs[fut]
            try:
                fut.result()
            except RuntimeError as e:
                print(f"  !! replan failed {m}/{w}: {e}")
                continue
            ok[(m, w)] = (rho, sched)

    cells = []
    for (m, w), (rho, sched) in sorted(ok.items()):
        for g in fabrics:
            cells.append((m, w, f"fcAware_rho{rho}",
                          f"{m}__{w}__fcAware__{gtag(g)}", sched, 2, None, g))
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(run_cell, *c): c for c in cells}
        for fut in cf.as_completed(futs):
            c = futs[fut]
            rec = fut.result()
            sch = json.load(open(c[4]))
            steps = sch["schedule"] if isinstance(sch, dict) and "schedule" in sch else sch
            try:
                peak = max(s[1] if isinstance(s, list) else s["workers"] for s in steps)
            except Exception:
                peak = None
            rec["replan_rho"] = float(c[2].split("rho")[1])
            rec["peak_workers"] = peak
            # the planner's own ceiling (forecast_schedule_issuetime.py
            # --max-workers default). A replan pinned flat at the cap is not a
            # replan: the size-unaware ceiling has made the arm meaningless.
            rec["maxworkers_cap"] = SCHED_MAX_WORKERS
            rec["hit_maxworkers_cap"] = (peak == SCHED_MAX_WORKERS)
            res[c[3]] = rec
            print(f"  {c[3]:48s} p99={rec['encoder_delay_p99_ms']:9.1f} "
                  f"prov={rec['provisioned_worker_s']:9.1f} peak={peak} "
                  f"{'PASS' if rec['sla_pass'] else 'FAIL'}"
                  f"{f'  [HIT max-workers={SCHED_MAX_WORKERS} CAP]' if rec['hit_maxworkers_cap'] else ''}")
    return res


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# stage: capsweep  (the size-AWARE batching fix)
# --------------------------------------------------------------------------
# The zero-queue service floor is f(cap) + p99 handoff -- the thesis's own
# reading of why every adequately-provisioned policy lands on 588 ms
# (f(64)=316.4 + handoff 272). When a mixture's floor alone exceeds the
# 1000 ms bound, the failure is IRRECOVERABLE BY PROVISIONING: no worker count
# lowers it, which is why the `recover` replan cannot help. The genuine fix is
# to stop capping batches by IMAGE count (a 448^2-calibrated constant) and cap
# them by PATCH count instead, holding patches-per-forward at the collected
# 64 x 784 = 50,176. That is the size-aware deployment, and this stage prices it.
PATCH_BUDGET = 64 * 784


def patch_equivalent_cap(reprice_entry: dict) -> int:
    """Image cap holding pre-merge patches per forward at the collected budget.

    SINGLE DEFINITION -- stage_reprice calls this too, so the cap it bakes into
    `f_n_ms` is the same integer stage_capsweep dispatches with and the same key
    floor_decomposition looks up. Do not re-inline the arithmetic anywhere.
    """
    mix = {int(k): v for k, v in reprice_entry["mixture"].items()}
    mean_pre = sum(w * (px // 16) ** 2 for px, w in mix.items())
    return max(1, int(round(PATCH_BUDGET / mean_pre)))


def stage_capsweep(reprice, pool, wins, jobs, fabrics) -> dict:
    # as in recover: only the fabric the thesis assumes defines a size failure
    target = max(fabrics)
    broken = broken_mixtures(pool, target)
    print(f"capsweep stage: {len(broken)} mixtures broken at {target:g} Gbps -> {broken}")
    cells = []
    for m in broken:
        cap = patch_equivalent_cap(reprice[m])
        for w in wins:
            sched = OUTDIR / f"sched_{w}_fc_L30.json"
            if not sched.exists():
                continue
            for g in fabrics:
                cells.append((m, w, f"fc_L30_cap{cap}",
                              f"{m}__{w}__fc_L30_cap{cap}__{gtag(g)}",
                              sched, 2, cap, g))
    res = {}
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(run_cell, *c): c for c in cells}
        for fut in cf.as_completed(futs):
            c = futs[fut]
            rec = fut.result()
            res[c[3]] = rec
            print(f"  {c[3]:48s} cap={rec['batch_cap_images']:3d} "
                  f"p99={rec['encoder_delay_p99_ms']:9.1f} "
                  f"prov={rec['provisioned_worker_s']:9.1f} "
                  f"{'PASS' if rec['sla_pass'] else 'FAIL'}")
    return res


def floor_decomposition(reprice, pool, wins) -> dict:
    """Split each cell's p99 into service floor vs queueing.

    floor = f_mix(cap) + p99 handoff. A cell whose floor already exceeds the
    bound is floor-bound (irrecoverable by adding workers); one that fails only
    with queueing on top is queue-bound (a provisioning problem).
    """
    out = {}
    for key, rec in pool.items():
        m = rec["mixture"]
        if m not in reprice:
            continue
        f_cap = reprice[m]["f_n_ms"].get(str(rec["batch_cap_images"]))
        if f_cap is None:
            # a cap that stage_reprice did not price means the cap definition
            # and the reprice key have drifted apart. Silently dropping the cell
            # would delete rows from the floor table without a trace.
            raise KeyError(
                f"floor_decomposition: no f(N) at cap={rec['batch_cap_images']} "
                f"for mixture {m!r} (cell {key}). stage_reprice must price every "
                f"cap patch_equivalent_cap() can produce -- they share one "
                f"definition, so this means one of them changed.")
        floor = f_cap + rec["handoff_p99_ms"]
        p99 = rec["encoder_delay_p99_ms"]
        out[key] = {
            "f_at_cap_ms": round(f_cap, 3),
            "handoff_p99_ms": rec["handoff_p99_ms"],
            "handoff_gbps": rec.get("handoff_gbps"),
            "fabric_limited": rec.get("fabric_limited"),
            # which term of the floor dominates -- compute or transfer
            "floor_share_handoff": (round(rec["handoff_p99_ms"] / floor, 4)
                                    if floor > 0 else None),
            "service_floor_ms": round(floor, 3),
            "queueing_ms": round(max(0.0, p99 - floor), 3),
            "floor_exceeds_sla": floor > SLA_ENCODER_P99_MS,
            "failure_mode": (
                "pass" if rec["sla_pass"]
                else "floor-bound (irrecoverable by provisioning)"
                if floor > SLA_ENCODER_P99_MS else "queue-bound (add workers)"),
        }
    return out


def summarize(reprice, pool, recover, wins, fabrics) -> dict:
    """Cost ratio + break-point, the two numbers the thesis needs.

    Everything is keyed BY FABRIC. A break-point without its handoff line rate
    is not a size result (tex/intro.tex:513-518).
    """
    floors = floor_decomposition(reprice, pool, wins)
    ratios, breakpoint = {}, {}
    for w in wins:
      for g in fabrics:
        gt = gtag(g)
        den = pool.get(f"{BASELINE}__{w}__static_C8__{gt}")
        for m in reprice:
            num = pool.get(f"{m}__{w}__fc_L30__{gt}")
            d_m = pool.get(f"{m}__{w}__static_C8__{gt}")
            if not (num and den):
                continue
            ratios[f"{m}__{w}__{gt}"] = {
                "handoff_gbps": g,
                "fabric_limited": num["fabric_limited"],
                "fc_provisioned_worker_s": num["provisioned_worker_s"],
                "static_C8_provisioned_worker_s": den["provisioned_worker_s"],
                "cost_ratio_vs_static_C8": round(
                    num["provisioned_worker_s"] / den["provisioned_worker_s"], 4),
                "fc_sla_pass": num["sla_pass"],
                "fc_p99_ms": num["encoder_delay_p99_ms"],
                "static_C8_sla_pass": d_m["sla_pass"] if d_m else None,
                "static_C8_p99_ms": d_m["encoder_delay_p99_ms"] if d_m else None,
            }
    # break-point on the esc ladder (fraction of 896^2 images), per fabric.
    # Each rung carries its floor decomposition so the head-line number is never
    # reported without its CAUSE: floor-bound vs queue-bound, and the
    # compute-vs-handoff split of the floor.
    for w in wins:
      for g in fabrics:
        gt = gtag(g)
        ladder = []
        for m in sorted(reprice):
            if not m.startswith("esc"):
                continue
            key = f"{m}__{w}__fc_L30__{gt}"
            rec = pool.get(key)
            if not rec:
                continue
            fd = floors.get(key, {})
            ladder.append({
                "frac_896": int(m[3:]) / 100.0,
                "sla_pass": rec["sla_pass"],
                "p99_ms": rec["encoder_delay_p99_ms"],
                "f_at_cap_ms": fd.get("f_at_cap_ms"),
                "handoff_p99_ms": fd.get("handoff_p99_ms"),
                "service_floor_ms": fd.get("service_floor_ms"),
                "queueing_ms": fd.get("queueing_ms"),
                "floor_share_handoff": fd.get("floor_share_handoff"),
                "failure_mode": fd.get("failure_mode"),
            })
        ladder.sort(key=lambda r: r["frac_896"])
        first_fail = next((r["frac_896"] for r in ladder if not r["sla_pass"]), None)
        last_pass = max([r["frac_896"] for r in ladder if r["sla_pass"]], default=None)
        fail_mode = next((r["failure_mode"] for r in ladder if not r["sla_pass"]), None)
        breakpoint[f"{w}__{gt}"] = {
            "window": w, "handoff_gbps": g,
            "fabric_limited": g <= 25.0,
            "ladder": ladder,
            "last_passing_frac_896": last_pass,
            "first_failing_frac_896": first_fail,
            "break_failure_mode": fail_mode,
            "size_distribution_provenance": SIZE_PROVENANCE,
        }
    # invariance check: repricing must not move provisioned worker-time
    inv = {}
    for w in wins:
      for g in fabrics:
        gt = gtag(g)
        vals = {m: pool[f"{m}__{w}__fc_L30__{gt}"]["provisioned_worker_s"]
                for m in reprice if f"{m}__{w}__fc_L30__{gt}" in pool}
        inv[f"{w}__{gt}"] = {"distinct_values": sorted(set(vals.values())),
                             "invariant": len(set(vals.values())) == 1}
    return {"cost_ratios": ratios, "breakpoint": breakpoint,
            "provisioned_invariance": inv,
            "recover_cost": recover_cost(pool, recover, wins, fabrics),
            "floor_decomposition": floors}


def recover_cost(pool, recover, wins, fabrics) -> dict:
    """Price the size-AWARE replan arm.

    IMPORTANT SCOPE LIMIT. G6 does NOT simulate a static fleet grown to meet the
    SLA under the repriced mixture, so this is NOT a size-aware cost ratio. The
    denominator stays the UNCHANGED u448 static C=8 fleet, which means the ratio
    below is an UPPER BOUND: a static fleet facing the same mixture would have to
    grow too, and that growth would push the ratio back down. Reported as an
    absolute worker-second count first, the bounded ratio second.
    """
    out = {}
    for key, rec in (recover or {}).items():
        w, g = rec["window"], rec["handoff_gbps"]
        den = pool.get(f"{BASELINE}__{w}__static_C8__{gtag(g)}")
        if den is None:
            continue
        out[key] = {
            "mixture": rec["mixture"], "window": w, "handoff_gbps": g,
            "replan_rho": rec.get("replan_rho"),
            "peak_workers": rec.get("peak_workers"),
            "hit_maxworkers_cap": rec.get("hit_maxworkers_cap"),
            "recover_provisioned_worker_s": rec["provisioned_worker_s"],
            "baseline_static_C8_provisioned_worker_s": den["provisioned_worker_s"],
            "upper_bound_ratio_vs_UNGROWN_static_C8": round(
                rec["provisioned_worker_s"] / den["provisioned_worker_s"], 4),
            "ratio_caveat": (
                "UPPER BOUND ONLY: denominator is the unchanged u448 static C=8 "
                "fleet. A static fleet meeting the SLA under this mixture must "
                "grow; that growth is NOT simulated, so the true size-aware cost "
                "ratio is lower than this number."),
            "recover_sla_pass": rec["sla_pass"],
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["reprice", "pool", "recover", "all"])
    ap.add_argument("--dists", default=",".join(DISTRIBUTIONS))
    ap.add_argument("--windows", default=",".join(DEFAULT_WINDOWS))
    ap.add_argument("--policies", default=",".join(DEFAULT_POLICIES))
    ap.add_argument("--fabrics", default=",".join(f"{g:g}" for g in DEFAULT_FABRICS),
                    help="encoder->LLM handoff line rates (Gbps) to sweep. "
                         "Default 25,100: 25 is the converter default and the "
                         "fabric the ledgered endpoints were produced under; "
                         "100 is the fabric tex/intro.tex:513-518 says the "
                         "588 ms floor and the 0.62x result assume. Do not drop "
                         "100 -- a break-point at 25 alone is a FABRIC result "
                         "misreported as a SIZE result.")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--with-aggregate", action="store_true",
                    help="append the week-scale `aggregate` window (749,601 req). "
                         "NOT validated at authoring time (the >100k scale was "
                         "off-limits); extrapolated at ~30-60 s and ~1.5 GB per "
                         "cell from the measured 88k-request point (3.0 s, 0.48 GB).")
    ap.add_argument("--smoke", action="store_true",
                    help="tiny validation: burst3 only, 3 distributions, 2 jobs")
    args = ap.parse_args()

    if args.smoke:
        args.dists = "u448,esc010,mix_heavytail"
        args.windows = "burst3"
        args.policies = "fc_L30,static_C8"
        args.fabrics = "25,100"
        args.jobs = 2
        args.stage = "all"

    dists = [d.strip() for d in args.dists.split(",") if d.strip()]
    wins = [w.strip() for w in args.windows.split(",") if w.strip()]
    fabrics = sorted({float(g) for g in args.fabrics.split(",") if g.strip()})
    if LEDGER_FABRIC_GBPS not in fabrics:
        sys.exit(f"--fabrics must include the ledgered {LEDGER_FABRIC_GBPS:g} Gbps "
                 f"(GATE 2's control cell is defined there); got {fabrics}")
    if max(fabrics) < 100.0:
        print("WARNING: no >=100 Gbps arm. Every SLA verdict this run emits is "
              "FABRIC-LIMITED and must not be attributed to image size.")
    if args.with_aggregate and "aggregate" not in wins:
        wins.append("aggregate")
    pols = [p.strip() for p in args.policies.split(",") if p.strip()]
    for d in dists:
        if d not in DISTRIBUTIONS:
            sys.exit(f"unknown distribution {d!r}; have {sorted(DISTRIBUTIONS)}")
    OUTDIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    res = {"config": {"dists": dists, "windows": wins, "policies": pols,
                      "fabrics_gbps": fabrics,
                      "ledger_fabric_gbps": LEDGER_FABRIC_GBPS,
                      "sla_encoder_p99_ms": SLA_ENCODER_P99_MS, "smoke": args.smoke,
                      "size_distribution_provenance": SIZE_PROVENANCE}}

    print("== stage: reprice ==")
    res["reprice"] = stage_reprice(dists)
    if args.stage in ("pool", "all"):
        print("== stage: pool ==")
        res["pool"] = stage_pool(dists, wins, pols, args.jobs, fabrics)
        gate2(res["pool"], args.smoke)
    if args.stage == "recover" and "pool" not in res:
        # recover consumes pool results; it has no way to obtain them alone.
        sys.exit("--stage recover needs pool results in the same invocation "
                 "(it grades which mixtures broke). Run --stage all.")
    if args.stage in ("recover", "all") and "pool" in res:
        print("== stage: recover ==")
        res["recover"] = stage_recover(res["reprice"], res["pool"], wins,
                                       args.jobs, fabrics)
        print("== stage: capsweep ==")
        res["capsweep"] = stage_capsweep(res["reprice"], res["pool"], wins,
                                         args.jobs, fabrics)
        res["capsweep_floor"] = floor_decomposition(res["reprice"], res["capsweep"], wins)
    if "pool" in res:
        res["summary"] = summarize(res["reprice"], res["pool"],
                                   res.get("recover", {}), wins, fabrics)

    res["wall_s"] = round(time.time() - t0, 1)
    dest = OUTDIR / ("g6_smoke.json" if args.smoke else "g6_sizesens.json")
    dest.write_text(json.dumps(res, indent=1))
    print(f"\n== done in {res['wall_s']}s -> {dest}")
    if "summary" in res:
        print(f"  NOTE: all size distributions are {SIZE_PROVENANCE}")
        for k, bp in sorted(res["summary"]["breakpoint"].items()):
            if not bp["ladder"]:
                continue
            print(f"  break-point {k} ({bp['handoff_gbps']:g} Gbps"
                  f"{', FABRIC-LIMITED' if bp['fabric_limited'] else ''}): "
                  f"last pass q(896)={bp['last_passing_frac_896']}, "
                  f"first fail q(896)={bp['first_failing_frac_896']}"
                  f"  cause={bp['break_failure_mode']}")
        for k, iv in sorted(res["summary"]["provisioned_invariance"].items()):
            print(f"  provisioned-worker-time invariance {k}: {iv['invariant']} "
                  f"({iv['distinct_values']})")
        for k, rc in sorted(res["summary"].get("recover_cost", {}).items()):
            print(f"  recover {k:44s} prov={rc['recover_provisioned_worker_s']:9.1f} "
                  f"<= {rc['upper_bound_ratio_vs_UNGROWN_static_C8']:.3f}x "
                  f"(UPPER BOUND, ungrown denominator)"
                  f"{'  [HIT CAP]' if rc['hit_maxworkers_cap'] else ''}")
        print("  failure modes:")
        for k, v in sorted(res["summary"]["floor_decomposition"].items()):
            if v["failure_mode"] != "pass":
                print(f"    {k:48s} floor={v['service_floor_ms']:8.1f} "
                      f"(f={v['f_at_cap_ms']:7.1f} + handoff={v['handoff_p99_ms']:7.1f}, "
                      f"{100 * (v['floor_share_handoff'] or 0):4.1f}% handoff) "
                      f"queue={v['queueing_ms']:8.1f}  {v['failure_mode']}")
        for k, v in sorted(res.get("capsweep_floor", {}).items()):
            print(f"    [capsweep] {k:38s} floor={v['service_floor_ms']:8.1f} "
                  f"-> {v['failure_mode']}")


if __name__ == "__main__":
    main()
