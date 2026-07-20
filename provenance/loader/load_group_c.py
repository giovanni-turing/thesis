#!/usr/bin/env python3
"""K31 loader -- ADJUDICATION §2.4, §2.5, §2.11 (GROUP C).

DDL lives in provenance/schema/25_group_c.sql (+ 26_group_c_checks.sql) and must be applied first.

WHAT THIS LOADS
---------------
§2.4  The riders knee/belief derivation (closedloop.tex:328, 331, 337).
      The riders RUNS were already in the store; the DERIVATION was not. This
      loads the inputs, not just the outputs, so the claim is recomputable:

        capacity_belief_sample   every "Agg: X rps / Y engine_rps" tick from all
                                 20 riders44 replay logs, degenerate ticks kept
                                 and FLAGGED rather than dropped
        capacity_knee_probe      the two knee ladders (arrival-speedup on burst1,
                                 forecast-scale on burst1 and burst4), each with
                                 its offered rate, tail metrics and SLA verdict
        capacity_derivation      belief / r_tail -> scale, with the margin

      Verified during authoring, against the artifacts:
        belief  median(engine_rps | engine_rps<=100) over fc_lead60.log
                = 10.0700 exactly, n=86, p10 8.45 p90 12.83
                -> published "10.07 (p10-p90 8.5-12.8)"  results-ledger.md:147
        burst1  r_tail = 3.2466094488562023 / 2 = 1.6233 req/s  (s=1.5, PASS 905.86)
                next rung s=2.0 -> 2.1643 FAILS (1078.61)       -> published 1.62
        burst4  6.22 FAIL (1103.91) => r_tail < 10.07/6.22 = 1.6190
                7.00 PASS ( 792.01) => r_tail <= 10.07/7.00 = 1.4386
                8.00 PASS ( 753.79) => r_tail >= 10.07/8.00 = 1.2588
                -> published bracket [1.26, 1.44]
        scale   10.07 / 1.2588 = 8.0 adopted; vs binding 10.07/1.4386 = 7.0
                -> margin 8.0/7.0 = 1.1429 -> published "~14%"

§2.5  The four riders LADDER runs carried NULL lead_s / window_name / tp although
      run_44_riders.sh pins STARTUP_TIME=60, AIC_TP=2 and the burst1 grid trace.
      Backfilled (NULL -> value ONLY; a non-NULL value aborts the write), with
      every change recorded in runs_config_backfill, the generating command in
      grid_command, and a ledger_entry row. Also policy='reactive' and n_replicas=2.

§2.4 (completion, 2026-07-20)  _load_probe_config extends the same NULL-only
      backfill to the SIXTEEN non-ladder riders runs -- the derivation's own INPUT
      runs -- which still carried NULL window_name / lead_s / n_replicas /
      arrival_speedup, so that `runs WHERE window_name='burst1'` missed every knee
      probe. window_name is re-derived from each report's num_requests, not the file
      name. Checks C405 (rewritten column-agnostic), C408, C409 and view
      v_riders_probe_config live in provenance/schema/29_riders_probe_config.sql --
      apply it after this loader for the checks; the loader itself needs only the
      columns already created by 01_schema.sql.

§2.11 (a) collector_artifacts/phaseB_fallback_trace/result.txt -> collector_scalar
          SOL 0.00605 ms vs rtx_5090 measured 0.03580 ms = 5.9174x  (intro.tex:311)
      (b) handoff_gbps / handoff_rtt_ms promoted out of encoder_run_summary.metrics
          so the ds4 fabric arm is queryable                 (intro.tex:514, 516)
      (c) the encoder factoring-invariance probe             (twopool.tex:118)

IDEMPOTENCE
-----------
Every file is sha256-gated through ingest_log and every write is an upsert or a
delete-then-insert scoped to this loader's own rows. Running twice loads 0 rows.
The §2.5 backfill and the §2.11(b) promotion are UPDATE ... WHERE col IS NULL, so
they are no-ops on the second pass by construction.

Run:  cd /home/gio/tese/provenance/loader && python3 load_group_c.py [--reload]
"""
import json
import os
import re
import sys

import db
import ingest_common as ic
from runid import run_id_of

KIND = "K31"

RIDERS = "/home/gio/tese/simulation/results/riders44"
RIDERS_SH = "/home/gio/tese/simulation/run_44_riders.sh"
PHASEB = "/home/gio/tese/collector_artifacts/phaseB_fallback_trace/result.txt"
PHASE2_MD = "/home/gio/tese/progress/phase2-simulation.md"
LEDGER_MD = "/home/gio/tese/progress/results-ledger.md"

# Thesis evaluation SLA (twopool.tex; the same bound the grid and the closed loop use).
SLA_TTFT_P99_MS = 1000.0
SLA_ITL_P99_MS = 100.0

# A tick reporting >100 req/s per replica is a start-up/idle artefact: a couple of
# completions over a near-zero busy window. Dropped from the published median by the
# rule recorded at results-ledger.md:147. Stored and flagged, never deleted.
DEGENERATE_ENGINE_RPS = 100.0

TICK_RE = re.compile(r"Agg: ([0-9.]+) rps / ([0-9.]+) engine_rps")

# The log whose ticks the published belief is the median of. This is NOT arbitrary and
# NOT poolable: fc_lead60 is the ledgered burst1 forecast run at the deployed 60 s lead,
# and its median is 10.07 exactly. Pooling all 20 logs gives 8.94; pooling the four
# fc_lead* logs gives 9.84. Recorded here because the population IS the derivation.
BELIEF_LOG = "fc_lead60.log"


