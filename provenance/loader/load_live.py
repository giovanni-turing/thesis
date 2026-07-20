#!/usr/bin/env python3
"""K50 -- the LIVE ARM loader (ADJUDICATION §2.10).

Ingests the three live-hardware arms under
simulation/results/live51/live_runs/, which back tex/validation.tex's
tab:val-anchor and were entirely absent from the store:

    <arm>/profile_export_aiperf.json  -> live_arm (headline) + live_arm_metric (all)
    <arm>/manager.jsonl               -> live_worker_event + replica_seconds
    <arm>/planner.log.gz              -> live_fpm_pass + live_spawn_latency

plus the §2.10 backfill of runs.tp = 2 on every experiment='live' row,
from simulation/live51/engine_args.json ("aic_tp_size": 2).

RUN_ID
------
An arm is three files of three different kinds in one directory, so
runid.run_id_of() -- which keys on the file STEM -- would split each arm
into three unrelated run_ids ('live:live_fc:manager',
'live:live_fc:profile_export_aiperf', ...). K50 therefore assigns one
run_id per ARM, 'live:arm:<arm>', and registers all three source files
against it in ingest_log. This is the same shape as the other bulk
loaders (K20 grid, K21 collector) and K50 is deliberately NOT in
ingest_common.PER_FILE_KINDS, so the collision guard reads these rows as
a bulk registration rather than a collision. guard_run_collision() is
still called before each write, to catch the case where a PER-FILE
loader has claimed the same id.

IDEMPOTENT: sha256 in ingest_log short-circuits an unchanged file, and
every write is an upsert or a delete-then-insert scoped to one arm. A
second run loads 0 rows.

Run:  cd /home/gio/tese/provenance/loader && python3 load_live.py [--reload]
"""
import datetime as dt
import gzip
import json
import os
import re
import sys

import db
import ingest_common as ic

TESE = "/home/gio/tese"
LIVE_ROOT = f"{TESE}/simulation/results/live51/live_runs"
ENGINE_ARGS = f"{TESE}/simulation/live51/engine_args.json"

# arm -> (policy, is_thesis_arm)
ARMS = {
    "live_fc":     ("forecast", True),
    "live_re":     ("reactive", True),
    # NOT a policy arm: a short planner feature-flag verification control.
    # Ingested so the third sibling directory is not silently dropped.
    "verify_flag": (None, False),
}

# Census window for the mixed-pass rates, measured from the first FPM line.
FPM_WINDOW_S = 300.0

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_TS = re.compile(r"(\d{4}-\d\d-\d\dT[\d:.]+Z)")
_FPM = re.compile(
    r"FPM decode engine (?P<engine>\d+):dp(?P<dp>\d+): "
    r"wall_time=(?P<wall>[\d.]+)s, "
    r"sched\(prefill_tok=(?P<ptok>\d+), prefill_req=(?P<preq>\d+), "
    r"decode_kv=(?P<dkv>\d+), decode_req=(?P<dreq>\d+)\), "
    r"queued\(prefill_tok=(?P<qptok>\d+), decode_kv=(?P<qdkv>\d+)\)")
_DISCOVERY = "Discovery Added"


def _clean(s):
    return _ANSI.sub("", s)


def _ts(line):
    m = _TS.search(line)
    if not m:
        return None
    return dt.datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))


def _paths(arm):
    d = f"{LIVE_ROOT}/{arm}"
    return (f"{d}/profile_export_aiperf.json", f"{d}/manager.jsonl", f"{d}/planner.log.gz")


