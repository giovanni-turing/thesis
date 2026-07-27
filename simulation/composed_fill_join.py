#!/usr/bin/env python3
"""Composed (request-linked) join for the 9 fill cells.

Modelled line-for-line on defense/anim/build/extract_a12.py: same encoder FIFO
key match against the raw CSV slice, same CONV() p99 index convention, same
sub-millisecond arrival-alignment guard.

The one addition is forced by a runtime fact, not by choice: `--report-jsonl`
records carry `session_id` only on the PLANNER path
(components/src/dynamo/replay/main.py:963-989); the plain path
(main.py:1006-1032) emits `session_id: null`. A static arm has no planner by
definition, so extract_a12's `request_<N>` key does not exist there. For those
cells the language records are keyed by

    (arrival_time_ms, min(input_length, len(hash_ids)*block), requested_output_length)

with a FIFO deque per key -- the same FIFO idiom extract_a12.py:76-87 already
uses on the encoder side. The input-length clamp mirrors
lib/mocker/src/loadgen/trace.rs:255-263.

The key is cross-validated on every PLANNER cell, where BOTH keys are
available: the FIFO-key assignment must reproduce the session_id assignment
line for line (reported as `key_selftest`).

Usage: composed_fill_join.py [cell ...]   (default: all)
"""
import argparse
import collections
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# TESE_ROOT override (2026-07-27, repro test §8.8-1): lets a clean checkout
# resolve its OWN inputs; default unchanged for the live tree (and for the K16
# pre-ingest guard, which invokes this script without the override).
ROOT = Path(os.environ.get("TESE_ROOT", "/home/gio/tese"))
OUT = ROOT / "simulation/results/composed_fill"
BLOCK = 512  # --trace-block-size, run_replay.sh

CONV = lambda n: min(n - 1, int(n * 99 / 100))


def p99(a: np.ndarray) -> float:
    n = len(a)
    i = CONV(n)
    return float(np.partition(a, i)[i])


# ---------------------------------------------------------------- windows ---
WINS = json.load(open(ROOT / "simulation/windows.json"))
WINS_EXT = json.load(open(ROOT / "defense/anim/data/windows_ext.json"))
WINS = {**WINS_EXT, **WINS}  # simulation/windows.json wins where both define it
WINS["fulltrace"] = WINS_EXT["fulltrace"]

# cell -> (window, composed trace, language records, replay report, planner?)
CELLS = {
    "burst1_static_C8":   ("burst1",    OUT / "burst1_static_C8.jsonl",    OUT / "burst1_static.requests.jsonl",    OUT / "burst1_static.report.json",    False),
    "burst3_static_C8":   ("burst3",    OUT / "burst3_static_C8.jsonl",    OUT / "burst3_static.requests.jsonl",    OUT / "burst3_static.report.json",    False),
    "burst4_static_C8":   ("burst4",    OUT / "burst4_static_C8.jsonl",    OUT / "burst4_static.requests.jsonl",    OUT / "burst4_static.report.json",    False),
    "burst5_static_C8":   ("burst5",    OUT / "burst5_static_C8.jsonl",    OUT / "burst5_static.requests.jsonl",    OUT / "burst5_static.report.json",    False),
    "steady24h_static_C8": ("steady24h", OUT / "steady24h_static_C8.jsonl", OUT / "steady24h_static.requests.jsonl", OUT / "steady24h_static.report.json", False),
    "steady24h_fc_chronos": ("steady24h", ROOT / "defense/anim/data/a2_runs/steady24h_forecast_L30.jsonl", OUT / "steady24h_fc_chronos.requests.jsonl", OUT / "steady24h_fc_chronos.report.json", True),
    "steady24h_reactive":   ("steady24h", ROOT / "defense/anim/data/a2_runs/steady24h_reactive_L30.jsonl", OUT / "steady24h_reactive.requests.jsonl",   OUT / "steady24h_reactive.report.json",   True),
    "fulltrace_static_C8": ("fulltrace", ROOT / "defense/anim/data/a13_runs/ft_static_C8.jsonl",    ROOT / "defense/anim/data/a13_runs/ft_llm_static.requests.jsonl",   ROOT / "defense/anim/data/a13_runs/ft_llm_static.report.json",   False),
    "fulltrace_reactive":  ("fulltrace", ROOT / "defense/anim/data/a13_runs/ft_reactive_L30.jsonl", ROOT / "defense/anim/data/a13_runs/ft_llm_reactive.requests.jsonl", ROOT / "defense/anim/data/a13_runs/ft_llm_reactive.report.json", True),
}

_RAW = None


