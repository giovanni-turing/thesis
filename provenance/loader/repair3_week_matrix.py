"""REPAIR 3(a): backfill the week_matrix spine.

Re-runs the real K3 (encoder stats) and K4 (worker schedule) loaders, but with
iter_files() narrowed to /simulation/results/week_matrix/ ONLY, so nothing under the
still-being-generated a16*/g2_runs/g3_32b*/g6_runs families is touched.

Both loaders already emit ic.run_upsert_sql(run); the 112 runs rows were missing only
because these files were ingested by an earlier loader revision that did not. The
experiment label comes from the hardened runid.py ("week_matrix" -> "factorial").
"""
import sys, glob, os
sys.path.insert(0, "/home/gio/tese/provenance/loader")
import loaders as L
import runid
from ingest_common import load_ingest_index

WM = "/home/gio/tese/simulation/results/week_matrix"

_orig_parse = runid.parse


def parse_wm(path, kind=None, pool=None):
    d = _orig_parse(path, kind=kind, pool=pool)
    # The window is evidenced by the family directory (week_matrix), not by the stem.
    if path.startswith(WM + "/"):
        d.setdefault("window_name", "week")
    return d


def iter_wm(patterns, roots):
    for pat in patterns:
        for p in sorted(glob.glob(os.path.join(WM, pat))):
            yield p


L.iter_files = iter_wm
L.parse = parse_wm

idx = load_ingest_index()
for k, fn in (("K3", L.load_encoder_stats), ("K4", L.load_worker_schedule)):
    nf, nr = fn(idx, True)
    print(f"[{k}] files={nf} rows={nr}", flush=True)