# --- probe ladders ---------------------------------------------------------
# (stem, window, probe_kind, arrival_speedup, forecast_req_scale, superseded_reason)
KNEE_PROBES = [
    # (c) direct measurement: burst1, N=2 TP2 replicas, arrival clock sped up.
    ("tp2knee_s1.25", "burst1", "arrival_speedup", 1.25, None, None),
    ("tp2knee_s1.5",  "burst1", "arrival_speedup", 1.5,  None, None),
    ("tp2knee_s2",    "burst1", "arrival_speedup", 2.0,  None, None),
    # forecast-scale bracket on burst1
    ("fc_scale4.64",         "burst1", "forecast_scale", None, 4.64, None),
    ("fc_scale6.22",         "burst1", "forecast_scale", None, 6.22, None),
    ("fc_scale6.22_regress", "burst1", "forecast_scale", None, 6.22, None),
    ("fc_lead60",            "burst1", "forecast_scale", None, 8.0,  None),
    # forecast-scale bracket on burst4 -- the BINDING window
    ("fc_scale6.22_burst4_v2", "burst4", "forecast_scale", None, 6.22, None),
    ("fc_scale7.0_burst4_v2",  "burst4", "forecast_scale", None, 7.0,  None),
    ("fc_scale8.0_burst4_v2",  "burst4", "forecast_scale", None, 8.0,  None),
    # superseded: pre-bugfix sub-minute forecast feed (results-ledger.md, 2026-07-09).
    # Two compounding bugs understated demand 4x at 15 s resolution. Kept as the bug
    # record; the _v2 rows above replace them.
    ("fc_scale6.22_burst4", "burst4", "forecast_scale", None, 6.22,
     "pre-bugfix sub-minute forecast feed (units + tick-clock); superseded by "
     "fc_scale6.22_burst4_v2 -- see results-ledger.md 2026-07-09"),
    ("fc_scale8_burst4", "burst4", "forecast_scale", None, 8.0,
     "pre-bugfix sub-minute forecast feed (units + tick-clock); superseded by "
     "fc_scale8.0_burst4_v2 -- see results-ledger.md 2026-07-09"),
]

# §2.5 -- what run_44_riders.sh pins for the four ladder runs, and where it says so.
LADDER_RUNS = ["riders:ladder_t400_40", "riders:ladder_t300_30",
               "riders:ladder_t250_25", "riders:ladder_t200_20"]
LADDER_BACKFILL = {
    "lead_s": (60, RIDERS_SH, "32",
               "STARTUP_TIME=60 on the ladder invocation -- the 60-second replica lead the "
               "chapter states (baselines.tex:167)"),
    "window_name": ("burst1", RIDERS_SH, "15,32",
                    "GRID_TRACE=results/grid/traces/grid_burst1_C6.jsonl; num_requests 64,804 "
                    "in every ladder report matches windows.burst1"),
    "tp": (2, RIDERS_SH, "32",
           "AIC_TP=2 on the ladder invocation; decode_gpus_per_worker=2 in every report"),
    "n_replicas": (2, RIDERS_SH, "34",
                   "positional arg 4 of run_replay.sh is WORKERS (run_replay.sh:23); the ladder "
                   "invocation passes 2"),
    "policy": ("reactive", RIDERS_SH, "3",
               "run_44_riders.sh:3 calls this arm the 'reactive planner tightened-targets "
               "ladder', and baselines.tex:170-181 publishes it as the reactive baseline "
               "(SLA planner, variant-B shape). Vocabulary matches runs.policy elsewhere "
               "('reactive', 286 rows)"),
}

# ---------------------------------------------------------------------------
# §2.4 (completion) -- the SAME configuration defect as §2.5, on the sixteen
# non-ladder riders runs: the knee probes and the validation ladder that ARE the
# derivation's inputs carried NULL window_name / lead_s / n_replicas /
# arrival_speedup on provenance.runs. capacity_knee_probe knew the window; runs
# did not, so `runs WHERE window_name='burst1'` silently missed every probe that
# backs closedloop.tex:328-337. Same never-overwrite-a-NULL rule, same visible
# record in runs_config_backfill.
#
# The window identification is not asserted from a file name: it is an arithmetic
# identity on the archived report. num_requests is 64,804 on the burst1 runs and
# 25,639 on the burst4 runs, and those two counts are unique across all 18 rows of
# provenance.windows. duration_ms corroborates independently -- 29,939 s == the
# burst1 span, 11,339 s == the burst4 span, and the three tp2knee durations are the
# burst1 span divided by exactly their arrival_speedup (29,939.3/1.25 = 23,951.4;
# /1.5 = 19,959.5; /2 = 14,969.7). Check C408 re-derives all of it.
_EV_REPORT = "num_requests + duration_ms vs provenance.windows"
_EV_LEDGER = "182"

_PROBE_WINDOW = {
    "fc_lead60": "burst1", "fc_lead90": "burst1", "fc_lead120": "burst1",
    "fc_lead300": "burst1", "fc_lead60_s1": "burst1",
    "fc_scale4.64": "burst1", "fc_scale6.22": "burst1", "fc_scale6.22_regress": "burst1",
    "tp2knee_s1.25": "burst1", "tp2knee_s1.5": "burst1", "tp2knee_s2": "burst1",
    "fc_scale6.22_burst4": "burst4", "fc_scale6.22_burst4_v2": "burst4",
    "fc_scale7.0_burst4_v2": "burst4", "fc_scale8.0_burst4_v2": "burst4",
    "fc_scale8_burst4": "burst4",
}

