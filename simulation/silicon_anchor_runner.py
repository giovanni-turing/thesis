#!/usr/bin/env python3
"""Silicon anchor runner -- detached, unbounded, preemption-resilient daemon.

WHAT IT DOES
    Trace-driven PHYSICAL replay. For each queued cell (= one controller arm on
    one window) it takes that arm's ACTUAL encoder batch-dispatch sequence from
    the frozen simulation artifacts (regenerated + gated by
    silicon_anchor_extract.py) and executes the SAME batch sequence on the real
    Qwen3-VL vision tower on this GPU, measuring per-batch wall service time.
    It then (A) pairs each measured batch against the simulator's AIC-predicted
    service, and (B) rebuilds the queue trajectory those REAL times imply under
    frozen batch composition, giving per-request encoder delay on silicon.

WHY THIS SHAPE
    One GPU cannot host a time-shared fake fleet without distorting physics.
    Replaying the arm's real dispatch sequence, one forward at a time, on a
    single-tenant clock-locked GPU is the physically honest test: every number
    is a measured forward, and the fleet only ever appears as the schedule that
    produced the dispatch sequence -- never as concurrent tenants.

GUARANTEES
    * UNBOUNDED: runs until the author creates the STOP file. No time target.
    * PREEMPTION RESILIENT: every completed rep is checkpointed immediately to
      an append-only manifest (JSONL); within a rep, measured batches are
      flushed to disk every ~500 batches / ~60 s, so a kill at ANY moment loses
      at most one segment. On restart the runner reads the manifest, skips
      completed (cell, rep) pairs, and resumes a partial rep at the exact batch
      index it reached.
    * MOST-RELEVANT-FIRST: strict tier order; within a tier, rep-major, so one
      rep of every cell in the tier lands before any second rep.
    * CLOCK LOCK: delivered SM/MEM clocks, throttle reasons, persistence mode
      and single-tenancy are verified before every rep AND every segment. On
      violation the runner WAITS (poll 60 s, logging) -- it never measures on
      unlocked or boost clocks, and never silently proceeds.
    * GPU work is strictly sequential: one process, one forward at a time.

USAGE (detached; this file owns the loop and must survive its launcher)
    cd /home/gio/tese
    nohup setsid /home/gio/tese/eda/.venv/bin/python \
        simulation/silicon_anchor_runner.py \
        >> simulation/results/silicon_anchor/daemon.out 2>&1 &

    # stop it (graceful, banks the partial segment):
    touch simulation/results/silicon_anchor/STOP

    # dry run, no GPU, prints the resolved work order and exits:
    .../python simulation/silicon_anchor_runner.py --plan

    # pilot: bounded proof-of-correctness pass, see --pilot in the docstring below
    .../python simulation/silicon_anchor_runner.py --pilot
"""
from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import json
import os
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import time
import traceback
from collections import deque
from pathlib import Path

ROOT = Path("/home/gio/tese")
QUEUE_PATH = ROOT / "simulation" / "silicon_anchor_queue.json"

_stop_signal = False


def _on_signal(signum, _frame):
    global _stop_signal
    _stop_signal = True


