#!/usr/bin/env python3
"""Structural metric-stack gate (D65, hardened per reviewer msg 208).

Binds EVERY printed cell of tab:cl-metric-stack and tab:cl-readiness and
every promoted derived claim to the artifact -- ORDERED and ROLE-SCOPED:
table cells are parsed by column position (a within-row column swap fails),
and claim operands are bound by regex patterns that fix which number plays
which role (an operand swap or polarity flip fails). Literal-presence-
somewhere is not accepted anywhere.

Checks:
  1. metric_stack.json ladder completeness (p99.5/p99.99 generated).
  2. tab:cl-metric-stack: six arms x six numeric cells, column-ordered.
  3. Claim operands at their loci, role-scoped: absolute worker-seconds,
     55.7-fewer saving, total-delay pair + 3738.1 + 11.0%, survival
     exception interval + 3-vs-2, paired outcomes, p99.5/p99.99 pairs,
     M2 p99.99 exception, 45.0% excess, 754.4 h / 12.6% floor premium,
     7.7% saving -- every derived number recomputed from the artifact.
  4. tab:cl-readiness: three rows, column-ordered (forecast column before
     reactive column), diagnostics cross-checked against the frontier
     declaration, derived percentages recomputed, polarity phrases bound,
     warm-M1 burst3 failure asserted, sweep reversal recomputed.
  5. Conclusion compact claim: 669.7 / 801.8 / 1.20x / 725.4 in role.
  6. Bound-robustness margins from frontier_summary_cells.json, role-scoped.
  7. Figure PDF byte-identical to regeneration; tracked bytes restored in a
     finally path on BOTH success and failure.

Usage: metric_stack_gate.py <TESE_ROOT>   |   --selftest <TESE_ROOT>
Selftest: a relocated clone (eda/.venv symlinked as a DIRECTORY so the
interpreter and matplotlib work) must (0) bind CLEAN, then fail each of the
nine reviewer corruption probes (msg 208) for its intended semantic reason.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def fmt_int(v):
    return f"{int(v):,}".replace(",", "{,}")


def fmt_1dp(v):
    s = f"{v:,.1f}"
    return s.replace(",", "{,}")


def rx(pattern, text, errs, why):
    """Role-scoped regex bind: whitespace-tolerant, order-enforcing."""
    if not re.search(pattern, text):
        errs.append(f"role-bind missing: {why}")


def row_cells(line):
    """Split a tabular row into stripped cell strings, dropping the \\\\."""
    line = line.split("\\\\")[0]
    return [c.strip() for c in line.split("&")]


def bind(tese: Path) -> list:
    errs = []
    base = tese / "simulation/results/comparator_frontier"
    ms = json.loads((base / "metric_stack.json").read_text())
    arms = {r["arm"]: r for r in ms["arms"]}
    tex = (tese / "tex/closedloop.tex").read_text()
    conc = (tese / "tex/conclusion.tex").read_text()
    W = r"[\s\n]+"   # line-wrap tolerant separator

    # 1. generated ladder completeness
    for arm in ("forecast_p90", "reactive"):
        q = arms[arm]["delay_quantiles_all_ms"]
        for k in ("99.5", "99.9", "99.99"):
            if k not in q:
                errs.append(f"artifact missing p{k} for {arm}")

    # 2. tab:cl-metric-stack: column-ORDERED cell binding
    rowmap = [
        ("oracle", "oracle_H0"), ("forecast p90", "forecast_p90"),
        ("reactive", "reactive"), ("warm floor $M{=}2$", "warm_floor_M2"),
        ("static $C{=}8$", "static_C8"), ("warm floor $M{=}6$", "warm_floor_M6"),
    ]
    m = re.search(r"\\label\{tab:cl-metric-stack\}.*?\\end\{tabular\}", tex, re.S)
    if not m:
        return ["tab:cl-metric-stack not found"]
    tab = m.group(0)
    for label, arm in rowmap:
        r = arms[arm]
        lines = [ln for ln in tab.splitlines() if ln.strip().startswith(label)]
        if len(lines) != 1:
            errs.append(f"table row for {label!r}: found {len(lines)} lines")
            continue
        cells = row_cells(lines[0])
        want = [fmt_1dp(round(r["worker_s"] / 3600.0, 1)),
                fmt_1dp(round(r["total_delay_request_s"], 1)),
                fmt_int(r["violations"]["500"]["count"]),
                fmt_int(r["violations"]["1000"]["count"]),
                fmt_int(r["violations"]["2000"]["count"]),
                fmt_1dp(r["violations"]["1000"]["excess_mass_request_s"])]
        if len(cells) != 7:
            errs.append(f"{label}: expected 7 columns, found {len(cells)}")
            continue
        for i, (got, exp) in enumerate(zip(cells[1:], want)):
            if got != exp:
                errs.append(f"{label} column {i + 1}: printed {got!r} != artifact {exp!r}")

    # 3. promoted claims, role-scoped
    fc, rea = arms["forecast_p90"], arms["reactive"]
    q_fc = fc["delay_quantiles_all_ms"]; q_re = rea["delay_quantiles_all_ms"]
    if round(q_fc["99.99"], 1) != 6705.9 or round(q_re["99.99"], 1) != 14724.0:
        errs.append(f"p99.99 artifact drift: {q_fc['99.99']} / {q_re['99.99']}")
    rx(r"p99\.99 \(\\num\{" + re.escape(f"{round(q_fc['99.99'], 1)}")
       + r"\} against" + W + r"\\SI\{" + re.escape(f"{round(q_re['99.99'], 1)}")
       + r"\}\{\\milli\\second\}\)",
       tex, errs, "p99.99 pair in artifact order (forecast first)")
    rx(r"at p99\.5 \(\\num\{" + re.escape(f"{round(q_fc['99.5'], 1)}") + r"\} against" + W
       + r"\\num\{" + re.escape(f"{round(q_re['99.5'], 1)}") + r"\}\)",
       tex, errs, "p99.5 pair in artifact order")
    m2 = arms["warm_floor_M2"]
    if round(m2["delay_quantiles_all_ms"]["99.99"], 1) != 6933.1:
        errs.append("M2 p99.99 artifact drift")
    rx(r"\$M\{=\}2\$'s p99\.99, \\num\{6933\.1\}, sits above the forecast's",
       tex, errs, "M2 p99.99 exception clause")

    saving = (1 - fc["worker_s"] / rea["worker_s"]) * 100
    if round(saving, 1) != 7.7:
        errs.append(f"worker-time saving recomputes to {saving:.4f}%, printed 7.7%")
    ws_fc, ws_re = f"{fc['worker_s']:.1f}", f"{rea['worker_s']:.1f}"
    if (ws_fc, ws_re) != ("2410754.7", "2611319.7"):
        errs.append("worker-second operands drifted from printed values")
    rx(r"provisions \\num\{" + re.escape(ws_fc) + r"\}" + W
       + r"worker-seconds against reactive's \\num\{" + re.escape(ws_re) + r"\}",
       tex, errs, "absolute worker-seconds in role order (forecast provisions, reactive against)")
    if round((rea["worker_s"] - fc["worker_s"]) / 3600.0, 1) != 55.7:
        errs.append("55.7 worker-hour saving does not recompute")
    rx(r"\\num\{55\.7\} fewer" + W + r"worker-hours \(7\.7\\%\)",
       tex, errs, "55.7 FEWER worker-hours (7.7%) with polarity")

    td_fc, td_re = fc["total_delay_request_s"], rea["total_delay_request_s"]
    if round(td_fc, 1) != 30277.5 or round(td_re, 1) != 34015.6:
        errs.append(f"total-delay artifact drift: {td_fc} / {td_re}")
    if round(td_re - td_fc, 1) != 3738.1:
        errs.append("3738.1 request-second reduction does not recompute")
    tdred = (1 - td_fc / td_re) * 100
    if round(tdred, 1) != 11.0:
        errs.append(f"total-delay reduction recomputes to {tdred:.4f}%")
    rx(r"accumulating 11\.0\\% less total delay" + W
       + r"\(\\num\{" + re.escape(f"{round(td_fc, 1)}") + r"\} against \\num\{"
       + re.escape(f"{round(td_re, 1)}") + r"\} request-seconds, a reduction of" + W
       + r"\\num\{3738\.1\}\)",
       tex, errs, "total-delay pair in role order with 11.0% polarity (fc less)")

    fvr = ms["fc_vs_re"]
    ivs = fvr["exception_intervals"]
    if len(ivs) != 1 or ivs[0]["counts_fc_re"] != [3, 2] or \
            round(ivs[0]["interval_s"][0], 2) != 25.08 or \
            round(ivs[0]["interval_s"][1], 2) != 26.23:
        errs.append(f"survival exception drift: {ivs}")
    rx(r"\$\[\\num\{25\.08\}, \\num\{26\.23\}\)\$~s, where it counts" + W
       + r"3 against 2", tex, errs, "exception interval with 3-vs-2 in role order")
    p = fvr["paired"]
    if (p["forecast_better"], p["ties"], p["forecast_worse"]) != (6742, 738027, 4832):
        errs.append(f"paired outcomes drift: {p}")
    rx(r"\\num\{6742\} forecast-better, \\num\{738027\} ties, \\num\{4832\}" + W
       + r"forecast-worse", tex, errs, "paired outcomes with roles attached")

    t = (td_re - td_fc) / (td_re - m2["total_delay_request_s"])
    interp = rea["worker_s"] + t * (m2["worker_s"] - rea["worker_s"])
    if round(interp / 3600.0, 1) != 754.4:
        errs.append(f"total-delay floor interpolation recomputes to {interp/3600:.3f} h")
    if round((interp / fc["worker_s"] - 1) * 100, 1) != 12.6:
        errs.append("12.6% floor premium does not recompute")
    rx(r"costs \\num\{754\.4\}" + W + r"worker-hours, 12\.6\\% more",
       tex, errs, "754.4 h / 12.6% floor premium with polarity (more)")

    m1 = arms["warm_floor_M1"]
    if m1["worker_s"] != rea["worker_s"] or \
            m1["violations"]["1000"]["count"] != rea["violations"]["1000"]["count"]:
        errs.append("M1 != reactive identity broken")
    e_fc = fc["violations"]["1000"]["excess_mass_request_s"]
    e_re = rea["violations"]["1000"]["excess_mass_request_s"]
    if round((1 - e_fc / e_re) * 100, 1) != 45.0:
        errs.append("45.0% excess reduction does not recompute")
    rx(r"\(45\.0\\% less: \\num\{" + re.escape(f"{e_fc:.1f}") + r"\} against \\num\{"
       + re.escape(f"{e_re:.1f}") + r"\}", tex, errs,
       "45.0% excess with operands in role order (fc first)")

    # 4. readiness block: declaration cross-check, ordered table, polarity
    diag = {r["arm"]: r for r in ms["comparisons_by_readiness"]["arms"]}
    fs_, m1w, m2w = (diag["forecast_p90_strict_rewarm"],
                     diag["reactive_warmpool_M1"], diag["reactive_warmpool_M2"])
    fsum = json.loads((base / "frontier_summary.json").read_text())
    decl = fsum["symmetry_repair_diagnostics"]["arms"]
    for arm, r in (("forecast_p90_strict_rewarm", fs_),
                   ("reactive_warmpool_M1", m1w), ("reactive_warmpool_M2", m2w)):
        want_ws = decl[arm]["worker_s_per_window"]["aggregate"]
        if abs(r["worker_s"] - want_ws) > 0.05:
            errs.append(f"{arm} worker_s {r['worker_s']} != frontier declaration {want_ws}")
    if decl["reactive_warmpool_M1"]["p99_ms_per_window"]["burst3"] <= 1000.0:
        errs.append("warm M1 burst3 p99 not a failure in frontier declaration")
    if round(fs_["total_delay_request_s"], 1) != 30620.5 or \
            round(m1w["total_delay_request_s"], 1) != 28014.6:
        errs.append("readiness diagnostic total-delay drift")
    m = re.search(r"\\label\{tab:cl-readiness\}.*?\\end\{tabular\}", tex, re.S)
    if not m:
        errs.append("tab:cl-readiness not found")
    else:
        rt = m.group(0)
        fc_cell = f"{round(fc['worker_s']/3600, 1)} / {fmt_1dp(round(td_fc, 1))}"
        re_cell = f"{round(rea['worker_s']/3600, 1)} / {fmt_1dp(round(td_re, 1))}"
        fs_cell = f"{round(fs_['worker_s']/3600, 1)} / {fmt_1dp(round(fs_['total_delay_request_s'], 1))}"
        m1_cell = f"{round(m1w['worker_s']/3600, 1)} / {fmt_1dp(round(m1w['total_delay_request_s'], 1))}"
        for start, fcol, rcol in (
                ("shipped (mixed)", fc_cell, re_cell),
                ("common warm-pool", fc_cell, m1_cell),
                ("near-symm", fs_cell, re_cell)):
            lines = [ln for ln in rt.splitlines() if ln.strip().startswith(start)]
            if len(lines) != 1:
                errs.append(f"readiness row {start!r}: found {len(lines)} lines")
                continue
            cells = row_cells(lines[0])
            if len(cells) < 3:
                errs.append(f"readiness row {start!r}: malformed")
                continue
            if cells[1] != fcol:
                errs.append(f"readiness row {start!r} forecast column: {cells[1]!r} != {fcol!r}")
            if cells[2] != rcol:
                errs.append(f"readiness row {start!r} reactive column: {cells[2]!r} != {rcol!r}")
    if round((1 - fc["worker_s"] / m1w["worker_s"]) * 100, 1) != 12.1 or \
            round((fc["total_delay_request_s"] / m1w["total_delay_request_s"] - 1) * 100, 1) != 8.1:
        errs.append("common-warm 12.1%/8.1% do not recompute")
    rx(r"12\.1\\% cheaper, 8\.1\\% more delay", tex, errs,
       "common-warm polarity phrase (forecast cheaper, more delay)")
    rx(r"carries 8\.1\\% less" + W + r"total delay than the forecast at 12\.1\\% more cost",
       tex, errs, "warm-M1 polarity phrase (M1 less delay, more cost)")
    if round((1 - fs_["worker_s"] / rea["worker_s"]) * 100, 1) != 8.6 or \
            round((1 - fs_["total_delay_request_s"] / rea["total_delay_request_s"]) * 100, 1) != 10.0:
        errs.append("near-strict 8.6%/10.0% do not recompute")
    rx(r"8\.6\\% cheaper, 10\.0\\% less delay", tex, errs,
       "near-strict polarity phrase")
    if round((m2w["worker_s"] / fc["worker_s"] - 1) * 100, 1) != 19.7 or \
            round(m2w["worker_s"] / 3600.0, 1) != 801.8:
        errs.append("warm-M2 801.8 h / 19.7% do not recompute")
    rx(r"\$M\{=\}2\$ at \\num\{801\.8\}" + W + r"worker-hours, 19\.7\\% above the forecast",
       tex, errs, "801.8 h attaches to warm M2, 19.7% above forecast")
    if not all(m1w["violations"][str(t_)]["count"] < fc["violations"][str(t_)]["count"]
               for t_ in (250, 500, 750, 1000, 1500, 2000)):
        errs.append("common-warm sweep reversal does not recompute at all six thresholds")

    # 5. conclusion compact claim, role-scoped
    if round(m2w["worker_s"] / fc["worker_s"], 2) != 1.20:
        errs.append("1.20x does not recompute")
    rx(r"forecast-informed placement uses" + W + r"669\.7 provisioned worker-hours",
       conc, errs, "conclusion: 669.7 attaches to forecast")
    rx(r"cheapest passing common-warm reactive floor uses" + W
       + r"801\.8 \(1\.20\$\\times\$ the forecast\)", conc, errs,
       "conclusion: 801.8 / 1.20x attaches to the common-warm floor")
    rx(r"shipped reactive arm 725\.4" + W + r"under different readiness mechanics",
       conc, errs, "conclusion: 725.4 attaches to shipped reactive")

    # 6. bound-robustness margins, role-scoped
    fcells = json.loads((base / "frontier_summary_cells.json").read_text())
    EVAL = ("burst1", "burst3", "burst4", "burst5", "steady24h")
    worst = {}
    for c in fcells:
        if c.get("group") in ("core", "family") and c.get("window") in EVAL:
            worst[c["arm"]] = max(worst.get(c["arm"], 0.0), c["p99"])
    for a, v in (("forecast_p90", 681.1), ("static_C8", 807.6),
                 ("warm_floor_M6", 906.6), ("warm_floor_M7", 749.9)):
        if round(worst[a], 1) != v:
            errs.append(f"worst-window p99 for {a}: artifact {worst[a]:.1f} vs printed {v}")
    rx(r"forecast schedule's worst evaluation-window p99 is \\num\{681\.1\}~ms",
       tex, errs, "681.1 attaches to forecast worst window")
    rx(r"static fleet's worst window" + W + r"is \\num\{807\.6\}",
       tex, errs, "807.6 attaches to static worst window")
    rx(r"\$M\{=\}6\$ floor's \\num\{906\.6\}", tex, errs,
       "906.6 attaches to M6 floor")
    if round(arms["warm_floor_M7"]["worker_s"] / arms["static_C8"]["worker_s"], 3) != 1.139 or \
            round(arms["warm_floor_M8"]["worker_s"] / arms["static_C8"]["worker_s"], 3) != 1.239:
        errs.append("M7/M8 vs static ratios do not recompute")
    for lit in ("1.139", "1.239"):
        if lit not in tex:
            errs.append(f"margin ratio literal {lit} missing")

    # 7. figure byte-identity, restore in FINALLY (failure-safe)
    env_fig = tese / "figuras/sim/sim_metric_frontier.pdf"
    tracked = env_fig.read_bytes()
    try:
        rc = subprocess.run([str(tese / "eda/.venv/bin/python"),
                             str(base / "make_metric_stack_figure.py")],
                            capture_output=True)
        if rc.returncode != 0:
            errs.append("figure regeneration failed: "
                        + rc.stderr.decode(errors="replace")[-200:])
        elif env_fig.read_bytes() != tracked:
            errs.append("figure NOT byte-identical to regeneration")
    finally:
        env_fig.write_bytes(tracked)
    return errs


PROBES = [
    ("columns swapped within forecast row",
     "tex/closedloop.tex",
     lambda s: s.replace(
         "forecast p90        & 669.7   & 30{,}277.5",
         "forecast p90        & 30{,}277.5   & 669.7", 1),
     "forecast p90"),
    ("p99.5 changed 752.8 -> 999.9",
     "tex/closedloop.tex",
     lambda s: s.replace("752.8", "999.9"),
     "p99.5"),
    ("p99.99 operands swapped",
     "tex/closedloop.tex",
     lambda s: s.replace("\\num{6705.9} against", "\\num{14724.0} against", 1)
                .replace("\\SI{14724.0}{\\milli\\second}", "\\SI{6705.9}{\\milli\\second}", 1),
     "p99.99"),
    ("55.7 fewer -> 55.7 more",
     "tex/closedloop.tex",
     lambda s: s.replace("\\num{55.7} fewer", "\\num{55.7} more"),
     "FEWER"),
    ("total-delay operands swapped",
     "tex/closedloop.tex",
     lambda s: s.replace("(\\num{30277.5} against \\num{34015.6}",
                         "(\\num{34015.6} against \\num{30277.5}"),
     "total-delay pair"),
    ("paired better/worse roles swapped",
     "tex/closedloop.tex",
     lambda s: s.replace("\\num{6742}", "\\num{XSWAPX}", 1)
                .replace("\\num{4832}", "\\num{6742}", 1)
                .replace("\\num{XSWAPX}", "\\num{4832}", 1),
     "paired"),
    ("common-warm forecast/reactive cells swapped",
     "tex/closedloop.tex",
     lambda s: s.replace(
         "common warm-pool  & 669.7 / 30{,}277.5 & 762.1 / 28{,}014.6",
         "common warm-pool  & 762.1 / 28{,}014.6 & 669.7 / 30{,}277.5"),
     "readiness row"),
    ("readiness polarity reversed",
     "tex/closedloop.tex",
     lambda s: s.replace("12.1\\% cheaper, 8.1\\% more delay",
                         "12.1\\% costlier, 8.1\\% less delay"),
     "polarity"),
    ("conclusion 669.7/801.8 roles swapped",
     "tex/conclusion.tex",
     lambda s: s.replace("669.7", "XSWAPX", 1)
                .replace("801.8", "669.7", 1)
                .replace("XSWAPX", "801.8", 1),
     "conclusion"),
]


def selftest(tese: Path) -> int:
    ok = True
    base = bind(tese)
    print(f"{'PASS' if not base else 'FAIL'}: live tree binds clean ({len(base)} errors)")
    for e in base[:8]:
        print("   ", e)
    ok &= not base
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "clone"
        root.mkdir(parents=True)
        shutil.copytree(tese / "tex", root / "tex")
        cf = root / "simulation/results/comparator_frontier"
        cf.mkdir(parents=True)
        for f in ("metric_stack.json", "make_metric_stack_figure.py",
                  "frontier_summary_cells.json", "frontier_summary.json"):
            shutil.copy(tese / "simulation/results/comparator_frontier" / f, cf / f)
        (root / "figuras/sim").mkdir(parents=True)
        shutil.copy(tese / "figuras/sim/sim_metric_frontier.pdf", root / "figuras/sim/")
        (root / "eda").mkdir()
        # symlink the WHOLE venv directory: interpreter resolves pyvenv.cfg
        # and site-packages through it, so matplotlib imports (msg 208)
        (root / "eda/.venv").symlink_to(tese / "eda/.venv")

        errs = bind(root)
        good = not errs
        print(f"{'PASS' if good else 'FAIL'}: CLEAN relocated tree binds ({len(errs)} errors)")
        for e in errs[:8]:
            print("   ", e)
        ok &= good

        for name, rel, corrupt, expect in PROBES:
            fpath = root / rel
            orig = fpath.read_text()
            mutated = corrupt(orig)
            if mutated == orig:
                print(f"FAIL: probe {name!r} made no change (pattern drift)")
                ok = False
                continue
            fpath.write_text(mutated)
            errs = bind(root)
            hit = [e for e in errs if expect.lower() in e.lower()]
            good = bool(hit)
            print(f"{'PASS' if good else 'FAIL'}: probe {name!r} -> "
                  f"{len(errs)} errors, semantic hit: {hit[0][:70] if hit else 'NONE'}")
            ok &= good
            fpath.write_text(orig)

        # artifact perturbation in the relocated tree must also fail
        ap = cf / "metric_stack.json"
        d = json.loads(ap.read_text())
        for r in d["arms"]:
            if r["arm"] == "forecast_p90":
                r["violations"]["1000"]["count"] += 1
        orig = ap.read_text()
        ap.write_text(json.dumps(d))
        errs = bind(root)
        good = len(errs) > 0
        print(f"{'PASS' if good else 'FAIL'}: perturbed relocated artifact detected ({len(errs)} errors)")
        ok &= good
        ap.write_text(orig)
    print("METRIC-STACK-GATE-SELFTEST:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    args = [a for a in sys.argv[1:] if a != "--selftest"]
    tese = Path(args[0]) if args else Path("/home/gio/tese")
    if "--selftest" in sys.argv:
        return selftest(tese)
    errs = bind(tese)
    for e in errs:
        print("BIND-FAIL:", e)
    print("metric-stack gate:", "OK" if not errs else f"{len(errs)} failures")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
