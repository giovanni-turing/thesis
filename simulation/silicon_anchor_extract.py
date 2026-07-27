#!/usr/bin/env python3
"""Extract the ACTUAL encoder batch-dispatch sequence of a controller arm.

Each queued cell is a (window, arm) pair whose worker schedule is already
frozen on disk (comparator_frontier/eval for the headline arms, encoder_hybrid
for the folds). The dispatch log is NOT stored by those runs -- only aggregate
stats are -- so it is regenerated here by re-running the SAME converter with
the SAME frozen arguments plus the strictly-additive `--batches-out` dump flag
(workload/trace_to_two_pool.py). Nothing is guessed.

The regeneration is then GATED against the banked stats of the original run:
batches, encoder_forwards, total_images, requests, busy_worker_seconds,
provisioned_worker_seconds and encoder_delay p50/p90/p99/max must all match
exactly. A cell that fails the gate is unusable -- it means the dispatch log
is not the arm's dispatch.

Outputs per cell, under <root>/dispatch/:
  <cell>.batches.jsonl      [start_ms, finish_ms, total_images, n_forwards] per line
  <cell>.batches.jsonl.reqs.json   image-bearing arrivals + percentile convention
  <cell>.regen.stats.json   the regenerated stats (gate input)
  <cell>.meta.json          provenance + gate verdict + measured-time estimate

Usage:
  silicon_anchor_extract.py --cell burst3__fc [--cell ...]   # explicit
  silicon_anchor_extract.py --all                            # every queued cell
  silicon_anchor_extract.py --tier 1                         # one tier
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/home/gio/tese")
QUEUE = ROOT / "simulation" / "silicon_anchor_queue.json"
CONVERTER = ROOT / "workload" / "trace_to_two_pool.py"
# The interpreter the frozen arms were produced with (comparator_frontier_eval.sh:47,
# run_encoder_hybrid_folds.sh:14): imports the aiconfigurator EncoderCostModel.
CONV_PY = ROOT / "ai-dynamo" / "dynamo" / ".venv" / "bin" / "python"
ANCHOR = ROOT / "collector_artifacts" / "phaseE_physical_anchor" / "anchor_sdpa_locked2400.json"

# Fields that must reproduce exactly for the dump to be THE arm's dispatch.
GATE_SCALARS = ("requests", "requests_with_images", "total_images", "batches",
                "encoder_forwards", "busy_worker_seconds",
                "provisioned_worker_seconds", "requests_chunked")
GATE_DICTS = ("encoder_delay_ms", "encoder_batch_service_ms", "images_per_batch")


def sha256(path: Path, limit: int | None = None) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
            if limit and h.name and f.tell() > limit:
                break
    return h.hexdigest()


def git_sha() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception:
        return "unknown"


class AnchorCurve:
    """Master-anchor measured f(N) (sdpa, locked 2400 MHz), for RUNTIME ESTIMATES
    only -- never used as a measurement. Linear interpolation, last-segment
    extrapolation, f(0)=0."""

    def __init__(self, path: Path = ANCHOR):
        rows = json.load(open(path))["rows"]
        pts = sorted((int(r["n_images"]), float(r["mean_ms"])) for r in rows)
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


def load_queue() -> dict:
    return json.load(open(QUEUE))


def all_cells(q: dict) -> dict:
    out = {}
    for tier in q["tiers"]:
        for cid, spec in tier["cells"].items():
            out[cid] = dict(spec, tier=tier["tier"])
    return out


def dispatch_paths(root: Path, cid: str) -> dict:
    d = root / "dispatch"
    return {"dir": d,
            "batches": d / f"{cid}.batches.jsonl",
            "reqs": d / f"{cid}.batches.jsonl.reqs.json",
            "regen_stats": d / f"{cid}.regen.stats.json",
            "meta": d / f"{cid}.meta.json",
            "conv_log": d / f"{cid}.conv.log"}


def is_extracted(root: Path, cid: str) -> bool:
    p = dispatch_paths(root, cid)
    if not p["meta"].exists():
        return False
    try:
        return json.load(open(p["meta"])).get("gate", {}).get("pass") is True
    except Exception:
        return False


def extract(cid: str, spec: dict, root: Path, log=print) -> dict:
    """Regenerate + gate one cell's dispatch log. Returns the meta dict."""
    p = dispatch_paths(root, cid)
    p["dir"].mkdir(parents=True, exist_ok=True)
    sched = ROOT / spec["schedule"]
    banked = ROOT / spec["banked_stats"]
    if not sched.exists():
        raise FileNotFoundError(f"{cid}: schedule missing {sched}")
    if not banked.exists():
        raise FileNotFoundError(f"{cid}: banked stats missing {banked}")

    cmd = [str(CONV_PY), str(CONVERTER),
           "--out", "/dev/null",
           "--stats", str(p["regen_stats"]),
           "--offset", str(spec["offset"]),
           "--max-requests", str(spec["max_requests"]),
           "--encoder-workers", str(spec.get("encoder_workers", 2)),
           "--worker-schedule", str(sched),
           "--batches-out", str(p["batches"])]
    t0 = time.time()
    log(f"[extract] {cid}: {' '.join(cmd)}")
    with open(p["conv_log"], "w") as lf:
        rc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT,
                            env={**os.environ, "TESE_WINDOWS": str(ROOT / "simulation" / "windows.json")}).returncode
    if rc != 0:
        raise RuntimeError(f"{cid}: converter rc={rc}, see {p['conv_log']}")
    conv_s = round(time.time() - t0, 1)

    regen = json.load(open(p["regen_stats"]))
    bank = json.load(open(banked))
    diffs = []
    for k in GATE_SCALARS:
        if regen.get(k) != bank.get(k):
            diffs.append({"field": k, "banked": bank.get(k), "regen": regen.get(k)})
    for k in GATE_DICTS:
        if regen.get(k) != bank.get(k):
            diffs.append({"field": k, "banked": bank.get(k), "regen": regen.get(k)})
    gate_pass = not diffs

    # Batch-size histogram + anchor-based runtime estimate (estimate only).
    curve = AnchorCurve()
    hist: dict[int, int] = {}
    sim_busy_ms = 0.0
    est_ms = 0.0
    n_batches = 0
    with open(p["batches"]) as f:
        for line in f:
            start, fin, total, n_fwd = json.loads(line)
            n_batches += 1
            hist[total] = hist.get(total, 0) + 1
            sim_busy_ms += fin - start
            if n_fwd <= 1:
                est_ms += curve.ms(total)
            else:
                full, rem = divmod(total, spec.get("cap", 64))
                est_ms += full * curve.ms(spec.get("cap", 64)) + (curve.ms(rem) if rem else 0.0)

    meta = {
        "cell": cid,
        "window": spec["window"],
        "arm": spec["arm"],
        "tier": spec.get("tier"),
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_sha": git_sha(),
        "provenance": {
            "schedule": spec["schedule"],
            "schedule_sha256": sha256(sched),
            "banked_stats": spec["banked_stats"],
            "banked_stats_sha256": sha256(banked),
            "converter": str(CONVERTER.relative_to(ROOT)),
            "converter_sha256": sha256(CONVERTER),
            "interpreter": str(CONV_PY),
            "source_run": spec.get("source_run"),
            "command": " ".join(cmd),
            "converter_wall_s": conv_s,
        },
        "gate": {"pass": gate_pass, "fields": list(GATE_SCALARS) + list(GATE_DICTS),
                 "diffs": diffs},
        "dispatch": {
            "batches": n_batches,
            "distinct_batch_sizes": len(hist),
            "max_batch_images": max(hist) if hist else 0,
            "total_images": regen.get("total_images"),
            "sim_busy_s": round(sim_busy_ms / 1000.0, 3),
            "est_measured_busy_s": round(est_ms / 1000.0, 1),
            "est_ratio_measured_over_sim": round(est_ms / sim_busy_ms, 4) if sim_busy_ms else None,
            "batch_size_hist": {str(k): hist[k] for k in sorted(hist)},
        },
        "files": {k: str(v.relative_to(ROOT)) for k, v in p.items() if k != "dir"},
    }
    json.dump(meta, open(p["meta"], "w"), indent=1)
    log(f"[extract] {cid}: gate={'PASS' if gate_pass else 'FAIL'} "
        f"batches={n_batches} sim_busy={meta['dispatch']['sim_busy_s']}s "
        f"est_measured={meta['dispatch']['est_measured_busy_s']}s ({conv_s}s CPU)")
    if not gate_pass:
        log(f"[extract] {cid}: GATE DIFFS {json.dumps(diffs)[:600]}")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cell", action="append", default=[])
    ap.add_argument("--tier", type=int, action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-extract even if gated OK")
    a = ap.parse_args()

    q = load_queue()
    root = ROOT / q["root"]
    cells = all_cells(q)
    want = list(a.cell)
    if a.tier:
        want += [c for c, s in cells.items() if s["tier"] in a.tier]
    if a.all or not want:
        want = list(cells)
    seen, order = set(), []
    for c in want:
        if c not in seen:
            seen.add(c)
            order.append(c)

    rc = 0
    for cid in order:
        if cid not in cells:
            print(f"[extract] unknown cell {cid}", file=sys.stderr)
            rc = 2
            continue
        if not a.force and is_extracted(root, cid):
            print(f"[extract] {cid}: already extracted + gated, skipping")
            continue
        try:
            m = extract(cid, cells[cid], root)
            if not m["gate"]["pass"]:
                rc = 1
        except Exception as ex:
            print(f"[extract] {cid}: FAILED {type(ex).__name__}: {ex}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
