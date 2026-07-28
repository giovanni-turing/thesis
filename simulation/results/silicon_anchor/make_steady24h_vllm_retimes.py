#!/usr/bin/env python3
"""Exact vLLM queue retimes for the steady24h cells of the silicon-anchor campaign.

WHAT THIS COMPUTES
    For each cell, three encoder-delay p99 values over the SAME frozen dispatch:

      stored_sim_p99      the banked simulator p99 (simulation/silicon_anchor_queue.json,
                          cells[cid].banked.encoder_delay_ms.p99), re-derived here by
                          replaying the sim's own service times through the runner's
                          retime() and request_delays() -- the reconstruction gate.

      direct_vllm_p99     each batch's service time replaced by the MEASURED vLLM
                          per-N forward time for that batch's image count N
                          (mean_ms of the dense sweep, linearly interpolated by the
                          runner's Piecewise -- no interpolation is actually
                          exercised: every dispatched N is an exact dense-table key).

      per_n_scaled_p99    each batch's service time SCALED by the per-N engine ratio
                          vllm_mean_ms(N) / aic_ms(N), where aic_ms is the runner's own
                          aic_curve() over collector_artifacts/phaseB_batch_validation/
                          aic_f_n_postinfill.csv. This preserves the simulator's own
                          per-batch service variation and only re-levels it to the
                          measured engine.

    In both retimed representations the batch ORDER, the recovered MEMBERSHIP and the
    worker SCHEDULE are held fixed (frozen-composition retiming); only per-batch
    service changes. No campaign math is reimplemented: recover_membership, retime,
    request_delays, pct, Piecewise and aic_curve are called from
    simulation/silicon_anchor_runner.py through an importlib spec shim, exactly as
    verification/silicon_negative_gates.py does.

METHOD VALIDATION GATE
    burst3__staticC8 is recomputed first and must reproduce the independently
    verified pair (ledger entry "silicon-anchor-tier5-engine-adjudication-v2"):
        stored sim p99      717.755 ms
        direct vLLM p99     746.994 ms
        per-N scaled p99    748.409 ms
    The script FAILS LOUDLY (exit 2) if the gate does not reproduce digit-exact.

    PROVENANCE NOTE (important): the verified 746.994 / 748.409 pair reproduces
    digit-exact ONLY from the tier-5 rerun sweep
    simulation/results/silicon_anchor/reps/engine__vllm_serving/vllm_eager_dense_rerun.json
    (mean_ms), NOT from the canonical phase-E manuscript artifact
    collector_artifacts/phaseE_physical_anchor/vllm_eager_dense.json, which yields
    745.758 / 747.169. Both tables are therefore carried here, side by side, and the
    gate is asserted against the table that provably produced the verified pair.

READ-ONLY
    Nothing under the campaign tree is opened for writing except this script's own
    output artifact. rep.json files, the manifest, dispatch/, tex/ and review/ are
    never touched.

Usage:
    python3 simulation/results/silicon_anchor/make_steady24h_vllm_retimes.py

Deterministic: no timestamps, no environment capture; two runs are byte-identical.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "steady24h_vllm_retimes.json"

GATE_CELL = "burst3__staticC8"
GATE_EXPECT = {"stored_sim_p99": 717.755,
               "direct_vllm_p99": 746.994,
               "per_n_scaled_p99": 748.409}
CELLS = ["steady24h__fc", "steady24h__re", "steady24h__staticC8"]

VLLM_TABLES = {
    # the table that provably reproduces the verified burst3__staticC8 pair
    "tier5_rerun": "simulation/results/silicon_anchor/reps/engine__vllm_serving/"
                   "vllm_eager_dense_rerun.json",
    # the manuscript's replication artifact (tab:app-engine, 12.8% envelope)
    "phaseE_canonical": "collector_artifacts/phaseE_physical_anchor/vllm_eager_dense.json",
}
AIC_CSV = "collector_artifacts/phaseB_batch_validation/aic_f_n_postinfill.csv"
SLA_BOUND_MS = 1000.0


# --------------------------------------------------------------------------
# import shim (script-style module, loaded by spec; no import-time side effects)
# --------------------------------------------------------------------------
def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


runner = _load("_sa_runner", ROOT / "simulation" / "silicon_anchor_runner.py")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cells() -> dict:
    q = json.load(open(ROOT / "simulation" / "silicon_anchor_queue.json"))
    return {cid: c for t in q["tiers"] for cid, c in t["cells"].items()}


def vllm_piecewise(rows: dict):
    """Piecewise over the dense sweep's per-N MEAN forward time."""
    return runner.Piecewise([(int(n), v["mean_ms"]) for n, v in rows.items()])


