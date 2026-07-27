#!/usr/bin/env python3
"""Tracked generator/verifier for verification/replay_archive_manifest.json
(D52/D56 closure).

All archive reads are STREAMED (chunked sha256/byte/row accounting, no whole
file in memory) through `zstd -d -c`, and the decoder's exit status is
REQUIRED to be zero -- a failing decoder can never yield a green row.

Modes:
  (default)   regenerate the manifest. Requires the plain files (live tree):
              each archive's decoded stream is byte-compared CHUNKWISE against
              its plain file before the row is written.
  --verify    CLEAN-CHECKOUT verification from the tracked .zst files ALONE:
              plain sha256/bytes/rows are recomputed from the decoded stream
              (no plain file opened) and the full manifest object is compared
              against the tracked one; nonzero exit on any difference.
  --with-plain (with --verify) additionally byte-compare each decoded stream
              against a present plain file, when the live tree has them.
  --selftest  negative probes: truncated archive -> decoder failure raises;
              stream accounting matches a known tiny payload.

Generation provenance (command, generation commit, ledger anchor) is declared
in GENERATION below -- distinct from the archive commit.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

TESE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(TESE, "verification/replay_archive_manifest.json")
CHUNK = 1 << 20

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
ROUND_TRIP_TEXT = ("decoded stream sha256/bytes/rows computed with decoder exit "
                   "status REQUIRED zero; at generation the stream is additionally "
                   "byte-compared chunkwise against the plain file")


class DecoderError(RuntimeError):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(CHUNK), b""):
            h.update(ch)
    return h.hexdigest()


def stream_archive(comp_path, plain_path=None):
    """Stream-decode comp_path; return (sha256, bytes, rows). If plain_path is
    given, byte-compare the stream against it chunkwise and raise on any
    difference. Raises DecoderError on nonzero decoder exit."""
    h = hashlib.sha256()
    nbytes = 0
    rows = 0
    proc = subprocess.Popen(["zstd", "-d", "-q", "-c", comp_path],
                            stdout=subprocess.PIPE)
    pf = open(plain_path, "rb") if plain_path else None
    try:
        for ch in iter(lambda: proc.stdout.read(CHUNK), b""):
            h.update(ch)
            nbytes += len(ch)
            rows += ch.count(b"\n")
            if pf is not None and pf.read(len(ch)) != ch:
                raise RuntimeError(f"round-trip mismatch for {comp_path}")
        if pf is not None and pf.read(1) != b"":
            raise RuntimeError(f"plain file longer than stream for {comp_path}")
    finally:
        if pf is not None:
            pf.close()
        proc.stdout.close()
        rc = proc.wait()
    if rc != 0:
        raise DecoderError(f"zstd decoder exit {rc} for {comp_path}")
    return h.hexdigest(), nbytes, rows


def build(compare_plain):
    zv = subprocess.run(["zstd", "--version"], capture_output=True,
                        text=True).stdout.strip()
    rows = []
    for rel, meta in FILES.items():
        comp_p = os.path.join(TESE, rel) + ".zst"
        plain_p = os.path.join(TESE, rel) if compare_plain else None
        sha, nbytes, nrows = stream_archive(comp_p, plain_p)
        rows.append({
            "path": rel + ".zst",
            "plain_path": rel,
            "plain_sha256": sha,
            "compressed_sha256": sha256_file(comp_p),
            "plain_bytes": nbytes,
            "compressed_bytes": os.path.getsize(comp_p),
            "rows": nrows,
            "generating_source": meta["generating_source"],
            "generation_command": meta["generation_command"],
            "generation_commit": meta["generation_commit"],
            "ledger_anchor": meta["ledger_anchor"],
            "archived_in_commit": "ba5e4a3 (compression/archive commit, distinct from generation)",
            "compression": "zstd -19 -T8",
            "zstd_version": zv,
            "round_trip_cmp": ROUND_TRIP_TEXT,
        })
    return {
        "package": "composed-join replay inputs (tab:cl-ledger-* / K16 pipeline)",
        "generator": ("verification/make_replay_archive_manifest.py (tracked; "
                      "--verify recomputes from the tracked archives alone and compares)"),
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


def _selftest():
    ok = True
    with tempfile.TemporaryDirectory() as td:
        plain = os.path.join(td, "t.jsonl")
        payload = b'{"a":1}\n{"b":2}\n{"c":3}\n'
        open(plain, "wb").write(payload)
        subprocess.run(["zstd", "-q", "-f", plain, "-o", plain + ".zst"], check=True)
        sha, nb, nr = stream_archive(plain + ".zst", plain)
        good = (sha == hashlib.sha256(payload).hexdigest()
                and nb == len(payload) and nr == 3)
        print(f"{'PASS' if good else 'FAIL'}: stream-accounting (bytes={nb} rows={nr})")
        ok &= good
        trunc = os.path.join(td, "trunc.jsonl.zst")
        blob = open(plain + ".zst", "rb").read()
        open(trunc, "wb").write(blob[:len(blob) // 2])
        try:
            stream_archive(trunc)
            print("FAIL: nonzero-decoder (no raise)")
            ok = False
        except DecoderError as e:
            print(f"PASS: nonzero-decoder ({e})")
        except RuntimeError as e:
            print(f"FAIL: nonzero-decoder (wrong error: {e})")
            ok = False
    print("MANIFEST-SELFTEST:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    args = sys.argv[1:]
    if args[:1] == ["--selftest"]:
        return _selftest()
    if args[:1] == ["--verify"]:
        manifest = build(compare_plain="--with-plain" in args)
        tracked = json.load(open(OUT))
        if tracked == manifest:
            print("manifest verify: OK (recomputed-from-stream == tracked)")
            return 0
        print("manifest verify: MISMATCH")
        return 1
    manifest = build(compare_plain=True)
    with open(OUT, "w") as f:
        json.dump(manifest, f, indent=1)
    tot_c = sum(r["compressed_bytes"] for r in manifest["files"])
    tot_p = sum(r["plain_bytes"] for r in manifest["files"])
    print(f"manifest written: 6 files, compressed {tot_c:,} B "
          f"({tot_c / 2**20:.3f} MiB), plain {tot_p:,} B ({tot_p / 2**30:.5f} GiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
