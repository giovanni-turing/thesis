#!/usr/bin/env python3
"""§8.8-1 reproduction predicates (D50/D53 closure): every pass/fail decision
of repro_clean_checkout.sh lives here as a pure function, and `--selftest`
runs the negative probes: 312-cell verdict, nonzero join exit with plausible
content, unrelated/suffix/wrong-type error paths, tenth cell, missing cell,
value drift, stale output, H2 aggregate/candidate-set mutations, H3 decimal
mutations. Run: python verification/repro_predicates.py --selftest
"""
import json
import os
import re
import sys
import tempfile

FRONTIER_VERDICT_RE = re.compile(
    r"^cells=313\s+stats-missing=0\s+stats-mismatches=0\s+"
    r"calib-selection=OK\s+calib-table=OK\s+summary-link=OK\s*$")

NINE = {
    "burst1_static_C8", "burst3_static_C8", "burst4_static_C8",
    "burst5_static_C8", "steady24h_static_C8", "steady24h_fc_chronos",
    "steady24h_reactive", "fulltrace_static_C8", "fulltrace_reactive",
}
TRACKED_OK5 = {
    "burst1_static_C8", "burst3_static_C8", "burst4_static_C8",
    "burst5_static_C8", "steady24h_static_C8",
}
# cell -> the DOCUMENTED first missing input (checkout-relative), matching the
# manifest row for tab:cl-ledger-*; the join reads the composed trace first.
EXPECTED_MISSING = {
    "steady24h_fc_chronos": "defense/anim/data/a2_runs/steady24h_forecast_L30.jsonl",
    "steady24h_reactive": "defense/anim/data/a2_runs/steady24h_reactive_L30.jsonl",
    "fulltrace_static_C8": "defense/anim/data/a13_runs/ft_static_C8.jsonl",
    "fulltrace_reactive": "defense/anim/data/a13_runs/ft_reactive_L30.jsonl",
}
EVAL_WINDOWS = {"burst1", "burst3", "burst4", "burst5", "steady24h"}
# D50 round 2 + D55: the error is parsed EXACTLY -- full-STRING match (\Z, so
# not even a terminal newline is accepted), exact exception type token, exact
# quoted missing path. Substring containment is not accepted.
FNF_RE = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*): \[Errno 2\] No such file or directory: '([^']*)'\Z")


def frontier_verdict_ok(rc: int, verdict_line: str) -> bool:
    return rc == 0 and bool(FRONTIER_VERDICT_RE.match(verdict_line.strip()))


def fresh_output_ok(path: str) -> bool:
    """D50 round 2 + D55: the join PRELOADS an existing --out, so a run is
    valid only if the output path is absent at invocation time -- including
    dangling-symlink residue, which os.path.exists reports as absent; lexists
    catches it."""
    return not os.path.lexists(path)


def stage_a_ok(rc: int, got: dict, committed: dict, checkout_root: str) -> str:
    """Tracked-only boundary: rc==0 (a nonzero exit voids the run regardless of
    content), the exact pinned nine-cell identity, exactly the five pinned
    successes field-equal to the committed cells, and each of the four pinned
    failures an EXACTLY parsed FileNotFoundError whose missing filename equals
    ITS documented checkout-local input."""
    if rc != 0:
        return f"BAD rc={rc}"
    if set(got) != NINE:
        return f"BAD cell-set {sorted(set(got) ^ NINE)}"
    if set(committed) != NINE:
        return f"BAD committed-cell-set {sorted(set(committed) ^ NINE)}"
    ok_cells = {c for c, v in got.items() if "error" not in v}
    if ok_cells != TRACKED_OK5:
        return f"BAD ok-set {sorted(ok_cells ^ TRACKED_OK5)}"
    for c in TRACKED_OK5:
        if got[c] != committed[c]:
            return f"BAD value-drift {c}"
    for c, rel in EXPECTED_MISSING.items():
        m = FNF_RE.fullmatch(got[c].get("error", ""))
        if not m:
            return f"BAD error-form {c}"
        if m.group(1) != "FileNotFoundError":
            return f"BAD error-type {c} ({m.group(1)})"
        if m.group(2) != f"{checkout_root}/{rel}":
            return f"BAD error-path {c} (got {m.group(2)!r}, wanted {rel})"
    return "OK"


