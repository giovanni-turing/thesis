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
    """Role-scoped regex bind: order-enforcing. `text` must be
    whitespace-normalized (see norm()); patterns use plain single spaces, so
    line wrapping can never false-negative a correct sentence (msg 221)."""
    if not re.search(pattern, text):
        errs.append(f"role-bind missing: {why}")


def norm(s):
    """Collapse all whitespace runs to single spaces for role binding."""
    return re.sub(r"\s+", " ", s)


def row_cells(line):
    """Split a tabular row into stripped cell strings, dropping the \\\\."""
    line = line.split("\\\\")[0]
    return [c.strip() for c in line.split("&")]


def abstract_bodies(tese: Path):
    """Return (PT resumo body, EN abstract body), whitespace-normalized.

    Bind the BODIES, never the whole tese.tex: the D114/D115 provenance
    comments sitting above them legitimately quote the same ruled phrases,
    so a file-wide bind could be satisfied by a comment while the printed
    abstract had lost the scope.  Extraction is brace-balanced from a
    line-initial \\resumo{ / \\abstract{ (comments mention the names but
    never open a brace group)."""
    src = (tese / "tex/tese.tex").read_text()
    out = []
    for cmd in ("resumo", "abstract"):
        m = re.search(r"^\\" + cmd + r"\{", src, re.M)
        if not m:
            return None, None
        j = m.end()
        depth = 1
        while depth:
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
            j += 1
        out.append(norm(src[m.end():j - 1]))
    return out[0], out[1]


def dec(s):
    """'2{,}410{,}754.7' / '2\\,410\\,754,7' -> float (both abstract locales)."""
    s = s.replace("{,}", "").replace("\\,", "").replace(",", ".")
    # a trailing decimal comma became '.'; any earlier ones were separators
    if s.count(".") > 1:
        head, _, tail = s.rpartition(".")
        s = head.replace(".", "") + "." + tail
    return float(s)