# ------------------------------------------------------------------ parsing
def _parse_aiperf(path):
    """-> (headline dict, [metric rows]). aiperf metrics are {unit, avg, p50, ...}."""
    with open(path) as f:
        j = json.load(f)
    rows = []
    for metric, v in j.items():
        if not isinstance(v, dict):
            continue
        unit = v.get("unit")
        for stat, val in v.items():
            if stat == "unit" or not isinstance(val, (int, float)) or isinstance(val, bool):
                continue
            rows.append({"metric": metric, "stat": stat, "value": float(val), "unit": unit})

    def g(metric, stat):
        v = (j.get(metric) or {})
        v = v.get(stat) if isinstance(v, dict) else None
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    def cnt(metric):
        v = g(metric, "avg")
        return int(v) if v is not None else None

    head = {
        "ttft_p99_ms": g("time_to_first_token", "p99"),
        "ttft_p50_ms": g("time_to_first_token", "p50"),
        "ttft_avg_ms": g("time_to_first_token", "avg"),
        # aiperf `inter_token_latency` is per-request MEAN inter-token time = TPOT.
        # This is what tab:val-anchor prints as "ITL p99". See the schema comment.
        "itl_p99_ms": g("inter_token_latency", "p99"),
        "itl_p50_ms": g("inter_token_latency", "p50"),
        "itl_avg_ms": g("inter_token_latency", "avg"),
        # the genuine per-chunk ITL, kept distinct on purpose
        "chunk_latency_p99_ms": g("inter_chunk_latency", "p99"),
        "request_latency_p99_ms": g("request_latency", "p99"),
        "request_latency_p50_ms": g("request_latency", "p50"),
        "request_count": cnt("request_count"),
        "error_request_count": cnt("error_request_count"),
        "benchmark_duration_s": g("benchmark_duration", "avg"),
        "output_token_throughput": g("output_token_throughput", "avg"),
        "aiperf_version": j.get("aiperf_version"),
        "benchmark_id": j.get("benchmark_id"),
    }
    return head, rows


def _parse_manager(path):
    """-> (event rows, replica_seconds, span_s, n_spawns, max_n_live).

    replica_seconds integrates n_live over t_wall: the provisioned-replica
    area under the manager's own occupancy trace.
    """
    evs = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            evs.append({"line_no": i, "event": e.get("event"), "seq": e.get("seq"),
                        "pid": e.get("pid"), "reason": e.get("reason"),
                        "n_live": e.get("n_live"), "n_pending": e.get("n_pending"),
                        "t_wall": e.get("t_wall"), "raw": e})
    ts = [e["t_wall"] for e in evs if e["t_wall"] is not None]
    t0 = min(ts) if ts else None
    for e in evs:
        e["t_rel_s"] = (e["t_wall"] - t0) if (e["t_wall"] is not None and t0 is not None) else None

    occ = sorted(((e["t_wall"], e["n_live"]) for e in evs
                  if e["t_wall"] is not None and e["n_live"] is not None),
                 key=lambda x: x[0])
    rs = sum((occ[i + 1][0] - occ[i][0]) * occ[i][1] for i in range(len(occ) - 1))
    span = (occ[-1][0] - occ[0][0]) if len(occ) > 1 else 0.0
    spawns = [e for e in evs if e["event"] == "spawn"]
    return evs, rs, span, len(spawns), (max((n for _, n in occ), default=None))


def _parse_planner(path):
    """-> (fpm rows, discovery timestamps as epoch floats)."""
    with gzip.open(path, "rt", errors="replace") as f:
        lines = [_clean(l) for l in f.read().splitlines()]

    disc = sorted(t.timestamp() for t in
                  (_ts(l) for l in lines if _DISCOVERY in l) if t is not None)

    fpm = []
    for line in lines:
        if "_log_fpm" not in line:
            continue
        m = _FPM.search(line)
        t = _ts(line)
        if not m:
            # Keep the line countable even if the format shifts, rather than
            # silently shrinking the mixed-pass denominator.
            fpm.append({"ts": t, "engine_id": None, "dp_rank": None, "wall_time_s": None,
                        "prefill_tok": None, "prefill_req": None, "decode_kv": None,
                        "decode_req": None, "queued_prefill_tok": None,
                        "queued_decode_kv": None, "is_mixed": None})
            continue
        d = m.groupdict()
        ptok, dkv = int(d["ptok"]), int(d["dkv"])
        fpm.append({"ts": t, "engine_id": d["engine"], "dp_rank": int(d["dp"]),
                    "wall_time_s": float(d["wall"]),
                    "prefill_tok": ptok, "prefill_req": int(d["preq"]),
                    "decode_kv": dkv, "decode_req": int(d["dreq"]),
                    "queued_prefill_tok": int(d["qptok"]),
                    "queued_decode_kv": int(d["qdkv"]),
                    # a pass that batched prefill AND decode work together
                    "is_mixed": ptok > 0 and dkv > 0})

    fts = [r["ts"] for r in fpm if r["ts"] is not None]
    f0 = min(fts) if fts else None
    for i, r in enumerate(fpm):
        r["idx"] = i + 1
        r["t_rel_s"] = ((r["ts"] - f0).total_seconds()
                        if (r["ts"] is not None and f0 is not None) else None)
    return fpm, disc