def headlines(cells_path: str, composed_path: str) -> dict:
    """H1/H2/H3 from the RECOMPUTED artifacts (never the committed summary).

    H2 (D53 round 2): the candidate set is EVERY warm_floor_* member in any
    group -- including the calibrated core M4 arm -- and passing requires
    p99 < 1000 ms on all five evaluation windows AND the aggregate.

    H3 (D53 round 2): the predicate pins the regenerated artifact's serialized
    one-decimal values EXACTLY (1122.2 / 1143.5). The manuscript's printed
    integers 1122/1143 are the nearest-integer renderings of the
    PRE-serialization full-precision p99s (1122.2019909993 /
    1143.4552270435, recorded by direct raw re-evaluation of the join);
    they are NOT derived by rounding the serialized decimals, which would
    double-round 1143.5 to 1144. Byte-identity of the artifact (checked by
    the runner) plus this exact-decimal pin fixes both layers.
    """
    cells = json.load(open(cells_path))
    static = next(c["worker_s"] for c in cells if c["group"] == "core"
                  and c["arm"] == "static_C8" and c["window"] == "aggregate")
    fc = next(c["worker_s"] for c in cells if c["group"] == "core"
              and c["arm"] == "forecast_p90" and c["window"] == "aggregate")
    floors = {}
    for c in cells:
        if c["arm"].startswith("warm_floor_"):
            floors.setdefault(c["arm"], {})[c["window"]] = c
    need = EVAL_WINDOWS | {"aggregate"}
    passing = {a: v["aggregate"]["worker_s"] for a, v in floors.items()
               if need <= set(v) and all(v[w]["p99"] < 1000.0 for w in need)}
    best = min(passing, key=passing.get) if passing else None
    d = json.load(open(composed_path))
    return {
        "H1": {"value": round(fc / static, 3), "expect": 0.623,
               "locus": "tex/closedloop.tex (frontier) + tex/conclusion.tex",
               "claim": "p90 forecast arm at 0.623x deployable static worker-time"},
        "H2": {"value": (round(passing[best] / static, 3) if best else None),
               "member": best, "expect": 1.042, "expect_member": "warm_floor_M6",
               "locus": "tex/conclusion.tex + tex/closedloop.tex",
               "claim": ("cheapest floor member passing every evaluation window "
                         "AND aggregate, over ALL warm_floor_* arms incl core M4, "
                         "at 1.042x static")},
        "H3": {"value": [d["steady24h_fc_chronos"]["e2e_p99"],
                         d["steady24h_reactive"]["e2e_p99"]],
               "expect": [1122.2, 1143.5],
               "locus": "tex/closedloop.tex sec:cl-ledger-joint",
               "claim": ("composed calm-day e2e p99 serialized decimals "
                         "1122.2/1143.5 (manuscript prints 1122/1143 = nearest "
                         "integers of the pre-serialization full precision)")},
    }


def headlines_ok(h: dict) -> bool:
    return (h["H1"]["value"] == h["H1"]["expect"]
            and h["H2"]["value"] == h["H2"]["expect"]
            and h["H2"]["member"] == h["H2"]["expect_member"]
            and h["H3"]["value"] == h["H3"]["expect"])


def _synthetic(tmp, m6_agg_p99=500.0, m4_passes_all=False, h3=(1122.2, 1143.5)):
    """Synthetic artifact pair for probing headlines()."""
    cells = [
        {"group": "core", "arm": "static_C8", "window": "aggregate",
         "worker_s": 3869278.8, "p99": 500.0},
        {"group": "core", "arm": "forecast_p90", "window": "aggregate",
         "worker_s": 2410754.7, "p99": 500.0},
    ]
    for w in EVAL_WINDOWS:
        cells.append({"group": "family", "arm": "warm_floor_M6", "window": w,
                      "worker_s": 1.0, "p99": 500.0})
        cells.append({"group": "core", "arm": "warm_floor_M4", "window": w,
                      "worker_s": 1.0,
                      "p99": 500.0 if (m4_passes_all or w != "burst3") else 1600.0})
    cells.append({"group": "family", "arm": "warm_floor_M6", "window": "aggregate",
                  "worker_s": 4033184.1, "p99": m6_agg_p99})
    cells.append({"group": "core", "arm": "warm_floor_M4", "window": "aggregate",
                  "worker_s": 3338000.0, "p99": 500.0})
    cp = os.path.join(tmp, "cells.json")
    json.dump(cells, open(cp, "w"))
    comp = {"steady24h_fc_chronos": {"e2e_p99": h3[0]},
            "steady24h_reactive": {"e2e_p99": h3[1]}}
    jp = os.path.join(tmp, "composed.json")
    json.dump(comp, open(jp, "w"))
    return cp, jp


