# Phase C merge: fold the infill staging CSVs into the repo parquet files.
# Duplicate-key guard: refuses rows whose key already exists in the parquet
# (the infill case list was generated against the grid, so overlaps indicate
# a stale cases.json — investigate, don't overwrite). Run host-side in the
# aiconfigurator venv AFTER run_infill.py finishes clean:
#   .venv/bin/python collector_artifacts/phaseC_vit_shape_infill/merge_parquet.py
import os
import sys

import pandas as pd

ART = os.path.dirname(os.path.abspath(__file__))
BASE = "/home/gio/tese/ai-dynamo/aiconfigurator/src/aiconfigurator/systems/data/rtx_5090/vllm/0.22.0"

MERGES = [
    (os.path.join(ART, "encoder_attention_perf.txt"),
     os.path.join(BASE, "encoder_attention_perf.parquet"),
     ["batch_size", "isl", "num_heads", "head_dim"]),
    (os.path.join(ART, "gemm_perf.txt"),
     os.path.join(BASE, "gemm_perf.parquet"),
     ["gemm_dtype", "m", "n", "k"]),
]

for csv_path, pq_path, keys in MERGES:
    if not os.path.exists(csv_path):
        print(f"skip (no staging file): {csv_path}")
        continue
    new = pd.read_csv(csv_path)
    old = pd.read_parquet(pq_path)
    missing = [c for c in old.columns if c not in new.columns]
    if missing:
        sys.exit(f"schema mismatch for {csv_path}: staging lacks {missing}")
    new = new[list(old.columns)]
    dup = pd.merge(new[keys], old[keys], how="inner")
    if len(dup):
        sys.exit(f"{len(dup)} duplicate keys between staging and parquet for "
                 f"{os.path.basename(pq_path)} — stale cases.json? aborting")
    merged = pd.concat([old, new], ignore_index=True)
    # Original parquets are root-owned (written by the collection container);
    # the dir is user-writable, so write a temp file and replace atomically.
    tmp = pq_path + ".tmp"
    merged.to_parquet(tmp, index=False)
    os.replace(tmp, pq_path)
    print(f"{os.path.basename(pq_path)}: {len(old)} + {len(new)} -> {len(merged)} rows")
