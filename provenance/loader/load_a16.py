"""K26 — the two file-only A16 analysis tracks.

a16_decode (decode-spread) and a16_controller_cost (controller inference cost) had ZERO
database provenance: their outputs were shipped as files only. Both are pure ANALYSIS over
already-ingested runs — they produce no new run_id and no per-request rows — so they land in
provenance.analysis_artifact, lossless as jsonb, keyed by track:arm.

Names written:
  a16_decode:<tag>              one per arm (ft_llm_static, ft_llm_reactive, timesfm_e2e)
  a16_controller_cost:accounting
  a16_controller_cost:timing:<model>_<device>
"""
import glob
import json
import os

import db
import ingest_common as ic

TESE = os.environ.get("TESE_ROOT", "/home/gio/tese")
DEC = f"{TESE}/defense/anim/data/a16_decode_spread"
DEC2 = f"{TESE}/defense/anim/data/a16_decode"
CTRL = f"{TESE}/defense/anim/data/a16_controller_cost"
KEY = "K30"


def _prep(path, idx, reload):
    if ic.is_worktree(path):
        return None
    sha, nbytes = ic.file_meta(path)
    if not reload and idx.get(path) == sha:
        return None
    return sha, nbytes


def _artifact(name, path, payload, sha, nbytes):
    db.run_sql(ic.upsert_sql("analysis_artifact",
               {"name": name, "source_path": path, "payload": payload},
               "name", jsonb_cols=("payload",)))
    db.run_sql(ic.ingest_sql(path, sha, KEY, 1, None, nbytes))


def load_a16(idx, reload):
    nf = nr = 0

    # ---- a16_decode: one artifact per arm ------------------------------------
    for root in (DEC, DEC2):
        for path in sorted(glob.glob(f"{root}/*_a16_stats.json")):
            prep = _prep(path, idx, reload)
            if not prep:
                continue
            sha, nbytes = prep
            j = json.load(open(path))
            tag = j.get("tag") or os.path.basename(path).replace("_a16_stats.json", "")
            _artifact(f"a16_decode:{tag}", path, j, sha, nbytes)
            nf += 1
            nr += 1

    # ---- a16_controller_cost: accounting + per-(model,device) timings --------
    acc = f"{CTRL}/accounting.json"
    if os.path.exists(acc):
        prep = _prep(acc, idx, reload)
        if prep:
            sha, nbytes = prep
            _artifact("a16_controller_cost:accounting", acc, json.load(open(acc)), sha, nbytes)
            nf += 1
            nr += 1
    for path in sorted(glob.glob(f"{CTRL}/timing_*.json")):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        stem = os.path.basename(path)[len("timing_"):-len(".json")]
        _artifact(f"a16_controller_cost:timing:{stem}", path, json.load(open(path)), sha, nbytes)
        nf += 1
        nr += 1

    return nf, nr