# STARTUP_TIME (= runs.lead_s). Pinned per-run by run_44_riders.sh:41-51 for the
# fc_lead arm; pinned at 60 for the whole validation arm by results-ledger.md:182
# ("fc runs FORECAST_REQ_SCALE in {4.64,6.22,7.0,8.0}, STARTUP_TIME=60").
# DELIBERATELY ABSENT: tp2knee_*. No archived file states a startup_time for the
# three knee probes, and the knee is a fixed-N replay where it would not bind
# anyway. Guessing it would be inventing a dimension, so those stay NULL.
_PROBE_LEAD = {
    "fc_lead60": (60, RIDERS_SH, "41-51"), "fc_lead90": (90, RIDERS_SH, "41-51"),
    "fc_lead120": (120, RIDERS_SH, "41-51"), "fc_lead300": (300, RIDERS_SH, "41-51"),
    "fc_lead60_s1": (60, RIDERS_SH, "41-51"),
    "fc_scale4.64": (60, LEDGER_MD, _EV_LEDGER),
    "fc_scale6.22": (60, LEDGER_MD, _EV_LEDGER),
    "fc_scale6.22_regress": (60, LEDGER_MD, _EV_LEDGER),
    "fc_scale6.22_burst4": (60, LEDGER_MD, _EV_LEDGER),
    "fc_scale6.22_burst4_v2": (60, LEDGER_MD, _EV_LEDGER),
    "fc_scale7.0_burst4_v2": (60, LEDGER_MD, _EV_LEDGER),
    "fc_scale8.0_burst4_v2": (60, LEDGER_MD, _EV_LEDGER),
    "fc_scale8_burst4": (60, LEDGER_MD, _EV_LEDGER),
}

# The arrival-clock speed-up that defines the three knee rungs. Already a column on
# capacity_knee_probe; mirrored onto runs so the offered-rate mapping is reachable
# from the run row, and cross-checked against the report duration by C408/C409.
_PROBE_SPEEDUP = {"tp2knee_s1.25": 1.25, "tp2knee_s1.5": 1.5, "tp2knee_s2": 2.0}


def _prep(path, idx, reload):
    if ic.is_worktree(path):
        return None
    sha, nbytes = ic.file_meta(path)
    if not reload and idx.get(path) == sha:
        return None
    return sha, nbytes


def _run(*stmts):
    sql = ";\n".join(s for s in stmts if s)
    if sql:
        db.run_sql(sql)


def _q(v):
    return ic.lit(v)


# ===========================================================================
# §2.4 (input 1) -- planner belief ticks
# ===========================================================================
def _load_belief(idx, reload):
    nf = nr = 0
    if not os.path.isdir(RIDERS):
        print(f"[{KIND}] MISSING {RIDERS}", file=sys.stderr, flush=True)
        return nf, nr
    for name in sorted(os.listdir(RIDERS)):
        if not name.endswith(".log"):
            continue
        path = os.path.join(RIDERS, name)
        prep = _prep(path, idx, reload)
        if prep is None:
            continue
        sha, nbytes = prep
        run_id = run_id_of(path)
        with open(path, errors="replace") as f:
            text = f.read()
        rows = []
        for i, m in enumerate(TICK_RE.finditer(text)):
            eng = float(m.group(2))
            rows.append({"source_log": path, "tick_idx": i, "run_id": run_id,
                         "agg_rps": float(m.group(1)), "engine_rps": eng,
                         "is_degenerate": eng > DEGENERATE_ENGINE_RPS})
        # The logs are not per-file run artifacts in the collision-guard sense (a .log
        # and its .report.json share a stem, which the guard already allows), but route
        # through it anyway so a future rename cannot silently clobber.
        ic.guard_run_collision(run_id, path, idx, table="capacity_belief_sample")
        stmts = [f"delete from provenance.capacity_belief_sample where source_log={_q(path)}"]
        for chunk in range(0, len(rows), 2000):
            stmts.append(ic.multi_upsert_sql(
                "capacity_belief_sample",
                ["source_log", "tick_idx", "run_id", "agg_rps", "engine_rps", "is_degenerate"],
                rows[chunk:chunk + 2000], ["source_log", "tick_idx"]))
        stmts.append(ic.ingest_sql(path, sha, KIND, len(rows), run_id, nbytes))
        _run(*stmts)
        nf += 1
        nr += len(rows)
    return nf, nr


def _belief_stats():
    """Median / p10 / p90 of the non-degenerate ticks of BELIEF_LOG, read back from the
    DB so the stored derivation is a function of the stored inputs, not of this process.

    BOTH percentile conventions are returned and BOTH are stored. percentile_disc (order
    statistic) gives 8.45 / 12.83, which is what the published band 8.5-12.8 rounds from;
    percentile_cont (linear interpolation) gives 8.46 / 12.66, whose p90 rounds to 12.7
    instead. The discrepancy is a convention, not a data disagreement, and it is recorded
    rather than resolved by picking the flattering one. It does not propagate: the
    derivation consumes the MEDIAN, which is 10.07 under every convention tested.
    """
    path = os.path.join(RIDERS, BELIEF_LOG)
    r = db.rows(
        "select count(*), "
        "percentile_cont(0.5)  within group (order by engine_rps), "
        "percentile_cont(0.10) within group (order by engine_rps), "
        "percentile_cont(0.90) within group (order by engine_rps), "
        "percentile_disc(0.10) within group (order by engine_rps), "
        "percentile_disc(0.90) within group (order by engine_rps) "
        "from provenance.capacity_belief_sample "
        f"where source_log={_q(path)} and not is_degenerate")
    if not r or not r[0][0] or r[0][0] == "0":
        return None
    n, med, p10, p90, p10d, p90d = r[0]
    return (int(n), float(med), float(p10), float(p90),
            float(p10d), float(p90d), path)


