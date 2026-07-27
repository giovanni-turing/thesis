#!/usr/bin/env python3
"""§8.2 REPORT builder: independent recomputation -> frontier_summary.json + frontier figure.

Recomputes every reported number from raw outputs (trace CSV + emitted mooncake
JSONL + worker schedule JSON). Imports nothing from simulation/ or workload/.

  delay_i    = timestamp_i(ms) - arrival_i(ms), request index = hash_ids[0] // 100000
  percentile = converter's own rule, s[min(n-1, int(n*p/100))]   (workload/trace_to_two_pool.py:401-406)
  worker-s   = integral of the step schedule to t_end = max(last_arrival,
               max_i(ts_i - handoff(n_img_i))), handoff(n) = 0.2 + n*196*4096*2/(25e9/8)*1e3 ms

Usage:  python3 build_frontier_summary.py [--jobs 12]
"""
from __future__ import annotations

import argparse
import io
import json
import multiprocessing as mp
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/gio/tese")
HERE = Path(__file__).resolve().parent
TRACE = ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz"
WINDOWS = json.loads((ROOT / "simulation/windows.json").read_text())

SLA_MS = 1000.0
EVAL_EPISODES = ["burst1", "burst3", "burst4", "burst5", "steady24h"]
COST_WINDOW = "aggregate"

# handoff model, re-derived from the converter's documented constants
TOK_PER_IMG, LLM_HIDDEN, BYTES_PER_ELEM = 196, 4096, 2
RTT_MS, GBPS = 0.2, 25.0
PER_IMG_MS = TOK_PER_IMG * LLM_HIDDEN * BYTES_PER_ELEM / (GBPS * 1e9 / 8) * 1e3

_trace = None