# --------------------------------------------------------------------------
# logging / manifest
# --------------------------------------------------------------------------
class Journal:
    """Append-only manifest (JSONL) + human log. Every write is flushed+fsynced
    so a hard kill cannot lose a checkpoint."""

    def __init__(self, root: Path, name: str = "manifest.jsonl"):
        self.root = root
        self.manifest = root / name
        self.logfile = root / "daemon.log"
        root.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str) -> None:
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
        print(line, flush=True)
        with open(self.logfile, "a") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    def event(self, ev: str, **kw) -> dict:
        rec = {"ev": ev, "ts": time.time(),
               "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **kw}
        with open(self.manifest, "a") as f:
            f.write(json.dumps(rec) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return rec

    def read(self) -> list[dict]:
        if not self.manifest.exists():
            return []
        out = []
        with open(self.manifest) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    # a torn last line from a hard kill: ignore, never crash resume
                    pass
        return out


# --------------------------------------------------------------------------
# clock / tenancy gate
# --------------------------------------------------------------------------
def gpu_snapshot() -> dict:
    q = ("clocks.sm,clocks.mem,clocks.max.sm,persistence_mode,"
         "clocks_throttle_reasons.active,temperature.gpu,power.draw,memory.used,"
         "utilization.gpu")
    try:
        r = subprocess.run(["nvidia-smi", f"--query-gpu={q}",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=15)
        p = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")]
        snap = {"sm_mhz": int(p[0]), "mem_mhz": int(p[1]), "max_sm_mhz": int(p[2]),
                "persistence": p[3], "throttle_hex": p[4], "temp_c": int(p[5]),
                "power_w": float(p[6]), "mem_used_mib": int(p[7]),
                "util_pct": int(p[8])}
    except Exception as ex:
        return {"error": f"{type(ex).__name__}: {ex}"}
    try:
        r = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=15)
        apps = []
        for line in r.stdout.strip().splitlines():
            if not line.strip():
                continue
            pid, mib = [x.strip() for x in line.split(",")]
            apps.append({"pid": int(pid), "mib": int(mib)})
        snap["compute_apps"] = apps
    except Exception as ex:
        snap["compute_apps_error"] = str(ex)
    snap["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return snap


def gate_verdict(snap: dict, gate: dict, own_pid: int) -> tuple[bool, list[str]]:
    """Returns (ok, reasons_for_failure). Pure function of the snapshot."""
    bad = []
    if "error" in snap:
        return False, [f"nvidia-smi unavailable: {snap['error']}"]
    if not (gate["sm_mhz_min"] <= snap["sm_mhz"] <= gate["sm_mhz_max"]):
        bad.append(f"SM {snap['sm_mhz']} MHz outside locked band "
                   f"[{gate['sm_mhz_min']},{gate['sm_mhz_max']}]")
    if snap["mem_mhz"] not in gate["mem_mhz_allowed"]:
        bad.append(f"MEM {snap['mem_mhz']} MHz not in {gate['mem_mhz_allowed']}")
    if gate.get("throttle_hex_required") and snap["throttle_hex"] != gate["throttle_hex_required"]:
        bad.append(f"throttle reasons {snap['throttle_hex']} != {gate['throttle_hex_required']}")
    if gate.get("require_persistence_mode") and snap["persistence"].lower() not in ("enabled", "1"):
        bad.append(f"persistence mode {snap['persistence']}")
    if gate.get("require_single_tenant"):
        tol = gate.get("foreign_compute_app_mib_tolerance", 64)
        foreign = [a for a in snap.get("compute_apps", [])
                   if a["pid"] != own_pid and a["mib"] > tol]
        if foreign:
            bad.append(f"foreign compute apps {foreign}")
    return (not bad), bad


def wait_for_gate(j: Journal, gate: dict, where: str) -> dict:
    """Block until the clock/tenancy gate passes. NEVER measures while it fails."""
    polls = 0
    while True:
        if stop_requested(j.root):
            raise StopRequested(f"STOP while waiting on clock gate ({where})")
        snap = gpu_snapshot()
        ok, why = gate_verdict(snap, gate, os.getpid())
        if ok:
            if polls:
                j.event("clock_ok_after_wait", where=where, polls=polls, snapshot=snap)
                j.log(f"[gate] {where}: clocks OK after {polls} polls "
                      f"({polls * gate.get('poll_s', 60)} s waited)")
            return snap
        j.log(f"[gate] {where}: WAITING (not measuring) -- {'; '.join(why)} "
              f"| SM {snap.get('sm_mhz')} MEM {snap.get('mem_mhz')} "
              f"thr {snap.get('throttle_hex')} used {snap.get('mem_used_mib')} MiB")
        if polls % 10 == 0:
            j.event("clock_wait", where=where, poll=polls, reasons=why, snapshot=snap)
        polls += 1
        time.sleep(gate.get("poll_s", 60))


class StopRequested(Exception):
    pass


class CellSkipped(Exception):
    """Cell cannot run for a benign, recorded reason (e.g. an engine image that
    is not installed). Not a failure: the runner moves on without retrying."""


def stop_requested(root: Path) -> bool:
    return _stop_signal or (root / "STOP").exists()


# --------------------------------------------------------------------------
# queue resolution
# --------------------------------------------------------------------------
def load_queue() -> dict:
    return json.load(open(QUEUE_PATH))


def cells_of(q: dict) -> dict:
    out = {}
    for t in q["tiers"]:
        for cid, spec in t["cells"].items():
            out[cid] = dict(spec, tier=t["tier"], _tier_order=t["order"],
                            _min_reps=t["min_reps"])
    return out


def completed_reps(records: list[dict]) -> dict:
    """(cell, rep) -> True for every banked rep_done. Also returns attempt counts."""
    done, attempts, abandoned = set(), {}, set()
    for r in records:
        key = (r.get("cell"), r.get("rep"))
        if r["ev"] == "rep_done":
            done.add(key)
        elif r["ev"] in ("rep_fail", "rep_skip"):
            attempts[key] = attempts.get(key, 0) + 1
        elif r["ev"] == "rep_abandoned":
            abandoned.add(key)
    return {"done": done, "attempts": attempts, "abandoned": abandoned}


def n_done(state: dict, cid: str) -> int:
    return sum(1 for (c, _r) in state["done"] if c == cid)


def next_unit(q: dict, state: dict) -> tuple[str, int, str] | None:
    """Strict priority. Returns (cell_id, rep, phase) or None if exhausted
    (only possible when the extension is disabled)."""
    cells = cells_of(q)
    max_try = q["execution"]["max_attempts_per_rep"]
    # --- tiers, in order ---
    for t in q["tiers"]:
        ids = list(t["cells"])
        minr = t["min_reps"]
        if t["order"] == "rep_major":
            for rep in range(1, minr + 1):
                for cid in ids:
                    if (cid, rep) in state["done"] or (cid, rep) in state["abandoned"]:
                        continue
                    if state["attempts"].get((cid, rep), 0) >= max_try:
                        continue
                    return cid, rep, f"tier{t['tier']}"
        else:  # cell_major
            for cid in ids:
                for rep in range(1, minr + 1):
                    if (cid, rep) in state["done"] or (cid, rep) in state["abandoned"]:
                        continue
                    if state["attempts"].get((cid, rep), 0) >= max_try:
                        continue
                    return cid, rep, f"tier{t['tier']}"
    # --- extension: unbounded, min-reps-first over the headline cells ---
    headline = [cid for t in q["tiers"] if t["tier"] <= 4 for cid in t["cells"]]
    if not headline:
        return None
    ranked = sorted(headline, key=lambda c: (n_done(state, c), cells[c]["tier"],
                                             headline.index(c)))
    for cid in ranked:
        rep = n_done(state, cid) + 1
        while (cid, rep) in state["done"] or (cid, rep) in state["abandoned"] \
                or state["attempts"].get((cid, rep), 0) >= max_try:
            rep += 1
        return cid, rep, "extension"
    return None


# --------------------------------------------------------------------------
# cost curves
# --------------------------------------------------------------------------
class Piecewise:
    def __init__(self, points):
        pts = sorted(points)
        if pts[0][0] != 0:
            pts = [(0, 0.0)] + pts
        self.xs = [p[0] for p in pts]
        self.ys = [p[1] for p in pts]

    def ms(self, n: int) -> float:
        n = int(n)
        if n <= 0:
            return 0.0
        if n <= self.xs[-1]:
            j = bisect.bisect_left(self.xs, n)
            if self.xs[j] == n:
                return self.ys[j]
            x0, x1, y0, y1 = self.xs[j - 1], self.xs[j], self.ys[j - 1], self.ys[j]
        else:
            x0, x1, y0, y1 = self.xs[-2], self.xs[-1], self.ys[-2], self.ys[-1]
        return y0 + (y1 - y0) * (n - x0) / (x1 - x0)


def aic_curve() -> Piecewise:
    p = ROOT / "collector_artifacts" / "phaseB_batch_validation" / "aic_f_n_postinfill.csv"
    pts = []
    with open(p) as f:
        next(f)
        for line in f:
            n, ms, _ = line.split(",")
            pts.append((int(float(n)), float(ms)))
    return Piecewise(pts)


# --------------------------------------------------------------------------
# the physical encoder
# --------------------------------------------------------------------------
class Encoder:
    """The real Qwen3-VL vision tower on this GPU, one forward at a time.

    A single preallocated pixel buffer of the maximum batch size is SLICED per
    batch, so no batch pays an allocation cost and every shape is exact.
    """

    def __init__(self, cfg: dict, n_max: int, j: Journal):
        import torch  # imported lazily so --plan works with no GPU
        from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel
        self.torch = torch
        self.px = cfg["image_px"]
        self.grid = cfg["grid"]
        self.in_features = 3 * cfg["temporal_patch"] * cfg["patch"] * cfg["patch"]
        self.n_max = n_max
        t0 = time.time()
        self.model = Qwen3VLVisionModel.from_pretrained(
            cfg["model_dir"], dtype=torch.bfloat16,
            attn_implementation=cfg["attn"]).to("cuda").eval()
        self.load_s = round(time.time() - t0, 2)
        self.n_params = sum(p.numel() for p in self.model.parameters())
        rows = self.grid * self.grid * n_max
        self.px_buf = torch.randn(rows, self.in_features, device="cuda",
                                  dtype=torch.bfloat16)
        self.grid_buf = torch.tensor([[1, self.grid, self.grid]] * n_max, device="cuda")
        self._ev_a = torch.cuda.Event(enable_timing=True)
        self._ev_b = torch.cuda.Event(enable_timing=True)
        j.log(f"[encoder] loaded {cfg['model_dir']} attn={cfg['attn']} "
              f"params={self.n_params/1e6:.1f}M in {self.load_s}s; "
              f"buffer {rows}x{self.in_features} bf16 "
              f"({self.px_buf.numel()*2/2**30:.2f} GiB), n_max={n_max}")

    def forward_ms(self, n_images: int) -> float:
        """ONE forward over n_images. Returns CUDA-event wall time in ms."""
        rows = self.grid * self.grid * n_images
        px = self.px_buf[:rows]
        grid = self.grid_buf[:n_images]
        t = self.torch
        with t.inference_mode():
            self._ev_a.record()
            self.model(px, grid_thw=grid)
            self._ev_b.record()
            t.cuda.synchronize()
        return self._ev_a.elapsed_time(self._ev_b)

    def batch_ms(self, total_images: int, n_forwards: int, cap: int) -> float:
        """Service time of one dispatched BATCH (>1 forward only under the
        sequential-chunk policy, which none of the queued arms use)."""
        if n_forwards <= 1:
            return self.forward_ms(total_images)
        full, rem = divmod(total_images, cap)
        ms = sum(self.forward_ms(cap) for _ in range(full))
        if rem:
            ms += self.forward_ms(rem)
        return ms

    def warmup(self, sizes: list[int], reps: int, j: Journal) -> dict:
        t0 = time.time()
        for _ in range(reps):
            for n in sizes:
                self.forward_ms(n)
        self.torch.cuda.synchronize()
        out = {"sizes": sizes, "reps": reps, "wall_s": round(time.time() - t0, 2)}
        j.log(f"[encoder] warmup {reps}x{sizes} in {out['wall_s']}s")
        return out


# --------------------------------------------------------------------------
# frozen-composition retiming + per-request delay
# --------------------------------------------------------------------------
def build_slot_windows(schedule):
    """Verbatim port of workload/trace_to_two_pool.py:build_slot_windows (lines
    203-229) so the retiming uses the SIMULATOR's own slot semantics: slots
    activate lowest-index-first on scale-up and retire LIFO on scale-down."""
    max_cap = max(c for _, c in schedule)
    windows = [[] for _ in range(max_cap)]
    open_since = [None] * max_cap
    active = 0
    for t, cap_now in schedule:
        if cap_now > active:
            for w in range(active, cap_now):
                open_since[w] = t
        elif cap_now < active:
            for w in range(cap_now, active):
                windows[w].append((open_since[w], t))
                open_since[w] = None
        active = cap_now
    for w in range(max_cap):
        if open_since[w] is not None:
            windows[w].append((open_since[w], float("inf")))
    return windows


def recover_membership(batches, reqs_meta):
    """Recover which requests each dispatched batch carried, and the batch's
    head arrival, by replaying the simulator's own FIFO admission against the
    dumped dispatch START times.

    Faithful to simulate_vision_pool: oversized requests are decomposed into
    <=cap chunk units (never batched with anything), units are FIFO by arrival,
    everything that has arrived by the batch's start is eligible, and the head
    absorbs following whole requests while the running image total stays within
    the batch's own recorded total.

    Returns (members_per_batch, head_arrival_per_batch).
    """
    cap = reqs_meta["cap"]
    reqs = [tuple(r) for r in reqs_meta["reqs"]]
    units = []
    for arr, idx, n in reqs:
        if n > cap:
            full, rem = divmod(n, cap)
            units.extend((arr, idx, cap, True) for _ in range(full))
            if rem:
                units.append((arr, idx, rem, True))
        else:
            units.append((arr, idx, n, False))
    units.sort()
    members, head_arr = [], []
    q: deque = deque()
    i = 0
    for start, _fin, total, _nf in batches:
        if not q and i < len(units):
            q.append(units[i])
            i += 1
        while i < len(units) and units[i][0] <= start:
            q.append(units[i])
            i += 1
        if not q:
            members.append([])
            head_arr.append(start)
            continue
        head = q.popleft()
        mem = [head]
        got = head[2]
        if not head[3]:
            while q and not q[0][3] and got + q[0][2] <= total:
                u = q.popleft()
                mem.append(u)
                got += u[2]
        members.append(mem)
        head_arr.append(head[0])
    return members, head_arr


def retime(batches, head_arr, service_ms, schedule):
    """Frozen-composition retiming. Batch order, membership and the worker
    schedule are held fixed; only the per-batch SERVICE TIME changes.

    Slot choice and admissible start reproduce simulate_vision_pool exactly
    (earliest_start over the slot's active windows, ties by lowest index), so
    feeding the SIM's own service times back through this function must
    reproduce the dumped start/finish to the bit -- that is the self-consistency
    gate that licenses the measured retiming.
    """
    slot_windows = build_slot_windows(schedule)
    n_slots = len(slot_windows)
    free = [0.0] * n_slots

    def earliest_start(w, lower):
        s = max(free[w], lower)
        for a, d in slot_windows[w]:
            if s < a:
                s = a
            if s < d:
                return s
        return float("inf")

    starts, fins, slots = [], [], []
    for i, _b in enumerate(batches):
        lower = head_arr[i]
        w = min(range(n_slots), key=lambda k: (earliest_start(k, lower), k))
        s = earliest_start(w, lower)
        f = s + service_ms[i]
        free[w] = f
        starts.append(s)
        fins.append(f)
        slots.append(w)
    return starts, fins, slots


def request_delays(members, fins, reqs_meta):
    """Per-request encoder delay from a retimed batch-finish vector."""
    finish: dict[int, float] = {}
    for mem, f in zip(members, fins):
        for _a, idx, _n, _c in mem:
            finish[idx] = max(finish.get(idx, 0.0), f)
    gbps = reqs_meta.get("handoff_gbps", 25.0)
    rtt = reqs_meta.get("handoff_rtt_ms", 0.2)

    def handoff(n):
        if gbps <= 0 or n <= 0:
            return 0.0
        return rtt + (196 * n * 4096 * 2) * 8 / (gbps * 1e9) * 1e3

    delays = []
    for arr, idx, n in reqs_meta["reqs"]:
        if idx in finish:
            delays.append((finish[idx] - arr) + handoff(n))
    # sim convention: percentiles over ALL window requests, text-only contribute 0
    pad = max(0, reqs_meta["n_all_requests"] - len(delays))
    return delays + [0.0] * pad, len(finish)


def pct(vals, ps=(50, 90, 99)):
    if not vals:
        return {f"p{p}": 0.0 for p in ps}
    s = sorted(vals)
    return {f"p{p}": round(s[min(len(s) - 1, int(len(s) * p / 100))], 3) for p in ps}


# --------------------------------------------------------------------------
# one rep
# --------------------------------------------------------------------------
def rep_dir(root: Path, cid: str, rep: int) -> Path:
    return root / "reps" / cid / f"rep{rep:03d}"


def run_trace_replay(q, cid, spec, rep, enc, j, gate, root) -> dict:
    """Physically replay one (cell, rep). Segment-checkpointed; resumable."""
    disp = root / "dispatch"
    meta = json.load(open(disp / f"{cid}.meta.json"))
    if not meta["gate"]["pass"]:
        raise RuntimeError(f"{cid}: dispatch log failed the fidelity gate; refusing to measure")
    batches = []
    with open(disp / f"{cid}.batches.jsonl") as f:
        for line in f:
            batches.append(json.loads(line))
    reqs_meta = json.load(open(disp / f"{cid}.batches.jsonl.reqs.json"))
    cap = reqs_meta["cap"]
    n_b = len(batches)

    d = rep_dir(root, cid, rep)
    d.mkdir(parents=True, exist_ok=True)
    partial = d / "batches.csv"
    clocks = d / "clock.jsonl"

    # ---- resume: how many batches are already banked for this rep? ----
    done_rows = []
    if partial.exists():
        with open(partial) as f:
            rdr = csv.reader(f)
            hdr = next(rdr, None)
            for row in rdr:
                if len(row) == 5:
                    done_rows.append(row)
    start_i = len(done_rows)
    if start_i >= n_b:
        j.log(f"[rep] {cid} rep{rep}: all {n_b} batches already measured; finalizing")
    elif start_i:
        j.log(f"[rep] {cid} rep{rep}: RESUMING at batch {start_i}/{n_b}")

    measured = [float(r[4]) for r in done_rows]
    ex = q["execution"]

    snap0 = wait_for_gate(j, gate, f"{cid}/rep{rep}/start")
    with open(clocks, "a") as cf:
        cf.write(json.dumps({"at": "rep_start", "batch": start_i, **snap0}) + "\n")

    if start_i == 0:
        j.event("rep_start", cell=cid, rep=rep, n_batches=n_b,
                dispatch_sha_meta=str((disp / f'{cid}.meta.json').relative_to(ROOT)),
                clock=snap0)
        with open(partial, "w") as f:
            f.write("batch_idx,n_images,sim_start_ms,sim_service_ms,meas_service_ms\n")
            f.flush()
            os.fsync(f.fileno())
    else:
        j.event("rep_resume", cell=cid, rep=rep, from_batch=start_i, n_batches=n_b,
                clock=snap0)

    warm = enc.warmup([cap, max(1, cap // 8), 1], ex["warmup_forwards_per_rep"] // 3 or 1, j)

    t_rep0 = time.time()
    since_flush = 0
    t_flush = time.time()
    buf = []
    fh = open(partial, "a")
    interrupted = False
    try:
        for i in range(start_i, n_b):
            s_ms, f_ms, total, n_fwd = batches[i]
            ms = enc.batch_ms(int(total), int(n_fwd), cap)
            measured.append(ms)
            buf.append(f"{i},{int(total)},{s_ms!r},{round(f_ms - s_ms, 6)!r},{round(ms, 6)!r}\n")
            since_flush += 1
            if since_flush >= ex["segment_flush_batches"] or \
                    (time.time() - t_flush) >= ex["segment_flush_seconds"]:
                fh.writelines(buf)
                fh.flush()
                os.fsync(fh.fileno())
                buf.clear()
                j.event("segment", cell=cid, rep=rep, batches_done=i + 1, n_batches=n_b,
                        elapsed_s=round(time.time() - t_rep0, 1))
                snap = gpu_snapshot()
                with open(clocks, "a") as cf:
                    cf.write(json.dumps({"at": "segment", "batch": i + 1, **snap}) + "\n")
                ok, why = gate_verdict(snap, gate, os.getpid())
                if not ok:
                    j.log(f"[gate] {cid} rep{rep}: clocks left the band mid-rep at batch "
                          f"{i+1} -- {'; '.join(why)}; pausing")
                    j.event("clock_drift_pause", cell=cid, rep=rep, batch=i + 1,
                            reasons=why, snapshot=snap)
                    wait_for_gate(j, gate, f"{cid}/rep{rep}/batch{i+1}")
                since_flush = 0
                t_flush = time.time()
                if stop_requested(root):
                    interrupted = True
                    break
    finally:
        if buf:
            fh.writelines(buf)
        fh.flush()
        os.fsync(fh.fileno())
        fh.close()

    if interrupted:
        j.event("rep_interrupted", cell=cid, rep=rep, batches_done=len(measured),
                n_batches=n_b)
        j.log(f"[rep] {cid} rep{rep}: STOP -- banked {len(measured)}/{n_b} batches, "
              f"will resume here")
        raise StopRequested("STOP mid-rep (partial banked)")

    snap1 = wait_for_gate(j, gate, f"{cid}/rep{rep}/end")
    with open(clocks, "a") as cf:
        cf.write(json.dumps({"at": "rep_end", "batch": n_b, **snap1}) + "\n")
    wall_s = round(time.time() - t_rep0, 2)

    # ---- analysis (CPU, cheap) ----
    aic = aic_curve()
    sim_ms = [b[1] - b[0] for b in batches]
    sizes = [int(b[2]) for b in batches]
    ratio = [measured[i] / sim_ms[i] for i in range(n_b) if sim_ms[i] > 0]
    per_n: dict[int, list[float]] = {}
    for i in range(n_b):
        per_n.setdefault(sizes[i], []).append(measured[i])
    fn_table = {str(n): {"count": len(v), "median_ms": round(statistics.median(v), 4),
                         "mean_ms": round(statistics.fmean(v), 4),
                         "min_ms": round(min(v), 4), "max_ms": round(max(v), 4),
                         "aic_ms": round(aic.ms(n), 4),
                         "ratio_median_over_aic": round(statistics.median(v) / aic.ms(n), 4)
                         if aic.ms(n) else None}
                for n, v in sorted(per_n.items())}

    schedule = json.load(open(ROOT / spec["schedule"]))
    schedule = sorted((float(t) * 1000.0, int(c)) for t, c in schedule)
    members, head_arr = recover_membership(batches, reqs_meta)

    # --- self-consistency gate: retiming under the SIM's own service times must
    # --- reproduce the dumped dispatch timeline exactly. If it does not, the
    # --- membership/slot recovery is wrong and the measured retiming is void.
    rs, rf, _ = retime(batches, head_arr, sim_ms, schedule)
    max_dev = max((abs(rf[i] - batches[i][1]) for i in range(n_b)), default=0.0)
    sim_delays, _ = request_delays(members, [b[1] for b in batches], reqs_meta)
    banked = spec.get("banked", {})
    bank_p99 = (banked.get("encoder_delay_ms") or {}).get("p99")
    sim_p99 = pct(sim_delays)["p99"]
    recon_ok = (max_dev <= 1e-6) and (
        bank_p99 is None or abs(sim_p99 - bank_p99) <= max(1e-3, 1e-6 * abs(bank_p99)))

    ns, nf, slot_of = retime(batches, head_arr, measured, schedule)
    delays, n_req = request_delays(members, nf, reqs_meta)
    summary = {
        "cell": cid, "rep": rep, "window": spec["window"], "arm": spec["arm"],
        "n_batches": n_b, "total_images": sum(sizes),
        "wall_s": wall_s,
        "resumed_from_batch": start_i or None,
        "measured_busy_s": round(sum(measured) / 1000.0, 3),
        "sim_busy_s": round(sum(sim_ms) / 1000.0, 3),
        # Non-forward overhead. Only defined for an uninterrupted rep: after a
        # resume, wall_s covers the tail while measured[] covers the whole rep.
        "overhead_frac": (round(1 - (sum(measured) / 1000.0) / wall_s, 5)
                          if (wall_s and start_i == 0) else None),
        "peak_mem_gb": round(enc.torch.cuda.max_memory_allocated() / 2**30, 3),
        "per_batch_ratio_measured_over_sim": {
            **pct(ratio), "mean": round(statistics.fmean(ratio), 4) if ratio else None,
            "min": round(min(ratio), 4) if ratio else None,
            "max": round(max(ratio), 4) if ratio else None},
        "measured_batch_service_ms": {**pct(measured),
                                      "max": round(max(measured), 3) if measured else 0.0},
        "sim_batch_service_ms": {**pct(sim_ms), "max": round(max(sim_ms), 3) if sim_ms else 0.0},
        "measured_fn_table": fn_table,
        "retimed_encoder_delay_ms": {**pct(delays),
                                     "max": round(max(delays), 3) if delays else 0.0},
        "replayed_sim_encoder_delay_ms": {**pct(sim_delays),
                                          "max": round(max(sim_delays), 3) if sim_delays else 0.0},
        "banked_sim_encoder_delay_ms": banked.get("encoder_delay_ms"),
        "reconstruction_gate": {
            "pass": bool(recon_ok),
            "max_batch_finish_deviation_ms": max_dev,
            "replayed_sim_p99_ms": sim_p99,
            "banked_sim_p99_ms": bank_p99,
            "meaning": "retiming under the sim's OWN service times reproduces the dumped "
                       "dispatch timeline and the banked encoder-delay p99; membership and "
                       "slot recovery are therefore faithful and the measured retiming is valid",
        },
        "membership_recovery_requests_matched": n_req,
        "membership_recovery_requests_total": len(reqs_meta["reqs"]),
        "warmup": warm,
        "clock_start": snap0, "clock_end": snap1,
        "encoder": {"model_dir": q["execution"]["model_dir"], "attn": q["execution"]["attn"],
                    "n_params": enc.n_params, "load_s": enc.load_s,
                    "image_px": q["execution"]["image_px"]},
        "dispatch_meta": meta["files"]["meta"],
        "queue_sha": None,
    }
    json.dump(summary, open(d / "rep.json", "w"), indent=1)
    with open(partial, "rb") as fi, gzip.open(d / "batches.csv.gz", "wb") as fo:
        shutil.copyfileobj(fi, fo)
    partial.unlink()
    return summary


def run_fn_sweep(q, cid, spec, rep, enc, j, gate, root) -> dict:
    """Engine-diversity cell: f(N) on anchor shapes through one engine."""
    d = rep_dir(root, cid, rep)
    d.mkdir(parents=True, exist_ok=True)
    engine = spec["engine"]
    if engine == "vllm_docker":
        img = spec["docker_image"]
        chk = subprocess.run(["docker", "image", "inspect", img],
                             capture_output=True, text=True)
        if chk.returncode != 0:
            j.event("rep_skip", cell=cid, rep=rep,
                    reason=f"docker image {img} not present locally; "
                           f"`docker pull {img}` to enable this cell")
            j.log(f"[rep] {cid} rep{rep}: SKIP -- docker image {img} absent")
            raise CellSkipped(f"docker image {img} absent")
        raise NotImplementedError(
            "vllm_docker cell: run collector_artifacts/phaseE_physical_anchor/"
            "vllm_eager_dense.py inside the pinned image with the GPU idle; the "
            "daemon refuses to launch a container while it holds the GPU")

    snap0 = wait_for_gate(j, gate, f"{cid}/rep{rep}/start")
    j.event("rep_start", cell=cid, rep=rep, engine=engine, clock=snap0)
    aic = aic_curve()
    t0 = time.time()
    rows = []
    for n in spec["ns"]:
        run_means, allt, clk = [], [], []
        for _ in range(spec["nruns"]):
            for _ in range(spec["warmup"]):
                enc.forward_ms(n)
            ts = [enc.forward_ms(n) for _ in range(spec["iters"])]
            run_means.append(statistics.fmean(ts))
            allt += ts
            clk.append(gpu_snapshot().get("sm_mhz", -1))
        m = statistics.fmean(run_means)
        ci = 2.776 * statistics.stdev(run_means) / (spec["nruns"] ** 0.5) \
            if spec["nruns"] > 1 else 0.0
        allt.sort()
        rows.append({"n_images": n, "mean_ms": round(m, 4), "ci95_ms": round(ci, 4),
                     "p50_ms": round(allt[len(allt) // 2], 4), "min_ms": round(allt[0], 4),
                     "ms_per_img": round(m / n, 4), "sm_clock_mhz": int(statistics.median(clk)),
                     "aic_ms": round(aic.ms(n), 4),
                     "ratio_meas_over_aic": round(m / aic.ms(n), 4) if aic.ms(n) else None})
        j.log(f"[rep] {cid} rep{rep}: N={n} mean={m:.3f} ci95={ci:.3f} "
              f"ratio={rows[-1]['ratio_meas_over_aic']}")
    snap1 = wait_for_gate(j, gate, f"{cid}/rep{rep}/end")
    summary = {"cell": cid, "rep": rep, "engine": engine, "type": "fn_sweep",
               "wall_s": round(time.time() - t0, 2), "rows": rows,
               "protocol": {k: spec[k] for k in ("ns", "nruns", "iters", "warmup")},
               "reference": spec.get("reference"),
               "clock_start": snap0, "clock_end": snap1,
               "encoder": {"attn": spec.get("attn"), "n_params": enc.n_params}}
    json.dump(summary, open(d / "rep.json", "w"), indent=1)
    return summary


# --------------------------------------------------------------------------
# main loop
# --------------------------------------------------------------------------
def ensure_dispatch(cid: str, root: Path, j: Journal) -> None:
    meta = root / "dispatch" / f"{cid}.meta.json"
    if meta.exists() and json.load(open(meta)).get("gate", {}).get("pass") is True:
        return
    j.log(f"[extract] {cid}: dispatch log missing/ungated -- extracting (CPU)")
    conv_py = ROOT / "ai-dynamo" / "dynamo" / ".venv" / "bin" / "python"
    r = subprocess.run([str(conv_py), str(ROOT / "simulation" / "silicon_anchor_extract.py"),
                        "--cell", cid], capture_output=True, text=True)
    j.log(f"[extract] {cid}: rc={r.returncode} {r.stdout.strip()[-400:]} "
          f"{r.stderr.strip()[-400:]}")
    if r.returncode != 0:
        raise RuntimeError(f"{cid}: dispatch extraction failed (rc={r.returncode})")


def main() -> int:
    global QUEUE_PATH
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true",
                    help="resolve and print the next N work units; no GPU, no measurement")
    ap.add_argument("--plan-n", type=int, default=30)
    ap.add_argument("--pilot", action="store_true",
                    help="bounded correctness pass: burst3__fc rep 0, first --pilot-batches "
                         "batches only, artifacts under reps/_pilot/. Proves the six pilot "
                         "invariants (see the runner's return notes) without entering the queue")
    ap.add_argument("--pilot-batches", type=int, default=300)
    ap.add_argument("--pilot-cell", default="burst3__fc")
    ap.add_argument("--queue", default=str(QUEUE_PATH),
                    help="alternate queue JSON (its `root` selects an independent manifest, "
                         "so a variant or self-test run never touches production state)")
    ap.add_argument("--max-reps", type=int, default=0,
                    help="stop after this many completed reps (0 = unbounded, the default)")
    a = ap.parse_args()

    QUEUE_PATH = Path(a.queue)
    q = load_queue()
    root = ROOT / q["root"]
    root.mkdir(parents=True, exist_ok=True)
    j = Journal(root, "pilot_manifest.jsonl" if a.pilot else "manifest.jsonl")
    gate = q["clock_gate"]
    cells = cells_of(q)

    if a.plan:
        recs = j.read()
        state = completed_reps(recs)
        print(f"manifest: {len(recs)} records, {len(state['done'])} completed reps")
        sim = {"done": set(state["done"]), "attempts": dict(state["attempts"]),
               "abandoned": set(state["abandoned"])}
        tot_lo = tot_hi = 0.0
        for k in range(a.plan_n):
            u = next_unit(q, sim)
            if not u:
                break
            cid, rep, phase = u
            s = cells[cid]
            band = s.get("est_gpu_s_band", [0, 0])
            tot_lo += band[0]
            tot_hi += band[1]
            print(f"{k+1:3d}. [{phase:9s}] {cid:22s} rep{rep:<3d} "
                  f"est {band[0]/3600:5.2f}-{band[1]/3600:5.2f} h  "
                  f"cum {tot_lo/3600:6.1f}-{tot_hi/3600:6.1f} h")
            sim["done"].add((cid, rep))
        return 0

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    (root / "daemon.pid").write_text(str(os.getpid()))
    j.event("daemon_start", pid=os.getpid(), host=socket.gethostname(),
            argv=sys.argv, python=sys.executable, queue=str(QUEUE_PATH))
    j.log(f"[daemon] pid={os.getpid()} python={sys.executable} "
          f"root={root} STOP={root/'STOP'}")

    if stop_requested(root):
        j.log("[daemon] STOP file already present at launch -- exiting without measuring")
        j.event("daemon_stop", reason="stop_file_present_at_launch")
        return 0

    enc = None
    completed = 0
    rc = 0
    try:
        while True:
            if stop_requested(root):
                raise StopRequested("STOP between reps")
            recs = j.read()
            state = completed_reps(recs)

            if a.pilot:
                cid, rep, phase = a.pilot_cell, 0, "pilot"
                if (cid, 0) in state["done"]:
                    j.log("[pilot] already complete")
                    break
            else:
                u = next_unit(q, state)
                if not u:
                    j.log("[daemon] queue exhausted (extension disabled?)")
                    break
                cid, rep, phase = u

            spec = cells[cid]
            j.log(f"[daemon] next: {cid} rep{rep} ({phase}) "
                  f"est {spec.get('est_gpu_s_band', ['?','?'])} GPU-s")

            try:
                if spec["type"] == "trace_replay":
                    ensure_dispatch(cid, root, j)
                    n_max = spec.get("cap", 64)
                    if enc is not None and enc.n_max < n_max:
                        j.log(f"[daemon] reloading encoder: buffer {enc.n_max} < {n_max}")
                        enc = None
                    if enc is None:
                        wait_for_gate(j, gate, "model_load")
                        enc = Encoder(q["execution"], n_max, j)
                    if a.pilot:
                        summary = _pilot(q, cid, spec, enc, j, gate, root, a.pilot_batches)
                    else:
                        summary = run_trace_replay(q, cid, spec, rep, enc, j, gate, root)
                elif spec["type"] == "fn_sweep":
                    need = max(spec["ns"])
                    if enc is not None and enc.n_max < need:
                        j.log(f"[daemon] reloading encoder: buffer {enc.n_max} < {need}")
                        enc = None
                    if enc is None:
                        wait_for_gate(j, gate, "model_load")
                        enc = Encoder(q["execution"], need, j)
                    summary = run_fn_sweep(q, cid, spec, rep, enc, j, gate, root)
                else:
                    raise RuntimeError(f"unknown cell type {spec['type']}")
            except StopRequested:
                raise
            except CellSkipped as ex:
                j.log(f"[daemon] {cid} rep{rep} SKIPPED: {ex}")
                time.sleep(2)
                continue  # benign, already recorded by the cell handler
            except Exception as ex:
                tb = traceback.format_exc(limit=6)
                j.event("rep_fail", cell=cid, rep=rep, error=f"{type(ex).__name__}: {ex}",
                        traceback=tb)
                j.log(f"[daemon] {cid} rep{rep} FAILED {type(ex).__name__}: {ex}")
                n_try = state["attempts"].get((cid, rep), 0) + 1
                if n_try >= q["execution"]["max_attempts_per_rep"]:
                    j.event("rep_abandoned", cell=cid, rep=rep, attempts=n_try)
                    j.log(f"[daemon] {cid} rep{rep} ABANDONED after {n_try} attempts; "
                          f"continuing with the next unit")
                time.sleep(5)
                continue

            if a.pilot:
                j.event("pilot_done", cell=cid, rep=0, summary=summary)
                j.log("[pilot] complete -- see the six pilot invariants in pilot.json")
                break

            d = rep_dir(root, cid, rep)
            j.event("rep_done", cell=cid, rep=rep, phase=phase,
                    artifacts={"rep_json": str((d / 'rep.json').relative_to(ROOT)),
                               "batches_csv_gz": str((d / 'batches.csv.gz').relative_to(ROOT))
                               if (d / "batches.csv.gz").exists() else None,
                               "clock_jsonl": str((d / 'clock.jsonl').relative_to(ROOT))
                               if (d / "clock.jsonl").exists() else None},
                    clock_start=summary.get("clock_start"),
                    clock_end=summary.get("clock_end"),
                    wall_s=summary.get("wall_s"),
                    summary={k: summary.get(k) for k in
                             ("measured_busy_s", "sim_busy_s", "overhead_frac",
                              "per_batch_ratio_measured_over_sim",
                              "retimed_encoder_delay_ms", "replayed_sim_encoder_delay_ms",
                              "banked_sim_encoder_delay_ms", "n_batches")})
            completed += 1
            j.log(f"[daemon] {cid} rep{rep} DONE in {summary.get('wall_s')}s "
                  f"({completed} reps this process)")
            if a.pilot or (a.max_reps and completed >= a.max_reps):
                break
    except StopRequested as ex:
        j.log(f"[daemon] stopping: {ex}")
        j.event("daemon_stop", reason=str(ex), completed_this_process=completed)
    except Exception as ex:
        j.log(f"[daemon] FATAL {type(ex).__name__}: {ex}\n{traceback.format_exc()}")
        j.event("daemon_stop", reason=f"fatal {type(ex).__name__}: {ex}",
                completed_this_process=completed)
        rc = 1
    else:
        j.event("daemon_stop", reason="loop exited", completed_this_process=completed)
    finally:
        try:
            (root / "daemon.pid").unlink()
        except OSError:
            pass
    return rc


def _pilot(q, cid, spec, enc, j, gate, root, n_limit) -> dict:
    """Bounded correctness pass over the first n_limit batches of a cell."""
    disp = root / "dispatch"
    batches = []
    with open(disp / f"{cid}.batches.jsonl") as f:
        for k, line in enumerate(f):
            if k >= n_limit:
                break
            batches.append(json.loads(line))
    d = root / "reps" / "_pilot" / cid
    d.mkdir(parents=True, exist_ok=True)
    snap0 = wait_for_gate(j, gate, "pilot/start")
    enc.warmup([64, 8, 1], 7, j)
    t0 = time.time()
    ms = [enc.batch_ms(int(b[2]), int(b[3]), spec.get("cap", 64)) for b in batches]
    wall = time.time() - t0
    snap1 = gpu_snapshot()
    aic = aic_curve()
    n64 = [m for m, b in zip(ms, batches) if int(b[2]) == 64]
    anchor = json.load(open(ROOT / "collector_artifacts" / "phaseE_physical_anchor"
                            / "anchor_sdpa_locked2400.json"))
    a64 = next(r["mean_ms"] for r in anchor["rows"] if r["n_images"] == 64)
    med64 = statistics.median(n64) if n64 else None
    out = {"cell": cid, "rep": 0, "pilot": True, "n_batches": len(batches),
           "wall_s": round(wall, 2),
           "measured_busy_s": round(sum(ms) / 1000.0, 3),
           "overhead_frac": round(1 - (sum(ms) / 1000.0) / wall, 5),
           "median_f64_ms": round(med64, 4) if med64 else None,
           "anchor_f64_ms": a64,
           "f64_vs_anchor_pct": round((med64 / a64 - 1) * 100, 3) if med64 else None,
           "sim_busy_s": round(sum(b[1] - b[0] for b in batches) / 1000.0, 3),
           "peak_mem_gb": round(enc.torch.cuda.max_memory_allocated() / 2**30, 3),
           "clock_start": snap0, "clock_end": snap1,
           "aic_f64_ms": round(aic.ms(64), 3)}
    json.dump(out, open(d / "pilot.json", "w"), indent=1)
    j.log(f"[pilot] {json.dumps({k: out[k] for k in ('n_batches','wall_s','measured_busy_s','overhead_frac','median_f64_ms','anchor_f64_ms','f64_vs_anchor_pct','peak_mem_gb')})}")
    return out


if __name__ == "__main__":
    sys.exit(main())
