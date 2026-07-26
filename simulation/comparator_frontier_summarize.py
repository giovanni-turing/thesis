#!/usr/bin/env python3
"""§8.2 comparator frontier: INDEPENDENT recomputation + pass/fail table.

Does not trust any run's own stats.json. For every replay artifact in a
comparator-frontier directory it recomputes, from raw outputs:

  encoder delay p99   from the emitted mooncake JSONL alone. The converter
                      writes  timestamp_i = arrival_i + encoder_delay_i  and
                      encodes the source request index in the first hash id,
                      hash_ids[0] = i*100000 (workload/trace_to_two_pool.py:
                      471-478, 494-505), so the per-request delay is recoverable
                      as timestamp_i - arrival_i with arrival_i read back from
                      the trace slice. Percentile estimator is the converter's
                      own nearest-rank rule (trace_to_two_pool.py:401-406) so
                      the number is comparable to every published figure.
  provisioned         by integrating the schedule JSON, piecewise-constant, to
  worker-seconds      the simulated end t_end = max(last arrival, last encoder
                      finish), with the encoder finish recovered as
                      arrival + delay - handoff and the handoff recomputed from
                      the converter's own cost model.

Both are cross-checked against the run's stats.json; any disagreement is
printed as a MISMATCH and makes the script exit nonzero.

Then applies the two pre-registered, calibration-only selection rules for the
warm-floor arm and prints the frozen M.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

_ROOT = os.environ.get("TESE_ROOT") or str(Path(__file__).resolve().parents[1])
sys.path.insert(0, os.path.join(_ROOT, "workload"))
import trace_to_two_pool as tp  # EncoderCostModel + handoff constants, verbatim

TRACE = os.environ.get("TESE_TRACE",
                       os.path.join(_ROOT, "data/AzureLMMInferenceTrace_multimodal.csv.gz"))
WINDOWS = Path(os.environ.get("TESE_WINDOWS", os.path.join(_ROOT, "simulation/windows.json")))
SLA_MS = 1000.0  # tex/twopool.tex:186-191 -- encoder delay p99 < 1 s, all requests

_arr_cache: dict[str, tuple] = {}


def window_arrivals(window: str):
    """(arrival_ms[], num_images[]) for the window slice, from the raw trace."""
    if window in _arr_cache:
        return _arr_cache[window]
    win = json.loads(WINDOWS.read_text())[window]
    nreq = int(win.get("max_requests") or win["requests"])
    df = tp.load_window(nreq, win["offset"])
    t0 = df["ts"].iloc[0]
    arr = (df["ts"] - t0).dt.total_seconds().to_numpy() * 1000.0
    _arr_cache[window] = (arr, df["NumImages"].to_numpy())
    return _arr_cache[window]


def pct(values, p):
    """The converter's own nearest-rank percentile (trace_to_two_pool.py:401-406)."""
    s = sorted(values)
    return round(s[min(len(s) - 1, int(len(s) * p / 100))], 3)


def recompute(jsonl: str, sched: str, window: str, px: int = 448,
              rtt_ms: float = 0.2, gbps: float = 25.0):
    arr, nimg = window_arrivals(window)
    enc = tp.EncoderCostModel(px)
    delays = [0.0] * len(arr)
    seen = 0
    if jsonl.endswith(".zst"):  # repo convention: large replays stored zstd-compressed
        import io
        import zstandard
        fh = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(open(jsonl, "rb")))
    else:
        fh = open(jsonl)
    with fh as f:
        for line in f:
            r = json.loads(line)
            i = r["hash_ids"][0] // 100_000
            delays[i] = r["timestamp"] - arr[i]
            seen += 1
    if seen != len(arr):
        raise SystemExit(f"{jsonl}: {seen} rows for a {len(arr)}-request window")

    # encoder finish = arrival + delay - handoff  (trace_to_two_pool.py:478-494)
    def handoff(n):
        if gbps <= 0 or n <= 0:
            return 0.0
        return rtt_ms + enc.post_merge_tokens(int(n)) * tp.LLM_HIDDEN * tp.BYTES_PER_ELEM \
            / (gbps * 1e9 / 8) * 1e3
    last_fin = 0.0
    for i in range(len(arr)):
        if nimg[i] > 0:
            last_fin = max(last_fin, arr[i] + delays[i] - handoff(nimg[i]))
    t_end = max(float(arr[-1]), last_fin)

    steps = sorted((float(t) * 1000.0, int(c)) for t, c in json.load(open(sched)))
    prov = 0.0
    for (a, ca), (b, _c) in zip(steps, steps[1:]):
        prov += ca * max(0.0, min(b, t_end) - min(a, t_end))
    prov += steps[-1][1] * max(0.0, t_end - steps[-1][0])
    return {
        "p50": pct(delays, 50), "p90": pct(delays, 90), "p99": pct(delays, 99),
        "max": round(max(delays), 3),
        "prov_worker_s": round(prov / 1000.0, 1),
        "t_end_s": round(t_end / 1000.0, 3),
        "min_workers": min(c for _, c in steps),
        "max_workers": max(c for _, c in steps),
        "steps": len(steps),
        "n_requests": len(arr),
        "violations_1000ms": int(sum(1 for d in delays if d > SLA_MS)),
    }