def full_trace() -> pd.DataFrame:
    global _trace
    if _trace is None:
        df = pd.read_csv(TRACE)
        ts = df["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
        df["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
        _trace = df.drop(columns=["TIMESTAMP"]).sort_values("ts").reset_index(drop=True)
    return _trace


def window_arrivals(w: str):
    cfg = WINDOWS[w]
    off = cfg["offset"]
    n = cfg.get("max_requests") or cfg.get("requests")
    d = full_trace().iloc[off:off + n]
    t0 = d["ts"].iloc[0]
    arr = (d["ts"] - t0).dt.total_seconds().to_numpy() * 1000.0
    ni = d["NumImages"].to_numpy().astype(np.int64)
    return arr, ni


def open_jsonl(path: Path):
    p = str(path)
    if p.endswith(".zst"):
        proc = subprocess.Popen(["zstdcat", p], stdout=subprocess.PIPE)
        return io.TextIOWrapper(proc.stdout)
    if p.endswith(".gz"):
        import gzip
        return gzip.open(p, "rt")
    return open(p)


def pctl(values: np.ndarray, p: float) -> float:
    s = np.sort(np.asarray(values))
    return round(float(s[min(len(s) - 1, int(len(s) * p / 100))]), 3)


def recompute(jsonl: Path, sched: Path, window: str) -> dict:
    arr, ni = window_arrivals(window)
    n = len(arr)
    ts = np.full(n, np.nan)
    seen = 0
    with open_jsonl(jsonl) as f:
        for line in f:
            r = json.loads(line)
            i = r["hash_ids"][0] // 100_000
            if not np.isnan(ts[i]):
                raise SystemExit(f"duplicate index {i} in {jsonl}")
            ts[i] = r["timestamp"]
            seen += 1
    if seen != n or np.isnan(ts).any():
        raise SystemExit(f"row-count mismatch {jsonl}: {seen} vs window {n}")

    delay = np.where(ni > 0, ts - arr, 0.0)
    h = RTT_MS + PER_IMG_MS * ni
    fin = ts - h
    last_finish = float(fin[ni > 0].max()) if (ni > 0).any() else 0.0
    t_end_ms = max(float(arr[-1]), last_finish)

    steps = sorted((float(t) * 1000.0, int(c)) for t, c in json.loads(sched.read_text()))
    prov = 0.0
    for (t0, c0), (t1, _) in zip(steps, steps[1:]):
        prov += c0 * max(0.0, min(t1, t_end_ms) - min(t0, t_end_ms))
    prov += steps[-1][1] * max(0.0, t_end_ms - steps[-1][0])

    return dict(
        n_requests=n, n_with_images=int((ni > 0).sum()),
        p50=pctl(delay, 50), p90=pctl(delay, 90), p99=pctl(delay, 99),
        max_delay_ms=round(float(delay.max()), 3),
        violations_1000ms=int((delay > SLA_MS).sum()),
        worker_s=round(prov / 1000.0, 1),
        t_end_s=round(t_end_ms / 1000.0, 3),
        sched_steps=len(steps),
        sched_min=min(c for _, c in steps), sched_max=max(c for _, c in steps),
    )


# ---------------------------------------------------------------- cell inventory
def cells() -> list[dict]:
    out = []
    core = {"fc_L30": ("forecast_p90", None), "re_L30": ("reactive", None),
            "floorM4_L30": ("warm_floor_M4", 4), "oracle_L30_H0": ("oracle_H0", None),
            "staticC8_L30": ("static_C8", 8)}
    for w in [COST_WINDOW] + EVAL_EPISODES:
        for suf, (arm, M) in core.items():
            out.append(dict(group="core", window=w, arm=arm, M=M,
                            tag=f"{w}_{suf}", dir=HERE / "eval"))
        for M in [1, 2, 3, 5, 6, 7, 8, 9, 10, 12, 14, 16, 20, 24, 32]:
            out.append(dict(group="family", window=w, arm=f"warm_floor_M{M}", M=M,
                            tag=f"{w}_floorM{M}_L30", dir=HERE / "eval_family"))
        for suf, arm in [("fcSTRICT", "forecast_p90_strict_rewarm"),
                         ("oracleH3", "oracle_H3"),
                         ("oracleWS", "oracle_warmstart_H0"),
                         ("oracleWSH3", "oracle_warmstart_H3"),
                         ("reWPm1", "reactive_warmpool_M1"),
                         ("reWPm2", "reactive_warmpool_M2"),
                         ("reWPm3", "reactive_warmpool_M3"),
                         ("reWPm4", "reactive_warmpool_M4")]:
            out.append(dict(group="adversarial", window=w, arm=arm,
                            M=int(suf[-1]) if suf.startswith("reWP") else None,
                            tag=f"{w}_{suf}", dir=HERE / "adversarial"))
    # D20 (2026-07-26, hardened per reviewer D20-round-2): the calibration grid is
    # pinned by EXACT identity -- the expected Cartesian products from FROZEN.json,
    # not whatever files happen to match a regex. A missing declared cell OR an
    # undeclared extra cell is a hard abort (identity substitution defense).
    frozen0 = json.loads((HERE / "FROZEN.json").read_text())
    grid_M = frozen0["arm_3_reactive_plus_warm_floor"]["grid_M"]
    LEADS = [15, 30, 45, 300]
    expected = {f"{w}_floorM{M}_L{L}" for w in ("burst2", "burst6")
                for M in grid_M for L in LEADS}
    expected |= {f"{w}_oracle_L{L}_H{H}" for w in ("burst2", "burst6")
                 for L in LEADS for H in (0, 3)}
    import glob as _glob, re as _re
    found = {Path(x).name[:-len(".sched.json")]
             for x in _glob.glob(str(HERE / "calib" / "*.sched.json"))}
    if found != expected:
        missing = sorted(expected - found); extra = sorted(found - expected)
        raise SystemExit(f"calibration identity mismatch: missing={missing[:5]} extra={extra[:5]} "
                         f"(missing {len(missing)}, extra {len(extra)})")
    for base in sorted(found):
        m = _re.match(r"^(burst[26])_floorM(\d+)_L(\d+)$", base)
        mo = _re.match(r"^(burst[26])_oracle_L(\d+)_H(\d+)$", base)
        if m:
            out.append(dict(group="calib", window=m.group(1), arm=f"calib_floorM{m.group(2)}_L{m.group(3)}",
                            M=int(m.group(2)), tag=base, dir=HERE / "calib"))
        else:
            out.append(dict(group="calib_oracle", window=mo.group(1),
                            arm=f"calib_oracle_L{mo.group(2)}_H{mo.group(3)}", M=None,
                            tag=base, dir=HERE / "calib"))
    out.append(dict(group="check", window=COST_WINDOW, arm="static_C8_encworkers_path", M=8,
                    tag="aggregate_encworkers8", dir=HERE / "checks"))
    return out


def _jsonl_path(d: Path, tag: str) -> Path:
    for ext in (".jsonl.zst", ".jsonl.gz", ".jsonl"):
        p = d / (tag + ext)
        if p.exists():
            return p
    raise SystemExit(f"no jsonl for {tag} in {d}")


def _sched_path(d: Path, tag: str, arm: str) -> Path:
    p = d / (tag + ".sched.json")
    if p.exists():
        return p
    if "static" in arm:                      # static arms carry a synthetic 1-step schedule
        return p
    raise SystemExit(f"no schedule for {tag}")


def work(c: dict) -> dict:
    d = Path(c["dir"])
    jsonl = _jsonl_path(d, c["tag"])
    sp = d / (c["tag"] + ".sched.json")
    if sp.exists():
        got = recompute(jsonl, sp, c["window"])
    else:
        # static, run through --encoder-workers: schedule is the constant [[0, M]]
        tmp = d / (c["tag"] + ".sched.json")
        arr, ni = window_arrivals(c["window"])
        synth = HERE / f".synth_{c['tag']}.json"
        synth.write_text(json.dumps([[0, c["M"]]]))
        got = recompute(jsonl, synth, c["window"])
        synth.unlink()
    st = d / (c["tag"] + ".jsonl.stats.json")
    agrees = None
    if st.exists():
        s = json.loads(st.read_text())
        agrees = (abs(s["encoder_delay_ms"]["p99"] - got["p99"]) < 1e-3 and
                  abs(s["provisioned_worker_seconds"] - got["worker_s"]) < 0.15 and
                  int(s["encoder_delay_violations"]["1000"]) == got["violations_1000ms"])
    return {**{k: v for k, v in c.items() if k != "dir"},
            "dir": str(c["dir"]), "stats_agrees": agrees, **got}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10)
    args = ap.parse_args()

    cs = cells()
    print(f"recomputing {len(cs)} cells with {args.jobs} workers ...", file=sys.stderr)
    with mp.Pool(args.jobs) as pool:
        rows = pool.map(work, cs, chunksize=1)
    df = pd.DataFrame(rows)
    bad = df[df["stats_agrees"] == False]  # noqa: E712
    missing = df[df["stats_agrees"].isna()]
    fail = False
    # D20.1: absent evidence is a failure, not a silent None
    if len(missing):
        print("MISSING stats files for cells:", file=sys.stderr)
        print(missing[["group", "tag"]].to_string(), file=sys.stderr)
        fail = True
    # D20.3: recompute the calibration selection and compare with FROZEN.json
    calib = df[df["group"] == "calib"]
    sel_ok = "SKIP"
    if len(calib):
        import re as _re
        passing = []
        for M, g in calib.groupby("M"):
            if (g["p99"] < 1000.0).all() and set(g["window"]) == {"burst2", "burst6"}:
                passing.append(int(M))
        recomputed_M = min(passing) if passing else None
        frozen = json.loads((HERE / "FROZEN.json").read_text())
        frozen_M = frozen["arm_3_reactive_plus_warm_floor"]["frozen_M"]
        sel_ok = "OK" if (recomputed_M is not None and recomputed_M == frozen_M) else f"FAIL(recomputed={recomputed_M},frozen={frozen_M})"
        if sel_ok != "OK":
            fail = True
    # D25 (2026-07-26): the report generator consumes the tracked
    # calib_recheck_cells.json -- verify that intermediate against the freshly
    # recomputed calibration rows (tag -> p99/worker_s/violations/n_requests),
    # missing/extra/mismatched rows are a hard fail. Oracle calib cells are not
    # in that table by design (floor grid only).
    calib_tbl_ok = "OK"
    try:
        raw_tracked = json.loads((HERE / "calib_recheck_cells.json").read_text())
        tags_list = [r["tag"] for r in raw_tracked]
        tracked = {r["tag"]: r for r in raw_tracked}
        fresh = {r["tag"]: r for _, r in df[df["group"].isin(["calib", "calib_oracle"])].iterrows()}
        floor_fresh = {t for t in fresh if "floorM" in t}
        # D25 round 3: exact cardinality, unique tags, exact identity sets, and
        # equality of EVERY generator-consumed schema field (window/arm/M/L/
        # stats_agrees) in addition to the numerics -- metadata mutation of the
        # binding row (e.g. L=300 -> 301) must fail here, where truth is
        # recomputed from raw, not downstream where the corruption propagates.
        ORACLE_L30 = {f"{w}_oracle_L30_H{h}" for w in ("burst2", "burst6") for h in (0, 3)}
        expected_tracked = floor_fresh | ORACLE_L30
        if len(tags_list) != len(set(tags_list)):
            calib_tbl_ok = "FAIL(duplicate tags in tracked table)"
        elif len(tags_list) != len(expected_tracked) or set(tags_list) != expected_tracked:
            calib_tbl_ok = (f"FAIL(identities: {len(tags_list)} rows vs {len(expected_tracked)} expected; "
                            f"missing {sorted(expected_tracked-set(tags_list))[:2]} extra {sorted(set(tags_list)-expected_tracked)[:2]})")
        else:
            import re as _re2, math as _math
            def _intlike(v):
                # D34: exact integral check BEFORE any coercion -- 4.5 / 300.5 / NaN all fail
                return isinstance(v, (int, float)) and not isinstance(v, bool) \
                       and _math.isfinite(float(v)) and float(v).is_integer()
            def _finite(v):
                return isinstance(v, (int, float)) and not isinstance(v, bool) and _math.isfinite(float(v))
            for tag, tr in tracked.items():
                fr = fresh[tag]
                mM = _re2.search(r"floorM(\d+)_L(\d+)$", tag)
                exp_M = int(mM.group(1)) if mM else None
                exp_L = int(mM.group(2)) if mM else int(_re2.search(r"_L(\d+)_H", tag).group(1))
                exp_arm = "warm_floor" if mM else ("oracle_H" + _re2.search(r"_H(\d+)$", tag).group(1))
                if exp_M is not None and not _intlike(tr.get("M")):
                    calib_tbl_ok = f"FAIL({tag}: M not integral: {tr.get('M')!r})"; break
                if exp_M is None and ("M" not in tr or tr.get("M") is not None):
                    calib_tbl_ok = f"FAIL({tag}: oracle M must be present and null, got {('<absent>' if 'M' not in tr else repr(tr.get('M')))})"; break
                if not _intlike(tr.get("L")):
                    calib_tbl_ok = f"FAIL({tag}: L not integral: {tr.get('L')!r})"; break
                if not all(_finite(tr.get(k)) for k in ("p99", "worker_s")) \
                        or not _intlike(tr.get("violations_1000ms")) or not _intlike(tr.get("n_requests")):
                    calib_tbl_ok = f"FAIL({tag}: non-finite/non-integral numeric)"; break
                tr_M = None if tr.get("M") is None else float(tr["M"])
                if (tr.get("arm") != exp_arm or tr.get("window") != fr["window"]
                        or (exp_M is not None and tr_M != float(exp_M))
                        or float(tr.get("L")) != float(exp_L) or tr.get("stats_agrees") is not True
                        or float(tr["p99"]) != float(fr["p99"])
                        or float(tr["worker_s"]) != float(fr["worker_s"])
                        or int(tr["violations_1000ms"]) != int(fr["violations_1000ms"])
                        or int(tr["n_requests"]) != int(fr["n_requests"])):
                    calib_tbl_ok = f"FAIL({tag})"; break
    except Exception as e:
        calib_tbl_ok = f"FAIL({e})"
    if calib_tbl_ok != "OK":
        fail = True
    # D20.4: link the raw cells to the summary object the gate reads
    link_ok = "OK"
    try:
        summ = json.loads((HERE / "frontier_summary.json").read_text())
        static_ref = summ["static_reference_worker_s"]
        cells_by = {}
        for _, r in df[df["group"].isin(["core", "family", "adversarial"])].iterrows():
            cells_by[(r["arm"], r["window"])] = r
        problems = []
        def _check_block(key, arm, blk):
            for w, want_p99 in blk.get("p99_ms_per_window", {}).items():
                row = cells_by.get((arm, w))
                if row is None: problems.append(f"{arm}/{w}:no-cell"); return
                if abs(row["p99"] - want_p99) > 1e-2: problems.append(f"{arm}/{w}:p99 {row['p99']} vs {want_p99}"); return
            for w, want_ws in blk.get("worker_s_per_window", {}).items():
                row = cells_by.get((arm, w))
                if row is None or abs(row["worker_s"] - want_ws) > 0.15:
                    problems.append(f"{arm}/{w}:worker_s"); return
            if "cost_worker_s_eval_span" in blk:
                row = cells_by.get((arm, COST_WINDOW))
                if row is None or abs(row["worker_s"] - blk["cost_worker_s_eval_span"]) > 0.15:
                    problems.append(f"{arm}:eval-span cost"); return
                if "vs_static" in blk and abs(round(row["worker_s"]/static_ref, 4) - blk["vs_static"]) > 5e-4:
                    problems.append(f"{arm}:vs_static"); return
            if "episodes_failed" in blk:
                eps = [w for w in blk.get("p99_ms_per_window", {}) if w != COST_WINDOW]
                nf = sum(1 for w in eps if cells_by.get((arm, w)) is not None and cells_by[(arm, w)]["p99"] >= 1000.0)
                if nf != blk["episodes_failed"]: problems.append(f"{arm}:episodes_failed {nf} vs {blk['episodes_failed']}")
        arm_map = {"1_forecast_p90_issue_time": "forecast_p90", "2_reactive_react_point": "reactive",
                   "3_reactive_plus_warm_floor_M4": "warm_floor_M4", "4_static_C8_deployable": "static_C8",
                   "5_perfect_future_oracle_H0": "oracle_H0"}
        for key, arm in arm_map.items():
            _check_block(key, arm, summ["arms"][key])
        for name, blk in summ["warm_floor_family_envelope"]["members"].items():
            _check_block(name, name, blk)
        if problems:
            link_ok = "FAIL(" + "; ".join(problems[:3]) + ")"; fail = True
    except Exception as e:
        link_ok = f"FAIL({e})"; fail = True
    if len(bad):
        print(bad.to_string(), file=sys.stderr)
        fail = True
    print(f"cells={len(df)}  stats-missing={len(missing)}  stats-mismatches={len(bad)}  "
          f"calib-selection={sel_ok}  calib-table={calib_tbl_ok}  summary-link={link_ok}", file=sys.stderr)
    df.to_json(HERE / "frontier_summary_cells.json", orient="records", indent=1)
    print("wrote frontier_summary_cells.json", file=sys.stderr)
    if fail:
        sys.exit(2)


if __name__ == "__main__":
    main()
