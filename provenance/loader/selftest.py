#!/usr/bin/env python3
"""Regression tests for the loader's data-loss defects. Run:  python3 selftest.py

Guards three invariants that were violated in the 2026-07-19 audit:

  A. COLLISION GUARD  -- when two different source files resolve to the same run_id, the
     loader must RAISE, not silently delete the first file's rows.
  B. DIR COVERAGE     -- every directory under the ingest roots that holds an ingestible
     file must map to a real experiment, never the 'misc' catch-all (the fallback that
     made unrelated files collide on 'misc:<stem>').
  C. RUN_ID INJECTIVITY -- over the whole current file set, two files may share a run_id
     only if they are the same run in different file KINDS (same directory, same stem).

Read-only: touches no table, ingests nothing. Exit 0 = all green.
"""
import glob, os, sys, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest_common as ic
from runid import experiment_of, run_id_of, run_scope_key, stem_of

ROOTS = ["/home/gio/tese/defense/anim/data", "/home/gio/tese/simulation/results"]
PATTERNS = ["*.report.json", "*.jsonl.stats.json", "*.series.json", "*.sched.json",
            "*.requests.jsonl", "*.jsonl", "*.stats.json", "verification.json"]


def ingestible_files():
    seen = set()
    for root in ROOTS:
        for pat in PATTERNS:
            for p in glob.glob(os.path.join(root, "**", pat), recursive=True):
                if not ic.is_worktree(p):
                    seen.add(p)
    return sorted(seen)


# --------------------------------------------------------------------- test A
def test_collision_guard():
    """Two files, different dirs, same stem -> same run_id must RAISE."""
    a = "/home/gio/tese/defense/anim/data/a16_runs/cellA/iter3.requests.jsonl"
    b = "/home/gio/tese/defense/anim/data/a16_runs/cellB/iter3.requests.jsonl"
    rid = "misc:iter3"                       # the pre-fix, colliding run_id
    idx = ic.IngestIndex(runs={rid: {a: "K2"}})
    try:
        ic.guard_run_collision(rid, b, idx, "llm_request", "K2")
    except ic.RunIdCollision as e:
        assert a in str(e) and b in str(e), "error must name BOTH files"
    else:
        raise AssertionError("collision was NOT detected -- rows would be silently deleted")

    # the legitimate multi-kind case must NOT raise
    r1 = "/home/gio/tese/defense/anim/data/a11_runs/burst1_fc_chronos_L60.report.json"
    r2 = "/home/gio/tese/defense/anim/data/a11_runs/burst1_fc_chronos_L60.sched.json"
    r3 = "/home/gio/tese/defense/anim/data/a11_runs/burst1_fc_chronos_L60.requests.jsonl"
    idx2 = ic.IngestIndex(runs={run_id_of(r1): {r1: "K1", r2: "K4"}})
    ic.guard_run_collision(run_id_of(r3), r3, idx2, "llm_request", "K2")
    assert run_id_of(r1) == run_id_of(r2) == run_id_of(r3)

    # a BULK loader's many-files-under-one-synthetic-run_id rows must not read as a
    # collision (load_grid registers the whole grid file set under 'grid:grid_summary').
    g = "/home/gio/tese/simulation/results/grid/grid_summary.json"
    idx3 = ic.IngestIndex(runs={"grid:grid_summary": {
        "/home/gio/tese/simulation/results/grid/vision_burst1_C1.json": "K20"}})
    ic.guard_run_collision("grid:grid_summary", g, idx3, "llm_run_summary", "K1")

    # and the post-fix run_ids for the a16 case are actually distinct
    assert run_id_of(a) != run_id_of(b), (run_id_of(a), run_id_of(b))
    return "collision raises; multi-kind + bulk-loader rows allowed; a16 disambiguated"


# --------------------------------------------------------------------- test B
def test_dir_coverage(files):
    bad = {}
    for p in files:
        if experiment_of(p) == "misc":
            bad.setdefault(os.path.dirname(p), 0)
            bad[os.path.dirname(p)] += 1
    if bad:
        lines = "\n".join(f"    {n:5d} files  {d}" for d, n in sorted(bad.items()))
        raise AssertionError(
            "%d director%s still map to experiment 'misc' -- add them to runid._DIR_EXP:\n%s"
            % (len(bad), "y" if len(bad) == 1 else "ies", lines))
    dirs = {os.path.dirname(p) for p in files}
    return "%d directories, %d files, 0 'misc'" % (len(dirs), len(files))


# --------------------------------------------------------------------- test C
def test_run_id_injective(files):
    by_rid = {}
    for p in files:
        by_rid.setdefault(run_id_of(p), []).append(p)
    bad = {}
    for rid, ps in by_rid.items():
        scopes = {run_scope_key(p) for p in ps}
        if len(scopes) > 1:          # same run_id from genuinely different runs
            bad[rid] = ps
    if bad:
        lines = []
        for rid, ps in sorted(bad.items())[:20]:
            lines.append("    %s" % rid)
            lines += ["        %s" % p for p in sorted(ps)]
        raise AssertionError(
            "%d run_id(s) are shared by DIFFERENT runs (delete-then-insert would destroy "
            "data):\n%s" % (len(bad), "\n".join(lines)))
    multi = sum(1 for ps in by_rid.values() if len(ps) > 1)
    return "%d run_ids over %d files (%d legitimately multi-kind), injective" % (
        len(by_rid), len(files), multi)


def main():
    files = ingestible_files()
    tests = [("A collision guard", lambda: test_collision_guard()),
             ("B dir coverage", lambda: test_dir_coverage(files)),
             ("C run_id injectivity", lambda: test_run_id_injective(files))]
    fails = 0
    for name, fn in tests:
        try:
            print("PASS  %-22s %s" % (name, fn()))
        except Exception as e:
            fails += 1
            print("FAIL  %-22s %s" % (name, e))
            if not isinstance(e, AssertionError):
                traceback.print_exc()
    print("\n%s (%d/%d)" % ("ALL GREEN" if not fails else "FAILURES", len(tests) - fails,
                           len(tests)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
