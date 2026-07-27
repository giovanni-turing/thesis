#!/usr/bin/env python3
"""§8.8-1 reproduction predicates (D50 closure): every pass/fail decision of
repro_clean_checkout.sh lives here as a pure function, and `--selftest` runs
the negative probes the reviewer specified (312-cell verdict, nonzero join
exit with plausible content, unrelated missing paths, tenth cell, missing
cell, value drift). The shell runner never parses results itself.
"""
import json
import re
import sys

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


def frontier_verdict_ok(rc: int, verdict_line: str) -> bool:
    return rc == 0 and bool(FRONTIER_VERDICT_RE.match(verdict_line.strip()))


def stage_a_ok(rc: int, got: dict, committed: dict, checkout_root: str) -> str:
    """Tracked-only boundary: rc==0 (the join reports per-cell errors in-band,
    but a nonzero exit voids the run regardless of content), the exact pinned
    nine-cell identity, exactly the five pinned successes field-equal to the
    committed cells, and each of the four pinned failures a FileNotFoundError
    naming ITS documented checkout-local input."""
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
        err = got[c].get("error", "")
        want = f"{checkout_root}/{rel}"
        if not err.startswith("FileNotFoundError") or want not in err:
            return f"BAD error-path {c} (wanted {rel})"
    return "OK"


def headlines(cells_path: str, composed_path: str) -> dict:
    """H1/H2/H3 from the RECOMPUTED artifacts (never the committed summary)."""
    cells = json.load(open(cells_path))
    static = next(c["worker_s"] for c in cells if c["group"] == "core"
                  and c["arm"] == "static_C8" and c["window"] == "aggregate")
    fc = next(c["worker_s"] for c in cells if c["group"] == "core"
              and c["arm"] == "forecast_p90" and c["window"] == "aggregate")
    fam = {}
    for c in cells:
        if c["group"] == "family":
            fam.setdefault(c["arm"], {})[c["window"]] = c
    passing = {a: v["aggregate"]["worker_s"] for a, v in fam.items()
               if EVAL_WINDOWS <= set(v)
               and all(v[w]["p99"] < 1000.0 for w in EVAL_WINDOWS)}
    best = min(passing, key=passing.get)
    d = json.load(open(composed_path))
    return {
        "H1": {"value": round(fc / static, 3), "expect": 0.623,
               "locus": "tex/closedloop.tex (frontier) + tex/conclusion.tex",
               "claim": "p90 forecast arm at 0.623x deployable static worker-time"},
        "H2": {"value": round(passing[best] / static, 3), "member": best,
               "expect": 1.042, "expect_member": "warm_floor_M6",
               "locus": "tex/conclusion.tex + tex/closedloop.tex",
               "claim": "cheapest all-passing warm-floor member at 1.042x static"},
        "H3": {"value": [int(d["steady24h_fc_chronos"]["e2e_p99"]),
                         int(d["steady24h_reactive"]["e2e_p99"])],
               "expect": [1122, 1143],
               "locus": "tex/closedloop.tex sec:cl-ledger-joint",
               "claim": "composed calm-day e2e p99: forecast 1122 ms vs reactive 1143 ms"},
    }


def headlines_ok(h: dict) -> bool:
    return (h["H1"]["value"] == h["H1"]["expect"]
            and h["H2"]["value"] == h["H2"]["expect"]
            and h["H2"]["member"] == h["H2"]["expect_member"]
            and h["H3"]["value"] == h["H3"]["expect"])


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
    committed = {c: {"v": i} for i, c in enumerate(sorted(NINE))}
    got = {c: dict(committed[c]) for c in TRACKED_OK5}
    for c, rel in EXPECTED_MISSING.items():
        got[c] = {"error": f"FileNotFoundError: [Errno 2] No such file or directory: '{root}/{rel}'"}
    t("stageA-good", stage_a_ok(0, got, committed, root), "OK")
    t("stageA-nonzero-rc-plausible-content", stage_a_ok(1, got, committed, root).startswith("BAD rc"), True)
    bad = {**got, "steady24h_fc_chronos": {"error": f"FileNotFoundError: '{root}/some/unrelated/path.json'"}}
    t("stageA-unrelated-missing-path", stage_a_ok(0, bad, committed, root).startswith("BAD error-path"), True)
    tenth = {**got, "extra_cell": {"v": 99}}
    t("stageA-tenth-cell", stage_a_ok(0, tenth, {**committed, "extra_cell": {"v": 99}}, root).startswith("BAD cell-set"), True)
    missing = {c: v for c, v in got.items() if c != "burst1_static_C8"}
    t("stageA-missing-cell", stage_a_ok(0, missing, committed, root).startswith("BAD cell-set"), True)
    drift = {**got, "burst1_static_C8": {"v": -1}}
    t("stageA-value-drift", stage_a_ok(0, drift, committed, root).startswith("BAD value-drift"), True)
    swap = {c: dict(committed[c]) for c in NINE}
    t("stageA-tracked-only-all-ok", stage_a_ok(0, swap, committed, root).startswith("BAD ok-set"), True)

    print("REPRO-PREDICATES-SELFTEST:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(_selftest())
    print(__doc__)
