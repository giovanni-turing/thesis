#!/usr/bin/env python3
"""Negative gate tests for the silicon-anchor campaign (bridge 101 (i)-(iii),
accepted by the reviewer in 199).

WHAT IT PROVES
    The positive gates of the campaign (dispatch fidelity gate, reconstruction
    gate, membership recovery, clock/tenancy gate) are only worth what their
    negatives are worth. This suite takes ONE completed, never-resumed rep,
    copies it, verifies the clean copy end to end with the RUNNER'S OWN
    functions, and then re-verifies deliberately corrupted copies. Every
    corruption must FAIL LOUDLY with a named semantic reason -- never silently
    produce a retime.

    The three promised classes:
      (i)   missing or duplicated batch/request membership must fail
            extraction/retiming;
      (ii)  reordered or mismatched dispatch must fail;
      (iii) a changed engine/model/clock fingerprint must fail.

READ-ONLY WITH RESPECT TO THE LIVE CAMPAIGN
    Nothing under simulation/results/silicon_anchor/ is ever opened for
    writing, and the running daemon is never signalled. Every fixture is a
    COPY under a temp dir; `_guard` refuses any write outside it.

HOW THE RUNNER IS INVOKED
    silicon_anchor_runner.py and silicon_anchor_extract.py are script-style
    (both are `if __name__ == "__main__"`-guarded, with no import-time side
    effects and a lazy `import torch`), so they are loaded through an
    importlib spec shim and their functions are called directly:

        runner.recover_membership   membership replay of the FIFO admission
        runner.retime               frozen-composition retiming
        runner.request_delays       per-request encoder delay
        runner.pct                  the percentile convention
        runner.gate_verdict         the clock/tenancy gate (pure function)
        runner.throttle_evidence    the banked clock-evidence summary
        extract.sha256              the provenance fingerprint function
        extract.GATE_SCALARS/DICTS  the dispatch fidelity gate field list

    No campaign math is reimplemented here. The only transcriptions are the
    two gate PREDICATES that live inline in run_trace_replay (the
    reconstruction-gate comparison, lines 796-803, and the dispatch-verdict
    refusal, lines 645-646); both are quoted in the code below.

GATE MAP (and how much of each the LIVE runner actually enforces)
    G1  dispatch-verdict            ENFORCED   run_trace_replay:645 raises
    G1b dispatch-fidelity-recomputed EXTRACT-TIME ONLY; the runner trusts the
                                     banked verdict and never recomputes it
    G2  dispatch-fingerprint        RECORDED, NEVER VERIFIED
    G3  batch-row-alignment         NOT CHECKED ANYWHERE (and the resume path
                                     keys off row COUNT, not batch_idx)
    G4  reconstruction              COMPUTED + BANKED, ADVISORY -- it never
                                     raises; a failed rep is still written and
                                     still checkpointed rep_done
    G5  membership-completeness     RECORDED, NEVER ASSERTED
    G6  headline-reproduction       POST-HOC ONLY (derivation, not transcription)
    G7  model/engine-fingerprint    RECORDED, NEVER COMPARED
    G8  clock/tenancy               ENFORCED   wait_for_gate + per-segment
                                     gate_verdict; clock.jsonl is the evidence

    Per the campaign freeze, this file does NOT patch the runner. The
    post-hoc-only gates are the extractor-side guards to add once the campaign
    stops; this suite is what will hold them honest.

Usage:
    silicon_negative_gates.py [--selftest] [--cell burst3__fc] [--rep 2]
                              [--all-reps] [--keep]

NOT WIRED INTO verify_all.sh YET -- that happens with the settled evidence
commit, once the campaign stops and the corrective pin exists.
"""
from __future__ import annotations

import argparse
import calendar
import gzip
import importlib.util
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path("/home/gio/tese")
CAMPAIGN = ROOT / "simulation" / "results" / "silicon_anchor"
ANCHOR = ROOT / "collector_artifacts" / "phaseE_physical_anchor" / "anchor_sdpa_locked2400.json"
DEFAULT_CELL = "burst3__fc"      # tier-1 headline cell
DEFAULT_REP = 2                  # rep002: COMPLETE, resumed_from_batch = null

_TMP_ROOT: Path | None = None


# --------------------------------------------------------------------------
# import shim (script-style modules, loaded by spec; no side effects)
# --------------------------------------------------------------------------
def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


runner = _load("_sa_runner", ROOT / "simulation" / "silicon_anchor_runner.py")
extract = _load("_sa_extract", ROOT / "simulation" / "silicon_anchor_extract.py")


# --------------------------------------------------------------------------
# write guard: the live campaign is never touched
# --------------------------------------------------------------------------
def _guard(p: Path) -> Path:
    p = Path(p)
    if _TMP_ROOT is None or not str(p.resolve()).startswith(str(_TMP_ROOT.resolve())):
        raise AssertionError(f"REFUSING to write outside the fixture: {p}")
    return p


def _wjson(p: Path, obj) -> None:
    json.dump(obj, open(_guard(p), "w"), indent=1)


def _rlines_gz(p: Path) -> list[str]:
    with gzip.open(p, "rt") as f:
        return f.read().splitlines(keepends=True)


def _wlines_gz(p: Path, lines: list[str]) -> None:
    with gzip.open(_guard(p), "wt") as f:
        f.writelines(lines)


def _rlines(p: Path) -> list[str]:
    return Path(p).read_text().splitlines(keepends=True)


def _wlines(p: Path, lines: list[str]) -> None:
    _guard(p).write_text("".join(lines))