# ===========================================================================
# §2.4 (input 2) -- knee probes
# ===========================================================================
def _load_knee(idx, reload, belief):
    """The riders .report.json files are ALREADY owned by K1 (llm_reports), and
    ingest_log is keyed on file_path, so this loader must not re-register them: doing so
    would overwrite K1's kind and erase the record of who loaded them first. The sha256
    of each file is therefore already archived under K1 and is not re-recorded here.
    Idempotence comes from the upsert on probe_id instead, which is exact -- re-running
    rewrites the same 12 rows with the same values and inserts nothing new.
    """
    nf = nr = 0
    for stem, window, kind, speedup, scale, sup_reason in KNEE_PROBES:
        path = os.path.join(RIDERS, f"{stem}.report.json")
        if not os.path.exists(path):
            print(f"[{KIND}] MISSING {path}", file=sys.stderr, flush=True)
            continue
        if ic.is_worktree(path):
            continue
        probe_id = f"riders:{stem}"
        sha, _nbytes = ic.file_meta(path)
        if not reload:
            stored = db.scalar("select coalesce(source_sha256,'') from "
                               f"provenance.capacity_knee_probe where probe_id={_q(probe_id)}")
            if stored == sha:
                continue
        with open(path) as f:
            d = json.load(f)

        n_rep = 2
        offered = d.get("request_throughput_rps") if kind == "arrival_speedup" else None
        per_rep = offered / n_rep if offered is not None else None
        implied = (belief / scale) if (kind == "forecast_scale" and belief and scale) else None
        ttft, itl = d.get("p99_ttft_ms"), d.get("p99_itl_ms")
        passes = None
        if ttft is not None and itl is not None:
            passes = (ttft <= SLA_TTFT_P99_MS) and (itl <= SLA_ITL_P99_MS)

        row = {
            "probe_id": probe_id, "run_id": run_id_of(path),
            "window_name": window, "probe_kind": kind,
            "arrival_speedup": speedup, "forecast_req_scale": scale,
            "n_replicas": n_rep, "tp": 2,
            "offered_rps": offered, "offered_rps_per_replica": per_rep,
            "implied_r_tail": implied,
            "p99_ttft_ms": ttft, "p99_itl_ms": itl, "gpu_hours": d.get("gpu_hours"),
            "sla_ttft_p99_ms": SLA_TTFT_P99_MS, "sla_itl_p99_ms": SLA_ITL_P99_MS,
            "passes": passes,
            "is_superseded": sup_reason is not None,
            "superseded_reason": sup_reason,
            "source_path": path, "source_sha256": sha,
        }
        _run(ic.upsert_sql("capacity_knee_probe", row, "probe_id"))
        nf += 1
        nr += 1
    return nf, nr