def _pair_spawns(evs, disc):
    """Spawn -> first subsequent 'Discovery Added'.

    Initial spawns are EXCLUDED: they fire before the planner is fully
    subscribed, so the gap measures planner startup (~3.3 s), not replica
    registration. See the live_spawn_latency table comment.
    """
    out = []
    for e in evs:
        if e["event"] != "spawn" or e.get("reason") == "initial":
            continue
        t = e["t_wall"]
        if t is None:
            continue
        nxt = next((d for d in disc if d >= t), None)
        if nxt is None:
            continue
        out.append({"seq": e["seq"], "reason": e.get("reason"),
                    "t_spawn": t, "t_registered": nxt, "latency_s": nxt - t})
    return out


# ------------------------------------------------------------------- writing
_M_COLS = ["arm", "metric", "stat", "value", "unit"]
_E_COLS = ["arm", "line_no", "event", "seq", "pid", "reason", "n_live", "n_pending",
           "t_wall", "t_rel_s", "raw"]
_S_COLS = ["arm", "seq", "reason", "t_spawn", "t_registered", "latency_s"]
_F_COLS = ["arm", "idx", "ts_utc", "t_rel_s", "engine_id", "dp_rank", "wall_time_s",
           "prefill_tok", "prefill_req", "decode_kv", "decode_req",
           "queued_prefill_tok", "queued_decode_kv", "is_mixed"]


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _load_arm(arm, idx, reload):
    aiperf_p, manager_p, planner_p = _paths(arm)
    for p in (aiperf_p, manager_p, planner_p):
        if not os.path.exists(p):
            print(f"[K50] MISSING {p}", file=sys.stderr, flush=True)
            return 0, 0
        if ic.is_worktree(p):
            return 0, 0

    metas = {p: ic.file_meta(p) for p in (aiperf_p, manager_p, planner_p)}
    if not reload and all(idx.get(p) == metas[p][0] for p in metas):
        return 0, 0

    run_id = f"live:arm:{arm}"
    policy, is_thesis = ARMS[arm]
    # Check the arm's run_id ONCE, against the file that identifies the run.
    #
    # Deliberately not once per file. guard_run_collision() notes each path it
    # clears under a PER-FILE kind (bulk kinds are recorded as K1), so calling
    # it for all three would make the second call collide with the note the
    # first one just wrote -- a false positive against ourselves. The guard's
    # real job here is to catch a PER-FILE loader having already claimed
    # 'live:arm:<arm>', and one call does that.
    ic.guard_run_collision(run_id, aiperf_p, idx, table="live_arm", kind="K50")

    head, metrics = _parse_aiperf(aiperf_p)
    evs, rs, span, n_spawns, max_live = _parse_manager(manager_p)
    fpm, disc = _parse_planner(planner_p)
    spawns = _pair_spawns(evs, disc)

    in_window = [r for r in fpm if r["t_rel_s"] is not None and r["t_rel_s"] <= FPM_WINDOW_S]

    run = {"run_id": run_id, "experiment": "live", "pool": "language", "policy": policy,
           "tp": 2, "gpu": "h100_sxm", "engine": "vLLM", "kind": "K50",
           "source_path": aiperf_p,
           "artifact_paths": [aiperf_p, manager_p, planner_p],
           "config": {"arm": arm, "is_thesis_arm": is_thesis,
                      "aic_tp_size": 2, "note": "live-hardware arm, ADJUDICATION 2.10"}}

    arm_row = dict(head)
    arm_row.update({"arm": arm, "run_id": run_id, "policy": policy,
                    "is_thesis_arm": is_thesis,
                    "replica_seconds": rs, "manager_span_s": span,
                    "n_spawns": n_spawns, "max_n_live": max_live,
                    "fpm_passes": len(in_window),
                    "fpm_mixed_passes": sum(1 for r in in_window if r["is_mixed"]),
                    "fpm_window_s": FPM_WINDOW_S,
                    "aiperf_path": aiperf_p, "manager_path": manager_p,
                    "planner_log_path": planner_p})

    stmts = [ic.run_upsert_sql(run),
             ic.upsert_sql("live_arm", arm_row, "arm")]
    # children: rewrite this arm wholesale so --reload cannot leave orphans
    for t in ("live_arm_metric", "live_worker_event", "live_spawn_latency", "live_fpm_pass"):
        stmts.append(f"delete from provenance.{t} where arm={ic.lit(arm)}")

    for c in _chunks([dict(m, arm=arm) for m in metrics], 500):
        stmts.append(ic.multi_upsert_sql("live_arm_metric", _M_COLS, c,
                                         ["arm", "metric", "stat"]))
    for c in _chunks([dict(e, arm=arm) for e in evs], 500):
        stmts.append(ic.multi_upsert_sql("live_worker_event", _E_COLS, c,
                                         ["arm", "line_no"], jsonb_cols=("raw",)))
    for c in _chunks([dict(s, arm=arm) for s in spawns], 500):
        stmts.append(ic.multi_upsert_sql("live_spawn_latency", _S_COLS, c, ["arm", "seq"]))
    for c in _chunks([{"arm": arm, "idx": r["idx"],
                       "ts_utc": r["ts"].isoformat() if r["ts"] else None,
                       "t_rel_s": r["t_rel_s"], "engine_id": r["engine_id"],
                       "dp_rank": r["dp_rank"], "wall_time_s": r["wall_time_s"],
                       "prefill_tok": r["prefill_tok"], "prefill_req": r["prefill_req"],
                       "decode_kv": r["decode_kv"], "decode_req": r["decode_req"],
                       "queued_prefill_tok": r["queued_prefill_tok"],
                       "queued_decode_kv": r["queued_decode_kv"],
                       "is_mixed": r["is_mixed"]} for r in fpm], 500):
        stmts.append(ic.multi_upsert_sql("live_fpm_pass", _F_COLS, c, ["arm", "idx"]))

    n = 1 + len(metrics) + len(evs) + len(spawns) + len(fpm)
    for p, (sha, nbytes) in metas.items():
        stmts.append(ic.ingest_sql(p, sha, "K50", n, run_id, nbytes))

    db.run_sql(";\n".join(s for s in stmts if s))
    return 3, n