def bind(tese: Path) -> list:
    errs = []
    base = tese / "simulation/results/comparator_frontier"
    ms = json.loads((base / "metric_stack.json").read_text())
    arms = {r["arm"]: r for r in ms["arms"]}
    tex = (tese / "tex/closedloop.tex").read_text()
    conc = (tese / "tex/conclusion.tex").read_text()
    texn, concn = norm(tex), norm(conc)   # for role binds (msg 221)
    W = " "   # patterns use plain spaces; rx() input is normalized

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
       + r"\}\{\\milli\\second\}\)", texn, errs, "p99.99 pair in artifact order (forecast first)")
    rx(r"at p99\.5 \(\\num\{" + re.escape(f"{round(q_fc['99.5'], 1)}") + r"\} against" + W
       + r"\\num\{" + re.escape(f"{round(q_re['99.5'], 1)}") + r"\}\)", texn, errs, "p99.5 pair in artifact order")
    m2 = arms["warm_floor_M2"]
    if round(m2["delay_quantiles_all_ms"]["99.99"], 1) != 6933.1:
        errs.append("M2 p99.99 artifact drift")
    rx(r"\$M\{=\}2\$'s p99\.99, \\num\{6933\.1\}, sits above the forecast's", texn, errs, "M2 p99.99 exception clause")

    saving = (1 - fc["worker_s"] / rea["worker_s"]) * 100
    if round(saving, 1) != 7.7:
        errs.append(f"worker-time saving recomputes to {saving:.4f}%, printed 7.7%")
    ws_fc, ws_re = f"{fc['worker_s']:.1f}", f"{rea['worker_s']:.1f}"
    if (ws_fc, ws_re) != ("2410754.7", "2611319.7"):
        errs.append("worker-second operands drifted from printed values")
    rx(r"provisions \\num\{" + re.escape(ws_fc) + r"\}" + W
       + r"worker-seconds against reactive's \\num\{" + re.escape(ws_re) + r"\}", texn, errs, "absolute worker-seconds in role order (forecast provisions, reactive against)")
    if round((rea["worker_s"] - fc["worker_s"]) / 3600.0, 1) != 55.7:
        errs.append("55.7 worker-hour saving does not recompute")
    rx(r"\\num\{55\.7\} fewer" + W + r"worker-hours \(7\.7\\%\)", texn, errs, "55.7 FEWER worker-hours (7.7%) with polarity")

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
       + r"\\num\{3738\.1\}\)", texn, errs, "total-delay pair in role order with 11.0% polarity (fc less)")

    fvr = ms["fc_vs_re"]
    ivs = fvr["exception_intervals"]
    if len(ivs) != 1 or ivs[0]["counts_fc_re"] != [3, 2] or \
            round(ivs[0]["interval_s"][0], 2) != 25.08 or \
            round(ivs[0]["interval_s"][1], 2) != 26.23:
        errs.append(f"survival exception drift: {ivs}")
    rx(r"\$\[\\num\{25\.08\}, \\num\{26\.23\}\)\$~s, where it counts" + W
       + r"3 against 2", texn, errs, "exception interval with 3-vs-2 in role order")
    p = fvr["paired"]
    if (p["forecast_better"], p["ties"], p["forecast_worse"]) != (6742, 738027, 4832):
        errs.append(f"paired outcomes drift: {p}")
    rx(r"\\num\{6742\} forecast-better, \\num\{738027\} ties, \\num\{4832\}" + W
       + r"forecast-worse", texn, errs, "paired outcomes with roles attached")

    t = (td_re - td_fc) / (td_re - m2["total_delay_request_s"])
    interp = rea["worker_s"] + t * (m2["worker_s"] - rea["worker_s"])
    if round(interp / 3600.0, 1) != 754.4:
        errs.append(f"total-delay floor interpolation recomputes to {interp/3600:.3f} h")
    if round((interp / fc["worker_s"] - 1) * 100, 1) != 12.6:
        errs.append("12.6% floor premium does not recompute")
    rx(r"costs \\num\{754\.4\}" + W + r"worker-hours, 12\.6\\% more", texn, errs, "754.4 h / 12.6% floor premium with polarity (more)")

    m1 = arms["warm_floor_M1"]
    if m1["worker_s"] != rea["worker_s"] or \
            m1["violations"]["1000"]["count"] != rea["violations"]["1000"]["count"]:
        errs.append("M1 != reactive identity broken")
    e_fc = fc["violations"]["1000"]["excess_mass_request_s"]
    e_re = rea["violations"]["1000"]["excess_mass_request_s"]
    if round((1 - e_fc / e_re) * 100, 1) != 45.0:
        errs.append("45.0% excess reduction does not recompute")
    rx(r"\(45\.0\\% less: \\num\{" + re.escape(f"{e_fc:.1f}") + r"\} against \\num\{"
       + re.escape(f"{e_re:.1f}") + r"\}", texn, errs,
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
    rx(r"12\.1\\% cheaper, 8\.1\\% more delay", texn, errs,
       "common-warm polarity phrase (forecast cheaper, more delay)")
    rx(r"carries 8\.1\\% less" + W + r"total delay than the forecast at 12\.1\\% more cost", texn, errs, "warm-M1 polarity phrase (M1 less delay, more cost)")
    if round((1 - fs_["worker_s"] / rea["worker_s"]) * 100, 1) != 8.6 or \
            round((1 - fs_["total_delay_request_s"] / rea["total_delay_request_s"]) * 100, 1) != 10.0:
        errs.append("near-strict 8.6%/10.0% do not recompute")
    rx(r"8\.6\\% cheaper, 10\.0\\% less delay", texn, errs,
       "near-strict polarity phrase")
    if round((m2w["worker_s"] / fc["worker_s"] - 1) * 100, 1) != 19.7 or \
            round(m2w["worker_s"] / 3600.0, 1) != 801.8:
        errs.append("warm-M2 801.8 h / 19.7% do not recompute")
    rx(r"\$M\{=\}2\$ at \\num\{801\.8\}" + W + r"worker-hours, 19\.7\\% above the forecast", texn, errs, "801.8 h attaches to warm M2, 19.7% above forecast")
    if not all(m1w["violations"][str(t_)]["count"] < fc["violations"][str(t_)]["count"]
               for t_ in (250, 500, 750, 1000, 1500, 2000)):
        errs.append("common-warm sweep reversal does not recompute at all six thresholds")

    # 5. conclusion compact claim, role-scoped
    if round(m2w["worker_s"] / fc["worker_s"], 2) != 1.20:
        errs.append("1.20x does not recompute")
    rx(r"forecast-informed placement uses" + W + r"669\.7 provisioned worker-hours", concn, errs, "conclusion: 669.7 attaches to forecast")
    rx(r"cheapest passing common-warm reactive floor uses" + W
       + r"801\.8 \(1\.20\$\\times\$ the forecast\)", concn, errs,
       "conclusion: 801.8 / 1.20x attaches to the common-warm floor")
    rx(r"shipped direct-reactive arm's 725\.4 is not an" + W
       + r"equal-compliance comparator: that arm fails burst3", concn, errs,
       "conclusion: 725.4 attaches to the failing shipped direct-reactive arm")

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
    rx(r"forecast schedule's worst evaluation-window p99 is \\num\{681\.1\}~ms", texn, errs, "681.1 attaches to forecast worst window")
    rx(r"static fleet's worst window" + W + r"is \\num\{807\.6\}", texn, errs, "807.6 attaches to static worst window")
    rx(r"\$M\{=\}6\$ floor's \\num\{906\.6\}", texn, errs,
       "906.6 attaches to M6 floor")
    if round(arms["warm_floor_M7"]["worker_s"] / arms["static_C8"]["worker_s"], 3) != 1.139 or \
            round(arms["warm_floor_M8"]["worker_s"] / arms["static_C8"]["worker_s"], 3) != 1.239:
        errs.append("M7/M8 vs static ratios do not recompute")

    # 6c. D68: adversarial strict cells + derived integer-ms passing bounds.
    # The declared gate is strict p99 < B, so the lowest passing integer
    # bound is floor(worst)+1 per population; populations must not merge.
    import math
    worst_strict = max(c["p99"] for c in fcells
                       if c.get("group") == "adversarial"
                       and c.get("arm") == "forecast_p90_strict_rewarm"
                       and c.get("window") in EVAL)
    if round(worst_strict, 3) != 732.999:
        errs.append(f"frontier strict worst window drifts: {worst_strict}")
    fact = json.loads((tese / "simulation/results/factorial_issuetime/"
                       "factorial_issuetime_p90_rho15_results.json").read_text())
    fact_max = max(r["p99_ms"] for r in fact["results"]
                   if r.get("readiness") == "strict")
    if round(fact_max, 3) != 733.643:
        errs.append(f"strict factorial maximum drifts: {fact_max}")
    derived_bounds = [
        ("shipped warm-pool forecast", worst["forecast_p90"], 682),
        ("frontier strict sensitivity", worst_strict, 733),
        ("strict factorial", fact_max, 734),
        ("static", worst["static_C8"], 808),
        ("M6 floor", worst["warm_floor_M6"], 907),
        ("M7 floor", worst["warm_floor_M7"], 750),
    ]
    for name, w, b in derived_bounds:
        if math.floor(w) + 1 != b:
            errs.append(f"integer passing bound for {name}: floor({w})+1 != {b}")
    rx(r"survives any bound down to" + W + r"\\SI\{682\}\{\\milli\\second\} under warm-pool readiness",
       texn, errs, "682 bound scoped to warm-pool readiness")
    rx(r"frontier strict" + W + r"re-warm sensitivity's worst window is \\SI\{732\.999\}\{\\milli\\second\}",
       texn, errs, "frontier strict role + exact 732.999 (msg 227 precision)")
    rx(r"pass survives down to" + W + r"\\SI\{733\}\{\\milli\\second\}", texn, errs,
       "frontier strict integer bound printed 733")
    rx(r"factorial's maximum,?" + W + r"?\\SI\{733\.6\}\{\\milli\\second\}, passes down to \\SI\{734\}\{\\milli\\second\}",
       texn, errs, "strict factorial 733.6 -> 734 separately scoped")
    rx(r"at integer-millisecond" + W + r"bounds over the tested 682--\\SI\{1000\}\{\\milli\\second\} interval, under the" + W
       + r"shipped warm-pool forecast readiness", texn, errs,
       "682-1000 sweep scoped to integer bounds + shipped warm-pool readiness")
    # D69: chapter crossing roles bound with their arm ratios
    rx(r"below \\SI\{907\}\{\\milli\\second\} the 1\.042\$\\times\$ floor is no" + W
       + r"longer all-passing \(\$M\{=\}7\$, at 1\.139", texn, errs,
       "907 crossing bound to M6->M7 role")
    rx(r"below" + W + r"\\SI\{750\}\{\\milli\\second\}, \$M\{=\}8\$ at 1\.239", texn, errs,
       "750 crossing bound to M8 role")
    rx(r"below" + W + r"\\SI\{808\}\{\\milli\\second\} the static reference itself fails",
       texn, errs, "808 crossing bound to static role")
    # D69: conclusion crossing claims bound independently
    rx(r"down to \\SI\{682\}\{\\milli\\second\} under warm-pool readiness; under the strict" + W
       + r"re-warm sensitivity the forecast's worst window is \\SI\{733\}\{\\milli\\second\}",
       concn, errs, "conclusion 682+warm-pool qualifier+733 bound")
    # D69: BOTH deck mirrors bound to the same claims and to each other
    deckA = norm((tese / "defense/reveal/index.html").read_text())
    deckB = norm((tese / "defense/deck_single.html").read_text())
    DFRAG = ("Tighten the 1 s bound (integer-ms crossings): the shipped "
             "warm-pool forecast still passes down to <b>682 ms</b>; "
             "static (readiness-independent) holds to 808 ms, the cheapest "
             "passing strict-rewarm floor to 907 ms. The verdict is not a "
             "gift of the convention.")
    for name, dk in (("reveal/index.html", deckA), ("deck_single.html", deckB)):
        if DFRAG not in dk:
            errs.append(f"deck {name}: complete integer-scope margins tile missing or diverged (msg 228)")
    for lit in ("1.139", "1.239"):
        if lit not in tex:
            errs.append(f"margin ratio literal {lit} missing")

    # 6b. span-level language-pool stack (tab:cl-llm-week-stack): column-
    # ordered cells against llm_week_stack.json, derived claims recomputed.
    lw = json.loads((tese / "simulation/results/llm_week/llm_week_stack.json").read_text())
    la = lw["arms"]
    pop = lw.get("population", {})
    if (pop.get("num_requests") != 749601
            or pop.get("input_tokens_total") != 2205332831
            or pop.get("output_tokens_total") != 140631564
            or pop.get("identical_across_all_five_reports") is not True):
        errs.append("llm-week population/token totals drift in artifact (msg 221)")
    for arm_name, r in la.items():
        if r["num_requests"] != 749601:
            errs.append(f"llm-week arm {arm_name}: num_requests != 749601")
    if pop.get("processed_tokens_total") != 2345964395:
        errs.append("llm-week processed_tokens_total drift (msg 223)")
    lc = lw.get("lead_config", {})
    if lc.get("lead_s") != 60:
        errs.append("llm-week lead_config lead_s != 60 (msg 223)")
    want_occ = {"launch.sh": 2, "run_llm_week_p50.sh": 1,
                "run_llm_week_models.sh": 1}
    for drv, n in want_occ.items():
        d = lc.get(drv, {})
        if d.get("lead_s") != 60 or d.get("occurrences") != n:
            errs.append(f"llm-week lead_config for {drv} != 60 x{n} (msg 224)")
    rx(r"language lead \$L\{=\}\\SI\{60\}\{\\second\}\$ is the held-cursor",
       texn, errs, "body L=60 claim bound to held-cursor role (msg 224)")
    rx(r"continuous planner replays, \$L\{=\}\\SI\{60\}\{\\second\}\$ by" + W
       + r"construction", texn, errs, "llm-week caption L=60 matches artifact lead_config")
    # msg 223 prose role binds: GPU-hour roles, reactive TTFT p99 role,
    # e2e polarity, ITL roles -- all against artifact-derived operands.
    rx(r"\\textbf\{passes the week\} at TTFT" + W
       + r"p99 \\SI\{651\}\{\\milli\\second\} \(ITL p99 \\SI\{6\.4\}\{\\milli\\second\}\) for 518\.6" + W
       + r"H100 GPU-hours", texn, errs,
       "forecast role: 651 ms + 518.6 GPU-h attach to the forecast arm")
    rx(r"\\textbf\{fails the week outright\} \(TTFT p99 1\{,\}197\\,\\si\{\\milli\\second\}\) on" + W
       + r"281\.8 GPU-hours", texn, errs,
       "reactive role: 1,197 ms + 281.8 GPU-h attach to reactive")
    if round(la["reactive_stock_planner"]["ttft_ms"]["p99"], 0) != 1197.0:
        errs.append("reactive span TTFT p99 drifts from printed 1,197 ms")
    if round(la["forecast_p90_chronos"]["gpu_hours"], 1) != 518.6 or \
            round(la["reactive_stock_planner"]["gpu_hours"], 1) != 281.8:
        errs.append("llm-week GPU-hour operands drift from printed values")
    rx(r"total end-to-end mass 16\.5\\% less", texn, errs,
       "16.5% e2e polarity (LESS, not more)")
    rx(r"\(6\.41 against 21\.28~ms", texn, errs,
       "ITL roles in artifact order (forecast 6.41 first)")
    if round(la["forecast_p90_chronos"]["itl_p99_ms"], 2) != 6.41 or \
            round(la["reactive_stock_planner"]["itl_p99_ms"], 2) != 21.28:
        errs.append("ITL operands drift from printed values")
    m = re.search(r"\\label\{tab:cl-llm-week-stack\}.*?\\end\{tabular\}", tex, re.S)
    if not m:
        errs.append("tab:cl-llm-week-stack not found")
    else:
        lt = m.group(0)
    rx(r"language-pool grading over the same \\num\{749601\}-request"
       + W + r"evaluation span", texn, errs,
       "llm-week caption population (749,601)")
    if m:
        lrow = [
            ("forecast p90 (Chronos)", "forecast_p90_chronos"),
            ("forecast p90 (Toto)", "forecast_p90_toto"),
            ("forecast p90 (TimesFM)", "forecast_p90_timesfm"),
            ("forecast p50 (thrift)", "forecast_p50"),
            ("reactive (stock planner)", "reactive_stock_planner"),
        ]
        for label, arm in lrow:
            r = la[arm]
            lines = [ln for ln in lt.splitlines() if ln.strip().startswith(label)]
            if len(lines) != 1:
                errs.append(f"llm-week row {label!r}: found {len(lines)} lines")
                continue
            cells = row_cells(lines[0])
            want = [fmt_1dp(r["gpu_hours"]), fmt_1dp(r["ttft_ms"]["p99"]),
                    fmt_1dp(r["ttft_ms"]["p95"]),
                    fmt_1dp(r["total_ttft_mass_request_s"]),
                    fmt_1dp(r["total_e2e_mass_request_s"]),
                    f"{r['itl_p99_ms']:.2f}"]
            if len(cells) != 7:
                errs.append(f"llm-week {label}: expected 7 columns, found {len(cells)}")
                continue
            for i, (got, exp) in enumerate(zip(cells[1:], want)):
                if got != exp:
                    errs.append(f"llm-week {label} column {i + 1}: printed {got!r} != artifact {exp!r}")
    lfc, lre = la["forecast_p90_chronos"], la["reactive_stock_planner"]
    if round((1 - lfc["total_ttft_mass_request_s"] / lre["total_ttft_mass_request_s"]) * 100, 1) != 37.4:
        errs.append("llm-week 37.4% TTFT-mass reduction does not recompute")
    if round((1 - lfc["total_e2e_mass_request_s"] / lre["total_e2e_mass_request_s"]) * 100, 1) != 16.5:
        errs.append("llm-week 16.5% e2e-mass reduction does not recompute")
    if lw["derived"]["p99_ttft_model_invariant_ms"] != [651.1]:
        errs.append("llm-week 651.1 model-invariance broken in artifact")
    rx(r"total TTFT mass \\num\{43598\.8\}" + W
       + r"request-seconds against reactive's \\num\{69671\.3\} \(37\.4\\% less\)", texn, errs, "llm-week total-mass pair in role order with polarity")
    rx(r"p95" + W + r"\\num\{178\.9\} against \\num\{501\.9\}~ms", texn, errs, "llm-week p95 pair in role order")

    # 6d. D71: fixed-vs-expanding context, held-out vs seven-day populations,
    # and the C2 outside-set role -- semantic binds the multiset baseline
    # cannot protect.
    rx(r"preregistered fixed-context" + W
       + r"protocol defines no forecast arm over the full trace", texn, errs,
       "seven-day forecast-free RULE (fixed-context protocol, not impossibility)")
    rx(r"seven-day rows are forecast-free", texn, errs,
       "seven-day rows labeled forecast-free")
    rx(r"scoring its" + W + r"1\.4-day context split as targets would violate the split",
       texn, errs, "1.4-day context-split role (targets violation)")
    rx(r"expanding-context forecast construction exists as a" + W
       + r"tracked diagnostic and is not part of the frozen protocol", texn, errs,
       "expanding-context acknowledged and excluded from frozen protocol")
    rx(r"Static \$C\{=\}2\$ is an" + W
       + r"encoder-only comparator outside the 29-arm composed set", texn, errs,
       "C2 marked outside the composed set")
    rx(r"All primary forecast evaluation" + W
       + r"evidence uses the held-out 5\.60-day span", texn, errs,
       "population hierarchy: primary evidence = held-out 5.60-day span")
    rx(r"separately labeled forecast-free seven-day aggregate diagnostic", texn,
       errs, "seven-day diagnostic labeled separately")

    # 6e. D72: abstract population roles, conclusion denominator label,
    # and the deck post-hoc disclosures -- multiset-invariant role reversals.
    # Re-anchored 2026-07-28 (D114/D115): the abstracts were rewritten as
    # single paragraphs, so the population roles now attach to the new
    # sentences.  Bound against the BODIES only (see abstract_bodies).
    ptn, enn = abstract_bodies(tese)
    if ptn is None:
        return errs + ["abstract bodies not extractable from tex/tese.tex"]
    rx(r"\(Azure, one million requests over seven days\), request rate"
       r" misrepresents vision demand", enn, errs,
       "EN abstract: full-trace population attached to the trace description")
    rx(r"over the 5\.60-day, 749\{,\}601-request evaluation span --- no burst"
       r" definition, SLA cutoff, or percentile selection in either operand ---"
       r" the p90-forecast schedule provisions", enn, errs,
       "EN abstract: evaluation population attached to the full-span RQ3 lead")
    rx(r"On the same span that schedule holds the encoder tail bound at"
       r" 0\.62\\vez\{\}", enn, errs,
       "EN abstract: 0.62x claim kept on the SAME evaluation span (anaphora)")
    rx(r"\(Azure, um milhão de requisições em sete dias\), a taxa de requisições"
       r" representa mal a demanda de visão", ptn, errs,
       "PT abstract: full-trace population attached to the trace description")
    rx(r"nos 5,60 dias e 749\\,601 requisições da avaliação --- sem definição de"
       r" rajada, corte de SLA ou seleção de percentil em nenhum operando ---"
       r" o cronograma de previsão p90 provisiona", ptn, errs,
       "PT abstract: evaluation population attached to the full-span RQ3 lead")
    rx(r"No mesmo intervalo esse cronograma sustenta o limite de cauda do"
       r" codificador a 0,62\\vez\{\}", ptn, errs,
       "PT abstract: 0.62x claim kept on the SAME evaluation span (anaphora)")
    rx(r"under request-matched normalization the" + W
       + r"published language point \(p90 at conversion scale 8\) reads 1\.03\$\\times\$",
       concn, errs, "conclusion: 1.03x bound to REQUEST-matched denominator + p90/s8")
    for name, dk in (("reveal/index.html", deckA), ("deck_single.html", deckB)):
        if "reactive-favorable post-hoc envelope" not in dk:
            errs.append(f"deck {name}: post-hoc-envelope disclosure (validity tile) missing (msg 244)")
        if "reactive-favorable post-hoc floor envelope" not in dk:
            errs.append(f"deck {name}: post-hoc floor-envelope disclosure (conclusion tile) missing (msg 244)")
        if "no symmetric forecast+floor sweep" not in dk:
            errs.append(f"deck {name}: unswept-family disclosure (validity tile) missing (msg 244)")
        if "a symmetric forecast+floor family was not swept" not in dk:
            errs.append(f"deck {name}: unswept-family disclosure (conclusion tile) missing (msg 244)")

    # 6f. Silicon physical-replay integration (bridge 199, settled commit
    # 6a8b2d7): replicate estimands with dispersion, the like-for-like vLLM
    # anchor triple, the 199c sensitivity-not-bound role, and the narrow
    # scope. Estimands recomputed 2026-07-28 from committed rep.json files.
    metn = norm((tese / "tex/metodologia.tex").read_text())
    rx(r"\$782\.455 \\pm 0\.270\$\\,ms --- inside the \\SI\{1\}\{\\second\} bound",
       metn, errs, "replay: fc estimand 782.455+-0.270 bound to the 1 s PASS role")
    rx(r"\$22\{,\}565\.317 \\pm 0\.935\$\\,ms", metn, errs,
       "replay: reactive estimand 22,565.317+-0.935 present")
    rx(r"static-\$C\{=\}8\$ feasible \(\\num\{745\.758\}\\,ms direct, \\num\{747\.169\}\\,ms"
       r" per-\$N\$ simulator-scaled, against \\num\{717\.755\}\\,ms stored simulation p99; the canonical phase-E",
       metn, errs, "replay: canonical vLLM exact-retime triple bound to static feasibility (D109)")
    rx(r"not a conservative bound", metn, errs,
       "replay: HF-eager carries the 199c sensitivity-not-bound role")
    rx(r"anchors \\emph\{encoder delays only\} \(resource-time economics remain"
       r" simulated by construction\)", metn, errs,
       "replay: encoder-delays-only scope with simulated-economics clause")
    rx(r"forecast-versus-reactive delay verdict for this window survives physical retiming",
       metn, errs, "replay: verdict claim scoped to THIS WINDOW")

    # 6g. Tier-3 calm-day replay (evidence commit 1511606): HF-eager
    # estimands, the vLLM like-for-like PASS quad, the banked triple, and
    # the engine-band-conditional role.
    rx(r"\$1\{,\}120\.967 \\pm 0\.456\$ and \$1\{,\}121\.004 \\pm 0\.143\$\\,ms",
       metn, errs, "calm day: fc/re HF-eager estimand pair adjacent (near-tie form)")
    rx(r"\$610\.596 \\pm 0\.175\$\\,ms", metn, errs,
       "calm day: static HF-eager estimand present")
    rx(r"Under the canonical vLLM representations, every arm passes the calm day"
       r" \(forecast/reactive \\num\{738\.751\} direct and \\num\{742\.587\} per-\$N\$"
       r" scaled; static \\num\{434\.516\}/\\num\{435\.497\}\\,ms\)",
       metn, errs, "calm day: canonical vLLM quad bound to the every-arm PASS role (D109)")
    rx(r"no resolved p99 separation from reactive in this experiment",
       metn, errs, "calm day: near-tie stated as unresolved separation, not equivalence (D110)")
    rx(r"static \\num\{418\.205\}, forecast \\num\{681\.117\}, reactive \\num\{684\.999\}\\,ms",
       metn, errs, "calm day: banked sim triple in the inside-the-bound sentence")
    rx(r"engine-band-conditional", metn, errs,
       "calm day: absolutes carry the engine-band-conditional role")

    # 6h. D114: the four abstract roles the compression had reopened, plus
    # the convention-minimized full-span pair that now LEADS RQ3 -- bound in
    # BOTH languages against the abstract bodies (ptn/enn from 6e).  Before
    # this section the abstract portion of the gate bound only the two
    # population phrases, so none of these regressions was detectable.

    # 6h-A. burst-window population of the encoder breach (D114.1).  The
    # evidence is inside the burst window, never a full-trace or steady-head
    # claim (tex/metodologia.tex:604-621,643-648).
    rx(r"reproduces the decoupling: \\emph\{inside the burst window\} the encoder"
       r" pool misses its tail bound at the trace's own recorded rate, invisibly"
       r" to rate- and utilization monitors", enn, errs,
       "EN abstract: burst-window qualifier on the encoder-breach claim (D114.1)")
    rx(r"reproduz o desacoplamento: \\emph\{dentro da janela de rajada\} o"
       r" \\emph\{pool\} codificador viola seu limite de cauda na taxa registrada"
       r" pelo próprio \\emph\{trace\}, invisível a monitores de taxa e utilização",
       ptn, errs,
       "PT abstract: burst-window qualifier on the encoder-breach claim (D114.1)")

    # 6h-B. floor endpoints + boundaries (D114.2).  The adjudicated choice
    # here is REMOVAL-WHOLE: under the one-page/500-word limits the floor
    # claim and its numbers left the abstracts together, which D114.2
    # authorizes, rather than surviving as a scope-free range.  So the bind
    # is conditional: if either endpoint literal EVER comes back, all three
    # ruled boundaries must come back with it (forecast fixed at one
    # operating point; no symmetric forecast-plus-floor family; the two
    # named floor members).  A bare "1.20x to 1.67x" therefore fails.
    floor_rules = (
        ("EN", enn, (r"reactive-favorable", r"post-hoc",
                     r"no symmetric forecast-plus-floor",
                     r"M\{=\}2", r"M\{=\}6")),
        ("PT", ptn, (r"favorável ao reativo", r"post hoc",
                     r"nenhuma varredura simétrica de previsão-mais-piso",
                     r"M\{=\}2", r"M\{=\}6")),
    )
    for lang, body, required in floor_rules:
        if re.search(r"1[.,]20|1[.,]67", body):
            for pat in required:
                if not re.search(pat, body):
                    errs.append(
                        f"{lang} abstract: floor endpoints present without the "
                        f"adjudicated boundary /{pat}/ -- a scope-free floor "
                        f"range is exactly the D114.2 regression")

    # 6h-C. language operating point (D114.3): the causal operator is that
    # the SLA holds ONLY through tail-aware conversion, and the near-break-
    # even operands belong to the published p90/scale-8 point -- other
    # language points have different ratios (tex/closedloop.tex:1006-1018).
    # The PT mirror must name the matching OPERATION, not just the axis.
    rx(r"The secondary language policy holds its SLA only through tail-aware"
       r" conversion and, at its published p90/scale-8 point, is near"
       r" break-even against static \(0\.965\\vez\{\} time-matched, 1\.03\\vez\{\}"
       r" request-matched\)", enn, errs,
       "EN abstract: language SLA held ONLY-through tail-aware conversion, "
       "operands bound to the p90/scale-8 point (D114.3)")
    rx(r"A política secundária de linguagem sustenta seu SLA apenas por conversão"
       r" ciente de cauda e, em seu ponto publicado p90/escala 8, fica em"
       r" quase-equilíbrio face ao estático \(0,965\\vez\{\} pareado por tempo,"
       r" 1,03\\vez\{\} pareado por requisições\)", ptn, errs,
       "PT abstract: language ONLY-through operator, p90/escala 8 point, and "
       "the matching-operation names 'pareado por tempo/requisições' (D114.3)")

    # 6h-D. live-versus-physical separation (D114.4): live evidence is the
    # fastest-onset LANGUAGE-pool p90/reactive result, one run per policy
    # through the real control plane with mocked engines
    # (tex/metodologia.tex:737-742,780-788); physical evidence is
    # five-repetition ENCODER-ONLY frozen-dispatch retiming on one RTX 5090
    # (tex/metodologia.tex:338-367,406-410).  Different pools, different
    # estimands -- they must not fuse into one "verdict".
    rx(r"The fastest-onset language-pool p90/reactive verdict agrees in one live"
       r" Dynamo run per policy \(real control plane, mocked engines\);"
       r" separately, five-repetition encoder-only frozen-dispatch retiming on"
       r" one RTX~5090 preserves that window's simulated forecast/reactive"
       r" verdict\. Week-scale economics remain simulated\.", enn, errs,
       "EN abstract: live (LANGUAGE pool) and physical (ENCODER-only) evidence "
       "separated, both pools named, week-scale still simulated (D114.4)")
    rx(r"O veredicto p90/reativo do \\emph\{pool\} de linguagem na rajada de"
       r" início mais rápido confirma-se em uma execução ao vivo do Dynamo por"
       r" política \(plano de controle real, \\emph\{engines\} simulados\); em"
       r" separado, a retemporização de despachos congelados, só do codificador,"
       r" em cinco repetições numa RTX~5090, preserva o veredicto simulado"
       r" previsão/reativo dessa janela\. A economia em escala semanal permanece"
       r" simulada\.", ptn, errs,
       "PT abstract: live (LANGUAGE pool) and physical (ENCODER-only) evidence "
       "separated, both pools named, week-scale still simulated (D114.4)")

    # 6h-E. the convention-minimized full-span RQ3 lead (D114.5).  Operands
    # are role-scoped (which number provisions, which arm is the comparator,
    # which pair is delay), the derived percentages are RECOMPUTED, the two
    # languages must carry identical operands, and both must agree with the
    # chapter locus tex/closedloop.tex:674-704.
    en_lead = re.search(
        r"the p90-forecast schedule provisions ([\d{},.]+) against the"
        r" identically informed direct-reactive arm's ([\d{},.]+) worker-seconds"
        r" \(([\d.]+)\\% less\) and accumulates ([\d{},.]+) against ([\d{},.]+)"
        r" request-seconds of total encoder delay \(([\d.]+)\\% less\)", enn)
    pt_lead = re.search(
        r"o cronograma de previsão p90 provisiona ([\d\\,.]+)"
        r" \\emph\{worker\}-segundos contra ([\d\\,.]+) do braço reativo direto"
        r" identicamente informado \(([\d,]+)\\% a menos\) e acumula"
        r" ([\d\\,.]+) contra ([\d\\,.]+) requisição-segundos de atraso total do"
        r" codificador \(([\d,]+)\\% a menos\)", ptn)
    if not en_lead:
        errs.append("EN abstract: full-span RQ3 lead missing or role-scrambled "
                    "(forecast worker-seconds / identically informed "
                    "direct-reactive comparator / delay pair) (D114.5)")
    if not pt_lead:
        errs.append("PT abstract: full-span RQ3 lead missing or role-scrambled "
                    "(forecast worker-seconds / identically informed "
                    "direct-reactive comparator / delay pair) (D114.5)")
    if en_lead and pt_lead:
        en_v = [dec(g) for g in en_lead.groups()]
        pt_v = [dec(g) for g in pt_lead.groups()]
        if en_v != pt_v:
            errs.append(f"abstract RQ3 lead: EN and PT operands disagree "
                        f"{en_v} vs {pt_v} (D114.5)")
        fc_ws, re_ws, pct_ws, fc_d, re_d, pct_d = en_v
        # the chapter locus owns these numbers; the abstract may not drift
        for val, lit in ((fc_ws, "2410754.7"), (re_ws, "2611319.7"),
                         (fc_d, "30277.5"), (re_d, "34015.6")):
            if f"\\num{{{lit}}}" not in tex:
                errs.append(f"closedloop.tex lost the RQ3 lead operand {lit}")
            if abs(val - float(lit)) > 1e-6:
                errs.append(f"abstract RQ3 lead operand {val} != chapter {lit}")
        if not (fc_ws < re_ws and fc_d < re_d):
            errs.append("abstract RQ3 lead: polarity reversed -- the forecast "
                        "arm must be the SMALLER of both operand pairs (D114.5)")
        for got, a, b, what in ((pct_ws, fc_ws, re_ws, "worker-second"),
                                (pct_d, fc_d, re_d, "total-delay")):
            want = round((b - a) / b * 100, 1)
            if abs(got - want) > 0.05:
                errs.append(f"abstract RQ3 lead: {what} saving states {got}% "
                            f"but the operands recompute to {want}%")
        # the lead must stay convention-free in BOTH languages
        rx(r"no burst definition, SLA cutoff, or percentile selection in either"
           r" operand", enn, errs,
           "EN abstract: RQ3 lead declares no burst/SLA/percentile convention")
        rx(r"sem definição de rajada, corte de SLA ou seleção de percentil em"
           r" nenhum operando", ptn, errs,
           "PT abstract: RQ3 lead declares no burst/SLA/percentile convention")
        rx(r"full-span", enn, errs, "EN abstract: RQ3 lead marked full-span")
        rx(r"cobre todo o intervalo", ptn, errs,
           "PT abstract: RQ3 lead marked full-span")

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
    ("llm-week forecast/reactive TTFT-mass operands swapped",
     "tex/closedloop.tex",
     lambda s: s.replace("total TTFT mass \\num{43598.8}",
                         "total TTFT mass \\num{69671.3}", 1)
                .replace("against reactive's \\num{69671.3}",
                         "against reactive's \\num{43598.8}", 1),
     "llm-week total-mass"),
    ("llm-week table GPU-hours column swapped with p99",
     "tex/closedloop.tex",
     lambda s: s.replace(
         "reactive (stock planner) & 281.8 & 1{,}196.6",
         "reactive (stock planner) & 1{,}196.6 & 281.8", 1),
     "llm-week reactive"),
    ("llm-week prose GPU-hour roles swapped",
     "tex/closedloop.tex",
     lambda s: s.replace("for 518.6", "for 281.8", 1)
                .replace("on\n281.8 GPU-hours", "on\n518.6 GPU-hours", 1),
     "forecast role"),
    ("llm-week reactive p99 fabricated 1,197 -> 1,999",
     "tex/closedloop.tex",
     lambda s: s.replace("TTFT p99 1{,}197\\,", "TTFT p99 1{,}999\\,", 1),
     "reactive role"),
    ("llm-week 16.5% polarity flipped",
     "tex/closedloop.tex",
     lambda s: s.replace("total end-to-end mass 16.5\\% less",
                         "total end-to-end mass 16.5\\% more", 1),
     "polarity"),
    ("llm-week ITL roles swapped",
     "tex/closedloop.tex",
     lambda s: s.replace("(6.41 against 21.28~ms", "(21.28 against 6.41~ms", 1),
     "ITL roles"),
    ("chapter crossing 808 -> 809",
     "tex/closedloop.tex",
     lambda s: s.replace("\\SI{808}{\\milli\\second} the static reference",
                         "\\SI{809}{\\milli\\second} the static reference", 1),
     "808 crossing"),
    ("chapter crossing 907 -> 908",
     "tex/closedloop.tex",
     lambda s: s.replace("below \\SI{907}{\\milli\\second} the 1.042$\\times$",
                         "below \\SI{908}{\\milli\\second} the 1.042$\\times$", 1),
     "907 crossing"),
    ("chapter role frontier strict -> factorial strict",
     "tex/closedloop.tex",
     lambda s: s.replace("frontier strict", "factorial strict", 1),
     "frontier strict role"),
    ("conclusion 682 changed independently",
     "tex/conclusion.tex",
     lambda s: s.replace("down to \\SI{682}{\\milli\\second} under warm-pool readiness; under the strict",
                         "down to \\SI{683}{\\milli\\second} under warm-pool readiness; under the strict", 1),
     "conclusion 682"),
    ("conclusion warm-pool qualifier removed",
     "tex/conclusion.tex",
     lambda s: s.replace("down to \\SI{682}{\\milli\\second} under warm-pool readiness; under the strict",
                         "down to \\SI{682}{\\milli\\second}; under the strict", 1),
     "conclusion 682"),
    ("deck reveal 682 changed",
     "defense/reveal/index.html",
     lambda s: s.replace("passes down to <b>682 ms</b>", "passes down to <b>683 ms</b>", 1),
     "reveal/index.html"),
    ("deck single-mirror 907 changed",
     "defense/deck_single.html",
     lambda s: s.replace("floor to 907 ms", "floor to 908 ms", 1),
     "deck_single.html"),
    ("deck one-mirror integer-scope phrase diverged",
     "defense/reveal/index.html",
     lambda s: s.replace("(integer-ms crossings)", "(continuous crossings)", 1),
     "reveal/index.html"),
    ("fulltrace forecast-free flipped to forecast-driven",
     "tex/closedloop.tex",
     lambda s: s.replace("seven-day rows are forecast-free",
                         "seven-day rows are forecast-driven", 1),
     "forecast-free"),
    ("context-split roles swapped 1.4 <-> 5.60",
     "tex/closedloop.tex",
     lambda s: s.replace("scoring its\n1.4-day context split", "scoring its\n5.60-day context split", 1)
                if "scoring its\n1.4-day context split" in s
                else s.replace("1.4-day context split as targets", "5.60-day context split as targets", 1),
     "context-split"),
    ("abstract populations swapped (D72)",
     "tex/tese.tex",
     lambda s: s.replace("(Azure, one million requests",
                         "(Azure, 749,601 requests over 5.60 days) (", 1),
     "full-trace population attached"),
    ("conclusion denominator relabeled time-matched (D72)",
     "tex/conclusion.tex",
     lambda s: s.replace("under request-matched normalization the",
                         "under time-matched normalization the", 1),
     "REQUEST-matched"),
    ("deck post-hoc disclosure erased in one mirror (D72)",
     "defense/reveal/index.html",
     lambda s: s.replace("reactive-favorable post-hoc", "pre-frozen symmetric", 1),
     "disclosure"),
    ("C2 outside-set role removed",
     "tex/closedloop.tex",
     lambda s: s.replace("encoder-only comparator outside the 29-arm composed set",
                         "encoder-only comparator of the 29-arm composed set", 1),
     "C2 marked outside"),
    ("silicon replay promoted to conservative bound (199c)",
     "tex/metodologia.tex",
     lambda s: s.replace("not a conservative bound", "a conservative lower bound", 1),
     "sensitivity-not-bound"),
    ("silicon fc estimand perturbed",
     "tex/metodologia.tex",
     lambda s: s.replace("782.455 \\pm 0.270", "782.5 \\pm 0.270", 1),
     "fc estimand"),
    ("calm-day absolutes promoted to engine-independent",
     "tex/metodologia.tex",
     lambda s: s.replace("engine-band-conditional", "engine-independent", 1),
     "engine-band-conditional"),
    ("calm-day near-tie perturbed",
     "tex/metodologia.tex",
     lambda s: s.replace("1{,}121.004 \\pm 0.143", "1{,}121.0 \\pm 0.143", 1),
     "fc/re HF-eager estimand pair"),

    # ---- D114 abstract role families (bilingual), one or more probe each ----
    # A. burst-window population of the encoder breach
    ("EN abstract: burst-window qualifier stripped from the breach (D114.1)",
     "tex/tese.tex",
     lambda s: s.replace(
         "reproduces the decoupling: \\emph{inside the burst window} the encoder pool",
         "reproduces the decoupling: the encoder pool", 1),
     "burst-window qualifier"),
    ("PT abstract: burst-window qualifier stripped from the breach (D114.1)",
     "tex/tese.tex",
     lambda s: s.replace(
         "\\emph{dentro da janela de rajada} o \\emph{pool} codificador viola",
         "o \\emph{pool} codificador viola", 1),
     "burst-window qualifier"),

    # B. floor endpoints must never return as a scope-free range
    ("EN abstract: scope-free floor range reintroduced (D114.2)",
     "tex/tese.tex",
     lambda s: s.replace(
         "worker-hours). The gain is a trade-off",
         "worker-hours), while the cheapest evaluation-passing reactive warm"
         " floor costs 1.20\\vez{} to 1.67\\vez{} the forecast's worker-time"
         " depending on readiness model. The gain is a trade-off", 1),
     "scope-free floor"),
    ("PT abstract: scope-free floor range reintroduced (D114.2)",
     "tex/tese.tex",
     lambda s: s.replace(
         "\\emph{worker}-horas). O\nganho",
         "\\emph{worker}-horas), enquanto o piso quente reativo mais barato"
         " custa de 1,20\\vez{} a 1,67\\vez{} a previsão conforme o modelo de"
         " prontidão. O\nganho", 1),
     "scope-free floor"),

    # C. language operating point and what "only" governs
    ("EN abstract: language 'only' moved off the conversion (D114.3)",
     "tex/tese.tex",
     lambda s: s.replace("policy holds its SLA only through",
                         "policy reaches only near break-even through", 1),
     "ONLY-through"),
    ("EN abstract: language operating point (p90/scale-8) erased (D114.3)",
     "tex/tese.tex",
     lambda s: s.replace("at its published p90/scale-8 point, is near",
                         "is near", 1),
     "p90/scale-8"),
    ("PT abstract: matching-operation names degraded to bare axes (D114.3)",
     "tex/tese.tex",
     lambda s: s.replace("pareado por tempo", "por tempo", 1)
                .replace("pareado por requisições", "por requisições", 1),
     "matching-operation names"),

    # D. live (language pool) vs physical (encoder-only) separation
    ("EN abstract: live and physical evidence fused into one verdict (D114.4)",
     "tex/tese.tex",
     lambda s: s.replace("mocked engines);\nseparately, five-repetition",
                         "mocked engines) and survives five-repetition", 1),
     "EN abstract: live"),
    ("EN abstract: physical replay relabeled controller-in-loop (D114.4)",
     "tex/tese.tex",
     lambda s: s.replace("five-repetition encoder-only frozen-dispatch retiming",
                         "five-repetition closed-loop re-simulation", 1),
     "EN abstract: live"),
    ("EN abstract: week-scale-simulated clause dropped (D114.4)",
     "tex/tese.tex",
     lambda s: s.replace("\nWeek-scale economics remain simulated.", "", 1),
     "EN abstract: live"),
    ("PT abstract: live evidence relabeled as the encoder pool (D114.4)",
     "tex/tese.tex",
     lambda s: s.replace(
         "O veredicto p90/reativo do \\emph{pool} de linguagem",
         "O veredicto p90/reativo do \\emph{pool} codificador", 1),
     "PT abstract: live"),

    # E. the convention-minimized full-span RQ3 lead
    ("EN abstract: RQ3 lead worker-second operands swapped (D114.5)",
     "tex/tese.tex",
     lambda s: s.replace("2{,}410{,}754.7", "XSWAPX", 1)
                .replace("2{,}611{,}319.7", "2{,}410{,}754.7", 1)
                .replace("XSWAPX", "2{,}611{,}319.7", 1),
     "polarity reversed"),
    ("EN abstract: RQ3 lead saving fabricated 7.7% -> 17.7%",
     "tex/tese.tex",
     lambda s: s.replace("worker-seconds (7.7\\% less)",
                         "worker-seconds (17.7\\% less)", 1),
     "recompute"),
    ("EN abstract: RQ3 lead convention-free clause removed (D114.5)",
     "tex/tese.tex",
     lambda s: s.replace("no burst definition, SLA cutoff, or\npercentile"
                         " selection in either operand ---", "", 1),
     "no burst/SLA/percentile convention"),
    ("EN abstract: RQ3 lead comparator loses 'identically informed' (D114.5)",
     "tex/tese.tex",
     lambda s: s.replace("against the identically informed direct-reactive",
                         "against the direct-reactive", 1),
     "role-scrambled"),
    ("PT abstract: RQ3 lead delay operands swapped (D114.5)",
     "tex/tese.tex",
     lambda s: s.replace("30\\,277,5 contra 34\\,015,6",
                         "34\\,015,6 contra 30\\,277,5", 1),
     "operands disagree"),
    ("PT abstract: evaluation population detached from the RQ3 lead (D72)",
     "tex/tese.tex",
     lambda s: s.replace("nos 5,60\ndias e 749\\,601 requisições da avaliação",
                         "na avaliação", 1),
     "PT abstract: evaluation population"),
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
        (root / "simulation/results/llm_week").mkdir(parents=True)
        shutil.copy(tese / "simulation/results/llm_week/llm_week_stack.json",
                    root / "simulation/results/llm_week/")
        (root / "defense/reveal").mkdir(parents=True)
        shutil.copy(tese / "defense/reveal/index.html", root / "defense/reveal/")
        shutil.copy(tese / "defense/deck_single.html", root / "defense/")
        (root / "simulation/results/factorial_issuetime").mkdir(parents=True)
        shutil.copy(tese / "simulation/results/factorial_issuetime/"
                           "factorial_issuetime_p90_rho15_results.json",
                    root / "simulation/results/factorial_issuetime/")
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