# tag grammar: <window>_<arm>_L<lead>[_H<hyst>]
#   arm in {floorM<M>, oracle, fc, re, staticC<M>}
TAG_RE = re.compile(r"^(?P<win>[A-Za-z0-9]+)_"
                    r"(?P<arm>floorM(?P<m>\d+)|staticC(?P<c>\d+)|oracle|fc|re)"
                    r"_L(?P<L>\d+)(?:_H(?P<H>\d+))?$")
ARM_NAME = {"oracle": "oracle", "fc": "forecast_p90", "re": "reactive"}


def frontier(df, args, bad: int) -> None:
    """§8.2 output: provisioned worker-time (eval span) vs worst-episode p99
    and failed-episode count, one row per arm. Nothing is selected here --
    every arm's parameters were frozen on the calibration split."""
    cost_w = args.cost_window
    print("\n=== §8.2 COMPARATOR FRONTIER (evaluation span) ===")
    print(f"cost axis: provisioned worker-seconds on '{cost_w}'; "
          f"tail axis: worst per-episode encoder-delay p99; "
          f"gate: p99 < {SLA_MS:.0f} ms\n")
    eps = sorted(w for w in df.window.unique() if w != cost_w)
    out = []
    for (arm, M, L, H), g in df.groupby(["arm", "M", "L", "H"], dropna=False):
        agg = g[g.window == cost_w]
        ep = g[g.window != cost_w]
        if not len(agg) or not len(ep):
            print(f"   incomplete arm {arm} M={M} L={L} H={H}: "
                  f"{len(agg)} cost row(s), {len(ep)}/{len(eps)} episode(s)")
        row = {"arm": arm, "M": M, "L": L, "H": H,
               "cost_worker_s": float(agg.prov_worker_s.iloc[0]) if len(agg) else float("nan"),
               "agg_p99": float(agg.p99.iloc[0]) if len(agg) else float("nan"),
               "worst_ep_p99": float(ep.p99.max()) if len(ep) else float("nan"),
               "worst_ep": ep.loc[ep.p99.idxmax(), "window"] if len(ep) else None,
               "failed_eps": int((ep.p99 >= SLA_MS).sum()),
               "failed_ep_names": ",".join(sorted(ep[ep.p99 >= SLA_MS].window)) or "-",
               "n_eps": len(ep)}
        out.append(row)
    fr = pd.DataFrame(out).sort_values(["cost_worker_s"])
    base = fr[(fr.arm == "static")]
    if len(base):
        ref = float(base.cost_worker_s.iloc[0])
        fr["vs_static"] = (fr.cost_worker_s / ref).round(3)
    print(fr.to_string(index=False))
    print(f"\nindependent-recomputation mismatches: {bad}")
    if args.json_out:
        Path(args.json_out).write_text(fr.to_json(orient="records", indent=1))
    sys.exit(1 if bad else 0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.join(_ROOT,
                    "simulation/results/comparator_frontier/calib"))
    ap.add_argument("--mode", choices=["calib", "frontier"], default="calib",
                    help="calib: apply the warm-floor selection rules. "
                         "frontier: worker-time vs worst-episode p99 table.")
    ap.add_argument("--cost-window", default="aggregate",
                    help="frontier mode: the window whose provisioned worker-time "
                         "is the cost axis (the 5.60-day evaluation span)")
    ap.add_argument("--frontier-lead", type=float, default=30.0,
                    help="the frozen lead of the comparator frontier (rule R1)")
    ap.add_argument("--declared-leads", default="15,30,45,300",
                    help="the thesis's declared encoder cold-start lead grid (rule R2)")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    rows = []
    bad = 0
    paths = sorted(glob.glob(os.path.join(args.dir, "*.jsonl"))
                   + glob.glob(os.path.join(args.dir, "*.jsonl.zst")))
    for jsonl in paths:
        tag = os.path.basename(jsonl).split(".jsonl")[0]
        sched = os.path.join(args.dir, tag + ".sched.json")
        stats_p = os.path.join(args.dir, tag + ".jsonl.stats.json")
        m = TAG_RE.match(tag)
        if not m or not os.path.exists(sched):
            print(f"skip {tag}")
            continue
        r = recompute(jsonl, sched, m.group("win"))
        st = json.load(open(stats_p))
        d_p99 = abs(st["encoder_delay_ms"]["p99"] - r["p99"])
        d_prov = abs(st["provisioned_worker_seconds"] - r["prov_worker_s"])
        ok = d_p99 <= 1e-3 and d_prov <= 0.2
        if not ok:
            bad += 1
            print(f"MISMATCH {tag}: p99 stats={st['encoder_delay_ms']['p99']} "
                  f"recomputed={r['p99']} | prov stats={st['provisioned_worker_seconds']} "
                  f"recomputed={r['prov_worker_s']}")
        raw_arm = m.group("arm")
        if raw_arm.startswith("floorM"):
            arm, size = "warm_floor", int(m.group("m"))
        elif raw_arm.startswith("staticC"):
            arm, size = "static", int(m.group("c"))
        else:
            arm, size = ARM_NAME[raw_arm], None
        rows.append({"tag": tag, "window": m.group("win"), "arm": arm,
                     "M": size,
                     "L": int(m.group("L")),
                     "H": int(m.group("H")) if m.group("H") is not None else 3,
                     "stats_agrees": bool(ok), **r})

    df = pd.DataFrame(rows).sort_values(["arm", "H", "L", "M", "window"])
    pd.set_option("display.width", 220, "display.max_rows", 500)

    if args.mode == "frontier":
        frontier(df, args, bad)
        return

    fl = df[df.arm == "warm_floor"]
    print("\n=== ARM (3) reactive + warm floor M : CALIBRATION SPLIT "
          "(burst2, burst6) ===")
    print("gate: encoder-delay p99 < 1000 ms, all requests, per window\n")
    piv = fl.pivot_table(index=["L", "M"], columns="window",
                         values=["p99", "prov_worker_s"])
    print(piv.to_string())

    leads = [float(x) for x in args.declared_leads.split(",")]
    wins = sorted(fl.window.unique())

    def passes(M, L):
        sub = fl[(fl.M == M) & (fl.L == L)]
        if len(sub) != len(wins):
            return None
        return bool((sub.p99 < SLA_MS).all())

    Ms = sorted(fl.M.unique())
    print("\n-- rule R1 (mandated): cheapest M passing BOTH calibration episodes "
          f"at the frozen frontier lead L={args.frontier_lead:g}s --")
    r1 = None
    for M in Ms:
        sub = fl[(fl.M == M) & (fl.L == args.frontier_lead)]
        cost = sub.prov_worker_s.sum()
        ok = passes(M, args.frontier_lead)
        print(f"   M={M:>2}  " + "  ".join(
            f"{w}: p99={float(sub[sub.window == w].p99.iloc[0]):8.1f} ms "
            f"({'PASS' if float(sub[sub.window == w].p99.iloc[0]) < SLA_MS else 'FAIL'})"
            for w in wins) + f"   sum worker-s={cost:12.1f}   -> {'PASS' if ok else 'FAIL'}")
        if ok and r1 is None:
            r1 = M
    print(f"   R1 selects M = {r1}")

    print("\n-- rule R2 (disclosed secondary): cheapest M passing BOTH calibration "
          f"episodes at EVERY declared lead {leads} --")
    r2 = None
    for M in Ms:
        per = {L: passes(M, L) for L in leads}
        allok = all(bool(v) for v in per.values())
        print(f"   M={M:>2}  " + "  ".join(
            f"L={int(L)}: {'PASS' if per[L] else 'FAIL'}" for L in leads)
            + f"   -> {'PASS' if allok else 'FAIL'}")
        if allok and r2 is None:
            r2 = M
    print(f"   R2 selects M = {r2}")

    orc = df[df.arm == "oracle"]
    if len(orc):
        print("\n=== ARM (5) perfect-future oracle : calibration-split smoke ===")
        print(orc[["window", "L", "H", "p99", "prov_worker_s", "min_workers",
                   "max_workers", "steps", "violations_1000ms"]].to_string(index=False))

    print(f"\nindependent-recomputation mismatches: {bad}")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"rows": rows, "R1_frozen_M": (None if r1 is None else int(r1)),
             "R2_frozen_M": (None if r2 is None else int(r2)),
             "sla_ms": SLA_MS, "frontier_lead_s": args.frontier_lead}, indent=1))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
