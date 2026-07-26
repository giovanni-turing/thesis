#!/usr/bin/env python3
"""§8.2 -- per-cell (arm x window) independent recomputation dump.

comparator_frontier_summarize.py --mode frontier collapses the evaluation grid
to one row per arm.  The §8.2 deliverable also needs the per-EPISODE encoder
delay p99 and the per-episode provisioned worker-seconds.  This script reuses
the very same recompute() (per-request delay from the emitted mooncake JSONL;
worker-seconds by integrating the schedule) and dumps the full cell table.

Read-only over the replay artifacts; writes one JSON + one text table.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comparator_frontier_summarize as S  # noqa: E402

EPISODES = ["burst1", "burst3", "burst4", "burst5", "steady24h"]


def collect(dirs):
    rows, bad = [], 0
    paths = []
    for d in dirs:
        paths += sorted(glob.glob(os.path.join(d, "*.jsonl"))
                        + glob.glob(os.path.join(d, "*.jsonl.zst")))
    for jsonl in paths:
        d = os.path.dirname(jsonl)
        tag = os.path.basename(jsonl).split(".jsonl")[0]
        sched = os.path.join(d, tag + ".sched.json")
        stats_p = os.path.join(d, tag + ".jsonl.stats.json")
        m = S.TAG_RE.match(tag)
        if not m or not os.path.exists(sched):
            print(f"skip {tag}", file=sys.stderr)
            continue
        r = S.recompute(jsonl, sched, m.group("win"))
        st = json.load(open(stats_p))
        ok = (abs(st["encoder_delay_ms"]["p99"] - r["p99"]) <= 1e-3
              and abs(st["provisioned_worker_seconds"] - r["prov_worker_s"]) <= 0.2)
        if not ok:
            bad += 1
            print(f"MISMATCH {tag}: stats p99={st['encoder_delay_ms']['p99']} "
                  f"recomputed={r['p99']}; stats prov="
                  f"{st['provisioned_worker_seconds']} recomputed={r['prov_worker_s']}",
                  file=sys.stderr)
        raw = m.group("arm")
        if raw.startswith("floorM"):
            arm, size = "warm_floor", int(m.group("m"))
        elif raw.startswith("staticC"):
            arm, size = "static", int(m.group("c"))
        else:
            arm, size = S.ARM_NAME[raw], None
        rows.append({"tag": tag, "dir": d, "window": m.group("win"), "arm": arm,
                     "M": size, "L": int(m.group("L")),
                     "H": int(m.group("H")) if m.group("H") is not None else 3,
                     "stats_agrees": bool(ok), **r})
    return pd.DataFrame(rows), bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", action="append", required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--cost-window", default="aggregate")
    args = ap.parse_args()

    df, bad = collect(args.dir)
    df["armkey"] = df.apply(
        lambda r: f"{r.arm}" + (f"_M{int(r.M)}" if pd.notna(r.M) else "")
                  + (f"_H{int(r.H)}" if r.arm == "oracle" else ""), axis=1)
    pd.set_option("display.width", 250, "display.max_rows", 800)

    p99 = df.pivot_table(index="armkey", columns="window", values="p99")
    ws = df.pivot_table(index="armkey", columns="window", values="prov_worker_s")
    cols = [args.cost_window] + [e for e in EPISODES if e in p99.columns]
    print("\n=== encoder-delay p99 (ms), all requests, per window ===")
    print(p99[cols].to_string())
    print("\n=== provisioned worker-seconds, per window ===")
    print(ws[cols].to_string())

    ep = [e for e in EPISODES if e in p99.columns]
    summ = pd.DataFrame({
        "cost_worker_s_" + args.cost_window: ws[args.cost_window],
        "agg_p99_ms": p99[args.cost_window],
        "worst_ep_p99_ms": p99[ep].max(axis=1),
        "worst_ep": p99[ep].idxmax(axis=1),
        "failed_eps": (p99[ep] >= S.SLA_MS).sum(axis=1),
        "failed_ep_names": p99[ep].apply(
            lambda r: ",".join(sorted(r.index[r >= S.SLA_MS])) or "-", axis=1),
    })
    ref = float(ws.loc["static_M8", args.cost_window]) if "static_M8" in ws.index else float("nan")
    summ["vs_static"] = (summ["cost_worker_s_" + args.cost_window] / ref).round(4)
    summ = summ.sort_values("cost_worker_s_" + args.cost_window)
    print("\n=== §8.2 frontier (cost axis = %s) ===" % args.cost_window)
    print(summ.to_string())
    print(f"\nindependent-recomputation mismatches: {bad}")

    Path(args.json_out).write_text(json.dumps({
        "sla_ms": S.SLA_MS, "cost_window": args.cost_window,
        "static_ref_worker_s": ref, "mismatches": bad,
        "cells": json.loads(df.drop(columns=["armkey"]).to_json(orient="records")),
        "p99_ms": json.loads(p99[cols].to_json()),
        "worker_s": json.loads(ws[cols].to_json()),
        "frontier": json.loads(summ.reset_index().to_json(orient="records")),
    }, indent=1))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