# ===========================================================================
# §2.4 (output) -- the derivation
# ===========================================================================
def _load_derivation(belief_stats, inputs_changed):
    """Compute the derivation FROM the two input tables and store it. Returns rows written.

    Recomputed only when an input actually changed (or the table is empty), so a re-run
    with no new bytes writes nothing. The derivation is a pure function of
    capacity_belief_sample + capacity_knee_probe -- it is stored for convenience, and
    checks C401-C403 assert that storing it changed nothing.
    """
    if belief_stats is None:
        print(f"[{KIND}] belief samples absent -- derivation skipped", file=sys.stderr)
        return 0
    if not inputs_changed and db.scalar(
            "select count(*) from provenance.capacity_derivation") != "0":
        return 0
    n, med, p10, p90, p10d, p90d, blog = belief_stats

    # burst1: measured. r_tail = the largest passing per-replica offered rate on the
    # arrival-speedup ladder.
    r = db.rows(
        "select max(offered_rps_per_replica) from provenance.capacity_knee_probe "
        "where window_name='burst1' and probe_kind='arrival_speedup' and passes "
        "and not is_superseded")
    b1_rtail = float(r[0][0]) if r and r[0][0] else None

    # burst4: bracketed by the forecast-scale ladder. Upper bound = the smallest
    # implied_r_tail that PASSES; lower bound = the largest that also passes at a
    # coarser scale. Concretely: FAIL at implied 1.6190 bounds from above, the two
    # PASSes at 1.4386 and 1.2588 sit inside.
    r = db.rows(
        "select min(implied_r_tail) filter (where passes), "
        "       max(implied_r_tail) filter (where passes), "
        "       min(implied_r_tail) filter (where not passes) "
        "  from provenance.capacity_knee_probe "
        " where window_name='burst4' and probe_kind='forecast_scale' and not is_superseded")
    b4_lo = float(r[0][0]) if r and r[0][0] else None
    b4_hi = float(r[0][1]) if r and r[0][1] else None

    rows = []
    if b1_rtail:
        rows.append({
            "derivation_id": "riders44:burst1", "window_name": "burst1",
            "belief_rps": med, "belief_p10_rps": p10, "belief_p90_rps": p90,
            "belief_n_ticks": n, "belief_source_log": blog,
            "belief_p10_disc_rps": p10d, "belief_p90_disc_rps": p90d,
            "r_tail_rps": b1_rtail, "r_tail_lo_rps": None, "r_tail_hi_rps": None,
            "r_tail_method": "measured", "r_tail_basis": "measured",
            "implied_scale": med / b1_rtail, "adopted_scale": 8.0,
            "margin_over_knee": 8.0 / (med / b1_rtail), "is_binding": False,
            "thesis_location": "closedloop.tex:331",
            "published_text": "1.62 req/s on burst1's mix",
            "rationale":
                "r_tail measured directly: arrival-speedup ladder at N=2 TP2 replicas. "
                "s=1.5 offers 3.2466 req/s pool-wide = 1.6233 per replica and PASSES "
                "(TTFT p99 905.86 ms); the next rung s=2.0 offers 2.1643 per replica and "
                "FAILS (1078.61 ms). The knee is therefore the s=1.5 rate. burst1 is NOT "
                "the binding window -- burst4 is looser and sets the fleet scale.",
            "source_paths": [os.path.join(RIDERS, "tp2knee_s1.5.report.json"),
                             os.path.join(RIDERS, "tp2knee_s2.report.json")],
        })
    if b4_lo and b4_hi:
        rows.append({
            "derivation_id": "riders44:burst4", "window_name": "burst4",
            "belief_rps": med, "belief_p10_rps": p10, "belief_p90_rps": p90,
            "belief_n_ticks": n, "belief_source_log": blog,
            "belief_p10_disc_rps": p10d, "belief_p90_disc_rps": p90d,
            "r_tail_rps": None, "r_tail_lo_rps": b4_lo, "r_tail_hi_rps": b4_hi,
            "r_tail_method": "bracketed", "r_tail_basis": "hi",
            "implied_scale": med / b4_hi, "adopted_scale": 8.0,
            "margin_over_knee": 8.0 / (med / b4_hi), "is_binding": True,
            "thesis_location": "closedloop.tex:331-337",
            "published_text": "bracketed in [1.26, 1.44] on burst4, the binding mix",
            "rationale":
                "r_tail is NOT measured on burst4 -- the forecast-scale ladder only "
                "brackets it. scale 6.22 asserts r_tail=1.6190 and FAILS (1103.91 ms), "
                "bounding it from above; 7.0 asserts 1.4386 and PASSES (792.01 ms); 8.0 "
                "asserts 1.2588 and PASSES (753.79 ms). Hence [1.2588, 1.4386] -> the "
                "published [1.26, 1.44]. The adopted scale 8.0 = belief/1.2588 sits at the "
                "conservative end of the bracket, 1.14x the strictly-required 7.0. That "
                "~14% margin is policy: r_tail is mix-dependent, and the same config "
                "replayed twice moves the tail ~4% (fc_scale6.22 932.35 ms vs "
                "fc_scale6.22_regress 968.42 ms).",
            "source_paths": [os.path.join(RIDERS, "fc_scale6.22_burst4_v2.report.json"),
                             os.path.join(RIDERS, "fc_scale7.0_burst4_v2.report.json"),
                             os.path.join(RIDERS, "fc_scale8.0_burst4_v2.report.json")],
        })
        rows.append({
            "derivation_id": "riders44:fleet", "window_name": None,
            "belief_rps": med, "belief_p10_rps": p10, "belief_p90_rps": p90,
            "belief_n_ticks": n, "belief_source_log": blog,
            "belief_p10_disc_rps": p10d, "belief_p90_disc_rps": p90d,
            "r_tail_rps": None, "r_tail_lo_rps": b4_lo, "r_tail_hi_rps": b4_hi,
            "r_tail_method": "bracketed", "r_tail_basis": "lo",
            "implied_scale": med / b4_lo, "adopted_scale": 8.0,
            "margin_over_knee": 8.0 / (med / b4_lo), "is_binding": True,
            "thesis_location": "closedloop.tex:328-337",
            "published_text":
                "x8 = belief/1.26 = binding-window knee + ~14% capacity margin",
            "rationale":
                "The deployed FORECAST_REQ_SCALE. scale = belief / r_tail with belief = "
                "10.07 req/s per TP2 replica (median of %d non-degenerate planner ticks in "
                "%s) and r_tail taken at the LOWER end of the binding window's bracket: "
                "10.07/1.2588 = 8.0. margin_over_knee is 1.0 against that conservative "
                "choice by construction; measured against the strictly-required 7.0 it is "
                "1.14. This row exists so the headline knob is one SELECT away from its "
                "inputs, not so it adds information."
                % (n, BELIEF_LOG),
            "source_paths": [os.path.join(RIDERS, BELIEF_LOG),
                             os.path.join(RIDERS, "fc_scale8.0_burst4_v2.report.json")],
        })

    if not rows:
        return 0
    cols = ["derivation_id", "window_name", "belief_rps", "belief_p10_rps", "belief_p90_rps",
            "belief_n_ticks", "belief_source_log", "belief_p10_disc_rps",
            "belief_p90_disc_rps", "r_tail_rps", "r_tail_lo_rps",
            "r_tail_hi_rps", "r_tail_method", "r_tail_basis", "implied_scale", "adopted_scale",
            "margin_over_knee", "is_binding", "thesis_location", "published_text",
            "rationale", "source_paths"]
    _run(ic.multi_upsert_sql("capacity_derivation", cols, rows, "derivation_id"))
    return len(rows)


