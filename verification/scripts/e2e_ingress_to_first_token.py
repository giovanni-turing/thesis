#!/usr/bin/env python
"""TASK 2 (B6/P0-6): modelled end-to-end ingress-to-first-token p99.

The thesis reports the encoder-delay p99 (588 ms) and the language TTFT p99
(651 ms) SEPARATELY and never combines them per request, even though a real
request traverses BOTH pools: ingress -> encoder pool (encoder_delay) -> LLM
pool (TTFT) -> first token. The user-visible tail is the p99 of the
per-request SUM (encoder_delay recovered EXACTLY, prefill TTFT MODELLED by
AIC and validated -- hence a modelled reconstruction, not a request-linked
replay measurement), which depends on how the two delays are CORRELATED (image
count drives encoder_delay; image+text tokens = ContextTokens drive prefill
TTFT, so the tails are positively coupled).

Method (aggregate fc_p90_L30 run, offset 250399, 749601 reqs, 5.60-day span):
  1. encoder_delay[i]  -- EXACT, recovered per request as emitted_ts[i] -
     raw_arrival[i]. The emitted mooncake timestamp = raw_arrival + encoder_delay
     (encoder_shift_applied=True, speedup=1); raw_arrival[i] is reconstructed
     from load_window() at the same window. hash_ids[0]//100000 = df index i.
  2. TTFT[i]  -- AIC single-pass prefill predict_prefill(1, isl_i, 0) on the
     SAME language-pool model the week replay used (h100_sxm / vllm 0.19.0 /
     Qwen3-VL-8B / TP2). VALIDATED against the week replay report's TTFT
     percentiles: if they match, the week's TTFT is prefill-compute-bound
     (the p90 forecast keeps LLM queueing negligible) and this per-request
     TTFT is faithful; the joint p99 is then well-founded.
  3. e2e[i] = encoder_delay[i] + TTFT[i]  -> report p99/p90/p50 and compare to
     the two marginals, the naive additive p99+p99, and the >= max(p99,p99)
     lower bound.

Run under the aiconfigurator venv.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/gio/tese/workload")
from trace_to_two_pool import load_window  # noqa: E402

OFFSET, MAXREQ = 250399, 749601
# Issue-time schedule (the headline policy). The 124 MB per-request jsonl is a
# gitignored, regenerable intermediate -- regenerate with:
#   simulation/run_44_aggregate_issuetime.sh   (writes fc_p90_L30_issuetime.jsonl)
JSONL = "/home/gio/tese/simulation/results/aggregate44/fc_p90_L30_issuetime.jsonl"
REPORT = "/home/gio/tese/simulation/results/llm_week/week_fc_p90.report.json"
STATS = "/home/gio/tese/simulation/results/aggregate44/fc_p90_L30_issuetime.jsonl.stats.json"
OUT = "/home/gio/tese/simulation/results/rerun_verify/e2e_ingress_to_first_token.json"


def pctile(a, ps=(50, 90, 95, 99)):
    a = np.asarray(a, float)
    return {f"p{p}": round(float(np.percentile(a, p)), 2) for p in ps}


def main():
    # ---- raw ingress arrivals + image counts for the aggregate window ----
    df = load_window(MAXREQ, OFFSET)
    t0 = df["ts"].iloc[0]
    raw_arr_ms = (df["ts"] - t0).dt.total_seconds().to_numpy() * 1000.0
    nimg = df["NumImages"].to_numpy()
    ctx = df["ContextTokens"].to_numpy()
    n = len(df)

    # ---- emitted trace: per request i = hash_ids[0]//100000, emitted_ts, isl ----
    emitted_ts = np.full(n, np.nan)
    isl = np.zeros(n, dtype=np.int64)
    seen = 0
    with open(JSONL) as f:
        for line in f:
            r = json.loads(line)
            i = r["hash_ids"][0] // 100_000
            emitted_ts[i] = r["timestamp"]
            isl[i] = r["input_length"]
            seen += 1
    assert seen == n, f"jsonl rows {seen} != window {n}"
    assert not np.isnan(emitted_ts).any(), "missing emitted rows"

    # ---- encoder_delay[i] = emitted_ts - raw_arrival (exact to 1e-3 ms) ----
    enc_delay = emitted_ts - raw_arr_ms
    enc_delay = np.clip(enc_delay, 0.0, None)  # kill sub-ms rounding on text-only
    # validate against the converter stats (all-request encoder_delay p99)
    st = json.load(open(STATS))
    enc_p99_ref = st["encoder_delay_ms"]["p99"]
    enc_p99_here = float(np.percentile(enc_delay, 99))
    img_mask = nimg > 0

    # ---- language TTFT[i] via AIC single-pass prefill (memoized by isl) ----
    from dynamo._internal.aic import create_session
    sess = create_session(backend_name="vllm", system="h100_sxm",
                          model_path="Qwen/Qwen3-VL-8B-Instruct", tp_size=2,
                          backend_version="0.19.0")
    memo = {}
    uniq = np.unique(isl)
    for v in uniq:
        memo[int(v)] = float(sess.predict_prefill(1, int(v), 0))
    ttft = np.array([memo[int(v)] for v in isl], float)

    # validate TTFT distribution against the week replay report
    rep = json.load(open(REPORT))
    ttft_val = {
        "modeled": pctile(ttft),
        "modeled_mean": round(float(ttft.mean()), 2),
        "modeled_max": round(float(ttft.max()), 2),
        "replay_report": {"p50": rep["median_ttft_ms"], "p90": rep["p90_ttft_ms"],
                          "p95": rep["p95_ttft_ms"], "p99": rep["p99_ttft_ms"],
                          "mean": rep["mean_ttft_ms"], "max": rep["max_ttft_ms"]},
    }

    # ---- modelled end-to-end ingress-to-first-token ----
    # (encoder_delay recovered exactly; prefill TTFT modelled per-request by
    #  AIC and validated against the week replay -- hence "modelled", not "true")
    e2e = enc_delay + ttft
    corr_all = float(np.corrcoef(enc_delay, ttft)[0, 1])
    corr_img = float(np.corrcoef(enc_delay[img_mask], ttft[img_mask])[0, 1])

    enc_p99 = float(np.percentile(enc_delay, 99))
    ttft_p99 = float(np.percentile(ttft, 99))
    e2e_p99 = float(np.percentile(e2e, 99))

    out = {
        "window": "aggregate fc_p90_L30", "offset": OFFSET, "requests": n,
        "requests_with_images": int(img_mask.sum()),
        "encoder_delay_validation": {
            "p99_recovered_here": round(enc_p99_here, 2),
            "p99_converter_stats": enc_p99_ref,
            "matches": abs(enc_p99_here - enc_p99_ref) < 1.0},
        "ttft_validation": ttft_val,
        "marginals_p99_ms": {"encoder_delay": round(enc_p99, 2),
                             "language_ttft": round(ttft_p99, 2)},
        "end_to_end_ingress_to_first_token_ms": {
            **pctile(e2e), "mean": round(float(e2e.mean()), 2),
            "max": round(float(e2e.max()), 2)},
        "comparison_p99": {
            "encoder_delay_only": round(enc_p99, 2),
            "language_ttft_only": round(ttft_p99, 2),
            "modelled_end_to_end": round(e2e_p99, 2),
            "naive_additive_p99+p99": round(enc_p99 + ttft_p99, 2),
            "lower_bound_max_of_marginals": round(max(enc_p99, ttft_p99), 2),
            "e2e_over_language_ttft": round(e2e_p99 / ttft_p99, 3),
            "e2e_over_naive_additive": round(e2e_p99 / (enc_p99 + ttft_p99), 3)},
        "correlation_enc_vs_ttft": {"all_requests": round(corr_all, 3),
                                    "image_requests_only": round(corr_img, 3)},
        # conditional (image-bearing) view: text-only reqs have enc_delay 0 and
        # short prefill, so the e2e tail is dominated by image-bearing requests
        "image_bearing_only_p99_ms": {
            "encoder_delay": round(float(np.percentile(enc_delay[img_mask], 99)), 2),
            "language_ttft": round(float(np.percentile(ttft[img_mask], 99)), 2),
            "modelled_end_to_end": round(float(np.percentile(e2e[img_mask], 99)), 2)},
    }
    json.dump(out, open(OUT, "w"), indent=1)

    print(f"aggregate fc_p90_L30: {n} reqs ({int(img_mask.sum())} image-bearing)")
    print(f"encoder_delay p99 recovered {enc_p99_here:.1f} vs stats {enc_p99_ref} "
          f"[{'OK' if out['encoder_delay_validation']['matches'] else 'MISMATCH'}]")
    print("TTFT modeled vs replay report:")
    print("   modeled:", ttft_val["modeled"], "mean", ttft_val["modeled_mean"],
          "max", ttft_val["modeled_max"])
    print("   replay :", ttft_val["replay_report"])
    print(f"\nMARGINAL p99:  encoder_delay {enc_p99:.1f} ms   language_TTFT {ttft_p99:.1f} ms")
    print(f"MODELLED e2e p99:  {e2e_p99:.1f} ms   (naive additive {enc_p99+ttft_p99:.1f}, "
          f"lower bound {max(enc_p99,ttft_p99):.1f})")
    print(f"correlation enc vs ttft: all {corr_all:.3f}, image-only {corr_img:.3f}")
    print(f"image-bearing e2e p99: {out['image_bearing_only_p99_ms']['modelled_end_to_end']} ms")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
