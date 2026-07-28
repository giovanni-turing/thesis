#!/usr/bin/env python3
"""D77 negative self-test (bridge 257): artifact_commit_sha lineage refresh.

1. Seed a deliberately stale SHA on the eda:i_burst_anatomy row.
2. Run K34 (load_config_backfill) and require the pin to ADVANCE to the
   live `git log -1 -- <source_path>` SHA (fill-only semantics would leave
   the seeded value in place -- the pre-D77 bug).
3. Run K34 again and require idempotence (the SHA unchanged).
The row ends in its correct state either way; the seeded value is the
historical 4e855370 commit the D77 finding demonstrated.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import db
import load_config_backfill

RID = "eda:i_burst_anatomy"
STALE = "4e8553708a6bb1a9cb5f35feaa983625bab7afb7"


def current_pin():
    return db.rows("SELECT artifact_commit_sha, source_path FROM provenance.runs "
                   f"WHERE run_id = '{RID}'")[0]


def main():
    ok = True
    sha0, sp = current_pin()
    rel = sp
    tese = str(HERE.parent.parent)
    if rel.startswith(tese + "/"):
        rel = rel[len(tese) + 1:]
    live = subprocess.run(["git", "-C", tese, "log", "-1", "--format=%H", "--", rel],
                          capture_output=True, text=True, check=True).stdout.strip()

    db.run_sql(f"UPDATE provenance.runs SET artifact_commit_sha = '{STALE}' "
               f"WHERE run_id = '{RID}'")
    seeded, _ = current_pin()
    if seeded != STALE:
        print("FAIL: could not seed stale SHA")
        return 1

    load_config_backfill.load_config_backfill()
    after, _ = current_pin()
    good = after == live and after != STALE
    print(f"{'PASS' if good else 'FAIL'}: K34 advances seeded stale pin "
          f"({seeded[:8]} -> {after[:8]}, live {live[:8]})")
    ok &= good

    load_config_backfill.load_config_backfill()
    again, _ = current_pin()
    good = again == after
    print(f"{'PASS' if good else 'FAIL'}: second K34 pass idempotent ({again[:8]})")
    ok &= good

    if not ok and sha0 == live:
        db.run_sql(f"UPDATE provenance.runs SET artifact_commit_sha = '{sha0}' "
                   f"WHERE run_id = '{RID}'")
    print("D77-SELFTEST:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