def _selftest() -> int:
    ok = True

    def t(name, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"{'PASS' if good else 'FAIL'}: {name} ({got!r})")

    good_line = ("cells=313  stats-missing=0  stats-mismatches=0  "
                 "calib-selection=OK  calib-table=OK  summary-link=OK")
    t("verdict-good", frontier_verdict_ok(0, good_line), True)
    t("verdict-312-cells", frontier_verdict_ok(0, good_line.replace("313", "312")), False)
    t("verdict-mismatch", frontier_verdict_ok(0, good_line.replace("stats-mismatches=0", "stats-mismatches=1")), False)
    t("verdict-nonzero-rc", frontier_verdict_ok(2, good_line), False)

    root = "/tmp/co"
    def fnf(p):
        return {"error": f"FileNotFoundError: [Errno 2] No such file or directory: '{p}'"}
    committed = {c: {"v": i} for i, c in enumerate(sorted(NINE))}
    got = {c: dict(committed[c]) for c in TRACKED_OK5}
    for c, rel in EXPECTED_MISSING.items():
        got[c] = fnf(f"{root}/{rel}")
    t("stageA-good", stage_a_ok(0, got, committed, root), "OK")
    t("stageA-nonzero-rc-plausible-content", stage_a_ok(1, got, committed, root).startswith("BAD rc"), True)
    c0 = "steady24h_fc_chronos"; want0 = f"{root}/{EXPECTED_MISSING[c0]}"
    t("stageA-suffix-path", stage_a_ok(0, {**got, c0: fnf(want0 + ".bak")}, committed, root).startswith("BAD error-path"), True)
    evil = {**got, c0: {"error": got[c0]["error"].replace("FileNotFoundError:", "FileNotFoundErrorEvil:")}}
    t("stageA-wrong-type", stage_a_ok(0, evil, committed, root).startswith("BAD error-type"), True)
    marker = {**got, c0: {"error": f"FileNotFoundError: [Errno 2] No such file or directory: '{root}/other.json' (cf {want0})"}}
    t("stageA-marker-injection", stage_a_ok(0, marker, committed, root).startswith("BAD"), True)
    newline = {**got, c0: {"error": got[c0]["error"] + "\n"}}
    t("stageA-terminal-newline", stage_a_ok(0, newline, committed, root).startswith("BAD error-form"), True)
    unrelated = {**got, c0: fnf(f"{root}/some/unrelated/path.json")}
    t("stageA-unrelated-missing-path", stage_a_ok(0, unrelated, committed, root).startswith("BAD error-path"), True)
    tenth = {**got, "extra_cell": {"v": 99}}
    t("stageA-tenth-cell", stage_a_ok(0, tenth, {**committed, "extra_cell": {"v": 99}}, root).startswith("BAD cell-set"), True)
    missing = {c: v for c, v in got.items() if c != "burst1_static_C8"}
    t("stageA-missing-cell", stage_a_ok(0, missing, committed, root).startswith("BAD cell-set"), True)
    drift = {**got, "burst1_static_C8": {"v": -1}}
    t("stageA-value-drift", stage_a_ok(0, drift, committed, root).startswith("BAD value-drift"), True)
    swap = {c: dict(committed[c]) for c in NINE}
    t("stageA-tracked-only-all-ok", stage_a_ok(0, swap, committed, root).startswith("BAD ok-set"), True)

    with tempfile.TemporaryDirectory() as td:
        stale = os.path.join(td, "out.json")
        t("fresh-output-absent", fresh_output_ok(stale), True)
        open(stale, "w").write("{}")
        t("fresh-output-stale-preload", fresh_output_ok(stale), False)
        os.unlink(stale)
        dangling = os.path.join(td, "dangling.json")
        os.symlink(os.path.join(td, "no-such-target"), dangling)
        t("fresh-output-dangling-symlink", fresh_output_ok(dangling), False)
        os.unlink(dangling)

        cp, jp = _synthetic(td)
        h = headlines(cp, jp)
        t("headlines-good", headlines_ok(h), True)
        t("headlines-H2-member", h["H2"]["member"], "warm_floor_M6")
        cp2, jp2 = _synthetic(td, m6_agg_p99=1500.0)
        t("H2-aggregate-p99-mutation", headlines_ok(headlines(cp2, jp2)), False)
        cp3, jp3 = _synthetic(td, m4_passes_all=True)
        h3v = headlines(cp3, jp3)
        t("H2-core-M4-pass-changes-verdict", (h3v["H2"]["member"], headlines_ok(h3v)), ("warm_floor_M4", False))
        cp4, jp4 = _synthetic(td, h3=(1122.9, 1143.9))
        t("H3-decimal-mutation", headlines_ok(headlines(cp4, jp4)), False)
        cp5, jp5 = _synthetic(td, h3=(1122.0, 1143.0))
        t("H3-integer-lookalike", headlines_ok(headlines(cp5, jp5)), False)

    print("REPRO-PREDICATES-SELFTEST:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(_selftest())
    print(__doc__)