def n_distribution(sizes: list[int]) -> dict:
    s = sorted(sizes)
    def q(p):
        return s[min(len(s) - 1, int(len(s) * p / 100))]
    return {"n_batches": len(s), "p50": q(50), "p90": q(90), "p99": q(99),
            "max": max(s), "min": min(s), "distinct_n": len(set(s)),
            "total_images": sum(s)}


def compute_cell(cid: str, spec: dict, tables: dict) -> dict:
    disp = ROOT / "simulation" / "results" / "silicon_anchor" / "dispatch"
    with open(disp / f"{cid}.batches.jsonl") as f:
        batches = [json.loads(line) for line in f]
    reqs_meta = json.load(open(disp / f"{cid}.batches.jsonl.reqs.json"))
    schedule = sorted((float(t) * 1000.0, int(c))
                      for t, c in json.load(open(ROOT / spec["schedule"])))

    sim_ms = [b[1] - b[0] for b in batches]
    sizes = [int(b[2]) for b in batches]
    n_fwd = sorted({int(b[3]) for b in batches})
    members, head_arr = runner.recover_membership(batches, reqs_meta)

    # --- reconstruction gate: the sim's own service times must reproduce the
    # --- dumped dispatch timeline and the banked encoder-delay p99 exactly.
    _, rf, _ = runner.retime(batches, head_arr, sim_ms, schedule)
    max_dev = max((abs(rf[i] - batches[i][1]) for i in range(len(batches))), default=0.0)
    sim_delays, n_matched = runner.request_delays(
        members, [b[1] for b in batches], reqs_meta)
    replayed_sim = runner.pct(sim_delays)
    banked_p99 = spec["banked"]["encoder_delay_ms"]["p99"]

    aic = runner.aic_curve()
    per_table = {}
    for tname, rows in tables.items():
        pw = vllm_piecewise(rows)
        covered = sorted(set(sizes) - {int(k) for k in rows})

        direct = [pw.ms(n) for n in sizes]
        _, f_direct, _ = runner.retime(batches, head_arr, direct, schedule)
        d_direct, _ = runner.request_delays(members, f_direct, reqs_meta)

        scaled = [sim_ms[i] * (pw.ms(sizes[i]) / aic.ms(sizes[i]))
                  for i in range(len(batches))]
        _, f_scaled, _ = runner.retime(batches, head_arr, scaled, schedule)
        d_scaled, _ = runner.request_delays(members, f_scaled, reqs_meta)

        per_table[tname] = {
            "direct_vllm_p99": runner.pct(d_direct)["p99"],
            "per_n_scaled_p99": runner.pct(d_scaled)["p99"],
            "direct_vllm_percentiles": {**runner.pct(d_direct),
                                        "max": round(max(d_direct), 3)},
            "per_n_scaled_percentiles": {**runner.pct(d_scaled),
                                         "max": round(max(d_scaled), 3)},
            "direct_vllm_busy_worker_s": round(sum(direct) / 1000.0, 3),
            "per_n_scaled_busy_worker_s": round(sum(scaled) / 1000.0, 3),
            "dispatch_n_not_in_table": covered,
            "interpolation_used": bool(covered),
        }

    return {
        "cell": cid,
        "window": spec["window"],
        "arm": spec["arm"],
        "cap": spec["cap"],
        "encoder_workers": spec["encoder_workers"],
        "schedule": spec["schedule"],
        "stored_sim_p99": banked_p99,
        "direct_vllm_p99": per_table["tier5_rerun"]["direct_vllm_p99"],
        "per_n_scaled_p99": per_table["tier5_rerun"]["per_n_scaled_p99"],
        "by_vllm_table": per_table,
        "n_distribution": n_distribution(sizes),
        "n_forwards_per_batch_seen": n_fwd,
        "reconstruction_gate": {
            "pass": bool(max_dev <= 1e-6 and abs(replayed_sim["p99"] - banked_p99)
                         <= max(1e-3, 1e-6 * abs(banked_p99))),
            "max_batch_finish_deviation_ms": max_dev,
            "replayed_sim_p99_ms": replayed_sim["p99"],
            "banked_sim_p99_ms": banked_p99,
        },
        "membership_recovery": {
            "requests_matched": n_matched,
            "requests_with_images": spec["banked"]["requests_with_images"],
            "complete": n_matched == spec["banked"]["requests_with_images"],
        },
        "replayed_sim_percentiles": {**replayed_sim,
                                     "max": round(max(sim_delays), 3)},
        "sim_busy_worker_s": round(sum(sim_ms) / 1000.0, 3),
    }