# ===========================================================================
# §2.5 -- ladder configuration backfill
# ===========================================================================
def _backfill_one(run_id, col, val, ev_path, ev_line, why):
    """NULL -> value only. A non-NULL current value aborts rather than overwrites.

    Returns 1 if it wrote, 0 if the value was already there (idempotent re-run).
    """
    cur = db.scalar(f"select coalesce({col}::text,'') from provenance.runs "
                    f"where run_id={_q(run_id)}")
    if cur == "":
        pass  # NULL (or absent run) -- safe to write
    elif cur == str(val) or (_is_num(cur) and _is_num(val) and float(cur) == float(val)):
        return 0  # already backfilled; idempotent no-op
    else:
        raise RuntimeError(
            f"REFUSING to overwrite provenance.runs.{col} on {run_id}: "
            f"stored {cur!r}, backfill wanted {val!r}. An archived non-NULL "
            f"dimension is a measurement; investigate before proceeding.")
    _run(f"update provenance.runs set {col}={_q(val)} "
         f"where run_id={_q(run_id)} and {col} is null",
         ic.upsert_sql("runs_config_backfill",
                       {"run_id": run_id, "column_name": col, "old_value": None,
                        "new_value": str(val), "evidence_path": ev_path,
                        "evidence_line": ev_line, "rationale": why},
                       ["run_id", "column_name"]))
    return 1


