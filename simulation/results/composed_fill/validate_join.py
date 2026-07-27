#!/usr/bin/env python3
"""Validate composed_fill_join.py against already-published A12 burst arms.

Two criteria:
 1. the join must reproduce a12_data.json's enc_p99 / e2e_p99 / e2e_max exactly;
 2. the FIFO key (the only key available on the static cells) must agree with
    the session_id key that extract_a12.py used, EXCEPT inside groups of
    requests whose (arrival_ms, clamped input, output) are all identical --
    those are interchangeable by construction. key_sensitivity.py shows those
    swaps move e2e_p99 / e2e_max / ttft_p99 by exactly 0.0 ms on every arm, so
    the criterion here is `disagreements <= ambiguous records`, not index
    identity.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/gio/tese/simulation")
import composed_fill_join as J  # noqa: E402

ROOT = Path("/home/gio/tese")
A12 = ROOT / "defense/anim/data/a12_runs"
VER = json.load(open(A12 / "verification.json"))
PUB = json.load(open(ROOT / "defense/anim/data/a12_data.json"))["windows"]

CHECK = [("burst3", "reactive"), ("burst5", "reactive"),
         ("burst4", "reactive"), ("burst1", "reactive"),
         ("burst3", "fc_chronos"), ("burst1", "fc_chronos")]

ok = True
for win, arm in CHECK:
    tag = f"{win}_{arm}"
    J.CELLS[tag] = (win, ROOT / VER[tag]["composed_trace"],
                    A12 / f"{tag}.requests.jsonl", A12 / f"{tag}.report.json", True)
    r = J.join_cell(tag)
    p = PUB[win]["runs"][arm]["stats"]
    d = {k: (r[k], p[k]) for k in ("enc_p99", "e2e_p99", "e2e_max")}
    match = all(a == b for a, b in d.values())
    st = r["key_selftest"]
    disagree = st["of"] - st["agree"]
    keyok = disagree <= st["ambiguous_key_records"]
    ok &= match and keyok
    print(f"{tag:20s} join={'MATCH' if match else 'MISMATCH'} "
          f"enc_p99 {r['enc_p99']}/{p['enc_p99']} e2e_p99 {r['e2e_p99']}/{p['e2e_p99']} "
          f"e2e_max {r['e2e_max']}/{p['e2e_max']} | fifo-key disagree={disagree} "
          f"ambiguous={st['ambiguous_key_records']} ({'OK' if keyok else 'BEYOND-TIES'}) "
          f"| drift={r['alignment_drift_ms']}")

print("VALIDATION", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
