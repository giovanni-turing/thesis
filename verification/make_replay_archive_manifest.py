#!/usr/bin/env python3
"""Tracked generator/verifier for verification/replay_archive_manifest.json
(D52 closure). Computes, per archive: plain and compressed SHA-256, exact byte
counts, row count, and a round-trip verdict obtained by DECOMPRESSING the
archive and byte-comparing against the plain file before the row is written.
Generation provenance (command, generation commit, ledger anchor) is declared
in GENERATION below -- distinct from the archive commit.

Usage:
  python verification/make_replay_archive_manifest.py            # regenerate
  python verification/make_replay_archive_manifest.py --verify   # recompute and
      compare against the tracked manifest; nonzero exit on any difference
      (timestamp-free, so verify is byte-stable)
"""
import hashlib
import json
import os
import subprocess
import sys

TESE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(TESE, "verification/replay_archive_manifest.json")

A2_GEN = {
    "generation_command": ("python3 defense/anim/build/gen_a2_fleet.py && "
                           "eda/.venv/bin/python defense/anim/build/extract_a2_fleet.py"),
    "generation_commit": "e9b84ad (A2 generator history)",
    "ledger_anchor": ("progress/results-ledger.md: 'Defense animation A2 v2: "
                      "episode selector + live tickers; 40-run fleet' (2026-07-19)"),
}
A13_GEN = {
    "generation_command": ("python3 defense/anim/build/gen_a13_fulltrace.py && "
                           "python3 defense/anim/build/build_coverage_manifest.py"),
    "generation_commit": ("bb1b7cb (A13 generator introduction); "
                          "a073840 (full-trace coverage result evidence)"),
    "ledger_anchor": ("progress/results-ledger.md: 'Full-trace coverage "
                      "GUARANTEE MET -- every request, both pools (A13)' (2026-07-19)"),
}
FILES = {
    "defense/anim/data/a2_runs/steady24h_forecast_L30.jsonl": dict(
        A2_GEN, generating_source="a2 steady24h forecast_L30 composed replay trace (A2 v2 fleet campaign)"),
    "defense/anim/data/a2_runs/steady24h_reactive_L30.jsonl": dict(
        A2_GEN, generating_source="a2 steady24h reactive_L30 composed replay trace (A2 v2 fleet campaign)"),
    "defense/anim/data/a13_runs/ft_static_C8.jsonl": dict(
        A13_GEN, generating_source="a13 full-trace static C=8 composed replay trace"),
    "defense/anim/data/a13_runs/ft_llm_static.requests.jsonl": dict(
        A13_GEN, generating_source="a13 full-trace static language-pool per-request records (dynamo.replay, source-build patch)"),
    "defense/anim/data/a13_runs/ft_reactive_L30.jsonl": dict(
        A13_GEN, generating_source="a13 full-trace reactive_L30 composed replay trace"),
    "defense/anim/data/a13_runs/ft_llm_reactive.requests.jsonl": dict(
        A13_GEN, generating_source="a13 full-trace reactive language-pool per-request records (dynamo.replay, source-build patch)"),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def build():
    zv = subprocess.run(["zstd", "--version"], capture_output=True,
                        text=True).stdout.strip()
    rows = []
    for rel, meta in FILES.items():
        plain_p = os.path.join(TESE, rel)
        comp_p = plain_p + ".zst"
        plain = open(plain_p, "rb").read()
        dec = subprocess.run(["zstd", "-d", "-q", "-c", comp_p],
                             capture_output=True).stdout
        if dec != plain:
            sys.exit(f"FATAL: round-trip mismatch for {rel}")
        rows.append({
            "path": rel + ".zst",
            "plain_path": rel,
            "plain_sha256": sha256(plain_p),
            "compressed_sha256": sha256(comp_p),
            "plain_bytes": len(plain),
            "compressed_bytes": os.path.getsize(comp_p),
            "rows": plain.count(b"\n"),
            "generating_source": meta["generating_source"],
            "generation_command": meta["generation_command"],
            "generation_commit": meta["generation_commit"],
            "ledger_anchor": meta["ledger_anchor"],
            "archived_in_commit": "ba5e4a3 (compression/archive commit, distinct from generation)",
            "compression": "zstd -19 -T8",
            "zstd_version": zv,
            "round_trip_cmp": "identical (decompressed and byte-compared by make_replay_archive_manifest.py before this row was written)",
        })
    return {
        "package": "composed-join replay inputs (tab:cl-ledger-* / K16 pipeline)",
        "generator": "verification/make_replay_archive_manifest.py (tracked; --verify recomputes and compares)",
        "lineage": ("Replay outputs derived from AzureLMMInferenceDataset2025 "
                    "(Microsoft/ModServe public production trace, CC-BY; see "
                    "data/source/README.md) via the simulation pipeline of "
                    "tex/metodologia.tex; no raw trace rows are redistributed "
                    "beyond what the tracked trace file already carries."),
        "terms": ("Derived data package, distributed with the thesis repository "
                  "under the same terms as its source attribution (CC-BY for "
                  "trace-derived content); cite the thesis and the dataset."),
        "files": rows,
    }


def main():
    manifest = build()
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        tracked = json.load(open(OUT))
        if tracked == manifest:
            print("manifest verify: OK (recomputed == tracked)")
            return 0
        print("manifest verify: MISMATCH")
        return 1
    with open(OUT, "w") as f:
        json.dump(manifest, f, indent=1)
    tot_c = sum(r["compressed_bytes"] for r in manifest["files"])
    tot_p = sum(r["plain_bytes"] for r in manifest["files"])
    print(f"manifest written: 6 files, compressed {tot_c:,} B "
          f"({tot_c / 2**20:.3f} MiB), plain {tot_p:,} B ({tot_p / 2**30:.5f} GiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
