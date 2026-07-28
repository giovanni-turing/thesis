#!/usr/bin/env python3
"""Span-level language-pool metric stack (author directive 2026-07-27:
grade both pools by the same standard -- full-span absolutes first, windows
as the anti-masking gate). COMPUTE-ONLY: derives llm_week_stack.json from
the five tracked full-week planner-replay reports (week_*.report.json, the
same 749,601-request evaluation-span population as the encoder stack) and
prints a table; touches no manuscript file.

Per arm: GPU-hours, the TTFT quantile ladder + mean + max, ITL p99, and the
threshold-free total delay masses (mean x N request-seconds: TTFT and e2e).
Derived block: reactive-vs-forecast spend ratio, total-TTFT-mass reduction,
and the cross-model 651 ms invariance check. Replays are L=60 planner runs
by construction (declared; not a lead sweep).

Usage: llm_week_stack.py [--check]
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

ARMS = [
    ("forecast_p90_chronos", "week_fc_p90"),
    ("forecast_p90_toto", "week_fc_p90_toto"),
    ("forecast_p90_timesfm", "week_fc_p90_timesfm"),
    ("forecast_p50", "week_fc_p50"),
    ("reactive_stock_planner", "week_re"),
]

QKEYS = ["median_ttft_ms", "p75_ttft_ms", "p90_ttft_ms", "p95_ttft_ms",
         "p99_ttft_ms"]


EXPECT_N = 749601
EXPECT_IN_TOK = 2205332831
EXPECT_OUT_TOK = 140631564
EXPECT_LEAD_S = 60

# The tracked replay drivers whose STARTUP_TIME setting IS the language
# replica lead (msg 223: mechanical link, not filename inference -- the
# upstream 'L30' in encoder-schedule filenames is the encoder's issued
# forecast lead, a different protocol).
# driver -> exact expected STARTUP_TIME=60 occurrence count (msg 224:
# launch.sh assigns the lead separately for the forecast and reactive
# arms, so BOTH assignments are bound, not just the value set)
LEAD_DRIVERS = {
    "launch.sh": 2,                       # relative to this directory
    "../../run_llm_week_p50.sh": 1,
    "../../run_llm_week_models.sh": 1,
}


def lead_config():
    import re as _re
    out = {}
    for rel, want_n in LEAD_DRIVERS.items():
        p = (HERE / rel).resolve()
        vals = _re.findall(r"STARTUP_TIME=(\d+)", p.read_text())
        if vals != [str(EXPECT_LEAD_S)] * want_n:
            raise SystemExit(f"{p.name}: STARTUP_TIME occurrences {vals} != "
                             f"{[str(EXPECT_LEAD_S)] * want_n}")
        out[p.name] = {"lead_s": EXPECT_LEAD_S, "occurrences": want_n}
    out["lead_s"] = EXPECT_LEAD_S
    return out


def arm_row(tag):
    r = json.loads((HERE / f"{tag}.report.json").read_text())
    n = r["num_requests"]
    if n != EXPECT_N or r["completed_requests"] != EXPECT_N:
        raise SystemExit(f"{tag}: population drift "
                         f"(num={n}, completed={r['completed_requests']}, "
                         f"expected {EXPECT_N})")
    # native reported counters bound directly (msg 223), not reconstructed
    if r["total_input_tokens"] != EXPECT_IN_TOK \
            or r["total_output_tokens"] != EXPECT_OUT_TOK:
        raise SystemExit(f"{tag}: native token-counter drift "
                         f"(in={r['total_input_tokens']}, "
                         f"out={r['total_output_tokens']})")
    if r["processed_tokens"] != r["total_input_tokens"] + r["total_output_tokens"]:
        raise SystemExit(f"{tag}: processed_tokens != input + output")
    row = {
        "report": f"{tag}.report.json",
        "num_requests": n,
        "gpu_hours": round(r["gpu_hours"], 1),
        "ttft_ms": {k.replace("_ttft_ms", "").replace("median", "p50"):
                    round(r[k], 1) for k in QKEYS},
        "ttft_mean_ms": round(r["mean_ttft_ms"], 2),
        "ttft_max_ms": round(r["max_ttft_ms"], 1),
        "itl_p99_ms": round(r["p99_itl_ms"], 2),
        "total_ttft_mass_request_s": round(r["mean_ttft_ms"] * n / 1000.0, 1),
        "total_e2e_mass_request_s": round(
            r["mean_e2e_latency_ms"] * n / 1000.0, 1),
    }
    return row


def main():
    check = "--check" in sys.argv
    rows = {arm: arm_row(tag) for arm, tag in ARMS}
    fc = rows["forecast_p90_chronos"]
    re_ = rows["reactive_stock_planner"]
    out = {
        "note": ("span-level language-pool stack over the 5.60-day evaluation "
                 "span (749,601 requests, the encoder stack's population); "
                 "derived from the tracked week planner-replay reports; "
                 "language replica lead L=60 s by construction (evidence: "
                 "llm_week/launch.sh and the results ledger, NOT report "
                 "filenames -- the upstream 'L30' in encoder-schedule names "
                 "is the encoder's issued forecast lead, a different "
                 "protocol); total masses are mean x N (a post-hoc "
                 "threshold-integrated magnitude synthesis; TTFT p99 remains "
                 "the declared contract statistic). The frozen endpoint "
                 "remains the declared TTFT/ITL p99 SLAs with per-window "
                 "grading as the compliance gate."),
        "population": {
            "num_requests": EXPECT_N,
            "input_tokens_total": EXPECT_IN_TOK,
            "output_tokens_total": EXPECT_OUT_TOK,
            "processed_tokens_total": EXPECT_IN_TOK + EXPECT_OUT_TOK,
            "identical_across_all_five_reports": True,
        },
        "lead_config": lead_config(),
        "arms": rows,
        "derived": {
            "reactive_over_fc_spend": round(
                re_["gpu_hours"] / fc["gpu_hours"], 4),
            "fc_ttft_mass_reduction_pct": round(
                (1 - fc["total_ttft_mass_request_s"]
                 / re_["total_ttft_mass_request_s"]) * 100, 1),
            "fc_e2e_mass_reduction_pct": round(
                (1 - fc["total_e2e_mass_request_s"]
                 / re_["total_e2e_mass_request_s"]) * 100, 1),
            "p99_ttft_model_invariant_ms": sorted(
                {rows[a]["ttft_ms"]["p99"]
                 for a in ("forecast_p90_chronos", "forecast_p90_toto",
                           "forecast_p90_timesfm")}),
        },
    }
    if check:
        tracked = json.loads((HERE / "llm_week_stack.json").read_text())
        if tracked == out:
            print("llm_week_stack --check: OK (recomputed == tracked)")
            return
        raise SystemExit("llm_week_stack --check: MISMATCH against tracked artifact")
    (HERE / "llm_week_stack.json").write_text(json.dumps(out, indent=1))
    print(f"{'arm':26s} {'GPU-h':>7} {'p99 TTFT':>9} {'p95':>7} {'mean':>7}"
          f" {'total TTFT':>11} {'total e2e':>11} {'ITL p99':>8}")
    for arm, _ in ARMS:
        r = rows[arm]
        print(f"{arm:26s} {r['gpu_hours']:>7.1f} {r['ttft_ms']['p99']:>9.1f}"
              f" {r['ttft_ms']['p95']:>7.1f} {r['ttft_mean_ms']:>7.2f}"
              f" {r['total_ttft_mass_request_s']:>11.1f}"
              f" {r['total_e2e_mass_request_s']:>11.1f}"
              f" {r['itl_p99_ms']:>8.2f}")
    print("derived:", json.dumps(out["derived"]))
    print(f"wrote {HERE / 'llm_week_stack.json'}")


if __name__ == "__main__":
    main()