def raw_frame() -> pd.DataFrame:
    global _RAW
    if _RAW is None:
        r = pd.read_csv(ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz")
        ts = r["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
        r["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
        _RAW = r.sort_values("ts").reset_index(drop=True)
    return _RAW


def read_trace(path: Path):
    """composed trace -> (ts, input_length, output_length, clamped_input,
    raw_id). The converter embeds exact raw-row identity in every request
    (workload/trace_to_two_pool.py: hash_ids[0] = request_index * 100000);
    that id is the AUTHORITATIVE encoder mapping (D29)."""
    ts, il, ol, cl, rid = [], [], [], [], []
    with open(path) as fh:
        for line in fh:
            r = json.loads(line)
            ts.append(r["timestamp"])
            il.append(r["input_length"])
            ol.append(r["output_length"])
            cl.append(min(r["input_length"], len(r["hash_ids"]) * BLOCK))
            rid.append(r["hash_ids"][0] // 100000)
    return (np.asarray(ts, dtype=np.float64), np.asarray(il, dtype=np.int64),
            np.asarray(ol, dtype=np.int64), np.asarray(cl, dtype=np.int64),
            np.asarray(rid, dtype=np.int64))


def read_records(path: Path):
    """per-request records -> parallel arrays, file order preserved."""
    sid, arr, ttft, il, ol = [], [], [], [], []
    with open(path) as fh:
        for line in fh:
            r = json.loads(line)
            sid.append(r["session_id"])
            arr.append(r["arrival_time_ms"])
            ttft.append(r["ttft_ms"])
            il.append(r["input_length"])
            ol.append(r["requested_output_length"])
    return (sid, np.asarray(arr, dtype=np.float64), np.asarray(ttft, dtype=np.float64),
            np.asarray(il, dtype=np.int64), np.asarray(ol, dtype=np.int64))


def key_assign(t_ts, t_cl, t_ol, r_arr, r_il, r_ol):
    """FIFO key match records -> trace line index.

    Key = (arrival_time_ms, clamped input_length, requested_output_length).
    The replay re-zeroes arrivals to the first one, so the trace side is
    t - t.min(). Returns rec2line, plus the count of records whose key was
    shared by >1 trace line (genuinely interchangeable rows).
    """
    base = t_ts - t_ts.min()
    key2lines = collections.defaultdict(collections.deque)
    for li in range(len(t_ts)):
        key2lines[(round(float(base[li]), 6), int(t_cl[li]), int(t_ol[li]))].append(li)
    multi = {k for k, v in key2lines.items() if len(v) > 1}
    rec2line = np.full(len(r_arr), -1, dtype=np.int64)
    ambiguous = 0
    for ri in range(len(r_arr)):
        k = (round(float(r_arr[ri]), 6), int(r_il[ri]), int(r_ol[ri]))
        dq = key2lines.get(k)
        if not dq:
            raise AssertionError(f"unmatched language record {ri} key={k}")
        rec2line[ri] = dq.popleft()
        if k in multi:
            ambiguous += 1
    left = sum(len(v) for v in key2lines.values())
    if left:
        raise AssertionError(f"{left} trace lines unmatched by language records")
    return rec2line, ambiguous


def join_cell(cell: str) -> dict:
    win_key, trace_path, rec_path, rep_path, planner = CELLS[cell]
    win = WINS[win_key]
    N = int(win["max_requests"])

    # ---- window slice of the raw trace (ingress arrivals) ----
    w = raw_frame().iloc[win["offset"]:win["offset"] + N].reset_index(drop=True)
    rel_ms = ((w.ts - w.ts.iloc[0]).dt.total_seconds() * 1000.0).to_numpy()

    # ---- encoder delays: composed-trace timestamps vs raw arrivals ----
    # D29: the embedded hash-id identity is authoritative; the regeneration
    # gate requires it to be a complete permutation of the window. The old
    # token-pair FIFO reconstruction is kept as a recorded cross-check only.
    t_ts, t_il, t_ol, t_cl, t_rid = read_trace(trace_path)
    n = len(t_ts)
    assert n == N, f"{cell}: composed trace has {n} lines, window expects {N}"
    assert np.array_equal(np.sort(t_rid), np.arange(n)), \
        f"{cell}: embedded hash-id identity is not a permutation of the window"
    line2raw = t_rid
    enc = np.full(n, np.nan)
    enc[line2raw] = t_ts - rel_ms[line2raw]
    assert not np.isnan(enc).any(), f"{cell}: unmatched encoder rows"
    key2idx = collections.defaultdict(collections.deque)
    for i, (ci, gi) in enumerate(zip(w["ContextTokens"], w["GeneratedTokens"])):
        key2idx[(max(1, int(ci)), max(1, int(gi)))].append(i)
    fifo = np.empty(n, dtype=np.int64)
    for li in range(n):
        fifo[li] = key2idx[(int(t_il[li]), int(t_ol[li]))].popleft()
    fifo_identity_agree = int((fifo == line2raw).sum())

    # ---- language records -> trace line index ----
    sid, r_arr, r_ttft, r_il, r_ol = read_records(rec_path)
    assert len(sid) == N, f"{cell}: {len(sid)} language records, expected {N}"
    selftest = None
    if planner:
        rec2line = np.array(
            [int(re.match(r"request_(\d+)", s).group(1)) - 1 for s in sid], dtype=np.int64)
        # cross-validate the static-cell key where both keys exist
        alt, amb = key_assign(t_ts, t_cl, t_ol, r_arr, r_il, r_ol)
        agree = int((alt == rec2line).sum())
        selftest = {"agree": agree, "of": N, "ambiguous_key_records": amb,
                    "fifo_identity_agree": fifo_identity_agree}
    else:
        assert all(s is None for s in sid), f"{cell}: expected null session_ids on the plain path"
        rec2line, amb = key_assign(t_ts, t_cl, t_ol, r_arr, r_il, r_ol)
        selftest = {"ambiguous_key_records": amb,
                    "fifo_identity_agree": fifo_identity_agree}

    assert len(set(rec2line.tolist())) == N, f"{cell}: line assignment not a bijection"
    ttft = np.full(n, np.nan)
    arr_l = np.full(n, np.nan)
    ttft[rec2line] = r_ttft
    arr_l[rec2line] = r_arr
    assert not np.isnan(ttft).any(), f"{cell}: unmatched language rows"

    # ---- alignment guard (extract_a12.py:97-100) ----
    d = arr_l - (t_ts - t_ts.min())
    drift = float(np.abs(d - d[0]).max())
    assert drift < 1.0, f"{cell}: arrival alignment drift {drift} ms"

    # ---- the join ----
    enc_of_line = enc[line2raw]
    e2e = enc_of_line + ttft

    rep = json.load(open(rep_path))
    enc_p99, e2e_p99 = p99(enc_of_line), p99(e2e)
    # The thesis "naive sum" column (tex/closedloop.tex:894-924) and A12's
    # ledger take the language p99 straight off the replay report
    # (extract_a12.py:102-113). But the report's p99 index is
    # `round((n-1)*99/100)` (lib/mocker/src/replay/collector.rs:1075) while
    # e2e_p99 here uses CONV = `min(n-1, int(n*99/100))` (extract_a12.py:31).
    # The two land 0 or 1 order statistics apart -- identical on the arms
    # published so far, but NOT on burst3/burst5 static, where the gap makes a
    # mixed-estimator "naive sum" appear to fall BELOW the joined p99. Since
    # the claim the column supports is a relation between sum-of-p99s and
    # p99-of-sum, that relation is only meaningful under ONE estimator, so both
    # are carried: `*_report` follows the published convention, `*_conv` is the
    # self-consistent one.
    ttft_p99 = round(rep["p99_ttft_ms"], 1)
    ttft_p99_conv = p99(ttft)
    naive = ttft_p99 + enc_p99
    naive_conv = ttft_p99_conv + enc_p99
    # D30: the sum-vs-composed relation is only meaningful under ONE estimator
    # at FULL precision, so the producer persists it as evidence: the
    # self-consistent CONV sum minus the composed p99, and its sign class
    # (|delta| <= 1e-6 ms = numerically coincident).
    _rel = naive_conv - e2e_p99
    conv_sum_relation = ("coincides" if abs(_rel) <= 1e-6
                         else ("overstates" if _rel > 0 else "understates"))
    return {
        "cell": cell, "window": win_key, "arm": cell[len(win_key) + 1:],
        "planner": planner,
        "requests": n, "expected": N,
        "alignment_drift_ms": round(drift, 9),
        "alignment_offset_ms": round(float(d[0]), 6),
        "key_selftest": selftest,
        "enc_p99": round(enc_p99, 1),
        "ttft_p99": ttft_p99,
        "ttft_p99_conv_recompute": round(ttft_p99_conv, 1),
        "e2e_p99": round(e2e_p99, 1),
        "e2e_max": round(float(e2e.max()), 1),
        "enc_max": round(float(enc_of_line.max()), 1),
        "itl_p99": round(rep["p99_itl_ms"], 1),
        "gpu_h": round(rep["gpu_hours"], 2),
        "completed_requests": rep["completed_requests"],
        "naive_sum": round(naive, 1),
        "error_ratio": round(naive / e2e_p99, 4),
        "naive_sum_conv": round(naive_conv, 1),
        "error_ratio_conv": round(naive_conv / e2e_p99, 4),
        "conv_sum_minus_e2e_ms": round(_rel, 6),
        "conv_sum_relation": conv_sum_relation,
        "composed_trace": str(trace_path.relative_to(ROOT)),
        "language_records": str(rec_path.relative_to(ROOT)),
        "report": str(rep_path.relative_to(ROOT)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cells", nargs="*", default=None)
    ap.add_argument("--out", default=str(OUT / "composed_fill_joined.json"))
    a = ap.parse_args()
    todo = a.cells or list(CELLS)
    res = {}
    outp = Path(a.out)
    if outp.exists():
        res = json.load(open(outp))
    for c in todo:
        try:
            r = join_cell(c)
        except Exception as e:  # report and continue
            r = {"cell": c, "error": f"{type(e).__name__}: {e}"}
        res[c] = r
        print(json.dumps(r), flush=True)
        outp.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
