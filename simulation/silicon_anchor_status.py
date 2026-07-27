#!/usr/bin/env python3
"""Silicon anchor progress: read the append-only manifest and print where the
unbounded run stands. Read-only; safe to run at any time against a live daemon.

  silicon_anchor_status.py            # progress table + headline results
  silicon_anchor_status.py --results  # per-rep measured-vs-simulated detail
  silicon_anchor_status.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

ROOT = Path("/home/gio/tese")
QUEUE = ROOT / "simulation" / "silicon_anchor_queue.json"


def hms(s: float) -> str:
    s = int(s)
    return f"{s//3600:d}h{(s%3600)//60:02d}m" if s >= 3600 else f"{s//60:d}m{s%60:02d}s"


def load(root: Path, name="manifest.jsonl") -> list[dict]:
    p = root / name
    if not p.exists():
        return []
    out = []
    for line in open(p):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    q = json.load(open(QUEUE))
    root = ROOT / q["root"]
    recs = load(root)
    cells: dict[str, dict] = {}
    for t in q["tiers"]:
        for cid, spec in t["cells"].items():
            cells[cid] = dict(spec, tier=t["tier"], min_reps=t["min_reps"])

    done: dict[str, list[dict]] = {c: [] for c in cells}
    fails: dict[str, int] = {c: 0 for c in cells}
    partial: dict[str, dict] = {}
    daemon_up = (root / "daemon.pid").exists()
    pid = int((root / "daemon.pid").read_text()) if daemon_up else None
    if pid is not None:
        daemon_up = Path(f"/proc/{pid}").exists()
    stopped = (root / "STOP").exists()

    for r in recs:
        c = r.get("cell")
        if c not in cells:
            continue
        if r["ev"] == "rep_done":
            done[c].append(r)
        elif r["ev"] in ("rep_fail", "rep_abandoned"):
            fails[c] += 1
        elif r["ev"] in ("segment", "rep_start", "rep_resume", "rep_interrupted"):
            partial[c] = {"rep": r.get("rep"),
                          "batches_done": r.get("batches_done", 0),
                          "n_batches": r.get("n_batches"),
                          "ts": r["ts"], "ev": r["ev"]}
    for c, lst in done.items():
        for r in lst:
            if c in partial and partial[c]["rep"] == r.get("rep"):
                del partial[c]

    dispatch_ok = {}
    for c in cells:
        mp = root / "dispatch" / f"{c}.meta.json"
        if mp.exists():
            try:
                m = json.load(open(mp))
                dispatch_ok[c] = (m["gate"]["pass"], m["dispatch"]["est_measured_busy_s"])
            except Exception:
                dispatch_ok[c] = (False, None)
        else:
            dispatch_ok[c] = (None, None)

    if a.json:
        print(json.dumps({
            "daemon_running": daemon_up, "pid": pid, "stop_file": stopped,
            "manifest_records": len(recs),
            "cells": {c: {"tier": cells[c]["tier"], "min_reps": cells[c]["min_reps"],
                          "reps_done": len(done[c]), "fails": fails[c],
                          "partial": partial.get(c),
                          "dispatch_gate": dispatch_ok[c][0],
                          "est_gpu_s": dispatch_ok[c][1],
                          "wall_s": [d.get("wall_s") for d in done[c]]}
                      for c in cells}}, indent=1))
        return 0

    state = "RUNNING" if daemon_up else ("STOPPED" if stopped else "not running")
    print(f"silicon anchor  |  daemon {state}"
          + (f" (pid {pid})" if daemon_up else "")
          + (f"  |  STOP file present" if stopped else "")
          + f"  |  {len(recs)} manifest records")
    if recs:
        age = time.time() - recs[-1]["ts"]
        print(f"last manifest event: {recs[-1]['ev']} "
              f"{recs[-1].get('cell','')} {hms(age)} ago")
    print()

    total_done = total_need = 0
    hdr = (f"{'cell':22s} {'tier':>4s} {'reps':>9s} {'in-flight':>18s} "
           f"{'est/rep':>9s} {'mean wall':>10s} {'disp':>5s} {'fail':>5s}")
    print(hdr)
    print("-" * len(hdr))
    last_tier = None
    for c, s in cells.items():
        if s["tier"] != last_tier:
            t = next(t for t in q["tiers"] if t["tier"] == s["tier"])
            print(f"  -- tier {t['tier']}: {t['name']}  [{t['order']}, min_reps={t['min_reps']}]")
            last_tier = s["tier"]
        nd, need = len(done[c]), s["min_reps"]
        total_done += min(nd, need)
        total_need += need
        p = partial.get(c)
        inflight = ""
        if p and p.get("n_batches"):
            frac = 100.0 * (p.get("batches_done") or 0) / p["n_batches"]
            inflight = f"rep{p['rep']} {p.get('batches_done',0)}/{p['n_batches']} ({frac:.0f}%)"
        walls = [d["wall_s"] for d in done[c] if d.get("wall_s")]
        est = dispatch_ok[c][1]
        print(f"{c:22s} {s['tier']:4d} {nd:4d}/{need:<4d} {inflight:>18s} "
              f"{(hms(est) if est else '-'):>9s} "
              f"{(hms(statistics.fmean(walls)) if walls else '-'):>10s} "
              f"{({True:'ok',False:'FAIL',None:'-'}[dispatch_ok[c][0]]):>5s} {fails[c]:5d}")
    print("-" * len(hdr))
    print(f"tiers 1-{max(t['tier'] for t in q['tiers'])} at min_reps: "
          f"{total_done}/{total_need} reps banked ({100.0*total_done/total_need:.1f}%)")

    banked_s = sum(d.get("wall_s") or 0 for c in cells for d in done[c])
    remaining = sum((dispatch_ok[c][1] or 0) * max(0, cells[c]["min_reps"] - len(done[c]))
                    for c in cells)
    print(f"GPU time banked: {hms(banked_s)}   |   remaining to min_reps (est): {hms(remaining)}")

    if a.results:
        print("\nper-rep measured vs simulated")
        h = (f"{'cell':22s} {'rep':>4s} {'ratio p50':>10s} {'ratio mean':>11s} "
             f"{'meas busy':>10s} {'sim busy':>9s} {'retimed p99':>12s} {'sim p99':>10s} "
             f"{'ovh%':>6s}")
        print(h)
        print("-" * len(h))
        for c in cells:
            for d in sorted(done[c], key=lambda r: r.get("rep", 0)):
                sm = d.get("summary") or {}
                rr = sm.get("per_batch_ratio_measured_over_sim") or {}
                rt = (sm.get("retimed_encoder_delay_ms") or {}).get("p99")
                sp = (sm.get("banked_sim_encoder_delay_ms") or {}).get("p99")
                ovh = sm.get("overhead_frac")
                r50, rmean = rr.get("p50"), rr.get("mean")
                mb, sb = sm.get("measured_busy_s"), sm.get("sim_busy_s")
                print(f"{c:22s} {d.get('rep',0):4d} "
                      f"{(f'{r50:.4f}' if r50 else '-'):>10s} "
                      f"{(f'{rmean:.4f}' if rmean else '-'):>11s} "
                      f"{(hms(mb) if mb else '-'):>10s} "
                      f"{(hms(sb) if sb else '-'):>9s} "
                      f"{(f'{rt:.1f}' if rt is not None else '-'):>12s} "
                      f"{(f'{sp:.1f}' if sp is not None else '-'):>10s} "
                      f"{(f'{100*ovh:.2f}' if ovh is not None else '-'):>6s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