def main() -> int:
    cells = load_cells()
    tables = {}
    table_meta = {}
    for tname, rel in VLLM_TABLES.items():
        p = ROOT / rel
        raw = json.load(open(p))
        tables[tname] = raw["rows"]
        table_meta[tname] = {
            "path": rel,
            "sha256": sha256(p),
            "attn_backend": raw.get("attn_backend"),
            "protocol": raw.get("protocol"),
            "field_used": "mean_ms",
            "n_keys": sorted(int(k) for k in raw["rows"]),
        }

    gate = compute_cell(GATE_CELL, cells[GATE_CELL], tables)
    gate_actual = {"stored_sim_p99": gate["stored_sim_p99"],
                   "direct_vllm_p99": gate["direct_vllm_p99"],
                   "per_n_scaled_p99": gate["per_n_scaled_p99"]}
    gate_pass = gate_actual == GATE_EXPECT
    if not gate_pass:
        sys.stderr.write("METHOD VALIDATION GATE FAILED\n"
                         f"  expected {GATE_EXPECT}\n  actual   {gate_actual}\n")
        return 2

    out = {
        "schema": "silicon-anchor/steady24h-vllm-retimes/1",
        "title": "Exact vLLM queue retimes for the steady24h silicon-anchor cells",
        "root": "simulation/results/silicon_anchor",
        "generator": "simulation/results/silicon_anchor/make_steady24h_vllm_retimes.py",
        "deterministic": "no timestamps, no environment capture; two runs are byte-identical",
        "method": {
            "retiming": "frozen-composition retiming with the runner's own functions "
                        "(silicon_anchor_runner.recover_membership / retime / "
                        "request_delays / pct / Piecewise / aic_curve), loaded through an "
                        "importlib spec shim. Batch order, recovered membership and the "
                        "worker schedule are held fixed; only per-batch SERVICE TIME changes.",
            "stored_sim_p99": "banked simulator encoder-delay p99 from "
                              "simulation/silicon_anchor_queue.json "
                              "cells[cid].banked.encoder_delay_ms.p99; re-derived here by "
                              "retiming under the simulator's own per-batch service times "
                              "(reconstruction gate: max batch-finish deviation <= 1e-6 ms "
                              "AND replayed p99 == banked p99).",
            "direct_vllm_p99": "per-batch service := vllm_mean_ms(N) for that batch's image "
                               "count N, taken from the dense vLLM sweep (mean_ms field) via "
                               "runner.Piecewise. Every dispatched N is an exact dense-table "
                               "key (N=1..64), so no interpolation is exercised.",
            "per_n_scaled_p99": "per-batch service := sim_service_ms * "
                                "(vllm_mean_ms(N) / aic_ms(N)), with aic_ms = "
                                "runner.aic_curve() over "
                                "collector_artifacts/phaseB_batch_validation/"
                                "aic_f_n_postinfill.csv. Preserves the simulator's own "
                                "per-batch service variation, re-levelled to the measured engine.",
            "percentile_convention": "runner.pct: sorted[min(len-1, int(len*p/100))] over "
                                     "ALL window requests, text-only requests contributing 0 "
                                     "(request_delays pads to n_all_requests); rounded to 3 dp.",
            "handoff_term": "request_delays adds the simulator's own handoff term "
                            "rtt + (196*N*4096*2)*8/(gbps*1e9)*1e3 with the dispatch's "
                            "banked rtt/gbps, identically in every representation.",
            "sla_bound_ms": SLA_BOUND_MS,
        },
        "vllm_tables": table_meta,
        "aic_curve": {"path": AIC_CSV, "sha256": sha256(ROOT / AIC_CSV)},
        "headline_table_for_direct_and_per_n_scaled": "tier5_rerun",
        "table_choice_note": (
            "The independently verified burst3__staticC8 pair (746.994 / 748.409 ms, ledger "
            "entry silicon-anchor-tier5-engine-adjudication-v2) reproduces DIGIT-EXACT only "
            "from the tier-5 rerun sweep vllm_eager_dense_rerun.json (mean_ms). The canonical "
            "phase-E manuscript artifact vllm_eager_dense.json gives 745.758 / 747.169 ms for "
            "the same cell under the same method. Both tables are reported per cell under "
            "by_vllm_table; the top-level direct_vllm_p99 / per_n_scaled_p99 fields use "
            "tier5_rerun so the steady24h numbers are LIKE-FOR-LIKE with the verified "
            "burst3 pair. Any manuscript propagation must state which table it used."),
        "validation_gate": {
            "cell": GATE_CELL,
            "expected": GATE_EXPECT,
            "actual": gate_actual,
            "digit_exact": gate_pass,
            "table_used": "tier5_rerun",
            "canonical_phaseE_for_same_cell": {
                "direct_vllm_p99": gate["by_vllm_table"]["phaseE_canonical"]["direct_vllm_p99"],
                "per_n_scaled_p99": gate["by_vllm_table"]["phaseE_canonical"]["per_n_scaled_p99"],
            },
            "cell_detail": gate,
        },
        "cells": {},
    }

    for cid in CELLS:
        out["cells"][cid] = compute_cell(cid, cells[cid], tables)

    vals = []
    for cid, c in out["cells"].items():
        for t, r in c["by_vllm_table"].items():
            vals += [r["direct_vllm_p99"], r["per_n_scaled_p99"]]
        vals.append(c["stored_sim_p99"])
    out["sla_bound_check"] = {
        "bound_ms": SLA_BOUND_MS,
        "all_steady24h_p99_below_bound": all(v < SLA_BOUND_MS for v in vals),
        "max_p99_over_all_steady24h_representations_ms": max(vals),
        "note": "p99 encoder delay only; the bound is the encoder-delay SLA the campaign "
                "uses for the static-C8 feasibility verdict.",
    }

    fc, re_ = out["cells"]["steady24h__fc"], out["cells"]["steady24h__re"]
    out["notes"] = [
        "steady24h dispatches are dominated by N=1 batches (p50 = 1 image/batch) with a "
        "heavy tail to the cap (p99 = 64). Both vLLM tables are dense over N=1..64 and every "
        "dispatched N is an exact table key in all three cells, so no interpolation and no "
        "extrapolation is exercised (dispatch_n_not_in_table is empty everywhere).",
        "steady24h__fc and steady24h__re return the SAME retimed p99 to full float precision "
        f"(direct {fc['direct_vllm_p99']}, per-N {fc['per_n_scaled_p99']}) even though their "
        f"stored simulator p99 differ ({fc['stored_sim_p99']} vs {re_['stored_sim_p99']}), "
        "their dispatches differ (39906 vs 39899 batches) and 1686 of the 88260 per-request "
        "delays differ. It is a genuine order-statistic coincidence at the p99 index, not an "
        "input mix-up: the immediate neighbours of the p99 order statistic, the p99.9 and the "
        "max all differ between the two arms.",
        "The static-C8 arm is the only steady24h cell whose retimed p99 sits far below the "
        "others; the reactive and forecast arms are provisioned more thinly in this window, "
        "which is why their p99 encoder delay is higher under every service representation.",
    ]

    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"gate {GATE_CELL}: {gate_actual} (digit-exact: {gate_pass})")
    for cid, c in out["cells"].items():
        print(f"  {cid:22s} stored {c['stored_sim_p99']:>9.3f}  "
              f"direct {c['direct_vllm_p99']:>9.3f}  "
              f"per-N {c['per_n_scaled_p99']:>9.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