# --------------------------------------------------------------------------
# fixture
# --------------------------------------------------------------------------
def cell_spec(queue: dict, cid: str) -> dict:
    for t in queue["tiers"]:
        if cid in t["cells"]:
            return dict(t["cells"][cid], tier=t["tier"])
    raise KeyError(cid)


def runner_pids(manifest: Path, cid: str, rep: int) -> list[tuple[float, int]]:
    """(start_ts, pid) of every runner process, from the append-only manifest.

    runner.gate_verdict's single-tenancy test is relative to the MEASURING
    process (`os.getpid()` at the moment of the snapshot). A rep that was
    preempted and resumed spans two daemons, so the pid has to be resolved per
    snapshot, not per rep -- otherwise the successor daemon looks like a
    foreign tenant to its own snapshots."""
    recs = []
    with open(manifest) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    starts = [r for r in recs if r.get("ev") in ("rep_start", "rep_resume")
              and r.get("cell") == cid and r.get("rep") == rep]
    if not starts:
        raise LookupError(f"no rep_start for {cid} rep{rep} in {manifest}")
    daemons = sorted((float(r["ts"]), int(r["pid"])) for r in recs
                     if r["ev"] == "daemon_start" and "pid" in r)
    if not daemons or daemons[0][0] > starts[0]["ts"]:
        raise LookupError(f"no daemon_start before {cid} rep{rep}")
    return daemons


