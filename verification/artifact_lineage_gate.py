#!/usr/bin/env python3
"""Artifact-lineage freshness gate (D77, bridge 257).

For every provenance.runs row whose artifact_commit_sha is non-null and
whose source_path is a repo-local tracked file, the stored SHA must equal
`git log -1 --format=%H -- <path>` in the live repository. SQL alone
cannot see Git history, so this bridges the two: a later commit archiving
an artifact must be reflected by K34; a stale pin here means the
staged-first refresh (load_config_backfill) has not run since that commit.

Exit nonzero on any mismatch. Paths outside the repo or untracked are
skipped (reported as a count).
"""
import subprocess
import sys
from pathlib import Path

TESE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TESE / "provenance/loader"))
import db  # the loaders' psql transport; no psycopg needed


def main():
    rows = db.rows("SELECT run_id, source_path, artifact_commit_sha "
                   "FROM provenance.runs WHERE artifact_commit_sha IS NOT NULL "
                   "AND source_path IS NOT NULL")
    by_path = {}
    for rid, sp, sha in rows:
        by_path.setdefault(sp, []).append((rid, sha))

    tracked = set(subprocess.run(
        ["git", "-C", str(TESE), "ls-files"],
        capture_output=True, text=True, check=True).stdout.splitlines())

    stale, checked, skipped = [], 0, 0
    for sp, pins in sorted(by_path.items()):
        rel = sp
        if rel.startswith(str(TESE) + "/"):
            rel = rel[len(str(TESE)) + 1:]
        if rel not in tracked:
            skipped += len(pins)
            continue
        head = subprocess.run(
            ["git", "-C", str(TESE), "log", "-1", "--format=%H", "--", rel],
            capture_output=True, text=True, check=True).stdout.strip()
        for rid, sha in pins:
            checked += 1
            if sha != head:
                stale.append((rid, rel, sha[:8], head[:8]))
    for rid, rel, old, new in stale:
        print(f"STALE-LINEAGE: {rid} {rel}: stored {old} != git {new}")
    print(f"artifact-lineage gate: {checked} pins checked over "
          f"{len([p for p in by_path if (p[len(str(TESE))+1:] if p.startswith(str(TESE)+'/') else p) in tracked])} tracked paths, "
          f"{skipped} non-repo pins skipped, {len(stale)} stale")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