def _backfill_tp(idx, reload):
    """§2.10: runs.tp = 2 on every experiment='live' row.

    Configuration, not measurement: engine_args.json is the deployment's own
    record and tp was NULL on all seven pre-existing live rows. Only ever
    fills a NULL or a value that already disagrees with the artifact; nothing
    measured is touched.
    """
    if not os.path.exists(ENGINE_ARGS):
        print(f"[K50] MISSING {ENGINE_ARGS}", file=sys.stderr, flush=True)
        return 0
    with open(ENGINE_ARGS) as f:
        tp = json.load(f).get("aic_tp_size")
    if not tp:
        return 0
    out = db.run_sql(
        "update provenance.runs set tp=%d where experiment='live' "
        "and tp is distinct from %d returning run_id" % (int(tp), int(tp)))
    return sum(1 for l in out.splitlines() if l.strip().startswith("live:"))


def load_live(idx, reload=False):
    """K50 entrypoint. Returns (files_loaded, rows_loaded)."""
    nf = nr = 0
    for arm in ARMS:
        f, r = _load_arm(arm, idx, reload)
        nf += f
        nr += r
    n_tp = _backfill_tp(idx, reload)
    if n_tp:
        print(f"[K50] backfilled runs.tp=2 on {n_tp} live rows", flush=True)
    return nf, nr


def main():
    reload = "--reload" in sys.argv
    idx = ic.load_ingest_index()
    nf, nr = load_live(idx, reload)
    print(f"[K50   live             ] files={nf:5d} rows={nr:13,d}", flush=True)


if __name__ == "__main__":
    main()