def pid_at(daemons: list[tuple[float, int]], snap: dict) -> int:
    """The pid that owned the GPU when `snap` was taken."""
    utc = snap.get("utc")
    if not utc:
        return daemons[-1][1]
    try:
        t = calendar.timegm(time.strptime(utc, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return daemons[-1][1]
    live = [p for ts, p in daemons if ts <= t + 1]
    return live[-1] if live else daemons[0][1]


def build_fixture(dst: Path, cid: str, rep: int) -> dict:
    """Copy ONE completed rep + its dispatch inputs into `dst`. Read-only with
    respect to the campaign."""
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "dispatch").mkdir(exist_ok=True)
    (dst / "inputs").mkdir(exist_ok=True)
    rd = dst / "reps" / cid / f"rep{rep:03d}"
    rd.mkdir(parents=True, exist_ok=True)

    q = json.load(open(ROOT / "simulation" / "silicon_anchor_queue.json"))
    spec = cell_spec(q, cid)
    shutil.copy(ROOT / "simulation" / "silicon_anchor_queue.json", dst / "queue.json")
    for suf in ("batches.jsonl", "batches.jsonl.reqs.json", "meta.json", "regen.stats.json"):
        shutil.copy(CAMPAIGN / "dispatch" / f"{cid}.{suf}", dst / "dispatch" / f"{cid}.{suf}")
    src_rep = CAMPAIGN / "reps" / cid / f"rep{rep:03d}"
    for f in ("rep.json", "batches.csv.gz", "clock.jsonl"):
        shutil.copy(src_rep / f, rd / f)
    shutil.copy(ROOT / spec["schedule"], dst / "inputs" / "schedule.json")
    shutil.copy(ROOT / spec["banked_stats"], dst / "inputs" / "banked_stats.json")
    shutil.copy(ANCHOR, dst / "anchor.json")
    daemons = runner_pids(CAMPAIGN / "manifest.jsonl", cid, rep)

    return {
        "root": dst, "cell": cid, "rep": rep, "daemons": daemons,
        "queue": dst / "queue.json",
        "batches_jsonl": dst / "dispatch" / f"{cid}.batches.jsonl",
        "reqs": dst / "dispatch" / f"{cid}.batches.jsonl.reqs.json",
        "meta": dst / "dispatch" / f"{cid}.meta.json",
        "regen": dst / "dispatch" / f"{cid}.regen.stats.json",
        "rep_json": rd / "rep.json",
        "csv_gz": rd / "batches.csv.gz",
        "clock": rd / "clock.jsonl",
        "schedule": dst / "inputs" / "schedule.json",
        "banked_stats": dst / "inputs" / "banked_stats.json",
        "anchor": dst / "anchor.json",
    }


def clone(fx: dict, dst: Path) -> dict:
    shutil.copytree(fx["root"], dst)
    out = dict(fx)
    out["root"] = dst
    for k, v in fx.items():
        if isinstance(v, Path) and k != "root":
            out[k] = dst / v.relative_to(fx["root"])
    return out


# --------------------------------------------------------------------------
# the verifier: the runner's own gates, recomputed over a fixture
# --------------------------------------------------------------------------
CSV_HEADER = "batch_idx,n_images,sim_start_ms,sim_service_ms,meas_service_ms\n"

LIVE_ENFORCEMENT = {
    "G1": "ENFORCED (run_trace_replay:645 refuses to measure)",
    "G1b": "extract-time only; the runner trusts the banked verdict",
    "G2": "recorded, never verified",
    "G3": "not checked anywhere (resume keys off row count, not batch_idx)",
    "G4": "computed + banked, ADVISORY -- never raises",
    "G5": "recorded, never asserted",
    "G6": "post-hoc only (derivation check)",
    "G7": "recorded, never compared",
    "G8": "ENFORCED (wait_for_gate + per-segment gate_verdict)",
}


def verify(fx: dict) -> list[str]:
    """Re-run every campaign gate over a fixture. Returns semantic error
    strings, each prefixed with its gate id. Empty list == the fixture is a
    faithful, self-consistent, correctly-fingerprinted rep."""
    errs: list[str] = []

    def E(gate: str, msg: str) -> None:
        errs.append(f"{gate}: {msg}")

    cid, rep = fx["cell"], fx["rep"]

    # ---- inputs -----------------------------------------------------------
    try:
        q = json.load(open(fx["queue"]))
        spec = cell_spec(q, cid)
        meta = json.load(open(fx["meta"]))
        reqs_meta = json.load(open(fx["reqs"]))
        rj = json.load(open(fx["rep_json"]))
        anchor = json.load(open(fx["anchor"]))
    except Exception as ex:
        E("G0/parse", f"fixture JSON unreadable: {type(ex).__name__}: {ex}")
        return errs
    try:
        batches = [json.loads(l) for l in open(fx["batches_jsonl"]) if l.strip()]
    except Exception as ex:
        E("G0/parse", f"dispatch log unreadable: {type(ex).__name__}: {ex}")
        return errs
    if not batches:
        E("G0/parse", "dispatch log empty")
        return errs
    n_b = len(batches)

    # ---- G1: the dispatch fidelity verdict the runner refuses to measure without
    # runner.run_trace_replay:645-646 --
    #   if not meta["gate"]["pass"]: raise RuntimeError(... refusing to measure)
    if meta.get("gate", {}).get("pass") is not True:
        E("G1/dispatch-verdict", f"{cid}: dispatch log failed the fidelity gate; "
                                 f"the runner refuses to measure")

    # ---- G1b: recompute that verdict instead of trusting it -----------------
    try:
        regen = json.load(open(fx["regen"]))
        bank = json.load(open(fx["banked_stats"]))
        diffs = [{"field": k, "banked": bank.get(k), "regen": regen.get(k)}
                 for k in list(extract.GATE_SCALARS) + list(extract.GATE_DICTS)
                 if regen.get(k) != bank.get(k)]
    except Exception as ex:
        diffs = None
        E("G1b/dispatch-fidelity", f"stats unreadable: {type(ex).__name__}: {ex}")
    if diffs:
        E("G1b/dispatch-fidelity", "regenerated dispatch stats diverge from the banked "
          f"run on {[d['field'] for d in diffs]} -- e.g. {json.dumps(diffs[0])[:160]}")
    if diffs is not None and bool(diffs) == (meta.get("gate", {}).get("pass") is True):
        E("G1b/dispatch-fidelity", "banked gate verdict contradicts the recomputed one "
          f"(meta.pass={meta.get('gate', {}).get('pass')}, recomputed diffs={len(diffs)})")

    # ---- G2: the recorded provenance fingerprints must still bind ----------
    for field, path in (("schedule_sha256", fx["schedule"]),
                        ("banked_stats_sha256", fx["banked_stats"])):
        want = meta.get("provenance", {}).get(field)
        got = extract.sha256(path)
        if want != got:
            E("G2/dispatch-fingerprint",
              f"{field} mismatch: meta says {str(want)[:16]}..., "
              f"{path.name} hashes to {got[:16]}...")
    # The dispatch log itself carries NO sha256 (extract.py records only the
    # schedule/banked/converter hashes), but extract.py:175-191 does bank a
    # digest of it. Recompute that digest -- it is the only fingerprint the
    # dispatch log has.
    hist: dict[int, int] = {}
    sim_busy_ms = 0.0
    for b in batches:
        hist[int(b[2])] = hist.get(int(b[2]), 0) + 1
        sim_busy_ms += b[1] - b[0]
    digest = {"batches": n_b, "distinct_batch_sizes": len(hist),
              "max_batch_images": max(hist) if hist else 0,
              "total_images": sum(int(b[2]) for b in batches),
              "sim_busy_s": round(sim_busy_ms / 1000.0, 3),
              "batch_size_hist": {str(k): hist[k] for k in sorted(hist)}}
    for k, v in digest.items():
        if meta.get("dispatch", {}).get(k) != v:
            was = meta.get("dispatch", {}).get(k)
            E("G2/dispatch-fingerprint",
              f"dispatch digest {k} recomputes to {json.dumps(v)[:110]} but the "
              f"extractor banked {json.dumps(was)[:110]} -- the dispatch log is not "
              f"the one that was gated")

    # ---- G3: measured rows must align with the dispatch log ---------------
    rows = None
    measured: list[float] = []
    try:
        raw = _rlines_gz(fx["csv_gz"])
        if not raw or raw[0] != CSV_HEADER:
            E("G3/row-alignment", f"batches.csv.gz header is not the runner's "
                                  f"({raw[0].strip() if raw else 'EMPTY'!r})")
        rows = [r.rstrip("\n").split(",") for r in raw[1:] if r.strip()]
        measured = [float(r[4]) for r in rows]
    except Exception as ex:
        E("G3/row-alignment", f"batches.csv.gz unreadable: {type(ex).__name__}: {ex}")
    if rows is not None:
        if len(rows) != n_b:
            E("G3/row-alignment", f"measured batch rows {len(rows)} != dispatched "
                                  f"batches {n_b} (missing or duplicated batch)")
        if rj.get("n_batches") != n_b:
            E("G3/row-alignment", f"rep.json n_batches {rj.get('n_batches')} != "
                                  f"dispatched batches {n_b}")
        idxs = [int(r[0]) for r in rows]
        if idxs != list(range(len(rows))):
            first = next((k for k, v in enumerate(idxs) if v != k), None)
            E("G3/row-alignment", f"batch_idx column is not 0..{len(rows)-1} "
                                  f"(first break at row {first}: idx {idxs[first]})")
        if len(set(idxs)) != len(idxs):
            dup = next(v for v in idxs if idxs.count(v) > 1)
            E("G3/row-alignment", f"duplicated batch_idx {dup} in the measured rows")
        for i, r in enumerate(rows[:n_b]):
            b = batches[i]
            if int(r[1]) != int(b[2]):
                E("G3/row-alignment", f"row {i}: measured n_images {r[1]} != dispatched "
                                      f"{int(b[2])} (batch membership does not match)")
                break
            if abs(float(r[2]) - float(b[0])) > 1e-9:
                E("G3/row-alignment", f"row {i}: sim_start_ms {r[2]} != dispatched {b[0]}")
                break
            if abs(float(r[3]) - round(float(b[1]) - float(b[0]), 6)) > 1e-9:
                E("G3/row-alignment", f"row {i}: sim_service_ms {r[3]} != dispatched "
                                      f"{round(float(b[1]) - float(b[0]), 6)}")
                break

    # ---- membership recovery + retiming, via the runner's own functions ----
    try:
        schedule = json.load(open(fx["schedule"]))
        schedule = sorted((float(t) * 1000.0, int(c)) for t, c in schedule)
    except Exception as ex:
        E("G4/reconstruction", f"schedule unreadable: {type(ex).__name__}: {ex}")
        return errs
    sim_ms = [b[1] - b[0] for b in batches]
    try:
        members, head_arr = runner.recover_membership(batches, reqs_meta)
    except Exception as ex:
        E("G4/reconstruction", f"recover_membership raised {type(ex).__name__}: {ex}")
        return errs

    # ---- G4: the reconstruction gate, verbatim from run_trace_replay:796-803
    #   rs, rf, _ = retime(batches, head_arr, sim_ms, schedule)
    #   max_dev = max(abs(rf[i] - batches[i][1]) ...)
    #   recon_ok = (max_dev <= 1e-6) and (bank_p99 is None or
    #              abs(sim_p99 - bank_p99) <= max(1e-3, 1e-6 * abs(bank_p99)))
    recon_ok = False
    max_dev = None
    sim_p99 = None
    bank_p99 = (spec.get("banked", {}).get("encoder_delay_ms") or {}).get("p99")
    try:
        _rs, rf, _sl = runner.retime(batches, head_arr, sim_ms, schedule)
        max_dev = max((abs(rf[i] - batches[i][1]) for i in range(n_b)), default=0.0)
        sim_delays, _ = runner.request_delays(members, [b[1] for b in batches], reqs_meta)
        sim_p99 = runner.pct(sim_delays)["p99"]
        recon_ok = (max_dev <= 1e-6) and (
            bank_p99 is None or abs(sim_p99 - bank_p99) <= max(1e-3, 1e-6 * abs(bank_p99)))
    except Exception as ex:
        E("G4/reconstruction", f"replaying the sim's OWN service times raised "
                               f"{type(ex).__name__}: {ex}")
    if max_dev is not None and max_dev > 1e-6:
        E("G4/reconstruction", f"retiming under the sim's own service times does NOT "
                               f"reproduce the dumped dispatch timeline "
                               f"(max batch-finish deviation {max_dev:.6g} ms > 1e-6): "
                               f"membership/slot recovery is not faithful, the measured "
                               f"retiming is void")
    if sim_p99 is not None and bank_p99 is not None and \
            abs(sim_p99 - bank_p99) > max(1e-3, 1e-6 * abs(bank_p99)):
        E("G4/reconstruction", f"replayed sim encoder-delay p99 {sim_p99} != banked "
                               f"{bank_p99}: recovered request membership is wrong")
    got_gate = {"pass": bool(recon_ok), "max_batch_finish_deviation_ms": max_dev,
                "replayed_sim_p99_ms": sim_p99, "banked_sim_p99_ms": bank_p99}
    rec_gate = rj.get("reconstruction_gate", {})
    for k, v in got_gate.items():
        if rec_gate.get(k) != v:
            E("G4/reconstruction", f"banked reconstruction_gate.{k}={rec_gate.get(k)!r} "
                                   f"but recomputes to {v!r}")

    # ---- G5: membership completeness --------------------------------------
    try:
        _d, n_req = runner.request_delays(members, [b[1] for b in batches], reqs_meta)
    except Exception as ex:
        n_req = None
        E("G5/membership", f"request_delays raised {type(ex).__name__}: {ex}")
    n_reqs_in = len(reqs_meta.get("reqs", []))
    idxs = [r[1] for r in reqs_meta.get("reqs", [])]
    if len(set(idxs)) != len(idxs):
        dup = next(v for v in idxs if idxs.count(v) > 1)
        E("G5/membership", f"duplicated request index {dup} in the membership input")
    if n_req is not None and n_req != n_reqs_in:
        E("G5/membership", f"only {n_req}/{n_reqs_in} image-bearing requests were "
                           f"recovered into a batch (missing request membership)")
    if rj.get("membership_recovery_requests_total") != n_reqs_in:
        E("G5/membership", f"rep.json membership total "
                           f"{rj.get('membership_recovery_requests_total')} != "
                           f"{n_reqs_in} requests in the membership input")
    if n_req is not None and rj.get("membership_recovery_requests_matched") != n_req:
        E("G5/membership", f"rep.json membership matched "
                           f"{rj.get('membership_recovery_requests_matched')} != "
                           f"recomputed {n_req}")

    # ---- G6: the banked headline must be DERIVABLE, not merely transcribed -
    if measured:
        try:
            _ns, nf, _sl = runner.retime(batches, head_arr, measured, schedule)
            delays, _ = runner.request_delays(members, nf, reqs_meta)
            got = {**runner.pct(delays),
                   "max": round(max(delays), 3) if delays else 0.0}
            if got != rj.get("retimed_encoder_delay_ms"):
                E("G6/headline", f"retimed_encoder_delay_ms recomputes to {got} but "
                                 f"rep.json banks {rj.get('retimed_encoder_delay_ms')}")
        except Exception as ex:
            E("G6/headline", f"retiming the MEASURED service times raised "
                             f"{type(ex).__name__}: {ex}")
        mb = round(sum(measured) / 1000.0, 3)
        if abs(mb - float(rj.get("measured_busy_s", -1))) > 5e-4:
            E("G6/headline", f"measured_busy_s recomputes to {mb} but rep.json banks "
                             f"{rj.get('measured_busy_s')}")
    ti = sum(int(b[2]) for b in batches)
    if rj.get("total_images") != ti:
        E("G6/headline", f"total_images recomputes to {ti} but rep.json banks "
                         f"{rj.get('total_images')}")
    sb = round(sum(sim_ms) / 1000.0, 3)
    if abs(sb - float(rj.get("sim_busy_s", -1))) > 5e-4:
        E("G6/headline", f"sim_busy_s recomputes to {sb} but rep.json banks "
                         f"{rj.get('sim_busy_s')}")

    # ---- G7: engine / model fingerprint vs the master anchor --------------
    enc = rj.get("encoder", {})
    ex_ = q["execution"]
    for label, got_v, want_v, src in (
            ("n_params", enc.get("n_params"), anchor.get("n_params"), "master anchor"),
            ("model_dir", enc.get("model_dir"), anchor.get("model_dir"), "master anchor"),
            ("attn", enc.get("attn"), anchor.get("attn_used"), "master anchor"),
            ("image_px", enc.get("image_px"), anchor.get("protocol", {}).get("image_px"),
             "master anchor"),
            ("model_dir", enc.get("model_dir"), ex_.get("model_dir"), "queue execution"),
            ("attn", enc.get("attn"), ex_.get("attn"), "queue execution"),
            ("image_px", enc.get("image_px"), ex_.get("image_px"), "queue execution")):
        if got_v != want_v:
            E("G7/model-fingerprint", f"rep {label}={got_v!r} != {src} {want_v!r}: the "
                                      f"measured engine/model is not the anchored one")

    # ---- G8: clock / tenancy gate over every banked snapshot --------------
    gate = q["clock_gate"]
    snaps = []
    try:
        with open(fx["clock"]) as f:
            for k, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                snaps.append((k, json.loads(line)))
    except Exception as ex:
        E("G8/clock", f"clock.jsonl unreadable: {type(ex).__name__}: {ex}")
    if not snaps:
        E("G8/clock", "no clock snapshots banked for this rep")
    for k, s in snaps:
        ok, why = runner.gate_verdict(s, gate, pid_at(fx["daemons"], s))
        if not ok:
            E("G8/clock", f"snapshot {k} (at={s.get('at')} batch={s.get('batch')}) "
                          f"violates the clock/tenancy gate: {'; '.join(why)}")
    for label in ("clock_start", "clock_end"):
        s = rj.get(label)
        if s:
            ok, why = runner.gate_verdict(s, gate, pid_at(fx["daemons"], s))
            if not ok:
                E("G8/clock", f"rep.json {label} violates the clock gate: {'; '.join(why)}")
    te = runner.throttle_evidence(fx["clock"])
    if te.get("fatal_slowdown_snapshots"):
        E("G8/clock", f"{te['fatal_slowdown_snapshots']} snapshot(s) carry a fatal "
                      f"throttle SLOWDOWN bit (histogram {te.get('throttle_hex_histogram')})")
    if te != rj.get("throttle_evidence"):
        E("G8/clock", "banked throttle_evidence does not recompute from clock.jsonl")

    return errs


# --------------------------------------------------------------------------
# probes
# --------------------------------------------------------------------------
# Each probe: (id, class, title, mutate(fixture) -> str|None, expected gate ids,
#              known_gap description or None, structural note or None)
# `mutate` returns a short note; returning None means the mutation did not
# apply (pattern drift) and the probe fails as a test bug.
MID = 1500          # a batch index in the interior of the rep


def _csv_rows(fx):
    raw = _rlines_gz(fx["csv_gz"])
    return raw[0], raw[1:]


def m_drop_batch_row(fx):
    hdr, rows = _csv_rows(fx)
    gone = rows[MID].strip()
    _wlines_gz(fx["csv_gz"], [hdr] + rows[:MID] + rows[MID + 1:])
    return f"dropped measured row {MID} ({gone})"


def m_dup_batch_row(fx):
    hdr, rows = _csv_rows(fx)
    _wlines_gz(fx["csv_gz"], [hdr] + rows[:MID + 1] + [rows[MID]] + rows[MID + 1:])
    return f"duplicated measured row {MID}"


def m_drop_request(fx):
    d = json.load(open(fx["reqs"]))
    gone = d["reqs"].pop(600)
    _wjson(fx["reqs"], d)
    return f"dropped request {gone} from the membership input"


def m_dup_request(fx):
    d = json.load(open(fx["reqs"]))
    d["reqs"].insert(601, list(d["reqs"][600]))
    _wjson(fx["reqs"], d)
    return "duplicated one request in the membership input"


def m_reorder_dispatch(fx):
    lines = _rlines(fx["batch_src"]) if "batch_src" in fx else _rlines(fx["batches_jsonl"])
    a, b = MID, MID + 1
    if json.loads(lines[a])[0] == json.loads(lines[b])[0]:
        # identical dispatch start -> swap would be a no-op; walk to a real one
        while b + 1 < len(lines) and json.loads(lines[a])[0] == json.loads(lines[b])[0]:
            b += 1
    lines[a], lines[b] = lines[b], lines[a]
    _wlines(fx["batches_jsonl"], lines)
    return f"swapped dispatch entries {a} and {b}"


def m_dispatch_images(fx):
    lines = _rlines(fx["batches_jsonl"])
    e = json.loads(lines[MID])
    old = e[2]
    e[2] = int(old) - 1
    lines[MID] = json.dumps(e) + "\n"
    _wlines(fx["batches_jsonl"], lines)
    return f"dispatch entry {MID} total_images {old} -> {e[2]}"


def m_dispatch_finish(fx):
    lines = _rlines(fx["batches_jsonl"])
    e = json.loads(lines[MID])
    old = e[1]
    e[1] = old + 50.0
    lines[MID] = json.dumps(e) + "\n"
    _wlines(fx["batches_jsonl"], lines)
    return f"dispatch entry {MID} finish_ms {old} -> {e[1]}"


def m_sha_field(fx):
    d = json.load(open(fx["meta"]))
    old = d["provenance"]["schedule_sha256"]
    d["provenance"]["schedule_sha256"] = ("0" if old[0] != "0" else "1") + old[1:]
    _wjson(fx["meta"], d)
    return f"meta schedule_sha256 {old[:12]}... -> {d['provenance']['schedule_sha256'][:12]}..."


def m_schedule_content(fx):
    sched = json.load(open(fx["schedule"]))
    old = sched[0][1]
    sched[0][1] = int(old) - 1
    _wjson(fx["schedule"], sched)
    return f"schedule capacity at t={sched[0][0]} {old} -> {sched[0][1]}"


def m_stale_verdict(fx):
    d = json.load(open(fx["regen"]))
    old = d["batches"]
    d["batches"] = int(old) - 1
    _wjson(fx["regen"], d)
    return f"regen.stats batches {old} -> {d['batches']} while meta.gate.pass stays true"


def m_params(fx):
    d = json.load(open(fx["rep_json"]))
    old = d["encoder"]["n_params"]
    d["encoder"]["n_params"] = int(old) + 1
    _wjson(fx["rep_json"], d)
    return f"encoder n_params {old} -> {d['encoder']['n_params']}"


def m_model_dir(fx):
    d = json.load(open(fx["rep_json"]))
    old = d["encoder"]["model_dir"]
    d["encoder"]["model_dir"] = old.replace("Qwen3-VL-8B-ViT", "Qwen3-VL-4B-ViT")
    _wjson(fx["rep_json"], d)
    return f"encoder model_dir {old} -> {d['encoder']['model_dir']}"


def m_attn(fx):
    d = json.load(open(fx["rep_json"]))
    old = d["encoder"]["attn"]
    d["encoder"]["attn"] = "flash_attention_2"
    _wjson(fx["rep_json"], d)
    return f"encoder attn {old} -> flash_attention_2"


def _mut_snap(fx, k, fn):
    lines = _rlines(fx["clock"])
    idx = min(k, len(lines) - 1)
    s = json.loads(lines[idx])
    note = fn(s)
    lines[idx] = json.dumps(s) + "\n"
    _wlines(fx["clock"], lines)
    return f"clock snapshot {idx}: {note}"


def m_clock_band(fx):
    def f(s):
        old = s["sm_mhz"]
        s["sm_mhz"] = 1755
        return f"sm_mhz {old} -> 1755 (below the locked band)"
    return _mut_snap(fx, 10, f)


def m_clock_throttle(fx):
    def f(s):
        old = s["throttle_hex"]
        s["throttle_hex"] = "0x0000000000000008"
        return f"throttle_hex {old} -> 0x8 (HwSlowdown)"
    return _mut_snap(fx, 10, f)


def m_clock_tenant(fx):
    def f(s):
        s.setdefault("compute_apps", []).append({"pid": 999999, "mib": 2048})
        return "injected a 2048 MiB foreign compute app"
    return _mut_snap(fx, 10, f)


def m_dispatch_verdict(fx):
    d = json.load(open(fx["meta"]))
    d["gate"]["pass"] = False
    d["gate"]["diffs"] = [{"field": "batches", "banked": 3179, "regen": 3178}]
    _wjson(fx["meta"], d)
    return "meta.gate.pass true -> false (dispatch log failed its fidelity gate)"


def m_headline_transcription(fx):
    d = json.load(open(fx["rep_json"]))
    old = d["retimed_encoder_delay_ms"]["p99"]
    d["retimed_encoder_delay_ms"]["p99"] = round(old * 0.85, 3)
    _wjson(fx["rep_json"], d)
    return f"banked retimed p99 {old} -> {d['retimed_encoder_delay_ms']['p99']} (no operand touched)"


PROBES = [
    # (i) missing / duplicated batch or request membership
    ("P01", "i", "batch row DROPPED from batches.csv.gz", m_drop_batch_row, ("G3",), None,
     "runner.retime() itself raises IndexError on the short vector -- it cannot "
     "silently retime; G3 names the reason instead of crashing"),
    ("P02", "i", "batch row DUPLICATED in batches.csv.gz", m_dup_batch_row, ("G3",), None,
     "the ONE corruption where runner.retime() would silently return a plausible "
     "retime (p99 off by ~0.015 ms); only the row/idx alignment check stops it"),
    ("P03", "i", "request DROPPED from the membership input", m_drop_request,
     ("G4", "G5"), None, None),
    ("P04", "i", "request DUPLICATED in the membership input", m_dup_request,
     ("G4", "G5"), None, None),
    # (ii) reordered / mismatched dispatch
    ("P05", "ii", "two dispatch entries REORDERED", m_reorder_dispatch, ("G4",), None, None),
    ("P06", "ii", "dispatch entry total_images MISMATCHED", m_dispatch_images,
     ("G2", "G3"), None, None),
    ("P07", "ii", "dispatch entry finish time MISMATCHED", m_dispatch_finish,
     ("G2", "G3", "G6"), None,
     "the reconstruction gate is STRUCTURALLY BLIND to this one: it replays the "
     "dispatch log's OWN service times, so a self-consistent edit of the log "
     "reproduces itself with max_dev = 0. It is caught only by the extractor's "
     "banked dispatch digest (G2) and the redundant sim columns in the measured "
     "CSV (G3). The dispatch log carries no sha256 -- adding one is the single "
     "clearest extractor-side guard this suite identifies"),
    # (iii) changed engine / model / clock fingerprint
    ("P08", "iii", "recorded dispatch fingerprint (schedule sha256) ALTERED",
     m_sha_field, ("G2",), None, None),
    ("P09", "iii", "dispatch INPUT altered (schedule content), fingerprint now stale",
     m_schedule_content, ("G2", "G4"), None, None),
    ("P10", "iii", "banked dispatch verdict STALE (regen stats diverge, pass stays true)",
     m_stale_verdict, ("G1b",), None, None),
    ("P11", "iii", "model fingerprint ALTERED (param count)", m_params, ("G7",), None, None),
    ("P12", "iii", "model fingerprint ALTERED (model dir)", m_model_dir, ("G7",), None, None),
    ("P13", "iii", "engine fingerprint ALTERED (attn kernel)", m_attn, ("G7",), None, None),
    ("P14", "iii", "out-of-band clock sample INJECTED (SM below the gate band)",
     m_clock_band, ("G8",), None, None),
    ("P15", "iii", "fatal throttle bit INJECTED (HwSlowdown)", m_clock_throttle,
     ("G8",), None, None),
    ("P16", "iii", "foreign compute app INJECTED (single-tenancy broken)",
     m_clock_tenant, ("G8",), None, None),
    # derivation, not transcription
    ("P17", "i", "banked headline p99 EDITED with every operand intact",
     m_headline_transcription, ("G6",), None, None),
    ("P18", "ii", "dispatch fidelity verdict FAILING (meta.gate.pass = false)",
     m_dispatch_verdict, ("G1",), None,
     "the one dispatch gate the live runner truly enforces: run_trace_replay "
     "raises RuntimeError and refuses to put the GPU on an ungated dispatch log"),
]


# --------------------------------------------------------------------------
# the silent-retime hazard, made concrete
# --------------------------------------------------------------------------
def hazard_demo(fx: dict) -> list[str]:
    """What the runner's own retime() does with a mis-membered service vector
    when NO alignment gate stands in front of it. This is the failure mode
    bridge 101 names ('silently produce a retime') and the reason G3 has to
    exist extractor-side."""
    out = []
    q = json.load(open(fx["queue"]))
    spec = cell_spec(q, fx["cell"])
    batches = [json.loads(l) for l in open(fx["batches_jsonl"]) if l.strip()]
    reqs_meta = json.load(open(fx["reqs"]))
    rj = json.load(open(fx["rep_json"]))
    schedule = sorted((float(t) * 1000.0, int(c))
                      for t, c in json.load(open(fx["schedule"])))
    members, head_arr = runner.recover_membership(batches, reqs_meta)
    _hdr, rows = _csv_rows(fx)
    measured = [float(r.rstrip("\n").split(",")[4]) for r in rows]
    good_p99 = rj["retimed_encoder_delay_ms"]["p99"]
    _ns, nf, _s = runner.retime(batches, head_arr, measured, schedule)
    truth, _ = runner.request_delays(members, nf, reqs_meta)

    def divergence(service):
        _n, f_, _sl = runner.retime(batches, head_arr, service, schedule)
        d, _ = runner.request_delays(members, f_, reqs_meta)
        return (runner.pct(d)["p99"],
                max(abs(x - y) for x, y in zip(d, truth)))

    short = measured[:MID] + measured[MID + 1:]
    try:
        runner.retime(batches, head_arr, short, schedule)
        out.append("  MISSING row -> retime() returned WITHOUT error (silent retime!)")
    except Exception as ex:
        out.append(f"  MISSING row -> runner.retime() raises {type(ex).__name__} "
                   f"(it positionally indexes service_ms, so it cannot silently retime)")

    p99, dmax = divergence(measured[:MID + 1] + [measured[MID]] + measured[MID + 1:])
    out.append(f"  DUPLICATED row -> runner.retime() silently returns a retime: "
               f"p99 {p99} vs the true {good_p99} ms, worst per-request delay shifted "
               f"by {dmax:.3f} ms -- nothing but G3 stands in front of this")

    # the live resume path: start_i = len(done_rows); batch_idx is never consulted
    p99, dmax = divergence(short + [measured[-1]])
    out.append(f"  LIVE RESUME after a lost row -> run_trace_replay:685 resumes at "
               f"len(rows)={len(short)} and banks a rep with p99 {p99} vs the true "
               f"{good_p99} ms, worst per-request delay shifted by {dmax:.3f} ms; the "
               f"p99 barely moves, which is exactly what makes it silent")
    del spec
    return out


# --------------------------------------------------------------------------
def main() -> int:
    global _TMP_ROOT
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="accepted for symmetry; "
                    "this file IS the selftest and always runs it")
    ap.add_argument("--cell", default=DEFAULT_CELL)
    ap.add_argument("--rep", type=int, default=DEFAULT_REP)
    ap.add_argument("--keep", action="store_true", help="keep the temp fixtures")
    ap.add_argument("--all-reps", action="store_true",
                    help="additionally verify EVERY completed trace_replay rep in the "
                         "live campaign against all 9 gates (read-only; opt-in because "
                         "the campaign is still running and an in-flight rep would "
                         "read as a spurious failure)")
    a = ap.parse_args()

    ok = True
    td = tempfile.mkdtemp(prefix="silicon_neg_")
    _TMP_ROOT = Path(td)
    try:
        base = build_fixture(_TMP_ROOT / "clean", a.cell, a.rep)
        print(f"silicon negative gates -- {a.cell} rep{a.rep:03d} "
              f"({len(base['daemons'])} runner pids on record), fixture {base['root']}")

        # the campaign is LIVE: prove the write guard refuses it before anything else
        try:
            _guard(CAMPAIGN / "reps" / a.cell / f"rep{a.rep:03d}" / "rep.json")
            print("FAIL: write guard did NOT refuse a live-campaign path")
            ok = False
        except AssertionError:
            print(f"PASS: write guard refuses every path outside {_TMP_ROOT} "
                  f"(the live campaign is never opened for writing)")

        errs = verify(base)
        good = not errs
        print(f"{'PASS' if good else 'FAIL'}: CLEAN copy verifies "
              f"({len(errs)} errors over 9 gates)")
        for e in errs[:8]:
            print("   ", e)
        ok &= good
        if not good:
            print("SILICON-NEGATIVE-GATES: FAIL (clean baseline broken; probes not run)")
            return 1

        print("  LIVE-PATH EXPOSURE -- the silent-retime hazard, demonstrated with "
              "runner.retime() itself:")
        for line in hazard_demo(base):
            print(line)

        n_caught = 0
        gaps = []
        for pid_, cls, title, mutate, expect, known_gap, struct_note in PROBES:
            fx = clone(base, _TMP_ROOT / pid_)
            note = mutate(fx)
            if note is None:
                print(f"FAIL: {pid_} ({cls}) {title} -- mutation did not apply "
                      f"(pattern drift, test bug)")
                ok = False
                continue
            errs = verify(fx)
            hit = sorted({e.split("/", 1)[0] for e in errs})
            want = [g for g in expect if g in hit]
            if want:
                n_caught += 1
                first = next(e for e in errs if e.startswith(want[0]))
                print(f"PASS: {pid_} [{cls}] {title}")
                print(f"        mutation : {note}")
                print(f"        caught by: {'+'.join(hit)}  ({LIVE_ENFORCEMENT[want[0]]})")
                print(f"        reason   : {first[:200]}")
                if struct_note:
                    print(f"        note     : {struct_note}")
            elif known_gap:
                print(f"EXPECTED-FAIL: {pid_} [{cls}] {title}")
                print(f"        mutation : {note}")
                print(f"        gap      : {known_gap}")
                gaps.append((pid_, known_gap))
            else:
                ok = False
                print(f"FAIL: {pid_} [{cls}] {title} -- expected {expect}, got "
                      f"{hit or 'NO ERROR AT ALL (silent retime)'}")
                print(f"        mutation : {note}")
                for e in errs[:4]:
                    print("       ", e)

        print()
        print("live-path enforcement of each gate (the campaign runner is frozen; "
              "post-hoc-only gates are the extractor-side guards to add after it stops):")
        for g, s in LIVE_ENFORCEMENT.items():
            print(f"  {g:4s} {s}")
        if gaps:
            print()
            print("EXPECTED-FAIL probes (real gaps, deliberately not patched):")
            for pid_, why in gaps:
                print(f"  {pid_}: {why}")
        if a.all_reps:
            print()
            print("every completed trace_replay rep in the live campaign, "
                  "against all 9 gates:")
            n_ok = n_seen = 0
            for rp in sorted(CAMPAIGN.glob("reps/*/rep*/rep.json")):
                try:
                    d = json.load(open(rp))
                except (OSError, json.JSONDecodeError):
                    continue
                if "reconstruction_gate" not in d:
                    continue                      # fn_sweep cell, different shape
                if not (rp.parent / "batches.csv.gz").exists():
                    print(f"  SKIP {d['cell']} rep{d['rep']:03d} (in flight)")
                    continue
                n_seen += 1
                fxr = build_fixture(_TMP_ROOT / f"live_{d['cell']}_{d['rep']}",
                                    d["cell"], d["rep"])
                errs = verify(fxr)
                n_ok += not errs
                if errs:
                    ok = False
                    print(f"  FAIL {d['cell']} rep{d['rep']:03d} ({len(errs)} errors)")
                    for e in errs[:4]:
                        print("       ", e)
            print(f"  {n_ok}/{n_seen} completed reps verify clean")

        print()
        print(f"SILICON-NEGATIVE-GATES: "
              f"{'ALL PASS' if ok else 'FAIL'} "
              f"({n_caught}/{len(PROBES)} corruptions fail loudly"
              + (f", {len(gaps)} expected-fail gaps" if gaps else "") + ")")
        return 0 if ok else 1
    finally:
        if a.keep:
            print(f"(fixtures kept at {td})")
        else:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