def _is_num(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _load_ladder_config(idx, reload):
    nrows = 0
    for run_id in LADDER_RUNS:
        for col, (val, ev_path, ev_line, why) in LADDER_BACKFILL.items():
            nrows += _backfill_one(run_id, col, val, ev_path, ev_line, why)
    return nrows


# ===========================================================================
# §2.4 (completion) -- configuration backfill on the sixteen probe/validation runs
# ===========================================================================
def _load_probe_config(idx, reload):
    """Give the derivation's INPUT runs the dimensions the derivation is indexed by.

    Without this, capacity_knee_probe.window_name and provenance.runs.window_name
    disagree by omission and the knee ladder is unreachable from a window query.
    Every write is NULL-only and lands in runs_config_backfill with its evidence.
    """
    nrows = 0
    for stem, window in sorted(_PROBE_WINDOW.items()):
        run_id = f"riders:{stem}"
        report = os.path.join(RIDERS, f"{stem}.report.json")

        nrows += _backfill_one(
            run_id, "window_name", window, report, _EV_REPORT,
            f"num_requests and duration_ms in {stem}.report.json match "
            f"provenance.windows.{window} and no other window; corroborated by "
            f"capacity_knee_probe.window_name where a probe row exists. Verified by C408.")

        # n_replicas: run_replay.sh positional arg 4 (WORKERS). The fc arm passes 2 in
        # run_44_riders.sh:49; the knee/validation arm is recorded as "TP2 N2" at
        # results-ledger.md:182. Corroborated by capacity_knee_probe.n_replicas=2.
        if stem.startswith("fc_lead"):
            ev_p, ev_l = RIDERS_SH, "49"
        else:
            ev_p, ev_l = LEDGER_MD, _EV_LEDGER
        nrows += _backfill_one(
            run_id, "n_replicas", 2, ev_p, ev_l,
            "run_replay.sh:23 -- positional arg 4 is WORKERS; this arm runs N=2 TP2 "
            "replicas. This is the denominator of offered_rps_per_replica, so the "
            "derivation is not recomputable without it.")

        if stem in _PROBE_LEAD:
            val, ev_p, ev_l = _PROBE_LEAD[stem]
            nrows += _backfill_one(
                run_id, "lead_s", val, ev_p, ev_l,
                "STARTUP_TIME on this invocation -- the replica lead. The whole point of "
                "the riders arm is that the closed loop is measured under a REALISTIC "
                "lead, so a NULL here made the runs look like the L=0 runs they "
                "supersede.")

        if stem in _PROBE_SPEEDUP:
            nrows += _backfill_one(
                run_id, "arrival_speedup", _PROBE_SPEEDUP[stem], LEDGER_MD, _EV_LEDGER,
                "run_replay.sh --arrival-speedup-ratio (results-ledger.md:182). Independently "
                "confirmed by the report itself: duration_ms is the burst1 span divided by "
                "exactly this factor. This IS the knee ladder's x-axis. Verified by C409.")
    return nrows


def _load_ladder_command(idx, reload):
    """Record the generating command in grid_command + a ledger_entry, per §2.5."""
    if not os.path.exists(RIDERS_SH):
        print(f"[{KIND}] MISSING {RIDERS_SH}", file=sys.stderr, flush=True)
        return 0, 0
    prep = _prep(RIDERS_SH, idx, reload)
    if prep is None:
        return 0, 0
    sha, nbytes = prep
    with open(RIDERS_SH, errors="replace") as f:
        script = f.read()

    cmds = []
    for run_id in LADDER_RUNS:
        stem = run_id.split(":", 1)[1]
        t = stem[len("ladder_t"):].split("_")
        cmds.append({
            "log_path": os.path.join(RIDERS, f"{stem}.log"),
            "grid_run_id": run_id, "stage": "riders_ladder", "artifact_stem": stem,
            "window_name": "burst1", "encoder_workers": 6, "tp": 2, "llm_workers": 2,
            "variant": f"sla_targets_ttft{t[0]}_itl{t[1]}",
            "cmd": ("RUST_LOG=warn AIC_TP=2 STARTUP_TIME=60 "
                    "REPLAY_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python AIC_VER=0.19.0 "
                    "bash /home/gio/tese/simulation/run_replay.sh "
                    "/home/gio/tese/simulation/results/grid/traces/grid_burst1_C6.jsonl aic "
                    f"{RIDERS}/{stem}.report.json 2 "
                    f"--planner-config {RIDERS}/planner_{stem}.json"),
            "cwd": "/home/gio/tese",
            "log_bytes": (os.path.getsize(os.path.join(RIDERS, f"{stem}.log"))
                          if os.path.exists(os.path.join(RIDERS, f"{stem}.log")) else None),
        })
    cols = ["log_path", "grid_run_id", "stage", "artifact_stem", "window_name",
            "encoder_workers", "tp", "llm_workers", "variant", "cmd", "cwd", "log_bytes"]

    ledger = {
        "section": "ADJUDICATION §2.5",
        "name": "riders ladder configuration re-ingest",
        "entry_date": "2026-07-20",
        "artifact_paths": [os.path.join(RIDERS, f"{r.split(':')[1]}.report.json")
                           for r in LADDER_RUNS],
        "command": "bash /home/gio/tese/simulation/run_44_riders.sh  (ladder arm)",
        "feeds": "baselines.tex:168,181 tab:base-ladder -- the reactive target ladder on "
                 "burst1 under a 60 s replica lead",
        "supersedes": "the NULL lead_s / window_name / tp on the four riders:ladder_* rows",
        "result_note":
            "gpu_hours 18.638/19.199/19.413/20.379 (t400_40 -> t200_20) reproduce the "
            "published 18.6->20.4; TTFT p99 1619.61/1616.60/1615.99/1615.49 reproduce "
            "1,616-1,620. A 10% spend increase moves the tail by 4 ms. Configuration is "
            "backfilled from run_44_riders.sh, not from the reports, and is recorded in "
            "provenance.runs_config_backfill.",
        "run_id": LADDER_RUNS[0],
        "raw": script[:4000],
    }
    _run(ic.multi_upsert_sql("grid_command", cols, cmds, "log_path"),
         # ledger_entry's key is a serial, so re-running would append duplicates;
         # scope a delete to THIS loader's section first. Nothing else writes it.
         "delete from provenance.ledger_entry where section='ADJUDICATION §2.5'",
         _insert_ledger_sql(ledger),
         ic.ingest_sql(RIDERS_SH, sha, KIND, len(cmds) + 1, LADDER_RUNS[0], nbytes))
    return 1, len(cmds) + 1


def _insert_ledger_sql(d):
    cols = [c for c in d]
    vals = ",".join(ic.lit(d[c]) for c in cols)
    return f"insert into provenance.ledger_entry ({','.join(cols)}) values ({vals})"


# ===========================================================================
# §2.11 (a) -- AIC speed-of-light fallback bound
# ===========================================================================
def _load_phaseb(idx, reload):
    if not os.path.exists(PHASEB):
        print(f"[{KIND}] MISSING {PHASEB}", file=sys.stderr, flush=True)
        return 0, 0
    prep = _prep(PHASEB, idx, reload)
    if prep is None:
        return 0, 0
    sha, nbytes = prep
    with open(PHASEB, errors="replace") as f:
        txt = f.read()

    def grab(pat, cast=float):
        m = re.search(pat, txt)
        return cast(m.group(1)) if m else None

    sol = grab(r"SOL\s*->\s*([0-9.]+) ms")
    meas = grab(r"rtx_5090 measured silicon, same shape: ([0-9.]+) ms")
    if sol is None or meas is None:
        raise RuntimeError(f"{PHASEB}: expected SOL and measured lines not found; "
                           "the artifact format changed -- fix the parser, do not guess.")
    ratio = meas / sol

    scope = "encoder_attention_b1_s784_n16_d72_bf16"
    rows = [
        ("sol_pred_ms", sol, None),
        ("measured_silicon_ms", meas, None),
        ("measured_over_sol_x", ratio, None),
        ("system", None, "rtx_pro_6000_server"),
        ("measured_system", None, "rtx_5090"),
        ("framework", None, "vllm 0.22.0"),
        ("silicon_mode_result", None, "PerfDataNotAvailableError"),
        ("hybrid_mode_result", None, "EmpiricalNotImplementedError"),
        ("empirical_mode_result", None, "EmpiricalNotImplementedError"),
        ("thesis_location", None, "intro.tex:311"),
        ("note", None,
         "AIC has no usable encoder-timing fallback on a system without "
         "encoder_attention_perf.parquet: SILICON and HYBRID hard-fail and SOL is "
         "~5.9x optimistic. Support-matrix rows PASS only because they pass no image "
         "dimensions (num_images_per_request=0), so the ViT is never costed."),
    ]
    payload = [{"source_path": PHASEB, "scope": scope, "metric": m,
                "value_num": vn, "value_text": vt} for m, vn, vt in rows]
    _run(f"delete from provenance.collector_scalar where source_path={_q(PHASEB)}",
         ic.multi_upsert_sql("collector_scalar",
                             ["source_path", "scope", "metric", "value_num", "value_text"],
                             payload, ["source_path", "scope", "metric"]),
         ic.ingest_sql(PHASEB, sha, KIND, len(payload), None, nbytes))
    return 1, len(payload)


# ===========================================================================
# §2.11 (b) -- promote the fabric dimension
# ===========================================================================
def _promote_handoff():
    """Backfill handoff_gbps / handoff_rtt_ms from the metrics jsonb. NULL -> value only."""
    before = db.scalar("select count(*) from provenance.encoder_run_summary "
                       "where handoff_gbps is null")
    _run("update provenance.encoder_run_summary "
         "set handoff_gbps = (metrics->>'handoff_gbps')::double precision "
         "where handoff_gbps is null and metrics ? 'handoff_gbps'",
         "update provenance.encoder_run_summary "
         "set handoff_rtt_ms = (metrics->>'handoff_rtt_ms')::double precision "
         "where handoff_rtt_ms is null and metrics ? 'handoff_rtt_ms'")
    after = db.scalar("select count(*) from provenance.encoder_run_summary "
                      "where handoff_gbps is null")
    return int(before) - int(after)


# ===========================================================================
# §2.11 (c) -- factoring invariance probe
# ===========================================================================
def _load_factoring(idx, reload):
    if not os.path.exists(PHASE2_MD):
        print(f"[{KIND}] MISSING {PHASE2_MD}", file=sys.stderr, flush=True)
        return 0, 0
    prep = _prep(PHASE2_MD, idx, reload)
    if prep is None:
        return 0, 0
    sha, nbytes = prep

    # The contemporaneous note records the probe verbally: "(batch_size=1, n=64) == (64,1)
    # == every factoring, delta 0.000000 ms". The published thesis pair f(1)=8.162 /
    # f(64)=316.369 comes from the CURRENT AIC data version and is independently in
    # provenance.collector_encoder_fn.aic_pred_ms; the note's 7.822/314.498 is the earlier
    # version. Both are stored, labelled, and neither is silently preferred.
    ref64 = db.scalar(
        "select max(aic_pred_ms) from provenance.collector_encoder_fn "
        "where image_px=448 and n_images=64 and aic_pred_ms is not null")
    ref1 = db.scalar(
        "select max(aic_pred_ms) from provenance.collector_encoder_fn "
        "where image_px=448 and n_images=1 and aic_pred_ms is not null")
    f64 = float(ref64) if ref64 else None
    f1 = float(ref1) if ref1 else None

    ev = f"{PHASE2_MD}:106-109"
    rows = []
    for i, (b, ipr) in enumerate([(1, 64), (2, 32), (4, 16), (8, 8), (16, 4), (32, 2), (64, 1)]):
        rows.append({
            "probe_id": f"aic448:n64:b{b}x{ipr}", "image_px": 448,
            "batch_size": b, "images_per_request": ipr, "total_images": 64,
            "predicted_ms": f64, "delta_vs_ref_ms": 0.0,
            "is_reference": (b == 1 and ipr == 64),
            "evidence_path": PHASE2_MD, "evidence_line": "106-109",
            "note": ("factoring invariance: identical to the microsecond across every "
                     "(batch, images-per-request) split of 64 images. predicted_ms is the "
                     "CURRENT AIC prediction (collector_encoder_fn.aic_pred_ms at 448px, "
                     "n=64), which is the value published at twopool.tex:122; the "
                     "contemporaneous note recorded 314.498 ms under an earlier AIC data "
                     "version. The invariance -- delta 0.000000 -- holds under both."),
        })
    rows.append({
        "probe_id": "aic448:n1:b1x1", "image_px": 448, "batch_size": 1,
        "images_per_request": 1, "total_images": 1, "predicted_ms": f1,
        "delta_vs_ref_ms": 0.0, "is_reference": True,
        "evidence_path": PHASE2_MD, "evidence_line": "109",
        "note": ("single-image floor f(1). Published 8.162 ms (twopool.tex:121); the "
                 "contemporaneous note recorded 7.822 ms under the earlier AIC data "
                 "version. With f(64) this gives 316.369/64 = 4.94 ms/img amortized and a "
                 "1.65x throughput gain, both as published."),
    })
    cols = ["probe_id", "image_px", "batch_size", "images_per_request", "total_images",
            "predicted_ms", "delta_vs_ref_ms", "is_reference", "evidence_path",
            "evidence_line", "note"]
    _run(ic.multi_upsert_sql("encoder_factoring_probe", cols, rows, "probe_id"),
         ic.ingest_sql(PHASE2_MD, sha, KIND, len(rows), None, nbytes))
    _ = ev
    return 1, len(rows)


# ===========================================================================
def load_group_c(idx, reload):
    """K31 entrypoint. Returns (files_loaded, rows_loaded)."""
    nf = nr = 0

    f, r = _load_belief(idx, reload)
    nf += f
    nr += r

    stats = _belief_stats()
    belief = stats[1] if stats else None

    f, knee_rows = _load_knee(idx, reload, belief)
    nf += f
    nr += knee_rows

    nr += _load_derivation(stats, inputs_changed=bool(r or knee_rows))
    nr += _load_ladder_config(idx, reload)
    nr += _load_probe_config(idx, reload)

    f, r = _load_ladder_command(idx, reload)
    nf += f
    nr += r

    f, r = _load_phaseb(idx, reload)
    nf += f
    nr += r

    nr += _promote_handoff()

    f, r = _load_factoring(idx, reload)
    nf += f
    nr += r
    return nf, nr


def main():
    reload = "--reload" in sys.argv
    idx = ic.load_ingest_index()
    nf, nr = load_group_c(idx, reload)
    print(f"[{KIND}   group_c         ] files={nf:5d} rows={nr:13,d}", flush=True)


if __name__ == "__main__":
    main()
